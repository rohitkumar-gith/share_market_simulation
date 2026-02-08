"""
User Model
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
        """Create User object from database row"""
        if not row:
            return None
        
        try:
            is_admin_val = row['is_admin']
        except Exception:
            is_admin_val = 0

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
        """Authenticate user"""
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
        """Register new user"""
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
        updated = User.get_by_id(self.user_id)
        if updated:
            self.wallet_balance = updated.wallet_balance
            self.is_admin = updated.is_admin

    @staticmethod
    def get_by_id(user_id):
        row = db.execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return User.from_db_row(row[0]) if row else None

    @staticmethod
    def get_by_username(username):
        row = db.execute_query("SELECT * FROM users WHERE username = ?", (username,))
        return User.from_db_row(row[0]) if row else None
        
    def get_portfolio(self):
        """Get user portfolio (holdings)"""
        holdings = db.get_user_holdings(self.user_id)
        
        # Calculate totals
        total_invested = sum(h['total_invested'] for h in holdings)
        total_current_value = sum(h['current_value'] for h in holdings)
        total_profit_loss = total_current_value - total_invested
        
        return {
            'holdings': holdings,
            'total_invested': total_invested,
            'total_current_value': total_current_value,
            'total_profit_loss': total_profit_loss
        }

    def get_active_loans(self):
        """Get all active loans for this user (MISSING METHOD ADDED)"""
        return db.get_user_loans(self.user_id)

    def get_net_worth(self):
        """Calculate total net worth (wallet + portfolio - loans)"""
        portfolio = self.get_portfolio()
        assets_value = portfolio['total_current_value']
        
        # Subtract loan debt
        loans = self.get_active_loans()
        debt = sum(l['remaining_balance'] for l in loans)
        
        return (self.wallet_balance + assets_value) - debt
        
    def add_funds(self, amount, description="Deposit"):
        if amount <= 0: return False
        
        new_balance = self.wallet_balance + amount
        db.execute_update("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_balance, self.user_id))
        db.add_wallet_transaction(self.user_id, 'DEPOSIT', amount, new_balance, description)
        
        self.wallet_balance = new_balance
        return True
        
    def withdraw_funds(self, amount, description="Withdrawal"):
        if amount <= 0 or self.wallet_balance < amount: return False
        
        new_balance = self.wallet_balance - amount
        db.execute_update("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_balance, self.user_id))
        db.add_wallet_transaction(self.user_id, 'WITHDRAW', amount, new_balance, description)
        
        self.wallet_balance = new_balance
        return True