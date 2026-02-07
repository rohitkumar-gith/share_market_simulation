"""
Share Model - Represents share IPO and trading operations
"""
from datetime import datetime
from database.db_manager import db
from models.user import User
from models.company import Company
from utils.validators import Validator
from utils.constants import *


class Share:
    """Share model for IPO and trading operations"""
    
    def __init__(self, share_id=None, company_id=None, issue_price=None,
                 shares_issued=None, issue_date=None):
        self.share_id = share_id
        self.company_id = company_id
        self.issue_price = issue_price
        self.shares_issued = shares_issued
        self.issue_date = issue_date
    
    @classmethod
    def from_dict(cls, data):
        """Create Share instance from dictionary"""
        if not data:
            return None
        return cls(
            share_id=data.get('share_id'),
            company_id=data.get('company_id'),
            issue_price=data.get('issue_price'),
            shares_issued=data.get('shares_issued'),
            issue_date=data.get('issue_date')
        )
    
    @classmethod
    def issue_ipo(cls, company_id, shares_to_issue, issue_price=None):
        """Issue IPO (Initial Public Offering)"""
        company = Company.get_by_id(company_id)
        if not company:
            raise ValueError("Company not found.")
        
        if shares_to_issue <= 0:
            raise ValueError("Shares to issue must be positive.")
        
        if shares_to_issue > company.available_shares:
            raise ValueError(f"Cannot issue {shares_to_issue} shares. Only {company.available_shares} available.")
        
        # Use current share price if not specified
        if issue_price is None:
            issue_price = company.share_price
        
        # Record IPO
        share_id = db.execute_insert(
            "INSERT INTO shares (company_id, issue_price, shares_issued) VALUES (?, ?, ?)",
            (company_id, issue_price, shares_to_issue)
        )
        
        # Update available shares (decrease)
        new_available = company.available_shares - shares_to_issue
        company.update_available_shares(new_available)
        
        # Add IPO proceeds to company wallet
        proceeds = shares_to_issue * issue_price
        company.add_to_wallet(proceeds, f"IPO proceeds: {shares_to_issue} shares @ ₹{issue_price}")
        
        return {
            'share_id': share_id,
            'shares_issued': shares_to_issue,
            'issue_price': issue_price,
            'total_proceeds': proceeds
        }
    
    @classmethod
    def buy_from_ipo(cls, user_id, company_id, quantity):
        """Buy shares from IPO (company)"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        
        user = User.get_by_id(user_id)
        company = Company.get_by_id(company_id)
        
        if not user or not company:
            raise ValueError("User or company not found.")
        
        if quantity > company.available_shares:
            raise ValueError(f"Only {company.available_shares} shares available.")
        
        # Calculate total cost
        total_cost = quantity * company.share_price
        
        if total_cost > user.wallet_balance:
            raise ValueError(f"Insufficient funds. Need ₹{total_cost:,.2f}, have ₹{user.wallet_balance:,.2f}")
        
        # Deduct from user wallet
        user.withdraw_funds(total_cost, f"Purchase {quantity} shares of {company.ticker_symbol}")
        
        # Update user holdings
        db.add_or_update_holding(user_id, company_id, quantity, company.share_price)
        
        # Update company available shares
        new_available = company.available_shares - quantity
        company.update_available_shares(new_available)
        
        # Add proceeds to company wallet
        company.add_to_wallet(total_cost, f"Share sale: {quantity} shares to {user.username}")
        
        # Record transaction
        db.add_transaction(
            user_id,
            company_id,
            quantity,
            company.share_price,
            TRANSACTION_TYPE_IPO,
            None  # No seller for IPO
        )
        
        return {
            'quantity': quantity,
            'price_per_share': company.share_price,
            'total_cost': total_cost,
            'new_balance': user.wallet_balance
        }
    
    @classmethod
    def buy_from_user(cls, buyer_id, seller_id, company_id, quantity, price_per_share):
        """Buy shares from another user"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        
        if price_per_share <= 0:
            raise ValueError("Price must be positive.")
        
        if buyer_id == seller_id:
            raise ValueError("Cannot buy from yourself.")
        
        buyer = User.get_by_id(buyer_id)
        seller = User.get_by_id(seller_id)
        company = Company.get_by_id(company_id)
        
        if not buyer or not seller or not company:
            raise ValueError("Invalid buyer, seller, or company.")
        
        # Check seller has enough shares
        seller_holding = db.get_holding(seller_id, company_id)
        if not seller_holding or seller_holding['quantity'] < quantity:
            raise ValueError(f"Seller does not have {quantity} shares.")
        
        # Calculate total cost
        total_cost = quantity * price_per_share
        
        if total_cost > buyer.wallet_balance:
            raise ValueError(f"Insufficient funds. Need ₹{total_cost:,.2f}, have ₹{buyer.wallet_balance:,.2f}")
        
        # Transfer money from buyer to seller
        buyer.withdraw_funds(total_cost, f"Purchase {quantity} shares of {company.ticker_symbol} from {seller.username}")
        seller.add_funds(total_cost, f"Sale of {quantity} shares of {company.ticker_symbol} to {buyer.username}")
        
        # Update holdings
        db.add_or_update_holding(buyer_id, company_id, quantity, price_per_share)
        db.reduce_holding(seller_id, company_id, quantity)
        
        # Record transaction
        db.add_transaction(
            buyer_id,
            company_id,
            quantity,
            price_per_share,
            TRANSACTION_TYPE_TRADE,
            seller_id
        )
        
        return {
            'quantity': quantity,
            'price_per_share': price_per_share,
            'total_cost': total_cost,
            'buyer_new_balance': buyer.wallet_balance,
            'seller_new_balance': seller.wallet_balance
        }
    
    @classmethod
    def sell_to_user(cls, seller_id, buyer_id, company_id, quantity, price_per_share):
        """Sell shares to another user (same as buy_from_user but from seller perspective)"""
        return cls.buy_from_user(buyer_id, seller_id, company_id, quantity, price_per_share)
    
    @classmethod
    def create_sell_order(cls, user_id, company_id, quantity, price_per_share):
        """Create a sell order"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        
        if price_per_share <= 0:
            raise ValueError("Price must be positive.")
        
        # Check user has enough shares
        holding = db.get_holding(user_id, company_id)
        if not holding or holding['quantity'] < quantity:
            raise ValueError(f"You don't have {quantity} shares to sell.")
        
        total_amount = quantity * price_per_share
        
        # Create order
        order_id = db.execute_insert(
            """INSERT INTO share_orders 
               (user_id, company_id, order_type, quantity, price_per_share, total_amount)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, company_id, ORDER_TYPE_SELL, quantity, price_per_share, total_amount)
        )
        
        return order_id
    
    @classmethod
    def create_buy_order(cls, user_id, company_id, quantity, price_per_share):
        """Create a buy order"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        
        if price_per_share <= 0:
            raise ValueError("Price must be positive.")
        
        user = User.get_by_id(user_id)
        total_amount = quantity * price_per_share
        
        if total_amount > user.wallet_balance:
            raise ValueError(f"Insufficient funds. Need ₹{total_amount:,.2f}")
        
        # Create order
        order_id = db.execute_insert(
            """INSERT INTO share_orders 
               (user_id, company_id, order_type, quantity, price_per_share, total_amount)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, company_id, ORDER_TYPE_BUY, quantity, price_per_share, total_amount)
        )
        
        return order_id
    
    @classmethod
    def get_pending_orders(cls, company_id=None, order_type=None):
        """Get pending orders"""
        query = "SELECT * FROM share_orders WHERE status = ?"
        params = [ORDER_STATUS_PENDING]
        
        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)
        
        if order_type:
            query += " AND order_type = ?"
            params.append(order_type)
        
        query += " ORDER BY created_at ASC"
        
        results = db.execute_query(query, params)
        return [dict(row) for row in results]
    
    @classmethod
    def cancel_order(cls, order_id, user_id):
        """Cancel an order"""
        order = db.execute_query(
            "SELECT * FROM share_orders WHERE order_id = ?",
            (order_id,)
        )
        
        if not order:
            raise ValueError("Order not found.")
        
        order = dict(order[0])
        
        if order['user_id'] != user_id:
            raise ValueError("You can only cancel your own orders.")
        
        if order['status'] != ORDER_STATUS_PENDING:
            raise ValueError("Can only cancel pending orders.")
        
        # Update order status
        db.execute_update(
            "UPDATE share_orders SET status = ? WHERE order_id = ?",
            (ORDER_STATUS_CANCELLED, order_id)
        )
        
        return True
    
    @classmethod
    def get_user_orders(cls, user_id, limit=50):
        """Get user's orders"""
        query = """
            SELECT o.*, c.company_name, c.ticker_symbol
            FROM share_orders o
            JOIN companies c ON o.company_id = c.company_id
            WHERE o.user_id = ?
            ORDER BY o.created_at DESC
            LIMIT ?
        """
        results = db.execute_query(query, (user_id, limit))
        return [dict(row) for row in results]
