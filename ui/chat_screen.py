"""
Chat Screen - Global User Chat
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from services.auth_service import auth_service
from services.chat_service import chat_service
import config

class ChatScreen(QWidget):
    """Global chat screen"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_timer()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("Global Trader Chat")
        header.setFont(QFont('Arial', 20, QFont.Bold))
        header.setStyleSheet(f"color: {config.COLOR_ACCENT}; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Message Display Area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        # Removed hardcoded style - uses global theme now
        layout.addWidget(self.chat_display)
        
        # Input Area
        input_layout = QHBoxLayout()
        
        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Type a message...")
        self.msg_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.msg_input)
        
        send_btn = QPushButton("Send")
        send_btn.setStyleSheet(f"background-color: {config.COLOR_SECONDARY}; color: white; padding: 10px; font-weight: bold;")
        send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(send_btn)
        
        layout.addLayout(input_layout)
        self.setLayout(layout)
        
    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_messages)
        self.timer.start(2000)
        self.refresh_messages()
        
    def refresh_messages(self):
        messages = chat_service.get_recent_messages()
        
        html = ""
        for msg in messages:
            time_str = msg['created_at'].strftime("%H:%M")
            user_color = "#5DADE2" 
            
            current_user = auth_service.get_current_user()
            if current_user and msg['username'] == current_user.username:
                user_color = config.COLOR_SUCCESS
                
            # Use distinct colors for username/message to stand out on dark bg
            html += f"<p style='margin: 4px 0;'><span style='color:#7f8c8d; font-size:11px;'>[{time_str}]</span> "
            html += f"<span style='color:{user_color}; font-weight:bold;'>{msg['username']}:</span> "
            html += f"<span style='color:#E0E0E0;'>{msg['message']}</span></p>"
            
        self.chat_display.setHtml(html)
        sb = self.chat_display.verticalScrollBar()
        sb.setValue(sb.maximum())

    def send_message(self):
        text = self.msg_input.text().strip()
        if not text: return
        
        user = auth_service.get_current_user()
        if user:
            chat_service.send_message(user.user_id, text)
            self.msg_input.clear()
            self.refresh_messages()