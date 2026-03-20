"""
Asset Service - Business Operations Logic
"""
from database.db_manager import db
from models.company import Company
from datetime import datetime
import math

class AssetService:
    
    def __init__(self):
        """Auto-patch the database safely for the new Rarity, Quantity, and Consumable features"""
        try:
            # 1. Patch the master_assets table
            columns_info = db.execute_query("PRAGMA table_info(master_assets)")
            if columns_info:
                existing_columns = [c['name'] if isinstance(c, dict) else c[1] for c in columns_info]
                
                if 'total_quantity' not in existing_columns: 
                    db.execute_update("ALTER TABLE master_assets ADD COLUMN total_quantity INTEGER DEFAULT -1") # -1 means infinite
                if 'available_quantity' not in existing_columns: 
                    db.execute_update("ALTER TABLE master_assets ADD COLUMN available_quantity INTEGER DEFAULT -1")
                if 'rarity' not in existing_columns: 
                    db.execute_update("ALTER TABLE master_assets ADD COLUMN rarity TEXT DEFAULT 'Common'")
                if 'max_uses' not in existing_columns: 
                    db.execute_update("ALTER TABLE master_assets ADD COLUMN max_uses INTEGER DEFAULT -1") # -1 means infinite use

            # 2. Patch the owned_assets table
            owned_cols_info = db.execute_query("PRAGMA table_info(owned_assets)")
            if owned_cols_info:
                owned_columns = [c['name'] if isinstance(c, dict) else c[1] for c in owned_cols_info]
                
                if 'remaining_uses' not in owned_columns:
                    db.execute_update("ALTER TABLE owned_assets ADD COLUMN remaining_uses INTEGER DEFAULT -1")
                # --- NEW: Quantity column for stacking items! ---
                if 'quantity' not in owned_columns:
                    db.execute_update("ALTER TABLE owned_assets ADD COLUMN quantity INTEGER DEFAULT 1")
        except Exception as e:
            print(f"Asset DB Patch Error: {e}")

    # --- ADMIN FUNCTIONS ---
    
    # --- ADMIN FUNCTIONS ---
    
    def create_master_asset(self, name, asset_type, base_price, revenue_rate, total_quantity=-1, rarity="Common", max_uses=-1):
        """Admin function to create a new asset with limited stock and uses"""
        try:
            db.execute_insert("""
                INSERT INTO master_assets (name, asset_type, base_price, revenue_rate, total_quantity, available_quantity, rarity, max_uses)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, asset_type, base_price, revenue_rate, total_quantity, total_quantity, rarity, max_uses))
            return {'success': True, 'message': f'Asset "{name}" created successfully!'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def delete_master_asset(self, asset_id):
        """Completely wipes an asset from the game, including player inventories"""
        try:
            # 1. Find all player-owned instances to delete their marketplace listings
            instances = db.execute_query("SELECT instance_id FROM owned_assets WHERE master_asset_id = ?", (asset_id,))
            if instances:
                for inst in instances:
                    db.execute_update("DELETE FROM marketplace_listings WHERE instance_id = ?", (inst['instance_id'],))
            
            # 2. Delete from player inventories
            db.execute_update("DELETE FROM owned_assets WHERE master_asset_id = ?", (asset_id,))
            
            # 3. Delete the master template
            db.execute_update("DELETE FROM master_assets WHERE asset_id = ?", (asset_id,))
            return {'success': True, 'message': 'Asset and all player copies completely wiped from the server!'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def sync_master_asset_update(self, asset_id, new_max_uses):
        """Retroactively updates existing player items if the admin changes the max uses"""
        try:
            db.execute_update("UPDATE owned_assets SET remaining_uses = ? WHERE master_asset_id = ?", (new_max_uses, asset_id))
            return True
        except:
            return False

    # --- CORE ASSET LOGIC ---

    def get_all_assets(self):
        """Get catalog of available master assets"""
        res = db.execute_query("SELECT * FROM master_assets ORDER BY base_price ASC")
        return [dict(row) for row in res] if res else []

    def buy_asset_for_company(self, user_id, company_id, asset_id, purchase_qty=1):
        """Company buys an asset (Car/Building/Item)"""
        try:
            if purchase_qty < 1: return {'success': False, 'message': "Must buy at least 1."}
            
            company = Company.get_by_id(company_id)
            if company.owner_id != user_id:
                return {'success': False, 'message': "Not owner"}
            
            assets = db.execute_query("SELECT * FROM master_assets WHERE asset_id = ?", (asset_id,))
            if not assets: return {'success': False, 'message': "Asset not found"}
            asset = dict(assets[0]) # Convert to dict!
            
            # Check limited stock
            if asset.get('total_quantity', -1) != -1 and asset.get('available_quantity', 0) < purchase_qty:
                return {'success': False, 'message': f"Out of Stock! Only {asset.get('available_quantity', 0)} available."}
            
            total_cost = asset['base_price'] * purchase_qty
            if company.company_wallet < total_cost:
                return {'success': False, 'message': "Insufficient company funds"}
            
            company.update_wallet(-total_cost)
            
            # Decrement global stock if it's a limited item
            if asset.get('total_quantity', -1) != -1:
                db.execute_update("UPDATE master_assets SET available_quantity = available_quantity - ? WHERE asset_id = ?", (purchase_qty, asset_id))
            
            # Companies don't stack currently, they buy instances
            db.execute_insert(
                """INSERT INTO owned_assets 
                   (master_asset_id, owner_id, owner_type, acquired_price, remaining_uses, quantity) 
                   VALUES (?, ?, 'COMPANY', ?, ?, ?)""",
                (asset_id, company_id, asset['base_price'], asset.get('max_uses', -1), purchase_qty)
            )
            
            db.execute_insert(
                "INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                (company_id, 'EXPENSE', total_cost, company.company_wallet, f"Bought {purchase_qty}x {asset['name']}")
            )
            
            return {'success': True, 'message': f"Successfully purchased {purchase_qty}x {asset['name']}"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_company_assets(self, company_id):
        """Get assets owned by a company"""
        query = """
            SELECT o.*, o.quantity, m.name, m.asset_type, m.revenue_rate, m.rarity, m.max_uses
            FROM owned_assets o
            JOIN master_assets m ON o.master_asset_id = m.asset_id
            WHERE o.owner_id = ? AND o.owner_type = 'COMPANY'
        """
        res = db.execute_query(query, (company_id,))
        return [dict(row) for row in res] if res else []

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
            
            if minutes_elapsed > 0 and asset.get('revenue_rate', 0) > 0:
                # MULTIPLY BY QUANTITY
                total_pending += minutes_elapsed * asset['revenue_rate'] * asset.get('quantity', 1)

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

    # --- USER ASSETS, ITEMS, & PASSIVE INCOME ---
    
    def buy_asset_for_user(self, user_id, asset_id, purchase_qty=1):
        """User buys an asset personally from Official Store"""
        try:
            if purchase_qty < 1: return {'success': False, 'message': "Must buy at least 1."}
            
            from models.user import User 
            user = User.get_by_id(user_id)
            if not user: return {'success': False, 'message': "User not found"}
            
            assets = db.execute_query("SELECT * FROM master_assets WHERE asset_id = ?", (asset_id,))
            if not assets: return {'success': False, 'message': "Asset not found"}
            asset = dict(assets[0]) # Convert to dict!
            
            # Check limited stock
            if asset.get('total_quantity', -1) != -1 and asset.get('available_quantity', 0) < purchase_qty:
                return {'success': False, 'message': f"Out of Stock! Only {asset.get('available_quantity', 0)} available."}
            
            total_cost = asset['base_price'] * purchase_qty
            if user.wallet_balance < total_cost:
                return {'success': False, 'message': "Insufficient personal funds!"}
            
            new_balance = user.wallet_balance - total_cost
            db.execute_update("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_balance, user_id))
            
            # Decrement global stock if it's a limited item
            if asset.get('total_quantity', -1) != -1:
                db.execute_update("UPDATE master_assets SET available_quantity = available_quantity - ? WHERE asset_id = ?", (purchase_qty, asset_id))
            
            # --- STACKING LOGIC ---
            # Check if user already has this item (and it's not listed on the market)
            existing_stack = db.execute_query("""
                SELECT instance_id, quantity FROM owned_assets 
                WHERE master_asset_id = ? AND owner_id = ? AND owner_type = 'USER' 
                AND instance_id NOT IN (SELECT instance_id FROM marketplace_listings WHERE status = 'ACTIVE')
            """, (asset_id, user_id))
            
            if existing_stack:
                stack = dict(existing_stack[0])
                new_qty = stack['quantity'] + purchase_qty
                db.execute_update("UPDATE owned_assets SET quantity = ? WHERE instance_id = ?", (new_qty, stack['instance_id']))
            else:
                db.execute_insert(
                    """INSERT INTO owned_assets 
                       (master_asset_id, owner_id, owner_type, acquired_price, remaining_uses, quantity) 
                       VALUES (?, ?, 'USER', ?, ?, ?)""",
                    (asset_id, user_id, asset['base_price'], asset.get('max_uses', -1), purchase_qty)
                )
            
            db.execute_insert(
                "INSERT INTO wallet_transactions (user_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, 'EXPENSE', total_cost, new_balance, f"Purchased {purchase_qty}x {asset['name']}")
            )
            return {'success': True, 'message': f"Congratulations! You bought {purchase_qty}x {asset.get('rarity', 'Common')} {asset['name']}!"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_user_assets(self, user_id):
        """Get all assets owned by a specific user, including usages and marketplace status"""
        query = """
            SELECT o.*, o.quantity, m.name, m.asset_type, m.revenue_rate, m.rarity, m.max_uses,
                   (SELECT asking_price FROM marketplace_listings ml WHERE ml.instance_id = o.instance_id AND ml.status = 'ACTIVE') as listed_price,
                   (SELECT listing_id FROM marketplace_listings ml WHERE ml.instance_id = o.instance_id AND ml.status = 'ACTIVE') as listing_id
            FROM owned_assets o
            JOIN master_assets m ON o.master_asset_id = m.asset_id
            WHERE o.owner_id = ? AND o.owner_type = 'USER'
        """
        res = db.execute_query(query, (user_id,))
        return [dict(row) for row in res] if res else []

    def use_user_asset(self, user_id, instance_id, use_qty=1):
        """Consumes an item. Deletes it from inventory if it reaches 0 uses."""
        try:
            if use_qty < 1: return {'success': False, 'message': 'Invalid amount.'}
            
            owned_res = db.execute_query("""
                SELECT o.*, m.name 
                FROM owned_assets o 
                JOIN master_assets m ON o.master_asset_id = m.asset_id 
                WHERE o.instance_id = ? AND o.owner_id = ? AND o.owner_type = 'USER'
            """, (instance_id, user_id))
            
            if not owned_res: return {'success': False, 'message': 'Asset not found in your inventory.'}
            owned = dict(owned_res[0]) # Convert to dict!

            # Prevent using listed items
            listing = db.execute_query("SELECT status FROM marketplace_listings WHERE instance_id = ? AND status = 'ACTIVE'", (instance_id,))
            if listing:
                return {'success': False, 'message': 'Cannot use an item while it is listed for sale!'}

            # Infinite use check
            if owned.get('remaining_uses', -1) == -1:
                return {'success': True, 'message': f"You used your {owned['name']}. It can be used infinitely!"}

            # Check if they have enough to consume
            current_qty = owned.get('quantity', 1)
            if use_qty > current_qty:
                return {'success': False, 'message': f"You only have {current_qty} of this item!"}

            # Consumable item logic (applies to the quantity stack)
            new_qty = current_qty - use_qty
            if new_qty > 0:
                db.execute_update("UPDATE owned_assets SET quantity = ? WHERE instance_id = ?", (new_qty, instance_id))
                return {'success': True, 'message': f"You used {use_qty}x {owned['name']}. You have {new_qty} left."}
            else:
                # Used the very last one! Destroy it.
                db.execute_update("DELETE FROM owned_assets WHERE instance_id = ?", (instance_id,))
                return {'success': True, 'message': f"You used your last {use_qty}x {owned['name']}! It has been removed from your inventory."}
                
        except Exception as e:
            return {'success': False, 'message': str(e)}

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
            if asset.get('revenue_rate', 0) <= 0: continue
            
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
                # MULTIPLY BY QUANTITY
                total_pending += minutes_elapsed * asset['revenue_rate'] * asset.get('quantity', 1)

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
            return {'success': True, 'message': f"Asset stack successfully listed on the marketplace for ₹{asking_price:,.2f}!"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def cancel_asset_listing(self, user_id, listing_id):
        """Cancel an active marketplace listing"""
        try:
            listing = db.execute_query("SELECT * FROM marketplace_listings WHERE listing_id = ? AND seller_id = ?", (listing_id, user_id))
            if not listing: return {'success': False, 'message': "Listing not found or unauthorized."}
            
            db.execute_update("UPDATE marketplace_listings SET status = 'CANCELLED' WHERE listing_id = ?", (listing_id,))
            return {'success': True, 'message': "Listing cancelled. Asset returned to inventory."}
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
            SELECT ml.*, m.name, m.asset_type, m.revenue_rate, m.rarity, o.remaining_uses, o.quantity, u.username as seller_name
            FROM marketplace_listings ml
            JOIN owned_assets o ON ml.instance_id = o.instance_id
            JOIN master_assets m ON o.master_asset_id = m.asset_id
            JOIN users u ON ml.seller_id = u.user_id
            WHERE ml.status = 'ACTIVE'
            ORDER BY ml.created_at DESC
        """
        res = db.execute_query(query)
        return [dict(row) for row in res] if res else []

    def buy_marketplace_asset(self, buyer_id, listing_id):
        """Process a player buying an asset stack from another player"""
        try:
            from models.user import User 
            
            listing_data = db.execute_query("SELECT * FROM marketplace_listings WHERE listing_id = ? AND status = 'ACTIVE'", (listing_id,))
            if not listing_data: return {'success': False, 'message': "Listing no longer available."}
            listing = dict(listing_data[0]) # Convert to dict!
            
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
            asset_res = db.execute_query("SELECT m.name, o.quantity FROM owned_assets o JOIN master_assets m ON o.master_asset_id = m.asset_id WHERE o.instance_id = ?", (listing['instance_id'],))
            asset_info = dict(asset_res[0])
            
            db.execute_insert(
                "INSERT INTO wallet_transactions (user_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                (buyer_id, 'EXPENSE', price, new_buyer_bal, f"Bought P2P Stack: {asset_info['quantity']}x {asset_info['name']} from {seller.username}")
            )
            db.execute_insert(
                "INSERT INTO wallet_transactions (user_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                (seller.user_id, 'REVENUE', price, new_seller_bal, f"Sold P2P Stack: {asset_info['quantity']}x {asset_info['name']} to {buyer.username}")
            )
            
            return {'success': True, 'message': f"Successfully purchased stack of {asset_info['quantity']}x {asset_info['name']}!"}
            
        except Exception as e:
            return {'success': False, 'message': str(e)}

asset_service = AssetService()