"""
Company Service - Manage companies, dividends, and wallets
"""
from database.db_manager import db
from models.company import Company
from models.user import User
from models.transaction import Transaction

class CompanyService:
    
    # ==========================
    # CORE MANAGEMENT
    # ==========================
    
    def create_company(self, user_id, name, ticker, price, total_shares, description):
        """Create a new company"""
        try:
            company = Company.create(user_id, name, ticker, price, total_shares, description)
            return {'success': True, 'message': f"Company {name} ({ticker}) created successfully!"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_user_companies(self, user_id):
        """Get companies owned by user"""
        companies = Company.get_by_owner(user_id)
        return [c.to_dict() for c in companies] # Return as dicts for UI

    def get_all_companies(self):
        """Get all companies"""
        companies = Company.get_all()
        return [c.to_dict() for c in companies]

    def get_company_details(self, company_id):
        """Get detailed company information"""
        try:
            company = Company.get_by_id(company_id)
            if not company:
                return None
            
            # Using AssetService for assets now, but basic list can be fetched here
            shareholders = company.get_shareholders()
            
            return {
                'company': company.to_dict(),
                'market_cap': company.get_market_cap(),
                'shareholders': shareholders,
                'total_assets_value': company.get_total_assets_value()
            }
        except Exception as e:
            print(f"Error getting details: {e}")
            return None

    # ==========================
    # WALLET & FINANCE (UPDATED)
    # ==========================

    def deposit_to_wallet(self, company_id, user_id, amount):
        """Owner deposits personal money into company wallet (Renamed from add_company_funds)"""
        try:
            company = Company.get_by_id(company_id)
            if company.owner_id != user_id:
                return {'success': False, 'message': "Only owner can deposit funds"}
            
            user = User.get_by_id(user_id)
            if user.wallet_balance < amount:
                return {'success': False, 'message': "Insufficient personal funds"}
            
            # Transfer
            user.withdraw_funds(amount, f"Invested in {company.company_name}")
            company.update_wallet(amount)
            
            # Record
            db.execute_insert(
                "INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                (company_id, 'DEPOSIT', amount, company.company_wallet, "Owner Investment")
            )
            
            # Check if bankruptcy can be removed
            if company.is_bankrupt and company.company_wallet >= 10000:
                db.execute_update("UPDATE companies SET is_bankrupt = 0 WHERE company_id = ?", (company_id,))
            
            return {'success': True, 'message': "Funds deposited successfully"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def withdraw_from_wallet(self, company_id, user_id, amount):
        """Owner withdraws money from company wallet (Renamed from withdraw_company_funds)"""
        try:
            company = Company.get_by_id(company_id)
            if company.owner_id != user_id:
                return {'success': False, 'message': "Only owner can withdraw funds"}
            
            if company.company_wallet < amount:
                return {'success': False, 'message': "Insufficient company funds"}
            
            # Transfer
            company.update_wallet(-amount)
            user = User.get_by_id(user_id)
            user.add_funds(amount, f"Withdrawal from {company.company_name}")
            
            # Record
            db.execute_insert(
                "INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                (company_id, 'WITHDRAW', amount, company.company_wallet, "Owner Withdrawal")
            )
            
            # Check Bankruptcy logic
            if company.company_wallet < 10000 and not company.is_bankrupt:
                db.execute_update("UPDATE companies SET is_bankrupt = 1 WHERE company_id = ?", (company_id,))
                
            return {'success': True, 'message': "Funds withdrawn successfully"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def issue_dividend(self, company_id, user_id, amount_per_share):
        """Issue dividend to shareholders"""
        try:
            company = Company.get_by_id(company_id)
            if not company:
                return {'success': False, 'message': "Company not found"}
            
            if company.owner_id != user_id:
                return {'success': False, 'message': "Only owner can issue dividends"}
            
            total_payout = amount_per_share * company.total_shares
            
            if company.company_wallet < total_payout:
                return {'success': False, 'message': f"Insufficient funds. Need ₹{total_payout:,.2f}"}
            
            # Deduct from company wallet
            company.update_wallet(-total_payout)
            
            # Record Transaction
            db.execute_insert(
                "INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                (company_id, 'DIVIDEND', total_payout, company.company_wallet, f"Dividend: {amount_per_share}/share")
            )
            
            # Distribute to shareholders
            shareholders = company.get_shareholders()
            for holder in shareholders:
                payout = holder['quantity'] * amount_per_share
                User.get_by_id(holder['user_id']).add_funds(payout, f"Dividend from {company.company_name}")
                
            return {'success': True, 'message': "Dividends issued successfully"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ==========================
    # DATA & ANALYTICS (RESTORED)
    # ==========================

    def get_company_financial_summary(self, company_id):
        """Get company financial summary (Restored)"""
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

    def calculate_ownership_percentage(self, company_id, user_id):
        """Calculate user's ownership percentage (Restored)"""
        company = Company.get_by_id(company_id)
        if not company: return 0
        
        holding = db.get_holding(user_id, company_id)
        if not holding: return 0
        
        # Percentage of Issued Shares (excluding what company still holds)
        issued_shares = company.total_shares - company.available_shares
        if issued_shares == 0: return 0
        
        return (holding['quantity'] / issued_shares) * 100

    # Note: add_company_asset was removed. Use AssetService.buy_asset_for_company instead.
    # Note: update_share_price was removed. Use AdminService or MarketEngine automation.

company_service = CompanyService()