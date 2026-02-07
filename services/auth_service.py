"""
Authentication Service - Handles user authentication and session management
"""
from models.user import User
from datetime import datetime


class AuthService:
    """Authentication service with session management"""
    
    def __init__(self):
        self.current_user = None
        self.session_start_time = None
    
    def register(self, username, password, email, full_name):
        """
        Register a new user
        
        Args:
            username: Unique username
            password: User password (will be hashed)
            email: User email
            full_name: User's full name
            
        Returns:
            User object if successful
            
        Raises:
            ValueError: If validation fails or username exists
        """
        try:
            user = User.register(username, password, email, full_name)
            return user
        except ValueError as e:
            raise e
        except Exception as e:
            raise Exception(f"Registration failed: {str(e)}")
    
    def login(self, username, password):
        """
        Authenticate user and create session
        
        Args:
            username: Username
            password: Password
            
        Returns:
            User object if successful
            
        Raises:
            ValueError: If credentials are invalid
        """
        try:
            user = User.login(username, password)
            self.current_user = user
            self.session_start_time = datetime.now()
            return user
        except ValueError as e:
            raise e
        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")
    
    def logout(self):
        """Logout current user and clear session"""
        self.current_user = None
        self.session_start_time = None
    
    def is_authenticated(self):
        """Check if user is authenticated"""
        return self.current_user is not None
    
    def get_current_user(self):
        """Get current authenticated user"""
        if self.current_user:
            # Refresh user data
            self.current_user.refresh()
        return self.current_user
    
    def require_authentication(self):
        """
        Require authentication, raise error if not authenticated
        
        Raises:
            Exception: If user is not authenticated
        """
        if not self.is_authenticated():
            raise Exception("Authentication required. Please login.")
    
    def get_session_duration(self):
        """Get current session duration in seconds"""
        if not self.session_start_time:
            return 0
        
        duration = datetime.now() - self.session_start_time
        return duration.total_seconds()
    
    def change_password(self, old_password, new_password):
        """
        Change user password
        
        Args:
            old_password: Current password
            new_password: New password
            
        Raises:
            Exception: If not authenticated or old password is wrong
        """
        self.require_authentication()
        
        # Verify old password
        if not User.verify_password(old_password, self.current_user.password_hash):
            raise ValueError("Current password is incorrect.")
        
        # Validate new password
        from utils.validators import Validator
        if not Validator.validate_password(new_password):
            raise ValueError("New password must be at least 6 characters long.")
        
        # Update password
        new_hash = User.hash_password(new_password)
        from database.db_manager import db
        db.execute_update(
            "UPDATE users SET password_hash = ? WHERE user_id = ?",
            (new_hash, self.current_user.user_id)
        )
        
        return True
    
    def get_user_profile(self):
        """Get current user's profile information"""
        self.require_authentication()
        return self.current_user.to_dict()
    
    def update_profile(self, email=None, full_name=None):
        """
        Update user profile
        
        Args:
            email: New email (optional)
            full_name: New full name (optional)
        """
        self.require_authentication()
        
        from database.db_manager import db
        from utils.validators import Validator
        
        if email:
            if not Validator.validate_email(email):
                raise ValueError("Invalid email format.")
            db.execute_update(
                "UPDATE users SET email = ? WHERE user_id = ?",
                (email, self.current_user.user_id)
            )
            self.current_user.email = email
        
        if full_name:
            if len(full_name.strip()) < 2:
                raise ValueError("Full name must be at least 2 characters.")
            db.execute_update(
                "UPDATE users SET full_name = ? WHERE user_id = ?",
                (full_name.strip(), self.current_user.user_id)
            )
            self.current_user.full_name = full_name.strip()
        
        return True
    
    def validate_session(self):
        """Validate current session"""
        if not self.is_authenticated():
            return False
        
        # Check if user still exists
        from database.db_manager import db
        user_data = db.get_user_by_id(self.current_user.user_id)
        if not user_data:
            self.logout()
            return False
        
        return True


# Global auth service instance
auth_service = AuthService()
