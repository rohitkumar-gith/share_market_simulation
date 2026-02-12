"""
Main Window - Container for all screens with navigation
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QStackedWidget, QMessageBox,
                             QFrame, QStatusBar)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from services.auth_service import auth_service
from trading.market_engine import market_engine
from trading.bot_trader import bot_trader
from trading.order_matcher import order_matcher
from utils.formatters import Formatter
import config
import time

# --- NEW: Background Worker for Bots ---
class BotWorker(QThread):
    """Runs trading bots in a separate thread to prevent UI freezing"""
    trades_executed = pyqtSignal(int)  # Signal to update UI with trade count
    
    def __init__(self):
        super().__init__()
        self.is_running = True

    def run(self):
        """Continuous trading loop"""
        while self.is_running:
            try:
                # Run one cycle of bot trades
                result = bot_trader.execute_bot_trades()
                count = result.get('trades_executed', 0)
                
                # Emit signal if trades happened
                if count > 0:
                    self.trades_executed.emit(count)
                
                # Wait before next cycle (Configuration defined interval)
                # We break the sleep into small chunks to allow fast stopping
                for _ in range(config.BOT_TRADING_INTERVAL): 
                    if not self.is_running: break
                    time.sleep(1) 
                    
            except Exception as e:
                print(f"Bot Worker Error: {e}")
                time.sleep(5) # specific error backoff

    def stop(self):
        self.is_running = False
        self.wait()

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.current_user = None
        self.bot_thread = None # Initialize variable
        self.init_ui()
        self.setup_timers()
    
    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle(config.APP_NAME)
        self.resize(1400, 900)
        
        # Central Container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main Layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Top Bar
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)
        
        # 2. Content Area
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        self.sidebar = self.create_sidebar()
        content_layout.addWidget(self.sidebar)
        
        self.content_stack = QStackedWidget()
        content_layout.addWidget(self.content_stack)
        
        main_layout.addLayout(content_layout)
        
        # 3. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status_bar()
        
        central_widget.setLayout(main_layout)
        
        # APPLY MODERN THEME
        self.apply_modern_theme()
    
    def create_top_bar(self):
        top_bar = QFrame()
        top_bar.setFixedHeight(70)
        top_bar.setObjectName("TopBar")
        
        layout = QHBoxLayout()
        layout.setContentsMargins(25, 10, 25, 10)
        
        title = QLabel(f"📈 {config.APP_NAME}")
        title.setObjectName("AppTitle")
        layout.addWidget(title)
        
        layout.addStretch()
        
        user_badge = QFrame()
        user_badge.setObjectName("UserBadge")
        badge_layout = QHBoxLayout(user_badge)
        badge_layout.setContentsMargins(15, 5, 15, 5)
        
        self.user_info_label = QLabel()
        self.user_info_label.setStyleSheet(f"color: {config.COLOR_TEXT}; font-weight: bold;")
        badge_layout.addWidget(self.user_info_label)
        
        self.balance_label = QLabel()
        self.balance_label.setStyleSheet(f"color: {config.COLOR_SUCCESS}; font-weight: bold; font-size: 14px; margin-left: 10px;")
        badge_layout.addWidget(self.balance_label)
        
        layout.addWidget(user_badge)
        
        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.setObjectName("ActionBtn")
        refresh_btn.clicked.connect(self.refresh_all_data)
        layout.addWidget(refresh_btn)
        
        logout_btn = QPushButton("Logout")
        logout_btn.setObjectName("LogoutBtn")
        logout_btn.clicked.connect(self.handle_logout)
        layout.addWidget(logout_btn)
        
        top_bar.setLayout(layout)
        return top_bar
    
    def create_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setObjectName("Sidebar")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(8)
        
        self.nav_buttons = {}
        
        self.nav_items = [
            ("📊  Dashboard", "dashboard"),
            ("📈  Market", "market"),
            ("💼  Portfolio", "portfolio"),
            ("📝  My Orders", "orders"),
            ("🏢  Companies", "companies"),
            ("💬  Chat Room", "chat"),
            ("💳  Wallet", "wallet"),
            ("🏦  Loans", "loans"),
        ]
        
        layout.addWidget(QLabel("NAVIGATION"))
        
        for text, key in self.nav_items:
            self.create_nav_btn(layout, text, key)
            
        layout.addStretch()
        
        self.admin_btn = QPushButton("🔒 ADMIN PANEL")
        self.admin_btn.setCheckable(True)
        self.admin_btn.setObjectName("AdminBtn")
        self.admin_btn.clicked.connect(lambda checked: self.switch_screen("admin"))
        self.admin_btn.hide()
        layout.addWidget(self.admin_btn)
        self.nav_buttons["admin"] = self.admin_btn
        
        sidebar.setLayout(layout)
        return sidebar
        
    def create_nav_btn(self, layout, text, key):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setObjectName("NavBtn")
        btn.clicked.connect(lambda checked, k=key: self.switch_screen(k))
        layout.addWidget(btn)
        self.nav_buttons[key] = btn

    def apply_modern_theme(self):
        """Apply a comprehensive QSS stylesheet for a modern dark look"""
        self.setStyleSheet(f"""
            /* GLOBAL */
            QMainWindow {{ background-color: {config.COLOR_BACKGROUND}; }}
            QWidget {{ color: {config.COLOR_TEXT}; font-family: 'Segoe UI', 'Roboto', sans-serif; font-size: 14px; }}
            
            /* DIALOGS */
            QDialog, QMessageBox, QInputDialog {{ background-color: #2D2D2D; color: white; }}
            QMessageBox QLabel, QInputDialog QLabel {{ color: white; }}
            
            /* TOP BAR */
            QFrame#TopBar {{ background-color: {config.COLOR_SURFACE}; border-bottom: 1px solid #333; }}
            QLabel#AppTitle {{ font-size: 22px; font-weight: bold; color: {config.COLOR_ACCENT}; }}
            QFrame#UserBadge {{ background-color: {config.COLOR_BACKGROUND}; border-radius: 15px; border: 1px solid #333; }}
            
            /* SIDEBAR */
            QFrame#Sidebar {{ background-color: {config.COLOR_SURFACE}; border-right: 1px solid #333; }}
            QFrame#Sidebar QLabel {{ color: #888; font-size: 11px; font-weight: bold; padding-left: 10px; }}
            
            /* BUTTONS */
            QPushButton#NavBtn {{
                background-color: transparent; text-align: left; padding: 12px 20px;
                border-radius: 8px; color: #888; border: none; font-weight: 500;
            }}
            QPushButton#NavBtn:hover {{ background-color: rgba(255,255,255,0.05); color: white; }}
            QPushButton#NavBtn:checked {{ background-color: {config.COLOR_ACCENT}; color: white; font-weight: bold; }}
            
            QPushButton {{
                background-color: {config.COLOR_ACCENT}; color: white; border: none;
                border-radius: 6px; padding: 6px 12px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #2980B9; }}
            
            QPushButton#LogoutBtn {{ background-color: transparent; border: 1px solid {config.COLOR_DANGER}; color: {config.COLOR_DANGER}; }}
            QPushButton#LogoutBtn:hover {{ background-color: {config.COLOR_DANGER}; color: white; }}
            
            /* TABLES */
            QTableWidget {{
                background-color: {config.COLOR_SURFACE};
                alternate-background-color: #262626; 
                gridline-color: #333;
                border: none;
                border-radius: 8px;
                outline: none;
            }}
            QHeaderView {{ background-color: {config.COLOR_BACKGROUND}; border: none; }}
            QHeaderView::section {{
                background-color: {config.COLOR_BACKGROUND};
                color: #AAA;
                padding: 4px; 
                border: none;
                border-bottom: 2px solid {config.COLOR_ACCENT};
                font-weight: bold;
                text-transform: uppercase;
                font-size: 11px;
            }}
            QTableCornerButton::section {{ background-color: {config.COLOR_BACKGROUND}; border: none; }}
            
            /* LISTS */
            QListWidget {{
                background-color: {config.COLOR_SURFACE};
                border: 1px solid #333;
                border-radius: 5px;
                color: {config.COLOR_TEXT};
            }}
            
            /* INPUTS */
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                background-color: {config.COLOR_BACKGROUND};
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px;
                color: white;
                selection-background-color: {config.COLOR_ACCENT};
            }}
            QComboBox QAbstractItemView {{
                background-color: {config.COLOR_SURFACE};
                color: white;
                border: 1px solid #444;
                selection-background-color: {config.COLOR_ACCENT};
            }}
            
            /* TABS */
            QTabWidget::pane {{ border: 1px solid #333; background: {config.COLOR_SURFACE}; border-radius: 6px; }}
            QTabBar::tab {{ background: {config.COLOR_BACKGROUND}; color: #888; padding: 10px 20px; }}
            QTabBar::tab:selected {{ background: {config.COLOR_SURFACE}; color: {config.COLOR_ACCENT}; border-bottom: 2px solid {config.COLOR_ACCENT}; font-weight: bold; }}
            QTabWidget > QWidget {{ background-color: transparent; }}
            
            /* TEXT EDITS */
            QTextEdit, QPlainTextEdit {{
                background-color: {config.COLOR_SURFACE};
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px;
                color: {config.COLOR_TEXT};
            }}
            
            /* CARDS */
            QStackedWidget > QWidget {{ background-color: transparent; }}
            QToolTip {{ color: white; background-color: #333; border: 1px solid #555; }}
            QScrollArea {{ background-color: transparent; border: none; }}
        """)

    def setup_timers(self):
        # Stop existing timers/threads
        try:
            if hasattr(self, 'market_timer'): self.market_timer.stop()
            if hasattr(self, 'order_timer'): self.order_timer.stop()
            if hasattr(self, 'ui_timer'): self.ui_timer.stop()
            if self.bot_thread and self.bot_thread.isRunning():
                self.bot_thread.stop()
        except: pass

        # --- SPEED OPTIMIZATION ---
        
        # 1. Market Engine (10s - Price updates)
        self.market_timer = QTimer()
        self.market_timer.timeout.connect(self.update_market_prices)
        self.market_timer.start(10000) 
        
        # 2. Bots -> NOW RUNNING IN BACKGROUND THREAD
        self.bot_thread = BotWorker()
        self.bot_thread.trades_executed.connect(self.on_bot_activity)
        self.bot_thread.start()
        
        # 3. Order Matching (5s - MATCHING SPEED INCREASED)
        self.order_timer = QTimer()
        self.order_timer.timeout.connect(self.match_orders)
        self.order_timer.start(5000)
        
        # 4. UI Refresh (5s - UI UPDATES FASTER)
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.refresh_ui_data)
        self.ui_timer.start(5000)
    
    def on_bot_activity(self, count):
        """Called when bots execute trades in background"""
        self.status_bar.showMessage(f"🤖 Market Active: {count} bot trades executed recently", 3000)

    def update_market_prices(self):
        try:
            market_engine.update_all_prices()
        except: pass
    
    def match_orders(self):
        try:
            order_matcher.match_all_orders()
        except: pass
    
    def refresh_ui_data(self):
        if self.isActiveWindow():
            if self.current_user:
                self.update_user_info()
                current_widget = self.content_stack.currentWidget()
                if hasattr(current_widget, 'refresh_data'):
                    current_widget.refresh_data()
    
    def update_user_info(self):
        if auth_service.is_authenticated():
            user = auth_service.get_current_user()
            self.current_user = user
            self.user_info_label.setText(f"👤 {user.full_name}")
            self.balance_label.setText(f"💰 {Formatter.format_currency(user.wallet_balance)}")
            if user.is_admin:
                self.admin_btn.show()
            else:
                self.admin_btn.hide()
    
    def update_status_bar(self):
        self.status_bar.showMessage("System Ready • Market Open")
    
    def load_screens(self):
        from ui.user_dashboard import UserDashboard
        from ui.market_screen import MarketScreen
        from ui.portfolio_screen import PortfolioScreen
        from ui.orders_screen import OrdersScreen
        from ui.company_dashboard import CompanyDashboard
        from ui.wallet_screen import WalletScreen
        from ui.loan_screen import LoanScreen
        from ui.chat_screen import ChatScreen
        from ui.admin_screen import AdminScreen
        
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
        reply = QMessageBox.question(self, 'Logout', 'Are you sure you want to logout?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            auth_service.logout()
            
            # STOP THREADS PROPERLY
            if self.bot_thread: self.bot_thread.stop()
            self.market_timer.stop()
            self.order_timer.stop()
            self.ui_timer.stop()
            
            self.close()
            from ui.auth_screen import AuthScreen
            self.auth_screen = AuthScreen()
            self.auth_screen.login_successful.connect(self.on_login_success)
            self.auth_screen.show()
    
    def on_login_success(self):
        self.update_user_info()
        self.load_screens()
        # RESTART THREADS/TIMERS
        self.setup_timers()
        self.showMaximized()
    
    def closeEvent(self, event):
        try:
            self.market_timer.stop()
            if self.bot_thread: self.bot_thread.stop()
            self.order_timer.stop()
            self.ui_timer.stop()
        except: pass
        event.accept()