"""
Bot Trader - Automated trading bots to simulate market activity
"""
import random
from datetime import datetime
from models.user import User
from models.company import Company
from models.share import Share
from database.db_manager import db
from trading.market_engine import market_engine # Need this for trend analysis
from utils.constants import *
import config

class BotTrader:
    """Automated trading bot"""
    
    def __init__(self):
        self.bots = []
        self.initialized = False
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
        if not self.initialized: self.initialize_bots()
        
        companies = Company.get_all()
        if not companies: return {'trades_executed': 0}
        
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
        
        return {'trades_executed': trades_executed}

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
        
        # Decide action based on random chance
        # (Realism comes from HOW they price the order, not whether they buy/sell)
        action = 'buy' if random.random() < 0.5 else 'sell'
        
        success = False
        if action == 'buy':
            success = self._bot_buy_shares(bot_user, companies, bot['strategy'])
            if not success:
                success = self._bot_sell_shares(bot_user, companies, bot['strategy'])
        else:
            success = self._bot_sell_shares(bot_user, companies, bot['strategy'])
            if not success:
                success = self._bot_buy_shares(bot_user, companies, bot['strategy'])
                
        return success
    
    def _get_market_sentiment(self, company_id):
        """
        Analyze recent price trend.
        Returns: 'bull' (Up > 2%), 'bear' (Down > 2%), or 'neutral' (Stable)
        """
        try:
            # Check 24h change (or shorter if you have 1h logic)
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
        
        # Analyze Sentiment
        sentiment, change = self._get_market_sentiment(company.company_id)
        
        # --- PRICING LOGIC ---
        if sentiment == 'bull':
            # FOMO: Buy aggressively! Bid 1-3% ABOVE market price to catch the rally.
            price_multiplier = random.uniform(1.01, 1.03)
        elif sentiment == 'bear':
            # Vulture: Buy cheap. Bid 2-5% BELOW market price (catching the knife).
            price_multiplier = random.uniform(0.95, 0.98)
        else:
            # Neutral/IPO: Standard fair value bid.
            price_multiplier = random.uniform(1.00, 1.01)

        bid_price = round(company.share_price * price_multiplier, 2)
        
        # Quantity Logic
        max_affordable = int(bot_user.wallet_balance / bid_price)
        if max_affordable < 1: return False
        max_qty = min(max_affordable, 100) # Cap at 100 shares per order
        quantity = random.randint(1, max(1, max_qty))
        
        # 1. Check User Sell Orders (Secondary Market)
        try:
            from services.trading_service import trading_service
            # Look for a seller close to our target price
            trading_service.create_buy_order(bot_user.user_id, company.company_id, quantity, bid_price)
            return True
        except: pass
        
        # 2. IPO Fallback (Only if Neutral/Bull and IPO is available)
        if company.available_shares >= quantity and bid_price >= company.share_price:
            try:
                Share.buy_from_ipo(bot_user.user_id, company.company_id, quantity)
                return True
            except: pass
            
        return False
    
    def _bot_sell_shares(self, bot_user, companies, strategy):
        """Smart Selling Logic"""
        holdings = db.get_user_holdings(bot_user.user_id)
        if not holdings: return False
        
        # Pick a holding
        holding = random.choice(holdings)
        company = Company.get_by_id(holding['company_id'])
        if not company: return False

        # Analyze Sentiment
        sentiment, change = self._get_market_sentiment(company.company_id)
        
        # --- PRICING LOGIC ---
        if sentiment == 'bull':
            # Greed: Everyone wants this stock. Ask for MORE.
            # Sell at 2-5% ABOVE market price.
            price_multiplier = random.uniform(1.02, 1.05)
            
        elif sentiment == 'bear':
            # Panic: Dump it! Undercut market by 1-3% to sell fast.
            price_multiplier = random.uniform(0.97, 0.99)
            
        else:
            # Neutral/IPO Fix: DO NOT UNDERCUT.
            # Ask for a small profit (0.5% - 2% gain).
            price_multiplier = random.uniform(1.005, 1.02)

        sell_price = round(company.share_price * price_multiplier, 2)
        
        sell_percentage = random.uniform(0.1, 0.5)
        quantity = max(1, int(holding['quantity'] * sell_percentage))
        
        try:
            from services.trading_service import trading_service
            trading_service.create_sell_order(bot_user.user_id, holding['company_id'], quantity, sell_price)
            return True
        except: return False
    
    def _select_company_to_buy(self, companies, strategy):
        """Select company, heavily weighted by momentum"""
        if not companies: return None
        
        # Sort companies by momentum (price change)
        # Using a simple proxy: (current_price / initial_price or just raw price for now)
        # Better: Sort by recent activity if possible, or just price.
        
        if strategy == BOT_STRATEGY_MOMENTUM:
            # Prefer expensive/rising stocks
            sorted_companies = sorted(companies, key=lambda c: c.share_price, reverse=True)
            weights = [1.0 / (i + 1) for i in range(len(sorted_companies))]
            return random.choices(sorted_companies, weights=weights)[0]
            
        elif strategy == BOT_STRATEGY_VALUE:
            # Prefer cheap stocks
            sorted_companies = sorted(companies, key=lambda c: c.share_price)
            weights = [1.0 / (i + 1) for i in range(len(sorted_companies))]
            return random.choices(sorted_companies, weights=weights)[0]
            
        return random.choice(companies)

    # --- Admin Helpers ---
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