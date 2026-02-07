"""
Portfolio Screen - View holdings and Sell shares
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from services.auth_service import auth_service
from services.trading_service import trading_service
from utils.formatters import Formatter
import config


class PortfolioScreen(QWidget):
    """Portfolio screen showing user holdings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("My Portfolio")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        layout.addWidget(title)
        
        # Summary
        self.summary_label = QLabel()
        self.summary_label.setFont(QFont('Arial', 12))
        layout.addWidget(self.summary_label)
        
        # Holdings table
        self.holdings_table = QTableWidget()
        # Changed column count to 8 to include Actions
        self.holdings_table.setColumnCount(8)
        self.holdings_table.setHorizontalHeaderLabels([
            "Company", "Quantity", "Avg Buy Price", "Current Price", 
            "Invested", "Current Value", "P/L", "Actions"
        ])
        self.holdings_table.horizontalHeader().setStretchLastSection(True)
        self.holdings_table.setAlternatingRowColors(True)
        layout.addWidget(self.holdings_table)
        
        self.setLayout(layout)
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh portfolio data"""
        user = auth_service.get_current_user()
        if not user:
            return
        
        portfolio = user.get_portfolio()
        
        # Update summary
        pl_text, pl_type = Formatter.format_profit_loss(
            portfolio['total_current_value'],
            portfolio['total_invested']
        )
        self.summary_label.setText(
            f"Total Invested: {Formatter.format_currency(portfolio['total_invested'])} | "
            f"Current Value: {Formatter.format_currency(portfolio['total_current_value'])} | "
            f"P/L: {pl_text}"
        )
        
        # Update holdings table
        holdings = portfolio['holdings']
        self.holdings_table.setRowCount(len(holdings))
        
        for row, holding in enumerate(holdings):
            self.holdings_table.setItem(row, 0, QTableWidgetItem(holding['company_name']))
            self.holdings_table.setItem(row, 1, QTableWidgetItem(str(holding['quantity'])))
            self.holdings_table.setItem(row, 2, QTableWidgetItem(
                Formatter.format_currency(holding['average_buy_price'])
            ))
            self.holdings_table.setItem(row, 3, QTableWidgetItem(
                Formatter.format_currency(holding['share_price'])
            ))
            self.holdings_table.setItem(row, 4, QTableWidgetItem(
                Formatter.format_currency(holding['total_invested'])
            ))
            self.holdings_table.setItem(row, 5, QTableWidgetItem(
                Formatter.format_currency(holding['current_value'])
            ))
            
            # P/L
            pl = holding['profit_loss']
            pl_item = QTableWidgetItem(Formatter.format_currency(pl))
            pl_item.setForeground(
                Qt.green if pl >= 0 else Qt.red
            )
            self.holdings_table.setItem(row, 6, pl_item)

            # --- Sell Button (New) ---
            sell_btn = QPushButton("Sell")
            sell_btn.setStyleSheet(f"background-color: {config.COLOR_WARNING}; color: white;")
            # Use lambda to pass the specific holding data to the function
            sell_btn.clicked.connect(lambda checked, h=holding: self.sell_shares(h))
            self.holdings_table.setCellWidget(row, 7, sell_btn)
        
        self.holdings_table.resizeColumnsToContents()

    def sell_shares(self, holding):
        """Handle sell shares action"""
        # 1. Ask for Quantity
        quantity, ok = QInputDialog.getInt(
            self,
            "Sell Shares",
            f"Enter quantity to sell (Max: {holding['quantity']}):",
            1, 1, holding['quantity'], 1
        )
        if not ok: return

        # 2. Ask for Price
        price, ok = QInputDialog.getDouble(
            self,
            "Sell Shares",
            f"Enter price per share (Current: {Formatter.format_currency(holding['share_price'])}):",
            holding['share_price'], 0.01, 1000000.0, 2
        )
        if not ok: return

        # 3. Create Sell Order
        user = auth_service.get_current_user()
        result = trading_service.create_sell_order(
            user.user_id, 
            holding['company_id'], 
            quantity, 
            price
        )

        # 4. Show Result
        if result['success']:
            QMessageBox.information(self, "Success", "Sell order placed successfully!\nIt will be executed when a buyer is found.")
            self.refresh_data()
        else:
            QMessageBox.warning(self, "Error", result['message'])