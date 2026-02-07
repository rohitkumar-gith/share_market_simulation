"""
Wallet Service - Handles wallet and financial operations
"""
from models.user import User
from models.wallet import Wallet
from datetime import datetime, timedelta


class WalletService:
    """Service for wallet and financial operations"""
    
    @staticmethod
    def add_funds(user_id, amount, description="Deposit"):
        """
        Add funds to user wallet
        
        Args:
            user_id: User ID
            amount: Amount to add
            description: Description
            
        Returns:
            Dictionary with success status
        """
        try:
            user = User.get_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            
            new_balance = user.add_funds(amount, description)
            
            return {
                'success': True,
                'message': f'₹{amount:,.2f} added to wallet',
                'new_balance': new_balance
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def withdraw_funds(user_id, amount, description="Withdrawal"):
        """
        Withdraw funds from user wallet
        
        Args:
            user_id: User ID
            amount: Amount to withdraw
            description: Description
            
        Returns:
            Dictionary with success status
        """
        try:
            user = User.get_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            
            new_balance = user.withdraw_funds(amount, description)
            
            return {
                'success': True,
                'message': f'₹{amount:,.2f} withdrawn from wallet',
                'new_balance': new_balance
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def transfer_funds(sender_id, recipient_username, amount, description=None):
        """
        Transfer funds to another user
        
        Args:
            sender_id: Sender user ID
            recipient_username: Recipient username
            amount: Amount to transfer
            description: Description (optional)
            
        Returns:
            Dictionary with success status
        """
        try:
            sender = User.get_by_id(sender_id)
            if not sender:
                raise ValueError("Sender not found")
            
            recipient = User.get_by_username(recipient_username)
            if not recipient:
                raise ValueError(f"User '{recipient_username}' not found")
            
            new_balance = sender.transfer_to_user(recipient.user_id, amount, description)
            
            return {
                'success': True,
                'message': f'₹{amount:,.2f} transferred to {recipient_username}',
                'new_balance': new_balance
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def get_balance(user_id):
        """Get user wallet balance"""
        balance = Wallet.get_user_balance(user_id)
        return balance
    
    @staticmethod
    def get_transaction_history(user_id, limit=50):
        """Get wallet transaction history"""
        transactions = Wallet.get_transaction_history(user_id, limit)
        return transactions
    
    @staticmethod
    def get_spending_analysis(user_id, days=30):
        """Get spending analysis for user"""
        analysis = Wallet.get_spending_analysis(user_id, days)
        return analysis
    
    @staticmethod
    def get_financial_summary(user_id):
        """Get comprehensive financial summary"""
        user = User.get_by_id(user_id)
        if not user:
            return None
        
        # Get portfolio
        portfolio = user.get_portfolio()
        
        # Get spending analysis
        spending = Wallet.get_spending_analysis(user_id, days=30)
        
        # Get net worth
        net_worth_data = user.get_net_worth()
        
        # Get active loans
        active_loans = user.get_active_loans()
        total_debt = sum(loan['remaining_balance'] for loan in active_loans)
        
        return {
            'wallet_balance': user.wallet_balance,
            'portfolio_value': portfolio['total_current_value'],
            'portfolio_invested': portfolio['total_invested'],
            'portfolio_profit_loss': portfolio['total_profit_loss'],
            'total_debt': total_debt,
            'net_worth': net_worth_data['net_worth'],
            'spending_30days': spending,
            'active_loans_count': len(active_loans)
        }
    
    @staticmethod
    def get_recent_activity(user_id, limit=10):
        """Get recent wallet activity"""
        transactions = Wallet.get_recent_activity(user_id, limit)
        return transactions
    
    @staticmethod
    def export_transactions(user_id, start_date=None, end_date=None):
        """Export transactions for date range"""
        transactions = Wallet.export_transactions(user_id, start_date, end_date)
        return transactions
    
    @staticmethod
    def get_monthly_summary(user_id, year, month):
        """Get monthly financial summary"""
        from calendar import monthrange
        
        # Create date range for the month
        start_date = datetime(year, month, 1)
        last_day = monthrange(year, month)[1]
        end_date = datetime(year, month, last_day, 23, 59, 59)
        
        # Get transactions for the month
        transactions = Wallet.export_transactions(user_id, start_date, end_date)
        
        # Calculate summary
        deposits = sum(t['amount'] for t in transactions if t['transaction_type'] == 'deposit')
        withdrawals = sum(t['amount'] for t in transactions if t['transaction_type'] == 'withdrawal')
        transfers_in = sum(t['amount'] for t in transactions if t['transaction_type'] == 'transfer_in')
        transfers_out = sum(t['amount'] for t in transactions if t['transaction_type'] == 'transfer_out')
        
        return {
            'year': year,
            'month': month,
            'total_transactions': len(transactions),
            'deposits': deposits,
            'withdrawals': withdrawals,
            'transfers_in': transfers_in,
            'transfers_out': transfers_out,
            'net_flow': deposits + transfers_in - withdrawals - transfers_out,
            'transactions': transactions
        }
    
    @staticmethod
    def check_sufficient_funds(user_id, amount):
        """Check if user has sufficient funds"""
        balance = Wallet.get_user_balance(user_id)
        return balance >= amount
    
    @staticmethod
    def get_largest_transactions(user_id, limit=10):
        """Get user's largest transactions"""
        transactions = Wallet.get_largest_transactions(user_id, limit)
        return transactions


# Global wallet service instance
wallet_service = WalletService()
