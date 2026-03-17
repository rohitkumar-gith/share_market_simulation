"""
Loan Screen - Borrow money from the bank and manage P2P Corporate Loans
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QBrush, QColor
from services.auth_service import auth_service
from services.loan_service import loan_service
from services.company_service import company_service
from utils.formatters import Formatter
import config

class ApplyLoanDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apply for Bank Loan")
        self.setFixedWidth(350)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()
        
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(1000.0, 5000000.0)
        self.amount_spin.setValue(100000.0)
        self.amount_spin.setPrefix("₹ ")
        form.addRow("Loan Amount:", self.amount_spin)
        
        self.term_combo = QComboBox()
        self.term_combo.addItems(["12 Months", "24 Months", "36 Months", "60 Months"])
        form.addRow("Loan Term:", self.term_combo)
        
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self.setLayout(layout)
        
    def get_data(self):
        return self.amount_spin.value(), int(self.term_combo.currentText().split()[0])

class LoanScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        title = QLabel("Financial Center")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 0; }}
            QTabBar::tab {{ background: #2C2C2C; color: white; padding: 10px 20px; font-weight: bold; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }}
            QTabBar::tab:selected {{ background: {config.COLOR_ACCENT}; }}
        """)
        
        self.bank_tab = QWidget()
        self.init_bank_tab()
        self.tabs.addTab(self.bank_tab, "🏦 System Bank")
        
        self.corp_tab = QWidget()
        self.init_corporate_tab()
        self.tabs.addTab(self.corp_tab, "🤝 P2P Corporate Loans")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.refresh_data()

    def init_bank_tab(self):
        layout = QVBoxLayout(self.bank_tab)
        
        apply_btn = QPushButton("💸 Apply for Standard Bank Loan")
        apply_btn.setStyleSheet(f"background-color: {config.COLOR_PRIMARY}; color: white; padding: 10px; font-weight: bold;")
        apply_btn.clicked.connect(self.apply_loan)
        layout.addWidget(apply_btn)
        
        self.loans_table = QTableWidget()
        self.loans_table.setColumnCount(6)
        self.loans_table.setHorizontalHeaderLabels(["Loan Amount", "Interest", "Remaining Balance", "Monthly EMI", "Pay EMI", "Payoff Full"])
        self.loans_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.loans_table)

    def init_corporate_tab(self):
        layout = QVBoxLayout(self.corp_tab)
        
        # 1. Request Form
        req_grp = QGroupBox("Beg a Company for Money")
        form = QFormLayout()
        
        self.target_company_input = QLineEdit()
        self.target_company_input.setPlaceholderText("Enter Lending Company Ticker (e.g., TATA)")
        form.addRow("Lending Company:", self.target_company_input)
        
        self.req_amount = QDoubleSpinBox()
        self.req_amount.setRange(1000, 100000000)
        self.req_amount.setPrefix("₹ ")
        form.addRow("Amount:", self.req_amount)
        
        self.req_interest = QDoubleSpinBox()
        self.req_interest.setRange(1.0, 100.0)
        self.req_interest.setValue(10.0)
        self.req_interest.setSuffix("%")
        form.addRow("Interest Rate:", self.req_interest)
        
        submit_btn = QPushButton("Send Request")
        submit_btn.setStyleSheet(f"background-color: {config.COLOR_WARNING}; color: black; font-weight: bold;")
        submit_btn.clicked.connect(self.request_corporate_loan)
        form.addRow("", submit_btn)
        req_grp.setLayout(form)
        layout.addWidget(req_grp)
        
        # Tables Split
        split = QHBoxLayout()
        
        # Incoming Offers
        inc_layout = QVBoxLayout()
        inc_layout.addWidget(QLabel("<b>Incoming Offers (Accept to get cash)</b>"))
        self.inc_corp_table = QTableWidget()
        self.inc_corp_table.setColumnCount(4)
        self.inc_corp_table.setHorizontalHeaderLabels(["Company", "Amount", "Interest", "Action"])
        self.inc_corp_table.horizontalHeader().setStretchLastSection(True)
        inc_layout.addWidget(self.inc_corp_table)
        split.addLayout(inc_layout)
        
        # Outgoing Requests
        out_layout = QVBoxLayout()
        out_layout.addWidget(QLabel("<b>Your Pending Requests</b>"))
        self.out_corp_table = QTableWidget()
        self.out_corp_table.setColumnCount(3)
        self.out_corp_table.setHorizontalHeaderLabels(["To Company", "Amount", "Action"])
        self.out_corp_table.horizontalHeader().setStretchLastSection(True)
        out_layout.addWidget(self.out_corp_table)
        split.addLayout(out_layout)
        
        layout.addLayout(split)
        
        # Active Debts
        layout.addWidget(QLabel("<b>Active Corporate Debts (Money you owe)</b>"))
        self.active_corp_table = QTableWidget()
        self.active_corp_table.setColumnCount(4)
        self.active_corp_table.setHorizontalHeaderLabels(["Lender", "Original", "Remaining", "Make Payment"])
        self.active_corp_table.horizontalHeader().setStretchLastSection(True)
        self.active_corp_table.setFixedHeight(150)
        layout.addWidget(self.active_corp_table)

    def refresh_data(self):
        self.refresh_bank()
        self.refresh_corporate()
        
    def refresh_bank(self):
        user = auth_service.get_current_user()
        if not user: return
        loans = loan_service.get_user_loans(user.user_id)
        self.loans_table.setRowCount(len(loans))
        for row, loan in enumerate(loans):
            self.loans_table.setItem(row, 0, QTableWidgetItem(Formatter.format_currency(loan['loan_amount'])))
            self.loans_table.setItem(row, 1, QTableWidgetItem(f"{loan['interest_rate']}%"))
            rem = QTableWidgetItem(Formatter.format_currency(loan['remaining_balance']))
            rem.setForeground(QBrush(QColor(Qt.red)))
            self.loans_table.setItem(row, 2, rem)
            self.loans_table.setItem(row, 3, QTableWidgetItem(Formatter.format_currency(loan['monthly_payment'])))
            
            pay_btn = QPushButton("Pay EMI")
            pay_btn.clicked.connect(lambda checked, l=loan: self.pay_emi(l))
            self.loans_table.setCellWidget(row, 4, pay_btn)
            
            full_btn = QPushButton("Payoff")
            full_btn.clicked.connect(lambda checked, l=loan: self.payoff_loan(l))
            self.loans_table.setCellWidget(row, 5, full_btn)

    def refresh_corporate(self):
        user = auth_service.get_current_user()
        if not user: return
        data = company_service.get_player_corporate_loans(user.user_id)
        
        self.inc_corp_table.setRowCount(len(data['incoming_offers']))
        for row, l in enumerate(data['incoming_offers']):
            self.inc_corp_table.setItem(row, 0, QTableWidgetItem(l['other_name']))
            self.inc_corp_table.setItem(row, 1, QTableWidgetItem(Formatter.format_currency(l['amount'])))
            self.inc_corp_table.setItem(row, 2, QTableWidgetItem(f"{l['interest_rate']}%"))
            
            w = QWidget(); lo = QHBoxLayout(w); lo.setContentsMargins(0,0,0,0)
            btn_acc = QPushButton("Accept"); btn_acc.setStyleSheet(f"background-color: {config.COLOR_SUCCESS};")
            btn_rej = QPushButton("Reject"); btn_rej.setStyleSheet(f"background-color: {config.COLOR_DANGER};")
            btn_acc.clicked.connect(lambda checked, ln=l: self.corp_action(ln, "ACCEPT"))
            btn_rej.clicked.connect(lambda checked, ln=l: self.corp_action(ln, "REJECT"))
            lo.addWidget(btn_acc); lo.addWidget(btn_rej)
            self.inc_corp_table.setCellWidget(row, 3, w)

        self.out_corp_table.setRowCount(len(data['outgoing_requests']))
        for row, l in enumerate(data['outgoing_requests']):
            self.out_corp_table.setItem(row, 0, QTableWidgetItem(l['other_name']))
            self.out_corp_table.setItem(row, 1, QTableWidgetItem(Formatter.format_currency(l['amount'])))
            btn = QPushButton("Cancel")
            btn.clicked.connect(lambda checked, ln=l: self.corp_action(ln, "CANCEL"))
            self.out_corp_table.setCellWidget(row, 2, btn)
            
        self.active_corp_table.setRowCount(len(data['active_debts']))
        for row, l in enumerate(data['active_debts']):
            self.active_corp_table.setItem(row, 0, QTableWidgetItem(l['other_name']))
            self.active_corp_table.setItem(row, 1, QTableWidgetItem(Formatter.format_currency(l['amount'])))
            rem = QTableWidgetItem(Formatter.format_currency(l['remaining_balance']))
            rem.setForeground(Qt.red)
            self.active_corp_table.setItem(row, 2, rem)
            
            btn = QPushButton("Make Payment")
            btn.setStyleSheet("background-color: #3498DB; color: white; font-weight:bold;")
            btn.clicked.connect(lambda checked, ln=l: self.pay_corp_loan(ln))
            self.active_corp_table.setCellWidget(row, 3, btn)

    # --- Actions ---

    def request_corporate_loan(self):
        user = auth_service.get_current_user()
        ticker = self.target_company_input.text().strip()
        if not ticker: return QMessageBox.warning(self, "Error", "Enter target company.")
        res = company_service.request_loan(user.user_id, "PLAYER", ticker, self.req_amount.value(), self.req_interest.value(), user.user_id)
        if res['success']:
            QMessageBox.information(self, "Success", res['message'])
            self.refresh_data()
        else: QMessageBox.warning(self, "Error", res['message'])

    def corp_action(self, loan, action):
        user = auth_service.get_current_user()
        res = company_service.respond_to_loan(loan['loan_id'], loan['type'], action, user.user_id)
        if res['success']: self.refresh_data()
        else: QMessageBox.warning(self, "Error", res['message'])

    def pay_corp_loan(self, loan):
        amt, ok = QInputDialog.getDouble(self, "Repay Loan", f"Amount to pay towards {Formatter.format_currency(loan['remaining_balance'])}:", loan['remaining_balance'] * 0.1, 1, loan['remaining_balance'], 2)
        if ok:
            user = auth_service.get_current_user()
            res = company_service.pay_corporate_loan(loan['loan_id'], loan['type'], user.user_id, amt)
            if res['success']: self.refresh_data()
            else: QMessageBox.warning(self, "Error", res['message'])

    def apply_loan(self):
        dialog = ApplyLoanDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            amount, term = dialog.get_data()
            user = auth_service.get_current_user()
            result = loan_service.apply_for_loan(user.user_id, amount, term)
            if result['success']:
                QMessageBox.information(self, "Approved", result['message'])
                self.refresh_data()
            else: QMessageBox.warning(self, "Denied", result['message'])

    def pay_emi(self, loan):
        user = auth_service.get_current_user()
        result = loan_service.pay_loan_installment(user.user_id, loan['loan_id'])
        if result['success']: self.refresh_data()
        else: QMessageBox.warning(self, "Failed", result['message'])

    def payoff_loan(self, loan):
        user = auth_service.get_current_user()
        result = loan_service.payoff_loan_completely(user.user_id, loan['loan_id'])
        if result['success']: self.refresh_data()
        else: QMessageBox.warning(self, "Failed", result['message'])