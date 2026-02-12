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
        self.trend_type = 'neutral' # 'bull', 'bear', or 'neutral'
        self.trend_end_time = datetime.min
        self.trend_step_multiplier = 1.0
        self.trend_intensity = 0.0 # Added for Bots to read
        
        # Initialize history on startup so charts aren't empty
        self._initialize_dummy_history()

    def set_market_trend(self, trend_type, duration_seconds, target_percent):
        """
        Set a specific market movement target.
        target_percent: e.g., 10.0 for +10%, -5.0 for -5%
        """
        self.trend_type = trend_type
        self.trend_end_time = datetime.now() + timedelta(seconds=duration_seconds)
        
        # Set intensity for Bots
        if trend_type == 'bull': self.trend_intensity = 0.05
        elif trend_type == 'bear': self.trend_intensity = -0.05
        else: self.trend_intensity = 0.0
        
        # Calculate Step Multiplier
        # The market updates every 10 seconds (defined in main_window timers)
        updates_per_minute = 6
        total_ticks = (duration_seconds / 60) * updates_per_minute
        total_ticks = max(1, int(total_ticks))
        
        # Target Multiplier (e.g., +10% = 1.10)
        target_multiplier = 1 + (target_percent / 100.0)
        
        # Calculate per-tick multiplier using root: step = target^(1/ticks)
        self.trend_step_multiplier = target_multiplier ** (1 / total_ticks)
        
        print(f"Market Trend Set: {trend_type.upper()} ({target_percent}%) for {duration_seconds}s. Step: {self.trend_step_multiplier:.6f}")

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
                # Random trend for the last 24h
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
        
        # --- 1. Base Logic (VWAP - Volume Weighted Average Price) ---
        query = """
            SELECT price_per_share, quantity 
            FROM transactions 
            WHERE company_id = ? 
            ORDER BY created_at DESC LIMIT 20
        """
        trades = db.execute_query(query, (company_id,))
        
        if not trades:
            # No recent trades: Random drift
            drift = random.uniform(-0.005, 0.005)
            new_price = current_price * (1 + drift)
        else:
            total_value = sum(t['price_per_share'] * t['quantity'] for t in trades)
            total_volume = sum(t['quantity'] for t in trades)
            
            if total_volume > 0:
                vwap = total_value / total_volume
                convergence = 0.2 # Pull price 20% towards VWAP
                gap = vwap - current_price
                new_price = current_price + (gap * convergence)
                
                # Add noise
                noise = random.uniform(-0.005, 0.005)
                new_price = new_price * (1 + noise)

        # --- 2. Apply Targeted Market Trend (Admin Control) ---
        if datetime.now() < self.trend_end_time:
            # Apply the calculated geometric step
            if self.trend_step_multiplier != 1.0:
                new_price = new_price * self.trend_step_multiplier
        else:
            # Reset trend if expired
            if self.trend_type != 'neutral':
                self.trend_type = 'neutral'
                self.trend_step_multiplier = 1.0
                self.trend_intensity = 0.0

        return round(max(0.10, new_price), 2)
    
    def update_all_prices(self):
        """Update all prices (Called by Main Window Timer)"""
        companies = Company.get_all()
        updated_count = 0
        
        for company in companies:
            new_price = self.calculate_dynamic_price(company.company_id)
            
            # Use a threshold to avoid spamming DB with 0.000001 changes
            if new_price and abs(new_price - company.share_price) > 0.001:
                # 1. Update History
                db.execute_insert(
                    "INSERT INTO price_history (company_id, price, recorded_at) VALUES (?, ?, ?)", 
                    (company.company_id, new_price, datetime.now())
                )
                # 2. Update Current Price
                db.execute_update(
                    "UPDATE companies SET share_price = ? WHERE company_id = ?",
                    (new_price, company.company_id)
                )
                updated_count += 1
                
        return {'updated_count': updated_count}
    
    def get_price_change(self, company_id, hours=24):
        """Get percentage change for UI"""
        company = Company.get_by_id(company_id)
        current_price = company.share_price if company else 0
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        result = db.execute_query("""
            SELECT price FROM price_history 
            WHERE company_id = ? AND recorded_at <= ? 
            ORDER BY recorded_at DESC LIMIT 1
        """, (company_id, cutoff_time))
        
        # Fallback if no history > 24h old
        if not result:
             result = db.execute_query("SELECT price FROM price_history WHERE company_id = ? ORDER BY recorded_at ASC LIMIT 1", (company_id,))

        old_price = result[0]['price'] if result else current_price
        
        if old_price == 0: 
            return {'change_amount': 0, 'change_percent': 0, 'current_price': current_price}
        
        change_amount = current_price - old_price
        change_percent = (change_amount / old_price) * 100
        
        return {
            'change_amount': round(change_amount, 2),
            'change_percent': round(change_percent, 2),
            'current_price': current_price,
            'old_price': old_price
        }

    def get_price_history(self, company_id, limit=100):
        """Get data for charts"""
        results = db.execute_query("""
            SELECT price, recorded_at as timestamp 
            FROM price_history WHERE company_id = ? ORDER BY recorded_at ASC LIMIT ?
        """, (company_id, limit))
        return [{'price': r['price'], 'timestamp': r['timestamp']} for r in results]

market_engine = MarketEngine()