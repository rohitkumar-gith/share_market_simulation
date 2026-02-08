"""
Main Window - Container for all screens with navigation
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QStackedWidget, QMessageBox,
                             QFrame, QStatusBar)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from services.auth_service import auth_service
from trading.market_engine import market_engine
from trading.bot_trader import bot_trader
from trading.order_matcher import order_matcher
from utils.formatters import Formatter
import config

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.current_user = None
        self.init_ui()
        self.setup_timers()
    
    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle(config.APP_NAME)
        self.showMaximized()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)
        
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        self.sidebar = self.create_sidebar()
        content_layout.addWidget(self.sidebar)
        
        self.content_stack = QStackedWidget()
        content_layout.addWidget(self.content_stack)
        
        main_layout.addLayout(content_layout)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status_bar()
        
        central_widget.setLayout(main_layout)
        self.apply_stylesheet()
    
    def create_top_bar(self):
        top_bar = QFrame()
        top_bar.setFixedHeight(60)
        top_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {config.COLOR_PRIMARY};
                border-bottom: 2px solid {config.COLOR_SECONDARY};
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)
        
        title = QLabel(config.APP_NAME)
        title.setFont(QFont('Arial', 18, QFont.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        self.user_info_label = QLabel()
        self.user_info_label.setFont(QFont('Arial', 11))
        self.user_info_label.setStyleSheet("color: white;")
        layout.addWidget(self.user_info_label)
        
        self.balance_label = QLabel()
        self.balance_label.setFont(QFont('Arial', 12, QFont.Bold))
        self.balance_label.setStyleSheet(f"color: {config.COLOR_SUCCESS}; margin-left: 20px;")
        layout.addWidget(self.balance_label)
        
        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.setStyleSheet("background-color: #34495E; color: white; border: none; padding: 8px 15px; border-radius: 4px; margin-left: 10px;")
        refresh_btn.clicked.connect(self.refresh_all_data)
        layout.addWidget(refresh_btn)
        
        logout_btn = QPushButton("Logout")
        logout_btn.setStyleSheet(f"background-color: {config.COLOR_DANGER}; color: white; border: none; padding: 8px 15px; border-radius: 4px; margin-left: 10px;")
        logout_btn.clicked.connect(self.handle_logout)
        layout.addWidget(logout_btn)
        
        top_bar.setLayout(layout)
        return top_bar
    
    def create_sidebar(self):
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setFixedWidth(200)
        self.sidebar_frame.setStyleSheet(f"QFrame {{ background-color: {config.COLOR_PRIMARY}; border-right: 1px solid {config.COLOR_SECONDARY}; }}")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(5)
        
        self.nav_buttons = {}
        
        # Base Nav Items
        self.nav_items = [
            ("Dashboard", "dashboard"),
            ("Market", "market"),
            ("Portfolio", "portfolio"),
            ("My Orders", "orders"),
            ("Companies", "companies"),
            ("Chat", "chat"), # <--- NEW
            ("Wallet", "wallet"),
            ("Loans", "loans"),
        ]
        
        for text, key in self.nav_items:
            self.create_nav_btn(layout, text, key)
            
        # Admin Button (Hidden by default)
        self.admin_btn = QPushButton("ADMIN PANEL")
        self.admin_btn.setCheckable(True)
        self.admin_btn.setStyleSheet("background-color: #C0392B; color: white; text-align: left; padding: 15px 20px; border: none; font-weight: bold;")
        self.admin_btn.clicked.connect(lambda checked: self.switch_screen("admin"))
        self.admin_btn.hide()
        layout.addWidget(self.admin_btn)
        self.nav_buttons["admin"] = self.admin_btn
        
        layout.addStretch()
        self.sidebar_frame.setLayout(layout)
        return self.sidebar_frame
        
    def create_nav_btn(self, layout, text, key):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                text-align: left;
                padding: 15px 20px;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #34495E; }
            QPushButton:checked { background-color: #3498DB; border-left: 4px solid #2ECC71; }
        """)
        btn.clicked.connect(lambda checked, k=key: self.switch_screen(k))
        layout.addWidget(btn)
        self.nav_buttons[key] = btn
    
    def setup_timers(self):
        self.market_timer = QTimer()
        self.market_timer.timeout.connect(self.update_market_prices)
        self.market_timer.start(config.BOT_TRADING_INTERVAL * 1000)
        
        self.bot_timer = QTimer()
        self.bot_timer.timeout.connect(self.execute_bot_trades)
        self.bot_timer.start(config.BOT_TRADING_INTERVAL * 1000)
        
        self.order_timer = QTimer()
        self.order_timer.timeout.connect(self.match_orders)
        self.order_timer.start(5000)
        
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.refresh_ui_data)
        self.ui_timer.start(2000)
    
    def update_market_prices(self):
        try:
            market_engine.update_all_prices()
        except: pass
    
    def execute_bot_trades(self):
        try:
            bot_trader.execute_bot_trades()
        except: pass
    
    def match_orders(self):
        try:
            order_matcher.match_all_orders()
        except: pass
    
    def refresh_ui_data(self):
        if self.current_user:
            self.update_user_info()
            current_widget = self.content_stack.currentWidget()
            if hasattr(current_widget, 'refresh_data') and self.isActiveWindow():
                current_widget.refresh_data()
    
    def update_user_info(self):
        if auth_service.is_authenticated():
            user = auth_service.get_current_user()
            self.current_user = user
            self.user_info_label.setText(f"👤 {user.full_name}")
            self.balance_label.setText(f"💰 {Formatter.format_currency(user.wallet_balance)}")
            
            # Show/Hide Admin Button
            if user.is_admin:
                self.admin_btn.show()
            else:
                self.admin_btn.hide()
    
    def update_status_bar(self):
        self.status_bar.showMessage("Ready")
    
    def load_screens(self):
        from ui.user_dashboard import UserDashboard
        from ui.market_screen import MarketScreen
        from ui.portfolio_screen import PortfolioScreen
        from ui.orders_screen import OrdersScreen
        from ui.company_dashboard import CompanyDashboard
        from ui.wallet_screen import WalletScreen
        from ui.loan_screen import LoanScreen
        from ui.chat_screen import ChatScreen # <--- NEW
        from ui.admin_screen import AdminScreen # <--- NEW
        
        # Clear existing
        while self.content_stack.count() > 0:
            self.content_stack.removeWidget(self.content_stack.widget(0))
            
        self.screens = {
            'dashboard': UserDashboard(self),
            'market': MarketScreen(self),
            'portfolio': PortfolioScreen(self),
            'orders': OrdersScreen(self),
            'companies': CompanyDashboard(self),
            'chat': ChatScreen(self),
            'wallet': WalletScreen(self),
            'loans': LoanScreen(self),
            'admin': AdminScreen(self)
        }
        
        # Add to stack in order
        for key in ['dashboard', 'market', 'portfolio', 'orders', 'companies', 'chat', 'wallet', 'loans', 'admin']:
            self.content_stack.addWidget(self.screens[key])
            
        self.switch_screen('dashboard')
    
    def switch_screen(self, screen_key):
        screen_indices = {
            'dashboard': 0, 'market': 1, 'portfolio': 2, 'orders': 3,
            'companies': 4, 'chat': 5, 'wallet': 6, 'loans': 7, 'admin': 8
        }
        
        if screen_key in screen_indices:
            idx = screen_indices[screen_key]
            
            # Update Nav Buttons
            for key, btn in self.nav_buttons.items():
                btn.setChecked(key == screen_key)
                
            self.content_stack.setCurrentIndex(idx)
            current_widget = self.content_stack.currentWidget()
            if hasattr(current_widget, 'refresh_data'):
                current_widget.refresh_data()
    
    def refresh_all_data(self):
        self.update_user_info()
        current_widget = self.content_stack.currentWidget()
        if hasattr(current_widget, 'refresh_data'):
            current_widget.refresh_data()
        self.status_bar.showMessage("Data refreshed", 2000)
    
    def handle_logout(self):
        reply = QMessageBox.question(self, 'Confirm Logout', 'Are you sure?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            auth_service.logout()
            self.close()
            from ui.auth_screen import AuthScreen
            self.auth_screen = AuthScreen()
            self.auth_screen.login_successful.connect(self.on_login_success)
            self.auth_screen.show()
    
    def on_login_success(self):
        self.update_user_info()
        self.load_screens()
        self.showMaximized()
    
    def apply_stylesheet(self):
        self.setStyleSheet(f"QMainWindow {{ background-color: {config.COLOR_BACKGROUND}; }} QPushButton {{ font-size: 13px; }} QLabel {{ color: {config.COLOR_TEXT}; }}")
    
    def closeEvent(self, event):
        try:
            self.market_timer.stop()
            self.bot_timer.stop()
            self.order_timer.stop()
            self.ui_timer.stop()
        except: pass
        event.accept()