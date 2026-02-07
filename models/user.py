"""
User Model - Represents a user in the system
"""
import bcrypt
from datetime import datetime
from database.db_manager import db
from utils.validators import Validator


class User:
    """User model with authentication and wallet management"""
    
    def __init__(self, user_id=None, username=None, email=None, full_name=None, 
                 wallet_balance=0.0, created_at=None, last_login=None):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.wallet_balance = wallet_balance
        self.created_at = created_at
        self.last_login = last_login
    
    @classmethod
    def from_dict(cls, data):
        """Create User instance from dictionary"""
        if not data:
            return None
        return cls(
            user_id=data.get('user_id'),
            username=data.get('username'),
            email=data.get('email'),
            full_name=data.get('full_name'),
            wallet_balance=data.get('wallet_balance', 0.0),
            created_at=data.get('created_at'),
            last_login=data.get('last_login')
        )
    
    def to_dict(self):
        """Convert User to dictionary"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'wallet_balance': self.wallet_balance,
            'created_at': self.created_at,
            'last_login': self.last_login
        }
    
    @staticmethod
    def hash_password(password):
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password, hashed_password):
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    @classmethod
    def register(cls, username, password, email, full_name):
        """Register a new user"""
        # Validation
        if not Validator.validate_username(username):
            raise ValueError("Invalid username. Must be 3-20 alphanumeric characters.")
        
        if not Validator.validate_password(password):
            raise ValueError("Password must be at least 6 characters long.")
        
        if not Validator.validate_email(email):
            raise ValueError("Invalid email format.")
        
        if not full_name or len(full_name.strip()) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        
        # Check if username exists
        if db.get_user_by_username(username):
            raise ValueError("Username already exists.")
        
        # Hash password and create user
        password_hash = cls.hash_password(password)
        user_id = db.create_user(username, password_hash, email, full_name.strip())
        
        # Fetch and return created user
        user_data = db.get_user_by_id(user_id)
        return cls.from_dict(user_data)
    
    @classmethod
    def login(cls, username, password):
        """Authenticate user and return User instance"""
        user_data = db.get_user_by_username(username)
        
        if not user_data:
            raise ValueError("Invalid username or password.")
        
        if not cls.verify_password(password, user_data['password_hash']):
            raise ValueError("Invalid username or password.")
        
        # Update last login
        db.update_last_login(user_data['user_id'])
        
        return cls.from_dict(user_data)
    
    @classmethod
    def get_by_id(cls, user_id):
        """Get user by ID"""
        user_data = db.get_user_by_id(user_id)
        return cls.from_dict(user_data)
    
    @classmethod
    def get_by_username(cls, username):
        """Get user by username"""
        user_data = db.get_user_by_username(username)
        return cls.from_dict(user_data)
    
    def refresh(self):
        """Refresh user data from database"""
        user_data = db.get_user_by_id(self.user_id)
        if user_data:
            self.__dict__.update(self.from_dict(user_data).__dict__)
    
    def get_wallet_balance(self):
        """Get current wallet balance"""
        self.refresh()
        return self.wallet_balance
    
    def update_wallet_balance(self, new_balance):
        """Update wallet balance"""
        db.update_user_balance(self.user_id, new_balance)
        self.wallet_balance = new_balance
    
    def add_funds(self, amount, description="Deposit"):
        """Add funds to wallet"""
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        
        new_balance = self.wallet_balance + amount
        self.update_wallet_balance(new_balance)
        
        # Record transaction
        from utils.constants import WALLET_DEPOSIT
        db.add_wallet_transaction(
            self.user_id,
            WALLET_DEPOSIT,
            amount,
            new_balance,
            description
        )
        
        return new_balance
    
    def withdraw_funds(self, amount, description="Withdrawal"):
        """Withdraw funds from wallet"""
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        
        if amount > self.wallet_balance:
            raise ValueError("Insufficient funds.")
        
        new_balance = self.wallet_balance - amount
        self.update_wallet_balance(new_balance)
        
        # Record transaction
        from utils.constants import WALLET_WITHDRAWAL
        db.add_wallet_transaction(
            self.user_id,
            WALLET_WITHDRAWAL,
            amount,
            new_balance,
            description
        )
        
        return new_balance
    
    def transfer_to_user(self, recipient_user_id, amount, description=None):
        """Transfer money to another user"""
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        
        if self.user_id == recipient_user_id:
            raise ValueError("Cannot transfer to yourself.")
        
        if amount > self.wallet_balance:
            raise ValueError("Insufficient funds.")
        
        # Get recipient
        recipient = User.get_by_id(recipient_user_id)
        if not recipient:
            raise ValueError("Recipient not found.")
        
        # Deduct from sender
        new_sender_balance = self.wallet_balance - amount
        self.update_wallet_balance(new_sender_balance)
        
        # Add to recipient
        new_recipient_balance = recipient.wallet_balance + amount
        recipient.update_wallet_balance(new_recipient_balance)
        
        # Record transactions
        from utils.constants import WALLET_TRANSFER_OUT, WALLET_TRANSFER_IN
        
        db.add_wallet_transaction(
            self.user_id,
            WALLET_TRANSFER_OUT,
            amount,
            new_sender_balance,
            description or f"Transfer to {recipient.username}",
            recipient_user_id
        )
        
        db.add_wallet_transaction(
            recipient_user_id,
            WALLET_TRANSFER_IN,
            amount,
            new_recipient_balance,
            description or f"Transfer from {self.username}",
            self.user_id
        )
        
        return new_sender_balance
    
    def get_wallet_transactions(self, limit=50):
        """Get wallet transaction history"""
        return db.get_wallet_transactions(self.user_id, limit)
    
    def get_portfolio(self):
        """Get user's share portfolio"""
        holdings = db.get_user_holdings(self.user_id)
        
        total_invested = 0
        total_current_value = 0
        
        for holding in holdings:
            invested = holding['total_invested']
            current_value = holding['quantity'] * holding['share_price']
            
            holding['current_value'] = current_value
            holding['profit_loss'] = current_value - invested
            holding['profit_loss_percent'] = ((current_value - invested) / invested * 100) if invested > 0 else 0
            
            total_invested += invested
            total_current_value += current_value
        
        return {
            'holdings': holdings,
            'total_invested': total_invested,
            'total_current_value': total_current_value,
            'total_profit_loss': total_current_value - total_invested,
            'total_profit_loss_percent': ((total_current_value - total_invested) / total_invested * 100) if total_invested > 0 else 0
        }
    
    def get_transaction_history(self, limit=50):
        """Get user's transaction history"""
        return db.get_user_transactions(self.user_id, limit)
    
    def get_companies_owned(self):
        """Get companies owned by this user"""
        return db.get_companies_by_owner(self.user_id)
    
    def get_active_loans(self):
        """Get user's active loans"""
        loans = db.get_user_loans(self.user_id)
        return [loan for loan in loans if loan['status'] == 'active']
    
    def get_total_debt(self):
        """Get total outstanding debt"""
        active_loans = self.get_active_loans()
        return sum(loan['remaining_balance'] for loan in active_loans)
    
    def get_net_worth(self):
        """Calculate user's net worth"""
        portfolio = self.get_portfolio()
        total_debt = self.get_total_debt()
        
        net_worth = self.wallet_balance + portfolio['total_current_value'] - total_debt
        
        return {
            'wallet_balance': self.wallet_balance,
            'portfolio_value': portfolio['total_current_value'],
            'total_debt': total_debt,
            'net_worth': net_worth
        }
    
    def __repr__(self):
        return f"<User(id={self.user_id}, username='{self.username}', balance={self.wallet_balance})>"
