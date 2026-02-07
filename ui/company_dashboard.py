"""
Company Dashboard - Manage companies
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from services.auth_service import auth_service
from services.company_service import company_service
from utils.formatters import Formatter
import config


class CompanyDashboard(QWidget):
    """Company management dashboard"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title and create button
        header_layout = QHBoxLayout()
        title = QLabel("My Companies")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        create_btn = QPushButton("+ Create Company")
        create_btn.setStyleSheet(f"background-color: {config.COLOR_SUCCESS}; color: white; padding: 10px;")
        create_btn.clicked.connect(self.create_company)
        header_layout.addWidget(create_btn)
        
        layout.addLayout(header_layout)
        
        # Companies table
        self.companies_table = QTableWidget()
        self.companies_table.setColumnCount(6)
        self.companies_table.setHorizontalHeaderLabels([
            "Company", "Ticker", "Share Price", "Shares", "Wallet", "Actions"
        ])
        self.companies_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.companies_table)
        
        self.setLayout(layout)
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh company data"""
        user = auth_service.get_current_user()
        if not user:
            return
        
        companies = company_service.get_user_companies(user.user_id)
        self.companies_table.setRowCount(len(companies))
        
        for row, company in enumerate(companies):
            self.companies_table.setItem(row, 0, QTableWidgetItem(company['company_name']))
            self.companies_table.setItem(row, 1, QTableWidgetItem(company['ticker_symbol']))
            self.companies_table.setItem(row, 2, QTableWidgetItem(
                Formatter.format_currency(company['share_price'])
            ))
            self.companies_table.setItem(row, 3, QTableWidgetItem(
                f"{company['total_shares'] - company['available_shares']}/{company['total_shares']}"
            ))
            self.companies_table.setItem(row, 4, QTableWidgetItem(
                Formatter.format_currency(company['company_wallet'])
            ))
            
            # Actions
            btn_layout = QHBoxLayout()
            btn_widget = QWidget()
            
            dividend_btn = QPushButton("Dividend")
            dividend_btn.clicked.connect(lambda checked, c=company: self.issue_dividend(c))
            btn_layout.addWidget(dividend_btn)
            
            btn_widget.setLayout(btn_layout)
            self.companies_table.setCellWidget(row, 5, btn_widget)
        
        self.companies_table.resizeColumnsToContents()
    
    def create_company(self):
        """Create new company"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Company")
        dialog.setFixedSize(400, 350)
        
        layout = QFormLayout()
        
        name_input = QLineEdit()
        ticker_input = QLineEdit()
        ticker_input.setMaxLength(6)
        price_input = QDoubleSpinBox()
        price_input.setRange(1, 100000)
        price_input.setValue(100)
        price_input.setPrefix("₹")
        shares_input = QSpinBox()
        shares_input.setRange(100, 10000000)
        shares_input.setValue(10000)
        desc_input = QTextEdit()
        desc_input.setMaximumHeight(80)
        
        layout.addRow("Company Name:", name_input)
        layout.addRow("Ticker Symbol:", ticker_input)
        layout.addRow("Initial Share Price:", price_input)
        layout.addRow("Total Shares:", shares_input)
        layout.addRow("Description:", desc_input)
        
        btn_layout = QHBoxLayout()
        create_btn = QPushButton("Create")
        cancel_btn = QPushButton("Cancel")
        
        create_btn.clicked.connect(lambda: self.handle_create_company(
            dialog, name_input.text(), ticker_input.text().upper(),
            price_input.value(), shares_input.value(), desc_input.toPlainText()
        ))
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def handle_create_company(self, dialog, name, ticker, price, shares, desc):
        """Handle company creation"""
        user = auth_service.get_current_user()
        result = company_service.create_company(
            user.user_id, name, ticker, price, shares, desc
        )
        
        if result['success']:
            QMessageBox.information(self, "Success", result['message'])
            dialog.accept()
            self.refresh_data()
        else:
            QMessageBox.warning(self, "Error", result['message'])
    
    def issue_dividend(self, company):
        """Issue dividend"""
        dividend, ok = QInputDialog.getDouble(
            self, "Issue Dividend",
            f"Enter dividend per share for {company['company_name']}:",
            1.0, 0.01, 1000.0, 2
        )
        
        if ok:
            user = auth_service.get_current_user()
            result = company_service.issue_dividend(
                company['company_id'], user.user_id, dividend
            )
            
            if result['success']:
                QMessageBox.information(self, "Success", result['message'])
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Error", result['message'])
