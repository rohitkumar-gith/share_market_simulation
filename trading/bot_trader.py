"""
Bot Trader - Automated trading bots to simulate market activity
"""
import random
from datetime import datetime
from models.user import User
from models.company import Company
from models.share import Share
from database.db_manager import db
from utils.constants import *
import config

class BotTrader:
    """Automated trading bot"""
    
    def __init__(self):
        self.bots = []
        self.initialized = False
        # --- NEW: Realistic Names ---
        self.bot_names = [
            "Arjun Mehta", "Priya Sharma", "Rahul Verma", 
            "Anjali Gupta", "Vikram Singh", "Sneha Patel", "Rohan Das"
        ]
    
    def initialize_bots(self, count=None):
        """Initialize trading bots"""
        if self.initialized: return
        
        # Force count to 7 if not specified
        if count is None: count = 7
        
        existing_bots = db.execute_query("SELECT * FROM bots")
        if existing_bots:
            self.bots = [dict(bot) for bot in existing_bots]
            self.initialized = True
            print(f"Loaded {len(self.bots)} existing trading bots")
            return
        
        strategies = [BOT_STRATEGY_RANDOM, BOT_STRATEGY_MOMENTUM, BOT_STRATEGY_VALUE]
        created_count = 0
        
        for i in range(count):
            # Use realistic name if available, else fallback
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
                created_count += 1
            except Exception as e:
                print(f"Error initializing bot {username} in DB: {e}")
        
        self.initialized = True
        print(f"Initialized {created_count} trading bots")
    
    def execute_bot_trades(self):
        """Execute trades for all active bots"""
        if not self.initialized: self.initialize_bots()
        
        companies = Company.get_all()
        if not companies: return {'trades_executed': 0}
        
        trades_executed = 0
        
        for bot in self.bots:
            if not bot['is_active']: continue
            
            # High activity rate (80%) to ensure liquidity
            if random.random() < 0.8:
                try:
                    result = self._execute_single_bot_trade(bot, companies)
                    if result: trades_executed += 1
                except Exception as e:
                    print(f"Bot trade error: {e}")
                    continue
        
        return {'trades_executed': trades_executed}
    
    def _execute_single_bot_trade(self, bot, companies):
        """Execute a single trade with Fallback Logic"""
        bot_user = User.get_by_id(bot['user_id'])
        if not bot_user: return False
        
        # 50/50 Split for Buy/Sell
        action = 'buy' if random.random() < 0.5 else 'sell'
        
        success = False
        if action == 'buy':
            success = self._bot_buy_shares(bot_user, companies, bot['strategy'])
            # Fallback: If buy failed, try selling
            if not success:
                success = self._bot_sell_shares(bot_user, companies, bot['strategy'])
        else:
            success = self._bot_sell_shares(bot_user, companies, bot['strategy'])
            # Fallback: If sell failed, try buying
            if not success:
                success = self._bot_buy_shares(bot_user, companies, bot['strategy'])
                
        return success
    
    def _bot_buy_shares(self, bot_user, companies, strategy):
        """Bot buys shares - PRIORITIZING USER SELL ORDERS"""
        # Select target from list
        target_in_list = self._select_company_to_buy(companies, strategy)
        if not target_in_list: return False
        
        # Force Fresh Fetch
        company = Company.get_by_id(target_in_list.company_id)
        if not company or company.share_price <= 0: return False
            
        max_affordable = int(bot_user.wallet_balance / company.share_price)
        if max_affordable < 1: return False
        
        max_qty = min(max_affordable, 100)
        quantity = random.randint(1, max(1, max_qty))
        
        # 1. CHECK SECONDARY MARKET (SELL ORDERS) FIRST
        best_sell_order = db.execute_query(
            "SELECT * FROM share_orders WHERE company_id = ? AND order_type = 'sell' AND status = 'pending' ORDER BY price_per_share ASC LIMIT 1",
            (company.company_id,)
        )
        
        if best_sell_order:
            sell_order = best_sell_order[0]
            sell_price = sell_order['price_per_share']
            
            # Bot will buy shares up to 50% MORE EXPENSIVE than market price.
            if sell_price <= company.share_price * 1.50:
                try:
                    from services.trading_service import trading_service
                    buy_qty = min(quantity, sell_order['quantity'])
                    
                    # Logic: Hesitate slightly on extremely high prices (>20%)
                    should_buy = True
                    if sell_price > company.share_price * 1.20:
                        should_buy = random.random() < 0.6 # 60% chance to buy
                        
                    if should_buy:
                        # Match seller's price instantly
                        trading_service.create_buy_order(bot_user.user_id, company.company_id, buy_qty, sell_price)
                        return True
                except:
                    pass 
        
        # 2. Check IPO Availability
        if company.available_shares >= quantity:
            try:
                Share.buy_from_ipo(bot_user.user_id, company.company_id, quantity)
                return True
            except: return False
            
        # 3. Standard Market Order
        else:
            price_multiplier = random.uniform(1.00, 1.03)
            offer_price = round(company.share_price * price_multiplier, 2)
            try:
                from services.trading_service import trading_service
                trading_service.create_buy_order(bot_user.user_id, company.company_id, quantity, offer_price)
                return True
            except: return False
    
    def _bot_sell_shares(self, bot_user, companies, strategy):
        """Bot Sells Shares - LOOKS FOR HIGH USER BIDS FIRST"""
        holdings = db.get_user_holdings(bot_user.user_id)
        if not holdings: return False
        
        # Check for High User Bids
        for holding in holdings:
            company = Company.get_by_id(holding['company_id'])
            if not company: continue

            best_buy_order = db.execute_query(
                "SELECT * FROM share_orders WHERE company_id = ? AND order_type = 'buy' AND status = 'pending' ORDER BY price_per_share DESC LIMIT 1",
                (company.company_id,)
            )

            if best_buy_order:
                buy_order = best_buy_order[0]
                buyer_price = buy_order['price_per_share']
                
                if buyer_price >= company.share_price:
                    sell_qty = min(holding['quantity'], buy_order['quantity'])
                    try:
                        from services.trading_service import trading_service
                        trading_service.create_sell_order(bot_user.user_id, company.company_id, sell_qty, buyer_price)
                        return True
                    except: pass

        # Standard Random Sell
        holding = random.choice(holdings)
        company = Company.get_by_id(holding['company_id'])
        if not company: return False

        sell_percentage = random.uniform(0.1, 0.5)
        quantity = max(1, int(holding['quantity'] * sell_percentage))
        
        price_multiplier = random.uniform(0.98, 1.0)
        sell_price = round(company.share_price * price_multiplier, 2)
        
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
        """Get statistics for all bots (Used by Admin Panel)"""
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
        """Enable or disable a bot (Used by Admin Panel)"""
        db.execute_update("UPDATE bots SET is_active = ? WHERE bot_id = ?", (1 if active else 0, bot_id))
        for bot in self.bots:
            if bot['bot_id'] == bot_id:
                bot['is_active'] = 1 if active else 0
                break

    def reset_bot_balances(self):
        """Reset all bots to initial funds (Used by Admin Panel)"""
        for bot in self.bots:
            bot_user = User.get_by_id(bot['user_id'])
            if bot_user:
                db.execute_update("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (config.BOT_INITIAL_BALANCE, bot_user.user_id))
                db.execute_update("DELETE FROM user_holdings WHERE user_id = ?", (bot_user.user_id,))

bot_trader = BotTrader()