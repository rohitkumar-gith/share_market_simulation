"""
Trading Service - Handles buy/sell logic and market data
"""
from database.db_manager import db
from models.share import Share
from models.company import Company
from models.user import User
from models.transaction import Transaction
from utils.constants import *
from utils.formatters import Formatter
from datetime import datetime
import config

class TradingService:
    
    # ==========================================
    # ORDER MANAGEMENT
    # ==========================================
    
    def get_my_orders(self, user_id):
        """Get all pending orders for a user"""
        query = """
            SELECT o.*, c.company_name, c.ticker_symbol 
            FROM share_orders o
            JOIN companies c ON o.company_id = c.company_id
            WHERE o.user_id = ? AND o.status = 'pending'
            ORDER BY o.created_at DESC
        """
        return db.execute_query(query, (user_id,))

    def cancel_order(self, order_id, user_id):
        """Cancel an order and refund remaining shares/money"""
        try:
            order = db.execute_query(
                "SELECT * FROM share_orders WHERE order_id = ? AND user_id = ?", 
                (order_id, user_id)
            )
            
            if not order:
                return {'success': False, 'message': 'Order not found'}
            
            order = order[0]
            
            if order['status'] != 'pending':
                return {'success': False, 'message': 'Cannot cancel completed order'}

            db.execute_update(
                "UPDATE share_orders SET status = 'cancelled' WHERE order_id = ?", 
                (order_id,)
            )

            remaining_qty = order['quantity']
            
            if remaining_qty > 0:
                if order['order_type'] == 'buy':
                    refund_amount = remaining_qty * order['price_per_share']
                    User.get_by_id(user_id).add_funds(
                        refund_amount, 
                        f"Refund from cancelled Buy Order #{order_id}"
                    )
                    
                elif order['order_type'] == 'sell':
                    # Try to restore holding with original average price
                    holding = db.get_holding(user_id, order['company_id'])
                    avg_price = holding['average_buy_price'] if holding else order['price_per_share']
                    
                    db.add_or_update_holding(
                        user_id, 
                        order['company_id'], 
                        remaining_qty, 
                        avg_price
                    )

            return {
                'success': True, 
                'message': f"Order cancelled. {remaining_qty} units returned."
            }

        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ==========================================
    # BUYING LOGIC (UPDATED)
    # ==========================================

    def process_buy_request(self, user_id, company_id, quantity, bid_price):
        """
        Process a user's buy request with a CUSTOM Price.
        1. Checks if IPO is available (and cheap enough).
        2. If not, places a Limit Order at the user's Bid Price.
        """
        company = Company.get_by_id(company_id)
        current_price = company.share_price
        
        # 1. Try Buying from IPO (Only if Bid >= Current Price)
        # If you bid ₹90 but stock is ₹100, you can't buy IPO. You must wait for drop.
        if company.available_shares >= quantity and bid_price >= current_price:
            try:
                # IPO always sells at Current Price.
                # If user bid ₹105, they get it for ₹100 (IPO Price). Savings!
                Share.buy_from_ipo(user_id, company_id, quantity)
                return {
                    'success': True, 
                    'message': f"Success! Bought {quantity} shares from IPO at ₹{current_price} (You saved ₹{bid_price - current_price:.2f}/share)",
                    'type': 'ipo'
                }
            except Exception as e:
                return {'success': False, 'message': str(e)}

        # 2. Place Limit Order
        else:
            user = User.get_by_id(user_id)
            total_cost = quantity * bid_price
            
            if user.wallet_balance < total_cost:
                return {
                    'success': False, 
                    'message': f"Insufficient funds. Need {Formatter.format_currency(total_cost)}"
                }

            result = self.create_buy_order(user_id, company_id, quantity, bid_price)
            if result['success']:
                msg = f"Order Placed for {quantity} shares @ {Formatter.format_currency(bid_price)}."
                if company.available_shares >= quantity:
                    msg += "\n(Note: IPO available, but your bid was below current price)"
                elif bid_price > current_price:
                    msg += "\n(Priority Bid: Higher chance of matching)"
                result['message'] = msg
            return result

    def create_buy_order(self, user_id, company_id, quantity, price):
        try:
            total_amount = quantity * price
            user = User.get_by_id(user_id)
            
            if user.wallet_balance < total_amount:
                return {'success': False, 'message': "Insufficient funds"}
            
            user.withdraw_funds(total_amount, f"Buy Order Reserved: {quantity} shares")
            
            query = """
                INSERT INTO share_orders 
                (user_id, company_id, order_type, quantity, price_per_share, total_amount, status)
                VALUES (?, ?, 'buy', ?, ?, ?, 'pending')
            """
            order_id = db.execute_insert(query, (user_id, company_id, quantity, price, total_amount))
            
            return {
                'success': True, 
                'message': f"Buy Order Placed.",
                'type': 'order',
                'order_id': order_id
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def create_sell_order(self, user_id, company_id, quantity, price):
        try:
            holding = db.get_holding(user_id, company_id)
            if not holding or holding['quantity'] < quantity:
                return {'success': False, 'message': "Insufficient shares"}
            
            db.reduce_holding(user_id, company_id, quantity)
            total_amount = quantity * price
            
            query = """
                INSERT INTO share_orders 
                (user_id, company_id, order_type, quantity, price_per_share, total_amount, status)
                VALUES (?, ?, 'sell', ?, ?, ?, 'pending')
            """
            order_id = db.execute_insert(query, (user_id, company_id, quantity, price, total_amount))
            
            return {'success': True, 'message': "Sell order placed successfully", 'order_id': order_id}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ==========================================
    # HELPERS
    # ==========================================

    def get_market_overview(self):
        companies = Company.get_all()
        if not companies: return {'total_companies': 0, 'total_market_cap': 0, 'average_share_price': 0}
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
        company = Company.get_by_id(company_id)
        if not company: return None
        return {'company': company.to_dict(), 'market_cap': company.get_market_cap(), 'shareholders': company.get_shareholders()}

    def get_user_portfolio(self, user_id):
        user = User.get_by_id(user_id)
        return user.get_portfolio() if user else None

    def search_companies(self, search_term):
        companies = Company.get_all()
        if not search_term: return companies
        term = search_term.lower()
        return [c for c in companies if term in c.company_name.lower() or term in c.ticker_symbol.lower()]

    def get_trending_stocks(self, limit=10):
        companies = Company.get_all()
        trending = []
        for company in companies:
            volume = Transaction.get_trading_volume(company.company_id, hours=24)
            trending.append({'company': company.to_dict(), 'volume': volume['volume']})
        trending.sort(key=lambda x: x['volume'], reverse=True)
        return trending[:limit]
        
    def get_available_shares(self, company_id):
        company = Company.get_by_id(company_id)
        return company.available_shares if company else 0

    def get_user_holding(self, user_id, company_id):
        return db.get_holding(user_id, company_id)

trading_service = TradingService()