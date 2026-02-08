"""
Company Dashboard - Manage companies
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from services.auth_service import auth_service
from services.company_service import company_service
from services.asset_service import asset_service
from utils.formatters import Formatter
import config

class CompanyDashboard(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
        # Auto-refresh pending revenue every 5 seconds (visual only)
        self.rev_timer = QTimer(self)
        self.rev_timer.timeout.connect(self.update_revenue_display)
        self.rev_timer.start(5000)
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Company Management")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        layout.addWidget(title)
        
        # Company Selector
        self.company_selector = QComboBox()
        self.company_selector.currentIndexChanged.connect(self.load_company_details)
        layout.addWidget(QLabel("Select Your Company:"))
        layout.addWidget(self.company_selector)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_overview_tab(), "Overview")
        self.tabs.addTab(self.create_wallet_tab(), "Wallet & Finance")
        self.tabs.addTab(self.create_ops_tab(), "Business Ops (Assets)")
        self.tabs.addTab(self.create_create_tab(), "Create New Company")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        
    def create_overview_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        self.info_label = QLabel("Select a company to view details")
        layout.addWidget(self.info_label)
        widget.setLayout(layout)
        return widget
        
    def create_wallet_tab(self):
        widget = QWidget()
        layout = QFormLayout()
        
        self.wallet_balance_lbl = QLabel("₹0.00")
        self.wallet_balance_lbl.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addRow("Company Wallet:", self.wallet_balance_lbl)
        
        # Deposit
        self.deposit_input = QDoubleSpinBox()
        self.deposit_input.setRange(0, 100000000)
        deposit_btn = QPushButton("Deposit Funds")
        deposit_btn.clicked.connect(self.deposit_funds)
        layout.addRow("Deposit (from User):", self.deposit_input)
        layout.addRow("", deposit_btn)
        
        # Withdraw
        self.withdraw_input = QDoubleSpinBox()
        self.withdraw_input.setRange(0, 100000000)
        withdraw_btn = QPushButton("Withdraw Funds")
        withdraw_btn.clicked.connect(self.withdraw_funds)
        layout.addRow("Withdraw (to User):", self.withdraw_input)
        layout.addRow("", withdraw_btn)
        
        widget.setLayout(layout)
        return widget
        
    def create_ops_tab(self):
        """Buying Assets and Collecting Revenue"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Buy Section
        layout.addWidget(QLabel("<b>Marketplace (Buy Assets)</b>"))
        self.assets_combo = QComboBox()
        buy_btn = QPushButton("Buy Asset")
        buy_btn.clicked.connect(self.buy_asset)
        layout.addWidget(self.assets_combo)
        layout.addWidget(buy_btn)
        
        layout.addSpacing(20)
        
        # Owned Section
        layout.addWidget(QLabel("<b>Owned Assets & Revenue</b>"))
        self.owned_assets_list = QListWidget()
        layout.addWidget(self.owned_assets_list)
        
        # Pending Revenue Display
        revenue_layout = QHBoxLayout()
        self.pending_revenue_lbl = QLabel("Pending Revenue: ₹0.00")
        self.pending_revenue_lbl.setFont(QFont("Arial", 12, QFont.Bold))
        self.pending_revenue_lbl.setStyleSheet(f"color: {config.COLOR_WARNING};")
        revenue_layout.addWidget(self.pending_revenue_lbl)
        
        self.collect_btn = QPushButton("Collect Revenue")
        self.collect_btn.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white; font-weight: bold;")
        self.collect_btn.clicked.connect(self.collect_revenue)
        revenue_layout.addWidget(self.collect_btn)
        
        layout.addLayout(revenue_layout)
        
        widget.setLayout(layout)
        return widget

    def create_create_tab(self):
        widget = QWidget()
        layout = QFormLayout()
        
        self.new_name = QLineEdit()
        layout.addRow("Company Name:", self.new_name)
        self.new_ticker = QLineEdit()
        layout.addRow("Ticker (e.g. TSL):", self.new_ticker)
        self.new_shares = QSpinBox()
        self.new_shares.setRange(1000, 1000000)
        self.new_shares.setValue(10000)
        layout.addRow("Total Shares:", self.new_shares)
        self.new_price = QDoubleSpinBox()
        self.new_price.setValue(10.0)
        layout.addRow("Initial Price:", self.new_price)
        
        create_btn = QPushButton("Launch IPO")
        create_btn.clicked.connect(self.create_company)
        layout.addRow(create_btn)
        
        widget.setLayout(layout)
        return widget

    def refresh_data(self):
        # Reload company list
        user = auth_service.get_current_user()
        if not user: return
        
        companies = company_service.get_user_companies(user.user_id)
        
        # Preserve Company Selection
        current_company_id = self.company_selector.currentData()
        
        self.company_selector.blockSignals(True)
        self.company_selector.clear()
        
        for c in companies:
            c_name = c['company_name'] if isinstance(c, dict) else c.company_name
            c_ticker = c['ticker_symbol'] if isinstance(c, dict) else c.ticker_symbol
            c_id = c['company_id'] if isinstance(c, dict) else c.company_id
            self.company_selector.addItem(f"{c_name} ({c_ticker})", c_id)
            
        # Restore Company Selection
        if current_company_id:
            idx = self.company_selector.findData(current_company_id)
            if idx >= 0:
                self.company_selector.setCurrentIndex(idx)
        
        self.company_selector.blockSignals(False)
        
        if self.company_selector.count() > 0:
            self.load_company_details()
            
            # Preserve Asset Selection
            current_asset_id = self.assets_combo.currentData()
            
            self.assets_combo.blockSignals(True)
            self.assets_combo.clear()
            assets = asset_service.get_all_assets()
            for a in assets:
                self.assets_combo.addItem(f"{a['name']} - ₹{a['base_price']} (Rev: {a['revenue_rate']})", a['asset_id'])
            
            # Restore Asset Selection
            if current_asset_id is not None:
                idx = self.assets_combo.findData(current_asset_id)
                if idx >= 0:
                    self.assets_combo.setCurrentIndex(idx)
            
            self.assets_combo.blockSignals(False)

    def load_company_details(self):
        if self.company_selector.currentIndex() == -1: return
        
        cid = self.company_selector.currentData()
        details = company_service.get_company_details(cid)
        if not details: return
        
        # Overview
        c = details['company']
        
        # Handle dict vs object access
        c_name = c['company_name'] if isinstance(c, dict) else c.company_name
        c_price = c['share_price'] if isinstance(c, dict) else c.share_price
        c_bankrupt = c['is_bankrupt'] if isinstance(c, dict) else c.is_bankrupt
        c_wallet = c['company_wallet'] if isinstance(c, dict) else c.company_wallet

        self.info_label.setText(
            f"Name: {c_name}\n"
            f"Price: ₹{c_price}\n"
            f"Market Cap: ₹{details['market_cap']:,.2f}\n"
            f"Status: {'BANKRUPT' if c_bankrupt else 'Active'}"
        )
        
        # Wallet
        self.wallet_balance_lbl.setText(Formatter.format_currency(c_wallet))
        if c_bankrupt:
            self.wallet_balance_lbl.setStyleSheet("color: red;")
        else:
            self.wallet_balance_lbl.setStyleSheet("color: green;")
            
        # Assets
        self.owned_assets_list.clear()
        my_assets = asset_service.get_company_assets(cid)
        for a in my_assets:
            self.owned_assets_list.addItem(f"{a['name']} (Type: {a['asset_type']}) - Earns: ₹{a['revenue_rate']}/min")

        # Update Revenue Display immediately
        self.update_revenue_display()

    def update_revenue_display(self):
        """Update the pending revenue label"""
        if self.company_selector.currentIndex() == -1: return
        cid = self.company_selector.currentData()
        
        # Calculate pending
        pending = asset_service.calculate_pending_revenue(cid)
        
        self.pending_revenue_lbl.setText(f"Pending Revenue: {Formatter.format_currency(pending)}")
        self.collect_btn.setText(f"Collect {Formatter.format_currency(pending)}")
        
        if pending > 0:
            self.collect_btn.setEnabled(True)
            self.collect_btn.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white; font-weight: bold;")
        else:
            self.collect_btn.setEnabled(False)
            self.collect_btn.setStyleSheet("background-color: gray; color: white;")

    def deposit_funds(self):
        if self.company_selector.currentIndex() == -1: return
        cid = self.company_selector.currentData()
        amount = self.deposit_input.value()
        user = auth_service.get_current_user()
        res = company_service.deposit_to_wallet(cid, user.user_id, amount)
        QMessageBox.information(self, "Result", res['message'])
        self.refresh_data()
        
    def withdraw_funds(self):
        if self.company_selector.currentIndex() == -1: return
        cid = self.company_selector.currentData()
        amount = self.withdraw_input.value()
        user = auth_service.get_current_user()
        res = company_service.withdraw_from_wallet(cid, user.user_id, amount)
        QMessageBox.information(self, "Result", res['message'])
        self.refresh_data()
        
    def buy_asset(self):
        if self.assets_combo.currentIndex() == -1: return
        cid = self.company_selector.currentData()
        aid = self.assets_combo.currentData()
        user = auth_service.get_current_user()
        
        res = asset_service.buy_asset_for_company(user.user_id, cid, aid)
        QMessageBox.information(self, "Result", res['message'])
        self.refresh_data()
        
    def collect_revenue(self):
        if self.company_selector.currentIndex() == -1: return
        cid = self.company_selector.currentData()
        rev = asset_service.collect_revenue(cid)
        if rev > 0:
            QMessageBox.information(self, "Success", f"Collected {Formatter.format_currency(rev)} in revenue!")
        else:
            QMessageBox.information(self, "Info", "No revenue to collect.")
        self.refresh_data()

    def create_company(self):
        user = auth_service.get_current_user()
        res = company_service.create_company(
            user.user_id, self.new_name.text(), self.new_ticker.text(),
            self.new_price.value(), self.new_shares.value(), "New Company"
        )
        QMessageBox.information(self, "Result", res['message'])
        self.refresh_data()