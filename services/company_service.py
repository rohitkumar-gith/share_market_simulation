"""
Company Service - Manage companies, dividends, wallets, Corporate Lending, and Ownership
"""
from database.db_manager import db
from models.company import Company
from models.user import User
from models.transaction import Transaction

class CompanyService:
    
    def __init__(self):
        """Auto-patch the database for new lending features safely without terminal errors"""
        try:
            columns_info = db.execute_query("PRAGMA table_info(inter_company_loans)")
            if columns_info:
                existing_columns = []
                for col in columns_info:
                    if isinstance(col, dict) and 'name' in col: existing_columns.append(col['name'])
                    elif isinstance(col, tuple) and len(col) > 1: existing_columns.append(col[1])
                
                if 'remaining_balance' not in existing_columns: db.execute_update("ALTER TABLE inter_company_loans ADD COLUMN remaining_balance REAL DEFAULT 0")
                if 'is_request' not in existing_columns: db.execute_update("ALTER TABLE inter_company_loans ADD COLUMN is_request BOOLEAN DEFAULT 0")
        except Exception as e: pass 
            
        try:
            db.execute_update("""
                CREATE TABLE IF NOT EXISTS company_user_loans (
                    loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lender_company_id INTEGER NOT NULL,
                    borrower_user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    interest_rate REAL NOT NULL,
                    total_repayment REAL NOT NULL,
                    remaining_balance REAL NOT NULL,
                    is_request BOOLEAN DEFAULT 0,
                    status TEXT DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lender_company_id) REFERENCES companies(company_id),
                    FOREIGN KEY (borrower_user_id) REFERENCES users(user_id)
                )
            """)
            cul_info = db.execute_query("PRAGMA table_info(company_user_loans)")
            if cul_info:
                cul_cols = [c['name'] if isinstance(c, dict) else c[1] for c in cul_info]
                if 'is_request' not in cul_cols: db.execute_update("ALTER TABLE company_user_loans ADD COLUMN is_request BOOLEAN DEFAULT 0")
        except: pass

    # ==========================
    # OWNERSHIP & HOSTILE TAKEOVERS
    # ==========================

    def check_hostile_takeovers(self):
        """Scans all companies and transfers ownership to the majority shareholder"""
        try:
            companies = Company.get_all()
            for comp in companies:
                # Find the user with the absolute highest number of shares
                top_holder = db.execute_query("""
                    SELECT user_id, quantity 
                    FROM user_holdings 
                    WHERE company_id = ? 
                    ORDER BY quantity DESC LIMIT 1
                """, (comp.company_id,))

                if top_holder and top_holder[0]['quantity'] > 0:
                    new_owner_id = top_holder[0]['user_id']
                    
                    # If the top holder is NOT the current owner, a takeover has occurred!
                    if new_owner_id != comp.owner_id:
                        db.execute_update("UPDATE companies SET owner_id = ? WHERE company_id = ?", (new_owner_id, comp.company_id))
                        
                        # Log the hostile takeover in the corporate ledger
                        db.execute_insert(
                            "INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)",
                            (comp.company_id, 'TAKEOVER', 0, comp.company_wallet, "Hostile Takeover: New Majority Shareholder took control.")
                        )
        except Exception as e:
            print(f"Error checking takeovers: {e}")

    def get_ranked_shareholders(self, company_id):
        """Returns a ranked list of all investors in the company"""
        query = """
            SELECT uh.user_id, uh.quantity, u.username, u.full_name,
                   (SELECT SUM(quantity) FROM user_holdings WHERE company_id = ?) as total_issued_shares
            FROM user_holdings uh
            JOIN users u ON uh.user_id = u.user_id
            WHERE uh.company_id = ? AND uh.quantity > 0
            ORDER BY uh.quantity DESC
        """
        return db.execute_query(query, (company_id, company_id))

    # ==========================
    # CORE MANAGEMENT
    # ==========================
    
    def create_company(self, user_id, name, ticker, price, total_shares, description):
        try:
            company = Company.create(user_id, name, ticker, price, total_shares, description)
            # Give the creator the initial shares so they are actually the owner
            initial_shares = int(total_shares * 0.10) # Give founder 10% to start
            if initial_shares > 0:
                from services.trading_service import trading_service
                db.execute_update("UPDATE companies SET available_shares = available_shares - ? WHERE company_id = ?", (initial_shares, company.company_id))
                db.execute_insert("INSERT INTO user_holdings (user_id, company_id, quantity, average_buy_price) VALUES (?, ?, ?, ?)", (user_id, company.company_id, initial_shares, price))
            return {'success': True, 'message': f"Company {name} ({ticker}) created! You were granted {initial_shares:,} founder shares."}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_user_companies(self, user_id):
        # Always check for hostile takeovers before loading the dashboard!
        self.check_hostile_takeovers()
        return [c.to_dict() for c in Company.get_by_owner(user_id)]

    def get_all_companies(self):
        return [c.to_dict() for c in Company.get_all()]

    def get_company_details(self, company_id):
        try:
            company = Company.get_by_id(company_id)
            if not company: return None
            return {
                'company': company.to_dict(),
                'market_cap': company.get_market_cap(),
                'shareholders': self.get_ranked_shareholders(company_id),
                'total_assets_value': company.get_total_assets_value()
            }
        except: return None

    def edit_company_details(self, user_id, company_id, new_name, new_desc):
        try:
            company = Company.get_by_id(company_id)
            if not company: return {'success': False, 'message': "Company not found."}
            if company.owner_id != user_id: return {'success': False, 'message': "Unauthorized."}
            company.update_details(new_name, new_desc)
            return {'success': True, 'message': "Company details updated successfully."}
        except Exception as e: return {'success': False, 'message': str(e)}

    def issue_more_shares(self, user_id, company_id, additional_shares):
        try:
            if additional_shares <= 0: return {'success': False, 'message': "Must issue at least 1 share."}
            company = Company.get_by_id(company_id)
            if not company or company.owner_id != user_id: return {'success': False, 'message': "Unauthorized."}
            company.issue_new_shares(additional_shares)
            return {'success': True, 'message': f"Issued {additional_shares:,} new shares."}
        except Exception as e: return {'success': False, 'message': str(e)}

    # ==========================
    # WALLET & FINANCE
    # ==========================

    def deposit_to_wallet(self, company_id, user_id, amount):
        try:
            company = Company.get_by_id(company_id)
            if company.owner_id != user_id: return {'success': False, 'message': "Unauthorized."}
            user = User.get_by_id(user_id)
            if user.wallet_balance < amount: return {'success': False, 'message': "Insufficient personal funds."}
            
            user.withdraw_funds(amount, f"Invested in {company.company_name}")
            company.update_wallet(amount)
            db.execute_insert("INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)", (company_id, 'DEPOSIT', amount, company.company_wallet, "Owner Investment"))
            
            if company.is_bankrupt and company.company_wallet >= 10000:
                db.execute_update("UPDATE companies SET is_bankrupt = 0 WHERE company_id = ?", (company_id,))
            return {'success': True, 'message': "Funds deposited successfully"}
        except Exception as e: return {'success': False, 'message': str(e)}

    def withdraw_from_wallet(self, company_id, user_id, amount):
        try:
            company = Company.get_by_id(company_id)
            if company.owner_id != user_id: return {'success': False, 'message': "Unauthorized."}
            if company.company_wallet < amount: return {'success': False, 'message': "Insufficient company funds."}
            
            company.update_wallet(-amount)
            user = User.get_by_id(user_id)
            user.add_funds(amount, f"Withdrawal from {company.company_name}")
            db.execute_insert("INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)", (company_id, 'WITHDRAW', amount, company.company_wallet, "Owner Withdrawal"))
            
            if company.company_wallet < 10000 and not company.is_bankrupt:
                db.execute_update("UPDATE companies SET is_bankrupt = 1 WHERE company_id = ?", (company_id,))
            return {'success': True, 'message': "Funds withdrawn successfully"}
        except Exception as e: return {'success': False, 'message': str(e)}

    def issue_dividend(self, company_id, user_id, amount_per_share):
        try:
            company = Company.get_by_id(company_id)
            if company.owner_id != user_id: return {'success': False, 'message': "Unauthorized."}
            
            shareholders = company.get_shareholders()
            if not shareholders: return {'success': False, 'message': "No shareholders to pay."}
            
            total_payout = amount_per_share * sum(h['quantity'] for h in shareholders)
            if total_payout <= 0: return {'success': False, 'message': "Total payout is zero."}
            if company.company_wallet < total_payout: return {'success': False, 'message': f"Insufficient funds. Need ₹{total_payout:,.2f}"}
            
            company.update_wallet(-total_payout)
            db.execute_insert("INSERT INTO dividends (company_id, dividend_per_share, total_amount, payment_date, status) VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'PAID')", (company_id, amount_per_share, total_payout))
            db.execute_insert("INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)", (company_id, 'DIVIDEND', total_payout, company.company_wallet, f"Dividend Payout: ₹{amount_per_share}/share"))
            
            count = 0
            for holder in shareholders:
                user = User.get_by_id(holder['user_id'])
                if user:
                    user.add_funds(holder['quantity'] * amount_per_share, f"Dividend from {company.company_name}")
                    count += 1
            return {'success': True, 'message': f"Distributed ₹{total_payout:,.2f} to {count} shareholders."}
        except Exception as e: return {'success': False, 'message': str(e)}

    # ==========================
    # CORPORATE LENDING (OFFERS & REQUESTS)
    # ==========================
    
    def offer_loan(self, lender_company_id, user_id, target_type, target_identifier, amount, interest_rate):
        try:
            lender = Company.get_by_id(lender_company_id)
            if not lender or lender.owner_id != user_id: return {'success': False, 'message': "Unauthorized."}
            if lender.company_wallet < amount: return {'success': False, 'message': f"Insufficient funds to offer ₹{amount:,.2f}."}
                
            total_repayment = amount + (amount * (interest_rate / 100))
            
            if target_type == "COMPANY":
                res = db.execute_query("SELECT company_id FROM companies WHERE ticker_symbol = ?", (target_identifier.upper(),))
                if not res: return {'success': False, 'message': "Target Company not found."}
                if res[0]['company_id'] == lender_company_id: return {'success': False, 'message': "Cannot lend to yourself."}
                db.execute_insert("INSERT INTO inter_company_loans (lender_company_id, borrower_company_id, amount, interest_rate, total_repayment, remaining_balance, status, is_request) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', 0)", (lender_company_id, res[0]['company_id'], amount, interest_rate, total_repayment, total_repayment))
            elif target_type == "PLAYER":
                res = User.get_by_username(target_identifier)
                if not res: return {'success': False, 'message': "Target Player not found."}
                db.execute_insert("INSERT INTO company_user_loans (lender_company_id, borrower_user_id, amount, interest_rate, total_repayment, remaining_balance, status, is_request) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', 0)", (lender_company_id, res.user_id, amount, interest_rate, total_repayment, total_repayment))
            return {'success': True, 'message': f"Loan offer of ₹{amount:,.2f} sent!"}
        except Exception as e: return {'success': False, 'message': str(e)}

    def request_loan(self, borrower_id, borrower_type, target_company_ticker, amount, interest_rate, user_id):
        try:
            res = db.execute_query("SELECT company_id FROM companies WHERE ticker_symbol = ?", (target_company_ticker.upper(),))
            if not res: return {'success': False, 'message': "Target Lender Company not found."}
            lender_id = res[0]['company_id']
            total_repayment = amount + (amount * (interest_rate / 100))
            
            if borrower_type == "COMPANY":
                borrower = Company.get_by_id(borrower_id)
                if not borrower or borrower.owner_id != user_id: return {'success': False, 'message': "Unauthorized."}
                if borrower_id == lender_id: return {'success': False, 'message': "Cannot request from yourself."}
                db.execute_insert("INSERT INTO inter_company_loans (lender_company_id, borrower_company_id, amount, interest_rate, total_repayment, remaining_balance, status, is_request) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', 1)", (lender_id, borrower_id, amount, interest_rate, total_repayment, total_repayment))
            elif borrower_type == "PLAYER":
                if borrower_id != user_id: return {'success': False, 'message': "Unauthorized."}
                db.execute_insert("INSERT INTO company_user_loans (lender_company_id, borrower_user_id, amount, interest_rate, total_repayment, remaining_balance, status, is_request) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', 1)", (lender_id, borrower_id, amount, interest_rate, total_repayment, total_repayment))
            return {'success': True, 'message': f"Loan request for ₹{amount:,.2f} sent to {target_company_ticker}!"}
        except Exception as e: return {'success': False, 'message': str(e)}

    def respond_to_loan(self, loan_id, loan_type, action, user_id):
        try:
            table = "inter_company_loans" if loan_type == "B2B" else "company_user_loans"
            loans = db.execute_query(f"SELECT * FROM {table} WHERE loan_id = ? AND status = 'PENDING'", (loan_id,))
            if not loans: return {'success': False, 'message': "Loan not found or already processed."}
            loan = loans[0]
            lender = Company.get_by_id(loan['lender_company_id'])
            
            if action in ["REJECT", "CANCEL"]:
                is_authorized = False
                if lender.owner_id == user_id: is_authorized = True
                if loan_type == "B2B":
                    borrower_comp = Company.get_by_id(loan['borrower_company_id'])
                    if borrower_comp and borrower_comp.owner_id == user_id: is_authorized = True
                else:
                    if loan['borrower_user_id'] == user_id: is_authorized = True
                
                if not is_authorized: return {'success': False, 'message': "Unauthorized."}
                status = "REJECTED" if action == "REJECT" else "CANCELLED"
                db.execute_update(f"UPDATE {table} SET status = ? WHERE loan_id = ?", (status, loan_id))
                return {'success': True, 'message': f"Loan has been {status.lower()}."}
            
            if action == "ACCEPT":
                if loan['is_request']:
                    if lender.owner_id != user_id: return {'success': False, 'message': "Only the lending company can approve this."}
                else:
                    if loan_type == "B2B":
                        borrower_comp = Company.get_by_id(loan['borrower_company_id'])
                        if not borrower_comp or borrower_comp.owner_id != user_id: return {'success': False, 'message': "Only the borrowing company can accept."}
                    else:
                        if loan['borrower_user_id'] != user_id: return {'success': False, 'message': "Only the borrowing player can accept."}

                if lender.company_wallet < loan['amount']: return {'success': False, 'message': "Lending company does not have enough funds!"}
                
                lender.update_wallet(-loan['amount'])
                db.execute_insert("INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)", (lender.company_id, 'LOAN_ISSUED', loan['amount'], lender.company_wallet, "Issued Corporate Loan"))
                
                if loan_type == "B2B":
                    borrower_comp = Company.get_by_id(loan['borrower_company_id'])
                    borrower_comp.update_wallet(loan['amount'])
                    db.execute_insert("INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)", (borrower_comp.company_id, 'LOAN_RECEIVED', loan['amount'], borrower_comp.company_wallet, "Received Corporate Loan"))
                else:
                    borrower_user = User.get_by_id(loan['borrower_user_id'])
                    borrower_user.add_funds(loan['amount'], f"Received Corporate Loan from {lender.ticker_symbol}")
                    
                db.execute_update(f"UPDATE {table} SET status = 'ACTIVE' WHERE loan_id = ?", (loan_id,))
                return {'success': True, 'message': "Loan accepted! Funds have been transferred."}
        except Exception as e: return {'success': False, 'message': str(e)}

    def pay_corporate_loan(self, loan_id, loan_type, user_id, payment_amount):
        try:
            table = "inter_company_loans" if loan_type == "B2B" else "company_user_loans"
            loans = db.execute_query(f"SELECT * FROM {table} WHERE loan_id = ? AND status = 'ACTIVE'", (loan_id,))
            if not loans: return {'success': False, 'message': "Active loan not found."}
            loan = loans[0]
            
            lender = Company.get_by_id(loan['lender_company_id'])
            payment_amount = min(payment_amount, loan['remaining_balance'])
            
            if loan_type == "B2B":
                borrower = Company.get_by_id(loan['borrower_company_id'])
                if borrower.owner_id != user_id: return {'success': False, 'message': "Unauthorized."}
                if borrower.company_wallet < payment_amount: return {'success': False, 'message': "Insufficient company funds."}
                borrower.update_wallet(-payment_amount)
                db.execute_insert("INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)", (borrower.company_id, 'LOAN_PAYMENT', payment_amount, borrower.company_wallet, "Corporate Loan Repayment"))
            else:
                if loan['borrower_user_id'] != user_id: return {'success': False, 'message': "Unauthorized."}
                borrower = User.get_by_id(user_id)
                if borrower.wallet_balance < payment_amount: return {'success': False, 'message': "Insufficient personal funds."}
                borrower.withdraw_funds(payment_amount, "Corporate Loan Repayment")

            lender.update_wallet(payment_amount)
            db.execute_insert("INSERT INTO company_wallet_transactions (company_id, transaction_type, amount, balance_after, description) VALUES (?, ?, ?, ?, ?)", (lender.company_id, 'REVENUE', payment_amount, lender.company_wallet, "Corporate Loan Payment Received"))

            new_bal = loan['remaining_balance'] - payment_amount
            new_status = "PAID" if new_bal <= 0 else "ACTIVE"
            db.execute_update(f"UPDATE {table} SET remaining_balance = ?, status = ? WHERE loan_id = ?", (new_bal, new_status, loan_id))
            return {'success': True, 'message': f"Paid ₹{payment_amount:,.2f} towards loan."}
        except Exception as e: return {'success': False, 'message': str(e)}

    # ==========================
    # DATA RETRIEVAL (UI HELPERS)
    # ==========================
    
    def get_company_lending_dashboard(self, company_id):
        b2b_all = db.execute_query("SELECT l.*, c.ticker_symbol as other_name, 'B2B' as type FROM inter_company_loans l JOIN companies c ON (l.borrower_company_id = c.company_id OR l.lender_company_id = c.company_id) WHERE (l.lender_company_id = ? OR l.borrower_company_id = ?) AND c.company_id != ?", (company_id, company_id, company_id)) or []
        b2c_all = db.execute_query("SELECT l.*, u.username as other_name, 'B2C' as type FROM company_user_loans l JOIN users u ON l.borrower_user_id = u.user_id WHERE l.lender_company_id = ?", (company_id,)) or []
        all_loans = b2b_all + b2c_all
        
        action_required = []; pending_outgoing = []; portfolio = []; debts = []
        for l in all_loans:
            is_lender = (l['lender_company_id'] == company_id)
            if l['status'] == 'PENDING':
                if is_lender and l['is_request']: action_required.append(l) 
                elif not is_lender and not l['is_request']: action_required.append(l)
                elif is_lender and not l['is_request']: pending_outgoing.append(l)
                elif not is_lender and l['is_request']: pending_outgoing.append(l)
            elif l['status'] == 'ACTIVE':
                if is_lender: portfolio.append(l)
                else: debts.append(l)
        return {'action_required': action_required, 'pending_outgoing': pending_outgoing, 'portfolio': portfolio, 'debts': debts}

    def get_player_corporate_loans(self, user_id):
        loans = db.execute_query("SELECT l.*, c.ticker_symbol as other_name, 'B2C' as type FROM company_user_loans l JOIN companies c ON l.lender_company_id = c.company_id WHERE l.borrower_user_id = ? AND l.status IN ('PENDING', 'ACTIVE')", (user_id,)) or []
        return {
            'incoming_offers': [l for l in loans if l['status'] == 'PENDING' and not l['is_request']],
            'outgoing_requests': [l for l in loans if l['status'] == 'PENDING' and l['is_request']],
            'active_debts': [l for l in loans if l['status'] == 'ACTIVE']
        }

    def get_company_financial_summary(self, company_id):
        try:
            company = Company.get_by_id(company_id)
            if not company: return None
            transactions = db.execute_query("SELECT * FROM company_wallet_transactions WHERE company_id = ? ORDER BY created_at DESC LIMIT 50", (company_id,))
            return {
                'wallet_balance': company.company_wallet, 'net_worth': company.net_worth,
                'market_cap': company.get_market_cap(), 'total_shares': company.total_shares,
                'available_shares': company.available_shares, 'share_price': company.share_price,
                'total_assets': company.get_total_assets_value(), 'recent_transactions': [dict(t) for t in transactions]
            }
        except: return None

company_service = CompanyService()