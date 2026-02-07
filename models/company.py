"""
Company Model - Represents a company in the stock market
"""
from datetime import datetime
from database.db_manager import db
from utils.validators import Validator
import config


class Company:
    """Company model with IPO and financial management"""
    
    def __init__(self, company_id=None, company_name=None, owner_id=None,
                 ticker_symbol=None, share_price=100.0, total_shares=0,
                 available_shares=0, company_wallet=0.0, net_worth=0.0,
                 description=None, created_at=None):
        self.company_id = company_id
        self.company_name = company_name
        self.owner_id = owner_id
        self.ticker_symbol = ticker_symbol
        self.share_price = share_price
        self.total_shares = total_shares
        self.available_shares = available_shares
        self.company_wallet = company_wallet
        self.net_worth = net_worth
        self.description = description
        self.created_at = created_at
    
    @classmethod
    def from_dict(cls, data):
        """Create Company instance from dictionary"""
        if not data:
            return None
        return cls(
            company_id=data.get('company_id'),
            company_name=data.get('company_name'),
            owner_id=data.get('owner_id'),
            ticker_symbol=data.get('ticker_symbol'),
            share_price=data.get('share_price', 100.0),
            total_shares=data.get('total_shares', 0),
            available_shares=data.get('available_shares', 0),
            company_wallet=data.get('company_wallet', 0.0),
            net_worth=data.get('net_worth', 0.0),
            description=data.get('description'),
            created_at=data.get('created_at')
        )
    
    def to_dict(self):
        """Convert Company to dictionary"""
        return {
            'company_id': self.company_id,
            'company_name': self.company_name,
            'owner_id': self.owner_id,
            'ticker_symbol': self.ticker_symbol,
            'share_price': self.share_price,
            'total_shares': self.total_shares,
            'available_shares': self.available_shares,
            'company_wallet': self.company_wallet,
            'net_worth': self.net_worth,
            'description': self.description,
            'created_at': self.created_at
        }
    
    @classmethod
    def create(cls, owner_id, company_name, ticker_symbol, initial_share_price,
               total_shares, description=None):
        """Create a new company"""
        # Validation
        if not company_name or len(company_name.strip()) < 3:
            raise ValueError("Company name must be at least 3 characters.")
        
        if not Validator.validate_ticker(ticker_symbol):
            raise ValueError("Ticker must be 2-6 uppercase letters.")
        
        if not Validator.validate_positive_number(initial_share_price):
            raise ValueError("Share price must be positive.")
        
        if not Validator.validate_positive_integer(total_shares):
            raise ValueError("Total shares must be a positive integer.")
        
        if total_shares < 100:
            raise ValueError("Total shares must be at least 100.")
        
        # Check price limits
        if initial_share_price < config.MINIMUM_SHARE_PRICE:
            raise ValueError(f"Share price must be at least ₹{config.MINIMUM_SHARE_PRICE}")
        
        if initial_share_price > config.MAXIMUM_SHARE_PRICE:
            raise ValueError(f"Share price cannot exceed ₹{config.MAXIMUM_SHARE_PRICE}")
        
        # Create company
        company_id = db.create_company(
            company_name.strip(),
            owner_id,
            ticker_symbol.upper(),
            initial_share_price,
            total_shares,
            description
        )
        
        # Fetch and return created company
        company_data = db.get_company_by_id(company_id)
        return cls.from_dict(company_data)
    
    @classmethod
    def get_by_id(cls, company_id):
        """Get company by ID"""
        company_data = db.get_company_by_id(company_id)
        return cls.from_dict(company_data)
    
    @classmethod
    def get_all(cls):
        """Get all companies"""
        companies_data = db.get_all_companies()
        return [cls.from_dict(data) for data in companies_data]
    
    @classmethod
    def get_by_owner(cls, owner_id):
        """Get companies owned by user"""
        companies_data = db.get_companies_by_owner(owner_id)
        return [cls.from_dict(data) for data in companies_data]
    
    def refresh(self):
        """Refresh company data from database"""
        company_data = db.get_company_by_id(self.company_id)
        if company_data:
            self.__dict__.update(self.from_dict(company_data).__dict__)
    
    def update_share_price(self, new_price):
        """Update share price"""
        if new_price < config.MINIMUM_SHARE_PRICE:
            new_price = config.MINIMUM_SHARE_PRICE
        elif new_price > config.MAXIMUM_SHARE_PRICE:
            new_price = config.MAXIMUM_SHARE_PRICE
        
        db.update_company_share_price(self.company_id, new_price)
        self.share_price = new_price
        self.update_net_worth()
    
    def update_available_shares(self, available_shares):
        """Update available shares"""
        if available_shares < 0:
            raise ValueError("Available shares cannot be negative.")
        
        if available_shares > self.total_shares:
            raise ValueError("Available shares cannot exceed total shares.")
        
        db.update_company_available_shares(self.company_id, available_shares)
        self.available_shares = available_shares
    
    def add_to_wallet(self, amount, description="Deposit"):
        """Add funds to company wallet"""
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        
        new_balance = self.company_wallet + amount
        db.update_company_wallet(self.company_id, new_balance)
        self.company_wallet = new_balance
        
        # Record transaction
        from utils.constants import COMPANY_DEPOSIT
        db.execute_insert(
            """INSERT INTO company_wallet_transactions 
               (company_id, transaction_type, amount, balance_after, description)
               VALUES (?, ?, ?, ?, ?)""",
            (self.company_id, COMPANY_DEPOSIT, amount, new_balance, description)
        )
        
        self.update_net_worth()
        return new_balance
    
    def withdraw_from_wallet(self, amount, description="Withdrawal"):
        """Withdraw funds from company wallet"""
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        
        if amount > self.company_wallet:
            raise ValueError("Insufficient company funds.")
        
        new_balance = self.company_wallet - amount
        db.update_company_wallet(self.company_id, new_balance)
        self.company_wallet = new_balance
        
        # Record transaction
        from utils.constants import COMPANY_WITHDRAWAL
        db.execute_insert(
            """INSERT INTO company_wallet_transactions 
               (company_id, transaction_type, amount, balance_after, description)
               VALUES (?, ?, ?, ?, ?)""",
            (self.company_id, COMPANY_WITHDRAWAL, amount, new_balance, description)
        )
        
        self.update_net_worth()
        return new_balance
    
    def add_asset(self, asset_name, asset_value, asset_type=None, description=None):
        """Add company asset"""
        if not asset_name or len(asset_name.strip()) < 2:
            raise ValueError("Asset name must be at least 2 characters.")
        
        if not Validator.validate_positive_number(asset_value):
            raise ValueError("Asset value must be positive.")
        
        asset_id = db.add_company_asset(
            self.company_id,
            asset_name.strip(),
            asset_value,
            asset_type,
            description
        )
        
        self.update_net_worth()
        return asset_id
    
    def get_assets(self):
        """Get all company assets"""
        return db.get_company_assets(self.company_id)
    
    def get_total_assets_value(self):
        """Get total value of all assets"""
        return db.get_company_total_assets_value(self.company_id)
    
    def calculate_net_worth(self):
        """Calculate company net worth"""
        # Market capitalization (total shares * current price)
        market_cap = self.total_shares * self.share_price
        
        # Company wallet balance
        wallet_value = self.company_wallet
        
        # Total assets value
        assets_value = self.get_total_assets_value()
        
        # Net worth = market cap + wallet + assets
        net_worth = market_cap + wallet_value + assets_value
        
        return net_worth
    
    def update_net_worth(self):
        """Update company net worth in database"""
        net_worth = self.calculate_net_worth()
        db.update_company_net_worth(self.company_id, net_worth)
        self.net_worth = net_worth
        return net_worth
    
    def get_market_cap(self):
        """Get market capitalization"""
        return self.total_shares * self.share_price
    
    def get_shareholders(self):
        """Get all shareholders"""
        return db.get_company_shareholders(self.company_id)
    
    def get_shares_held_by_public(self):
        """Get number of shares held by public"""
        return self.total_shares - self.available_shares
    
    def issue_dividend(self, dividend_per_share):
        """Issue dividend to shareholders"""
        if dividend_per_share <= 0:
            raise ValueError("Dividend per share must be positive.")
        
        # Get all shareholders
        shareholders = self.get_shareholders()
        
        if not shareholders:
            raise ValueError("No shareholders to pay dividends.")
        
        # Calculate total dividend amount
        total_dividend = sum(sh['quantity'] * dividend_per_share for sh in shareholders)
        
        if total_dividend > self.company_wallet:
            raise ValueError(f"Insufficient funds. Need ₹{total_dividend:,.2f}, have ₹{self.company_wallet:,.2f}")
        
        # Pay dividends to each shareholder
        from models.user import User
        from utils.constants import WALLET_DIVIDEND_RECEIVED, COMPANY_DIVIDEND_PAID
        
        for shareholder in shareholders:
            dividend_amount = shareholder['quantity'] * dividend_per_share
            
            # Add to user wallet
            user = User.get_by_id(shareholder['user_id'])
            new_balance = user.wallet_balance + dividend_amount
            user.update_wallet_balance(new_balance)
            
            # Record wallet transaction
            db.add_wallet_transaction(
                shareholder['user_id'],
                WALLET_DIVIDEND_RECEIVED,
                dividend_amount,
                new_balance,
                f"Dividend from {self.company_name} ({shareholder['quantity']} shares @ ₹{dividend_per_share})"
            )
        
        # Deduct from company wallet
        new_company_balance = self.company_wallet - total_dividend
        db.update_company_wallet(self.company_id, new_company_balance)
        self.company_wallet = new_company_balance
        
        # Record company transaction
        db.execute_insert(
            """INSERT INTO company_wallet_transactions 
               (company_id, transaction_type, amount, balance_after, description)
               VALUES (?, ?, ?, ?, ?)""",
            (self.company_id, COMPANY_DIVIDEND_PAID, total_dividend, new_company_balance,
             f"Dividend payment: ₹{dividend_per_share} per share")
        )
        
        # Record dividend
        db.create_dividend(self.company_id, dividend_per_share, total_dividend)
        
        return {
            'dividend_per_share': dividend_per_share,
            'total_amount': total_dividend,
            'shareholders_count': len(shareholders)
        }
    
    def get_price_history(self, days=30):
        """Get historical share prices (placeholder for future implementation)"""
        # This would require a price_history table
        # For now, return current price
        return [{'date': datetime.now(), 'price': self.share_price}]
    
    def __repr__(self):
        return f"<Company(id={self.company_id}, name='{self.company_name}', ticker='{self.ticker_symbol}', price={self.share_price})>"
