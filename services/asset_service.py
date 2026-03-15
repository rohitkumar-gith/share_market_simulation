"""
Asset Service - Business Operations Logic
"""
from database.db_manager import db
from models.company import Company
from datetime import datetime
import math

class AssetService:
    
    def get_all_assets(self):
        """Get catalog of available master assets"""
        return db.execute_query("SELECT * FROM master_assets")

    def buy_asset_for_company(self, user_id, company_id, asset_id):
        """Company buys an asset (Car/Building)"""
        try:
            company = Company.get_by_id(company_id)
            if company.owner_id != user_id:
                return {'success': False, 'message': "Not owner"}
            
            assets = db.execute_query("SELECT * FROM master_assets WHERE asset_id = ?", (asset_id,))
            if not assets: return {'success': False, 'message': "Asset not found"}
            asset = assets[0]
            
            if company.company_wallet < asset['base_price']:
                return {'success': False, 'message': "Insufficient company funds"}
            
            company.update_wallet(-asset['base_price'])
            
            db.execute_insert(
                """INSERT INTO owned_assets 
                   (master_asset_id, owner_id, owner_type, acquired_price) 
                   VALUES (?, ?, 'COMPANY', ?)""",
                (asset_id, company_id, asset['base_price'])
            )
            
            db.execute_insert(
                "INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                (company_id, 'EXPENSE', asset['base_price'], company.company_wallet, f"Bought {asset['name']}")
            )
            
            return {'success': True, 'message': f"Successfully purchased {asset['name']}"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_company_assets(self, company_id):
        """Get assets owned by a company"""
        query = """
            SELECT o.*, m.name, m.asset_type, m.revenue_rate 
            FROM owned_assets o
            JOIN master_assets m ON o.master_asset_id = m.asset_id
            WHERE o.owner_id = ? AND o.owner_type = 'COMPANY'
        """
        return db.execute_query(query, (company_id,))

    def get_last_collection_time(self, company_id):
        """Find when revenue was last collected"""
        query = """
            SELECT created_at FROM company_wallet_transactions 
            WHERE company_id = ? AND transaction_type = 'REVENUE' 
            ORDER BY created_at DESC LIMIT 1
        """
        rows = db.execute_query(query, (company_id,))
        if rows:
            ts = rows[0]['created_at']
            if isinstance(ts, str):
                try: return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                except: return datetime.fromisoformat(ts)
            return ts
        return None

    def calculate_pending_revenue(self, company_id):
        """Calculate revenue accumulated since last collection for a COMPANY"""
        assets = self.get_company_assets(company_id)
        if not assets: return 0.0

        last_collection = self.get_last_collection_time(company_id)
        now = datetime.utcnow() 
        total_pending = 0.0

        for asset in assets:
            acquired_at = asset['acquired_at']
            if isinstance(acquired_at, str):
                try: acquired_at = datetime.strptime(acquired_at, "%Y-%m-%d %H:%M:%S")
                except: continue
            
            start_time = acquired_at
            if last_collection and last_collection > acquired_at:
                start_time = last_collection
            
            duration = now - start_time
            minutes_elapsed = duration.total_seconds() / 60
            
            if minutes_elapsed > 0:
                total_pending += minutes_elapsed * asset['revenue_rate']

        return round(total_pending, 2)

    def collect_revenue(self, company_id):
        """Collect the calculated pending revenue for a COMPANY"""
        pending_amount = self.calculate_pending_revenue(company_id)
        
        if pending_amount > 0:
            company = Company.get_by_id(company_id)
            company.update_wallet(pending_amount)
            
            db.execute_insert(
                "INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                (company_id, 'REVENUE', pending_amount, company.company_wallet, "Asset Revenue Collection")
            )
            return pending_amount
        return 0

    # --- USER ASSETS & PASSIVE INCOME ---
    
    def buy_asset_for_user(self, user_id, asset_id):
        """User buys an asset personally from Official Store"""
        try:
            from models.user import User 
            user = User.get_by_id(user_id)
            if not user: return {'success': False, 'message': "User not found"}
            
            assets = db.execute_query("SELECT * FROM master_assets WHERE asset_id = ?", (asset_id,))
            if not assets: return {'success': False, 'message': "Asset not found"}
            asset = assets[0]
            
            if user.wallet_balance < asset['base_price']:
                return {'success': False, 'message': "Insufficient personal funds!"}
            
            new_balance = user.wallet_balance - asset['base_price']
            db.execute_update("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_balance, user_id))
            
            db.execute_insert(
                """INSERT INTO owned_assets 
                   (master_asset_id, owner_id, owner_type, acquired_price) 
                   VALUES (?, ?, 'USER', ?)""",
                (asset_id, user_id, asset['base_price'])
            )
            
            db.execute_insert(
                "INSERT INTO wallet_transactions (user_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, 'EXPENSE', asset['base_price'], new_balance, f"Purchased Asset: {asset['name']}")
            )
            return {'success': True, 'message': f"Congratulations! You bought a {asset['name']}!"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_user_assets(self, user_id):
        """Get all assets owned by a specific user, including listing status and listing_id"""
        query = """
            SELECT o.*, m.name, m.asset_type, m.revenue_rate,
                   (SELECT asking_price FROM marketplace_listings ml WHERE ml.instance_id = o.instance_id AND ml.status = 'ACTIVE') as listed_price,
                   (SELECT listing_id FROM marketplace_listings ml WHERE ml.instance_id = o.instance_id AND ml.status = 'ACTIVE') as listing_id
            FROM owned_assets o
            JOIN master_assets m ON o.master_asset_id = m.asset_id
            WHERE o.owner_id = ? AND o.owner_type = 'USER'
        """
        return db.execute_query(query, (user_id,))

    def get_user_last_collection_time(self, user_id):
        query = """
            SELECT created_at FROM wallet_transactions 
            WHERE user_id = ? AND transaction_type = 'REVENUE' AND description LIKE '%Asset Revenue%'
            ORDER BY created_at DESC LIMIT 1
        """
        rows = db.execute_query(query, (user_id,))
        if rows:
            ts = rows[0]['created_at']
            if isinstance(ts, str):
                try: return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                except: return datetime.fromisoformat(ts)
            return ts
        return None

    def calculate_user_pending_revenue(self, user_id):
        assets = self.get_user_assets(user_id)
        if not assets: return 0.0

        last_collection = self.get_user_last_collection_time(user_id)
        now = datetime.utcnow() 
        total_pending = 0.0

        for asset in assets:
            if asset['revenue_rate'] <= 0: continue
            
            # If asset is listed for sale, it doesn't generate passive income for the seller!
            if asset['listed_price'] is not None: continue 

            acquired_at = asset['acquired_at']
            if isinstance(acquired_at, str):
                try: acquired_at = datetime.strptime(acquired_at, "%Y-%m-%d %H:%M:%S")
                except: continue
            
            start_time = acquired_at
            if last_collection and last_collection > acquired_at:
                start_time = last_collection
            
            duration = now - start_time
            minutes_elapsed = duration.total_seconds() / 60
            
            if minutes_elapsed > 0:
                total_pending += minutes_elapsed * asset['revenue_rate']

        return round(total_pending, 2)

    def collect_user_revenue(self, user_id):
        pending_amount = self.calculate_user_pending_revenue(user_id)
        if pending_amount > 0:
            from models.user import User
            user = User.get_by_id(user_id)
            new_balance = user.wallet_balance + pending_amount
            
            db.execute_update("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_balance, user_id))
            
            db.execute_insert(
                "INSERT INTO wallet_transactions (user_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, 'REVENUE', pending_amount, new_balance, "Personal Asset Revenue Collection")
            )
            return {'success': True, 'amount': pending_amount}
        return {'success': False, 'amount': 0}

    # --- PLAYER-TO-PLAYER MARKETPLACE ---

    def list_asset_for_sale(self, user_id, instance_id, asking_price):
        """List an owned asset on the player-to-player marketplace"""
        try:
            asset = db.execute_query("SELECT * FROM owned_assets WHERE instance_id = ? AND owner_id = ? AND owner_type = 'USER'", (instance_id, user_id))
            if not asset: return {'success': False, 'message': "Asset not found or you don't own it."}
            
            existing = db.execute_query("SELECT * FROM marketplace_listings WHERE instance_id = ? AND status = 'ACTIVE'", (instance_id,))
            if existing: return {'success': False, 'message': "This asset is already listed for sale!"}
            
            db.execute_insert(
                "INSERT INTO marketplace_listings (instance_id, seller_id, seller_type, asking_price) VALUES (?, ?, 'USER', ?)",
                (instance_id, user_id, asking_price)
            )
            return {'success': True, 'message': f"Asset successfully listed on the marketplace for ₹{asking_price:,.2f}!"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def cancel_asset_listing(self, user_id, listing_id):
        """Cancel an active marketplace listing"""
        try:
            listing = db.execute_query("SELECT * FROM marketplace_listings WHERE listing_id = ? AND seller_id = ?", (listing_id, user_id))
            if not listing: return {'success': False, 'message': "Listing not found or unauthorized."}
            
            db.execute_update("UPDATE marketplace_listings SET status = 'CANCELLED' WHERE listing_id = ?", (listing_id,))
            return {'success': True, 'message': "Listing cancelled. Asset returned to garage."}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def update_asset_listing(self, user_id, listing_id, new_price):
        """Update the asking price of an active listing"""
        try:
            listing = db.execute_query("SELECT * FROM marketplace_listings WHERE listing_id = ? AND seller_id = ?", (listing_id, user_id))
            if not listing: return {'success': False, 'message': "Listing not found or unauthorized."}
            
            db.execute_update("UPDATE marketplace_listings SET asking_price = ? WHERE listing_id = ?", (new_price, listing_id))
            return {'success': True, 'message': f"Listing price updated to ₹{new_price:,.2f}"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_marketplace_listings(self):
        """Get all active player-to-player listings"""
        query = """
            SELECT ml.*, m.name, m.asset_type, m.revenue_rate, u.username as seller_name
            FROM marketplace_listings ml
            JOIN owned_assets o ON ml.instance_id = o.instance_id
            JOIN master_assets m ON o.master_asset_id = m.asset_id
            JOIN users u ON ml.seller_id = u.user_id
            WHERE ml.status = 'ACTIVE'
            ORDER BY ml.created_at DESC
        """
        return db.execute_query(query)

    def buy_marketplace_asset(self, buyer_id, listing_id):
        """Process a player buying an asset from another player"""
        try:
            from models.user import User 
            
            listing_data = db.execute_query("SELECT * FROM marketplace_listings WHERE listing_id = ? AND status = 'ACTIVE'", (listing_id,))
            if not listing_data: return {'success': False, 'message': "Listing no longer available."}
            listing = listing_data[0]
            
            if listing['seller_id'] == buyer_id:
                return {'success': False, 'message': "You cannot buy your own asset!"}
                
            buyer = User.get_by_id(buyer_id)
            seller = User.get_by_id(listing['seller_id'])
            price = listing['asking_price']
            
            if buyer.wallet_balance < price:
                return {'success': False, 'message': "Insufficient funds to buy this asset!"}
                
            # 1. Update Wallets (Transfer Money)
            new_buyer_bal = buyer.wallet_balance - price
            new_seller_bal = seller.wallet_balance + price
            db.execute_update("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_buyer_bal, buyer_id))
            db.execute_update("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_seller_bal, seller.user_id))
            
            # 2. Transfer Asset Ownership
            db.execute_update(
                "UPDATE owned_assets SET owner_id = ?, acquired_price = ?, acquired_at = CURRENT_TIMESTAMP WHERE instance_id = ?", 
                (buyer_id, price, listing['instance_id'])
            )
            
            # 3. Mark Listing as Sold
            db.execute_update("UPDATE marketplace_listings SET status = 'SOLD' WHERE listing_id = ?", (listing_id,))
            
            # 4. Record Wallet Transactions
            asset_info = db.execute_query("SELECT m.name FROM owned_assets o JOIN master_assets m ON o.master_asset_id = m.asset_id WHERE o.instance_id = ?", (listing['instance_id'],))[0]
            
            db.execute_insert(
                "INSERT INTO wallet_transactions (user_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                (buyer_id, 'EXPENSE', price, new_buyer_bal, f"Bought P2P Asset: {asset_info['name']} from {seller.username}")
            )
            db.execute_insert(
                "INSERT INTO wallet_transactions (user_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                (seller.user_id, 'REVENUE', price, new_seller_bal, f"Sold P2P Asset: {asset_info['name']} to {buyer.username}")
            )
            
            return {'success': True, 'message': f"Successfully purchased {asset_info['name']} from {seller.username}!"}
            
        except Exception as e:
            return {'success': False, 'message': str(e)}

asset_service = AssetService()