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

# Define new strategies to augment existing ones
BOT_STRATEGY_WHALE = 'whale'
BOT_STRATEGY_PANIC = 'panic'
BOT_STRATEGY_INCOME = 'income' # NEW: Dividend Hunter

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
        
        # Added new intelligent strategies including Income
        strategies = [
            BOT_STRATEGY_RANDOM, BOT_STRATEGY_MOMENTUM, 
            BOT_STRATEGY_VALUE, BOT_STRATEGY_WHALE, 
            BOT_STRATEGY_PANIC, BOT_STRATEGY_INCOME
        ]
        
        for i in range(count):
            if i < len(self.bot_names):
                full_name = self.bot_names[i]
                username = full_name.replace(" ", "") + "Bot"
            else:
                full_name = f"Trader {i+1}"
                username = f"TradingBot{i+1}"
            
            strategy = strategies[i % len(strategies)]
            
            # Whales need more starting capital to manipulate the market
            # Giving all bots a much higher baseline starting cash!
            base_cash = max(config.BOT_INITIAL_BALANCE, 1000000) 
            initial_balance = base_cash * 5 if strategy == BOT_STRATEGY_WHALE else base_cash

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
            
            # Update user balance for whales
            db.execute_update("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (initial_balance, bot_user.user_id))
            
            try:
                bot_id = db.execute_insert(
                    """INSERT INTO bots (bot_name, user_id, wallet_balance, strategy, is_active)
                       VALUES (?, ?, ?, ?, ?)""",
                    (full_name, bot_user.user_id, initial_balance, strategy, 1)
                )
                self.bots.append({
                    'bot_id': bot_id, 'bot_name': full_name, 'user_id': bot_user.user_id,
                    'wallet_balance': initial_balance, 'strategy': strategy, 'is_active': 1
                })
            except Exception as e:
                print(f"Error initializing bot {username} in DB: {e}")
        
        self.initialized = True
        print(f"Initialized bots")

    def _shout_in_chat(self, user_id, username, message):
        """Allows bots to manipulate the market socially via chat"""
        try:
            db.execute_insert(
                "INSERT INTO chat_messages (user_id, username, message) VALUES (?, ?, ?)",
                (user_id, username, message)
            )
        except Exception as e:
            print(f"Bot chat error: {e}")
            
    def _get_active_dividend(self, company_id):
        """Check if a company has an upcoming dividend payment"""
        query = "SELECT * FROM dividends WHERE company_id = ? AND status = 'declared' ORDER BY record_date DESC LIMIT 1"
        res = db.execute_query(query, (company_id,))
        return res[0] if res else None
    
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
        
        # --- INSTITUTIONAL BAILOUT (QUANTITATIVE EASING) ---
        # If the bot drops below ₹50,000, inject ₹500,000 of fresh capital
        if bot_user.wallet_balance < 50000:
            bailout_amount = 500000
            new_balance = bot_user.wallet_balance + bailout_amount
            db.execute_update("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_balance, bot_user.user_id))
            db.execute_insert(
                "INSERT INTO wallet_transactions (user_id, transaction_type, amount, balance_after, description) VALUES (?, 'REVENUE', ?, ?, ?)",
                (bot_user.user_id, bailout_amount, new_balance, "Institutional Capital Injection")
            )
            bot_user.wallet_balance = new_balance # Update local object for the rest of the turn
        # ---------------------------------------------------

        # Check Global Admin Trend
        is_crash = (market_engine.trend_type == 'bear' and datetime.now() < market_engine.trend_end_time)
        is_bull_run = (market_engine.trend_type == 'bull' and datetime.now() < market_engine.trend_end_time)
        
        # Strategy Overrides
        if bot['strategy'] == BOT_STRATEGY_PANIC and is_crash:
            return self._bot_sell_shares(bot_user, companies, bot['strategy'])
        if bot['strategy'] == BOT_STRATEGY_WHALE and is_bull_run:
            return self._bot_buy_shares(bot_user, companies, bot['strategy'])

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
            if not success and not is_crash: 
                success = self._bot_sell_shares(bot_user, companies, bot['strategy'])
        else:
            success = self._bot_sell_shares(bot_user, companies, bot['strategy'])
            if not success and not is_bull_run:
                success = self._bot_buy_shares(bot_user, companies, bot['strategy'])
                
        return success
    
    def _get_market_sentiment(self, company_id):
        """Analyze recent price trend using Technical Analysis (Moving Averages)."""
        if datetime.now() < market_engine.trend_end_time:
            if market_engine.trend_type == 'bull': return 'bull', 10.0
            if market_engine.trend_type == 'bear': return 'bear', -10.0

        try:
            history = market_engine.get_price_history(company_id, limit=20)
            if len(history) >= 10:
                short_sma = sum(h['price'] for h in history[-5:]) / 5
                long_sma = sum(h['price'] for h in history[-10:]) / 10
                change = ((short_sma - long_sma) / long_sma) * 100
                
                if short_sma > long_sma * 1.01: return 'bull', change
                if short_sma < long_sma * 0.99: return 'bear', change
                
            data = market_engine.get_price_change(company_id, hours=1) 
            change = data.get('change_percent', 0)
            if change >= 2.0: return 'bull', change
            if change <= -2.0: return 'bear', change
            
            return 'neutral', change
        except:
            return 'neutral', 0

    def _bot_buy_shares(self, bot_user, companies, strategy):
        """Smart Buying Logic with Position Sizing"""
        company_data = self._select_company_to_buy(companies, strategy)
        if not company_data: return False
        
        company = Company.get_by_id(company_data.company_id)
        if not company or company.share_price <= 0: return False
        
        sentiment, change = self._get_market_sentiment(company.company_id)
        active_dividend = self._get_active_dividend(company.company_id)
        
        is_crash = (market_engine.trend_type == 'bear' and datetime.now() < market_engine.trend_end_time)
        is_bull = (market_engine.trend_type == 'bull' and datetime.now() < market_engine.trend_end_time)

        # --- POSITION SIZING LOGIC (The 10% Rule) ---
        # Whales can spend up to 25% of their wallet, Normal bots only 10%
        max_spend_percent = 0.25 if strategy == BOT_STRATEGY_WHALE else 0.10
        allocated_cash = bot_user.wallet_balance * max_spend_percent
        
        # Calculate max shares they can afford with their allocated budget, NOT their full wallet
        max_affordable = int(allocated_cash / company.share_price)
        
        if max_affordable < 1: return False # Cannot afford even 1 share with their budget
        
        if strategy == BOT_STRATEGY_WHALE:
            quantity = random.randint(max(1, int(max_affordable * 0.5)), max_affordable)
        elif strategy == BOT_STRATEGY_VALUE and sentiment != 'bear':
            quantity = random.randint(max(1, int(max_affordable * 0.2)), int(max_affordable * 0.5))
        elif strategy == BOT_STRATEGY_INCOME and active_dividend:
            quantity = random.randint(max(1, int(max_affordable * 0.6)), max_affordable)
        else:
            quantity = random.randint(1, min(max_affordable, 100))

        # --- PRICING LOGIC ---
        if is_crash:
            price_multiplier = random.uniform(0.75, 0.85) # Vulture bid
        elif active_dividend:
            price_multiplier = random.uniform(1.05, 1.15)
        elif is_bull or strategy == BOT_STRATEGY_WHALE:
            price_multiplier = random.uniform(1.05, 1.15)
        elif sentiment == 'bull':
            price_multiplier = random.uniform(1.01, 1.03) 
        elif sentiment == 'bear':
            price_multiplier = random.uniform(0.95, 0.98) 
        else:
            price_multiplier = random.uniform(1.00, 1.01) 

        bid_price = round(company.share_price * price_multiplier, 2)
        
        # --- EXECUTE ---
        success = False
        
        best_sell_order = db.execute_query(
            "SELECT * FROM share_orders WHERE company_id = ? AND order_type = 'sell' AND status = 'pending' ORDER BY price_per_share ASC LIMIT 1",
            (company.company_id,)
        )
        
        if best_sell_order:
            sell_order = best_sell_order[0]
            ask_price = sell_order['price_per_share']
            if ask_price <= bid_price: 
                try:
                    from services.trading_service import trading_service
                    buy_qty = min(quantity, sell_order['quantity'])
                    trading_service.create_buy_order(bot_user.user_id, company.company_id, buy_qty, ask_price)
                    success = True
                except: pass

        if not success and company.available_shares >= quantity and not is_crash:
            try:
                Share.buy_from_ipo(bot_user.user_id, company.company_id, quantity)
                success = True
            except: pass

        if not success:
            try:
                from services.trading_service import trading_service
                trading_service.create_buy_order(bot_user.user_id, company.company_id, quantity, bid_price)
                success = True
            except: pass
            
        if success:
            msg = None
            if active_dividend and strategy in [BOT_STRATEGY_INCOME, BOT_STRATEGY_WHALE]:
                msg = f"Loading up on ${company.ticker_symbol} before the dividend payout! Easy passive income! 💸"
            elif strategy == BOT_STRATEGY_WHALE and quantity >= 50:
                msg = random.choice([
                    f"Just accumulated a massive position in ${company.ticker_symbol}. Watch the charts! 🚀",
                    f"Whale alert! Loading up on ${company.ticker_symbol}. Don't miss this train."
                ])
                
            if msg:
                self._shout_in_chat(bot_user.user_id, bot_user.username, msg)
            
        return success
    
    def _bot_sell_shares(self, bot_user, companies, strategy):
        """Smart Selling Logic with Risk Management"""
        holdings = db.get_user_holdings(bot_user.user_id)
        if not holdings: return False
        
        holding = random.choice(holdings)
        company = Company.get_by_id(holding['company_id'])
        if not company: return False

        active_dividend = self._get_active_dividend(company.company_id)
        
        if active_dividend and strategy != BOT_STRATEGY_PANIC:
            return False

        sentiment, change = self._get_market_sentiment(company.company_id)
        
        is_crash = (market_engine.trend_type == 'bear' and datetime.now() < market_engine.trend_end_time)
        is_bull = (market_engine.trend_type == 'bull' and datetime.now() < market_engine.trend_end_time)

        avg_buy_price = holding['average_buy_price']
        current_price = company.share_price
        pl_percent = ((current_price - avg_buy_price) / avg_buy_price) * 100 if avg_buy_price > 0 else 0

        force_sell = False
        chat_msg = None

        if strategy == BOT_STRATEGY_PANIC and pl_percent < -2.0:
            force_sell = True 
            chat_msg = f"Getting out of ${company.ticker_symbol} immediately! It's crashing! 📉"
        elif pl_percent < -10.0:
            force_sell = True 
        elif pl_percent > 20.0 and strategy not in [BOT_STRATEGY_VALUE, BOT_STRATEGY_INCOME]:
            force_sell = True 
            if pl_percent > 50.0:
                chat_msg = f"Taking massive profits on ${company.ticker_symbol} (+{round(pl_percent)}%). Thanks for the liquidity! 💰"

        if not force_sell and not is_crash and random.random() > 0.3:
            return False 

        if is_crash or force_sell:
            price_multiplier = random.uniform(0.80, 0.95)
            quantity = holding['quantity']
        elif is_bull:
            price_multiplier = random.uniform(1.10, 1.20)
            quantity = max(1, int(holding['quantity'] * 0.1))
        elif sentiment == 'bull':
            price_multiplier = random.uniform(1.02, 1.05)
            quantity = max(1, int(holding['quantity'] * 0.2))
        else:
            price_multiplier = random.uniform(0.98, 1.01)
            quantity = max(1, int(holding['quantity'] * 0.3))

        sell_price = round(company.share_price * price_multiplier, 2)
        
        success = False
        
        best_buy_order = db.execute_query(
            "SELECT * FROM share_orders WHERE company_id = ? AND order_type = 'buy' AND status = 'pending' ORDER BY price_per_share DESC LIMIT 1",
            (company.company_id,)
        )

        if best_buy_order:
            buy_order = best_buy_order[0]
            buyer_price = buy_order['price_per_share']
            
            acceptable_price = sell_price
            if is_crash or force_sell: acceptable_price = company.share_price * 0.60 
            
            if buyer_price >= acceptable_price:
                sell_qty = min(quantity, buy_order['quantity'])
                try:
                    from services.trading_service import trading_service
                    trading_service.create_sell_order(bot_user.user_id, company.company_id, sell_qty, buyer_price)
                    success = True
                except: pass

        if not success:
            try:
                from services.trading_service import trading_service
                trading_service.create_sell_order(bot_user.user_id, holding['company_id'], quantity, sell_price)
                success = True
            except: pass
            
        if success and chat_msg:
            self._shout_in_chat(bot_user.user_id, bot_user.username, chat_msg)

        return success
    
    def _select_company_to_buy(self, companies, strategy):
        """Select company based on strategy"""
        if not companies: return None
        
        if strategy == BOT_STRATEGY_INCOME:
            dividend_companies = [c for c in companies if self._get_active_dividend(c.company_id)]
            if dividend_companies:
                return random.choice(dividend_companies)
        
        if strategy == BOT_STRATEGY_RANDOM or strategy == BOT_STRATEGY_PANIC: 
            return random.choice(companies)
            
        elif strategy == BOT_STRATEGY_MOMENTUM or strategy == BOT_STRATEGY_WHALE:
            sorted_companies = sorted(companies, key=lambda c: c.share_price, reverse=True)
            weights = [1.0 / (i + 1) for i in range(len(sorted_companies))]
            return random.choices(sorted_companies, weights=weights)[0]
            
        elif strategy == BOT_STRATEGY_VALUE or strategy == BOT_STRATEGY_INCOME:
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