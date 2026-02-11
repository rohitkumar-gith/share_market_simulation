"""
Database Manager - Handles all SQLite interactions with High-Performance Optimizations
"""
import sqlite3
import os
import threading
import config
from datetime import datetime, timedelta

class DBManager:
    def __init__(self):
        self.db_path = config.DATABASE_PATH
        # Thread-local storage ensures UI and Bots don't fight for the same connection handle
        self._local = threading.local()
        self.check_connection()

    def get_connection(self):
        """Get or create a high-performance connection for the current thread"""
        if not hasattr(self._local, "connection"):
            conn = sqlite3.connect(
                self.db_path, 
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False # Essential for multi-threaded bot/UI access
            )
            conn.row_factory = sqlite3.Row
            
            # --- DATABASE ENGINE TUNING ---
            conn.execute("PRAGMA journal_mode=WAL;")      # Allows simultaneous reading and writing
            conn.execute("PRAGMA synchronous=NORMAL;")   # Significant increase in write speed
            conn.execute("PRAGMA cache_size=-32000;")    # 32MB Memory Cache for high-speed lookups
            conn.execute("PRAGMA temp_store=MEMORY;")    # Keep temporary tables/indexes in RAM
            
            self._local.connection = conn
        return self._local.connection

    def check_connection(self):
        """Ensure database exists and table structure is correct"""
        new_db = not os.path.exists(self.db_path)
        if new_db:
            conn = self.get_connection()
            print(f"Database initialized at: {self.db_path}")
            self.create_tables(conn)

    def create_tables(self, conn):
        """Execute schema script"""
        try:
            schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
            with open(schema_path, 'r') as f:
                conn.executescript(f.read())
            conn.commit()
        except Exception as e:
            print(f"Error creating tables: {e}")

    # ==========================
    # GENERIC EXECUTORS
    # ==========================

    def execute_query(self, query, params=()):
        """Execute a SELECT query using the persistent connection"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except Exception as e:
            print(f"Query Error: {e}")
            return []

    def execute_insert(self, query, params=()):
        """Execute an INSERT query and return ID"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Insert Error: {e}")
            raise e

    def execute_update(self, query, params=()):
        """Execute UPDATE or DELETE"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            print(f"Update Error: {e}")
            raise e

    # ==========================
    # USERS
    # ==========================

    def get_user_by_id(self, user_id):
        """Get user by ID"""
        rows = self.execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if rows:
            return dict(rows[0])
        return None

    # ==========================
    # PORTFOLIO & HOLDINGS
    # ==========================

    def get_user_holdings(self, user_id):
        """Get all holdings for a user using indexed lookup"""
        query = """
            SELECT 
                h.*,
                c.company_name,
                c.ticker_symbol,
                c.share_price as current_price,
                (h.quantity * c.share_price) as current_value,
                ((h.quantity * c.share_price) - h.total_invested) as profit_loss,
                CASE 
                    WHEN h.total_invested = 0 THEN 0 
                    ELSE (((h.quantity * c.share_price) - h.total_invested) / h.total_invested * 100) 
                END as profit_loss_percent
            FROM user_holdings h
            JOIN companies c ON h.company_id = c.company_id
            WHERE h.user_id = ? AND h.quantity > 0
        """
        return self.execute_query(query, (user_id,))

    def get_holding(self, user_id, company_id):
        """Get specific holding using unique index"""
        query = "SELECT * FROM user_holdings WHERE user_id = ? AND company_id = ?"
        rows = self.execute_query(query, (user_id, company_id))
        if rows:
            return dict(rows[0])
        return None
        
    def get_company_shareholders(self, company_id):
        """Get list of shareholders for a company"""
        query = """
            SELECT u.username, u.full_name, h.quantity, h.user_id 
            FROM user_holdings h
            JOIN users u ON h.user_id = u.user_id
            WHERE h.company_id = ? AND h.quantity > 0
            ORDER BY h.quantity DESC
        """
        return self.execute_query(query, (company_id,))

    def add_or_update_holding(self, user_id, company_id, quantity, price):
        """Add shares to portfolio (Buying)"""
        existing = self.get_holding(user_id, company_id)
        cost = quantity * price
        
        if existing:
            new_qty = existing['quantity'] + quantity
            new_total_invested = existing['total_invested'] + cost
            new_avg_price = new_total_invested / new_qty
            
            query = """
                UPDATE user_holdings 
                SET quantity = ?, average_buy_price = ?, total_invested = ?, last_updated = ?
                WHERE user_id = ? AND company_id = ?
            """
            self.execute_update(
                query, 
                (new_qty, new_avg_price, new_total_invested, datetime.now(), user_id, company_id)
            )
        else:
            query = """
                INSERT INTO user_holdings (user_id, company_id, quantity, average_buy_price, total_invested)
                VALUES (?, ?, ?, ?, ?)
            """
            self.execute_insert(query, (user_id, company_id, quantity, price, cost))

    def reduce_holding(self, user_id, company_id, quantity):
        """Remove shares from portfolio (Selling)"""
        existing = self.get_holding(user_id, company_id)
        if not existing or existing['quantity'] < quantity:
            raise ValueError("Insufficient shares")
            
        new_qty = existing['quantity'] - quantity
        cost_of_shares_sold = (quantity / existing['quantity']) * existing['total_invested']
        new_total_invested = existing['total_invested'] - cost_of_shares_sold
        
        if new_qty == 0:
            self.execute_update(
                "DELETE FROM user_holdings WHERE user_id = ? AND company_id = ?", 
                (user_id, company_id)
            )
        else:
            query = """
                UPDATE user_holdings 
                SET quantity = ?, total_invested = ?, last_updated = ?
                WHERE user_id = ? AND company_id = ?
            """
            self.execute_update(
                query, 
                (new_qty, new_total_invested, datetime.now(), user_id, company_id)
            )

    # ==========================
    # WALLET & TRANSACTIONS
    # ==========================
    
    def add_wallet_transaction(self, user_id, txn_type, amount, balance, desc):
        """Record a wallet transaction"""
        query = """
            INSERT INTO wallet_transactions (user_id, transaction_type, amount, balance_after, description)
            VALUES (?, ?, ?, ?, ?)
        """
        self.execute_insert(query, (user_id, txn_type, amount, balance, desc))

    def get_wallet_transactions(self, user_id, limit=50):
        """Load only required rows using Index and LIMIT to prevent UI lag"""
        query = """
            SELECT * FROM wallet_transactions 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """
        return self.execute_query(query, (user_id, limit))

    def add_transaction(self, buyer_id, company_id, qty, price, txn_type, seller_id=None):
        """Record a share transaction"""
        total = qty * price
        query = """
            INSERT INTO transactions (buyer_id, seller_id, company_id, quantity, price_per_share, total_amount, transaction_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.execute_insert(
            query, 
            (buyer_id, seller_id, company_id, qty, price, total, txn_type)
        )

    def get_recent_market_trades(self, limit=20):
        """Get recent trades from the entire market using Index"""
        query = """
            SELECT 
                t.*,
                c.ticker_symbol,
                b.username as buyer_name,
                s.username as seller_name
            FROM transactions t
            JOIN companies c ON t.company_id = c.company_id
            JOIN users b ON t.buyer_id = b.user_id
            LEFT JOIN users s ON t.seller_id = s.user_id
            WHERE t.transaction_type = 'trade'
            ORDER BY t.created_at DESC
            LIMIT ?
        """
        return self.execute_query(query, (limit,))

    # ==========================
    # LOANS & SYSTEM FEATURES
    # ==========================

    def create_loan(self, user_id, amount, rate, term):
        """Create a new loan with due date"""
        monthly_rate = rate / 100 / 12
        if monthly_rate == 0:
            payment = amount / term
        else:
            payment = amount * (monthly_rate * (1 + monthly_rate) ** term) / ((1 + monthly_rate) ** term - 1)
        
        due_date = datetime.now() + timedelta(days=30)
        
        query = """
            INSERT INTO loans (user_id, loan_amount, interest_rate, remaining_balance, monthly_payment, loan_term_months, status, due_date)
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
        """
        return self.execute_insert(query, (user_id, amount, rate, amount, payment, term, due_date))

    def get_user_loans(self, user_id):
        """Get all loans for a user"""
        rows = self.execute_query("SELECT * FROM loans WHERE user_id = ?", (user_id,))
        return [dict(row) for row in rows]

    def update_loan_balance(self, loan_id, new_balance, new_status):
        query = "UPDATE loans SET remaining_balance = ?, status = ? WHERE loan_id = ?"
        self.execute_update(query, (new_balance, new_status, loan_id))

    def add_loan_payment(self, loan_id, amount, principal, interest, balance):
        query = """
            INSERT INTO loan_payments (loan_id, payment_amount, principal_amount, interest_amount, remaining_balance)
            VALUES (?, ?, ?, ?, ?)
        """
        self.execute_insert(query, (loan_id, amount, principal, interest, balance))

# Global high-performance DB Instance
db = DBManager()