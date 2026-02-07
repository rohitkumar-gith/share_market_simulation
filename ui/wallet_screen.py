"""
Wallet Screen - Manage funds
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from services.auth_service import auth_service
from services.wallet_service import wallet_service
from utils.formatters import Formatter
import config


class WalletScreen(QWidget):
    """Wallet management screen"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Wallet")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        layout.addWidget(title)
        
        # Balance card
        balance_frame = QFrame()
        balance_frame.setStyleSheet("background-color: white; border-radius: 10px; padding: 20px;")
        balance_layout = QVBoxLayout()
        
        balance_label = QLabel("Current Balance")
        balance_label.setStyleSheet("color: #888; font-size: 14px;")
        balance_layout.addWidget(balance_label)
        
        self.balance_value = QLabel("₹0")
        self.balance_value.setFont(QFont('Arial', 32, QFont.Bold))
        self.balance_value.setStyleSheet(f"color: {config.COLOR_SUCCESS};")
        balance_layout.addWidget(self.balance_value)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("+ Add Funds")
        add_btn.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white; padding: 10px;")
        add_btn.clicked.connect(self.add_funds)
        btn_layout.addWidget(add_btn)
        
        withdraw_btn = QPushButton("- Withdraw")
        withdraw_btn.setStyleSheet(f"background-color: {config.COLOR_WARNING}; color: white; padding: 10px;")
        withdraw_btn.clicked.connect(self.withdraw_funds)
        btn_layout.addWidget(withdraw_btn)
        
        transfer_btn = QPushButton("↔ Transfer")
        transfer_btn.setStyleSheet(f"background-color: {config.COLOR_SECONDARY}; color: white; padding: 10px;")
        transfer_btn.clicked.connect(self.transfer_funds)
        btn_layout.addWidget(transfer_btn)
        
        balance_layout.addLayout(btn_layout)
        balance_frame.setLayout(balance_layout)
        layout.addWidget(balance_frame)
        
        # Transaction history
        history_label = QLabel("Transaction History")
        history_label.setFont(QFont('Arial', 16, QFont.Bold))
        layout.addWidget(history_label)
        
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(4)
        self.transactions_table.setHorizontalHeaderLabels(["Date", "Type", "Amount", "Balance"])
        self.transactions_table.horizontalHeader().setStretchLastSection(True)
        self.transactions_table.setAlternatingRowColors(True)
        layout.addWidget(self.transactions_table)
        
        self.setLayout(layout)
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh wallet data"""
        user = auth_service.get_current_user()
        if not user:
            return
        
        # Update balance
        self.balance_value.setText(Formatter.format_currency(user.wallet_balance))
        
        # Update transactions
        transactions = wallet_service.get_transaction_history(user.user_id, 50)
        self.transactions_table.setRowCount(len(transactions))
        
        for row, trans in enumerate(transactions):
            self.transactions_table.setItem(row, 0, QTableWidgetItem(
                Formatter.format_datetime(trans['created_at'])
            ))
            self.transactions_table.setItem(row, 1, QTableWidgetItem(
                trans['transaction_type'].replace('_', ' ').title()
            ))
            
            amount_item = QTableWidgetItem(Formatter.format_currency(trans['amount']))
            amount_item.setForeground(
                Qt.green if trans['amount'] > 0 else Qt.red
            )
            self.transactions_table.setItem(row, 2, amount_item)
            
            self.transactions_table.setItem(row, 3, QTableWidgetItem(
                Formatter.format_currency(trans['balance_after'])
            ))
        
        self.transactions_table.resizeColumnsToContents()
    
    def add_funds(self):
        """Add funds to wallet"""
        amount, ok = QInputDialog.getDouble(
            self, "Add Funds", "Enter amount to add:", 1000, 1, 1000000, 2
        )
        
        if ok:
            user = auth_service.get_current_user()
            result = wallet_service.add_funds(user.user_id, amount)
            
            if result['success']:
                QMessageBox.information(self, "Success", result['message'])
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Error", result['message'])
    
    def withdraw_funds(self):
        """Withdraw funds"""
        amount, ok = QInputDialog.getDouble(
            self, "Withdraw Funds", "Enter amount to withdraw:", 1000, 1, 1000000, 2
        )
        
        if ok:
            user = auth_service.get_current_user()
            result = wallet_service.withdraw_funds(user.user_id, amount)
            
            if result['success']:
                QMessageBox.information(self, "Success", result['message'])
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Error", result['message'])
    
    def transfer_funds(self):
        """Transfer funds to another user"""
        username, ok1 = QInputDialog.getText(
            self, "Transfer Funds", "Enter recipient username:"
        )
        
        if ok1 and username:
            amount, ok2 = QInputDialog.getDouble(
                self, "Transfer Funds", f"Enter amount to transfer to {username}:",
                100, 1, 1000000, 2
            )
            
            if ok2:
                user = auth_service.get_current_user()
                result = wallet_service.transfer_funds(user.user_id, username, amount)
                
                if result['success']:
                    QMessageBox.information(self, "Success", result['message'])
                    self.refresh_data()
                else:
                    QMessageBox.warning(self, "Error", result['message'])
