"""
Loan Service - Handles loan management operations
"""
from models.loan import Loan
from models.user import User
from datetime import datetime


class LoanService:
    """Service for loan management operations"""
    
    @staticmethod
    def apply_for_loan(user_id, loan_amount, loan_term_months, interest_rate=None):
        """
        Apply for a loan
        
        Args:
            user_id: User ID
            loan_amount: Loan amount
            loan_term_months: Loan term in months
            interest_rate: Interest rate (optional)
            
        Returns:
            Dictionary with success status and loan details
        """
        try:
            loan = Loan.apply(user_id, loan_amount, loan_term_months, interest_rate)
            
            if not loan:
                raise Exception("Loan application failed")
            
            return {
                'success': True,
                'message': f'Loan of ₹{loan_amount:,.2f} approved',
                'loan': loan.to_dict()
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def make_payment(loan_id, user_id, payment_amount):
        """
        Make a loan payment
        
        Args:
            loan_id: Loan ID
            user_id: User ID (for verification)
            payment_amount: Payment amount
            
        Returns:
            Dictionary with success status and payment details
        """
        try:
            loan = Loan.get_by_id(loan_id)
            if not loan:
                raise ValueError("Loan not found")
            
            if loan.user_id != user_id:
                raise ValueError("You can only make payments on your own loans")
            
            result = loan.make_payment(payment_amount)
            
            message = f'Payment of ₹{payment_amount:,.2f} processed'
            if result['status'] == 'paid':
                message += ' - Loan fully paid!'
            
            return {
                'success': True,
                'message': message,
                'payment': result
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def get_user_loans(user_id):
        """Get all user loans"""
        loans = Loan.get_user_loans(user_id)
        return [loan.to_dict() for loan in loans]
    
    @staticmethod
    def get_active_loans(user_id):
        """Get user's active loans"""
        user = User.get_by_id(user_id)
        if not user:
            return []
        
        active_loans = user.get_active_loans()
        return active_loans
    
    @staticmethod
    def get_loan_details(loan_id, user_id):
        """
        Get detailed loan information
        
        Args:
            loan_id: Loan ID
            user_id: User ID (for verification)
            
        Returns:
            Dictionary with loan details
        """
        try:
            loan = Loan.get_by_id(loan_id)
            if not loan:
                return None
            
            if loan.user_id != user_id:
                raise ValueError("Access denied")
            
            payment_history = loan.get_payment_history()
            amortization_schedule = loan.get_amortization_schedule()
            
            return {
                'loan': loan.to_dict(),
                'payment_history': payment_history,
                'amortization_schedule': amortization_schedule,
                'total_interest': loan.get_total_interest(),
                'is_overdue': loan.is_overdue()
            }
        except Exception as e:
            return None
    
    @staticmethod
    def calculate_loan_preview(loan_amount, loan_term_months, interest_rate=None):
        """
        Calculate loan preview without applying
        
        Args:
            loan_amount: Loan amount
            loan_term_months: Loan term in months
            interest_rate: Interest rate (optional)
            
        Returns:
            Dictionary with loan calculations
        """
        try:
            from utils.validators import Validator
            import config
            
            if not Validator.validate_positive_number(loan_amount):
                raise ValueError("Loan amount must be positive")
            
            if not Validator.validate_positive_integer(loan_term_months):
                raise ValueError("Loan term must be a positive integer")
            
            if interest_rate is None:
                interest_rate = config.DEFAULT_INTEREST_RATE
            
            # Calculate monthly payment
            monthly_payment = Loan.calculate_monthly_payment(
                loan_amount, interest_rate, loan_term_months
            )
            
            # Calculate total payment and interest
            total_payment = monthly_payment * loan_term_months
            total_interest = total_payment - loan_amount
            
            return {
                'success': True,
                'loan_amount': loan_amount,
                'interest_rate': interest_rate,
                'loan_term_months': loan_term_months,
                'monthly_payment': monthly_payment,
                'total_payment': total_payment,
                'total_interest': total_interest
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def get_loan_summary(user_id):
        """Get loan summary for user"""
        user = User.get_by_id(user_id)
        if not user:
            return None
        
        all_loans = Loan.get_user_loans(user_id)
        active_loans = [l for l in all_loans if l.status == 'active']
        paid_loans = [l for l in all_loans if l.status == 'paid']
        
        total_borrowed = sum(l.loan_amount for l in all_loans)
        total_debt = sum(l.remaining_balance for l in active_loans)
        total_paid = sum(l.loan_amount for l in paid_loans)
        
        # Calculate total monthly payment due
        monthly_payment_due = sum(l.monthly_payment for l in active_loans)
        
        return {
            'total_loans': len(all_loans),
            'active_loans': len(active_loans),
            'paid_loans': len(paid_loans),
            'total_borrowed': total_borrowed,
            'total_debt': total_debt,
            'total_paid': total_paid,
            'monthly_payment_due': monthly_payment_due
        }
    
    @staticmethod
    def get_payment_history(loan_id, user_id):
        """Get payment history for a loan"""
        loan = Loan.get_by_id(loan_id)
        if not loan:
            return []
        
        if loan.user_id != user_id:
            return []
        
        return loan.get_payment_history()
    
    @staticmethod
    def get_overdue_loans(user_id):
        """Get user's overdue loans"""
        active_loans = LoanService.get_active_loans(user_id)
        
        overdue = []
        for loan_data in active_loans:
            loan = Loan.from_dict(loan_data)
            if loan.is_overdue():
                overdue.append(loan.to_dict())
        
        return overdue
    
    @staticmethod
    def check_loan_eligibility(user_id, requested_amount):
        """
        Check if user is eligible for a loan
        
        Args:
            user_id: User ID
            requested_amount: Requested loan amount
            
        Returns:
            Dictionary with eligibility status
        """
        try:
            import config
            
            user = User.get_by_id(user_id)
            if not user:
                return {
                    'eligible': False,
                    'reason': 'User not found'
                }
            
            # Check active loans count
            active_loans = user.get_active_loans()
            if len(active_loans) >= 3:
                return {
                    'eligible': False,
                    'reason': 'Maximum 3 active loans allowed'
                }
            
            # Check total debt
            total_debt = sum(loan['remaining_balance'] for loan in active_loans)
            if total_debt + requested_amount > config.MAXIMUM_LOAN_AMOUNT * 2:
                return {
                    'eligible': False,
                    'reason': 'Total debt would exceed maximum allowed'
                }
            
            # Check amount range
            if requested_amount < config.MINIMUM_LOAN_AMOUNT:
                return {
                    'eligible': False,
                    'reason': f'Minimum loan amount is ₹{config.MINIMUM_LOAN_AMOUNT:,.0f}'
                }
            
            if requested_amount > config.MAXIMUM_LOAN_AMOUNT:
                return {
                    'eligible': False,
                    'reason': f'Maximum loan amount is ₹{config.MAXIMUM_LOAN_AMOUNT:,.0f}'
                }
            
            return {
                'eligible': True,
                'reason': 'Eligible for loan',
                'max_additional_loan': config.MAXIMUM_LOAN_AMOUNT * 2 - total_debt
            }
        except Exception as e:
            return {
                'eligible': False,
                'reason': str(e)
            }


# Global loan service instance
loan_service = LoanService()
