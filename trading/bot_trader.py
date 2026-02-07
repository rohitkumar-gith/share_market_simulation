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
    
    def initialize_bots(self, count=None):
        """
        Initialize trading bots
        
        Args:
            count: Number of bots to create (uses config if None)
        """
        if self.initialized:
            return
        
        if count is None:
            count = config.NUMBER_OF_BOTS
        
        # Check if bots already exist in database
        existing_bots = db.execute_query("SELECT * FROM bots")
        
        if existing_bots:
            self.bots = [dict(bot) for bot in existing_bots]
            self.initialized = True
            print(f"Loaded {len(self.bots)} existing trading bots")
            return
        
        # Create bot users
        strategies = [BOT_STRATEGY_RANDOM, BOT_STRATEGY_MOMENTUM, BOT_STRATEGY_VALUE]
        created_count = 0
        
        for i in range(count):
            # --- FIX: Removed underscore to pass alphanumeric validation ---
            bot_name = f"TradingBot{i+1}" 
            strategy = strategies[i % len(strategies)]
            
            # Check if bot user exists
            bot_user = User.get_by_username(bot_name)
            
            if not bot_user:
                # Create bot user
                try:
                    bot_user = User.register(
                        username=bot_name,
                        password=f"bot_password_{i+1}",
                        email=f"bot{i+1}@market.sim",
                        full_name=f"Trading Bot {i+1}"
                    )
                except Exception as e:
                    # --- FIX: Added error printing to see why it fails ---
                    print(f"Error creating user for bot {bot_name}: {e}")
                    continue
            
            # Create bot record
            try:
                bot_id = db.execute_insert(
                    """INSERT INTO bots (bot_name, user_id, wallet_balance, strategy, is_active)
                       VALUES (?, ?, ?, ?, ?)""",
                    (bot_name, bot_user.user_id, config.BOT_INITIAL_BALANCE, strategy, 1)
                )
                
                self.bots.append({
                    'bot_id': bot_id,
                    'bot_name': bot_name,
                    'user_id': bot_user.user_id,
                    'wallet_balance': config.BOT_INITIAL_BALANCE,
                    'strategy': strategy,
                    'is_active': 1
                })
                created_count += 1
            except Exception as e:
                print(f"Error initializing bot {bot_name} in DB: {e}")
        
        self.initialized = True
        print(f"Initialized {created_count} trading bots")
    
    def execute_bot_trades(self):
        """Execute trades for all active bots"""
        if not self.initialized:
            self.initialize_bots()
        
        companies = Company.get_all()
        if not companies:
            return {'trades_executed': 0, 'message': 'No companies available'}
        
        trades_executed = 0
        
        for bot in self.bots:
            if not bot['is_active']:
                continue
            
            # Random chance to trade (50%)
            if random.random() < 0.5:
                try:
                    result = self._execute_single_bot_trade(bot, companies)
                    if result:
                        trades_executed += 1
                except Exception as e:
                    print(f"Bot trade error: {e}")
                    continue
        
        return {
            'trades_executed': trades_executed,
            'active_bots': sum(1 for b in self.bots if b['is_active']),
            'timestamp': datetime.now()
        }
    
    def _execute_single_bot_trade(self, bot, companies):
        """
        Execute a single trade for a bot
        
        Args:
            bot: Bot dictionary
            companies: List of available companies
            
        Returns:
            True if trade executed, False otherwise
        """
        bot_user = User.get_by_id(bot['user_id'])
        if not bot_user:
            return False
        
        # Refresh bot balance
        bot_user.refresh()
        
        # Decide buy or sell (60% buy, 40% sell)
        action = 'buy' if random.random() < 0.6 else 'sell'
        
        if action == 'buy':
            return self._bot_buy_shares(bot_user, companies, bot['strategy'])
        else:
            return self._bot_sell_shares(bot_user, companies, bot['strategy'])
    
    def _bot_buy_shares(self, bot_user, companies, strategy):
        """
        Bot buys shares
        
        Args:
            bot_user: Bot user object
            companies: List of companies
            strategy: Bot strategy
            
        Returns:
            True if purchase successful
        """
        # Select company based on strategy
        company = self._select_company_to_buy(companies, strategy)
        
        if not company:
            return False
        
        # Determine quantity to buy
        # Protect against division by zero if share price is 0 (unlikely but possible)
        if company.share_price <= 0:
            return False
            
        max_affordable = int(bot_user.wallet_balance / company.share_price)
        
        if max_affordable < 1:
            return False
        
        # Random quantity between 1 and min(max_affordable, 100)
        max_qty = min(max_affordable, 100)
        quantity = random.randint(1, max(1, max_qty))
        
        # Limit to min/max trade amount
        total_cost = quantity * company.share_price
        
        if total_cost < config.BOT_MIN_TRADE_AMOUNT:
            # Try to increase quantity to meet min amount
            quantity = max(1, int(config.BOT_MIN_TRADE_AMOUNT / company.share_price))
            # Re-check affordability
            if quantity * company.share_price > bot_user.wallet_balance:
                return False
        elif total_cost > config.BOT_MAX_TRADE_AMOUNT:
            quantity = int(config.BOT_MAX_TRADE_AMOUNT / company.share_price)
        
        if quantity < 1:
            return False
        
        # Check if shares available from company
        if company.available_shares >= quantity:
            # Buy from IPO
            try:
                Share.buy_from_ipo(bot_user.user_id, company.company_id, quantity)
                return True
            except:
                return False
        else:
            # Try to find a seller
            # Get users who have this stock
            holders = db.get_company_shareholders(company.company_id)
            
            if not holders:
                return False
            
            # Select random holder
            holder = random.choice(holders)
            
            if holder['user_id'] == bot_user.user_id:
                return False  # Don't buy from self
            
            if holder['quantity'] < quantity:
                quantity = holder['quantity']
            
            if quantity < 1:
                return False
                
            # Offer slightly higher price (1-3% above current)
            price_multiplier = random.uniform(1.0, 1.03)
            offer_price = round(company.share_price * price_multiplier, 2)
            
            try:
                # In a real system we would create a buy order, but here we try direct trade
                # For this to work, we'd need to bypass the "Sell Order" requirement or implement full order matching
                # Since we want bots to populate the market, let's CREATE A BUY ORDER instead
                from services.trading_service import trading_service
                trading_service.create_buy_order(bot_user.user_id, company.company_id, quantity, offer_price)
                return True
            except:
                return False
    
    def _bot_sell_shares(self, bot_user, companies, strategy):
        """
        Bot sells shares
        
        Args:
            bot_user: Bot user object
            companies: List of companies
            strategy: Bot strategy
            
        Returns:
            True if sale successful
        """
        # Get bot's holdings
        holdings = db.get_user_holdings(bot_user.user_id)
        
        if not holdings:
            return False
        
        # Select holding to sell
        holding = random.choice(holdings)
        
        # Determine quantity to sell (10-50% of holding)
        sell_percentage = random.uniform(0.1, 0.5)
        quantity = max(1, int(holding['quantity'] * sell_percentage))
        
        # Price slightly lower (1-3% below current) for quick sale
        company = Company.get_by_id(holding['company_id'])
        if not company:
            return False
            
        price_multiplier = random.uniform(0.97, 1.0)
        sell_price = round(company.share_price * price_multiplier, 2)
        
        # Create a Sell Order
        try:
            from services.trading_service import trading_service
            trading_service.create_sell_order(bot_user.user_id, holding['company_id'], quantity, sell_price)
            return True
        except:
            return False
    
    def _select_company_to_buy(self, companies, strategy):
        """
        Select company to buy based on strategy
        
        Args:
            companies: List of companies
            strategy: Bot strategy
            
        Returns:
            Company object
        """
        if not companies:
            return None
        
        if strategy == BOT_STRATEGY_RANDOM:
            # Random selection
            return random.choice(companies)
        
        elif strategy == BOT_STRATEGY_MOMENTUM:
            # Buy stocks with recent price increases
            # For now, random with preference for higher priced stocks
            sorted_companies = sorted(companies, key=lambda c: c.share_price, reverse=True)
            # Weighted random selection favoring top companies
            weights = [1.0 / (i + 1) for i in range(len(sorted_companies))]
            return random.choices(sorted_companies, weights=weights)[0]
        
        elif strategy == BOT_STRATEGY_VALUE:
            # Buy undervalued stocks (lower price)
            sorted_companies = sorted(companies, key=lambda c: c.share_price)
            # Weighted random selection favoring cheaper stocks
            weights = [1.0 / (i + 1) for i in range(len(sorted_companies))]
            return random.choices(sorted_companies, weights=weights)[0]
        
        else:
            return random.choice(companies)
    
    def get_bot_statistics(self):
        """Get statistics for all bots"""
        stats = []
        
        for bot in self.bots:
            bot_user = User.get_by_id(bot['user_id'])
            if not bot_user:
                continue
            
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
        """Enable or disable a bot"""
        db.execute_update(
            "UPDATE bots SET is_active = ? WHERE bot_id = ?",
            (1 if active else 0, bot_id)
        )
        
        # Update local cache
        for bot in self.bots:
            if bot['bot_id'] == bot_id:
                bot['is_active'] = 1 if active else 0
                break
    
    def reset_bot_balances(self):
        """Reset all bot balances to initial amount"""
        for bot in self.bots:
            bot_user = User.get_by_id(bot['user_id'])
            if bot_user:
                # Reset wallet
                bot_user.update_wallet_balance(config.BOT_INITIAL_BALANCE)
                
                # Clear holdings (simplified - in production, would need to handle this properly)
                db.execute_update(
                    "DELETE FROM user_holdings WHERE user_id = ?",
                    (bot_user.user_id,)
                )


# Global bot trader instance
bot_trader = BotTrader()