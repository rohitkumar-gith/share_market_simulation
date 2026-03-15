"""
Portfolio Screen - View holdings, assets, and Sell Shares
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QBrush, QColor
from services.auth_service import auth_service
from services.trading_service import trading_service
from services.asset_service import asset_service
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
        info_layout = QFormLayout()
        info_layout.addRow("Company:", QLabel(self.holding['company_name']))
        qty_label = QLabel(str(self.holding['quantity']))
        qty_label.setStyleSheet(f"color: {config.COLOR_ACCENT}; font-weight: bold;")
        info_layout.addRow("Shares Owned:", qty_label)
        current_price_lbl = QLabel(Formatter.format_currency(self.holding['current_price']))
        info_layout.addRow("Current Market Price:", current_price_lbl)
        layout.addLayout(info_layout)
        layout.addWidget(QLabel("<b>Sell Order Details</b>"))
        
        form = QFormLayout()
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, self.holding['quantity'])
        self.qty_spin.setValue(min(10, self.holding['quantity']))
        self.qty_spin.valueChanged.connect(self.update_total)
        form.addRow("Quantity to Sell:", self.qty_spin)
        
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.10, 1000000.00)
        self.price_spin.setValue(self.holding['current_price'])
        self.price_spin.setSingleStep(0.10)
        self.price_spin.valueChanged.connect(self.update_total)
        form.addRow("Asking Price (₹):", self.price_spin)
        
        layout.addLayout(form)
        self.total_lbl = QLabel("Total Receive: ₹0.00")
        self.total_lbl.setFont(QFont('Arial', 11, QFont.Bold))
        self.total_lbl.setAlignment(Qt.AlignRight)
        self.total_lbl.setStyleSheet(f"color: {config.COLOR_SUCCESS};")
        layout.addWidget(self.total_lbl)
        
        self.warning_lbl = QLabel("")
        self.warning_lbl.setStyleSheet(f"color: {config.COLOR_WARNING}; font-size: 11px;")
        self.warning_lbl.setWordWrap(True)
        layout.addWidget(self.warning_lbl)
        
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
        fee = total * config.TRANSACTION_FEE_PERCENT / 100
        final = total - fee
        self.total_lbl.setText(f"Est. Return (after fee): {Formatter.format_currency(final)}")
        
        market_price = self.holding['current_price']
        if price > market_price * 1.20:
            self.warning_lbl.setText("⚠️ High Price: Order may take a long time to fill.")
        elif price < market_price * 0.80:
            self.warning_lbl.setText("⚠️ Low Price: Shares will likely sell instantly.")
        else:
            self.warning_lbl.setText("")
        
    def get_data(self):
        return self.qty_spin.value(), self.price_spin.value()

class ListAssetDialog(QDialog):
    """Dialog to list a luxury asset or update its price"""
    def __init__(self, asset, current_price=None, parent=None):
        super().__init__(parent)
        self.asset = asset
        self.current_price = current_price
        self.setWindowTitle("Update Price" if current_price else f"List {asset['name']} For Sale")
        self.setFixedWidth(350)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        info_layout = QFormLayout()
        info_layout.addRow("Asset:", QLabel(self.asset['name']))
        info_layout.addRow("You Paid:", QLabel(Formatter.format_currency(self.asset['acquired_price'])))
        layout.addLayout(info_layout)
        
        layout.addWidget(QLabel("<b>Set Marketplace Asking Price</b>"))
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(1.0, 999999999.0)
        
        # If updating, show current price. Else, suggest a 10% markup.
        default_price = self.current_price if self.current_price else self.asset['acquired_price'] * 1.10
        self.price_spin.setValue(default_price)
        self.price_spin.setPrefix("₹ ")
        
        layout.addWidget(self.price_spin)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self.setLayout(layout)
        
    def get_price(self):
        return self.price_spin.value()

class PortfolioScreen(QWidget):
    """User Portfolio Screen (Stocks & Assets)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        title = QLabel("My Portfolio")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.total_value_lbl = QLabel("Total Stock Value: ₹0.00")
        self.total_value_lbl.setFont(QFont('Arial', 14, QFont.Bold))
        self.total_value_lbl.setStyleSheet(f"color: {config.COLOR_ACCENT};")
        header_layout.addWidget(self.total_value_lbl)
        layout.addLayout(header_layout)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 0; }}
            QTabBar::tab {{ background: #2C2C2C; color: white; padding: 10px 20px; font-weight: bold; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }}
            QTabBar::tab:selected {{ background: {config.COLOR_ACCENT}; }}
        """)
        
        self.stocks_tab = QWidget()
        self.init_stocks_tab()
        self.tabs.addTab(self.stocks_tab, "📈 Stock Holdings")
        
        self.assets_tab = QWidget()
        self.init_assets_tab()
        self.tabs.addTab(self.assets_tab, "💎 My Luxury Assets")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.refresh_data()

    def init_stocks_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 10, 0, 0)
        self.holdings_table = QTableWidget()
        self.holdings_table.setColumnCount(9)
        self.holdings_table.setHorizontalHeaderLabels([
            "Ticker", "Company", "Qty", "Avg Buy Price", "Current Price", 
            "Invested", "Current Value", "P/L", "Action"
        ])
        self.holdings_table.horizontalHeader().setStretchLastSection(True)
        self.holdings_table.setAlternatingRowColors(True)
        self.holdings_table.verticalHeader().setDefaultSectionSize(50)
        layout.addWidget(self.holdings_table)
        self.stocks_tab.setLayout(layout)

    def init_assets_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 10, 0, 0)
        
        income_layout = QHBoxLayout()
        self.pending_income_lbl = QLabel("Pending Real Estate Income: ₹0.00")
        self.pending_income_lbl.setFont(QFont('Arial', 14, QFont.Bold))
        self.pending_income_lbl.setStyleSheet(f"color: {config.COLOR_SUCCESS};")
        
        self.collect_btn = QPushButton("💰 Collect Income")
        self.collect_btn.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white; padding: 10px 20px; font-weight: bold; border-radius: 4px; font-size: 14px;")
        self.collect_btn.clicked.connect(self.collect_passive_income)
        self.collect_btn.setEnabled(False)
        
        income_layout.addWidget(self.pending_income_lbl)
        income_layout.addStretch()
        income_layout.addWidget(self.collect_btn)
        layout.addLayout(income_layout)
        
        self.assets_table = QTableWidget()
        self.assets_table.setColumnCount(5)
        self.assets_table.setHorizontalHeaderLabels([
            "Asset Name", "Type", "Acquired Price", "Status", "Marketplace Action"
        ])
        self.assets_table.horizontalHeader().setStretchLastSection(True)
        self.assets_table.setAlternatingRowColors(True)
        self.assets_table.verticalHeader().setDefaultSectionSize(50)
        
        layout.addWidget(self.assets_table)
        self.assets_tab.setLayout(layout)

    def refresh_data(self):
        self.refresh_stocks()
        self.refresh_assets()
        
    def refresh_stocks(self):
        user = auth_service.get_current_user()
        if not user: return
        
        holdings = db.get_user_holdings(user.user_id)
        self.holdings_table.setRowCount(len(holdings))
        total_portfolio_value = 0.0
        
        for row, holding in enumerate(holdings):
            self.holdings_table.setItem(row, 0, QTableWidgetItem(holding['ticker_symbol']))
            self.holdings_table.setItem(row, 1, QTableWidgetItem(holding['company_name']))
            
            qty_item = QTableWidgetItem(str(holding['quantity']))
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.holdings_table.setItem(row, 2, qty_item)
            
            avg_item = QTableWidgetItem(Formatter.format_currency(holding['average_buy_price']))
            avg_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.holdings_table.setItem(row, 3, avg_item)
            
            curr_item = QTableWidgetItem(Formatter.format_currency(holding['current_price']))
            curr_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.holdings_table.setItem(row, 4, curr_item)
            
            invested_item = QTableWidgetItem(Formatter.format_currency(holding['total_invested']))
            invested_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.holdings_table.setItem(row, 5, invested_item)
            
            curr_val = holding['quantity'] * holding['current_price']
            total_portfolio_value += curr_val
            val_item = QTableWidgetItem(Formatter.format_currency(curr_val))
            val_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            val_item.setFont(QFont('Arial', 10, QFont.Bold))
            self.holdings_table.setItem(row, 6, val_item)
            
            pl = holding['profit_loss']
            pl_percent = holding['profit_loss_percent']
            pl_item = QTableWidgetItem(f"{Formatter.format_currency(pl)} ({pl_percent:+.2f}%)")
            pl_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            if pl > 0: pl_item.setForeground(QBrush(QColor(Qt.green)))
            elif pl < 0: pl_item.setForeground(QBrush(QColor(Qt.red)))
            else: pl_item.setForeground(QBrush(QColor(Qt.lightGray)))
            self.holdings_table.setItem(row, 7, pl_item)
            
            sell_btn = QPushButton("Sell")
            sell_btn.setStyleSheet(f"background-color: {config.COLOR_DANGER}; color: white; font-weight: bold; border-radius: 4px;")
            sell_btn.clicked.connect(lambda checked, h=holding: self.sell_shares(h))
            self.holdings_table.setCellWidget(row, 8, sell_btn)
            
        self.holdings_table.resizeColumnsToContents()
        self.total_value_lbl.setText(f"Total Stock Value: {Formatter.format_currency(total_portfolio_value)}")

    def refresh_assets(self):
        user = auth_service.get_current_user()
        if not user: return
        
        pending = asset_service.calculate_user_pending_revenue(user.user_id)
        self.pending_income_lbl.setText(f"Pending Real Estate Income: {Formatter.format_currency(pending)}")
        self.collect_btn.setEnabled(pending > 0)
        
        assets = asset_service.get_user_assets(user.user_id)
        self.assets_table.setRowCount(len(assets))
        
        for row, asset in enumerate(assets):
            name_item = QTableWidgetItem(asset['name'])
            name_item.setFont(QFont('Arial', 11, QFont.Bold))
            self.assets_table.setItem(row, 0, name_item)
            
            type_icon = "🏢 " if asset['asset_type'] == 'REAL_ESTATE' else "🏎️ "
            self.assets_table.setItem(row, 1, QTableWidgetItem(f"{type_icon}{asset['asset_type']}"))
            
            acq_item = QTableWidgetItem(Formatter.format_currency(asset['acquired_price']))
            self.assets_table.setItem(row, 2, acq_item)
            
            is_listed = asset['listed_price'] is not None
            
            # --- NEW DYNAMIC ACTION PANEL ---
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 5, 5, 5)
            
            if is_listed:
                status_item = QTableWidgetItem(f"Listed for {Formatter.format_currency(asset['listed_price'])}")
                status_item.setForeground(QBrush(QColor(Qt.yellow)))
                
                edit_btn = QPushButton("Edit Price")
                edit_btn.setStyleSheet("background-color: #3498DB; color: white; border-radius: 4px; padding: 5px;")
                edit_btn.clicked.connect(lambda checked, a=asset: self.edit_listing(a))
                
                cancel_btn = QPushButton("Cancel")
                cancel_btn.setStyleSheet(f"background-color: {config.COLOR_DANGER}; color: white; border-radius: 4px; padding: 5px;")
                cancel_btn.clicked.connect(lambda checked, a=asset: self.cancel_listing(a))
                
                action_layout.addWidget(edit_btn)
                action_layout.addWidget(cancel_btn)
            else:
                status_item = QTableWidgetItem("In Garage / Property Owned")
                status_item.setForeground(QBrush(QColor(Qt.green)))
                
                list_btn = QPushButton("List For Sale")
                list_btn.setStyleSheet(f"background-color: {config.COLOR_SECONDARY}; color: white; border-radius: 4px; padding: 5px; font-weight: bold;")
                list_btn.clicked.connect(lambda checked, a=asset: self.list_asset(a))
                action_layout.addWidget(list_btn)
                
            self.assets_table.setItem(row, 3, status_item)
            self.assets_table.setCellWidget(row, 4, action_widget)
            
        self.assets_table.resizeColumnsToContents()

    def collect_passive_income(self):
        user = auth_service.get_current_user()
        if not user: return
        result = asset_service.collect_user_revenue(user.user_id)
        if result['success'] and result['amount'] > 0:
            QMessageBox.information(self, "Income Collected!", f"Successfully transferred {Formatter.format_currency(result['amount'])} to your wallet.")
            self.refresh_data()
        else:
            QMessageBox.warning(self, "No Funds", "There is no pending revenue to collect yet.")

    def sell_shares(self, holding):
        dialog = SellOrderDialog(holding, self)
        if dialog.exec_() == QDialog.Accepted:
            qty, price = dialog.get_data()
            user = auth_service.get_current_user()
            result = trading_service.create_sell_order(user.user_id, holding['company_id'], qty, price)
            if result['success']:
                QMessageBox.information(self, "Success", result['message'])
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Error", result['message'])

    def list_asset(self, asset):
        dialog = ListAssetDialog(asset, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            price = dialog.get_price()
            user = auth_service.get_current_user()
            result = asset_service.list_asset_for_sale(user.user_id, asset['instance_id'], price)
            if result['success']:
                QMessageBox.information(self, "Listed Successfully", result['message'])
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Error", result['message'])

    def edit_listing(self, asset):
        """Update the price of an existing listing"""
        dialog = ListAssetDialog(asset, current_price=asset['listed_price'], parent=self)
        if dialog.exec_() == QDialog.Accepted:
            new_price = dialog.get_price()
            user = auth_service.get_current_user()
            result = asset_service.update_asset_listing(user.user_id, asset['listing_id'], new_price)
            if result['success']:
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Error", result['message'])

    def cancel_listing(self, asset):
        """Cancel an active marketplace listing"""
        reply = QMessageBox.question(self, 'Cancel Listing', f"Remove {asset['name']} from the marketplace?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            user = auth_service.get_current_user()
            result = asset_service.cancel_asset_listing(user.user_id, asset['listing_id'])
            if result['success']:
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Error", result['message'])