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
        return [c.to_dict() for c in companies]

    def get_all_companies(self):
        """Get all companies"""
        companies = Company.get_all()
        return [c.to_dict() for c in companies]

    def get_company_details(self, company_id):
        """Get detailed company information"""
        try:
            company = Company.get_by_id(company_id)
            if not company: return None
            
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

    # --- NEW FEATURE: EDIT COMPANY ---
    def edit_company_details(self, user_id, company_id, new_name, new_desc):
        """Allow owner to rename company or update description"""
        try:
            company = Company.get_by_id(company_id)
            if not company: return {'success': False, 'message': "Company not found."}
            if company.owner_id != user_id:
                return {'success': False, 'message': "Only the owner can edit the company."}
                
            company.update_details(new_name, new_desc)
            return {'success': True, 'message': "Company details updated successfully."}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # --- NEW FEATURE: ISSUE SHARES ---
    def issue_more_shares(self, user_id, company_id, additional_shares):
        """Allow owner to create more shares (Dilution)"""
        try:
            if additional_shares <= 0:
                return {'success': False, 'message': "Must issue at least 1 share."}
                
            company = Company.get_by_id(company_id)
            if not company: return {'success': False, 'message': "Company not found."}
            if company.owner_id != user_id:
                return {'success': False, 'message': "Only the owner can issue shares."}
                
            # Perform the issuance
            new_available = company.issue_new_shares(additional_shares)
            
            return {
                'success': True, 
                'message': f"Successfully issued {additional_shares:,} new shares. They are now available in the IPO pool."
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ==========================
    # WALLET & FINANCE
    # ==========================

    def deposit_to_wallet(self, company_id, user_id, amount):
        """Owner deposits personal money into company wallet"""
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
            
            # Bankruptcy Check (Remove if healthy)
            if company.is_bankrupt and company.company_wallet >= 10000:
                db.execute_update("UPDATE companies SET is_bankrupt = 0 WHERE company_id = ?", (company_id,))
            
            return {'success': True, 'message': "Funds deposited successfully"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def withdraw_from_wallet(self, company_id, user_id, amount):
        """Owner withdraws money from company wallet"""
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
            
            # Bankruptcy Check (Add if poor)
            if company.company_wallet < 10000 and not company.is_bankrupt:
                db.execute_update("UPDATE companies SET is_bankrupt = 1 WHERE company_id = ?", (company_id,))
                
            return {'success': True, 'message': "Funds withdrawn successfully"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def issue_dividend(self, company_id, user_id, amount_per_share):
        """Issue dividend to shareholders"""
        try:
            company = Company.get_by_id(company_id)
            if not company: return {'success': False, 'message': "Company not found"}
            
            if company.owner_id != user_id:
                return {'success': False, 'message': "Only owner can issue dividends"}
            
            # 1. Calculate Payout (Only on OUTSTANDING shares, not total)
            shareholders = company.get_shareholders()
            if not shareholders:
                return {'success': False, 'message': "No shareholders to pay."}

            outstanding_shares = sum(h['quantity'] for h in shareholders)
            total_payout = amount_per_share * outstanding_shares
            
            if total_payout <= 0:
                return {'success': False, 'message': "Total payout is zero."}

            if company.company_wallet < total_payout:
                return {'success': False, 'message': f"Insufficient funds. Need ₹{total_payout:,.2f}"}
            
            # 2. Deduct from Company Wallet
            company.update_wallet(-total_payout)
            
            # 3. Record in DIVIDENDS table (History)
            db.execute_insert(
                """INSERT INTO dividends (company_id, dividend_per_share, total_amount, payment_date, status)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'PAID')""",
                (company_id, amount_per_share, total_payout)
            )

            # 4. Record Wallet Transaction
            db.execute_insert(
                "INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                (company_id, 'DIVIDEND', total_payout, company.company_wallet, f"Dividend Payout: ₹{amount_per_share}/share")
            )
            
            # 5. Distribute to Shareholders
            count = 0
            for holder in shareholders:
                payout = holder['quantity'] * amount_per_share
                user = User.get_by_id(holder['user_id'])
                if user:
                    user.add_funds(payout, f"Dividend from {company.company_name} ({holder['quantity']} shares)")
                    count += 1
                
            return {'success': True, 'message': f"Distributed ₹{total_payout:,.2f} to {count} shareholders."}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ==========================
    # DATA & ANALYTICS
    # ==========================

    def get_company_financial_summary(self, company_id):
        """Get company financial summary"""
        try:
            company = Company.get_by_id(company_id)
            if not company: return None
            
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
        """Calculate user's ownership percentage"""
        company = Company.get_by_id(company_id)
        if not company: return 0
        
        holding = db.get_holding(user_id, company_id)
        if not holding: return 0
        
        issued_shares = company.total_shares - company.available_shares
        if issued_shares == 0: return 0
        
        return (holding['quantity'] / issued_shares) * 100

company_service = CompanyService()