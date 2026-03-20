"""
User Dashboard - Billionaire's Row, Global Leaderboard, and Market Overview
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QBrush
from services.auth_service import auth_service
from services.trading_service import trading_service
from database.db_manager import db
from utils.formatters import Formatter
import config

class UserDashboard(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # --- HEADER ---
        self.welcome_label = QLabel("Welcome back!")
        self.welcome_label.setFont(QFont('Arial', 24, QFont.Bold))
        self.welcome_label.setStyleSheet(f"color: {config.COLOR_ACCENT};")
        layout.addWidget(self.welcome_label)
        
        # --- TOP: PERSONAL SUMMARY CARDS ---
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        
        self.net_worth_card = self.create_summary_card("True Net Worth", "₹0.00", "#D4AF37") # Gold
        self.wallet_card = self.create_summary_card("Liquid Cash (Wallet)", "₹0.00", "#27AE60") # Green
        self.assets_card = self.create_summary_card("Total Assets (Stocks & Real Estate)", "₹0.00", "#8E44AD") # Purple
        self.debt_card = self.create_summary_card("Total Debt (Bank & Corp)", "₹0.00", "#C0392B") # Red
        
        cards_layout.addWidget(self.net_worth_card)
        cards_layout.addWidget(self.wallet_card)
        cards_layout.addWidget(self.assets_card)
        cards_layout.addWidget(self.debt_card)
        
        layout.addLayout(cards_layout)
        
        # --- BOTTOM: SPLIT VIEW (LEADERBOARD & TRENDING) ---
        split_layout = QHBoxLayout()
        split_layout.setSpacing(20)
        
        # LEFT: Billionaire's Row
        leaderboard_layout = QVBoxLayout()
        leader_title = QLabel("🏆 Billionaire's Row (Global Leaderboard)")
        leader_title.setFont(QFont('Arial', 18, QFont.Bold))
        leaderboard_layout.addWidget(leader_title)
        
        self.leaderboard_table = QTableWidget()
        self.leaderboard_table.setColumnCount(4)
        self.leaderboard_table.setHorizontalHeaderLabels(["Rank", "Player / Bot", "Entity", "True Net Worth"])
        self.leaderboard_table.horizontalHeader().setStretchLastSection(True)
        self.leaderboard_table.setAlternatingRowColors(True)
        self.leaderboard_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.leaderboard_table.verticalHeader().setDefaultSectionSize(45)
        self.leaderboard_table.setStyleSheet("QTableWidget { background-color: #1E1E1E; border-radius: 8px; }")
        leaderboard_layout.addWidget(self.leaderboard_table)
        
        split_layout.addLayout(leaderboard_layout, 6) # 60% width
        
        # RIGHT: Market Overview (Tabbed)
        market_layout = QVBoxLayout()
        market_title = QLabel("📊 Market Overview")
        market_title.setFont(QFont('Arial', 18, QFont.Bold))
        market_layout.addWidget(market_title)
        
        self.market_tabs = QTabWidget()
        self.market_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 0; }}
            QTabBar::tab {{ background: #2C2C2C; color: white; padding: 10px 20px; font-weight: bold; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }}
            QTabBar::tab:selected {{ background: {config.COLOR_ACCENT}; }}
        """)
        
        # Right Tab 1: Top Companies by Price
        self.top_companies_table = QTableWidget()
        self.top_companies_table.setColumnCount(4)
        self.top_companies_table.setHorizontalHeaderLabels(["Rank", "Ticker", "Share Price", "Market Cap"])
        self.top_companies_table.horizontalHeader().setStretchLastSection(True)
        self.top_companies_table.setAlternatingRowColors(True)
        self.top_companies_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.top_companies_table.verticalHeader().setDefaultSectionSize(45)
        self.top_companies_table.setStyleSheet("QTableWidget { background-color: #1E1E1E; border-radius: 8px; }")
        self.market_tabs.addTab(self.top_companies_table, "💎 Highest Valued")
        
        # Right Tab 2: Wealthiest Corporations (Net Worth)
        self.wealthiest_corps_table = QTableWidget()
        self.wealthiest_corps_table.setColumnCount(4)
        self.wealthiest_corps_table.setHorizontalHeaderLabels(["Rank", "Ticker", "True Net Worth", "Physical Assets"])
        self.wealthiest_corps_table.horizontalHeader().setStretchLastSection(True)
        self.wealthiest_corps_table.setAlternatingRowColors(True)
        self.wealthiest_corps_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.wealthiest_corps_table.verticalHeader().setDefaultSectionSize(45)
        self.wealthiest_corps_table.setStyleSheet("QTableWidget { background-color: #1E1E1E; border-radius: 8px; }")
        self.market_tabs.addTab(self.wealthiest_corps_table, "🏦 Wealthiest Corps")
        
        # Right Tab 3: Trending by Volume
        self.trending_table = QTableWidget()
        self.trending_table.setColumnCount(4)
        self.trending_table.setHorizontalHeaderLabels(["Ticker", "Price", "Volume", "Trend"])
        self.trending_table.horizontalHeader().setStretchLastSection(True)
        self.trending_table.setAlternatingRowColors(True)
        self.trending_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.trending_table.verticalHeader().setDefaultSectionSize(45)
        self.trending_table.setStyleSheet("QTableWidget { background-color: #1E1E1E; border-radius: 8px; }")
        self.market_tabs.addTab(self.trending_table, "🔥 Trending Vol")
        
        market_layout.addWidget(self.market_tabs)
        
        split_layout.addLayout(market_layout, 4) # 40% width
        
        layout.addLayout(split_layout)
        
        self.setLayout(layout)
        self.refresh_data()
    
    def create_summary_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {color}; border-radius: 10px; }}")
        card.setFrameShape(QFrame.StyledPanel)
        
        layout = QVBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.9); font-size: 13px; font-weight: bold;")
        value_lbl = QLabel(value)
        value_lbl.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        value_lbl.setAlignment(Qt.AlignRight)
        
        layout.addWidget(title_lbl)
        layout.addWidget(value_lbl)
        card.setLayout(layout)
        
        if title == "True Net Worth": self.net_worth_val = value_lbl
        elif title == "Liquid Cash (Wallet)": self.wallet_val = value_lbl
        elif "Assets" in title: self.assets_val = value_lbl
        elif "Debt" in title: self.debt_val = value_lbl
            
        return card

    def calculate_global_wealth(self):
        """Calculates True Net Worth for every user and bot in the system"""
        users = db.execute_query("SELECT user_id, username, full_name, wallet_balance FROM users")
        leaderboard = []
        
        for u in users:
            uid = u['user_id']
            cash = u['wallet_balance']
            total_assets = 0.0
            total_debt = 0.0

            # 1. Stock Portfolio Value
            stocks = db.execute_query("""
                SELECT SUM(uh.quantity * c.share_price) as stock_val
                FROM user_holdings uh
                JOIN companies c ON uh.company_id = c.company_id
                WHERE uh.user_id = ?
            """, (uid,))
            if stocks and stocks[0]['stock_val']:
                total_assets += stocks[0]['stock_val']

            # 2. Luxury Assets Value
            assets = db.execute_query("SELECT SUM(acquired_price) as asset_val FROM owned_assets WHERE owner_id = ? AND owner_type = 'USER'", (uid,))
            if assets and assets[0]['asset_val']:
                total_assets += assets[0]['asset_val']
                
            # 3. Commodity Vault Value (Gold, Silver, etc)
            vault = db.execute_query("""
                SELECT SUM(uc.quantity * c.current_price) as vault_val 
                FROM user_commodities uc 
                JOIN commodities c ON uc.commodity_id = c.id 
                WHERE uc.user_id = ?
            """, (uid,))
            if vault and vault[0]['vault_val']:
                total_assets += vault[0]['vault_val']

            # 4. Bank Debt
            loans = db.execute_query("SELECT SUM(remaining_balance) as debt FROM loans WHERE user_id = ? AND status = 'active'", (uid,))
            if loans and loans[0]['debt']:
                total_debt += loans[0]['debt']

            # 5. Corporate Debt
            corp_loans = db.execute_query("SELECT SUM(remaining_balance) as corp_debt FROM company_user_loans WHERE borrower_user_id = ? AND status = 'ACTIVE'", (uid,))
            if corp_loans and corp_loans[0]['corp_debt']:
                total_debt += corp_loans[0]['corp_debt']

            true_net_worth = cash + total_assets - total_debt
            is_bot = u['username'].endswith('Bot')

            leaderboard.append({
                'user_id': uid,
                'name': u['full_name'],
                'type': "🤖 AI Bot" if is_bot else "👤 Player",
                'is_bot': is_bot,
                'cash': cash,
                'assets': total_assets,
                'debt': total_debt,
                'net_worth': true_net_worth
            })

        # Sort by richest first
        leaderboard.sort(key=lambda x: x['net_worth'], reverse=True)
        return leaderboard

    def refresh_data(self):
        current_user = auth_service.get_current_user()
        if not current_user: return
            
        self.welcome_label.setText(f"Welcome back, {current_user.full_name}!")
        
        # --- 1. PROCESS GLOBAL LEADERBOARD & PERSONAL STATS ---
        leaderboard = self.calculate_global_wealth()
        
        # Update Personal Cards based on the global scan
        for data in leaderboard:
            if data['user_id'] == current_user.user_id:
                self.net_worth_val.setText(Formatter.format_currency(data['net_worth']))
                self.wallet_val.setText(Formatter.format_currency(data['cash']))
                self.assets_val.setText(Formatter.format_currency(data['assets']))
                self.debt_val.setText(Formatter.format_currency(data['debt']))
                break
                
        # Populate Leaderboard Table
        self.leaderboard_table.setRowCount(len(leaderboard))
        for row, p in enumerate(leaderboard):
            if row == 0: rank_str = "🥇 #1"
            elif row == 1: rank_str = "🥈 #2"
            elif row == 2: rank_str = "🥉 #3"
            else: rank_str = f"#{row + 1}"
            
            rank_item = QTableWidgetItem(rank_str)
            rank_item.setFont(QFont('Arial', 12, QFont.Bold))
            rank_item.setTextAlignment(Qt.AlignCenter)
            self.leaderboard_table.setItem(row, 0, rank_item)
            
            name_item = QTableWidgetItem(p['name'])
            name_item.setFont(QFont('Arial', 11, QFont.Bold))
            if p['user_id'] == current_user.user_id:
                name_item.setForeground(QBrush(QColor(Qt.cyan)))
                name_item.setText(f"{p['name']} (You)")
            self.leaderboard_table.setItem(row, 1, name_item)
            
            type_item = QTableWidgetItem(p['type'])
            if p['is_bot']: type_item.setForeground(QBrush(QColor(Qt.lightGray)))
            self.leaderboard_table.setItem(row, 2, type_item)
            
            nw_item = QTableWidgetItem(Formatter.format_currency(p['net_worth']))
            nw_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            nw_item.setFont(QFont('Arial', 11, QFont.Bold))
            if p['net_worth'] >= 0:
                nw_item.setForeground(QBrush(QColor(Qt.green)))
            else:
                nw_item.setForeground(QBrush(QColor(Qt.red)))
            self.leaderboard_table.setItem(row, 3, nw_item)
            
        self.leaderboard_table.resizeColumnsToContents()
        
        # --- 2. PROCESS TOP COMPANIES BY PRICE ---
        top_companies = db.execute_query("SELECT ticker_symbol, share_price, total_shares FROM companies ORDER BY share_price DESC LIMIT 10")
        if top_companies:
            self.top_companies_table.setRowCount(len(top_companies))
            for row, comp in enumerate(top_companies):
                # Rank
                rank_item = QTableWidgetItem(f"#{row + 1}")
                rank_item.setFont(QFont('Arial', 11, QFont.Bold))
                rank_item.setTextAlignment(Qt.AlignCenter)
                if row == 0: rank_item.setForeground(QBrush(QColor("#D4AF37")))
                elif row == 1: rank_item.setForeground(QBrush(QColor("#C0C0C0")))
                elif row == 2: rank_item.setForeground(QBrush(QColor("#CD7F32")))
                self.top_companies_table.setItem(row, 0, rank_item)
                
                # Ticker
                t_item = QTableWidgetItem(comp['ticker_symbol'])
                t_item.setFont(QFont('Arial', 11, QFont.Bold))
                self.top_companies_table.setItem(row, 1, t_item)
                
                # Price
                price_item = QTableWidgetItem(Formatter.format_currency(comp['share_price']))
                price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                price_item.setForeground(QBrush(QColor(Qt.green)))
                self.top_companies_table.setItem(row, 2, price_item)
                
                # Market Cap
                mcap = comp['share_price'] * comp['total_shares']
                mcap_item = QTableWidgetItem(Formatter.format_currency(mcap))
                mcap_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.top_companies_table.setItem(row, 3, mcap_item)
                
            self.top_companies_table.resizeColumnsToContents()

        # --- 3. PROCESS WEALTHIEST CORPORATIONS (TRUE NET WORTH) ---
        corps_query = """
            SELECT c.ticker_symbol, c.company_name, c.company_wallet,
                   (SELECT COALESCE(SUM(acquired_price), 0) FROM owned_assets WHERE owner_id = c.company_id AND owner_type = 'COMPANY') as asset_value,
                   (SELECT COALESCE(SUM(remaining_balance), 0) FROM inter_company_loans WHERE borrower_company_id = c.company_id AND status = 'ACTIVE') as debt
            FROM companies c
        """
        try:
            corps_data = db.execute_query(corps_query) or []
            
            # FIX: Convert to standard dictionaries before doing math!
            parsed_corps = []
            for c in corps_data:
                comp_dict = dict(c)
                comp_dict['net_worth'] = comp_dict['company_wallet'] + comp_dict['asset_value'] - comp_dict['debt']
                parsed_corps.append(comp_dict)
                
            # Sort by richest first using the new dictionaries
            parsed_corps.sort(key=lambda x: x['net_worth'], reverse=True)
            
            self.wealthiest_corps_table.setRowCount(min(10, len(parsed_corps)))
            for row in range(min(10, len(parsed_corps))):
                comp = parsed_corps[row]
                
                rank_item = QTableWidgetItem(f"#{row + 1}")
                rank_item.setFont(QFont('Arial', 11, QFont.Bold))
                rank_item.setTextAlignment(Qt.AlignCenter)
                if row == 0: rank_item.setForeground(QBrush(QColor("#D4AF37")))
                elif row == 1: rank_item.setForeground(QBrush(QColor("#C0C0C0")))
                elif row == 2: rank_item.setForeground(QBrush(QColor("#CD7F32")))
                self.wealthiest_corps_table.setItem(row, 0, rank_item)
                
                t_item = QTableWidgetItem(comp['ticker_symbol'])
                t_item.setFont(QFont('Arial', 11, QFont.Bold))
                self.wealthiest_corps_table.setItem(row, 1, t_item)
                
                nw_item = QTableWidgetItem(Formatter.format_currency(comp['net_worth']))
                nw_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                nw_item.setFont(QFont('Arial', 10, QFont.Bold))
                if comp['net_worth'] >= 0:
                    nw_item.setForeground(QBrush(QColor(Qt.green)))
                else:
                    nw_item.setForeground(QBrush(QColor(Qt.red)))
                self.wealthiest_corps_table.setItem(row, 2, nw_item)
                
                asset_item = QTableWidgetItem(Formatter.format_currency(comp['asset_value']))
                asset_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.wealthiest_corps_table.setItem(row, 3, asset_item)
                
            self.wealthiest_corps_table.resizeColumnsToContents()
        except Exception as e:
            print(f"Error loading wealthiest corps: {e}")

        # --- 4. PROCESS TRENDING STOCKS ---
        trending = trading_service.get_trending_stocks(limit=10)
        self.trending_table.setRowCount(len(trending))
        
        for row, item in enumerate(trending):
            company = item['company']
            
            if isinstance(company, dict):
                c_ticker = company['ticker_symbol']
                c_price = company['share_price']
            else:
                c_ticker = company.ticker_symbol
                c_price = company.share_price

            volume = item['volume']
            
            t_item = QTableWidgetItem(c_ticker)
            t_item.setFont(QFont('Arial', 11, QFont.Bold))
            self.trending_table.setItem(row, 0, t_item)
            
            price_item = QTableWidgetItem(Formatter.format_currency(c_price))
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.trending_table.setItem(row, 1, price_item)
            
            vol_item = QTableWidgetItem(Formatter.format_number(volume))
            vol_item.setTextAlignment(Qt.AlignCenter)
            self.trending_table.setItem(row, 2, vol_item)
            
            if volume > 5000:
                trend_str = "🔥 Hot"
                trend_color = Qt.red
            elif volume > 1000:
                trend_str = "📈 Active"
                trend_color = Qt.green
            else:
                trend_str = "Stable"
                trend_color = Qt.lightGray
                
            trend_item = QTableWidgetItem(trend_str)
            trend_item.setForeground(QBrush(QColor(trend_color)))
            self.trending_table.setItem(row, 3, trend_item)