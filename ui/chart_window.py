"""
Chart Window - Display price history graph
"""
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QHBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime
from trading.market_engine import market_engine

class ChartWindow(QDialog):
    """Popup window to show stock price history"""
    
    def __init__(self, company, parent=None):
        super().__init__(parent)
        self.company = company # Store company object
        self.setWindowTitle(f"Price History - {company.company_name}")
        self.resize(700, 550) 
        self.price_history = []
        self.current_minutes = 60 # Default 1 Hour
        
        self.init_ui()
        self.reload_data()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # --- Timeframe Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        timeframes = [("5 Min", 5), ("15 Min", 15), ("30 Min", 30), ("1 Hour", 60), ("24 Hours", 1440)]
        
        for label, mins in timeframes:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton { background-color: #34495E; color: white; border: none; padding: 6px; font-weight: bold; border-radius: 4px; }
                QPushButton:hover { background-color: #2C3E50; }
                QPushButton:pressed { background-color: #3498DB; }
            """)
            btn.clicked.connect(lambda checked, m=mins: self.set_timeframe(m))
            btn_layout.addWidget(btn)
            
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Chart Canvas
        self.figure = Figure(figsize=(6, 4), dpi=100, facecolor='#2D2D2D')
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton { background-color: #444; color: white; border: none; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #555; }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)

    def set_timeframe(self, minutes):
        """Update timeframe and reload"""
        self.current_minutes = minutes
        self.reload_data()

    def reload_data(self):
        """Fetch fresh data from engine"""
        self.price_history = market_engine.get_price_history(self.company.company_id, minutes=self.current_minutes)
        self.plot_graph()

    def plot_graph(self):
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#1E1E1E')
        ax.clear()
        
        if not self.price_history:
            ax.text(0.5, 0.5, 'No Data Available', 
                   horizontalalignment='center', verticalalignment='center', 
                   color='white')
            self.canvas.draw()
            return

        # 1. Parse Strings to Datetime Objects
        dates = []
        prices = [entry['price'] for entry in self.price_history]
        
        for entry in self.price_history:
            ts = entry['timestamp']
            if isinstance(ts, str):
                try:
                    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    try:
                        dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        dt = datetime.now()
                dates.append(dt)
            else:
                dates.append(ts)

        # 2. Plot
        line_color = '#2ECC71' if prices[-1] >= prices[0] else '#E74C3C'
        
        ax.plot(dates, prices, color=line_color, linewidth=2)
        ax.fill_between(dates, prices, min(prices) * 0.99, color=line_color, alpha=0.15)

        # 3. Styling
        ax.set_title(f"Price Trend (Last {self.current_minutes} Mins)", color='white', pad=10)
        ax.set_ylabel("Price (₹)", color='#AAA')
        ax.grid(True, linestyle=':', alpha=0.2, color='white')
        ax.tick_params(axis='x', colors='#AAA')
        ax.tick_params(axis='y', colors='#AAA')
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#444')
        ax.spines['left'].set_color('#444')

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        self.figure.autofmt_xdate()
        self.figure.tight_layout()
        self.canvas.draw()