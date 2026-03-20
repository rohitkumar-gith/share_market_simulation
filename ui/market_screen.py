"""
Market Screen - Buy and Sell Shares & Player Marketplace
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, 
                             QListWidgetItem, QMessageBox, QTabWidget, QComboBox, 
                             QDialog, QFormLayout, QSpinBox, QDoubleSpinBox, QDialogButtonBox,
                             QInputDialog) # Ensure QInputDialog is available
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QBrush, QColor
from services.auth_service import auth_service
from services.trading_service import trading_service
from services.admin_service import admin_service 
from services.asset_service import asset_service
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
    """Market screen for trading shares and buying assets"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the Tabbed UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 0; }}
            QTabBar::tab {{ background: #2C2C2C; color: white; padding: 12px 25px; font-weight: bold; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; font-size: 14px; }}
            QTabBar::tab:selected {{ background: {config.COLOR_ACCENT}; }}
        """)
        
        # Tab 1: Stocks
        self.stock_widget = QWidget()
        self.init_stock_tab()
        self.tabs.addTab(self.stock_widget, "📈 Stock Market")
        
        # Tab 2: Assets & Marketplace
        self.asset_widget = QWidget()
        self.init_asset_tab()
        self.tabs.addTab(self.asset_widget, "💎 Luxury Assets & Real Estate")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        
        self.refresh_data()

    def init_stock_tab(self):
        """Build the original stock market split screen inside Tab 1"""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # --- LEFT COLUMN: MARKET TABLE ---
        left_layout = QVBoxLayout()
        
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title = QLabel("Stock Exchange")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        subtitle = QLabel("Buy & Sell Company Shares")
        subtitle.setStyleSheet("color: #888; font-size: 14px;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)
        
        header_layout.addStretch()
        
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["5 Min", "15 Min", "30 Min", "1 Hour", "24 Hours"])
        self.timeframe_combo.setCurrentIndex(4) 
        self.timeframe_combo.setFixedWidth(100)
        self.timeframe_combo.currentIndexChanged.connect(lambda idx: self.refresh_table())
        header_layout.addWidget(QLabel("View:"))
        header_layout.addWidget(self.timeframe_combo)
        
        self.trend_btn = QPushButton("⚡ Set Trend")
        self.trend_btn.setStyleSheet("background-color: #8E44AD; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px;")
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
        
        main_layout.addLayout(right_layout, 1)
        
        self.stock_widget.setLayout(main_layout)

    def init_asset_tab(self):
        """Build the new Luxury Asset Marketplace with Sub-Tabs"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        title = QLabel("Global Marketplace")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        subtitle = QLabel("Buy brand new assets or trade directly with other players.")
        subtitle.setStyleSheet("color: #888; font-size: 14px;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # --- SUB-TAB SYSTEM FOR ASSETS ---
        self.asset_sub_tabs = QTabWidget()
        self.asset_sub_tabs.setStyleSheet("""
            QTabBar::tab { background: #333; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px; margin: 2px;}
            QTabBar::tab:selected { background: #E67E22; }
        """)

        # Sub-Tab 1: Official Store
        self.official_store_widget = QWidget()
        os_layout = QVBoxLayout(self.official_store_widget)
        self.assets_table = QTableWidget()
        self.assets_table.setColumnCount(6)
        self.assets_table.setHorizontalHeaderLabels([
            "Asset Name", "Type", "Description", "Price", "Passive Income", "Action"
        ])
        self.assets_table.horizontalHeader().setStretchLastSection(True)
        self.assets_table.setAlternatingRowColors(True)
        self.assets_table.verticalHeader().setDefaultSectionSize(60)
        os_layout.addWidget(self.assets_table)
        self.asset_sub_tabs.addTab(self.official_store_widget, "🏢 Official Store")

        # Sub-Tab 2: Player Marketplace
        self.player_market_widget = QWidget()
        pm_layout = QVBoxLayout(self.player_market_widget)
        self.p2p_table = QTableWidget()
        self.p2p_table.setColumnCount(6)
        self.p2p_table.setHorizontalHeaderLabels([
            "Asset Name", "Seller", "Asking Price", "Passive Income", "Listed On", "Action"
        ])
        self.p2p_table.horizontalHeader().setStretchLastSection(True)
        self.p2p_table.setAlternatingRowColors(True)
        self.p2p_table.verticalHeader().setDefaultSectionSize(60)
        pm_layout.addWidget(self.p2p_table)
        self.asset_sub_tabs.addTab(self.player_market_widget, "🤝 Player Marketplace")

        layout.addWidget(self.asset_sub_tabs)
        self.asset_widget.setLayout(layout)

    def refresh_data(self):
        """Refresh all market data and assets"""
        self.refresh_table()
        self.refresh_activity()
        self.refresh_official_store()
        self.refresh_player_marketplace()
        
    def refresh_official_store(self):
        """Load brand new luxury assets from the master catalog"""
        assets = asset_service.get_all_assets()
        self.assets_table.setRowCount(len(assets))
        
        for row, asset in enumerate(assets):
            name_item = QTableWidgetItem(asset['name'])
            name_item.setFont(QFont('Arial', 11, QFont.Bold))
            self.assets_table.setItem(row, 0, name_item)
            
            type_icon = "🏢 " if asset['asset_type'] == 'REAL_ESTATE' else "🏎️ "
            self.assets_table.setItem(row, 1, QTableWidgetItem(f"{type_icon}{asset['asset_type']}"))
            
            # Show availability in description if limited stock
            avail_str = f"Stock: {asset.get('available_quantity', 'Infinite')}"
            if asset.get('total_quantity', -1) == -1: avail_str = "Stock: Infinite"
            self.assets_table.setItem(row, 2, QTableWidgetItem(avail_str))
            
            price_item = QTableWidgetItem(Formatter.format_currency(asset['base_price']))
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.assets_table.setItem(row, 3, price_item)
            
            if asset['revenue_rate'] > 0:
                inc_text = f"+ {Formatter.format_currency(asset['revenue_rate'])} / min"
                inc_item = QTableWidgetItem(inc_text)
                inc_item.setForeground(QBrush(QColor(Qt.green)))
            else:
                inc_item = QTableWidgetItem("None (Flex Item)")
                inc_item.setForeground(QBrush(QColor(Qt.lightGray)))
            inc_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.assets_table.setItem(row, 4, inc_item)
            
            buy_btn = QPushButton("Buy New")
            buy_btn.setStyleSheet(f"background-color: {config.COLOR_SECONDARY}; color: white; border-radius: 4px; padding: 8px; font-weight: bold;")
            buy_btn.clicked.connect(lambda checked, a=asset: self.buy_official_asset(a))
            self.assets_table.setCellWidget(row, 5, buy_btn)
            
        self.assets_table.resizeColumnsToContents()
        self.assets_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

    def refresh_player_marketplace(self):
        """Load active P2P listings from other players"""
        listings = asset_service.get_marketplace_listings()
        self.p2p_table.setRowCount(len(listings))
        
        current_user = auth_service.get_current_user()
        
        for row, listing in enumerate(listings):
            name_item = QTableWidgetItem(listing['name'])
            name_item.setFont(QFont('Arial', 11, QFont.Bold))
            self.p2p_table.setItem(row, 0, name_item)
            
            seller_item = QTableWidgetItem(listing['seller_name'])
            if current_user and current_user.user_id == listing['seller_id']:
                seller_item.setText(f"{listing['seller_name']} (You)")
                seller_item.setForeground(QBrush(QColor(Qt.cyan)))
            self.p2p_table.setItem(row, 1, seller_item)
            
            price_item = QTableWidgetItem(Formatter.format_currency(listing['asking_price']))
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.p2p_table.setItem(row, 2, price_item)
            
            if listing['revenue_rate'] > 0:
                inc_text = f"+ {Formatter.format_currency(listing['revenue_rate'])} / min"
                inc_item = QTableWidgetItem(inc_text)
                inc_item.setForeground(QBrush(QColor(Qt.green)))
            else:
                inc_item = QTableWidgetItem("None (Flex Item)")
                inc_item.setForeground(QBrush(QColor(Qt.lightGray)))
            inc_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.p2p_table.setItem(row, 3, inc_item)
            
            try:
                time_str = listing['created_at'].strftime("%Y-%m-%d %H:%M")
            except AttributeError:
                raw_time = str(listing['created_at'])
                time_str = raw_time[:16]
            self.p2p_table.setItem(row, 4, QTableWidgetItem(time_str))
            
            if current_user and current_user.user_id == listing['seller_id']:
                btn = QPushButton("Your Listing")
                btn.setEnabled(False)
                btn.setStyleSheet("background-color: #555; color: #888; border-radius: 4px; padding: 8px;")
            else:
                btn = QPushButton("Buy from Player")
                btn.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white; border-radius: 4px; padding: 8px; font-weight: bold;")
                btn.clicked.connect(lambda checked, l=listing: self.buy_p2p_asset(l))
            self.p2p_table.setCellWidget(row, 5, btn)
            
        self.p2p_table.resizeColumnsToContents()

    def buy_official_asset(self, asset):
        """Handle buying from system store with quantity selection"""
        user = auth_service.get_current_user()
        if not user: return
        
        # Determine max quantity they can buy based on stock limits
        max_avail = asset.get('available_quantity', -1)
        limit = max_avail if max_avail != -1 else 1000000 # Use a high limit if infinite
        
        if max_avail == 0:
            QMessageBox.warning(self, "Out of Stock", f"Sorry, {asset['name']} is completely sold out!")
            return

        # Prompt user for quantity
        qty, ok = QInputDialog.getInt(
            self, "Purchase Quantity", 
            f"How many {asset['name']}s do you want to buy?\n\nPrice per item: {Formatter.format_currency(asset['base_price'])}", 
            1, 1, limit, 1
        )
        
        if ok:
            result = asset_service.buy_asset_for_user(user.user_id, asset['asset_id'], purchase_qty=qty)
            if result['success']:
                QMessageBox.information(self, "Transaction Complete", result['message'])
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Transaction Failed", result['message'])

    def buy_p2p_asset(self, listing):
        """Handle buying from another player"""
        reply = QMessageBox.question(
            self, 'Confirm P2P Purchase',
            f"Buy {listing['name']} from {listing['seller_name']} for {Formatter.format_currency(listing['asking_price'])}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            user = auth_service.get_current_user()
            result = asset_service.buy_marketplace_asset(user.user_id, listing['listing_id'])
            if result['success']:
                QMessageBox.information(self, "Purchase Successful", result['message'])
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Transaction Failed", result['message'])

    def refresh_table(self):
        companies = Company.get_all()
        self.companies_table.setRowCount(len(companies))
        
        time_text = self.timeframe_combo.currentText()
        hours = 24.0
        if time_text == "5 Min": hours = 5 / 60
        elif time_text == "15 Min": hours = 15 / 60
        elif time_text == "30 Min": hours = 30 / 60
        elif time_text == "1 Hour": hours = 1.0
        
        self.companies_table.setHorizontalHeaderItem(3, QTableWidgetItem(f"{time_text} Change"))
        
        for row, company in enumerate(companies):
            self.companies_table.setItem(row, 0, QTableWidgetItem(company.ticker_symbol))
            self.companies_table.setItem(row, 1, QTableWidgetItem(company.company_name))
            
            price_item = QTableWidgetItem(Formatter.format_currency(company.share_price))
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.companies_table.setItem(row, 2, price_item)
            
            change_data = market_engine.get_price_change(company.company_id, hours=hours)
            change_percent = change_data['change_percent']
            change_item = QTableWidgetItem(f"{change_percent:+.2f}%")
            change_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            if change_percent > 0:
                change_item.setForeground(QBrush(QColor(Qt.green)))
            elif change_percent < 0:
                change_item.setForeground(QBrush(QColor(Qt.red)))
            else:
                change_item.setForeground(QBrush(QColor(Qt.lightGray)))
            self.companies_table.setItem(row, 3, change_item)

            avail_item = QTableWidgetItem(Formatter.format_number(company.available_shares))
            avail_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.companies_table.setItem(row, 4, avail_item)
            
            cap_item = QTableWidgetItem(Formatter.format_currency(company.get_market_cap()))
            cap_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.companies_table.setItem(row, 5, cap_item)
            
            chart_btn = QPushButton("View Chart")
            chart_btn.setToolTip("Open Price History")
            chart_btn.setStyleSheet("background-color: #3498DB; color: white; border-radius: 4px; padding: 5px;")
            chart_btn.clicked.connect(lambda checked, c=company: self.show_chart(c))
            self.companies_table.setCellWidget(row, 6, chart_btn)

            buy_btn = QPushButton("Buy Share")
            buy_btn.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white; border-radius: 4px; padding: 5px;")
            buy_btn.clicked.connect(lambda checked, c=company: self.buy_shares(c))
            self.companies_table.setCellWidget(row, 7, buy_btn)
        
        self.companies_table.resizeColumnsToContents()

    def refresh_activity(self):
        trades = db.get_recent_market_trades(limit=20)
        self.activity_list.clear()
        
        if not trades:
            self.activity_list.addItem("No recent activity.")
            return
            
        for trade in trades:
            try:
                time_str = trade['created_at'].strftime("%H:%M:%S")
            except AttributeError:
                raw_time = str(trade['created_at'])
                time_str = raw_time[11:19] if len(raw_time) > 11 else "00:00:00"

            ticker = trade['ticker_symbol']
            qty = trade['quantity']
            price = trade['price_per_share']
            buyer = trade['buyer_name']
            text = f"[{time_str}] {buyer} bought {qty} {ticker} @ ₹{price}"
            self.activity_list.addItem(QListWidgetItem(text))

    def show_chart(self, company):
        chart = ChartWindow(company, self)
        chart.exec_()
    
    def open_trend_dialog(self):
        dialog = MarketTrendDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            percent, duration = dialog.get_data()
            event_type = 'bull' if percent > 0 else 'bear'
            result = admin_service.trigger_market_event(event_type, duration, percent)
            if result['success']:
                QMessageBox.information(self, "Trend Started", result['message'])
            else:
                QMessageBox.warning(self, "Error", result['message'])

    def buy_shares(self, company):
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