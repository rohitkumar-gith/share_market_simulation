"""
Database Manager - Handles all database operations
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager
import config


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self, db_path=None):
        """Initialize database manager"""
        self.db_path = db_path or config.DATABASE_PATH
        self._connection = None
        self.initialize_database()
    
    def get_connection(self):
        """Get database connection"""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            self._connection.row_factory = sqlite3.Row
        return self._connection
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
    
    def initialize_database(self):
        """Initialize database schema"""
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            with self.get_cursor() as cursor:
                cursor.executescript(schema_sql)
            
            print(f"Database initialized at: {self.db_path}")
        else:
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
    
    def execute_update(self, query, params=None):
        """Execute an update/insert/delete query"""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.rowcount
    
    def execute_insert(self, query, params=None):
        """Execute an insert query and return last row id"""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.lastrowid
    
    def execute_many(self, query, params_list):
        """Execute multiple queries with different parameters"""
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
            return cursor.rowcount
    
    @contextmanager
    def transaction(self):
        """Context manager for transactions"""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    # ===== USER OPERATIONS =====
    
    def create_user(self, username, password_hash, email, full_name):
        """Create a new user"""
        query = """
            INSERT INTO users (username, password_hash, email, full_name, wallet_balance)
            VALUES (?, ?, ?, ?, ?)
        """
        return self.execute_insert(
            query,
            (username, password_hash, email, full_name, config.INITIAL_USER_BALANCE)
        )
    
    def get_user_by_username(self, username):
        """Get user by username"""
        query = "SELECT * FROM users WHERE username = ?"
        results = self.execute_query(query, (username,))
        return dict(results[0]) if results else None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        query = "SELECT * FROM users WHERE user_id = ?"
        results = self.execute_query(query, (user_id,))
        return dict(results[0]) if results else None
    
    def update_user_balance(self, user_id, new_balance):
        """Update user wallet balance"""
        query = "UPDATE users SET wallet_balance = ? WHERE user_id = ?"
        return self.execute_update(query, (new_balance, user_id))
    
    def update_last_login(self, user_id):
        """Update user's last login timestamp"""
        query = "UPDATE users SET last_login = ? WHERE user_id = ?"
        return self.execute_update(query, (datetime.now(), user_id))
    
    # ===== WALLET OPERATIONS =====
    
    def add_wallet_transaction(self, user_id, transaction_type, amount, balance_after, description=None, reference_id=None):
        """Add wallet transaction record"""
        query = """
            INSERT INTO wallet_transactions 
            (user_id, transaction_type, amount, balance_after, description, reference_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        return self.execute_insert(
            query,
            (user_id, transaction_type, amount, balance_after, description, reference_id)
        )
    
    def get_wallet_transactions(self, user_id, limit=50):
        """Get user's wallet transaction history"""
        query = """
            SELECT * FROM wallet_transactions 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """
        results = self.execute_query(query, (user_id, limit))
        return [dict(row) for row in results]
    
    # ===== COMPANY OPERATIONS =====
    
    def create_company(self, company_name, owner_id, ticker_symbol, share_price, total_shares, description=None):
        """Create a new company"""
        query = """
            INSERT INTO companies 
            (company_name, owner_id, ticker_symbol, share_price, total_shares, available_shares, description, net_worth)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        net_worth = share_price * total_shares
        return self.execute_insert(
            query,
            (company_name, owner_id, ticker_symbol, share_price, total_shares, total_shares, description, net_worth)
        )
    
    def get_company_by_id(self, company_id):
        """Get company by ID"""
        query = "SELECT * FROM companies WHERE company_id = ?"
        results = self.execute_query(query, (company_id,))
        return dict(results[0]) if results else None
    
    def get_all_companies(self):
        """Get all companies"""
        query = "SELECT * FROM companies ORDER BY net_worth DESC"
        results = self.execute_query(query)
        return [dict(row) for row in results]
    
    def get_companies_by_owner(self, owner_id):
        """Get companies owned by user"""
        query = "SELECT * FROM companies WHERE owner_id = ?"
        results = self.execute_query(query, (owner_id,))
        return [dict(row) for row in results]
    
    def update_company_share_price(self, company_id, new_price):
        """Update company share price"""
        query = "UPDATE companies SET share_price = ? WHERE company_id = ?"
        return self.execute_update(query, (new_price, company_id))
    
    def update_company_available_shares(self, company_id, available_shares):
        """Update company available shares"""
        query = "UPDATE companies SET available_shares = ? WHERE company_id = ?"
        return self.execute_update(query, (available_shares, company_id))
    
    def update_company_wallet(self, company_id, new_balance):
        """Update company wallet balance"""
        query = "UPDATE companies SET company_wallet = ? WHERE company_id = ?"
        return self.execute_update(query, (new_balance, company_id))
    
    def update_company_net_worth(self, company_id, net_worth):
        """Update company net worth"""
        query = "UPDATE companies SET net_worth = ? WHERE company_id = ?"
        return self.execute_update(query, (net_worth, company_id))
    
    # ===== HOLDINGS OPERATIONS =====
    
    def get_user_holdings(self, user_id):
        """Get user's share holdings"""
        query = """
            SELECT h.*, c.company_name, c.ticker_symbol, c.share_price
            FROM user_holdings h
            JOIN companies c ON h.company_id = c.company_id
            WHERE h.user_id = ?
        """
        results = self.execute_query(query, (user_id,))
        return [dict(row) for row in results]
    
    def get_holding(self, user_id, company_id):
        """Get specific holding"""
        query = """
            SELECT * FROM user_holdings 
            WHERE user_id = ? AND company_id = ?
        """
        results = self.execute_query(query, (user_id, company_id))
        return dict(results[0]) if results else None
    
    def add_or_update_holding(self, user_id, company_id, quantity, buy_price):
        """Add or update user holding"""
        existing = self.get_holding(user_id, company_id)
        
        if existing:
            # Update existing holding
            new_quantity = existing['quantity'] + quantity
            total_invested = existing['total_invested'] + (quantity * buy_price)
            new_avg_price = total_invested / new_quantity
            
            query = """
                UPDATE user_holdings 
                SET quantity = ?, average_buy_price = ?, total_invested = ?, last_updated = ?
                WHERE user_id = ? AND company_id = ?
            """
            self.execute_update(
                query,
                (new_quantity, new_avg_price, total_invested, datetime.now(), user_id, company_id)
            )
        else:
            # Create new holding
            query = """
                INSERT INTO user_holdings 
                (user_id, company_id, quantity, average_buy_price, total_invested)
                VALUES (?, ?, ?, ?, ?)
            """
            self.execute_insert(
                query,
                (user_id, company_id, quantity, buy_price, quantity * buy_price)
            )
    
    def reduce_holding(self, user_id, company_id, quantity):
        """Reduce user holding"""
        existing = self.get_holding(user_id, company_id)
        
        if existing and existing['quantity'] >= quantity:
            new_quantity = existing['quantity'] - quantity
            
            if new_quantity == 0:
                # Delete holding
                query = "DELETE FROM user_holdings WHERE user_id = ? AND company_id = ?"
                self.execute_update(query, (user_id, company_id))
            else:
                # Update holding
                proportion = new_quantity / existing['quantity']
                new_invested = existing['total_invested'] * proportion
                
                query = """
                    UPDATE user_holdings 
                    SET quantity = ?, total_invested = ?, last_updated = ?
                    WHERE user_id = ? AND company_id = ?
                """
                self.execute_update(
                    query,
                    (new_quantity, new_invested, datetime.now(), user_id, company_id)
                )
            return True
        return False
    
    # ===== TRANSACTION OPERATIONS =====
    
    def add_transaction(self, buyer_id, company_id, quantity, price_per_share, transaction_type, seller_id=None):
        """Add transaction record"""
        query = """
            INSERT INTO transactions 
            (buyer_id, seller_id, company_id, quantity, price_per_share, total_amount, transaction_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        total_amount = quantity * price_per_share
        return self.execute_insert(
            query,
            (buyer_id, seller_id, company_id, quantity, price_per_share, total_amount, transaction_type)
        )
    
    def get_user_transactions(self, user_id, limit=50):
        """Get user's transaction history"""
        query = """
            SELECT t.*, c.company_name, c.ticker_symbol,
                   buyer.username as buyer_name,
                   seller.username as seller_name
            FROM transactions t
            JOIN companies c ON t.company_id = c.company_id
            JOIN users buyer ON t.buyer_id = buyer.user_id
            LEFT JOIN users seller ON t.seller_id = seller.user_id
            WHERE t.buyer_id = ? OR t.seller_id = ?
            ORDER BY t.created_at DESC
            LIMIT ?
        """
        results = self.execute_query(query, (user_id, user_id, limit))
        return [dict(row) for row in results]
    
    # ===== LOAN OPERATIONS =====
    
    def create_loan(self, user_id, loan_amount, interest_rate, loan_term_months):
        """Create a new loan"""
        monthly_rate = interest_rate / 100 / 12
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** loan_term_months) / \
                         ((1 + monthly_rate) ** loan_term_months - 1)
        
        from datetime import timedelta
        due_date = datetime.now() + timedelta(days=30 * loan_term_months)
        
        query = """
            INSERT INTO loans 
            (user_id, loan_amount, interest_rate, remaining_balance, monthly_payment, loan_term_months, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        return self.execute_insert(
            query,
            (user_id, loan_amount, interest_rate, loan_amount, monthly_payment, loan_term_months, due_date)
        )
    
    def get_user_loans(self, user_id):
        """Get user's loans"""
        query = "SELECT * FROM loans WHERE user_id = ? ORDER BY issued_at DESC"
        results = self.execute_query(query, (user_id,))
        return [dict(row) for row in results]
    
    def update_loan_balance(self, loan_id, remaining_balance, status='active'):
        """Update loan remaining balance"""
        query = "UPDATE loans SET remaining_balance = ?, status = ? WHERE loan_id = ?"
        return self.execute_update(query, (remaining_balance, status, loan_id))
    
    def add_loan_payment(self, loan_id, payment_amount, principal_amount, interest_amount, remaining_balance):
        """Add loan payment record"""
        query = """
            INSERT INTO loan_payments 
            (loan_id, payment_amount, principal_amount, interest_amount, remaining_balance)
            VALUES (?, ?, ?, ?, ?)
        """
        return self.execute_insert(
            query,
            (loan_id, payment_amount, principal_amount, interest_amount, remaining_balance)
        )
    
    # ===== ASSET OPERATIONS =====
    
    def add_company_asset(self, company_id, asset_name, asset_value, asset_type=None, description=None):
        """Add company asset"""
        query = """
            INSERT INTO assets (company_id, asset_name, asset_value, asset_type, description)
            VALUES (?, ?, ?, ?, ?)
        """
        return self.execute_insert(query, (company_id, asset_name, asset_value, asset_type, description))
    
    def get_company_assets(self, company_id):
        """Get company assets"""
        query = "SELECT * FROM assets WHERE company_id = ?"
        results = self.execute_query(query, (company_id,))
        return [dict(row) for row in results]
    
    def get_company_total_assets_value(self, company_id):
        """Get total value of company assets"""
        query = "SELECT SUM(asset_value) as total FROM assets WHERE company_id = ?"
        results = self.execute_query(query, (company_id,))
        return results[0]['total'] if results and results[0]['total'] else 0
    
    # ===== DIVIDEND OPERATIONS =====
    
    def create_dividend(self, company_id, dividend_per_share, total_amount):
        """Create dividend record"""
        query = """
            INSERT INTO dividends (company_id, dividend_per_share, total_amount)
            VALUES (?, ?, ?)
        """
        return self.execute_insert(query, (company_id, dividend_per_share, total_amount))
    
    def get_company_shareholders(self, company_id):
        """Get all shareholders of a company"""
        query = """
            SELECT h.user_id, h.quantity, u.username
            FROM user_holdings h
            JOIN users u ON h.user_id = u.user_id
            WHERE h.company_id = ?
        """
        results = self.execute_query(query, (company_id,))
        return [dict(row) for row in results]


# Create a global database instance
db = DatabaseManager()
