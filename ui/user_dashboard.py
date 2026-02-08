"""
User Dashboard - Overview of user's status
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from services.auth_service import auth_service
from services.trading_service import trading_service
from utils.formatters import Formatter
import config

class UserDashboard(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        self.welcome_label = QLabel("Welcome back!")
        self.welcome_label.setFont(QFont('Arial', 24, QFont.Bold))
        layout.addWidget(self.welcome_label)
        
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        
        self.net_worth_card = self.create_summary_card("Net Worth", "₹0.00", "#2980B9")
        self.wallet_card = self.create_summary_card("Wallet Balance", "₹0.00", "#27AE60")
        self.portfolio_card = self.create_summary_card("Portfolio Value", "₹0.00", "#8E44AD")
        
        cards_layout.addWidget(self.net_worth_card)
        cards_layout.addWidget(self.wallet_card)
        cards_layout.addWidget(self.portfolio_card)
        
        layout.addLayout(cards_layout)
        
        layout.addSpacing(10)
        trending_label = QLabel("🔥 Trending Stocks (24h Volume)")
        trending_label.setFont(QFont('Arial', 16, QFont.Bold))
        layout.addWidget(trending_label)
        
        self.trending_table = QTableWidget()
        self.trending_table.setColumnCount(4)
        self.trending_table.setHorizontalHeaderLabels(["Company", "Price", "Volume", "Trend"])
        self.trending_table.horizontalHeader().setStretchLastSection(True)
        self.trending_table.setAlternatingRowColors(True)
        self.trending_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.trending_table)
        
        self.setLayout(layout)
        self.refresh_data()
    
    def create_summary_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {color}; border-radius: 10px; }}")
        card.setFrameShape(QFrame.StyledPanel)
        
        layout = QVBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 14px;")
        value_lbl = QLabel(value)
        value_lbl.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        value_lbl.setAlignment(Qt.AlignRight)
        
        layout.addWidget(title_lbl)
        layout.addWidget(value_lbl)
        card.setLayout(layout)
        
        if title == "Net Worth": self.net_worth_val = value_lbl
        elif title == "Wallet Balance": self.wallet_val = value_lbl
        elif title == "Portfolio Value": self.portfolio_val = value_lbl
            
        return card

    def refresh_data(self):
        user = auth_service.get_current_user()
        if not user: return
            
        self.welcome_label.setText(f"Welcome back, {user.full_name}!")
        
        # FIX: get_net_worth is a float
        net_worth = user.get_net_worth() 
        portfolio = user.get_portfolio()
        
        self.net_worth_val.setText(Formatter.format_currency(net_worth))
        self.wallet_val.setText(Formatter.format_currency(user.wallet_balance))
        self.portfolio_val.setText(Formatter.format_currency(portfolio['total_current_value']))
        
        trending = trading_service.get_trending_stocks(limit=5)
        self.trending_table.setRowCount(len(trending))
        
        for row, item in enumerate(trending):
            company = item['company']
            
            # Handle company dict/obj duality
            if isinstance(company, dict):
                c_name = company['company_name']
                c_ticker = company['ticker_symbol']
                c_price = company['share_price']
            else:
                c_name = company.company_name
                c_ticker = company.ticker_symbol
                c_price = company.share_price

            volume = item['volume']
            
            self.trending_table.setItem(row, 0, QTableWidgetItem(f"{c_name} ({c_ticker})"))
            
            price_item = QTableWidgetItem(Formatter.format_currency(c_price))
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.trending_table.setItem(row, 1, price_item)
            
            vol_item = QTableWidgetItem(str(volume))
            vol_item.setTextAlignment(Qt.AlignCenter)
            self.trending_table.setItem(row, 2, vol_item)
            
            trend_item = QTableWidgetItem("High Activity" if volume > 1000 else "Moderate")
            self.trending_table.setItem(row, 3, trend_item)