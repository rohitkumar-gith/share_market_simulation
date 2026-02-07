"""
Transaction Model - Represents trading transactions
"""
from datetime import datetime
from database.db_manager import db


class Transaction:
    """Transaction model for tracking all trades"""
    
    def __init__(self, transaction_id=None, buyer_id=None, seller_id=None,
                 company_id=None, quantity=None, price_per_share=None,
                 total_amount=None, transaction_type=None, created_at=None):
        self.transaction_id = transaction_id
        self.buyer_id = buyer_id
        self.seller_id = seller_id
        self.company_id = company_id
        self.quantity = quantity
        self.price_per_share = price_per_share
        self.total_amount = total_amount
        self.transaction_type = transaction_type
        self.created_at = created_at
    
    @classmethod
    def from_dict(cls, data):
        """Create Transaction instance from dictionary"""
        if not data:
            return None
        return cls(
            transaction_id=data.get('transaction_id'),
            buyer_id=data.get('buyer_id'),
            seller_id=data.get('seller_id'),
            company_id=data.get('company_id'),
            quantity=data.get('quantity'),
            price_per_share=data.get('price_per_share'),
            total_amount=data.get('total_amount'),
            transaction_type=data.get('transaction_type'),
            created_at=data.get('created_at')
        )
    
    def to_dict(self):
        """Convert Transaction to dictionary"""
        return {
            'transaction_id': self.transaction_id,
            'buyer_id': self.buyer_id,
            'seller_id': self.seller_id,
            'company_id': self.company_id,
            'quantity': self.quantity,
            'price_per_share': self.price_per_share,
            'total_amount': self.total_amount,
            'transaction_type': self.transaction_type,
            'created_at': self.created_at
        }
    
    @classmethod
    def get_by_id(cls, transaction_id):
        """Get transaction by ID"""
        query = "SELECT * FROM transactions WHERE transaction_id = ?"
        results = db.execute_query(query, (transaction_id,))
        return cls.from_dict(dict(results[0])) if results else None
    
    @classmethod
    def get_user_transactions(cls, user_id, limit=50):
        """Get user's transaction history"""
        transactions = db.get_user_transactions(user_id, limit)
        return [cls.from_dict(t) for t in transactions]
    
    @classmethod
    def get_company_transactions(cls, company_id, limit=100):
        """Get all transactions for a company"""
        query = """
            SELECT t.*, 
                   buyer.username as buyer_name,
                   seller.username as seller_name,
                   c.company_name, c.ticker_symbol
            FROM transactions t
            JOIN companies c ON t.company_id = c.company_id
            JOIN users buyer ON t.buyer_id = buyer.user_id
            LEFT JOIN users seller ON t.seller_id = seller.user_id
            WHERE t.company_id = ?
            ORDER BY t.created_at DESC
            LIMIT ?
        """
        results = db.execute_query(query, (company_id, limit))
        return [dict(row) for row in results]
    
    @classmethod
    def get_recent_transactions(cls, limit=100):
        """Get recent market transactions"""
        query = """
            SELECT t.*, 
                   buyer.username as buyer_name,
                   seller.username as seller_name,
                   c.company_name, c.ticker_symbol
            FROM transactions t
            JOIN companies c ON t.company_id = c.company_id
            JOIN users buyer ON t.buyer_id = buyer.user_id
            LEFT JOIN users seller ON t.seller_id = seller.user_id
            ORDER BY t.created_at DESC
            LIMIT ?
        """
        results = db.execute_query(query, (limit,))
        return [dict(row) for row in results]
    
    @classmethod
    def get_trading_volume(cls, company_id, hours=24):
        """Get trading volume for a company in last N hours"""
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        query = """
            SELECT SUM(quantity) as volume, COUNT(*) as trade_count
            FROM transactions
            WHERE company_id = ? AND created_at > ?
        """
        results = db.execute_query(query, (company_id, cutoff_time))
        
        if results and results[0]['volume']:
            return {
                'volume': results[0]['volume'],
                'trade_count': results[0]['trade_count']
            }
        return {'volume': 0, 'trade_count': 0}
    
    @classmethod
    def get_market_activity(cls, hours=24):
        """Get overall market activity"""
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        query = """
            SELECT 
                COUNT(*) as total_trades,
                SUM(quantity) as total_volume,
                SUM(total_amount) as total_value,
                COUNT(DISTINCT company_id) as active_companies
            FROM transactions
            WHERE created_at > ?
        """
        results = db.execute_query(query, (cutoff_time,))
        return dict(results[0]) if results else {
            'total_trades': 0,
            'total_volume': 0,
            'total_value': 0,
            'active_companies': 0
        }
    
    def __repr__(self):
        return f"<Transaction(id={self.transaction_id}, company={self.company_id}, qty={self.quantity}, price={self.price_per_share})>"
