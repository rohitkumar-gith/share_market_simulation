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
        # Market Trend State
        self.trend_type = None # 'bull' or 'bear'
        self.trend_end_time = datetime.min
        self.trend_strength = 0.0
        
        self._initialize_dummy_history()

    def set_market_trend(self, trend_type, duration_seconds, strength=0.005):
        """Set a sustained market trend (Bull/Bear)"""
        self.trend_type = trend_type
        self.trend_strength = strength
        self.trend_end_time = datetime.now() + timedelta(seconds=duration_seconds)
        print(f"Market Trend Set: {trend_type.upper()} for {duration_seconds}s")

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
        """Calculate price based on VWAP + Active Market Trends"""
        company = Company.get_by_id(company_id)
        if not company: return None
        
        current_price = company.share_price
        new_price = current_price
        
        # --- 1. Base Logic (VWAP) ---
        query = """
            SELECT price_per_share, quantity 
            FROM transactions 
            WHERE company_id = ? 
            ORDER BY created_at DESC LIMIT 20
        """
        trades = db.execute_query(query, (company_id,))
        
        if not trades:
            # Random Drift if no trades
            drift = random.uniform(-0.005, 0.005)
            new_price = current_price * (1 + drift)
        else:
            total_value = sum(t['price_per_share'] * t['quantity'] for t in trades)
            total_volume = sum(t['quantity'] for t in trades)
            
            if total_volume > 0:
                vwap = total_value / total_volume
                convergence = 0.2
                gap = vwap - current_price
                new_price = current_price + (gap * convergence)
                
                noise = random.uniform(-0.005, 0.005)
                new_price = new_price * (1 + noise)

        # --- 2. Apply Admin Market Trend (The Fix) ---
        if datetime.now() < self.trend_end_time:
            # Apply sustained pressure every tick
            if self.trend_type == 'bull':
                # Force upward movement (e.g. +0.5% to +1.5% per tick)
                boost = random.uniform(0.005, 0.015) 
                new_price = new_price * (1 + boost)
            elif self.trend_type == 'bear':
                # Force downward movement
                drop = random.uniform(0.005, 0.015)
                new_price = new_price * (1 - drop)

        return round(max(0.10, new_price), 2)
    
    def update_all_prices(self):
        """Update all prices"""
        companies = Company.get_all()
        updated_count = 0
        for company in companies:
            new_price = self.calculate_dynamic_price(company.company_id)
            if new_price and new_price != company.share_price:
                db.execute_insert("INSERT INTO price_history (company_id, price, recorded_at) VALUES (?, ?, ?)", 
                                (company.company_id, new_price, datetime.now()))
                company.update_share_price(new_price)
                updated_count += 1
        return {'updated_count': updated_count}
    
    def get_price_change(self, company_id, hours=24):
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
        results = db.execute_query("""
            SELECT price, recorded_at as timestamp 
            FROM price_history WHERE company_id = ? ORDER BY recorded_at ASC LIMIT ?
        """, (company_id, limit))
        return [{'price': r['price'], 'timestamp': r['timestamp']} for r in results]

market_engine = MarketEngine()