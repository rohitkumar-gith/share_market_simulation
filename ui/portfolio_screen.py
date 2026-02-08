"""
Portfolio Screen - View user holdings and Sell Shares
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from services.auth_service import auth_service
from services.trading_service import trading_service  # <--- NEW IMPORT
from utils.formatters import Formatter
import config

class PortfolioScreen(QWidget):
    """Screen to view current share holdings and sell them"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("My Portfolio")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.total_value_label = QLabel("Total Value: ₹0.00")
        self.total_value_label.setFont(QFont('Arial', 16, QFont.Bold))
        self.total_value_label.setStyleSheet(f"color: {config.COLOR_SECONDARY};")
        header_layout.addWidget(self.total_value_label)
        
        layout.addLayout(header_layout)
        
        # Portfolio Table
        self.portfolio_table = QTableWidget()
        self.portfolio_table.setColumnCount(8) # <--- INCREASED to 8
        self.portfolio_table.setHorizontalHeaderLabels([
            "Company", "Ticker", "Quantity", "Avg Buy Price", 
            "Current Price", "Current Value", "Profit/Loss", "Actions" # <--- NEW COLUMN
        ])
        self.portfolio_table.horizontalHeader().setStretchLastSection(True)
        self.portfolio_table.setAlternatingRowColors(True)
        self.portfolio_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.portfolio_table)
        
        self.setLayout(layout)
        self.refresh_data()
    
    def refresh_data(self):
        """Reload portfolio data"""
        user = auth_service.get_current_user()
        if not user:
            return
            
        portfolio = user.get_portfolio()
        holdings = portfolio['holdings']
        
        self.total_value_label.setText(f"Total Value: {Formatter.format_currency(portfolio['total_current_value'])}")
        
        self.portfolio_table.setRowCount(len(holdings))
        
        for row, holding in enumerate(holdings):
            # Company Name
            self.portfolio_table.setItem(row, 0, QTableWidgetItem(holding['company_name']))
            
            # Ticker
            self.portfolio_table.setItem(row, 1, QTableWidgetItem(holding['ticker_symbol']))
            
            # Quantity
            qty_item = QTableWidgetItem(str(holding['quantity']))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.portfolio_table.setItem(row, 2, qty_item)
            
            # Avg Buy Price
            self.portfolio_table.setItem(row, 3, QTableWidgetItem(
                Formatter.format_currency(holding['average_buy_price'])
            ))
            
            # Current Price
            current_price = holding['current_price'] 
            self.portfolio_table.setItem(row, 4, QTableWidgetItem(
                Formatter.format_currency(current_price)
            ))
            
            # Current Value
            self.portfolio_table.setItem(row, 5, QTableWidgetItem(
                Formatter.format_currency(holding['current_value'])
            ))
            
            # Profit/Loss
            pl = holding['profit_loss']
            pl_percent = holding['profit_loss_percent']
            
            pl_text = f"{Formatter.format_currency(pl)} ({pl_percent:.2f}%)"
            pl_item = QTableWidgetItem(pl_text)
            
            if pl >= 0:
                pl_item.setForeground(QColor(config.COLOR_SUCCESS))
            else:
                pl_item.setForeground(QColor(config.COLOR_DANGER))
                
            self.portfolio_table.setItem(row, 6, pl_item)

            # Actions (Sell Button) <--- NEW
            sell_btn = QPushButton("Sell")
            sell_btn.setStyleSheet(f"background-color: {config.COLOR_DANGER}; color: white; font-weight: bold;")
            # Use lambda to capture the specific holding for this row
            sell_btn.clicked.connect(lambda checked, h=holding: self.sell_shares(h))
            self.portfolio_table.setCellWidget(row, 7, sell_btn)
            
        self.portfolio_table.resizeColumnsToContents()

    def sell_shares(self, holding):
        """Handle sell shares dialog"""
        user = auth_service.get_current_user()
        max_qty = holding['quantity']
        current_price = holding['current_price']
        
        # Ask for quantity
        quantity, ok = QInputDialog.getInt(
            self, "Sell Shares",
            f"Company: {holding['company_name']}\n"
            f"Current Price: {Formatter.format_currency(current_price)}\n"
            f"Your Holdings: {max_qty}\n\n"
            f"Enter quantity to sell:",
            1, 1, max_qty, 1
        )
        
        if ok and quantity > 0:
            # Call Trading Service
            result = trading_service.create_sell_order(
                user.user_id, 
                holding['company_id'], 
                quantity, 
                current_price
            )
            
            if result['success']:
                QMessageBox.information(self, "Success", result['message'])
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Error", result['message'])