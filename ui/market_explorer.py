"""
Market Explorer - Public directory to view all companies, their owners, and public ledgers.
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QBrush
from services.company_service import company_service
from services.auth_service import auth_service
from utils.formatters import Formatter
import config

class MarketExplorerScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Header ---
        header = QLabel("🌍 Global Market Explorer")
        header.setFont(QFont('Arial', 24, QFont.Bold))
        header.setStyleSheet(f"color: {config.COLOR_ACCENT};")
        main_layout.addWidget(header)
        
        info = QLabel("Public directory of all registered corporations. Scout for investments or hostile takeover targets.")
        info.setStyleSheet("color: #AAA; font-size: 14px; margin-bottom: 15px;")
        main_layout.addWidget(info)

        # --- Main Content Area (Stable Horizontal Layout) ---
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # --- LEFT PANEL: Company List ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        list_label = QLabel("Registered Companies")
        list_label.setFont(QFont('Arial', 14, QFont.Bold))
        left_layout.addWidget(list_label)
        
        self.companies_table = QTableWidget()
        self.companies_table.setColumnCount(3)
        self.companies_table.setHorizontalHeaderLabels(["Ticker", "Company Name", "Price"])
        self.companies_table.horizontalHeader().setStretchLastSection(True)
        self.companies_table.setAlternatingRowColors(True)
        self.companies_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.companies_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.companies_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.companies_table.verticalHeader().setVisible(False)
        self.companies_table.setStyleSheet("QTableWidget { background-color: #1E1E1E; border-radius: 8px; }")
        
        self.companies_table.itemSelectionChanged.connect(self.load_selected_company)
        left_layout.addWidget(self.companies_table)
        
        content_layout.addWidget(left_widget, 35) # Takes 35% of width
        
        # --- RIGHT PANEL: Stacked Widget for Stability ---
        self.right_stack = QStackedWidget()
        
        # Page 0: Placeholder View
        placeholder_page = QWidget()
        place_layout = QVBoxLayout(placeholder_page)
        msg = QLabel("Select a company from the list\nto view its public ledger and financials.")
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("color: #666; font-size: 18px; font-style: italic;")
        place_layout.addWidget(msg)
        self.right_stack.addWidget(placeholder_page)
        
        # Page 1: Detail View
        self.detail_page = QWidget()
        self.right_layout = QVBoxLayout(self.detail_page)
        self.right_layout.setContentsMargins(10, 0, 0, 0)
        
        # Details Header
        self.detail_name = QLabel("Select a company...")
        self.detail_name.setFont(QFont('Arial', 22, QFont.Bold))
        self.right_layout.addWidget(self.detail_name)
        
        self.detail_owner = QLabel("👑 Current Owner: --")
        self.detail_owner.setFont(QFont('Arial', 16, QFont.Bold))
        self.detail_owner.setStyleSheet("color: #D4AF37; margin-bottom: 10px;") # Gold
        self.right_layout.addWidget(self.detail_owner)
        
        # Stats Grid
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background-color: #2C2C2C; border-radius: 8px;")
        stats_layout = QGridLayout(stats_frame)
        
        self.lbl_price = self.create_stat_label("Current Share Price:", "--")
        self.lbl_mcap = self.create_stat_label("Market Cap:", "--")
        self.lbl_total_shares = self.create_stat_label("Total Issued Shares:", "--")
        self.lbl_avail_shares = self.create_stat_label("Available in IPO Pool:", "--")
        
        stats_layout.addWidget(self.lbl_price[0], 0, 0); stats_layout.addWidget(self.lbl_price[1], 0, 1)
        stats_layout.addWidget(self.lbl_mcap[0], 1, 0); stats_layout.addWidget(self.lbl_mcap[1], 1, 1)
        stats_layout.addWidget(self.lbl_total_shares[0], 0, 2); stats_layout.addWidget(self.lbl_total_shares[1], 0, 3)
        stats_layout.addWidget(self.lbl_avail_shares[0], 1, 2); stats_layout.addWidget(self.lbl_avail_shares[1], 1, 3)
        self.right_layout.addWidget(stats_frame)
        
        # Description
        self.right_layout.addWidget(QLabel("<b>Company Description:</b>"))
        self.detail_desc = QTextEdit()
        self.detail_desc.setReadOnly(True)
        self.detail_desc.setMaximumHeight(80)
        self.detail_desc.setStyleSheet("background-color: #1E1E1E; border: 1px solid #444; border-radius: 4px;")
        self.right_layout.addWidget(self.detail_desc)
        
        # Public Ledger (Shareholders)
        ledger_lbl = QLabel("📖 Public Shareholder Ledger")
        ledger_lbl.setFont(QFont('Arial', 14, QFont.Bold))
        ledger_lbl.setStyleSheet("margin-top: 10px;")
        self.right_layout.addWidget(ledger_lbl)
        
        self.ledger_table = QTableWidget()
        self.ledger_table.setColumnCount(4)
        self.ledger_table.setHorizontalHeaderLabels(["Rank", "Investor Name", "Shares Owned", "Ownership %"])
        self.ledger_table.horizontalHeader().setStretchLastSection(True)
        self.ledger_table.setAlternatingRowColors(True)
        self.ledger_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ledger_table.verticalHeader().setVisible(False)
        self.ledger_table.setStyleSheet("QTableWidget { background-color: #1E1E1E; border-radius: 8px; }")
        self.right_layout.addWidget(self.ledger_table)
        
        # Push all contents to the top so it doesn't float around weirdly
        self.right_layout.addStretch()
        
        self.right_stack.addWidget(self.detail_page)
        
        content_layout.addWidget(self.right_stack, 65) # Takes 65% of width
        
        # Add content layout to main with a stretch factor of 1 to push the header to the very top!
        main_layout.addLayout(content_layout, 1)
        
        self.refresh_data()

    def create_stat_label(self, title, default_val):
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #888; font-weight: bold;")
        val_lbl = QLabel(default_val)
        val_lbl.setFont(QFont('Arial', 12, QFont.Bold))
        val_lbl.setStyleSheet("color: white;")
        return title_lbl, val_lbl

    def refresh_data(self):
        """Loads all companies into the left table and secretly preserves selection"""
        company_service.check_hostile_takeovers()
        
        # 1. Memorize currently selected company ID before wiping the table
        selected_company_id = None
        selected_items = self.companies_table.selectedItems()
        if selected_items:
            selected_company_id = self.companies_table.item(selected_items[0].row(), 0).data(Qt.UserRole)
        
        # 2. Block signals so the UI doesn't freak out while we rebuild it
        self.companies_table.blockSignals(True)
        
        companies = company_service.get_all_companies()
        self.companies_table.setRowCount(len(companies))
        
        row_to_reselect = -1
        
        for row, comp in enumerate(companies):
            t_item = QTableWidgetItem(comp['ticker_symbol'])
            t_item.setFont(QFont('Arial', 10, QFont.Bold))
            t_item.setData(Qt.UserRole, comp['company_id'])
            
            self.companies_table.setItem(row, 0, t_item)
            self.companies_table.setItem(row, 1, QTableWidgetItem(comp['company_name']))
            
            p_item = QTableWidgetItem(Formatter.format_currency(comp['share_price']))
            p_item.setForeground(QBrush(QColor(Qt.green)))
            self.companies_table.setItem(row, 2, p_item)
            
            # Check if this is the row we had selected earlier
            if comp['company_id'] == selected_company_id:
                row_to_reselect = row
                
        self.companies_table.resizeColumnsToContents()
        
        # 3. Restore selection quietly
        if row_to_reselect >= 0:
            self.companies_table.selectRow(row_to_reselect)
        
        # 4. Re-enable signals
        self.companies_table.blockSignals(False)
        
        # 5. Manually trigger the right-side update if we reselected something, 
        # otherwise go back to the placeholder page
        if row_to_reselect >= 0:
            self.load_selected_company()
        else:
            self.right_stack.setCurrentIndex(0)

    def load_selected_company(self):
        """Fills the right panel when a company is clicked"""
        selected_items = self.companies_table.selectedItems()
        if not selected_items:
            self.right_stack.setCurrentIndex(0)
            return
            
        # Get the hidden company_id
        company_id = self.companies_table.item(selected_items[0].row(), 0).data(Qt.UserRole)
        details = company_service.get_company_details(company_id)
        if not details: return
        
        comp = details['company']
        self.detail_name.setText(f"{comp['company_name']} ({comp['ticker_symbol']})")
        self.detail_desc.setText(comp.get('description') or "No description provided.")
        
        self.lbl_price[1].setText(Formatter.format_currency(comp['share_price']))
        self.lbl_mcap[1].setText(Formatter.format_currency(details['market_cap']))
        self.lbl_total_shares[1].setText(Formatter.format_number(comp['total_shares']))
        self.lbl_avail_shares[1].setText(Formatter.format_number(comp['available_shares']))
        
        # Populate Public Ledger
        shareholders = details.get('shareholders', [])
        self.ledger_table.setRowCount(len(shareholders))
        
        owner_name = "Unknown"
        current_user = auth_service.get_current_user()
        
        for row, holder in enumerate(shareholders):
            h_dict = dict(holder) # Fix for SQLite row
            
            if h_dict['user_id'] == comp['owner_id']:
                owner_name = h_dict['full_name']
                if h_dict['username'].endswith('Bot'): owner_name += " 🤖"
                if current_user and h_dict['user_id'] == current_user.user_id: owner_name += " (You)"
            
            rank_item = QTableWidgetItem(f"#{row + 1}")
            rank_item.setTextAlignment(Qt.AlignCenter)
            if row == 0: rank_item.setForeground(QBrush(QColor("#D4AF37")))
            self.ledger_table.setItem(row, 0, rank_item)
            
            name = h_dict['full_name']
            if h_dict['username'].endswith('Bot'): name += " 🤖"
            if current_user and h_dict['user_id'] == current_user.user_id: name += " (You)"
            
            name_item = QTableWidgetItem(name)
            if h_dict['user_id'] == comp['owner_id']: 
                name_item.setText(name + " 👑")
                name_item.setForeground(QBrush(QColor("#D4AF37")))
            self.ledger_table.setItem(row, 1, name_item)
            
            shares_item = QTableWidgetItem(Formatter.format_number(h_dict['quantity']))
            shares_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.ledger_table.setItem(row, 2, shares_item)
            
            total_issued = h_dict.get('total_issued_shares') or 1
            percent = (h_dict['quantity'] / total_issued) * 100 if total_issued > 0 else 0
            pct_item = QTableWidgetItem(f"{percent:.2f}%")
            pct_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.ledger_table.setItem(row, 3, pct_item)
            
        self.detail_owner.setText(f"👑 Current Owner: {owner_name}")
        
        # Show the details page!
        self.right_stack.setCurrentIndex(1)