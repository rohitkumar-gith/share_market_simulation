"""
Orders Screen - View and Manage Pending Orders
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from services.auth_service import auth_service
from services.trading_service import trading_service
from utils.formatters import Formatter
import config

class OrdersScreen(QWidget):
    """Screen for managing active orders"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("My Active Orders")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Manage your pending buy and sell orders here.")
        subtitle.setStyleSheet("color: #7f8c8d; font-size: 14px;")
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)

        # Orders table
        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(7)
        self.orders_table.setHorizontalHeaderLabels([
            "ID", "Type", "Company", "Remaining Qty", "Price", "Total Value", "Actions"
        ])
        self.orders_table.horizontalHeader().setStretchLastSection(True)
        self.orders_table.setAlternatingRowColors(True)
        layout.addWidget(self.orders_table)
        
        self.setLayout(layout)
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh orders data"""
        user = auth_service.get_current_user()
        if not user:
            return
        
        orders = trading_service.get_my_orders(user.user_id)
        self.orders_table.setRowCount(len(orders))
        
        for row, order in enumerate(orders):
            # ID
            self.orders_table.setItem(row, 0, QTableWidgetItem(f"#{order['order_id']}"))
            
            # Type
            type_item = QTableWidgetItem(order['order_type'].upper())
            if order['order_type'] == 'buy':
                type_item.setForeground(Qt.darkGreen)
            else:
                type_item.setForeground(Qt.red)
            type_item.setFont(QFont("Arial", 10, QFont.Bold))
            self.orders_table.setItem(row, 1, type_item)
            
            # Company
            self.orders_table.setItem(row, 2, QTableWidgetItem(order['ticker_symbol']))
            
            # Remaining Quantity
            qty_item = QTableWidgetItem(str(order['quantity']))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.orders_table.setItem(row, 3, qty_item)
            
            # Price
            self.orders_table.setItem(row, 4, QTableWidgetItem(
                Formatter.format_currency(order['price_per_share'])
            ))
            
            # Total Value
            total_val = order['quantity'] * order['price_per_share']
            self.orders_table.setItem(row, 5, QTableWidgetItem(
                Formatter.format_currency(total_val)
            ))
            
            # Cancel Button
            cancel_btn = QPushButton("Cancel Order")
            cancel_btn.setStyleSheet(f"background-color: {config.COLOR_DANGER}; color: white; font-weight: bold;")
            cancel_btn.clicked.connect(lambda checked, oid=order['order_id']: self.cancel_order(oid))
            self.orders_table.setCellWidget(row, 6, cancel_btn)
        
        self.orders_table.resizeColumnsToContents()

    def cancel_order(self, order_id):
        """Handle cancel action"""
        reply = QMessageBox.question(
            self, 'Confirm Cancel', 
            'Are you sure you want to cancel this order?\nRemaining shares/funds will be returned.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            user = auth_service.get_current_user()
            result = trading_service.cancel_order(order_id, user.user_id)
            
            if result['success']:
                QMessageBox.information(self, "Success", result['message'])
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Error", result['message'])