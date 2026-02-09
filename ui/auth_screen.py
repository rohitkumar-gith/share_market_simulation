"""
Authentication Screen - Login and Registration
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QTabWidget,
                             QFormLayout, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from services.auth_service import auth_service
import config

class AuthScreen(QWidget):
    """Authentication screen with login and registration"""
    
    login_successful = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle(f"{config.APP_NAME} - Login")
        self.setMinimumSize(450, 650)
        self.resize(450, 650)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)
        
        # Title
        title_label = QLabel(config.APP_NAME)
        title_label.setFont(QFont('Segoe UI', 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"color: {config.COLOR_ACCENT}; margin-bottom: 5px;")
        main_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Virtual Stock Market Simulation")
        subtitle_label.setFont(QFont('Segoe UI', 12))
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet(f"color: {config.COLOR_TEXT_DIM};")
        main_layout.addWidget(subtitle_label)
        
        main_layout.addSpacing(20)
        
        # Tab widget for Login/Register
        self.tab_widget = QTabWidget()
        
        # Login tab
        login_widget = self.create_login_tab()
        self.tab_widget.addTab(login_widget, "Log In")
        
        # Register tab
        register_widget = self.create_register_tab()
        self.tab_widget.addTab(register_widget, "Register")
        
        main_layout.addWidget(self.tab_widget)
        
        # Footer
        footer_label = QLabel(f"Version {config.APP_VERSION}")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("color: #666; font-size: 10px; margin-top: 10px;")
        main_layout.addWidget(footer_label)
        
        self.setLayout(main_layout)
        
        # --- DARK THEME STYLESHEET ---
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {config.COLOR_BACKGROUND};
                color: {config.COLOR_TEXT};
                font-family: 'Segoe UI', sans-serif;
            }}
            
            QTabWidget::pane {{
                border: 1px solid #333;
                background: {config.COLOR_SURFACE};
                border-radius: 8px;
            }}
            
            QTabBar::tab {{
                background: {config.COLOR_BACKGROUND};
                color: {config.COLOR_TEXT_DIM};
                padding: 12px 0px;
                width: 150px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{
                background: {config.COLOR_SURFACE};
                color: {config.COLOR_ACCENT};
                border-bottom: 2px solid {config.COLOR_ACCENT};
                font-weight: bold;
            }}
            
            QLineEdit {{
                min-height: 40px; 
                padding: 0 10px;
                border: 1px solid #444;
                border-radius: 6px;
                font-size: 14px;
                background-color: {config.COLOR_BACKGROUND};
                color: white;
            }}
            QLineEdit:focus {{
                border: 1px solid {config.COLOR_ACCENT};
            }}
            
            QPushButton {{
                min-height: 45px;
                border-radius: 6px;
                font-size: 15px;
                font-weight: bold;
                color: white;
            }}
        """)
    
    def create_login_tab(self):
        """Create login tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setSpacing(20)
        
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Username")
        layout.addWidget(self.login_username)
        
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Password")
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_password.returnPressed.connect(self.handle_login)
        layout.addWidget(self.login_password)
        
        login_btn = QPushButton("Log In")
        login_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {config.COLOR_ACCENT}; }}
            QPushButton:hover {{ background-color: #2980B9; }}
        """)
        login_btn.clicked.connect(self.handle_login)
        layout.addWidget(login_btn)
        
        demo_info = QLabel("Demo: username=demo, password=demo123")
        demo_info.setStyleSheet("color: #666; font-size: 12px; font-style: italic;")
        demo_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(demo_info)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_register_tab(self):
        """Create registration tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        self.reg_username = QLineEdit()
        self.reg_username.setPlaceholderText("Username")
        layout.addWidget(self.reg_username)
        
        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Email Address")
        layout.addWidget(self.reg_email)
        
        self.reg_fullname = QLineEdit()
        self.reg_fullname.setPlaceholderText("Full Name")
        layout.addWidget(self.reg_fullname)
        
        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Password")
        self.reg_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.reg_password)
        
        self.reg_confirm_password = QLineEdit()
        self.reg_confirm_password.setPlaceholderText("Confirm Password")
        self.reg_confirm_password.setEchoMode(QLineEdit.Password)
        self.reg_confirm_password.returnPressed.connect(self.handle_register)
        layout.addWidget(self.reg_confirm_password)
        
        register_btn = QPushButton("Create Account")
        register_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {config.COLOR_SUCCESS}; }}
            QPushButton:hover {{ background-color: #00A045; }}
        """)
        register_btn.clicked.connect(self.handle_register)
        layout.addWidget(register_btn)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def handle_login(self):
        username = self.login_username.text().strip()
        password = self.login_password.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password")
            return
        
        try:
            user = auth_service.login(username, password)
            self.login_successful.emit()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Login Failed", str(e))
    
    def handle_register(self):
        username = self.reg_username.text().strip()
        email = self.reg_email.text().strip()
        fullname = self.reg_fullname.text().strip()
        password = self.reg_password.text()
        confirm_password = self.reg_confirm_password.text()
        
        if not all([username, email, fullname, password, confirm_password]):
            QMessageBox.warning(self, "Error", "Please fill in all fields")
            return
        
        if password != confirm_password:
            QMessageBox.warning(self, "Error", "Passwords do not match")
            return
        
        try:
            user = auth_service.register(username, password, email, fullname)
            QMessageBox.information(self, "Success", f"Account created! Welcome, {user.full_name}!")
            self.tab_widget.setCurrentIndex(0)
            self.login_username.setText(username)
            self.login_password.setFocus()
            self.clear_register_form()
        except Exception as e:
            QMessageBox.critical(self, "Registration Failed", str(e))
    
    def clear_register_form(self):
        self.reg_username.clear()
        self.reg_email.clear()
        self.reg_fullname.clear()
        self.reg_password.clear()
        self.reg_confirm_password.clear()