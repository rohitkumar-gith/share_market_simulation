"""
Asset Service - Business Operations Logic
"""
from database.db_manager import db
from models.company import Company
from datetime import datetime
import math

class AssetService:
    
    def get_all_assets(self):
        """Get catalog of available assets"""
        return db.execute_query("SELECT * FROM master_assets")

    def buy_asset_for_company(self, user_id, company_id, asset_id):
        """Company buys an asset (Car/Building)"""
        try:
            # 1. Validate Ownership
            company = Company.get_by_id(company_id)
            if company.owner_id != user_id:
                return {'success': False, 'message': "Not owner"}
            
            # 2. Get Asset Info
            assets = db.execute_query("SELECT * FROM master_assets WHERE asset_id = ?", (asset_id,))
            if not assets: return {'success': False, 'message': "Asset not found"}
            asset = assets[0]
            
            # 3. Check Funds
            if company.company_wallet < asset['base_price']:
                return {'success': False, 'message': "Insufficient company funds"}
            
            # 4. Transaction
            company.update_wallet(-asset['base_price'])
            
            # Add to owned_assets
            db.execute_insert(
                """INSERT INTO owned_assets 
                   (master_asset_id, owner_id, owner_type, acquired_price) 
                   VALUES (?, ?, 'COMPANY', ?)""",
                (asset_id, company_id, asset['base_price'])
            )
            
            # Record Expense
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
            # Handle string vs datetime object from SQLite
            ts = rows[0]['created_at']
            if isinstance(ts, str):
                try:
                    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                except:
                    # Fallback for ISO format if needed
                    return datetime.fromisoformat(ts)
            return ts
        return None

    def calculate_pending_revenue(self, company_id):
        """Calculate revenue accumulated since last collection"""
        assets = self.get_company_assets(company_id)
        if not assets:
            return 0.0

        last_collection = self.get_last_collection_time(company_id)
        
        # FIX: Use UTC Now to match Database (CURRENT_TIMESTAMP is UTC)
        now = datetime.utcnow() 
        
        total_pending = 0.0

        for asset in assets:
            # Ensure acquired_at is datetime
            acquired_at = asset['acquired_at']
            if isinstance(acquired_at, str):
                try: acquired_at = datetime.strptime(acquired_at, "%Y-%m-%d %H:%M:%S")
                except: continue

            # Revenue starts counting from whichever is LATER: 
            # 1. When the asset was bought
            # 2. When revenue was last collected (reset point)
            
            start_time = acquired_at
            if last_collection and last_collection > acquired_at:
                start_time = last_collection
            
            # Calculate duration in minutes
            duration = now - start_time
            minutes_elapsed = duration.total_seconds() / 60
            
            if minutes_elapsed > 0:
                total_pending += minutes_elapsed * asset['revenue_rate']

        return round(total_pending, 2)

    def collect_revenue(self, company_id):
        """Collect the calculated pending revenue"""
        pending_amount = self.calculate_pending_revenue(company_id)
        
        if pending_amount > 0:
            company = Company.get_by_id(company_id)
            company.update_wallet(pending_amount)
            
            # Log it so the timer resets (last_collection_time will update)
            db.execute_insert(
                "INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                (company_id, 'REVENUE', pending_amount, company.company_wallet, "Asset Revenue Collection")
            )
            return pending_amount
        return 0

asset_service = AssetService()