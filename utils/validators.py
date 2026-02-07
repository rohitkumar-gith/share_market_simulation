"""
Input validation utilities
"""
import re


class Validator:
    """Input validation class"""
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_username(username):
        """Validate username (alphanumeric, 3-20 characters)"""
        if not username or len(username) < 3 or len(username) > 20:
            return False
        return username.isalnum()
    
    @staticmethod
    def validate_password(password):
        """Validate password (minimum 6 characters)"""
        return password and len(password) >= 6
    
    @staticmethod
    def validate_ticker(ticker):
        """Validate ticker symbol (2-6 uppercase letters)"""
        if not ticker or len(ticker) < 2 or len(ticker) > 6:
            return False
        return ticker.isupper() and ticker.isalpha()
    
    @staticmethod
    def validate_positive_number(value, allow_zero=False):
        """Validate positive number"""
        try:
            num = float(value)
            if allow_zero:
                return num >= 0
            return num > 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_positive_integer(value, allow_zero=False):
        """Validate positive integer"""
        try:
            num = int(value)
            if allow_zero:
                return num >= 0
            return num > 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_range(value, min_val, max_val):
        """Validate number is within range"""
        try:
            num = float(value)
            return min_val <= num <= max_val
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def sanitize_string(text, max_length=None):
        """Sanitize string input"""
        if not text:
            return ""
        text = text.strip()
        if max_length:
            text = text[:max_length]
        return text
