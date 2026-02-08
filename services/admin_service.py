"""
Admin Service - Superuser controls
"""
from database.db_manager import db
from models.user import User
from models.company import Company
from trading.market_engine import market_engine
from datetime import datetime
import random

class AdminService:
    
    def create_master_asset(self, admin_id, name, asset_type, price, revenue, supply):
        """Create a new car model or property type"""
        user = User.get_by_id(admin_id)
        if not user or not user.is_admin:
            return {'success': False, 'message': "Unauthorized"}
            
        try:
            query = """
                INSERT INTO master_assets (name, asset_type, base_price, revenue_rate, total_supply)
                VALUES (?, ?, ?, ?, ?)
            """
            db.execute_insert(query, (name, asset_type, price, revenue, supply))
            return {'success': True, 'message': f"Created {name}"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def edit_master_asset(self, admin_id, asset_id, name, asset_type, price, revenue, supply):
        """Edit an existing asset"""
        user = User.get_by_id(admin_id)
        if not user or not user.is_admin:
            return {'success': False, 'message': "Unauthorized"}

        try:
            query = """
                UPDATE master_assets
                SET name = ?, asset_type = ?, base_price = ?, revenue_rate = ?, total_supply = ?
                WHERE asset_id = ?
            """
            db.execute_update(query, (name, asset_type, price, revenue, supply, asset_id))
            return {'success': True, 'message': f"Updated {name}"}
        except Exception as e:
            return {'success': False, 'message': str(e)}
            
    def trigger_market_event(self, event_type, duration_minutes=2):
        """Trigger Sustained Market Event (Bull/Bear)"""
        # 1. Initial Shock (Instant small jump/drop)
        companies = Company.get_all()
        for company in companies:
            change = 0
            if event_type == 'bull':
                change = random.uniform(0.05, 0.10) # Instant 5-10% boost
            elif event_type == 'bear':
                change = random.uniform(-0.10, -0.05) # Instant 5-10% drop
                
            new_price = company.share_price * (1 + change)
            new_price = max(1.0, round(new_price, 2))
            
            # Update DB and History
            company.update_share_price(new_price)
            db.execute_insert("INSERT INTO price_history (company_id, price, recorded_at) VALUES (?, ?, ?)", 
                            (company.company_id, new_price, datetime.now()))
            
            # --- FIX: FLUSH ORDER BOOK FOR EVERY COMPANY ---
            # This prevents old orders from reverting the price immediately
            self._flush_order_book(company.company_id)

        # 2. Sustained Trend (Duration based on input)
        duration_seconds = duration_minutes * 60
        market_engine.set_market_trend(event_type, duration_seconds)
            
        return {'success': True, 'message': f"Market {event_type.upper()} started! (Duration: {duration_minutes} mins). All pending orders flushed."}

    def manipulate_specific_company(self, company_id, percentage_change):
        """Targeted price manipulation for a single company"""
        try:
            company = Company.get_by_id(company_id)
            if not company:
                return {'success': False, 'message': "Company not found"}
            
            current_price = company.share_price
            
            # Calculate new price
            multiplier = 1 + (percentage_change / 100.0)
            if multiplier < 0.01: multiplier = 0.01 # Safety clamp
                
            new_price = current_price * multiplier
            new_price = max(0.10, round(new_price, 2))
            
            # 1. Apply Price Update
            company.update_share_price(new_price)
            
            # 2. Record in History
            db.execute_insert(
                "INSERT INTO price_history (company_id, price, recorded_at) VALUES (?, ?, ?)", 
                (company.company_id, new_price, datetime.now())
            )
            
            # 3. Flush Order Book
            self._flush_order_book(company.company_id)
            
            direction = "increased" if percentage_change > 0 else "decreased"
            return {
                'success': True, 
                'message': f"{company.ticker_symbol} {direction} by {abs(percentage_change)}% (₹{current_price} -> ₹{new_price}). Order book flushed."
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def _flush_order_book(self, company_id):
        """Cancel all pending orders for a company to force trading at new price"""
        try:
            # Get all pending orders
            orders = db.execute_query(
                "SELECT * FROM share_orders WHERE company_id = ? AND status = 'pending'", 
                (company_id,)
            )
            
            if not orders: return

            for order in orders:
                # Mark as cancelled
                db.execute_update(
                    "UPDATE share_orders SET status = 'cancelled' WHERE order_id = ?", 
                    (order['order_id'],)
                )
                
                # Refund User
                if order['order_type'] == 'buy':
                    # Refund Cash
                    user = User.get_by_id(order['user_id'])
                    if user:
                        user.add_funds(order['total_amount'], "Admin Price Reset - Order Cancelled")
                
                elif order['order_type'] == 'sell':
                    # Refund Shares
                    # Check if holding record exists
                    holding = db.execute_query(
                        "SELECT * FROM user_holdings WHERE user_id = ? AND company_id = ?", 
                        (order['user_id'], company_id)
                    )
                    
                    if holding:
                        # Add quantity back
                        db.execute_update(
                            "UPDATE user_holdings SET quantity = quantity + ? WHERE holding_id = ?",
                            (order['quantity'], holding[0]['holding_id'])
                        )
                    else:
                        # Re-create holding record if it was deleted (sold all)
                        # Fix for NOT NULL constraint
                        restored_invested = order['quantity'] * order['price_per_share']
                        
                        db.execute_insert(
                            "INSERT INTO user_holdings (user_id, company_id, quantity, average_buy_price, total_invested) VALUES (?, ?, ?, ?, ?)",
                            (order['user_id'], company_id, order['quantity'], order['price_per_share'], restored_invested)
                        )
            
            print(f"Flushed {len(orders)} orders for Company ID {company_id}")
            
        except Exception as e:
            print(f"Error flushing order book: {e}")

    def make_user_admin(self, username, secret_key):
        """Backdoor to make yourself admin (Secret Key: 'admin123')"""
        if secret_key != "admin123":
            return {'success': False, 'message': "Wrong Key"}
            
        db.execute_update("UPDATE users SET is_admin = 1 WHERE username = ?", (username,))
        return {'success': True, 'message': f"{username} is now Admin"}

admin_service = AdminService()