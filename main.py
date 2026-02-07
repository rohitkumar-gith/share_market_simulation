"""
Main Application Entry Point
Share Market Simulation System
"""
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from ui.auth_screen import AuthScreen
from ui.main_window import MainWindow
from services.auth_service import auth_service
from trading.bot_trader import bot_trader
import config


def main():
    """Main application entry point"""
    # Create Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    
    # Set application-wide style
    app.setStyle('Fusion')
    
    # Initialize trading bots
    print("Initializing trading bots...")
    bot_trader.initialize_bots()
    
    # Show authentication screen
    auth_screen = AuthScreen()
    
    # Create main window (hidden initially)
    main_window = MainWindow()
    
    def on_login_success():
        """Handle successful login"""
        auth_screen.close()
        main_window.update_user_info()
        main_window.load_screens()
        main_window.show()
    
    # Connect login signal
    auth_screen.login_successful.connect(on_login_success)
    
    # Show auth screen
    auth_screen.show()
    
    # Start event loop
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
