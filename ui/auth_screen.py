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
        
        # --- FIX 1: Allow window to be resized if needed ---
        self.setMinimumSize(500, 650) 
        self.resize(500, 650)
        # ---------------------------------------------------
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)
        
        # Title
        title_label = QLabel(config.APP_NAME)
        title_label.setFont(QFont('Arial', 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"color: {config.COLOR_PRIMARY};")
        main_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Virtual Stock Market Simulation")
        subtitle_label.setFont(QFont('Arial', 12))
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet(f"color: {config.COLOR_SECONDARY};")
        main_layout.addWidget(subtitle_label)
        
        main_layout.addSpacing(20)
        
        # Tab widget for Login/Register
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 5px;
                background: white;
            }
            QTabBar::tab {
                background: #f0f0f0;
                padding: 10px 20px;
                margin-right: 2px;
                color: black; 
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 2px solid #3498DB;
                color: black;
            }
        """)
        
        # Login tab
        login_widget = self.create_login_tab()
        self.tab_widget.addTab(login_widget, "Login")
        
        # Register tab
        register_widget = self.create_register_tab()
        self.tab_widget.addTab(register_widget, "Register")
        
        main_layout.addWidget(self.tab_widget)
        
        # Footer
        footer_label = QLabel(f"Version {config.APP_VERSION}")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("color: #888888; font-size: 10px;")
        main_layout.addWidget(footer_label)
        
        self.setLayout(main_layout)
        
        # --- FIX 2 & 3: Added min-height and color ---
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {config.COLOR_BACKGROUND};
            }}
            QLineEdit {{
                min-height: 40px; 
                padding: 5px 10px;
                border: 1px solid #cccccc;
                border-radius: 5px;
                font-size: 14px;
                background-color: white;
                color: black; 
            }}
            QLineEdit:focus {{
                border: 2px solid {config.COLOR_SECONDARY};
            }}
            QLabel {{
                color: {config.COLOR_TEXT};
            }}
            QPushButton {{
                min-height: 40px;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
    
    def create_login_tab(self):
        """Create login tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Enter username")
        form_layout.addRow("Username:", self.login_username)
        
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Enter password")
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_password.returnPressed.connect(self.handle_login)
        form_layout.addRow("Password:", self.login_password)
        
        layout.addLayout(form_layout)
        layout.addSpacing(10)
        
        # Login button
        login_btn = QPushButton("Login")
        login_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {config.COLOR_SUCCESS};
                color: white;
            }}
            QPushButton:hover {{
                background-color: #229954;
            }}
        """)
        login_btn.clicked.connect(self.handle_login)
        layout.addWidget(login_btn)
        
        # Demo credentials info
        demo_info = QLabel("Demo: username=demo, password=demo123")
        demo_info.setStyleSheet("color: #888888; font-size: 11px; font-style: italic;")
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
        
        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        self.reg_username = QLineEdit()
        self.reg_username.setPlaceholderText("3-20 alphanumeric characters")
        form_layout.addRow("Username:", self.reg_username)
        
        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("your.email@example.com")
        form_layout.addRow("Email:", self.reg_email)
        
        self.reg_fullname = QLineEdit()
        self.reg_fullname.setPlaceholderText("Your full name")
        form_layout.addRow("Full Name:", self.reg_fullname)
        
        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("At least 6 characters")
        self.reg_password.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password:", self.reg_password)
        
        self.reg_confirm_password = QLineEdit()
        self.reg_confirm_password.setPlaceholderText("Confirm password")
        self.reg_confirm_password.setEchoMode(QLineEdit.Password)
        self.reg_confirm_password.returnPressed.connect(self.handle_register)
        form_layout.addRow("Confirm:", self.reg_confirm_password)
        
        layout.addLayout(form_layout)
        layout.addSpacing(10)
        
        # Register button
        register_btn = QPushButton("Create Account")
        register_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {config.COLOR_SECONDARY};
                color: white;
            }}
            QPushButton:hover {{
                background-color: #2980B9;
            }}
        """)
        register_btn.clicked.connect(self.handle_register)
        layout.addWidget(register_btn)
        
        # Info label
        info_label = QLabel(f"You'll start with ₹{config.INITIAL_USER_BALANCE:,.0f} in your wallet")
        info_label.setStyleSheet("color: #27AE60; font-size: 11px; font-style: italic;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def handle_login(self):
        """Handle login button click"""
        username = self.login_username.text().strip()
        password = self.login_password.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password")
            return
        
        try:
            user = auth_service.login(username, password)
            QMessageBox.information(
                self, 
                "Success", 
                f"Welcome back, {user.full_name}!"
            )
            self.login_successful.emit()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Login Failed", str(e))
    
    def handle_register(self):
        """Handle registration button click"""
        username = self.reg_username.text().strip()
        email = self.reg_email.text().strip()
        fullname = self.reg_fullname.text().strip()
        password = self.reg_password.text()
        confirm_password = self.reg_confirm_password.text()
        
        # Validation
        if not all([username, email, fullname, password, confirm_password]):
            QMessageBox.warning(self, "Error", "Please fill in all fields")
            return
        
        if password != confirm_password:
            QMessageBox.warning(self, "Error", "Passwords do not match")
            return
        
        try:
            user = auth_service.register(username, password, email, fullname)
            QMessageBox.information(
                self,
                "Success",
                f"Account created successfully!\nWelcome, {user.full_name}!\n\nYou can now login with your credentials."
            )
            self.tab_widget.setCurrentIndex(0)
            self.login_username.setText(username)
            self.login_password.setFocus()
            self.clear_register_form()
        except Exception as e:
            QMessageBox.critical(self, "Registration Failed", str(e))
    
    def clear_register_form(self):
        """Clear registration form"""
        self.reg_username.clear()
        self.reg_email.clear()
        self.reg_fullname.clear()
        self.reg_password.clear()
        self.reg_confirm_password.clear()