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
        layout.addWidget(header)
        
        # Message Display Area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.chat_display)
        
        # Input Area
        input_layout = QHBoxLayout()
        
        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Type a message...")
        self.msg_input.returnPressed.connect(self.send_message)
        self.msg_input.setStyleSheet("padding: 10px; border-radius: 5px; border: 1px solid #bdc3c7;")
        input_layout.addWidget(self.msg_input)
        
        send_btn = QPushButton("Send")
        send_btn.setStyleSheet(f"background-color: {config.COLOR_SECONDARY}; color: white; padding: 10px; font-weight: bold;")
        send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(send_btn)
        
        layout.addLayout(input_layout)
        self.setLayout(layout)
        
    def setup_timer(self):
        # Poll for new messages every 2 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_messages)
        self.timer.start(2000)
        self.refresh_messages()
        
    def refresh_messages(self):
        messages = chat_service.get_recent_messages()
        
        # Simple HTML formatting
        html = ""
        for msg in messages:
            time_str = msg['created_at'].strftime("%H:%M")
            user_color = config.COLOR_PRIMARY
            
            # Highlight own messages
            current_user = auth_service.get_current_user()
            if current_user and msg['username'] == current_user.username:
                user_color = config.COLOR_SUCCESS
                
            html += f"<p><span style='color:#95a5a6; font-size:10px;'>[{time_str}]</span> "
            html += f"<span style='color:{user_color}; font-weight:bold;'>{msg['username']}:</span> "
            html += f"{msg['message']}</p>"
            
        self.chat_display.setHtml(html)
        # Scroll to bottom
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