"""
Loan Screen - Manage loans
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from services.auth_service import auth_service
from services.loan_service import loan_service
from utils.formatters import Formatter
import config


class LoanScreen(QWidget):
    """Loan management screen"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title and apply button
        header_layout = QHBoxLayout()
        title = QLabel("Loans")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        apply_btn = QPushButton("+ Apply for Loan")
        apply_btn.setStyleSheet(f"background-color: {config.COLOR_SECONDARY}; color: white; padding: 10px;")
        apply_btn.clicked.connect(self.apply_for_loan)
        header_layout.addWidget(apply_btn)
        
        layout.addLayout(header_layout)
        
        # Summary
        self.summary_label = QLabel()
        self.summary_label.setFont(QFont('Arial', 12))
        layout.addWidget(self.summary_label)
        
        # Loans table
        self.loans_table = QTableWidget()
        self.loans_table.setColumnCount(7)
        self.loans_table.setHorizontalHeaderLabels([
            "Loan Amount", "Interest Rate", "Remaining", "Monthly Payment",
            "Status", "Due Date", "Actions"
        ])
        self.loans_table.horizontalHeader().setStretchLastSection(True)
        self.loans_table.setAlternatingRowColors(True)
        layout.addWidget(self.loans_table)
        
        self.setLayout(layout)
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh loan data"""
        user = auth_service.get_current_user()
        if not user:
            return
        
        # Update summary
        summary = loan_service.get_loan_summary(user.user_id)
        if summary:
            self.summary_label.setText(
                f"Active Loans: {summary['active_loans']} | "
                f"Total Debt: {Formatter.format_currency(summary['total_debt'])} | "
                f"Monthly Due: {Formatter.format_currency(summary['monthly_payment_due'])}"
            )
        
        # Update loans table
        loans = loan_service.get_user_loans(user.user_id)
        self.loans_table.setRowCount(len(loans))
        
        for row, loan in enumerate(loans):
            self.loans_table.setItem(row, 0, QTableWidgetItem(
                Formatter.format_currency(loan['loan_amount'])
            ))
            self.loans_table.setItem(row, 1, QTableWidgetItem(f"{loan['interest_rate']}%"))
            self.loans_table.setItem(row, 2, QTableWidgetItem(
                Formatter.format_currency(loan['remaining_balance'])
            ))
            self.loans_table.setItem(row, 3, QTableWidgetItem(
                Formatter.format_currency(loan['monthly_payment'])
            ))
            
            status_item = QTableWidgetItem(loan['status'].upper())
            status_item.setForeground(
                Qt.green if loan['status'] == 'paid' else Qt.darkYellow
            )
            self.loans_table.setItem(row, 4, status_item)
            
            self.loans_table.setItem(row, 5, QTableWidgetItem(
                Formatter.format_datetime(loan['due_date'])
            ))
            
            # Payment button
            if loan['status'] == 'active':
                pay_btn = QPushButton("Make Payment")
                pay_btn.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white;")
                pay_btn.clicked.connect(lambda checked, l=loan: self.make_payment(l))
                self.loans_table.setCellWidget(row, 6, pay_btn)
        
        self.loans_table.resizeColumnsToContents()
    
    def apply_for_loan(self):
        """Apply for a new loan"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Apply for Loan")
        dialog.setFixedSize(400, 250)
        
        layout = QFormLayout()
        
        amount_input = QDoubleSpinBox()
        amount_input.setRange(config.MINIMUM_LOAN_AMOUNT, config.MAXIMUM_LOAN_AMOUNT)
        amount_input.setValue(10000)
        amount_input.setPrefix("₹")
        
        term_input = QSpinBox()
        term_input.setRange(config.MINIMUM_LOAN_TERM, config.MAXIMUM_LOAN_TERM)
        term_input.setValue(12)
        term_input.setSuffix(" months")
        
        layout.addRow("Loan Amount:", amount_input)
        layout.addRow("Loan Term:", term_input)
        
        # Preview
        preview_label = QLabel()
        preview_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addRow("", preview_label)
        
        def update_preview():
            result = loan_service.calculate_loan_preview(
                amount_input.value(), term_input.value()
            )
            if result['success']:
                preview_label.setText(
                    f"Monthly Payment: {Formatter.format_currency(result['monthly_payment'])}\n"
                    f"Total Interest: {Formatter.format_currency(result['total_interest'])}"
                )
        
        amount_input.valueChanged.connect(update_preview)
        term_input.valueChanged.connect(update_preview)
        update_preview()
        
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        cancel_btn = QPushButton("Cancel")
        
        apply_btn.clicked.connect(lambda: self.handle_loan_application(
            dialog, amount_input.value(), term_input.value()
        ))
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def handle_loan_application(self, dialog, amount, term):
        """Handle loan application"""
        user = auth_service.get_current_user()
        result = loan_service.apply_for_loan(user.user_id, amount, term)
        
        if result['success']:
            QMessageBox.information(self, "Success", result['message'])
            dialog.accept()
            self.refresh_data()
        else:
            QMessageBox.warning(self, "Error", result['message'])
    
    def make_payment(self, loan):
        """Make loan payment"""
        amount, ok = QInputDialog.getDouble(
            self, "Make Payment",
            f"Enter payment amount (Monthly: {Formatter.format_currency(loan['monthly_payment'])}):",
            loan['monthly_payment'], 1, loan['remaining_balance'], 2
        )
        
        if ok:
            user = auth_service.get_current_user()
            result = loan_service.make_payment(loan['loan_id'], user.user_id, amount)
            
            if result['success']:
                QMessageBox.information(self, "Success", result['message'])
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Error", result['message'])
