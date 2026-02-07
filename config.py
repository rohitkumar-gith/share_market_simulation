"""
Configuration settings for Share Market Simulation System
"""
import os

# Database Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'market_simulation.db')

# Application Settings
APP_NAME = "Share Market Simulator"
APP_VERSION = "1.0.0"
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900

# Market Settings
INITIAL_USER_BALANCE = 100000.0
MINIMUM_SHARE_PRICE = 1.0
MAXIMUM_SHARE_PRICE = 100000.0
TRANSACTION_FEE_PERCENT = 0.1  # 0.1% transaction fee

# Loan Settings
MINIMUM_LOAN_AMOUNT = 1000.0
MAXIMUM_LOAN_AMOUNT = 1000000.0
DEFAULT_INTEREST_RATE = 5.0  # 5% annual interest
MINIMUM_LOAN_TERM = 6  # months
MAXIMUM_LOAN_TERM = 60  # months

# Bot Trading Settings
BOT_TRADING_INTERVAL = 10  # seconds
BOT_INITIAL_BALANCE = 50000.0
NUMBER_OF_BOTS = 5
BOT_MIN_TRADE_AMOUNT = 100
BOT_MAX_TRADE_AMOUNT = 5000

# Price Adjustment Settings
PRICE_VOLATILITY_FACTOR = 0.05  # 5% maximum price change per update
DEMAND_IMPACT_FACTOR = 0.02  # Impact of buy/sell ratio on price

# UI Colors
COLOR_PRIMARY = "#2C3E50"
COLOR_SECONDARY = "#3498DB"
COLOR_SUCCESS = "#27AE60"
COLOR_DANGER = "#E74C3C"
COLOR_WARNING = "#F39C12"
COLOR_BACKGROUND = "#ECF0F1"
COLOR_TEXT = "#2C3E50"

# Date Format
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_DISPLAY_FORMAT = "%d %b %Y, %I:%M %p"
