"""
Market Screen - Buy and Sell Shares (Updated for Custom Pricing)
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from services.auth_service import auth_service
from services.trading_service import trading_service
from services.admin_service import admin_service 
from trading.market_engine import market_engine
from models.company import Company
from utils.formatters import Formatter
from ui.chart_window import ChartWindow
from database.db_manager import db
import config

class MarketTrendDialog(QDialog):
    """Dialog to manually set market trend"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚡ Set Market Trend")
        self.setFixedWidth(300)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Control Market Direction</b>"))
        
        form = QFormLayout()
        
        self.percent_spin = QDoubleSpinBox()
        self.percent_spin.setRange(-90.0, 200.0)
        self.percent_spin.setValue(10.0)
        self.percent_spin.setSuffix("%")
        form.addRow("Target Change:", self.percent_spin)
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 60)
        self.duration_spin.setValue(5)
        self.duration_spin.setSuffix(" mins")
        form.addRow("Duration:", self.duration_spin)
        
        layout.addLayout(form)
        
        # Info
        self.info_lbl = QLabel("Market will gradually move to target.")
        self.info_lbl.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.info_lbl)
        
        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
        self.setLayout(layout)
    
    def get_data(self):
        return self.percent_spin.value(), self.duration_spin.value()

class BuyOrderDialog(QDialog):
    """Custom Dialog to enter Quantity and Price"""
    def __init__(self, company, parent=None):
        super().__init__(parent)
        self.company = company
        self.setWindowTitle(f"Buy {company.ticker_symbol}")
        self.setFixedWidth(350)
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
        default_price = self.company.share_price
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
        # Main Horizontal Layout (Split Screen)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # --- LEFT COLUMN: MARKET TABLE ---
        left_layout = QVBoxLayout()
        
        # Header with Title, Time Selector, and Trend Button
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title = QLabel("Market")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        subtitle = QLabel("Buy & Sell Shares")
        subtitle.setStyleSheet("color: #888; font-size: 12px;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)
        
        header_layout.addStretch()
        
        # --- NEW: Timeframe Selector ---
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["5 Min", "15 Min", "30 Min", "1 Hour", "24 Hours"])
        self.timeframe_combo.setCurrentIndex(4) # Default to 24h
        self.timeframe_combo.setFixedWidth(100)
        self.timeframe_combo.currentIndexChanged.connect(self.refresh_table)
        header_layout.addWidget(QLabel("View:"))
        header_layout.addWidget(self.timeframe_combo)
        
        # Trend Button
        self.trend_btn = QPushButton("⚡ Set Trend")
        self.trend_btn.setStyleSheet("background-color: #8E44AD; color: white; font-weight: bold; padding: 5px 15px;")
        self.trend_btn.clicked.connect(self.open_trend_dialog)
        header_layout.addWidget(self.trend_btn)
        
        left_layout.addLayout(header_layout)
        
        self.companies_table = QTableWidget()
        self.companies_table.setColumnCount(8)
        self.companies_table.setHorizontalHeaderLabels([
            "Ticker", "Company", "Price", "24h Change", "Available", "Market Cap", "Analysis", "Trade"
        ])
        self.companies_table.horizontalHeader().setStretchLastSection(True)
        self.companies_table.setAlternatingRowColors(True)
        self.companies_table.verticalHeader().setDefaultSectionSize(50)
        
        left_layout.addWidget(self.companies_table)
        
        # Add Left Column to Main (Flex 2/3)
        main_layout.addLayout(left_layout, 2)
        
        # --- RIGHT COLUMN: RECENT ACTIVITY ---
        right_layout = QVBoxLayout()
        
        activity_title = QLabel("Recent Activity")
        activity_title.setFont(QFont('Arial', 18, QFont.Bold))
        right_layout.addWidget(activity_title)
        
        self.activity_list = QListWidget()
        self.activity_list.setStyleSheet("""
            QListWidget {
                background-color: #1E1E1E;
                border: 1px solid #333;
                border-radius: 8px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #333;
                color: #DDD;
            }
        """)
        right_layout.addWidget(self.activity_list)
        
        # Add Right Column to Main (Flex 1/3)
        main_layout.addLayout(right_layout, 1)
        
        self.setLayout(main_layout)
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh market data and activity feed"""
        self.refresh_table()
        self.refresh_activity()
        
    def refresh_table(self):
        companies = Company.get_all()
        self.companies_table.setRowCount(len(companies))
        
        # Get selected timeframe in hours
        time_text = self.timeframe_combo.currentText()
        hours = 24.0
        if time_text == "5 Min": hours = 5 / 60
        elif time_text == "15 Min": hours = 15 / 60
        elif time_text == "30 Min": hours = 30 / 60
        elif time_text == "1 Hour": hours = 1.0
        
        # Update Header Label
        self.companies_table.setHorizontalHeaderItem(3, QTableWidgetItem(f"{time_text} Change"))
        
        for row, company in enumerate(companies):
            self.companies_table.setItem(row, 0, QTableWidgetItem(company.ticker_symbol))
            self.companies_table.setItem(row, 1, QTableWidgetItem(company.company_name))
            
            price_item = QTableWidgetItem(Formatter.format_currency(company.share_price))
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.companies_table.setItem(row, 2, price_item)
            
            # Use dynamic hours
            change_data = market_engine.get_price_change(company.company_id, hours=hours)
            change_percent = change_data['change_percent']
            change_item = QTableWidgetItem(f"{change_percent:+.2f}%")
            change_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            if change_percent > 0:
                change_item.setForeground(Qt.green)
            elif change_percent < 0:
                change_item.setForeground(Qt.red)
            else:
                change_item.setForeground(Qt.lightGray)
            self.companies_table.setItem(row, 3, change_item)

            avail_item = QTableWidgetItem(Formatter.format_number(company.available_shares))
            avail_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.companies_table.setItem(row, 4, avail_item)
            
            cap_item = QTableWidgetItem(Formatter.format_currency(company.get_market_cap()))
            cap_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.companies_table.setItem(row, 5, cap_item)
            
            # Chart Button
            chart_btn = QPushButton("View Chart")
            chart_btn.setToolTip("Open Price History")
            chart_btn.setStyleSheet("background-color: #3498DB; color: white; border-radius: 4px; padding: 5px;")
            chart_btn.clicked.connect(lambda checked, c=company: self.show_chart(c))
            self.companies_table.setCellWidget(row, 6, chart_btn)

            # Buy Button
            buy_btn = QPushButton("Buy Share")
            buy_btn.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white; border-radius: 4px; padding: 5px;")
            buy_btn.clicked.connect(lambda checked, c=company: self.buy_shares(c))
            self.companies_table.setCellWidget(row, 7, buy_btn)
        
        self.companies_table.resizeColumnsToContents()

    def refresh_activity(self):
        """Fetch and display recent trades"""
        trades = db.get_recent_market_trades(limit=20)
        self.activity_list.clear()
        
        if not trades:
            self.activity_list.addItem("No recent activity.")
            return
            
        for trade in trades:
            time_str = trade['created_at'].strftime("%H:%M:%S")
            ticker = trade['ticker_symbol']
            qty = trade['quantity']
            price = trade['price_per_share']
            buyer = trade['buyer_name']
            
            # Simple standard message
            text = f"[{time_str}] {buyer} bought {qty} {ticker} @ ₹{price}"
            
            item = QListWidgetItem(text)
            self.activity_list.addItem(item)

    def show_chart(self, company):
        """Open chart window for company"""
        # FIX: Pass company object, not just name/history
        chart = ChartWindow(company, self)
        chart.exec_()
    
    def open_trend_dialog(self):
        """Open dialog to set market trend"""
        dialog = MarketTrendDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            percent, duration = dialog.get_data()
            event_type = 'bull' if percent > 0 else 'bear'
            
            # Call Admin Service
            result = admin_service.trigger_market_event(event_type, duration, percent)
            
            if result['success']:
                QMessageBox.information(self, "Trend Started", result['message'])
            else:
                QMessageBox.warning(self, "Error", result['message'])

    def buy_shares(self, company):
        """Open Buy Dialog"""
        dialog = BuyOrderDialog(company, self)
        if dialog.exec_() == QDialog.Accepted:
            quantity, bid_price = dialog.get_data()
            user = auth_service.get_current_user()
            
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