"""
Bot Trader - Automated trading bots to simulate market activity
"""
import random
from datetime import datetime
from models.user import User
from models.company import Company
from models.share import Share
from database.db_manager import db
from trading.market_engine import market_engine 
from utils.constants import *
import config

class BotTrader:
    """Automated trading bot"""
    
    def __init__(self):
        self.bots = []
        self.initialized = False
        self.is_processing = False # Thread Safety Flag
        # Realistic Names
        self.bot_names = [
            "Arjun Mehta", "Priya Sharma", "Rahul Verma", 
            "Anjali Gupta", "Vikram Singh", "Sneha Patel", "Rohan Das",
            "Kavita Reddy", "Amit Joshi", "Pooja Malhotra"
        ]
    
    def initialize_bots(self, count=None):
        """Initialize trading bots"""
        if self.initialized: return
        
        # Force count to 10 if not specified
        if count is None: count = 10
        
        existing_bots = db.execute_query("SELECT * FROM bots")
        if existing_bots:
            self.bots = [dict(bot) for bot in existing_bots]
            self.initialized = True
            print(f"Loaded {len(self.bots)} existing trading bots")
            return
        
        strategies = [BOT_STRATEGY_RANDOM, BOT_STRATEGY_MOMENTUM, BOT_STRATEGY_VALUE]
        
        for i in range(count):
            if i < len(self.bot_names):
                full_name = self.bot_names[i]
                username = full_name.replace(" ", "") + "Bot"
            else:
                full_name = f"Trader {i+1}"
                username = f"TradingBot{i+1}"
            
            strategy = strategies[i % len(strategies)]
            
            bot_user = User.get_by_username(username)
            if not bot_user:
                try:
                    bot_user = User.register(
                        username=username,
                        password=f"bot_pass_{i+1}",
                        email=f"{username.lower()}@market.sim",
                        full_name=full_name
                    )
                except Exception as e:
                    print(f"Error creating user for bot {username}: {e}")
                    continue
            
            try:
                bot_id = db.execute_insert(
                    """INSERT INTO bots (bot_name, user_id, wallet_balance, strategy, is_active)
                       VALUES (?, ?, ?, ?, ?)""",
                    (full_name, bot_user.user_id, config.BOT_INITIAL_BALANCE, strategy, 1)
                )
                self.bots.append({
                    'bot_id': bot_id, 'bot_name': full_name, 'user_id': bot_user.user_id,
                    'wallet_balance': config.BOT_INITIAL_BALANCE, 'strategy': strategy, 'is_active': 1
                })
            except Exception as e:
                print(f"Error initializing bot {username} in DB: {e}")
        
        self.initialized = True
        print(f"Initialized bots")
    
    def execute_bot_trades(self):
        """Execute trades for all active bots"""
        if self.is_processing: return {'trades_executed': 0}
        self.is_processing = True
        
        try:
            if not self.initialized: self.initialize_bots()
            
            companies = Company.get_all()
            if not companies: 
                self.is_processing = False
                return {'trades_executed': 0}
            
            trades_executed = 0
            
            for bot in self.bots:
                if not bot['is_active']: continue
                
                # 100% Activity Rate (Fast Market)
                try:
                    result = self._execute_single_bot_trade(bot, companies)
                    if result: trades_executed += 1
                except Exception as e:
                    print(f"Bot trade error: {e}")
                    continue
            
            self.is_processing = False
            return {'trades_executed': trades_executed}
            
        except Exception as e:
            self.is_processing = False
            print(f"Critical Bot Error: {e}")
            return {'trades_executed': 0}

    def force_market_scan(self):
        """Force bots to react instantly to new user orders"""
        if not self.initialized: self.initialize_bots()
        companies = Company.get_all()
        if not companies: return
        
        for bot in self.bots:
            if not bot['is_active']: continue
            bot_user = User.get_by_id(bot['user_id'])
            if not bot_user: continue
            
            self._bot_sell_shares(bot_user, companies, bot['strategy'])
            self._bot_buy_shares(bot_user, companies, bot['strategy'])

    def _execute_single_bot_trade(self, bot, companies):
        """Execute a trade based on market conditions"""
        bot_user = User.get_by_id(bot['user_id'])
        if not bot_user: return False
        
        # --- NEW: Check Global Admin Trend ---
        # If Admin triggered a Crash or Bull Run, SKEW the probability!
        is_crash = (market_engine.trend_type == 'bear' and datetime.now() < market_engine.trend_end_time)
        is_bull_run = (market_engine.trend_type == 'bull' and datetime.now() < market_engine.trend_end_time)
        
        action = 'buy'
        
        if is_crash:
            # PANIC: 90% chance to SELL, only 10% chance to BUY (Vultures)
            action = 'sell' if random.random() < 0.90 else 'buy'
        elif is_bull_run:
            # FOMO: 90% chance to BUY, only 10% chance to SELL (Profit Taking)
            action = 'buy' if random.random() < 0.90 else 'sell'
        else:
            # Normal Market: 50/50 Split
            action = 'buy' if random.random() < 0.5 else 'sell'
        
        success = False
        if action == 'buy':
            success = self._bot_buy_shares(bot_user, companies, bot['strategy'])
            if not success and not is_crash: # Don't fallback to sell in normal times
                success = self._bot_sell_shares(bot_user, companies, bot['strategy'])
        else:
            success = self._bot_sell_shares(bot_user, companies, bot['strategy'])
            if not success and not is_bull_run:
                success = self._bot_buy_shares(bot_user, companies, bot['strategy'])
                
        return success
    
    def _get_market_sentiment(self, company_id):
        """Analyze recent price trend."""
        # 1. Check Global Admin Event First
        if datetime.now() < market_engine.trend_end_time:
            if market_engine.trend_type == 'bull': return 'bull', 10.0
            if market_engine.trend_type == 'bear': return 'bear', -10.0

        # 2. Local History Check
        try:
            data = market_engine.get_price_change(company_id, hours=1) 
            change = data.get('change_percent', 0)
            if change >= 2.0: return 'bull', change
            if change <= -2.0: return 'bear', change
            return 'neutral', change
        except:
            return 'neutral', 0

    def _bot_buy_shares(self, bot_user, companies, strategy):
        """Smart Buying Logic"""
        company_data = self._select_company_to_buy(companies, strategy)
        if not company_data: return False
        
        company = Company.get_by_id(company_data.company_id)
        if not company or company.share_price <= 0: return False
        
        sentiment, change = self._get_market_sentiment(company.company_id)
        
        # Check Global Events for Aggressive Pricing
        is_crash = (market_engine.trend_type == 'bear' and datetime.now() < market_engine.trend_end_time)
        is_bull = (market_engine.trend_type == 'bull' and datetime.now() < market_engine.trend_end_time)

        # Quantity Logic
        max_affordable = int(bot_user.wallet_balance / company.share_price)
        if max_affordable < 1: return False
        quantity = random.randint(1, min(max_affordable, 100))

        # --- PRICING LOGIC ---
        if is_crash:
            # CRASH MODE: Vulture Buying Only
            # Only buy if price is 15-25% BELOW market.
            price_multiplier = random.uniform(0.75, 0.85)
            
        elif is_bull:
            # BULL MODE: FOMO Buying
            # Bid 5-15% ABOVE market to catch the rocket.
            price_multiplier = random.uniform(1.05, 1.15)
            
        elif sentiment == 'bull':
            price_multiplier = random.uniform(1.01, 1.03) # Normal Uptrend
        elif sentiment == 'bear':
            price_multiplier = random.uniform(0.95, 0.98) # Normal Downtrend
        else:
            price_multiplier = random.uniform(1.00, 1.01) # Neutral

        bid_price = round(company.share_price * price_multiplier, 2)
        
        # --- EXECUTE ---
        
        # 1. Secondary Market (User Sells)
        # In a crash, we only buy if the seller is desperate (matches our low bid)
        best_sell_order = db.execute_query(
            "SELECT * FROM share_orders WHERE company_id = ? AND order_type = 'sell' AND status = 'pending' ORDER BY price_per_share ASC LIMIT 1",
            (company.company_id,)
        )
        
        if best_sell_order:
            sell_order = best_sell_order[0]
            ask_price = sell_order['price_per_share']
            
            # Will we pay this price?
            if ask_price <= bid_price: 
                try:
                    from services.trading_service import trading_service
                    buy_qty = min(quantity, sell_order['quantity'])
                    trading_service.create_buy_order(bot_user.user_id, company.company_id, buy_qty, ask_price)
                    return True
                except: pass

        # 2. IPO (Rare during crash)
        if company.available_shares >= quantity and not is_crash:
            try:
                Share.buy_from_ipo(bot_user.user_id, company.company_id, quantity)
                return True
            except: pass

        # 3. Limit Order (The Lowball Bid)
        try:
            from services.trading_service import trading_service
            trading_service.create_buy_order(bot_user.user_id, company.company_id, quantity, bid_price)
            return True
        except: return False
    
    def _bot_sell_shares(self, bot_user, companies, strategy):
        """Smart Selling Logic"""
        holdings = db.get_user_holdings(bot_user.user_id)
        if not holdings: return False
        
        holding = random.choice(holdings)
        company = Company.get_by_id(holding['company_id'])
        if not company: return False

        sentiment, change = self._get_market_sentiment(company.company_id)
        
        is_crash = (market_engine.trend_type == 'bear' and datetime.now() < market_engine.trend_end_time)
        is_bull = (market_engine.trend_type == 'bull' and datetime.now() < market_engine.trend_end_time)

        # --- PRICING LOGIC ---
        if is_crash:
            # CRASH MODE: Panic Sell!
            # Undercut market by 10-20% to get out FAST.
            price_multiplier = random.uniform(0.80, 0.90)
            quantity = holding['quantity'] # Sell ALL or most
            
        elif is_bull:
            # BULL MODE: Greed
            # Ask for 10-20% MORE.
            price_multiplier = random.uniform(1.10, 1.20)
            quantity = max(1, int(holding['quantity'] * 0.1)) # Sell small amounts
            
        elif sentiment == 'bull':
            price_multiplier = random.uniform(1.02, 1.05)
            quantity = max(1, int(holding['quantity'] * 0.2))
        elif sentiment == 'bear':
            price_multiplier = random.uniform(0.97, 0.99)
            quantity = max(1, int(holding['quantity'] * 0.3))
        else:
            price_multiplier = random.uniform(1.005, 1.02)
            quantity = max(1, int(holding['quantity'] * 0.1))

        sell_price = round(company.share_price * price_multiplier, 2)
        
        # --- EXECUTE ---
        
        # 1. Check User Buys (Exit Liquidity)
        best_buy_order = db.execute_query(
            "SELECT * FROM share_orders WHERE company_id = ? AND order_type = 'buy' AND status = 'pending' ORDER BY price_per_share DESC LIMIT 1",
            (company.company_id,)
        )

        if best_buy_order:
            buy_order = best_buy_order[0]
            buyer_price = buy_order['price_per_share']
            
            # If panic selling (crash), take ANY price that isn't near zero
            acceptable_price = sell_price
            if is_crash: acceptable_price = company.share_price * 0.50 # Desperate
            
            if buyer_price >= acceptable_price:
                sell_qty = min(quantity, buy_order['quantity'])
                try:
                    from services.trading_service import trading_service
                    trading_service.create_sell_order(bot_user.user_id, company.company_id, sell_qty, buyer_price)
                    return True
                except: pass

        # 2. Limit Sell Order
        try:
            from services.trading_service import trading_service
            trading_service.create_sell_order(bot_user.user_id, holding['company_id'], quantity, sell_price)
            return True
        except: return False
    
    def _select_company_to_buy(self, companies, strategy):
        """Select company based on strategy"""
        if not companies: return None
        if strategy == BOT_STRATEGY_RANDOM: return random.choice(companies)
        elif strategy == BOT_STRATEGY_MOMENTUM:
            sorted_companies = sorted(companies, key=lambda c: c.share_price, reverse=True)
            weights = [1.0 / (i + 1) for i in range(len(sorted_companies))]
            return random.choices(sorted_companies, weights=weights)[0]
        elif strategy == BOT_STRATEGY_VALUE:
            sorted_companies = sorted(companies, key=lambda c: c.share_price)
            weights = [1.0 / (i + 1) for i in range(len(sorted_companies))]
            return random.choices(sorted_companies, weights=weights)[0]
        return random.choice(companies)

    def get_bot_statistics(self):
        stats = []
        for bot in self.bots:
            bot_user = User.get_by_id(bot['user_id'])
            if not bot_user: continue
            portfolio = bot_user.get_portfolio()
            stats.append({
                'bot_name': bot['bot_name'],
                'strategy': bot['strategy'],
                'wallet_balance': bot_user.wallet_balance,
                'portfolio_value': portfolio['total_current_value'],
                'total_value': bot_user.wallet_balance + portfolio['total_current_value'],
                'profit_loss': portfolio['total_profit_loss'],
                'is_active': bot['is_active']
            })
        return stats
    
    def toggle_bot(self, bot_id, active):
        db.execute_update("UPDATE bots SET is_active = ? WHERE bot_id = ?", (1 if active else 0, bot_id))
        for bot in self.bots:
            if bot['bot_id'] == bot_id:
                bot['is_active'] = 1 if active else 0
                break

    def reset_bot_balances(self):
        for bot in self.bots:
            bot_user = User.get_by_id(bot['user_id'])
            if bot_user:
                db.execute_update("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (config.BOT_INITIAL_BALANCE, bot_user.user_id))
                db.execute_update("DELETE FROM user_holdings WHERE user_id = ?", (bot_user.user_id,))

bot_trader = BotTrader()