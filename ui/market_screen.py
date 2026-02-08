"""
Market Screen - Buy and Sell Shares (Updated for Custom Pricing)
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from services.auth_service import auth_service
from services.trading_service import trading_service
from trading.market_engine import market_engine
from models.company import Company
from utils.formatters import Formatter
from ui.chart_window import ChartWindow
import config

class BuyOrderDialog(QDialog):
    """Custom Dialog to enter Quantity and Price"""
    def __init__(self, company, parent=None):
        super().__init__(parent)
        self.company = company
        self.setWindowTitle(f"Buy {company.ticker_symbol}")
        self.setFixedWidth(300)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Info Header
        info_layout = QFormLayout()
        info_layout.addRow("Current Price:", QLabel(Formatter.format_currency(self.company.share_price)))
        info_layout.addRow("Available (IPO):", QLabel(str(self.company.available_shares)))
        layout.addLayout(info_layout)
        
        layout.addWidget(QLabel("<b>Place Order</b>"))
        
        # Inputs
        form = QFormLayout()
        
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 1000000)
        self.qty_spin.setValue(10)
        self.qty_spin.valueChanged.connect(self.update_total)
        form.addRow("Quantity:", self.qty_spin)
        
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.10, 1000000.00)
        # Default to Current + 2% for priority, but let user change it
        default_price = round(self.company.share_price * 1.02, 2)
        self.price_spin.setValue(default_price)
        self.price_spin.setSingleStep(0.10)
        self.price_spin.valueChanged.connect(self.update_total)
        form.addRow("Bid Price (₹):", self.price_spin)
        
        layout.addLayout(form)
        
        # Total
        self.total_lbl = QLabel("Total: ₹0.00")
        self.total_lbl.setFont(QFont('Arial', 11, QFont.Bold))
        self.total_lbl.setAlignment(Qt.AlignRight)
        layout.addWidget(self.total_lbl)
        
        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
        self.setLayout(layout)
        self.update_total()
        
    def update_total(self):
        total = self.qty_spin.value() * self.price_spin.value()
        self.total_lbl.setText(f"Total: {Formatter.format_currency(total)}")
        
    def get_data(self):
        return self.qty_spin.value(), self.price_spin.value()

class MarketScreen(QWidget):
    """Market screen for trading shares"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Market - Buy & Sell Shares")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        layout.addWidget(title)
        
        self.companies_table = QTableWidget()
        self.companies_table.setColumnCount(8)
        self.companies_table.setHorizontalHeaderLabels([
            "Ticker", "Company", "Price", "24h Change", "Available", "Market Cap", "Chart", "Actions"
        ])
        self.companies_table.horizontalHeader().setStretchLastSection(True)
        self.companies_table.setAlternatingRowColors(True)
        layout.addWidget(self.companies_table)
        
        self.setLayout(layout)
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh market data"""
        companies = Company.get_all()
        self.companies_table.setRowCount(len(companies))
        
        for row, company in enumerate(companies):
            self.companies_table.setItem(row, 0, QTableWidgetItem(company.ticker_symbol))
            self.companies_table.setItem(row, 1, QTableWidgetItem(company.company_name))
            
            price_item = QTableWidgetItem(Formatter.format_currency(company.share_price))
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.companies_table.setItem(row, 2, price_item)
            
            change_data = market_engine.get_price_change(company.company_id, hours=24)
            change_percent = change_data['change_percent']
            change_item = QTableWidgetItem(f"{change_percent:+.2f}%")
            change_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            if change_percent > 0:
                change_item.setForeground(Qt.darkGreen)
            elif change_percent < 0:
                change_item.setForeground(Qt.red)
            else:
                change_item.setForeground(Qt.black)
            self.companies_table.setItem(row, 3, change_item)

            avail_item = QTableWidgetItem(Formatter.format_number(company.available_shares))
            avail_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.companies_table.setItem(row, 4, avail_item)
            
            cap_item = QTableWidgetItem(Formatter.format_currency(company.get_market_cap()))
            cap_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.companies_table.setItem(row, 5, cap_item)
            
            # Chart Button
            chart_btn = QPushButton("📈")
            chart_btn.setToolTip("View Price Chart")
            chart_btn.setStyleSheet("background-color: #3498DB; color: white; font-weight: bold;")
            chart_btn.clicked.connect(lambda checked, c=company: self.show_chart(c))
            self.companies_table.setCellWidget(row, 6, chart_btn)

            # Buy Button
            buy_btn = QPushButton("Buy")
            buy_btn.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white;")
            buy_btn.clicked.connect(lambda checked, c=company: self.buy_shares(c))
            self.companies_table.setCellWidget(row, 7, buy_btn)
        
        self.companies_table.resizeColumnsToContents()
    
    def show_chart(self, company):
        """Open chart window for company"""
        history = market_engine.get_price_history(company.company_id)
        chart = ChartWindow(company.company_name, history, self)
        chart.exec_()

    def buy_shares(self, company):
        """Open Buy Dialog"""
        dialog = BuyOrderDialog(company, self)
        if dialog.exec_() == QDialog.Accepted:
            quantity, bid_price = dialog.get_data()
            user = auth_service.get_current_user()
            
            # Call updated process_buy_request with custom price
            result = trading_service.process_buy_request(
                user.user_id, 
                company.company_id, 
                quantity, 
                bid_price
            )
            
            if result['success']:
                QMessageBox.information(self, "Success", result['message'])
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Error", result['message'])