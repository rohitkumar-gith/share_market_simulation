"""
Data formatting utilities
"""
from datetime import datetime
import config


class Formatter:
    """Data formatting class"""
    
    @staticmethod
    def format_currency(amount):
        """Format amount as currency"""
        if amount is None:
            return "₹0.00"
        return f"₹{amount:,.2f}"
    
    @staticmethod
    def format_number(number):
        """Format number with commas"""
        if number is None:
            return "0"
        return f"{number:,}"
    
    @staticmethod
    def format_percentage(value):
        """Format as percentage"""
        if value is None:
            return "0.00%"
        return f"{value:.2f}%"
    
    @staticmethod
    def format_datetime(dt, display_format=True):
        """Format datetime object"""
        if dt is None:
            return "N/A"
        
        if isinstance(dt, str):
            try:
                dt = datetime.strptime(dt, config.DATE_FORMAT)
            except:
                return dt
        
        if display_format:
            return dt.strftime(config.DATE_DISPLAY_FORMAT)
        return dt.strftime(config.DATE_FORMAT)
    
    @staticmethod
    def format_profit_loss(current_value, invested_value):
        """Format profit/loss with color indicator"""
        if invested_value == 0:
            return "N/A", "neutral"
        
        profit_loss = current_value - invested_value
        percentage = (profit_loss / invested_value) * 100
        
        if profit_loss > 0:
            return f"+{Formatter.format_currency(profit_loss)} (+{percentage:.2f}%)", "profit"
        elif profit_loss < 0:
            return f"{Formatter.format_currency(profit_loss)} ({percentage:.2f}%)", "loss"
        else:
            return f"{Formatter.format_currency(0)} (0.00%)", "neutral"
    
    @staticmethod
    def format_change(old_value, new_value):
        """Format value change"""
        if old_value == 0:
            return "N/A"
        
        change = new_value - old_value
        percentage = (change / old_value) * 100
        
        if change > 0:
            return f"+{change:.2f} (+{percentage:.2f}%)"
        elif change < 0:
            return f"{change:.2f} ({percentage:.2f}%)"
        else:
            return "0.00 (0.00%)"
    
    @staticmethod
    def truncate_text(text, max_length=50):
        """Truncate text with ellipsis"""
        if not text or len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    @staticmethod
    def parse_currency(currency_str):
        """Parse currency string to float"""
        if isinstance(currency_str, (int, float)):
            return float(currency_str)
        
        # Remove currency symbol and commas
        cleaned = currency_str.replace('₹', '').replace(',', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
