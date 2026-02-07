"""
Company Service - Handles company management operations
"""
from models.company import Company
from models.share import Share
from models.user import User
from database.db_manager import db
from datetime import datetime


class CompanyService:
    """Service for company management operations"""
    
    @staticmethod
    def create_company(owner_id, company_name, ticker_symbol, initial_share_price, 
                      total_shares, description=None):
        """
        Create a new company
        
        Args:
            owner_id: Owner user ID
            company_name: Company name
            ticker_symbol: Ticker symbol (2-6 uppercase letters)
            initial_share_price: Initial share price
            total_shares: Total shares to issue
            description: Company description (optional)
            
        Returns:
            Dictionary with success status and company data
        """
        try:
            company = Company.create(
                owner_id,
                company_name,
                ticker_symbol,
                initial_share_price,
                total_shares,
                description
            )
            
            return {
                'success': True,
                'message': f'Company {company_name} created successfully',
                'company': company.to_dict()
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def issue_ipo(company_id, shares_to_issue, issue_price=None):
        """
        Issue IPO for a company
        
        Args:
            company_id: Company ID
            shares_to_issue: Number of shares to issue
            issue_price: Issue price (optional, uses current price if None)
            
        Returns:
            Dictionary with success status and IPO details
        """
        try:
            result = Share.issue_ipo(company_id, shares_to_issue, issue_price)
            
            return {
                'success': True,
                'message': f'IPO issued successfully',
                'details': result
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def add_company_funds(company_id, amount, owner_id, description="Deposit"):
        """
        Add funds to company wallet
        
        Args:
            company_id: Company ID
            amount: Amount to add
            owner_id: Owner user ID (for verification)
            description: Description
            
        Returns:
            Dictionary with success status
        """
        try:
            company = Company.get_by_id(company_id)
            if not company:
                raise ValueError("Company not found")
            
            if company.owner_id != owner_id:
                raise ValueError("Only company owner can add funds")
            
            # Deduct from owner's wallet
            owner = User.get_by_id(owner_id)
            owner.withdraw_funds(amount, f"Transfer to {company.company_name}")
            
            # Add to company wallet
            new_balance = company.add_to_wallet(amount, description)
            
            return {
                'success': True,
                'message': f'₹{amount:,.2f} added to company wallet',
                'new_balance': new_balance
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def withdraw_company_funds(company_id, amount, owner_id, description="Withdrawal"):
        """
        Withdraw funds from company wallet
        
        Args:
            company_id: Company ID
            amount: Amount to withdraw
            owner_id: Owner user ID (for verification)
            description: Description
            
        Returns:
            Dictionary with success status
        """
        try:
            company = Company.get_by_id(company_id)
            if not company:
                raise ValueError("Company not found")
            
            if company.owner_id != owner_id:
                raise ValueError("Only company owner can withdraw funds")
            
            # Withdraw from company wallet
            new_balance = company.withdraw_from_wallet(amount, description)
            
            # Add to owner's wallet
            owner = User.get_by_id(owner_id)
            owner.add_funds(amount, f"Withdrawal from {company.company_name}")
            
            return {
                'success': True,
                'message': f'₹{amount:,.2f} withdrawn from company wallet',
                'new_balance': new_balance
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def add_company_asset(company_id, owner_id, asset_name, asset_value, 
                         asset_type=None, description=None):
        """
        Add an asset to company
        
        Args:
            company_id: Company ID
            owner_id: Owner user ID (for verification)
            asset_name: Asset name
            asset_value: Asset value
            asset_type: Asset type (optional)
            description: Description (optional)
            
        Returns:
            Dictionary with success status
        """
        try:
            company = Company.get_by_id(company_id)
            if not company:
                raise ValueError("Company not found")
            
            if company.owner_id != owner_id:
                raise ValueError("Only company owner can add assets")
            
            asset_id = company.add_asset(asset_name, asset_value, asset_type, description)
            
            return {
                'success': True,
                'message': f'Asset "{asset_name}" added successfully',
                'asset_id': asset_id
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def issue_dividend(company_id, owner_id, dividend_per_share):
        """
        Issue dividend to shareholders
        
        Args:
            company_id: Company ID
            owner_id: Owner user ID (for verification)
            dividend_per_share: Dividend amount per share
            
        Returns:
            Dictionary with success status and dividend details
        """
        try:
            company = Company.get_by_id(company_id)
            if not company:
                raise ValueError("Company not found")
            
            if company.owner_id != owner_id:
                raise ValueError("Only company owner can issue dividends")
            
            result = company.issue_dividend(dividend_per_share)
            
            return {
                'success': True,
                'message': f'Dividend of ₹{dividend_per_share} per share issued',
                'details': result
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def get_company_details(company_id):
        """Get detailed company information"""
        try:
            company = Company.get_by_id(company_id)
            if not company:
                return None
            
            assets = company.get_assets()
            shareholders = company.get_shareholders()
            
            return {
                'company': company.to_dict(),
                'assets': assets,
                'total_assets_value': company.get_total_assets_value(),
                'shareholders': shareholders,
                'market_cap': company.get_market_cap(),
                'shares_held_by_public': company.get_shares_held_by_public()
            }
        except Exception as e:
            return None
    
    @staticmethod
    def get_user_companies(user_id):
        """Get companies owned by user"""
        companies = Company.get_by_owner(user_id)
        return [c.to_dict() for c in companies]
    
    @staticmethod
    def update_share_price(company_id, owner_id, new_price):
        """
        Update company share price (owner only)
        
        Args:
            company_id: Company ID
            owner_id: Owner user ID (for verification)
            new_price: New share price
            
        Returns:
            Dictionary with success status
        """
        try:
            company = Company.get_by_id(company_id)
            if not company:
                raise ValueError("Company not found")
            
            if company.owner_id != owner_id:
                raise ValueError("Only company owner can update share price")
            
            company.update_share_price(new_price)
            
            return {
                'success': True,
                'message': f'Share price updated to ₹{new_price:,.2f}',
                'new_price': new_price
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def get_company_financial_summary(company_id):
        """Get company financial summary"""
        try:
            company = Company.get_by_id(company_id)
            if not company:
                return None
            
            # Get wallet transactions
            query = """
                SELECT * FROM company_wallet_transactions 
                WHERE company_id = ? 
                ORDER BY created_at DESC 
                LIMIT 50
            """
            transactions = db.execute_query(query, (company_id,))
            
            return {
                'wallet_balance': company.company_wallet,
                'net_worth': company.net_worth,
                'market_cap': company.get_market_cap(),
                'total_shares': company.total_shares,
                'available_shares': company.available_shares,
                'share_price': company.share_price,
                'total_assets': company.get_total_assets_value(),
                'recent_transactions': [dict(t) for t in transactions]
            }
        except Exception as e:
            return None
    
    @staticmethod
    def get_all_companies():
        """Get all companies"""
        companies = Company.get_all()
        return [c.to_dict() for c in companies]
    
    @staticmethod
    def get_company_shareholders(company_id):
        """Get company shareholders"""
        company = Company.get_by_id(company_id)
        if not company:
            return []
        
        return company.get_shareholders()
    
    @staticmethod
    def calculate_ownership_percentage(company_id, user_id):
        """Calculate user's ownership percentage in company"""
        company = Company.get_by_id(company_id)
        if not company:
            return 0
        
        holding = db.get_holding(user_id, company_id)
        if not holding:
            return 0
        
        total_issued = company.total_shares - company.available_shares
        if total_issued == 0:
            return 0
        
        return (holding['quantity'] / total_issued) * 100


# Global company service instance
company_service = CompanyService()
