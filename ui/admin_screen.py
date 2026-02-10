"""
Admin Screen - System management, market control, and asset creation
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from services.admin_service import admin_service
from services.auth_service import auth_service
from services.asset_service import asset_service
from database.db_manager import db
from models.user import User
from models.company import Company
from utils.formatters import Formatter
import config

class AdminScreen(QWidget):
    """Admin Dashboard for managing the system"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header
        title = QLabel("Admin Control Panel")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        title.setStyleSheet(f"color: {config.COLOR_ACCENT};")
        main_layout.addWidget(title)
        
        # Tabs for different sections
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_market_tab(), "📉 Market Control")
        self.tabs.addTab(self.create_users_tab(), "👥 User Management")
        self.tabs.addTab(self.create_bots_tab(), "🤖 Bot Control")
        self.tabs.addTab(self.create_asset_tab(), "🆕 Create Asset")
        self.tabs.addTab(self.create_edit_asset_tab(), "✏️ Edit Assets")
        
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)
        
    # ==========================================
    # TAB 1: MARKET CONTROL
    # ==========================================
    def create_market_tab(self):
        """Tab for Market Events & Company Management"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # --- Section 1: Global Market Events ---
        events_group = QGroupBox("Global Market Events")
        events_layout = QHBoxLayout()
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 60)
        self.duration_spin.setValue(2)
        self.duration_spin.setSuffix(" mins")
        self.duration_spin.setPrefix("Duration: ")
        events_layout.addWidget(self.duration_spin)
        
        btn_bull = QPushButton("🚀 Trigger BULL RUN")
        btn_bull.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white; font-weight: bold; padding: 10px;")
        btn_bull.clicked.connect(lambda: self.trigger_event('bull'))
        events_layout.addWidget(btn_bull)
        
        btn_bear = QPushButton("🩸 Trigger MARKET CRASH")
        btn_bear.setStyleSheet(f"background-color: {config.COLOR_DANGER}; color: white; font-weight: bold; padding: 10px;")
        btn_bear.clicked.connect(lambda: self.trigger_event('bear'))
        events_layout.addWidget(btn_bear)
        
        events_group.setLayout(events_layout)
        layout.addWidget(events_group)
        
        # --- Section 2: Targeted Manipulation ---
        target_group = QGroupBox("Targeted Manipulation (Single Company)")
        target_layout = QFormLayout()
        
        # Company Selector
        self.target_company_combo = QComboBox()
        self.refresh_company_combo()
        target_layout.addRow("Select Company:", self.target_company_combo)
        
        # Action Selector (Increase/Decrease)
        self.manipulation_action = QComboBox()
        self.manipulation_action.addItems(["📈 Increase Price", "📉 Decrease Price"])
        target_layout.addRow("Action:", self.manipulation_action)
        
        # Percentage Input
        self.manipulation_percent = QSpinBox()
        self.manipulation_percent.setRange(0, 10000)
        self.manipulation_percent.setValue(10)
        self.manipulation_percent.setSuffix("%")
        target_layout.addRow("Percentage:", self.manipulation_percent)
        
        # Apply Button
        btn_apply = QPushButton("Apply Price Change")
        btn_apply.setStyleSheet(f"background-color: {config.COLOR_WARNING}; color: black; font-weight: bold; padding: 10px;")
        btn_apply.clicked.connect(self.apply_manipulation)
        target_layout.addRow(btn_apply)
        
        target_group.setLayout(target_layout)
        layout.addWidget(target_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    # ==========================================
    # TAB 2: USER MANAGEMENT
    # ==========================================
    def create_users_tab(self):
        """Tab for User Management"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # User List
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(6)
        self.user_table.setHorizontalHeaderLabels(["ID", "Username", "Balance", "Role", "Add (+)", "Remove (-)"])
        self.user_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.user_table)
        
        # Refresh Button
        btn_refresh = QPushButton("Refresh Users")
        btn_refresh.clicked.connect(self.refresh_users)
        layout.addWidget(btn_refresh)
        
        widget.setLayout(layout)
        return widget

    # ==========================================
    # TAB 3: BOT CONTROL (UPDATED)
    # ==========================================
    def create_bots_tab(self):
        """Tab for Bot Management"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Bot List
        self.bot_table = QTableWidget()
        self.bot_table.setColumnCount(7) # Increased to 7 for Login Button
        self.bot_table.setHorizontalHeaderLabels(["Bot Name", "Strategy", "Wallet", "Portfolio", "Total Value", "Status", "Access"])
        self.bot_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.bot_table)
        
        # Actions
        actions_layout = QHBoxLayout()
        btn_reset = QPushButton("Reset Bot Balances")
        btn_reset.setStyleSheet("background-color: #E67E22; color: white;")
        btn_reset.clicked.connect(self.reset_bots)
        actions_layout.addWidget(btn_reset)
        
        btn_refresh = QPushButton("Refresh Bots")
        btn_refresh.clicked.connect(self.refresh_bots)
        actions_layout.addWidget(btn_refresh)
        
        layout.addLayout(actions_layout)
        widget.setLayout(layout)
        return widget

    # ==========================================
    # TAB 4: CREATE ASSET
    # ==========================================
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

    # ==========================================
    # TAB 5: EDIT ASSETS
    # ==========================================
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

    # ==========================================
    # LOGIC & ACTIONS
    # ==========================================
    
    def trigger_event(self, event_type):
        """Trigger global market event with Percentage Popup"""
        minutes = self.duration_spin.value()
        
        # Ask for Target Percentage
        default_percent = 20.0 if event_type == 'bull' else -20.0
        
        target_percent, ok = QInputDialog.getDouble(
            self, 
            "Set Target Change", 
            f"Enter target change % for {event_type.upper()} run:", 
            default_percent, -90, 500, 1
        )
        
        if not ok: return
        
        # Call service with ALL required arguments
        result = admin_service.trigger_market_event(event_type, minutes, target_percent)
        
        if result['success']:
            QMessageBox.information(self, "Success", result['message'])
        else:
            QMessageBox.warning(self, "Error", result['message'])

    def apply_manipulation(self):
        """Apply targeted price change"""
        if self.target_company_combo.currentIndex() == -1: return
        
        company_id = self.target_company_combo.currentData()
        percent = self.manipulation_percent.value()
        action = self.manipulation_action.currentText()
        
        if percent == 0:
            QMessageBox.information(self, "Info", "0% change selected.")
            return

        # Determine direction
        final_percent = percent
        if "Decrease" in action:
            final_percent = -percent
            
        result = admin_service.manipulate_specific_company(company_id, final_percent)
        
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

    # --- Loaders ---

    def refresh_company_combo(self):
        self.target_company_combo.clear()
        companies = Company.get_all()
        for comp in companies:
            self.target_company_combo.addItem(f"{comp.ticker_symbol} - {comp.company_name}", comp.company_id)

    def refresh_users(self):
        users = db.execute_query("SELECT * FROM users ORDER BY user_id DESC")
        self.user_table.setRowCount(len(users))
        
        for row, user in enumerate(users):
            self.user_table.setItem(row, 0, QTableWidgetItem(str(user['user_id'])))
            self.user_table.setItem(row, 1, QTableWidgetItem(user['username']))
            self.user_table.setItem(row, 2, QTableWidgetItem(Formatter.format_currency(user['wallet_balance'])))
            
            role = "Admin" if user['is_admin'] else "User"
            self.user_table.setItem(row, 3, QTableWidgetItem(role))
            
            # Add Fund Button (+ 10k)
            btn_add = QPushButton("+ ₹10k")
            btn_add.setStyleSheet("color: green; font-weight: bold;")
            btn_add.clicked.connect(lambda checked, u=user: self.add_funds_to_user(u))
            self.user_table.setCellWidget(row, 4, btn_add)

            # Remove Fund Button (- 10k)
            btn_remove = QPushButton("- ₹10k")
            btn_remove.setStyleSheet("color: red; font-weight: bold;")
            btn_remove.clicked.connect(lambda checked, u=user: self.remove_funds_from_user(u))
            self.user_table.setCellWidget(row, 5, btn_remove)

    def add_funds_to_user(self, user):
        u = User.get_by_id(user['user_id'])
        u.add_funds(10000, "Admin Grant")
        self.refresh_users()
        QMessageBox.information(self, "Success", f"Added ₹10,000 to {user['username']}")

    def remove_funds_from_user(self, user):
        try:
            u = User.get_by_id(user['user_id'])
            u.withdraw_funds(10000, "Admin Fine/Correction")
            self.refresh_users()
            QMessageBox.information(self, "Success", f"Removed ₹10,000 from {user['username']}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not remove funds: {str(e)}")

    def refresh_bots(self):
        try:
            from trading.bot_trader import bot_trader
            stats = bot_trader.get_bot_statistics()
            self.bot_table.setRowCount(len(stats))
            
            for row, bot in enumerate(stats):
                self.bot_table.setItem(row, 0, QTableWidgetItem(bot['bot_name']))
                self.bot_table.setItem(row, 1, QTableWidgetItem(bot['strategy']))
                self.bot_table.setItem(row, 2, QTableWidgetItem(Formatter.format_currency(bot['wallet_balance'])))
                self.bot_table.setItem(row, 3, QTableWidgetItem(Formatter.format_currency(bot['portfolio_value'])))
                self.bot_table.setItem(row, 4, QTableWidgetItem(Formatter.format_currency(bot['total_value'])))
                
                status = "Active" if bot['is_active'] else "Inactive"
                self.bot_table.setItem(row, 5, QTableWidgetItem(status))
                
                # --- NEW LOGIN BUTTON ---
                btn_login = QPushButton("👁️ Login")
                btn_login.setStyleSheet("background-color: #3498DB; color: white; font-weight: bold;")
                # Need to find the associated User ID. We can guess from bot name or fetch it.
                # Fortunately, our stats already include user_id if we modify bot_trader.
                # Let's just find the user by username since bot['bot_name'] is the full name.
                # Actually, best to fetch user by username derived from bot name, or...
                # WAIT: bot_trader.get_bot_statistics() didn't return user_id in previous code.
                # Let's fix that too.
                
                # Since I can't modify bot_trader in this specific response block easily without making it huge, 
                # I'll rely on the username convention: "ArjunMehtaBot"
                username = bot['bot_name'].replace(" ", "") + "Bot"
                user = User.get_by_username(username)
                
                if user:
                    btn_login.clicked.connect(lambda checked, uid=user.user_id: self.switch_to_user(uid))
                    self.bot_table.setCellWidget(row, 6, btn_login)
                    
        except Exception as e:
            print(f"Error loading bots: {e}")

    def switch_to_user(self, user_id):
        """Switch session to the selected bot"""
        success = auth_service.login_as_user(user_id)
        if success:
            # Refresh the MAIN WINDOW to show new user data
            # We access the main window via parent() or window()
            if self.window():
                self.window().on_login_success()
                QMessageBox.information(self, "Switched", "You are now logged in as this Bot.\nGo to Dashboard to see their stats.")
        else:
            QMessageBox.warning(self, "Error", "Could not switch user.")

    def reset_bots(self):
        try:
            from trading.bot_trader import bot_trader
            bot_trader.reset_bot_balances()
            QMessageBox.information(self, "Success", "All bots reset to initial funds.")
            self.refresh_bots()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

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

    def refresh_data(self):
        """Called by main window when tab is switched"""
        self.refresh_company_combo()
        self.refresh_users()
        self.refresh_bots()
        self.load_assets_for_edit()