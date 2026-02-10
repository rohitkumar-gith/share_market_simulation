"""
Company Dashboard - Manage companies, assets, and finances
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from services.auth_service import auth_service
from services.company_service import company_service
from services.asset_service import asset_service # <--- RESTORED
from utils.formatters import Formatter
import config

class CreateCompanyDialog(QDialog):
    """Dialog to create a new company"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Start New Company")
        self.setFixedWidth(400)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Tata Steel")
        form.addRow("Company Name:", self.name_input)
        
        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("e.g. TATA")
        form.addRow("Ticker Symbol:", self.ticker_input)
        
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(1.0, 10000.0)
        self.price_input.setValue(100.0)
        form.addRow("IPO Share Price:", self.price_input)
        
        self.shares_input = QSpinBox()
        self.shares_input.setRange(1000, 10000000)
        self.shares_input.setValue(100000)
        self.shares_input.setSingleStep(1000)
        form.addRow("Total Shares:", self.shares_input)
        
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Brief description of your business...")
        self.desc_input.setMaximumHeight(80)
        form.addRow("Description:", self.desc_input)
        
        layout.addLayout(form)
        
        self.cost_label = QLabel("IPO Listing Fee: ₹5,000")
        self.cost_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.cost_label)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
        self.setLayout(layout)
    
    def get_data(self):
        return (self.name_input.text(), self.ticker_input.text(), 
                self.price_input.value(), self.shares_input.value(), 
                self.desc_input.toPlainText())

