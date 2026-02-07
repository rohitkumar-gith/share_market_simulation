"""
Loan Model - Represents user loans with payment calculations
"""
from datetime import datetime, timedelta
from database.db_manager import db
from models.user import User
from utils.validators import Validator
from utils.constants import *
import config


class Loan:
    """Loan model with payment calculations"""
    
    def __init__(self, loan_id=None, user_id=None, loan_amount=None,
                 interest_rate=None, remaining_balance=None, monthly_payment=None,
                 loan_term_months=None, status=None, issued_at=None, due_date=None):
        self.loan_id = loan_id
        self.user_id = user_id
        self.loan_amount = loan_amount
        self.interest_rate = interest_rate
        self.remaining_balance = remaining_balance
        self.monthly_payment = monthly_payment
        self.loan_term_months = loan_term_months
        self.status = status
        self.issued_at = issued_at
        self.due_date = due_date
    
    @classmethod
    def from_dict(cls, data):
        """Create Loan instance from dictionary"""
        if not data:
            return None
        return cls(
            loan_id=data.get('loan_id'),
            user_id=data.get('user_id'),
            loan_amount=data.get('loan_amount'),
            interest_rate=data.get('interest_rate'),
            remaining_balance=data.get('remaining_balance'),
            monthly_payment=data.get('monthly_payment'),
            loan_term_months=data.get('loan_term_months'),
            status=data.get('status'),
            issued_at=data.get('issued_at'),
            due_date=data.get('due_date')
        )
    
    def to_dict(self):
        """Convert Loan to dictionary"""
        return {
            'loan_id': self.loan_id,
            'user_id': self.user_id,
            'loan_amount': self.loan_amount,
            'interest_rate': self.interest_rate,
            'remaining_balance': self.remaining_balance,
            'monthly_payment': self.monthly_payment,
            'loan_term_months': self.loan_term_months,
            'status': self.status,
            'issued_at': self.issued_at,
            'due_date': self.due_date
        }
    
    @staticmethod
    def calculate_monthly_payment(principal, annual_rate, months):
        """Calculate monthly loan payment using amortization formula"""
        if months <= 0:
            raise ValueError("Loan term must be positive.")
        
        monthly_rate = annual_rate / 100 / 12
        
        if monthly_rate == 0:
            return principal / months
        
        # Amortization formula: M = P * [r(1+r)^n] / [(1+r)^n - 1]
        payment = principal * (monthly_rate * (1 + monthly_rate) ** months) / \
                 ((1 + monthly_rate) ** months - 1)
        
        return round(payment, 2)
    
    @classmethod
    def apply(cls, user_id, loan_amount, loan_term_months, interest_rate=None):
        """Apply for a loan"""
        # Validation
        if not Validator.validate_range(loan_amount, config.MINIMUM_LOAN_AMOUNT, config.MAXIMUM_LOAN_AMOUNT):
            raise ValueError(f"Loan amount must be between ₹{config.MINIMUM_LOAN_AMOUNT:,.0f} and ₹{config.MAXIMUM_LOAN_AMOUNT:,.0f}")
        
        if not Validator.validate_range(loan_term_months, config.MINIMUM_LOAN_TERM, config.MAXIMUM_LOAN_TERM):
            raise ValueError(f"Loan term must be between {config.MINIMUM_LOAN_TERM} and {config.MAXIMUM_LOAN_TERM} months")
        
        # Use default interest rate if not specified
        if interest_rate is None:
            interest_rate = config.DEFAULT_INTEREST_RATE
        
        # Check user eligibility (basic check: user exists and doesn't have too many active loans)
        user = User.get_by_id(user_id)
        if not user:
            raise ValueError("User not found.")
        
        active_loans = user.get_active_loans()
        if len(active_loans) >= 3:
            raise ValueError("Maximum 3 active loans allowed.")
        
        total_debt = sum(loan['remaining_balance'] for loan in active_loans)
        if total_debt + loan_amount > config.MAXIMUM_LOAN_AMOUNT * 2:
            raise ValueError("Total debt would exceed maximum allowed.")
        
        # Create loan
        loan_id = db.create_loan(user_id, loan_amount, interest_rate, loan_term_months)
        
        # Add loan amount to user wallet
        user.add_funds(loan_amount, f"Loan received (ID: {loan_id})")
        
        # Fetch and return created loan
        loan_data = db.execute_query("SELECT * FROM loans WHERE loan_id = ?", (loan_id,))
        return cls.from_dict(dict(loan_data[0])) if loan_data else None
    
    @classmethod
    def get_by_id(cls, loan_id):
        """Get loan by ID"""
        query = "SELECT * FROM loans WHERE loan_id = ?"
        results = db.execute_query(query, (loan_id,))
        return cls.from_dict(dict(results[0])) if results else None
    
    @classmethod
    def get_user_loans(cls, user_id):
        """Get user's loans"""
        loans_data = db.get_user_loans(user_id)
        return [cls.from_dict(loan) for loan in loans_data]
    
    def make_payment(self, payment_amount):
        """Make a loan payment"""
        if payment_amount <= 0:
            raise ValueError("Payment amount must be positive.")
        
        if self.status != LOAN_STATUS_ACTIVE:
            raise ValueError("Can only make payments on active loans.")
        
        if payment_amount > self.remaining_balance:
            payment_amount = self.remaining_balance
        
        # Get user
        user = User.get_by_id(self.user_id)
        if payment_amount > user.wallet_balance:
            raise ValueError(f"Insufficient funds. Need ₹{payment_amount:,.2f}")
        
        # Calculate interest and principal portions
        monthly_rate = self.interest_rate / 100 / 12
        interest_amount = self.remaining_balance * monthly_rate
        principal_amount = payment_amount - interest_amount
        
        if principal_amount < 0:
            principal_amount = 0
            interest_amount = payment_amount
        
        # Update remaining balance
        new_balance = self.remaining_balance - principal_amount
        
        # Deduct from user wallet
        user.withdraw_funds(payment_amount, f"Loan payment (ID: {self.loan_id})")
        
        # Update loan status
        if new_balance <= 0.01:  # Account for floating point precision
            new_balance = 0
            new_status = LOAN_STATUS_PAID
        else:
            new_status = LOAN_STATUS_ACTIVE
        
        db.update_loan_balance(self.loan_id, new_balance, new_status)
        
        # Record payment
        db.add_loan_payment(
            self.loan_id,
            payment_amount,
            principal_amount,
            interest_amount,
            new_balance
        )
        
        # Update instance
        self.remaining_balance = new_balance
        self.status = new_status
        
        return {
            'payment_amount': payment_amount,
            'principal_amount': principal_amount,
            'interest_amount': interest_amount,
            'remaining_balance': new_balance,
            'status': new_status
        }
    
    def get_payment_history(self):
        """Get loan payment history"""
        query = "SELECT * FROM loan_payments WHERE loan_id = ? ORDER BY payment_date DESC"
        results = db.execute_query(query, (self.loan_id,))
        return [dict(row) for row in results]
    
    def get_amortization_schedule(self):
        """Get loan amortization schedule"""
        schedule = []
        balance = self.loan_amount
        monthly_rate = self.interest_rate / 100 / 12
        
        for month in range(1, self.loan_term_months + 1):
            interest = balance * monthly_rate
            principal = self.monthly_payment - interest
            balance -= principal
            
            if balance < 0:
                balance = 0
            
            schedule.append({
                'month': month,
                'payment': self.monthly_payment,
                'principal': principal,
                'interest': interest,
                'remaining_balance': balance
            })
        
        return schedule
    
    def get_total_interest(self):
        """Calculate total interest to be paid"""
        total_payment = self.monthly_payment * self.loan_term_months
        return total_payment - self.loan_amount
    
    def is_overdue(self):
        """Check if loan is overdue"""
        if self.status != LOAN_STATUS_ACTIVE:
            return False
        
        if isinstance(self.due_date, str):
            due_date = datetime.strptime(self.due_date, '%Y-%m-%d %H:%M:%S')
        else:
            due_date = self.due_date
        
        return datetime.now() > due_date
    
    def __repr__(self):
        return f"<Loan(id={self.loan_id}, amount={self.loan_amount}, balance={self.remaining_balance}, status='{self.status}')>"
