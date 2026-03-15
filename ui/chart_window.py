"""
Chart Window - Display price history graph
"""
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QHBoxLayout, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from trading.market_engine import market_engine

class ChartWindow(QDialog):
    """Popup window to show stock price history"""
    
    def __init__(self, company, parent=None):
        super().__init__(parent)
        self.company = company # Store company object
        self.setWindowTitle(f"Price History - {company.company_name}")
        self.resize(800, 600) # Slightly larger to fit indicators
        self.price_history = []
        self.current_minutes = 60 # Default 1 Hour
        self.chart_style = 'candle' # Default to new Candlestick view
        
        self.init_ui()
        self.reload_data()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # --- Top Controls ---
        top_layout = QHBoxLayout()
        
        # Timeframe Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        timeframes = [("5 Min", 5), ("15 Min", 15), ("30 Min", 30), ("1 Hour", 60), ("24 Hours", 1440)]
        
        for label, mins in timeframes:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton { background-color: #34495E; color: white; border: none; padding: 6px 12px; font-weight: bold; border-radius: 4px; }
                QPushButton:hover { background-color: #2C3E50; }
                QPushButton:pressed { background-color: #3498DB; }
            """)
            btn.clicked.connect(lambda checked, m=mins: self.set_timeframe(m))
            btn_layout.addWidget(btn)
            
        top_layout.addLayout(btn_layout)
        top_layout.addStretch()
        
        # Toggle Chart Type Button
        self.toggle_btn = QPushButton("🔄 Switch to Line Chart")
        self.toggle_btn.setStyleSheet("""
            QPushButton { background-color: #8E44AD; color: white; border: none; padding: 6px 12px; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background-color: #732D91; }
        """)
        self.toggle_btn.clicked.connect(self.toggle_chart_style)
        top_layout.addWidget(self.toggle_btn)
        
        layout.addLayout(top_layout)

        # Chart Canvas
        self.figure = Figure(figsize=(8, 5), dpi=100, facecolor='#121212')
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Bottom Close Button
        close_btn = QPushButton("Close Window")
        close_btn.setStyleSheet("""
            QPushButton { background-color: #444; color: white; border: none; padding: 10px; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background-color: #555; }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)

    def set_timeframe(self, minutes):
        """Update timeframe and reload"""
        self.current_minutes = minutes
        self.reload_data()
        
    def toggle_chart_style(self):
        """Toggle between Candlestick and Line charts"""
        if self.chart_style == 'candle':
            self.chart_style = 'line'
            self.toggle_btn.setText("🔄 Switch to Candlestick")
        else:
            self.chart_style = 'candle'
            self.toggle_btn.setText("🔄 Switch to Line Chart")
        self.plot_graph()

    def reload_data(self):
        """Fetch fresh data from engine"""
        self.price_history = market_engine.get_price_history(self.company.company_id, minutes=self.current_minutes)
        self.plot_graph()

    def plot_graph(self):
        self.figure.clear() # Wipe clean to prevent text overlapping
        
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#1E1E1E')
        
        if len(self.price_history) < 2:
            ax.text(0.5, 0.5, 'Not Enough Data to Display', 
                   horizontalalignment='center', verticalalignment='center', 
                   color='white', fontsize=12)
            self.canvas.draw()
            return

        # 1. Parse Strings to Datetime Objects
        dates = []
        prices = [entry['price'] for entry in self.price_history]
        
        for entry in self.price_history:
            ts = entry['timestamp']
            if isinstance(ts, str):
                try: dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    try: dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                    except ValueError: dt = datetime.now()
                dates.append(dt)
            else:
                dates.append(ts)

        # 2. Calculate Technical Indicators (Moving Averages matching the Bots)
        sma5 = [sum(prices[max(0, i-4):i+1]) / len(prices[max(0, i-4):i+1]) for i in range(len(prices))]
        sma10 = [sum(prices[max(0, i-9):i+1]) / len(prices[max(0, i-9):i+1]) for i in range(len(prices))]

        # 3. Plot Based on Selected Style
        if self.chart_style == 'candle':
            # --- ROBUST CANDLESTICK LOGIC ---
            
            # Determine bin size based on the selected timeframe
            if self.current_minutes <= 5: bin_sec = 10
            elif self.current_minutes <= 15: bin_sec = 30
            elif self.current_minutes <= 60: bin_sec = 60
            else: bin_sec = 1800 # 30 mins for 24 hours
            
            candle_width = (bin_sec / 86400) * 0.8 # Matplotlib dates are in fractions of a day
            
            # Group ticks into OHLC bins
            candles = {}
            for d, p in zip(dates, prices):
                timestamp = d.timestamp()
                binned_ts = timestamp - (timestamp % bin_sec)
                bin_date = datetime.fromtimestamp(binned_ts)
                
                if bin_date not in candles:
                    candles[bin_date] = {'open': p, 'high': p, 'low': p, 'close': p}
                else:
                    candles[bin_date]['high'] = max(candles[bin_date]['high'], p)
                    candles[bin_date]['low'] = min(candles[bin_date]['low'], p)
                    candles[bin_date]['close'] = p
            
            sorted_bins = sorted(candles.keys())
            candles_x = [mdates.date2num(b) for b in sorted_bins]
            opens = [candles[b]['open'] for b in sorted_bins]
            highs = [candles[b]['high'] for b in sorted_bins]
            lows = [candles[b]['low'] for b in sorted_bins]
            closes = [candles[b]['close'] for b in sorted_bins]

            # Draw the Candles
            for i in range(len(candles_x)):
                color = '#2ECC71' if closes[i] >= opens[i] else '#E74C3C' # Green / Red
                
                # Draw the wick (High to Low)
                ax.vlines(candles_x[i], lows[i], highs[i], color=color, linewidth=1.5, zorder=1)
                
                # Draw the body
                body_bottom = min(opens[i], closes[i])
                body_height = abs(closes[i] - opens[i])
                
                # FIX: If Open == Close, force a tiny height so the candle is still visible as a dash
                if body_height == 0:
                    body_height = opens[i] * 0.0005 
                    body_bottom -= body_height / 2
                
                ax.bar(candles_x[i], body_height, width=candle_width, bottom=body_bottom, color=color, zorder=2)
                
        else:
            # --- STANDARD LINE CHART ---
            line_color = '#2ECC71' if prices[-1] >= prices[0] else '#E74C3C'
            ax.plot(dates, prices, color=line_color, linewidth=2.5, label="Price", zorder=3)
            ax.fill_between(dates, prices, min(prices) * 0.99, color=line_color, alpha=0.15, zorder=1)

        # 4. Draw Technical Indicators (Behind the candles/lines)
        ax.plot(dates, sma5, color='#F39C12', linewidth=1.5, linestyle='--', label='Short SMA (5)', zorder=2)
        ax.plot(dates, sma10, color='#9B59B6', linewidth=1.5, linestyle='-.', label='Long SMA (10)', zorder=2)

        # 5. Styling & Legend
        ax.set_title(f"Market Analysis (Last {self.current_minutes} Mins)", color='white', pad=10, fontweight='bold')
        ax.set_ylabel("Price (₹)", color='#AAA')
        ax.grid(True, linestyle=':', alpha=0.15, color='white', zorder=0)
        ax.tick_params(axis='x', colors='#AAA')
        ax.tick_params(axis='y', colors='#AAA')
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#444')
        ax.spines['left'].set_color('#444')

        ax.legend(loc='upper left', facecolor='#1E1E1E', edgecolor='#444', labelcolor='white')
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        self.figure.autofmt_xdate()
        self.figure.tight_layout()
        self.canvas.draw()