"""
Company Dashboard - Manage companies, assets, finances, corporate lending, and Shareholders
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QBrush
from services.auth_service import auth_service
from services.company_service import company_service
from services.asset_service import asset_service
from utils.formatters import Formatter
import config

class CreateCompanyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Start New Company (IPO)")
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
        self.price_input.valueChanged.connect(self.update_cost_calculator) # Live update
        form.addRow("IPO Share Price:", self.price_input)
        
        self.shares_input = QSpinBox()
        self.shares_input.setRange(1000, 10000000)
        self.shares_input.setValue(100000)
        self.shares_input.setSingleStep(1000)
        self.shares_input.valueChanged.connect(self.update_cost_calculator) # Live update
        form.addRow("Total Shares:", self.shares_input)
        
        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(80)
        form.addRow("Description:", self.desc_input)
        
        layout.addLayout(form)
        
        # --- NEW: Mandatory 30% Stake Calculator UI ---
        calc_box = QGroupBox("Required Founder's Investment (30% Stake)")
        calc_box.setStyleSheet("QGroupBox { border: 1px solid #E67E22; border-radius: 5px; margin-top: 10px; }")
        calc_layout = QVBoxLayout()
        
        self.stake_info_lbl = QLabel("You must purchase 30% of the company at IPO.")
        self.stake_info_lbl.setStyleSheet("color: #888; font-size: 12px;")
        calc_layout.addWidget(self.stake_info_lbl)
        
        self.total_cost_lbl = QLabel("Required Capital: ₹0.00")
        self.total_cost_lbl.setFont(QFont('Arial', 12, QFont.Bold))
        self.total_cost_lbl.setStyleSheet("color: #E67E22;")
        self.total_cost_lbl.setAlignment(Qt.AlignCenter)
        calc_layout.addWidget(self.total_cost_lbl)
        
        calc_box.setLayout(calc_layout)
        layout.addWidget(calc_box)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
        self.setLayout(layout)
        self.update_cost_calculator() # Run once on load
        
    def update_cost_calculator(self):
        """Dynamically calculates the 30% cost as the user types"""
        total_shares = self.shares_input.value()
        price = self.price_input.value()
        
        founder_shares = int(total_shares * 0.30)
        required_capital = founder_shares * price
        
        self.stake_info_lbl.setText(f"You will receive {Formatter.format_number(founder_shares)} shares.")
        self.total_cost_lbl.setText(f"Required Capital: {Formatter.format_currency(required_capital)}")

    def get_data(self):
        return (self.name_input.text(), self.ticker_input.text(), self.price_input.value(), self.shares_input.value(), self.desc_input.toPlainText())

class CompanyDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_company_id = None
        self.init_ui()
        self.rev_timer = QTimer(self)
        self.rev_timer.timeout.connect(self.update_revenue_display)
        self.rev_timer.start(5000)
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
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
        
        # --- Page 2: Details ---
        self.details_page = QWidget()
        details_layout = QVBoxLayout(self.details_page)
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        back_btn = QPushButton("← Back to List")
        back_btn.setStyleSheet("background-color: transparent; color: #BBB; text-align: left;")
        back_btn.setFixedWidth(100)
        back_btn.clicked.connect(self.go_back)
        details_layout.addWidget(back_btn)
        
        self.comp_title = QLabel("Company Name")
        self.comp_title.setFont(QFont('Arial', 22, QFont.Bold))
        self.comp_title.setStyleSheet(f"color: {config.COLOR_ACCENT};")
        details_layout.addWidget(self.comp_title)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_overview_tab(), "📊 Overview")
        self.tabs.addTab(self.create_finance_tab(), "💰 Finance & Dividends")
        self.tabs.addTab(self.create_ops_tab(), "🏭 Assets") 
        self.tabs.addTab(self.create_lending_tab(), "🏦 Corporate Lending")
        self.tabs.addTab(self.create_shareholders_tab(), "👥 Shareholders")
        self.tabs.addTab(self.create_settings_tab(), "⚙️ Settings")
        
        details_layout.addWidget(self.tabs)
        self.content_stack.addWidget(self.details_page)
        
        layout.addWidget(self.content_stack)
        self.setLayout(layout)
        self.refresh_data()

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
        layout.setRowStretch(2, 1)
        widget.setLayout(layout)
        return widget

    def create_finance_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        grp = QGroupBox("Company Wallet")
        form = QFormLayout()
        self.lbl_wallet_finance = QLabel("₹0.00")
        self.lbl_wallet_finance.setFont(QFont("Arial", 16, QFont.Bold))
        self.lbl_wallet_finance.setStyleSheet(f"color: {config.COLOR_SUCCESS};")
        form.addRow("Current Balance:", self.lbl_wallet_finance)
        grp.setLayout(form)
        layout.addWidget(grp)
        
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
        
        layout.addWidget(QLabel("Recent Transactions"))
        self.trans_table = QTableWidget()
        self.trans_table.setColumnCount(3)
        self.trans_table.setHorizontalHeaderLabels(["Type", "Amount", "Description"])
        self.trans_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.trans_table)
        widget.setLayout(layout)
        return widget

    def create_ops_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        buy_grp = QGroupBox("Marketplace")
        buy_layout = QHBoxLayout()
        self.assets_combo = QComboBox()
        buy_layout.addWidget(self.assets_combo, 2)
        buy_btn = QPushButton("Buy Asset")
        buy_btn.setStyleSheet(f"background-color: {config.COLOR_PRIMARY}; color: white;")
        buy_btn.clicked.connect(self.buy_asset)
        buy_layout.addWidget(buy_btn, 1)
        buy_grp.setLayout(buy_layout)
        layout.addWidget(buy_grp)
        
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
        
        layout.addWidget(QLabel("Owned Assets"))
        self.owned_assets_list = QListWidget()
        layout.addWidget(self.owned_assets_list)
        widget.setLayout(layout)
        return widget

    def create_lending_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.lending_sub_tabs = QTabWidget()
        self.lending_sub_tabs.setStyleSheet("""
            QTabBar::tab { background: #333; color: white; padding: 8px 15px; font-weight: bold; border-radius: 4px; margin: 2px;}
            QTabBar::tab:selected { background: #E67E22; }
        """)
        
        proposal_tab = QWidget()
        prop_layout = QVBoxLayout(proposal_tab)
        action_grp = QGroupBox("New Corporate Loan Proposal")
        form = QFormLayout()
        
        self.loan_action_combo = QComboBox()
        self.loan_action_combo.addItems(["Offer a Loan", "Request a Loan"])
        self.loan_action_combo.currentIndexChanged.connect(self.toggle_lending_form)
        form.addRow("Action:", self.loan_action_combo)
        
        self.loan_type_combo = QComboBox()
        self.loan_type_combo.addItems(["COMPANY", "PLAYER"])
        form.addRow("Target Type:", self.loan_type_combo)
        
        self.loan_target_input = QLineEdit()
        self.loan_target_input.setPlaceholderText("Enter Target Ticker or Username")
        form.addRow("Target Name:", self.loan_target_input)
        
        self.loan_amount = QDoubleSpinBox()
        self.loan_amount.setRange(1000, 100000000)
        self.loan_amount.setValue(50000)
        self.loan_amount.setPrefix("₹ ")
        form.addRow("Amount:", self.loan_amount)
        
        self.loan_interest = QDoubleSpinBox()
        self.loan_interest.setRange(1.0, 100.0)
        self.loan_interest.setValue(10.0)
        self.loan_interest.setSuffix("%")
        form.addRow("Interest Rate:", self.loan_interest)
        
        self.loan_submit_btn = QPushButton("Send Offer")
        self.loan_submit_btn.setStyleSheet(f"background-color: {config.COLOR_ACCENT}; color: white; font-weight: bold; padding: 10px;")
        self.loan_submit_btn.clicked.connect(self.submit_loan_proposal)
        form.addRow("", self.loan_submit_btn)
        
        action_grp.setLayout(form)
        prop_layout.addWidget(action_grp)
        prop_layout.addStretch()
        self.lending_sub_tabs.addTab(proposal_tab, "📝 New Proposal")
        
        incoming_tab = QWidget()
        inc_layout = QVBoxLayout(incoming_tab)
        self.incoming_loans_table = QTableWidget()
        self.incoming_loans_table.setColumnCount(4)
        self.incoming_loans_table.setHorizontalHeaderLabels(["From", "Type", "Amount", "Action"])
        self.incoming_loans_table.horizontalHeader().setStretchLastSection(True)
        self.incoming_loans_table.setAlternatingRowColors(True)
        self.incoming_loans_table.verticalHeader().setDefaultSectionSize(50)
        inc_layout.addWidget(self.incoming_loans_table)
        self.lending_sub_tabs.addTab(incoming_tab, "📥 Incoming (Action Needed)")
        
        outgoing_tab = QWidget()
        out_layout = QVBoxLayout(outgoing_tab)
        self.outgoing_loans_table = QTableWidget()
        self.outgoing_loans_table.setColumnCount(4)
        self.outgoing_loans_table.setHorizontalHeaderLabels(["To", "Type", "Amount", "Action"])
        self.outgoing_loans_table.horizontalHeader().setStretchLastSection(True)
        self.outgoing_loans_table.setAlternatingRowColors(True)
        self.outgoing_loans_table.verticalHeader().setDefaultSectionSize(50)
        out_layout.addWidget(self.outgoing_loans_table)
        self.lending_sub_tabs.addTab(outgoing_tab, "📤 Pending Outgoing")
        
        portfolio_tab = QWidget()
        port_layout = QVBoxLayout(portfolio_tab)
        self.portfolio_table = QTableWidget()
        self.portfolio_table.setColumnCount(4)
        self.portfolio_table.setHorizontalHeaderLabels(["Borrower", "Type", "Original Amount", "Remaining Balance"])
        self.portfolio_table.horizontalHeader().setStretchLastSection(True)
        self.portfolio_table.setAlternatingRowColors(True)
        self.portfolio_table.verticalHeader().setDefaultSectionSize(50)
        port_layout.addWidget(self.portfolio_table)
        self.lending_sub_tabs.addTab(portfolio_tab, "💼 Active Portfolio")
        
        layout.addWidget(self.lending_sub_tabs)
        return widget

    def create_shareholders_tab(self):
        """NEW: Leaderboard of everyone invested in this company"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("Top Investors")
        title.setFont(QFont('Arial', 16, QFont.Bold))
        layout.addWidget(title)
        
        info = QLabel("If an investor holds more shares than you, they will trigger a Hostile Takeover and seize the company!")
        info.setStyleSheet("color: #C0392B; font-style: italic;") # Red warning
        layout.addWidget(info)
        
        self.shareholders_table = QTableWidget()
        self.shareholders_table.setColumnCount(5)
        self.shareholders_table.setHorizontalHeaderLabels(["Rank", "Shareholder Name", "Shares Owned", "Ownership %", "Status"])
        self.shareholders_table.horizontalHeader().setStretchLastSection(True)
        self.shareholders_table.setAlternatingRowColors(True)
        self.shareholders_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.shareholders_table.verticalHeader().setDefaultSectionSize(40)
        
        layout.addWidget(self.shareholders_table)
        widget.setLayout(layout)
        return widget

    def toggle_lending_form(self):
        if self.loan_action_combo.currentText() == "Request a Loan":
            self.loan_type_combo.setCurrentText("COMPANY")
            self.loan_type_combo.setEnabled(False)
            self.loan_submit_btn.setText("Send Request")
            self.loan_submit_btn.setStyleSheet(f"background-color: {config.COLOR_WARNING}; color: black; font-weight: bold; padding: 10px;")
        else:
            self.loan_type_combo.setEnabled(True)
            self.loan_submit_btn.setText("Send Offer")
            self.loan_submit_btn.setStyleSheet(f"background-color: {config.COLOR_ACCENT}; color: white; font-weight: bold; padding: 10px;")

    def create_settings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        edit_grp = QGroupBox("Edit Details")
        form = QFormLayout()
        self.edit_name_input = QLineEdit()
        form.addRow("Company Name:", self.edit_name_input)
        self.edit_desc_input = QTextEdit()
        self.edit_desc_input.setMaximumHeight(80)
        form.addRow("Description:", self.edit_desc_input)
        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white; width: 150px;")
        save_btn.clicked.connect(self.save_company_details)
        form.addRow("", save_btn)
        edit_grp.setLayout(form)
        layout.addWidget(edit_grp)
        
        shares_grp = QGroupBox("Corporate Actions")
        shares_layout = QVBoxLayout()
        issue_form = QFormLayout()
        self.issue_shares_spin = QSpinBox()
        self.issue_shares_spin.setRange(100, 10000000)
        self.issue_shares_spin.setValue(1000)
        self.issue_shares_spin.setSingleStep(1000)
        issue_form.addRow("Shares to Issue:", self.issue_shares_spin)
        issue_btn = QPushButton("Issue Shares")
        issue_btn.setStyleSheet(f"background-color: {config.COLOR_PRIMARY}; color: white;")
        issue_btn.clicked.connect(self.issue_new_shares)
        issue_form.addRow("", issue_btn)
        shares_layout.addLayout(issue_form)
        shares_grp.setLayout(shares_layout)
        layout.addWidget(shares_grp)
        layout.addStretch()
        widget.setLayout(layout)
        return widget

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

    def refresh_data(self):
        user = auth_service.get_current_user()
        if not user: return
        current_row = self.company_list.currentRow()
        
        self.company_list.clear()
        
        # When fetching companies, the service auto-checks for Hostile Takeovers!
        companies = company_service.get_user_companies(user.user_id)
        if not companies: self.company_list.addItem("You haven't started any companies yet.")
        else:
            for comp in companies:
                item = QListWidgetItem(f"{comp['company_name']} ({comp['ticker_symbol']})")
                item.setData(Qt.UserRole, comp['company_id'])
                self.company_list.addItem(item)
                
        if current_row >= 0 and current_row < self.company_list.count():
            self.company_list.setCurrentRow(current_row)
        
        # If the user was viewing a company they just lost to a Hostile Takeover, kick them out!
        if self.current_company_id:
            still_owns = any(c['company_id'] == self.current_company_id for c in companies)
            if not still_owns:
                QMessageBox.critical(self, "Hostile Takeover!", "You have lost majority ownership of this company. It has been seized by another investor!")
                self.go_back()
            else:
                self.load_company_details(self.current_company_id)

    def load_company_details(self, company_id):
        data = company_service.get_company_financial_summary(company_id)
        details = company_service.get_company_details(company_id)
        if not data or not details: return
        
        comp = details['company']
        self.comp_title.setText(f"{comp['company_name']} ({comp['ticker_symbol']})")
        self.edit_name_input.setText(comp['company_name'])
        self.edit_desc_input.setText(comp.get('description', ''))
        
        real_net_worth = data.get('wallet_balance', 0) + data.get('total_assets', 0)
        self.update_card_value(self.lbl_price, Formatter.format_currency(data['share_price']))
        self.update_card_value(self.lbl_market_cap, Formatter.format_currency(data['market_cap']))
        self.update_card_value(self.lbl_net_worth, Formatter.format_currency(real_net_worth))
        self.update_card_value(self.lbl_wallet_overview, Formatter.format_currency(data.get('wallet_balance', 0)))
        
        self.lbl_wallet_finance.setText(Formatter.format_currency(data.get('wallet_balance', 0)))
        
        self.trans_table.setRowCount(len(data['recent_transactions']))
        for row, t in enumerate(data['recent_transactions']):
            self.trans_table.setItem(row, 0, QTableWidgetItem(t['transaction_type']))
            amt_item = QTableWidgetItem(Formatter.format_currency(t['amount']))
            if t['transaction_type'] in ['DEPOSIT', 'REVENUE', 'LOAN_RECEIVED', 'LOAN_PAYMENT']: amt_item.setForeground(QBrush(QColor(Qt.green)))
            else: amt_item.setForeground(QBrush(QColor(Qt.red)))
            self.trans_table.setItem(row, 1, amt_item)
            self.trans_table.setItem(row, 2, QTableWidgetItem(t['description']))
            
        if self.assets_combo.count() == 0:
            self.assets_combo.clear()
            for a in asset_service.get_all_assets():
                self.assets_combo.addItem(f"{a['name']} - ₹{a['base_price']}", a['asset_id'])
            
        self.owned_assets_list.clear()
        for a in asset_service.get_company_assets(company_id):
            self.owned_assets_list.addItem(f"{a['name']} - Earns: ₹{a['revenue_rate']}/min")
            
        self.update_revenue_display()
        self.refresh_lending_tab()
        
        # Update Shareholders Table
        shareholders = details.get('shareholders', [])
        self.shareholders_table.setRowCount(len(shareholders))
        
        current_user = auth_service.get_current_user()
        
        for row, holder in enumerate(shareholders):
            h_dict = dict(holder)
            
            rank_item = QTableWidgetItem(f"#{row + 1}")
            rank_item.setFont(QFont('Arial', 10, QFont.Bold))
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.shareholders_table.setItem(row, 0, rank_item)
            
            name = h_dict['full_name']
            if h_dict['username'].endswith('Bot'): name += " 🤖"
            if current_user and h_dict['user_id'] == current_user.user_id: name += " (You)"
            self.shareholders_table.setItem(row, 1, QTableWidgetItem(name))
            
            shares_item = QTableWidgetItem(Formatter.format_number(h_dict['quantity']))
            shares_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.shareholders_table.setItem(row, 2, shares_item)
            
            total_issued = h_dict.get('total_issued_shares') or 1 
            percent = (h_dict['quantity'] / total_issued) * 100 if total_issued > 0 else 0
            
            pct_item = QTableWidgetItem(f"{percent:.2f}%")
            pct_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.shareholders_table.setItem(row, 3, pct_item)
            
            status = "Owner 👑" if row == 0 else "Investor"
            status_item = QTableWidgetItem(status)
            if row == 0: status_item.setForeground(QBrush(QColor("#D4AF37"))) # Gold for owner
            self.shareholders_table.setItem(row, 4, status_item)

    def refresh_lending_tab(self):
        if not self.current_company_id: return
        dash = company_service.get_company_lending_dashboard(self.current_company_id)
        
        self.incoming_loans_table.setRowCount(len(dash['action_required']))
        for row, loan in enumerate(dash['action_required']):
            l_type = "They Offered" if not loan['is_request'] else "They Requested"
            self.incoming_loans_table.setItem(row, 0, QTableWidgetItem(loan['other_name']))
            self.incoming_loans_table.setItem(row, 1, QTableWidgetItem(l_type))
            self.incoming_loans_table.setItem(row, 2, QTableWidgetItem(f"{Formatter.format_currency(loan['amount'])} @ {loan['interest_rate']}%"))
            
            w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(5, 5, 5, 5)
            btn_acc = QPushButton("Accept")
            btn_acc.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white; padding: 5px;")
            btn_rej = QPushButton("Reject")
            btn_rej.setStyleSheet(f"background-color: {config.COLOR_DANGER}; color: white; padding: 5px;")
            
            btn_acc.clicked.connect(lambda checked, ln=loan: self.action_loan(ln, "ACCEPT"))
            btn_rej.clicked.connect(lambda checked, ln=loan: self.action_loan(ln, "REJECT"))
            
            l.addWidget(btn_acc); l.addWidget(btn_rej)
            self.incoming_loans_table.setCellWidget(row, 3, w)

        self.outgoing_loans_table.setRowCount(len(dash['pending_outgoing']))
        for row, loan in enumerate(dash['pending_outgoing']):
            l_type = "We Offered" if not loan['is_request'] else "We Requested"
            self.outgoing_loans_table.setItem(row, 0, QTableWidgetItem(loan['other_name']))
            self.outgoing_loans_table.setItem(row, 1, QTableWidgetItem(l_type))
            self.outgoing_loans_table.setItem(row, 2, QTableWidgetItem(Formatter.format_currency(loan['amount'])))
            
            btn_can = QPushButton("Cancel")
            btn_can.setStyleSheet(f"background-color: {config.COLOR_WARNING}; color: black; padding: 5px;")
            btn_can.clicked.connect(lambda checked, ln=loan: self.action_loan(ln, "CANCEL"))
            self.outgoing_loans_table.setCellWidget(row, 3, btn_can)

        self.portfolio_table.setRowCount(len(dash['portfolio']))
        for row, loan in enumerate(dash['portfolio']):
            self.portfolio_table.setItem(row, 0, QTableWidgetItem(loan['other_name']))
            self.portfolio_table.setItem(row, 1, QTableWidgetItem(loan['type']))
            self.portfolio_table.setItem(row, 2, QTableWidgetItem(Formatter.format_currency(loan['amount'])))
            
            rem = QTableWidgetItem(Formatter.format_currency(loan['remaining_balance']))
            rem.setForeground(QBrush(QColor(Qt.green)))
            self.portfolio_table.setItem(row, 3, rem)

    # --- Actions ---

    def submit_loan_proposal(self):
        if not self.current_company_id: return
        target_id = self.loan_target_input.text().strip()
        if not target_id: return QMessageBox.warning(self, "Error", "Enter a target.")
        
        user = auth_service.get_current_user()
        action = self.loan_action_combo.currentText()
        amount = self.loan_amount.value()
        rate = self.loan_interest.value()
        
        if action == "Offer a Loan":
            res = company_service.offer_loan(self.current_company_id, user.user_id, self.loan_type_combo.currentText(), target_id, amount, rate)
        else:
            res = company_service.request_loan(self.current_company_id, "COMPANY", target_id, amount, rate, user.user_id)
            
        if res['success']:
            QMessageBox.information(self, "Success", res['message'])
            self.loan_target_input.clear()
            self.refresh_data()
        else: QMessageBox.warning(self, "Error", res['message'])

    def action_loan(self, loan, action):
        user = auth_service.get_current_user()
        res = company_service.respond_to_loan(loan['loan_id'], loan['type'], action, user.user_id)
        if res['success']:
            QMessageBox.information(self, "Success", res['message'])
            self.refresh_data()
        else: QMessageBox.warning(self, "Error", res['message'])

    def save_company_details(self):
        if not self.current_company_id: return
        user = auth_service.get_current_user()
        res = company_service.edit_company_details(user.user_id, self.current_company_id, self.edit_name_input.text().strip(), self.edit_desc_input.toPlainText().strip())
        if res['success']: self.refresh_data()
        else: QMessageBox.warning(self, "Error", res['message'])

    def issue_new_shares(self):
        if not self.current_company_id: return
        shares = self.issue_shares_spin.value()
        reply = QMessageBox.question(self, 'Confirm', f"Issue {shares:,} new shares?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            res = company_service.issue_more_shares(auth_service.get_current_user().user_id, self.current_company_id, shares)
            if res['success']: self.refresh_data()
            else: QMessageBox.warning(self, "Error", res['message'])

    def update_revenue_display(self):
        if not self.current_company_id or self.content_stack.currentIndex() != 1: return
        pending = asset_service.calculate_pending_revenue(self.current_company_id)
        self.pending_revenue_lbl.setText(f"Pending: {Formatter.format_currency(pending)}")
        self.collect_btn.setEnabled(pending > 0)
        if pending > 0:
            self.collect_btn.setText(f"Collect {Formatter.format_currency(pending)}")
            self.collect_btn.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white; font-weight: bold;")

    def start_new_company(self):
        dialog = CreateCompanyDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, ticker, price, shares, desc = dialog.get_data()
            user = auth_service.get_current_user()
            
            # --- NEW: Check if they can afford the 30% stake before sending to the backend ---
            founder_shares = int(shares * 0.30)
            required_capital = founder_shares * price
            
            if user.wallet_balance < required_capital: 
                return QMessageBox.warning(self, "Error", f"Insufficient funds. You need {Formatter.format_currency(required_capital)} for the mandatory 30% founder stake.")
            
            res = company_service.create_company(user.user_id, name, ticker, price, shares, desc)
            if res['success']:
                # The wallet is now deducted dynamically in the backend based on the 30% stake!
                QMessageBox.information(self, "Success", res['message'])
                self.refresh_data()
            else: 
                QMessageBox.warning(self, "Error", res['message'])

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
        amount, ok = QInputDialog.getDouble(self, "Deposit", "Amount:", 1000, 1, 10000000, 2)
        if ok:
            res = company_service.deposit_to_wallet(self.current_company_id, auth_service.get_current_user().user_id, amount)
            self.refresh_data()

    def withdraw_funds(self):
        if not self.current_company_id: return
        amount, ok = QInputDialog.getDouble(self, "Withdraw", "Amount:", 1000, 1, 10000000, 2)
        if ok:
            res = company_service.withdraw_from_wallet(self.current_company_id, auth_service.get_current_user().user_id, amount)
            self.refresh_data()

    def issue_dividend(self):
        if not self.current_company_id: return
        amount, ok = QInputDialog.getDouble(self, "Dividend", "Amount per share:", 5, 0.1, 1000, 2)
        if ok:
            res = company_service.issue_dividend(self.current_company_id, auth_service.get_current_user().user_id, amount)
            self.refresh_data()

    def buy_asset(self):
        if not self.current_company_id or self.assets_combo.currentIndex() == -1: return
        res = asset_service.buy_asset_for_company(auth_service.get_current_user().user_id, self.current_company_id, self.assets_combo.currentData())
        self.refresh_data()

    def collect_revenue(self):
        if not self.current_company_id: return
        asset_service.collect_revenue(self.current_company_id)
        self.refresh_data()