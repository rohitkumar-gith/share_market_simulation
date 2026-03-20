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
from database.db_manager import db
import config

def run_first_time_setup():
    """Checks if the DB is missing companies and auto-generates the starting world."""
    try:
        # Check if the market is completely empty of companies
        res = db.execute_query("SELECT COUNT(*) as count FROM companies")
        if res and res[0]['count'] == 0:
            print("Empty market detected! Initializing the global economy...")
            
            # 1. Ensure the Admin Account Exists
            admin_res = db.execute_query("SELECT user_id FROM users WHERE username = 'admin'")
            
            if not admin_res:
                # Create the admin if it doesn't exist yet
                auth_service.register("admin", "admin123", "admin@system.local", "System Admin")
                db.execute_update("UPDATE users SET is_admin = 1, wallet_balance = 10000000.0 WHERE username = 'admin'")
                admin_res = db.execute_query("SELECT user_id FROM users WHERE username = 'admin'")
                
            admin_id = admin_res[0]['user_id']
            
            # 2. Create the 3 Default Companies
            defaults = [
                ("Global Tech", "GLBT", 150.0, 50000, "Leading technology innovator.", 5000000.0),
                ("Apex Industries", "APEX", 85.0, 100000, "Heavy manufacturing and logistics.", 3000000.0),
                ("Venture Capital Corp", "VCC", 200.0, 25000, "Investment and finance conglomerate.", 10000000.0)
            ]
            for name, ticker, price, shares, desc, wallet in defaults:
                db.execute_insert('''
                    INSERT INTO companies (company_name, ticker_symbol, owner_id, share_price, total_shares, available_shares, company_wallet, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, ticker, admin_id, price, shares, shares, wallet, desc))

            # 3. Stock the Luxury Asset Store (Only if it's empty)
            asset_count = db.execute_query("SELECT COUNT(*) as count FROM master_assets")
            if asset_count and asset_count[0]['count'] == 0:
                from services.asset_service import asset_service
                asset_service.create_master_asset("Downtown Penthouse", "REAL_ESTATE", 1500000, 1500, 5, "Legendary", -1)
                asset_service.create_master_asset("Italian Sports Car", "CAR", 85000, 0, 50, "Rare", -1)
                asset_service.create_master_asset("Premium Cuban Cigar", "CONSUMABLE", 500, 0, -1, "Common", 3)
            
            print("Economy generated successfully! Ready to play.")
    except Exception as e:
        print(f"First-run setup failed: {e}")

def main():
    """Main application entry point"""
    # RUN THE CHECK BEFORE THE UI LOADS
    run_first_time_setup()

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