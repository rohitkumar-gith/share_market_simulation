"""
Configuration settings for Share Market Simulation System
"""
import os

# Database Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'market_simulation.db')

# Application Settings
APP_NAME = "Share Market Simulator"
APP_VERSION = "2.0.0" 
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900

# Market Settings
INITIAL_USER_BALANCE = 100000.0
MINIMUM_SHARE_PRICE = 1.0
MAXIMUM_SHARE_PRICE = 100000.0
TRANSACTION_FEE_PERCENT = 0.1 

# Loan Settings
MINIMUM_LOAN_AMOUNT = 1000.0
MAXIMUM_LOAN_AMOUNT = 1000000.0
DEFAULT_INTEREST_RATE = 5.0  
MINIMUM_LOAN_TERM = 6  
MAXIMUM_LOAN_TERM = 60  

# Bot Trading Settings
BOT_TRADING_INTERVAL = 10  
BOT_INITIAL_BALANCE = 50000.0
NUMBER_OF_BOTS = 15  
BOT_MIN_TRADE_AMOUNT = 100
BOT_MAX_TRADE_AMOUNT = 5000

# Price Adjustment Settings
PRICE_VOLATILITY_FACTOR = 0.05
DEMAND_IMPACT_FACTOR = 0.02

# --- MODERN DARK THEME COLORS ---
# Backgrounds
COLOR_BACKGROUND = "#121212"      # Very dark gray (Main BG)
COLOR_SURFACE    = "#1E1E1E"      # Slightly lighter (Cards/Panels)
COLOR_PRIMARY    = "#2C2C2C"      # Sidebar/Top bar

# Accents
COLOR_ACCENT     = "#3498DB"      # Bright Blue (Primary Actions)
COLOR_SECONDARY  = "#BB86FC"      # Purple (Secondary Actions)

# Status Colors
COLOR_SUCCESS    = "#00C853"      # Vibrant Green
COLOR_DANGER     = "#CF6679"      # Soft Red
COLOR_WARNING    = "#FFB74D"      # Orange

# Text
COLOR_TEXT       = "#E0E0E0"      # Off-white
COLOR_TEXT_DIM   = "#A0A0A0"      # Gray text

# Formatting Settings
CURRENCY_SYMBOL = "₹"
DATE_DISPLAY_FORMAT = "%Y-%m-%d %H:%M"