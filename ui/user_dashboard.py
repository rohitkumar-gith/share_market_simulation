"""
User Dashboard - Main overview screen
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QGridLayout, QScrollArea, QTableWidget,
                             QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from services.auth_service import auth_service
from services.wallet_service import wallet_service
from models.transaction import Transaction
from models.company import Company
from utils.formatters import Formatter
import config


class UserDashboard(QWidget):
    """User dashboard with portfolio overview"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Dashboard")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        layout.addWidget(title)
        
        # Stats cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        self.wallet_card = self.create_stat_card("Wallet Balance", "₹0", config.COLOR_SUCCESS)
        self.portfolio_card = self.create_stat_card("Portfolio Value", "₹0", config.COLOR_SECONDARY)
        self.networth_card = self.create_stat_card("Net Worth", "₹0", config.COLOR_PRIMARY)
        self.profit_card = self.create_stat_card("Total P/L", "₹0", config.COLOR_WARNING)
        
        stats_layout.addWidget(self.wallet_card)
        stats_layout.addWidget(self.portfolio_card)
        stats_layout.addWidget(self.networth_card)
        stats_layout.addWidget(self.profit_card)
        
        layout.addLayout(stats_layout)
        
        # Recent activity
        activity_label = QLabel("Recent Market Activity")
        activity_label.setFont(QFont('Arial', 16, QFont.Bold))
        layout.addWidget(activity_label)
        
        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(5)
        self.activity_table.setHorizontalHeaderLabels(["Time", "Company", "Type", "Quantity", "Price"])
        self.activity_table.horizontalHeader().setStretchLastSection(True)
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.activity_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.activity_table)
        
        self.setLayout(layout)
        self.refresh_data()
    
    def create_stat_card(self, title, value, color):
        """Create a statistics card"""
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
                padding: 15px;
            }}
        """)
        
        layout = QVBoxLayout()
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #888888; font-size: 12px;")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setFont(QFont('Arial', 20, QFont.Bold))
        value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(value_label)
        
        card.setLayout(layout)
        card.value_label = value_label  # Store reference
        return card
    
    def refresh_data(self):
        """Refresh dashboard data"""
        user = auth_service.get_current_user()
        if not user:
            return
        
        # Update wallet balance
        self.wallet_card.value_label.setText(Formatter.format_currency(user.wallet_balance))
        
        # Update portfolio
        portfolio = user.get_portfolio()
        self.portfolio_card.value_label.setText(
            Formatter.format_currency(portfolio['total_current_value'])
        )
        
        # Update net worth
        net_worth = user.get_net_worth()
        self.networth_card.value_label.setText(
            Formatter.format_currency(net_worth['net_worth'])
        )
        
        # Update profit/loss
        profit_loss = portfolio['total_profit_loss']
        color = config.COLOR_SUCCESS if profit_loss >= 0 else config.COLOR_DANGER
        self.profit_card.value_label.setText(Formatter.format_currency(profit_loss))
        self.profit_card.value_label.setStyleSheet(f"color: {color};")
        
        # Update recent activity
        self.update_activity_table()
    
    def update_activity_table(self):
        """Update recent activity table"""
        transactions = Transaction.get_recent_transactions(limit=20)
        
        self.activity_table.setRowCount(len(transactions))
        
        for row, trans in enumerate(transactions):
            # Time
            time_item = QTableWidgetItem(Formatter.format_datetime(trans['created_at']))
            self.activity_table.setItem(row, 0, time_item)
            
            # Company
            company_item = QTableWidgetItem(f"{trans['ticker_symbol']} - {trans['company_name']}")
            self.activity_table.setItem(row, 1, company_item)
            
            # Type
            type_item = QTableWidgetItem(trans['transaction_type'].upper())
            self.activity_table.setItem(row, 2, type_item)
            
            # Quantity
            qty_item = QTableWidgetItem(str(trans['quantity']))
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.activity_table.setItem(row, 3, qty_item)
            
            # Price
            price_item = QTableWidgetItem(Formatter.format_currency(trans['price_per_share']))
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.activity_table.setItem(row, 4, price_item)
        
        self.activity_table.resizeColumnsToContents()
