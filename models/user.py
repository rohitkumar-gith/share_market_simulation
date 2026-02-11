"""
User Model - Optimized for High-Performance Simulation
"""
import bcrypt
from database.db_manager import db
import config

class User:
    def __init__(self, user_id, username, email, full_name, wallet_balance, is_admin=0):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.wallet_balance = wallet_balance
        self.is_admin = bool(is_admin)

    @classmethod
    def from_db_row(cls, row):
        """Create User object from database row with safety checks"""
        if not row:
            return None
        
        # Safe retrieval of is_admin to support various schema versions
        is_admin_val = row['is_admin'] if 'is_admin' in row.keys() else 0

        return cls(
            user_id=row['user_id'],
            username=row['username'],
            email=row['email'],
            full_name=row['full_name'],
            wallet_balance=row['wallet_balance'],
            is_admin=is_admin_val
        )

    # ==========================
    # AUTH METHODS
    # ==========================

    @staticmethod
    def login(username, password):
        """Authenticate user with optimized indexed lookup"""
        rows = db.execute_query("SELECT * FROM users WHERE username = ?", (username,))
        if not rows:
            raise ValueError("User not found")
        
        row = rows[0]
        stored_hash = row['password_hash']
        
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            return User.from_db_row(row)
        else:
            raise ValueError("Invalid password")

    @staticmethod
    def register(username, password, email, full_name):
        """Register new user with default simulation balance"""
        if User.get_by_username(username):
            raise ValueError("Username already exists")
            
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        query = """
            INSERT INTO users (username, password_hash, email, full_name, wallet_balance, is_admin)
            VALUES (?, ?, ?, ?, ?, 0)
        """
        try:
            user_id = db.execute_insert(
                query, 
                (username, hashed.decode('utf-8'), email, full_name, config.INITIAL_USER_BALANCE)
            )
            return User.get_by_id(user_id)
        except Exception as e:
            raise ValueError(f"Registration failed: {str(e)}")

    # ==========================
    # DATA METHODS
    # ==========================
    
    def refresh(self):
        """Refresh user data from DB without re-instantiating object"""
        updated = User.get_by_id(self.user_id)
        if updated:
            self.wallet_balance = updated.wallet_balance
            self.is_admin = updated.is_admin

    @staticmethod
    def get_by_id(user_id):
        """Primary key lookup (Fastest)"""
        row = db.execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return User.from_db_row(row[0]) if row else None

    @staticmethod
    def get_by_username(username):
        """Indexed unique lookup"""
        row = db.execute_query("SELECT * FROM users WHERE username = ?", (username,))
        return User.from_db_row(row[0]) if row else None
        
    def get_portfolio(self):
        """
        Get user portfolio (holdings).
        Optimization: Uses indexed join and calculates totals in Python 
        to avoid redundant 'SUM' queries in SQLite.
        """
        holdings = db.get_user_holdings(self.user_id)
        
        # Calculate totals in-memory for speed
        total_invested = 0
        total_current_value = 0
        
        processed_holdings = []
        for h in holdings:
            # Convert row to dict to ensure compatibility
            holding_dict = dict(h)
            total_invested += holding_dict['total_invested']
            total_current_value += holding_dict['current_value']
            processed_holdings.append(holding_dict)
        
        return {
            'holdings': processed_holdings,
            'total_invested': total_invested,
            'total_current_value': total_current_value,
            'total_profit_loss': total_current_value - total_invested
        }

    def get_active_loans(self):
        """Fast indexed retrieval of active loans"""
        return db.get_user_loans(self.user_id)

    def get_net_worth(self):
        """High-performance net worth calculation"""
        portfolio = self.get_portfolio()
        assets_value = portfolio['total_current_value']
        
        # Subtract loan debt
        loans = self.get_active_loans()
        debt = sum(l['remaining_balance'] for l in loans)
        
        return (self.wallet_balance + assets_value) - debt
        
    def add_funds(self, amount, description="Deposit"):
        """Update wallet balance with audit trail"""
        if amount <= 0: return False
        
        new_balance = self.wallet_balance + amount
        db.execute_update("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_balance, self.user_id))
        db.add_wallet_transaction(self.user_id, 'DEPOSIT', amount, new_balance, description)
        
        self.wallet_balance = new_balance
        return True
        
    def withdraw_funds(self, amount, description="Withdrawal"):
        """Deduct from wallet balance with sufficient funds check"""
        if amount <= 0 or self.wallet_balance < amount: return False
        
        new_balance = self.wallet_balance - amount
        db.execute_update("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_balance, self.user_id))
        db.add_wallet_transaction(self.user_id, 'WITHDRAW', amount, new_balance, description)
        
        self.wallet_balance = new_balance
        return True

    def transfer_to_user(self, recipient_id, amount, description=None):
        """
        Transfer funds to another user.
        Uses optimized indexed lookups for sender/recipient updates.
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if self.wallet_balance < amount:
            raise ValueError("Insufficient funds")
            
        recipient = User.get_by_id(recipient_id)
        if not recipient:
            raise ValueError("Recipient not found")
            
        # Deduct from sender
        new_sender_balance = self.wallet_balance - amount
        db.execute_update("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_sender_balance, self.user_id))
        db.add_wallet_transaction(
            self.user_id, 
            'transfer_out', 
            amount, 
            new_sender_balance, 
            description or f"Transfer to {recipient.username}"
        )
        self.wallet_balance = new_sender_balance
        
        # Add to recipient
        new_recipient_balance = recipient.wallet_balance + amount
        db.execute_update("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_recipient_balance, recipient.user_id))
        db.add_wallet_transaction(
            recipient.user_id, 
            'transfer_in', 
            amount, 
            new_recipient_balance, 
            description or f"Transfer from {self.username}"
        )
        
        return self.wallet_balance