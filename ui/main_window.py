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
        
        # --- FIX: Maximize window to fit any screen ---
        self.showMaximized()
        # ----------------------------------------------
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Top bar
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)
        
        # Content area
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = self.create_sidebar()
        content_layout.addWidget(self.sidebar)
        
        # Main content stack
        self.content_stack = QStackedWidget()
        content_layout.addWidget(self.content_stack)
        
        main_layout.addLayout(content_layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status_bar()
        
        central_widget.setLayout(main_layout)
        
        # Apply stylesheet
        self.apply_stylesheet()
    
    def create_top_bar(self):
        """Create top navigation bar"""
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
        
        # App title
        title = QLabel(config.APP_NAME)
        title.setFont(QFont('Arial', 18, QFont.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # User info
        self.user_info_label = QLabel()
        self.user_info_label.setFont(QFont('Arial', 11))
        self.user_info_label.setStyleSheet("color: white;")
        layout.addWidget(self.user_info_label)
        
        # Wallet balance
        self.balance_label = QLabel()
        self.balance_label.setFont(QFont('Arial', 12, QFont.Bold))
        self.balance_label.setStyleSheet(f"color: {config.COLOR_SUCCESS}; margin-left: 20px;")
        layout.addWidget(self.balance_label)
        
        # Refresh button
        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495E;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                margin-left: 10px;
            }
            QPushButton:hover {
                background-color: #415B76;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_all_data)
        layout.addWidget(refresh_btn)
        
        # Logout button
        logout_btn = QPushButton("Logout")
        logout_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {config.COLOR_DANGER};
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                margin-left: 10px;
            }}
            QPushButton:hover {{
                background-color: #C0392B;
            }}
        """)
        logout_btn.clicked.connect(self.handle_logout)
        layout.addWidget(logout_btn)
        
        top_bar.setLayout(layout)
        return top_bar
    
    def create_sidebar(self):
        """Create sidebar navigation"""
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {config.COLOR_PRIMARY};
                border-right: 1px solid {config.COLOR_SECONDARY};
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(5)
        
        # Navigation buttons
        self.nav_buttons = {}
        
        nav_items = [
            ("Dashboard", "dashboard"),
            ("Market", "market"),
            ("Portfolio", "portfolio"),
            ("My Companies", "companies"),
            ("Wallet", "wallet"),
            ("Loans", "loans"),
        ]
        
        for text, key in nav_items:
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
                QPushButton:hover {
                    background-color: #34495E;
                }
                QPushButton:checked {
                    background-color: #3498DB;
                    border-left: 4px solid #2ECC71;
                }
            """)
            btn.clicked.connect(lambda checked, k=key: self.switch_screen(k))
            layout.addWidget(btn)
            self.nav_buttons[key] = btn
        
        layout.addStretch()
        
        # Market status
        status_label = QLabel("Market Status")
        status_label.setStyleSheet("color: white; padding: 10px 20px; font-weight: bold;")
        layout.addWidget(status_label)
        
        self.market_status_label = QLabel("● Active")
        self.market_status_label.setStyleSheet("color: #2ECC71; padding: 5px 20px;")
        layout.addWidget(self.market_status_label)
        
        sidebar.setLayout(layout)
        return sidebar
    
    def setup_timers(self):
        """Setup background timers for market updates"""
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
        """Update market prices"""
        try:
            result = market_engine.update_all_prices()
            self.status_bar.showMessage(f"Market updated: {result['updated_count']} companies", 3000)
        except Exception as e:
            print(f"Market update error: {e}")
    
    def execute_bot_trades(self):
        """Execute bot trades"""
        try:
            result = bot_trader.execute_bot_trades()
            if result['trades_executed'] > 0:
                self.status_bar.showMessage(f"Bot trades: {result['trades_executed']} executed", 2000)
        except Exception as e:
            print(f"Bot trading error: {e}")
    
    def match_orders(self):
        """Match pending orders"""
        try:
            result = order_matcher.match_all_orders()
            if result['total_matches'] > 0:
                self.status_bar.showMessage(f"Orders matched: {result['total_matches']}", 2000)
        except Exception as e:
            print(f"Order matching error: {e}")
    
    def refresh_ui_data(self):
        """Refresh UI data"""
        if self.current_user:
            self.update_user_info()
            current_widget = self.content_stack.currentWidget()
            if hasattr(current_widget, 'refresh_data'):
                current_widget.refresh_data()
    
    def update_user_info(self):
        """Update user information display"""
        if auth_service.is_authenticated():
            user = auth_service.get_current_user()
            self.current_user = user
            self.user_info_label.setText(f"👤 {user.full_name}")
            self.balance_label.setText(f"💰 {Formatter.format_currency(user.wallet_balance)}")
    
    def update_status_bar(self):
        """Update status bar"""
        self.status_bar.showMessage("Ready")
    
    def load_screens(self):
        """Load all application screens"""
        from ui.user_dashboard import UserDashboard
        from ui.market_screen import MarketScreen
        from ui.portfolio_screen import PortfolioScreen
        from ui.company_dashboard import CompanyDashboard
        from ui.wallet_screen import WalletScreen
        from ui.loan_screen import LoanScreen
        
        self.dashboard_screen = UserDashboard(self)
        self.market_screen = MarketScreen(self)
        self.portfolio_screen = PortfolioScreen(self)
        self.company_screen = CompanyDashboard(self)
        self.wallet_screen = WalletScreen(self)
        self.loan_screen = LoanScreen(self)
        
        self.content_stack.addWidget(self.dashboard_screen)  # 0
        self.content_stack.addWidget(self.market_screen)      # 1
        self.content_stack.addWidget(self.portfolio_screen)   # 2
        self.content_stack.addWidget(self.company_screen)     # 3
        self.content_stack.addWidget(self.wallet_screen)      # 4
        self.content_stack.addWidget(self.loan_screen)        # 5
        
        self.switch_screen('dashboard')
    
    def switch_screen(self, screen_key):
        """Switch to different screen"""
        screen_map = {
            'dashboard': 0, 'market': 1, 'portfolio': 2,
            'companies': 3, 'wallet': 4, 'loans': 5
        }
        if screen_key in screen_map:
            for key, btn in self.nav_buttons.items():
                btn.setChecked(key == screen_key)
            self.content_stack.setCurrentIndex(screen_map[screen_key])
            current_widget = self.content_stack.currentWidget()
            if hasattr(current_widget, 'refresh_data'):
                current_widget.refresh_data()
    
    def refresh_all_data(self):
        """Refresh all data"""
        self.update_user_info()
        current_widget = self.content_stack.currentWidget()
        if hasattr(current_widget, 'refresh_data'):
            current_widget.refresh_data()
        self.status_bar.showMessage("Data refreshed", 2000)
    
    def handle_logout(self):
        """Handle logout"""
        reply = QMessageBox.question(self, 'Confirm Logout', 'Are you sure you want to logout?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            auth_service.logout()
            self.close()
            from ui.auth_screen import AuthScreen
            self.auth_screen = AuthScreen()
            self.auth_screen.login_successful.connect(self.on_login_success)
            self.auth_screen.show()
    
    def on_login_success(self):
        """Handle successful login"""
        self.update_user_info()
        self.load_screens()
        # --- FIX: Ensure maximized on login ---
        self.showMaximized() 
        # --------------------------------------
    
    def apply_stylesheet(self):
        """Apply global stylesheet"""
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {config.COLOR_BACKGROUND}; }}
            QPushButton {{ font-size: 13px; }}
            QLabel {{ color: {config.COLOR_TEXT}; }}
        """)
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.market_timer.stop()
        self.bot_timer.stop()
        self.order_timer.stop()
        self.ui_timer.stop()
        event.accept()