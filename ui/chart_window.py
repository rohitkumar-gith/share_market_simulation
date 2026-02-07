"""
Chart Window - Display price history graph
"""
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates

class ChartWindow(QDialog):
    """Popup window to show stock price history"""
    
    def __init__(self, company_name, price_history, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Price History - {company_name}")
        self.resize(600, 400)
        self.price_history = price_history
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.plot_graph()
        layout.addWidget(self.canvas)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        self.setLayout(layout)

    def plot_graph(self):
        ax = self.figure.add_subplot(111)
        ax.clear()
        
        if not self.price_history:
            ax.text(0.5, 0.5, 'No Data Available', horizontalalignment='center', verticalalignment='center')
            self.canvas.draw()
            return

        dates = [entry['timestamp'] for entry in self.price_history]
        prices = [entry['price'] for entry in self.price_history]
        
        ax.plot(dates, prices, color='#3498DB', linewidth=2, marker='o', markersize=3)
        ax.set_title("Price Trend (Last 24h)")
        ax.set_ylabel("Price (₹)")
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        self.figure.autofmt_xdate()
        self.canvas.draw()