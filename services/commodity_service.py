"""
Commodity Service - Handles the global Bullion Exchange with Stock Market Correlation
"""
from database.db_manager import db
from models.user import User
import random

class CommodityService:
    def __init__(self):
        """Auto-patch the database to support physical commodities"""
        self.last_stock_market_avg = None # Used to track if the stock market is crashing or booming

        try:
            db.execute_update("""
                CREATE TABLE IF NOT EXISTS commodities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    symbol TEXT UNIQUE NOT NULL,
                    current_price REAL NOT NULL,
                    volatility REAL NOT NULL,
                    color TEXT
                )
            """)
            db.execute_update("""
                CREATE TABLE IF NOT EXISTS user_commodities (
                    user_id INTEGER NOT NULL,
                    commodity_id INTEGER NOT NULL,
                    quantity REAL NOT NULL DEFAULT 0,
                    average_buy_price REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id, commodity_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (commodity_id) REFERENCES commodities(id)
                )
            """)
            
            # Seed the initial metals if the table is empty
            count = db.execute_query("SELECT COUNT(*) as c FROM commodities")[0]['c']
            if count == 0:
                db.execute_insert("INSERT INTO commodities (name, symbol, current_price, volatility, color) VALUES (?, ?, ?, ?, ?)", ('Gold', 'XAU', 6500.0, 0.008, '#FFD700'))
                db.execute_insert("INSERT INTO commodities (name, symbol, current_price, volatility, color) VALUES (?, ?, ?, ?, ?)", ('Silver', 'XAG', 85.0, 0.015, '#C0C0C0'))
                db.execute_insert("INSERT INTO commodities (name, symbol, current_price, volatility, color) VALUES (?, ?, ?, ?, ?)", ('Platinum', 'XPT', 2800.0, 0.012, '#E5E4E2'))
                db.execute_insert("INSERT INTO commodities (name, symbol, current_price, volatility, color) VALUES (?, ?, ?, ?, ?)", ('Palladium', 'XPD', 2500.0, 0.020, '#9AC4DD'))
        except Exception as e:
            pass

    def get_market_prices(self):
        """Get live prices of all metals"""
        return db.execute_query("SELECT * FROM commodities ORDER BY current_price DESC") or []

    def get_user_vault(self, user_id):
        """Get the metals currently owned by a user"""
        query = """
            SELECT uc.quantity, uc.average_buy_price, c.name, c.symbol, c.current_price, c.color, c.id as commodity_id
            FROM user_commodities uc
            JOIN commodities c ON uc.commodity_id = c.id
            WHERE uc.user_id = ? AND uc.quantity > 0
        """
        return db.execute_query(query, (user_id,)) or []

    def update_market_prices(self):
        """Fluctuate commodity prices with realistic stock market correlation"""
        
        # 1. Calculate the overall trend of the Stock Market
        stock_trend = 0.0
        try:
            res = db.execute_query("SELECT AVG(share_price) as avg_price FROM companies")
            if res and res[0]['avg_price']:
                current_avg = res[0]['avg_price']
                if self.last_stock_market_avg:
                    # Calculate percentage change in the stock market (e.g., -0.05 means a 5% crash)
                    stock_trend = (current_avg - self.last_stock_market_avg) / self.last_stock_market_avg
                self.last_stock_market_avg = current_avg
        except:
            pass

        # 2. Apply updates to the Commodities Market
        commodities = self.get_market_prices()
        for c in commodities:
            # Base RNG walk (normal market noise)
            base_change = random.uniform(-c['volatility'], c['volatility'])
            
            # 3. Apply the Real-World Economic Multiplier
            market_bias = 0.0
            
            if c['symbol'] == 'XAU': # GOLD: Ultimate safe haven. Inverse to stocks.
                market_bias = stock_trend * -0.60 
            elif c['symbol'] == 'XAG': # SILVER: Partial safe haven.
                market_bias = stock_trend * -0.30
            elif c['symbol'] in ['XPT', 'XPD']: # PLATINUM/PALLADIUM: Industrial. Moves WITH stocks.
                market_bias = stock_trend * 0.40 
            
            # Combine random noise with the economic bias
            final_change = base_change + market_bias
            
            new_price = c['current_price'] * (1 + final_change)
            new_price = max(1.0, round(new_price, 2)) # Prevent crashing to zero
            
            db.execute_update("UPDATE commodities SET current_price = ? WHERE id = ?", (new_price, c['id']))

    def buy_metal(self, user_id, commodity_id, quantity_grams):
        try:
            if quantity_grams <= 0: return {'success': False, 'message': "Quantity must be greater than zero."}
            
            user = User.get_by_id(user_id)
            metals = db.execute_query("SELECT * FROM commodities WHERE id = ?", (commodity_id,))
            if not metals: return {'success': False, 'message': "Metal not found."}
            metal = metals[0]
            
            total_cost = metal['current_price'] * quantity_grams
            
            if user.wallet_balance < total_cost:
                return {'success': False, 'message': f"Insufficient funds. You need ₹{total_cost:,.2f}"}
                
            # Deduct funds
            user.withdraw_funds(total_cost, f"Bought {quantity_grams}g of {metal['name']}")
            
            # Add to vault
            existing = db.execute_query("SELECT * FROM user_commodities WHERE user_id = ? AND commodity_id = ?", (user_id, commodity_id))
            if existing:
                old_qty = existing[0]['quantity']
                old_avg = existing[0]['average_buy_price']
                new_qty = old_qty + quantity_grams
                new_avg = ((old_qty * old_avg) + total_cost) / new_qty
                db.execute_update("UPDATE user_commodities SET quantity = ?, average_buy_price = ? WHERE user_id = ? AND commodity_id = ?", (new_qty, new_avg, user_id, commodity_id))
            else:
                db.execute_insert("INSERT INTO user_commodities (user_id, commodity_id, quantity, average_buy_price) VALUES (?, ?, ?, ?)", (user_id, commodity_id, quantity_grams, metal['current_price']))
                
            return {'success': True, 'message': f"Successfully secured {quantity_grams}g of {metal['name']} in your vault!"}
        except Exception as e: return {'success': False, 'message': str(e)}

    def sell_metal(self, user_id, commodity_id, quantity_grams):
        try:
            if quantity_grams <= 0: return {'success': False, 'message': "Quantity must be greater than zero."}
            
            existing = db.execute_query("SELECT * FROM user_commodities WHERE user_id = ? AND commodity_id = ?", (user_id, commodity_id))
            if not existing or existing[0]['quantity'] < quantity_grams:
                return {'success': False, 'message': "You don't have enough of this metal in your vault."}
                
            metals = db.execute_query("SELECT * FROM commodities WHERE id = ?", (commodity_id,))
            metal = metals[0]
            
            total_revenue = metal['current_price'] * quantity_grams
            
            # Update vault
            new_qty = existing[0]['quantity'] - quantity_grams
            db.execute_update("UPDATE user_commodities SET quantity = ? WHERE user_id = ? AND commodity_id = ?", (new_qty, user_id, commodity_id))
            
            # Add funds
            user = User.get_by_id(user_id)
            user.add_funds(total_revenue, f"Sold {quantity_grams}g of {metal['name']}")
            
            return {'success': True, 'message': f"Liquidated {quantity_grams}g of {metal['name']} for ₹{total_revenue:,.2f}!"}
        except Exception as e: return {'success': False, 'message': str(e)}

commodity_service = CommodityService()