class CompanyDashboard(QWidget):
    """Dashboard for company owners"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_company_id = None
        self.init_ui()
        
        # RESTORED: Auto-refresh pending revenue every 5 seconds
        self.rev_timer = QTimer(self)
        self.rev_timer.timeout.connect(self.update_revenue_display)
        self.rev_timer.start(5000)
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("My Companies")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        
        new_btn = QPushButton("+ Start New Company")
        new_btn.setStyleSheet(f"background-color: {config.COLOR_PRIMARY}; color: white; font-weight: bold; padding: 8px 15px;")
        new_btn.clicked.connect(self.start_new_company)
        header.addWidget(new_btn)
        
        layout.addLayout(header)
        
        # Content Stack
        self.content_stack = QStackedWidget()
        
        # --- Page 1: List ---
        self.list_page = QWidget()
        list_layout = QVBoxLayout(self.list_page)
        list_layout.setContentsMargins(0, 0, 0, 0)
        
        self.company_list = QListWidget()
        self.company_list.setStyleSheet("""
            QListWidget { background-color: #2D2D2D; border-radius: 8px; padding: 10px; }
            QListWidget::item { padding: 15px; border-bottom: 1px solid #444; font-size: 16px; }
            QListWidget::item:selected { background-color: #444; border-radius: 4px; }
        """)
        self.company_list.itemDoubleClicked.connect(self.open_company_details)
        list_layout.addWidget(self.company_list)
        
        self.content_stack.addWidget(self.list_page)
        
        # --- Page 2: Details (With Tabs) ---
        self.details_page = QWidget()
        details_layout = QVBoxLayout(self.details_page)
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        # Back Nav
        back_btn = QPushButton("← Back to List")
        back_btn.setStyleSheet("background-color: transparent; color: #BBB; text-align: left;")
        back_btn.setFixedWidth(100)
        back_btn.clicked.connect(self.go_back)
        details_layout.addWidget(back_btn)
        
        # Header
        self.comp_title = QLabel("Company Name")
        self.comp_title.setFont(QFont('Arial', 22, QFont.Bold))
        self.comp_title.setStyleSheet(f"color: {config.COLOR_ACCENT};")
        details_layout.addWidget(self.comp_title)
        
        # Tabs Container
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_overview_tab(), "📊 Overview")
        self.tabs.addTab(self.create_finance_tab(), "💰 Finance & Dividends")
        self.tabs.addTab(self.create_ops_tab(), "🏭 Operations (Assets)") # RESTORED
        
        details_layout.addWidget(self.tabs)
        self.content_stack.addWidget(self.details_page)
        
        layout.addWidget(self.content_stack)
        self.setLayout(layout)
        self.refresh_data()

    # --- Tab Builders ---

    def create_overview_tab(self):
        widget = QWidget()
        layout = QGridLayout()
        layout.setSpacing(15)
        
        self.lbl_price = self.create_stat_card("Share Price", "₹0.00")
        layout.addWidget(self.lbl_price, 0, 0)
        
        self.lbl_market_cap = self.create_stat_card("Market Cap", "₹0.00")
        layout.addWidget(self.lbl_market_cap, 0, 1)
        
        self.lbl_net_worth = self.create_stat_card("Net Worth", "₹0.00")
        layout.addWidget(self.lbl_net_worth, 1, 0)
        
        self.lbl_wallet_overview = self.create_stat_card("Wallet Balance", "₹0.00")
        layout.addWidget(self.lbl_wallet_overview, 1, 1)
        
        # Add filler to push content up
        layout.setRowStretch(2, 1)
        widget.setLayout(layout)
        return widget

    def create_finance_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Wallet Control
        grp = QGroupBox("Company Wallet")
        form = QFormLayout()
        
        self.lbl_wallet_finance = QLabel("₹0.00")
        self.lbl_wallet_finance.setFont(QFont("Arial", 16, QFont.Bold))
        self.lbl_wallet_finance.setStyleSheet(f"color: {config.COLOR_SUCCESS};")
        form.addRow("Current Balance:", self.lbl_wallet_finance)
        
        layout.addWidget(grp)
        grp.setLayout(form)
        
        # Actions Row
        actions = QHBoxLayout()
        
        btn_dep = QPushButton("Deposit Funds")
        btn_dep.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white;")
        btn_dep.clicked.connect(self.deposit_funds)
        actions.addWidget(btn_dep)
        
        btn_with = QPushButton("Withdraw Funds")
        btn_with.setStyleSheet(f"background-color: {config.COLOR_WARNING}; color: white;")
        btn_with.clicked.connect(self.withdraw_funds)
        actions.addWidget(btn_with)
        
        btn_div = QPushButton("Issue Dividend")
        btn_div.setStyleSheet("background-color: #8E44AD; color: white; font-weight: bold;")
        btn_div.clicked.connect(self.issue_dividend)
        actions.addWidget(btn_div)
        
        layout.addLayout(actions)
        
        # Transactions
        layout.addWidget(QLabel("Recent Transactions"))
        self.trans_table = QTableWidget()
        self.trans_table.setColumnCount(3)
        self.trans_table.setHorizontalHeaderLabels(["Type", "Amount", "Description"])
        self.trans_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.trans_table)
        
        widget.setLayout(layout)
        return widget

    def create_ops_tab(self):
        """RESTORED: Buy Assets & Collect Revenue"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 1. Buy Section
        buy_grp = QGroupBox("Marketplace")
        buy_layout = QHBoxLayout()
        
        self.assets_combo = QComboBox()
        # Populate later in refresh_data/load_details
        buy_layout.addWidget(self.assets_combo, 2)
        
        buy_btn = QPushButton("Buy Asset")
        buy_btn.setStyleSheet(f"background-color: {config.COLOR_PRIMARY}; color: white;")
        buy_btn.clicked.connect(self.buy_asset)
        buy_layout.addWidget(buy_btn, 1)
        
        buy_grp.setLayout(buy_layout)
        layout.addWidget(buy_grp)
        
        # 2. Revenue Section
        rev_grp = QGroupBox("Revenue Control")
        rev_layout = QHBoxLayout()
        
        self.pending_revenue_lbl = QLabel("Pending: ₹0.00")
        self.pending_revenue_lbl.setFont(QFont("Arial", 12, QFont.Bold))
        self.pending_revenue_lbl.setStyleSheet(f"color: {config.COLOR_WARNING};")
        rev_layout.addWidget(self.pending_revenue_lbl)
        
        self.collect_btn = QPushButton("Collect Revenue")
        self.collect_btn.clicked.connect(self.collect_revenue)
        rev_layout.addWidget(self.collect_btn)
        
        rev_grp.setLayout(rev_layout)
        layout.addWidget(rev_grp)
        
        # 3. List
        layout.addWidget(QLabel("Owned Assets"))
        self.owned_assets_list = QListWidget()
        layout.addWidget(self.owned_assets_list)
        
        widget.setLayout(layout)
        return widget

    # --- Helpers ---

    def create_stat_card(self, title, value):
        frame = QFrame()
        frame.setStyleSheet("background-color: #333; border-radius: 8px; padding: 10px;")
        l = QVBoxLayout(frame)
        t = QLabel(title)
        t.setStyleSheet("color: #888; font-size: 12px;")
        v = QLabel(value)
        v.setFont(QFont('Arial', 16, QFont.Bold))
        v.setStyleSheet("color: white;")
        l.addWidget(t)
        l.addWidget(v)
        return frame

    def update_card_value(self, frame, value):
        labels = frame.findChildren(QLabel)
        if len(labels) >= 2: labels[1].setText(value)

    # --- Logic ---

    def refresh_data(self):
        user = auth_service.get_current_user()
        if not user: return
        
        # Refresh Company List
        self.company_list.clear()
        companies = company_service.get_user_companies(user.user_id)
        
        if not companies:
            self.company_list.addItem("You haven't started any companies yet.")
        else:
            for comp in companies:
                item = QListWidgetItem(f"{comp['company_name']} ({comp['ticker_symbol']})")
                item.setData(Qt.UserRole, comp['company_id'])
                self.company_list.addItem(item)
                
        # Refresh Details if active
        if self.current_company_id:
            self.load_company_details(self.current_company_id)

    def load_company_details(self, company_id):
        # Fetch Data
        data = company_service.get_company_financial_summary(company_id)
        details = company_service.get_company_details(company_id)
        
        if not data or not details: return
        
        comp = details['company']
        self.comp_title.setText(f"{comp['company_name']} ({comp['ticker_symbol']})")
        
        # 1. Update Overview Stats
        self.update_card_value(self.lbl_price, Formatter.format_currency(data['share_price']))
        self.update_card_value(self.lbl_market_cap, Formatter.format_currency(data['market_cap']))
        self.update_card_value(self.lbl_net_worth, Formatter.format_currency(data['net_worth']))
        self.update_card_value(self.lbl_wallet_overview, Formatter.format_currency(data['wallet_balance']))
        
        # 2. Update Finance Tab
        self.lbl_wallet_finance.setText(Formatter.format_currency(data['wallet_balance']))
        
        self.trans_table.setRowCount(len(data['recent_transactions']))
        for row, t in enumerate(data['recent_transactions']):
            self.trans_table.setItem(row, 0, QTableWidgetItem(t['transaction_type']))
            amt_item = QTableWidgetItem(Formatter.format_currency(t['amount']))
            if t['transaction_type'] in ['DEPOSIT', 'REVENUE']: amt_item.setForeground(Qt.green)
            else: amt_item.setForeground(Qt.red)
            self.trans_table.setItem(row, 1, amt_item)
            self.trans_table.setItem(row, 2, QTableWidgetItem(t['description']))
            
        # 3. Update Operations Tab (Assets)
        # Populate Marketplace Dropdown
        self.assets_combo.clear()
        all_assets = asset_service.get_all_assets()
        for a in all_assets:
            self.assets_combo.addItem(f"{a['name']} - ₹{a['base_price']} (Earns ₹{a['revenue_rate']}/min)", a['asset_id'])
            
        # Populate Owned List
        self.owned_assets_list.clear()
        my_assets = asset_service.get_company_assets(company_id)
        for a in my_assets:
            self.owned_assets_list.addItem(f"{a['name']} (Type: {a['asset_type']}) - Earns: ₹{a['revenue_rate']}/min")
            
        # Update Revenue
        self.update_revenue_display()

    def update_revenue_display(self):
        """Timer calls this to update pending revenue label"""
        if not self.current_company_id or self.content_stack.currentIndex() != 1: 
            return
            
        pending = asset_service.calculate_pending_revenue(self.current_company_id)
        self.pending_revenue_lbl.setText(f"Pending: {Formatter.format_currency(pending)}")
        
        if pending > 0:
            self.collect_btn.setEnabled(True)
            self.collect_btn.setText(f"Collect {Formatter.format_currency(pending)}")
            self.collect_btn.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white; font-weight: bold;")
        else:
            self.collect_btn.setEnabled(False)
            self.collect_btn.setText("No Revenue")
            self.collect_btn.setStyleSheet("background-color: gray; color: white;")

    # --- Actions ---

    def start_new_company(self):
        dialog = CreateCompanyDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, ticker, price, shares, desc = dialog.get_data()
            user = auth_service.get_current_user()
            
            if user.wallet_balance < 5000:
                QMessageBox.warning(self, "Error", "Insufficient funds for listing fee (₹5,000)")
                return
                
            result = company_service.create_company(user.user_id, name, ticker, price, shares, desc)
            if result['success']:
                user.withdraw_funds(5000, f"Listing Fee for {ticker}")
                QMessageBox.information(self, "Success", result['message'])
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Error", result['message'])

    def open_company_details(self, item):
        self.current_company_id = item.data(Qt.UserRole)
        if self.current_company_id:
            self.load_company_details(self.current_company_id)
            self.content_stack.setCurrentIndex(1)

    def go_back(self):
        self.content_stack.setCurrentIndex(0)
        self.current_company_id = None

    def deposit_funds(self):
        if not self.current_company_id: return
        amount, ok = QInputDialog.getDouble(self, "Deposit", "Amount to deposit:", 1000, 1, 10000000, 2)
        if ok:
            user = auth_service.get_current_user()
            res = company_service.deposit_to_wallet(self.current_company_id, user.user_id, amount)
            QMessageBox.information(self, "Result", res['message'])
            self.refresh_data()

    def withdraw_funds(self):
        if not self.current_company_id: return
        amount, ok = QInputDialog.getDouble(self, "Withdraw", "Amount to withdraw:", 1000, 1, 10000000, 2)
        if ok:
            user = auth_service.get_current_user()
            res = company_service.withdraw_from_wallet(self.current_company_id, user.user_id, amount)
            QMessageBox.information(self, "Result", res['message'])
            self.refresh_data()

    def issue_dividend(self):
        if not self.current_company_id: return
        amount, ok = QInputDialog.getDouble(self, "Dividend", "Amount per share:", 5, 0.1, 1000, 2)
        if ok:
            user = auth_service.get_current_user()
            res = company_service.issue_dividend(self.current_company_id, user.user_id, amount)
            QMessageBox.information(self, "Result", res['message'])
            self.refresh_data()

    def buy_asset(self):
        if not self.current_company_id or self.assets_combo.currentIndex() == -1: return
        
        asset_id = self.assets_combo.currentData()
        user = auth_service.get_current_user()
        
        res = asset_service.buy_asset_for_company(user.user_id, self.current_company_id, asset_id)
        QMessageBox.information(self, "Result", res['message'])
        self.refresh_data()

    def collect_revenue(self):
        if not self.current_company_id: return
        rev = asset_service.collect_revenue(self.current_company_id)
        if rev > 0:
            QMessageBox.information(self, "Success", f"Collected {Formatter.format_currency(rev)}!")
        else:
            QMessageBox.information(self, "Info", "No revenue to collect.")
        self.refresh_data()