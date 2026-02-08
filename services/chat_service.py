"""
Chat Service - Global Chat Logic
"""
from database.db_manager import db
from models.user import User

class ChatService:
    
    def send_message(self, user_id, message):
        """Post a message to global chat"""
        try:
            user = User.get_by_id(user_id)
            if not user:
                return {'success': False}
                
            query = "INSERT INTO chat_messages (user_id, username, message) VALUES (?, ?, ?)"
            db.execute_insert(query, (user_id, user.username, message))
            return {'success': True}
        except Exception as e:
            print(f"Chat error: {e}")
            return {'success': False}

    def get_recent_messages(self, limit=50):
        """Get last 50 messages"""
        query = """
            SELECT username, message, created_at 
            FROM chat_messages 
            ORDER BY created_at DESC LIMIT ?
        """
        messages = db.execute_query(query, (limit,))
        # Return in correct order (Oldest -> Newest) for the UI
        return messages[::-1]

chat_service = ChatService()