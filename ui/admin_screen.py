"""
Admin Screen - Market Control and Asset Creation
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from services.auth_service import auth_service
from services.admin_service import admin_service
from services.company_service import company_service
from services.asset_service import asset_service  # <--- NEW IMPORT
import config

class AdminScreen(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Admin Control Panel")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        title.setStyleSheet(f"color: {config.COLOR_DANGER};")
        layout.addWidget(title)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_market_tab(), "Market Control")
        self.tabs.addTab(self.create_asset_tab(), "Create Asset")
        self.tabs.addTab(self.create_edit_asset_tab(), "Edit Assets") # <--- NEW TAB
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def refresh_data(self):
        """Reload lists"""
        self.load_companies()
        self.load_assets_for_edit()
        
    def create_market_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(15)
        
        # --- Section 1: Global Events ---
        lbl_global = QLabel("Global Market Events")
        lbl_global.setFont(QFont('Arial', 14, QFont.Bold))
        layout.addWidget(lbl_global)
        
        # Duration Selector
        dur_layout = QHBoxLayout()
        dur_layout.addWidget(QLabel("Event Duration (Minutes):"))
        self.event_duration = QSpinBox()
        self.event_duration.setRange(1, 60)
        self.event_duration.setValue(2) # Default 2 mins
        dur_layout.addWidget(self.event_duration)
        dur_layout.addStretch()
        layout.addLayout(dur_layout)
        
        btn_layout = QHBoxLayout()
        
        btn_bull = QPushButton("🚀 START BULL RUN")
        btn_bull.setToolTip("Starts a sustained upward trend")
        btn_bull.setStyleSheet("background-color: #27AE60; color: white; padding: 15px; font-weight: bold; font-size: 14px;")
        btn_bull.clicked.connect(lambda: self.trigger_event('bull'))
        btn_layout.addWidget(btn_bull)
        
        btn_bear = QPushButton("📉 START CRASH")
        btn_bear.setToolTip("Starts a sustained downward trend")
        btn_bear.setStyleSheet("background-color: #C0392B; color: white; padding: 15px; font-weight: bold; font-size: 14px;")
        btn_bear.clicked.connect(lambda: self.trigger_event('bear'))
        btn_layout.addWidget(btn_bear)
        
        layout.addLayout(btn_layout)
        
        # --- Section 2: Targeted Manipulation ---
        layout.addSpacing(20)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        lbl_target = QLabel("Targeted Manipulation (Single Company)")
        lbl_target.setFont(QFont('Arial', 14, QFont.Bold))
        layout.addWidget(lbl_target)
        
        form_layout = QFormLayout()
        
        self.target_company_combo = QComboBox()
        form_layout.addRow("Select Company:", self.target_company_combo)
        
        self.manipulation_action = QComboBox()
        self.manipulation_action.addItems(["📈 Increase Price", "📉 Decrease Price"])
        form_layout.addRow("Action:", self.manipulation_action)
        
        self.manipulation_percent = QSpinBox()
        self.manipulation_percent.setRange(0, 10000)
        self.manipulation_percent.setValue(10)
        self.manipulation_percent.setSuffix("%")
        form_layout.addRow("Percentage:", self.manipulation_percent)
        
        layout.addLayout(form_layout)
        
        btn_apply = QPushButton("Apply Price Change")
        btn_apply.setStyleSheet(f"background-color: {config.COLOR_WARNING}; color: black; font-weight: bold; padding: 10px;")
        btn_apply.clicked.connect(self.apply_manipulation)
        layout.addWidget(btn_apply)
        
        widget.setLayout(layout)
        self.load_companies()
        return widget
        
    def create_asset_tab(self):
        widget = QWidget()
        layout = QFormLayout()
        layout.setSpacing(15)
        
        title = QLabel("Create New Master Asset")
        title.setFont(QFont('Arial', 12, QFont.Bold))
        layout.addRow(title)
        
        self.asset_name = QLineEdit()
        layout.addRow("Asset Name:", self.asset_name)
        
        self.asset_type = QComboBox()
        self.asset_type.addItems(["CAR", "REAL_ESTATE"])
        layout.addRow("Type:", self.asset_type)
        
        self.asset_price = QDoubleSpinBox()
        self.asset_price.setRange(0, 100000000)
        self.asset_price.setValue(50000)
        layout.addRow("Base Price (₹):", self.asset_price)
        
        self.asset_revenue = QDoubleSpinBox()
        self.asset_revenue.setRange(0, 100000)
        self.asset_revenue.setValue(500)
        layout.addRow("Revenue/Min (₹):", self.asset_revenue)
        
        self.asset_supply = QSpinBox()
        self.asset_supply.setRange(-1, 10000)
        self.asset_supply.setValue(100)
        layout.addRow("Total Supply:", self.asset_supply)
        
        create_btn = QPushButton("Create Asset")
        create_btn.setStyleSheet(f"background-color: {config.COLOR_PRIMARY}; color: white;")
        create_btn.clicked.connect(self.create_asset)
        layout.addRow(create_btn)
        
        widget.setLayout(layout)
        return widget

    def create_edit_asset_tab(self):
        """New Tab for Editing Assets"""
        widget = QWidget()
        layout = QFormLayout()
        layout.setSpacing(15)
        
        title = QLabel("Edit Existing Asset")
        title.setFont(QFont('Arial', 12, QFont.Bold))
        layout.addRow(title)
        
        # Selector
        self.edit_asset_selector = QComboBox()
        self.edit_asset_selector.currentIndexChanged.connect(self.load_asset_details)
        layout.addRow("Select Asset:", self.edit_asset_selector)
        
        # Fields
        self.edit_name = QLineEdit()
        layout.addRow("Asset Name:", self.edit_name)
        
        self.edit_type = QComboBox()
        self.edit_type.addItems(["CAR", "REAL_ESTATE"])
        layout.addRow("Type:", self.edit_type)
        
        self.edit_price = QDoubleSpinBox()
        self.edit_price.setRange(0, 100000000)
        layout.addRow("Base Price (₹):", self.edit_price)
        
        self.edit_revenue = QDoubleSpinBox()
        self.edit_revenue.setRange(0, 100000)
        layout.addRow("Revenue/Min (₹):", self.edit_revenue)
        
        self.edit_supply = QSpinBox()
        self.edit_supply.setRange(-1, 10000)
        layout.addRow("Total Supply:", self.edit_supply)
        
        update_btn = QPushButton("Update Asset")
        update_btn.setStyleSheet(f"background-color: {config.COLOR_WARNING}; color: black;")
        update_btn.clicked.connect(self.update_asset)
        layout.addRow(update_btn)
        
        widget.setLayout(layout)
        return widget

    def load_companies(self):
        self.target_company_combo.clear()
        companies = company_service.get_all_companies()
        for c in companies:
            c_name = c['company_name'] if isinstance(c, dict) else c.company_name
            c_ticker = c['ticker_symbol'] if isinstance(c, dict) else c.ticker_symbol
            c_id = c['company_id'] if isinstance(c, dict) else c.company_id
            self.target_company_combo.addItem(f"{c_name} ({c_ticker})", c_id)

    def load_assets_for_edit(self):
        """Populate the Edit Asset dropdown"""
        self.edit_asset_selector.blockSignals(True)
        self.edit_asset_selector.clear()
        assets = asset_service.get_all_assets()
        for a in assets:
            self.edit_asset_selector.addItem(f"{a['name']} ({a['asset_type']})", a['asset_id'])
        self.edit_asset_selector.blockSignals(False)
        
        # Load first item details if available
        if self.edit_asset_selector.count() > 0:
            self.load_asset_details()

    def load_asset_details(self):
        """Fill inputs with selected asset data"""
        if self.edit_asset_selector.currentIndex() == -1: return
        
        asset_id = self.edit_asset_selector.currentData()
        assets = asset_service.get_all_assets()
        target_asset = next((a for a in assets if a['asset_id'] == asset_id), None)
        
        if target_asset:
            self.edit_name.setText(target_asset['name'])
            
            idx = self.edit_type.findText(target_asset['asset_type'])
            if idx >= 0: self.edit_type.setCurrentIndex(idx)
            
            self.edit_price.setValue(target_asset['base_price'])
            self.edit_revenue.setValue(target_asset['revenue_rate'])
            self.edit_supply.setValue(target_asset['total_supply'])

    def trigger_event(self, event_type):
        minutes = self.event_duration.value()
        result = admin_service.trigger_market_event(event_type, minutes)
        QMessageBox.information(self, "Market Event", result['message'])
        
    def apply_manipulation(self):
        if self.target_company_combo.currentIndex() == -1: return
        
        cid = self.target_company_combo.currentData()
        percent = self.manipulation_percent.value()
        action = self.manipulation_action.currentText()
        
        if percent == 0:
            QMessageBox.information(self, "Info", "0% change selected.")
            return

        final_percent = percent
        if "Decrease" in action:
            final_percent = -percent
            
        result = admin_service.manipulate_specific_company(cid, final_percent)
        if result['success']:
            QMessageBox.information(self, "Success", result['message'])
        else:
            QMessageBox.warning(self, "Error", result['message'])
        
    def create_asset(self):
        name = self.asset_name.text()
        if not name: return
        
        user = auth_service.get_current_user()
        result = admin_service.create_master_asset(
            user.user_id, name, self.asset_type.currentText(),
            self.asset_price.value(), self.asset_revenue.value(), self.asset_supply.value()
        )
        
        if result['success']:
            QMessageBox.information(self, "Success", result['message'])
            self.asset_name.clear()
            self.load_assets_for_edit() # Refresh edit list
        else:
            QMessageBox.warning(self, "Error", result['message'])

    def update_asset(self):
        if self.edit_asset_selector.currentIndex() == -1: return
        
        asset_id = self.edit_asset_selector.currentData()
        name = self.edit_name.text()
        
        if not name: return
        
        user = auth_service.get_current_user()
        result = admin_service.edit_master_asset(
            user.user_id, asset_id, name, self.edit_type.currentText(),
            self.edit_price.value(), self.edit_revenue.value(), self.edit_supply.value()
        )
        
        if result['success']:
            QMessageBox.information(self, "Success", result['message'])
            self.load_assets_for_edit() # Refresh list
        else:
            QMessageBox.warning(self, "Error", result['message'])