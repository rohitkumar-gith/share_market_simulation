"""
Portfolio Screen - View holdings and Sell Shares
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from services.auth_service import auth_service
from services.trading_service import trading_service
from database.db_manager import db
from utils.formatters import Formatter
import config

class SellOrderDialog(QDialog):
    """Custom Dialog to sell shares with specific price"""
    def __init__(self, holding, parent=None):
        super().__init__(parent)
        self.holding = holding
        self.setWindowTitle(f"Sell {holding['ticker_symbol']}")
        self.setFixedWidth(350)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Info Header
        info_layout = QFormLayout()
        info_layout.addRow("Company:", QLabel(self.holding['company_name']))
        
        qty_label = QLabel(str(self.holding['quantity']))
        qty_label.setStyleSheet(f"color: {config.COLOR_ACCENT}; font-weight: bold;")
        info_layout.addRow("Shares Owned:", qty_label)
        
        current_price_lbl = QLabel(Formatter.format_currency(self.holding['current_price']))
        info_layout.addRow("Current Market Price:", current_price_lbl)
        
        layout.addLayout(info_layout)
        
        layout.addWidget(QLabel("<b>Sell Order Details</b>"))
        
        # Inputs
        form = QFormLayout()
        
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, self.holding['quantity'])
        self.qty_spin.setValue(min(10, self.holding['quantity']))
        self.qty_spin.valueChanged.connect(self.update_total)
        form.addRow("Quantity to Sell:", self.qty_spin)
        
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.10, 1000000.00)
        # Default to current market price
        self.price_spin.setValue(self.holding['current_price'])
        self.price_spin.setSingleStep(0.10)
        self.price_spin.valueChanged.connect(self.update_total)
        form.addRow("Asking Price (₹):", self.price_spin)
        
        layout.addLayout(form)
        
        # Total
        self.total_lbl = QLabel("Total Receive: ₹0.00")
        self.total_lbl.setFont(QFont('Arial', 11, QFont.Bold))
        self.total_lbl.setAlignment(Qt.AlignRight)
        self.total_lbl.setStyleSheet(f"color: {config.COLOR_SUCCESS};")
        layout.addWidget(self.total_lbl)
        
        # Warning for High Price
        self.warning_lbl = QLabel("")
        self.warning_lbl.setStyleSheet(f"color: {config.COLOR_WARNING}; font-size: 11px;")
        self.warning_lbl.setWordWrap(True)
        layout.addWidget(self.warning_lbl)
        
        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
        self.setLayout(layout)
        self.update_total()
        
    def update_total(self):
        qty = self.qty_spin.value()
        price = self.price_spin.value()
        total = qty * price
        
        # Fee calculation (simulated visual only)
        fee = total * config.TRANSACTION_FEE_PERCENT / 100
        final = total - fee
        
        self.total_lbl.setText(f"Est. Return (after fee): {Formatter.format_currency(final)}")
        
        # Warning if price is too high above market
        market_price = self.holding['current_price']
        if price > market_price * 1.20:
            self.warning_lbl.setText("⚠️ High Price: Order may take a long time to fill.")
        elif price < market_price * 0.80:
            self.warning_lbl.setText("⚠️ Low Price: Shares will likely sell instantly.")
        else:
            self.warning_lbl.setText("")
        
    def get_data(self):
        return self.qty_spin.value(), self.price_spin.value()

class PortfolioScreen(QWidget):
    """User Portfolio Screen"""
    
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
        
        self.total_value_lbl = QLabel("Total Value: ₹0.00")
        self.total_value_lbl.setFont(QFont('Arial', 14, QFont.Bold))
        self.total_value_lbl.setStyleSheet(f"color: {config.COLOR_ACCENT};")
        header_layout.addWidget(self.total_value_lbl)
        
        layout.addLayout(header_layout)
        
        # Holdings Table
        self.holdings_table = QTableWidget()
        self.holdings_table.setColumnCount(9)
        self.holdings_table.setHorizontalHeaderLabels([
            "Ticker", "Company", "Qty", "Avg Buy Price", "Current Price", 
            "Invested", "Current Value", "P/L", "Action"
        ])
        self.holdings_table.horizontalHeader().setStretchLastSection(True)
        self.holdings_table.setAlternatingRowColors(True)
        self.holdings_table.verticalHeader().setDefaultSectionSize(50) # Taller rows for buttons
        
        layout.addWidget(self.holdings_table)
        
        self.setLayout(layout)
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh portfolio data"""
        user = auth_service.get_current_user()
        if not user: return
        
        holdings = db.get_user_holdings(user.user_id)
        self.holdings_table.setRowCount(len(holdings))
        
        total_portfolio_value = 0.0
        
        for row, holding in enumerate(holdings):
            self.holdings_table.setItem(row, 0, QTableWidgetItem(holding['ticker_symbol']))
            self.holdings_table.setItem(row, 1, QTableWidgetItem(holding['company_name']))
            
            # Quantity
            qty_item = QTableWidgetItem(str(holding['quantity']))
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.holdings_table.setItem(row, 2, qty_item)
            
            # Avg Buy
            avg_item = QTableWidgetItem(Formatter.format_currency(holding['average_buy_price']))
            avg_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.holdings_table.setItem(row, 3, avg_item)
            
            # Current Price
            curr_item = QTableWidgetItem(Formatter.format_currency(holding['current_price']))
            curr_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.holdings_table.setItem(row, 4, curr_item)
            
            # Invested
            invested_item = QTableWidgetItem(Formatter.format_currency(holding['total_invested']))
            invested_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.holdings_table.setItem(row, 5, invested_item)
            
            # Current Value
            curr_val = holding['quantity'] * holding['current_price']
            total_portfolio_value += curr_val
            val_item = QTableWidgetItem(Formatter.format_currency(curr_val))
            val_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            val_item.setFont(QFont('Arial', 10, QFont.Bold))
            self.holdings_table.setItem(row, 6, val_item)
            
            # Profit/Loss
            pl = holding['profit_loss']
            pl_percent = holding['profit_loss_percent']
            pl_text = f"{Formatter.format_currency(pl)} ({pl_percent:+.2f}%)"
            pl_item = QTableWidgetItem(pl_text)
            pl_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            if pl > 0:
                pl_item.setForeground(Qt.green)
            elif pl < 0:
                pl_item.setForeground(Qt.red)
            else:
                pl_item.setForeground(Qt.lightGray)
            self.holdings_table.setItem(row, 7, pl_item)
            
            # Sell Button
            sell_btn = QPushButton("Sell")
            sell_btn.setStyleSheet(f"background-color: {config.COLOR_DANGER}; color: white; font-weight: bold; border-radius: 4px;")
            # We use a lambda to capture the specific holding for this row
            sell_btn.clicked.connect(lambda checked, h=holding: self.sell_shares(h))
            self.holdings_table.setCellWidget(row, 8, sell_btn)
            
        self.holdings_table.resizeColumnsToContents()
        self.total_value_lbl.setText(f"Total Value: {Formatter.format_currency(total_portfolio_value)}")

    def sell_shares(self, holding):
        """Open Sell Dialog"""
        dialog = SellOrderDialog(holding, self)
        if dialog.exec_() == QDialog.Accepted:
            qty, price = dialog.get_data()
            user = auth_service.get_current_user()
            
            result = trading_service.create_sell_order(
                user.user_id,
                holding['company_id'],
                qty,
                price
            )
            
            if result['success']:
                QMessageBox.information(self, "Success", result['message'])
                self.refresh_data()
                # Also refresh wallet if visible/needed, handled by main window timer
            else:
                QMessageBox.warning(self, "Error", result['message'])