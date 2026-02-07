"""
Wallet Model - Represents wallet and financial transactions
"""
from datetime import datetime
from database.db_manager import db
from utils.constants import *


class Wallet:
    """Wallet model for transaction management"""
    
    @staticmethod
    def get_user_balance(user_id):
        """Get user's current wallet balance"""
        user_data = db.get_user_by_id(user_id)
        return user_data['wallet_balance'] if user_data else 0
    
    @staticmethod
    def get_transaction_history(user_id, limit=50, transaction_type=None):
        """Get wallet transaction history with optional filtering"""
        transactions = db.get_wallet_transactions(user_id, limit)
        
        if transaction_type:
            transactions = [t for t in transactions if t['transaction_type'] == transaction_type]
        
        return transactions
    
    @staticmethod
    def get_transaction_summary(user_id, days=30):
        """Get transaction summary for last N days"""
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT 
                transaction_type,
                COUNT(*) as count,
                SUM(amount) as total_amount
            FROM wallet_transactions
            WHERE user_id = ? AND created_at > ?
            GROUP BY transaction_type
        """
        
        results = db.execute_query(query, (user_id, cutoff_date))
        
        summary = {}
        for row in results:
            summary[row['transaction_type']] = {
                'count': row['count'],
                'total_amount': row['total_amount']
            }
        
        return summary
    
    @staticmethod
    def get_spending_analysis(user_id, days=30):
        """Analyze spending patterns"""
        summary = Wallet.get_transaction_summary(user_id, days)
        
        total_deposits = 0
        total_withdrawals = 0
        total_transfers_out = 0
        total_transfers_in = 0
        total_share_purchases = 0
        total_share_sales = 0
        total_loan_payments = 0
        total_dividends = 0
        
        # Aggregate amounts
        for trans_type, data in summary.items():
            amount = data['total_amount']
            
            if trans_type == WALLET_DEPOSIT:
                total_deposits += amount
            elif trans_type == WALLET_WITHDRAWAL:
                total_withdrawals += amount
            elif trans_type == WALLET_TRANSFER_OUT:
                total_transfers_out += amount
            elif trans_type == WALLET_TRANSFER_IN:
                total_transfers_in += amount
            elif trans_type == WALLET_SHARE_PURCHASE:
                total_share_purchases += amount
            elif trans_type == WALLET_SHARE_SALE:
                total_share_sales += amount
            elif trans_type == WALLET_LOAN_PAYMENT:
                total_loan_payments += amount
            elif trans_type == WALLET_DIVIDEND_RECEIVED:
                total_dividends += amount
        
        # Calculate totals
        total_income = (total_deposits + total_transfers_in + 
                       total_share_sales + total_dividends)
        
        total_expenses = (total_withdrawals + total_transfers_out + 
                         total_share_purchases + total_loan_payments)
        
        net_flow = total_income - total_expenses
        
        return {
            'deposits': total_deposits,
            'withdrawals': total_withdrawals,
            'transfers_out': total_transfers_out,
            'transfers_in': total_transfers_in,
            'share_purchases': total_share_purchases,
            'share_sales': total_share_sales,
            'loan_payments': total_loan_payments,
            'dividends': total_dividends,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_flow': net_flow
        }
    
    @staticmethod
    def get_daily_balance_history(user_id, days=30):
        """Get daily balance history (simplified version)"""
        from datetime import timedelta
        
        current_balance = Wallet.get_user_balance(user_id)
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT 
                DATE(created_at) as date,
                balance_after
            FROM wallet_transactions
            WHERE user_id = ? AND created_at > ?
            ORDER BY created_at ASC
        """
        
        results = db.execute_query(query, (user_id, cutoff_date))
        
        # Group by date and get last balance of each day
        daily_balances = {}
        for row in results:
            date = row['date']
            daily_balances[date] = row['balance_after']
        
        return daily_balances
    
    @staticmethod
    def export_transactions(user_id, start_date=None, end_date=None):
        """Export transactions for a date range"""
        query = "SELECT * FROM wallet_transactions WHERE user_id = ?"
        params = [user_id]
        
        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date)
        
        query += " ORDER BY created_at DESC"
        
        results = db.execute_query(query, params)
        return [dict(row) for row in results]
    
    @staticmethod
    def get_largest_transactions(user_id, limit=10, transaction_type=None):
        """Get largest transactions"""
        query = """
            SELECT * FROM wallet_transactions 
            WHERE user_id = ?
        """
        params = [user_id]
        
        if transaction_type:
            query += " AND transaction_type = ?"
            params.append(transaction_type)
        
        query += " ORDER BY ABS(amount) DESC LIMIT ?"
        params.append(limit)
        
        results = db.execute_query(query, params)
        return [dict(row) for row in results]
    
    @staticmethod
    def get_recent_activity(user_id, limit=10):
        """Get recent wallet activity"""
        return db.get_wallet_transactions(user_id, limit)
    
    @classmethod
    def format_transaction_type(cls, transaction_type):
        """Format transaction type for display"""
        type_map = {
            WALLET_DEPOSIT: "Deposit",
            WALLET_WITHDRAWAL: "Withdrawal",
            WALLET_TRANSFER_IN: "Transfer In",
            WALLET_TRANSFER_OUT: "Transfer Out",
            WALLET_SHARE_PURCHASE: "Share Purchase",
            WALLET_SHARE_SALE: "Share Sale",
            WALLET_LOAN_RECEIVED: "Loan Received",
            WALLET_LOAN_PAYMENT: "Loan Payment",
            WALLET_DIVIDEND_RECEIVED: "Dividend Received"
        }
        return type_map.get(transaction_type, transaction_type.replace('_', ' ').title())
