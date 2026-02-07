"""
Trading Service - Handles buy/sell logic and market data
"""
from database.db_manager import db
from models.share import Share
from models.company import Company
from models.user import User
from models.transaction import Transaction
from utils.constants import *
from datetime import datetime
import config

class TradingService:
    
    # ==========================================
    # SMART BUYING & ORDER LOGIC
    # ==========================================

    def smart_buy(self, user_id, company_id, quantity, current_price):
        """
        Smart Buy: Tries IPO first. If sold out, places a Market Order.
        """
        company = Company.get_by_id(company_id)
        
        # 1. Try Buying from IPO (Direct from Company)
        if company.available_shares >= quantity:
            try:
                Share.buy_from_ipo(user_id, company_id, quantity)
                # Note: Price updates are now handled by MarketEngine in the background
                return {
                    'success': True, 
                    'message': f"Successfully bought {quantity} shares from IPO!",
                    'type': 'ipo'
                }
            except Exception as e:
                return {'success': False, 'message': str(e)}

        # 2. If IPO is full/closed, Place a Buy Order (Market Trade)
        else:
            user = User.get_by_id(user_id)
            total_cost = quantity * current_price
            if user.wallet_balance < total_cost:
                return {'success': False, 'message': "Insufficient funds for market order."}

            return self.create_buy_order(user_id, company_id, quantity, current_price)

    def buy_shares_from_ipo(self, user_id, company_id, quantity):
        """Buy direct from IPO"""
        try:
            Share.buy_from_ipo(user_id, company_id, quantity)
            return {'success': True, 'message': "Purchase successful"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def create_buy_order(self, user_id, company_id, quantity, price):
        """Create a pending Buy Order"""
        try:
            total_amount = quantity * price
            
            # Lock funds (deduct from wallet immediately)
            user = User.get_by_id(user_id)
            if user.wallet_balance < total_amount:
                return {'success': False, 'message': "Insufficient funds"}
            
            user.withdraw_funds(total_amount, f"Buy Order Reserved: {quantity} shares")
            
            # Insert Order
            query = """
                INSERT INTO share_orders 
                (user_id, company_id, order_type, quantity, price_per_share, total_amount, status)
                VALUES (?, ?, 'buy', ?, ?, ?, 'pending')
            """
            order_id = db.execute_insert(query, (user_id, company_id, quantity, price, total_amount))
            
            return {
                'success': True, 
                'message': f"IPO Sold Out.\nPlaced Buy Order for {quantity} shares at ₹{price}.\nWaiting for a seller...",
                'type': 'order',
                'order_id': order_id
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def create_sell_order(self, user_id, company_id, quantity, price):
        """Create a pending Sell Order"""
        try:
            # Check holdings
            holding = db.get_holding(user_id, company_id)
            if not holding or holding['quantity'] < quantity:
                return {'success': False, 'message': "Insufficient shares"}
            
            # Lock shares (deduct from holdings immediately)
            db.reduce_holding(user_id, company_id, quantity)
            
            total_amount = quantity * price
            
            # Insert Order
            query = """
                INSERT INTO share_orders 
                (user_id, company_id, order_type, quantity, price_per_share, total_amount, status)
                VALUES (?, ?, 'sell', ?, ?, ?, 'pending')
            """
            order_id = db.execute_insert(query, (user_id, company_id, quantity, price, total_amount))
            
            return {
                'success': True, 
                'message': "Sell order placed successfully",
                'order_id': order_id
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
            
    def cancel_order(self, order_id, user_id):
        """Cancel an order"""
        try:
            Share.cancel_order(order_id, user_id)
            return {'success': True, 'message': 'Order cancelled successfully'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ==========================================
    # READ-ONLY HELPER FUNCTIONS
    # ==========================================

    def get_market_overview(self):
        """Get overall market overview"""
        companies = Company.get_all()
        if not companies:
            return {'total_companies': 0, 'total_market_cap': 0, 'average_share_price': 0}
        
        total_market_cap = sum(c.get_market_cap() for c in companies)
        avg_price = sum(c.share_price for c in companies) / len(companies)
        top_companies = sorted(companies, key=lambda c: c.get_market_cap(), reverse=True)[:10]
        
        return {
            'total_companies': len(companies),
            'total_market_cap': total_market_cap,
            'average_share_price': avg_price,
            'top_companies': [c.to_dict() for c in top_companies]
        }

    def get_company_details(self, company_id):
        """Get detailed company information"""
        company = Company.get_by_id(company_id)
        if not company: return None
        
        return {
            'company': company.to_dict(),
            'market_cap': company.get_market_cap(),
            'shareholders': company.get_shareholders()
        }

    def get_user_portfolio(self, user_id):
        """Get user's complete portfolio"""
        user = User.get_by_id(user_id)
        return user.get_portfolio() if user else None

    def search_companies(self, search_term):
        """Search companies by name or ticker"""
        companies = Company.get_all()
        if not search_term: return companies
        
        term = search_term.lower()
        return [c for c in companies if term in c.company_name.lower() or term in c.ticker_symbol.lower()]

    def get_trending_stocks(self, limit=10):
        """Get trending stocks based on trading volume"""
        companies = Company.get_all()
        trending = []
        for company in companies:
            volume = Transaction.get_trading_volume(company.company_id, hours=24)
            trending.append({
                'company': company.to_dict(),
                'volume': volume['volume']
            })
        trending.sort(key=lambda x: x['volume'], reverse=True)
        return trending[:limit]
        
    def get_available_shares(self, company_id):
        """Get available shares"""
        company = Company.get_by_id(company_id)
        return company.available_shares if company else 0

    def get_user_holding(self, user_id, company_id):
        """Get specific holding"""
        return db.get_holding(user_id, company_id)

# Global trading service instance
trading_service = TradingService()