"""
Commodities Market - Trade Gold, Silver, and Platinum
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QBrush
from services.auth_service import auth_service
from services.commodity_service import commodity_service
from utils.formatters import Formatter
import config

class CommodityScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Header ---
        header = QLabel("⚖️ The Bullion Exchange")
        header.setFont(QFont('Arial', 24, QFont.Bold))
        header.setStyleSheet(f"color: {config.COLOR_ACCENT};")
        main_layout.addWidget(header)
        
        info = QLabel("Trade physical commodities (measured in grams). A safe haven for your wealth.")
        info.setStyleSheet("color: #AAA; font-size: 14px; margin-bottom: 10px;")
        main_layout.addWidget(info)

        split_layout = QHBoxLayout()
        split_layout.setSpacing(20)

        # --- LEFT: Live Market & Trading ---
        trade_layout = QVBoxLayout()
        trade_layout.addWidget(QLabel("<b>Live Metal Prices (per Gram)</b>"))
        
        self.market_table = QTableWidget()
        self.market_table.setColumnCount(3)
        self.market_table.setHorizontalHeaderLabels(["Metal", "Symbol", "Price/Gram"])
        self.market_table.horizontalHeader().setStretchLastSection(True)
        self.market_table.setAlternatingRowColors(True)
        self.market_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.market_table.verticalHeader().setDefaultSectionSize(40)
        self.market_table.setStyleSheet("QTableWidget { background-color: #1E1E1E; border-radius: 8px; }")
        trade_layout.addWidget(self.market_table)
        
        # Trading Console
        action_grp = QGroupBox("Trading Console")
        form = QFormLayout()
        
        self.action_combo = QComboBox()
        self.action_combo.addItems(["Buy Metal", "Sell Metal"])
        form.addRow("Action:", self.action_combo)
        
        self.metal_combo = QComboBox()
        form.addRow("Select Metal:", self.metal_combo)
        
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setRange(1.0, 1000000.0)
        self.qty_spin.setValue(10.0)
        self.qty_spin.setSuffix(" Grams")
        form.addRow("Quantity:", self.qty_spin)
        
        self.execute_btn = QPushButton("Execute Trade")
        self.execute_btn.setStyleSheet(f"background-color: {config.COLOR_ACCENT}; color: white; font-weight: bold; padding: 10px;")
        self.execute_btn.clicked.connect(self.execute_trade)
        form.addRow("", self.execute_btn)
        
        action_grp.setLayout(form)
        trade_layout.addWidget(action_grp)
        
        split_layout.addLayout(trade_layout, 5)

        # --- RIGHT: Personal Vault ---
        vault_layout = QVBoxLayout()
        vault_title = QLabel("🔐 Your Personal Vault")
        vault_title.setFont(QFont('Arial', 18, QFont.Bold))
        vault_layout.addWidget(vault_title)
        
        self.vault_table = QTableWidget()
        self.vault_table.setColumnCount(5)
        self.vault_table.setHorizontalHeaderLabels(["Metal", "Quantity", "Avg Buy Price", "Current Value", "P/L"])
        self.vault_table.horizontalHeader().setStretchLastSection(True)
        self.vault_table.setAlternatingRowColors(True)
        self.vault_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.vault_table.verticalHeader().setDefaultSectionSize(45)
        self.vault_table.setStyleSheet("QTableWidget { background-color: #1E1E1E; border-radius: 8px; }")
        vault_layout.addWidget(self.vault_table)
        
        split_layout.addLayout(vault_layout, 5)
        main_layout.addLayout(split_layout)
        
        self.refresh_data()

    def refresh_data(self):
        user = auth_service.get_current_user()
        if not user: return
        
        # 1. Update Market
        metals = commodity_service.get_market_prices()
        self.market_table.setRowCount(len(metals))
        
        # Preserve combo selection if possible
        current_metal = self.metal_combo.currentData()
        self.metal_combo.blockSignals(True)
        self.metal_combo.clear()
        
        for row, m in enumerate(metals):
            # Market Table
            name_item = QTableWidgetItem(m['name'])
            name_item.setForeground(QBrush(QColor(m['color'])))
            name_item.setFont(QFont('Arial', 10, QFont.Bold))
            self.market_table.setItem(row, 0, name_item)
            
            self.market_table.setItem(row, 1, QTableWidgetItem(m['symbol']))
            
            price_item = QTableWidgetItem(Formatter.format_currency(m['current_price']))
            price_item.setForeground(QBrush(QColor(Qt.green)))
            self.market_table.setItem(row, 2, price_item)
            
            # Populate Combo
            self.metal_combo.addItem(f"{m['name']} ({Formatter.format_currency(m['current_price'])}/g)", m['id'])
            if m['id'] == current_metal:
                self.metal_combo.setCurrentIndex(row)
                
        self.metal_combo.blockSignals(False)
        
        # 2. Update Vault
        vault = commodity_service.get_user_vault(user.user_id)
        self.vault_table.setRowCount(len(vault))
        
        for row, v in enumerate(vault):
            name_item = QTableWidgetItem(f"{v['name']} ({v['symbol']})")
            name_item.setForeground(QBrush(QColor(v['color'])))
            name_item.setFont(QFont('Arial', 10, QFont.Bold))
            self.vault_table.setItem(row, 0, name_item)
            
            self.vault_table.setItem(row, 1, QTableWidgetItem(f"{v['quantity']:,.2f}g"))
            self.vault_table.setItem(row, 2, QTableWidgetItem(Formatter.format_currency(v['average_buy_price'])))
            
            current_val = v['quantity'] * v['current_price']
            self.vault_table.setItem(row, 3, QTableWidgetItem(Formatter.format_currency(current_val)))
            
            # Profit/Loss Calculation
            total_cost = v['quantity'] * v['average_buy_price']
            pl = current_val - total_cost
            pl_item = QTableWidgetItem(Formatter.format_currency(pl))
            if pl >= 0: pl_item.setForeground(QBrush(QColor(Qt.green)))
            else: pl_item.setForeground(QBrush(QColor(Qt.red)))
            self.vault_table.setItem(row, 4, pl_item)

    def execute_trade(self):
        user = auth_service.get_current_user()
        if not user: return
        
        action = self.action_combo.currentText()
        metal_id = self.metal_combo.currentData()
        qty = self.qty_spin.value()
        
        if not metal_id: return
        
        if action == "Buy Metal":
            res = commodity_service.buy_metal(user.user_id, metal_id, qty)
        else:
            res = commodity_service.sell_metal(user.user_id, metal_id, qty)
            
        if res['success']:
            QMessageBox.information(self, "Trade Executed", res['message'])
            self.refresh_data()
        else:
            QMessageBox.warning(self, "Trade Failed", res['message'])