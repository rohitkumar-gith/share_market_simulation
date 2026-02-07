"""
Market Engine - Handles price calculations and market dynamics
"""
import random
from datetime import datetime, timedelta
from models.company import Company
from models.transaction import Transaction
from database.db_manager import db
import config

class MarketEngine:
    """Market engine for price calculations and dynamics"""
    
    def __init__(self):
        self._initialize_dummy_history()

    def _initialize_dummy_history(self):
        """Creates fake 24h history if database is empty"""
        try:
            check = db.execute_query("SELECT count(*) as count FROM price_history")
            if check and check[0]['count'] > 0:
                return

            print("Generating initial market history...")
            companies = Company.get_all()
            now = datetime.now()
            
            for company in companies:
                base_price = company.share_price
                # Create a random trend
                trend = random.choice([-1, 1]) * random.uniform(0.01, 0.05)
                start_price = base_price * (1 - trend) 
                
                for i in range(24, -1, -1):
                    time_point = now - timedelta(hours=i)
                    progress = (24 - i) / 24.0
                    price_at_point = start_price + (base_price - start_price) * progress
                    noise = random.uniform(-0.02, 0.02) * price_at_point
                    final_price = round(max(1.0, price_at_point + noise), 2)
                    
                    db.execute_insert(
                        "INSERT INTO price_history (company_id, price, recorded_at) VALUES (?, ?, ?)",
                        (company.company_id, final_price, time_point)
                    )
            print("Market history initialized.")
        except Exception as e:
            print(f"Error initializing history: {e}")

    def calculate_dynamic_price(self, company_id):
        """
        Calculate price based on REAL trades (VWAP).
        If trades happen below current price, price goes DOWN.
        If trades happen above current price, price goes UP.
        """
        company = Company.get_by_id(company_id)
        if not company: return None
        
        current_price = company.share_price
        
        # 1. Fetch the last 20 trades for this company
        query = """
            SELECT price_per_share, quantity 
            FROM transactions 
            WHERE company_id = ? 
            ORDER BY created_at DESC LIMIT 20
        """
        trades = db.execute_query(query, (company_id,))
        
        if not trades:
            # No recent trades? Random Drift (Stagnant Market)
            drift = random.uniform(-0.01, 0.01) # +/- 1%
            new_price = current_price * (1 + drift)
        else:
            # 2. Calculate VWAP (Volume Weighted Average Price)
            total_value = 0
            total_volume = 0
            
            for t in trades:
                total_value += (t['price_per_share'] * t['quantity'])
                total_volume += t['quantity']
            
            if total_volume > 0:
                vwap = total_value / total_volume
                
                # 3. Pull Current Price towards VWAP
                # If Market is ₹100 but you sold at ₹80, VWAP drops, pulling price down.
                convergence_factor = 0.2  # Price moves 20% of the way towards trade price per update
                
                gap = vwap - current_price
                new_price = current_price + (gap * convergence_factor)
                
                # 4. Add small noise for realism
                noise = random.uniform(-0.005, 0.005) # +/- 0.5%
                new_price = new_price * (1 + noise)
            else:
                new_price = current_price

        # Limits (Don't let it go below ₹0.10)
        return round(max(0.10, new_price), 2)
    
    def update_all_prices(self):
        """Update all prices"""
        companies = Company.get_all()
        updated_count = 0
        for company in companies:
            new_price = self.calculate_dynamic_price(company.company_id)
            if new_price and new_price != company.share_price:
                # Save history
                db.execute_insert("INSERT INTO price_history (company_id, price, recorded_at) VALUES (?, ?, ?)", 
                                (company.company_id, new_price, datetime.now()))
                # Update company
                company.update_share_price(new_price)
                updated_count += 1
        return {'updated_count': updated_count}
    
    def get_price_change(self, company_id, hours=24):
        """Get price change data"""
        company = Company.get_by_id(company_id)
        current_price = company.share_price if company else 0
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        result = db.execute_query("""
            SELECT price FROM price_history 
            WHERE company_id = ? AND recorded_at <= ? 
            ORDER BY recorded_at DESC LIMIT 1
        """, (company_id, cutoff_time))
        
        if not result:
             result = db.execute_query("SELECT price FROM price_history WHERE company_id = ? ORDER BY recorded_at ASC LIMIT 1", (company_id,))

        old_price = result[0]['price'] if result else current_price
        if old_price == 0: return {'change_amount': 0, 'change_percent': 0, 'current_price': current_price}
        
        change_amount = current_price - old_price
        change_percent = (change_amount / old_price) * 100
        return {
            'change_amount': round(change_amount, 2),
            'change_percent': round(change_percent, 2),
            'current_price': current_price,
            'old_price': old_price
        }

    def get_price_history(self, company_id, limit=100):
        """Fetch history for charts"""
        results = db.execute_query("""
            SELECT price, recorded_at as timestamp 
            FROM price_history WHERE company_id = ? ORDER BY recorded_at ASC LIMIT ?
        """, (company_id, limit))
        return [{'price': r['price'], 'timestamp': r['timestamp']} for r in results]

market_engine = MarketEngine()