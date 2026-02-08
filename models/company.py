"""
Company Model
"""
from database.db_manager import db

class Company:
    def __init__(self, company_id, company_name, owner_id, ticker_symbol, share_price, 
                 total_shares, available_shares, company_wallet=0.0, net_worth=0.0, 
                 is_bankrupt=0, description=None):
        self.company_id = company_id
        self.company_name = company_name
        self.owner_id = owner_id
        self.ticker_symbol = ticker_symbol
        self.share_price = share_price
        self.total_shares = total_shares
        self.available_shares = available_shares
        self.company_wallet = company_wallet
        self.net_worth = net_worth
        self.is_bankrupt = bool(is_bankrupt)
        self.description = description

    @classmethod
    def from_db_row(cls, row):
        if not row: return None
        
        # FIX: Safe access for SQLite rows without .get()
        try: c_wallet = row['company_wallet']
        except: c_wallet = 0.0
            
        try: c_net_worth = row['net_worth']
        except: c_net_worth = 0.0
            
        try: c_bankrupt = row['is_bankrupt']
        except: c_bankrupt = 0
            
        try: c_desc = row['description']
        except: c_desc = None

        return cls(
            company_id=row['company_id'],
            company_name=row['company_name'],
            owner_id=row['owner_id'],
            ticker_symbol=row['ticker_symbol'],
            share_price=row['share_price'],
            total_shares=row['total_shares'],
            available_shares=row['available_shares'],
            company_wallet=c_wallet,
            net_worth=c_net_worth,
            is_bankrupt=c_bankrupt,
            description=c_desc
        )

    def to_dict(self):
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
            'is_bankrupt': self.is_bankrupt,
            'description': self.description
        }

    # ==========================
    # FACTORY METHODS
    # ==========================
    @staticmethod
    def create(owner_id, name, ticker, price, total_shares, description):
        existing = db.execute_query("SELECT * FROM companies WHERE ticker_symbol = ?", (ticker,))
        if existing:
            raise ValueError(f"Ticker {ticker} already exists")

        query = """
            INSERT INTO companies (owner_id, company_name, ticker_symbol, share_price, total_shares, available_shares, description, company_wallet, net_worth)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, 0.0)
        """
        company_id = db.execute_insert(query, (owner_id, name, ticker, price, total_shares, total_shares, description))
        db.execute_insert("INSERT INTO price_history (company_id, price) VALUES (?, ?)", (company_id, price))
        return Company.get_by_id(company_id)

    @staticmethod
    def get_by_id(company_id):
        rows = db.execute_query("SELECT * FROM companies WHERE company_id = ?", (company_id,))
        return Company.from_db_row(rows[0]) if rows else None

    @staticmethod
    def get_all():
        rows = db.execute_query("SELECT * FROM companies")
        return [Company.from_db_row(row) for row in rows]

    @staticmethod
    def get_by_owner(owner_id):
        rows = db.execute_query("SELECT * FROM companies WHERE owner_id = ?", (owner_id,))
        return [Company.from_db_row(row) for row in rows]

    # ==========================
    # OPERATIONS
    # ==========================
    def update_share_price(self, new_price):
        db.execute_update("UPDATE companies SET share_price = ? WHERE company_id = ?", (new_price, self.company_id))
        self.share_price = new_price

    def update_wallet(self, amount):
        """Update company wallet balance"""
        new_bal = self.company_wallet + amount
        db.execute_update("UPDATE companies SET company_wallet = ? WHERE company_id = ?", (new_bal, self.company_id))
        self.company_wallet = new_bal
        return new_bal

    def add_to_wallet(self, amount, description=None):
        """Alias for update_wallet to support older code (FIX ADDED)"""
        return self.update_wallet(amount)

    def update_available_shares(self, new_quantity):
        """Update available shares in DB and Object"""
        db.execute_update("UPDATE companies SET available_shares = ? WHERE company_id = ?", (new_quantity, self.company_id))
        self.available_shares = new_quantity

    def get_market_cap(self):
        return self.share_price * self.total_shares
    
    def get_total_assets_value(self):
        """Calculate value of all assets owned by company"""
        query = "SELECT SUM(acquired_price) as total FROM owned_assets WHERE owner_id = ? AND owner_type = 'COMPANY'"
        result = db.execute_query(query, (self.company_id,))
        if result and result[0]['total']:
            return result[0]['total']
        return 0.0

    def get_shareholders(self):
        return db.get_company_shareholders(self.company_id)