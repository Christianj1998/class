import bcrypt
import time
from dataclasses import dataclass
from typing import Optional, Dict
from loguru import logger
from datetime import datetime, timedelta

@dataclass
class User:
    id: int
    username: str
    email: str
    role: str  # 'admin', 'operator', 'viewer'
    created_at: float
    last_login: Optional[float] = None
    is_active: bool = True

@dataclass
class Session:
    user: User
    login_time: float
    last_activity: float
    
    def is_expired(self, timeout_minutes: int = 60) -> bool:
        """Check if session has expired"""
        current_time = time.time()
        elapsed = (current_time - self.last_activity) / 60
        return elapsed > timeout_minutes
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()

class AuthManager:
    def __init__(self, database):
        self.database = database
        self.current_session: Optional[Session] = None
        self.session_timeout = 60  # minutes
        self.max_login_attempts = 5
        self.lockout_duration = 300  # 5 minutes in seconds
        self.failed_attempts: Dict[str, list] = {}
        
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    def is_locked_out(self, username: str) -> bool:
        """Check if user is temporarily locked out"""
        if username not in self.failed_attempts:
            return False
        
        attempts = self.failed_attempts[username]
        if len(attempts) < self.max_login_attempts:
            return False
        
        # Check if lockout period has expired
        last_attempt = attempts[-1]
        if time.time() - last_attempt > self.lockout_duration:
            # Reset attempts
            self.failed_attempts[username] = []
            return False
        
        return True
    
    def record_failed_attempt(self, username: str):
        """Record a failed login attempt"""
        if username not in self.failed_attempts:
            self.failed_attempts[username] = []
        self.failed_attempts[username].append(time.time())
        
        # Keep only recent attempts
        cutoff = time.time() - self.lockout_duration
        self.failed_attempts[username] = [
            t for t in self.failed_attempts[username] if t > cutoff
        ]
    
    def clear_failed_attempts(self, username: str):
        """Clear failed login attempts for user"""
        if username in self.failed_attempts:
            self.failed_attempts[username] = []
    
    def login(self, username: str, password: str) -> tuple[bool, str, Optional[User]]:
        """
        Authenticate user
        Returns: (success, message, user)
        """
        try:
            # Check if locked out
            if self.is_locked_out(username):
                remaining = self.lockout_duration - (time.time() - self.failed_attempts[username][-1])
                return False, f"Account locked. Try again in {int(remaining/60)} minutes", None
            
            # Get user from database
            user_data = self.database.get_user_by_username(username)
            if not user_data:
                self.record_failed_attempt(username)
                return False, "Invalid username or password", None
            
            # Check if user is active
            if not user_data['is_active']:
                return False, "Account is disabled", None
            
            # Verify password
            if not self.verify_password(password, user_data['password_hash']):
                self.record_failed_attempt(username)
                attempts_left = self.max_login_attempts - len(self.failed_attempts.get(username, []))
                return False, f"Invalid username or password. {attempts_left} attempts remaining", None
            
            # Clear failed attempts on successful login
            self.clear_failed_attempts(username)
            
            # Create user object
            user = User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                role=user_data['role'],
                created_at=user_data['created_at'],
                last_login=user_data['last_login'],
                is_active=user_data['is_active']
            )
            
            # Create session
            self.current_session = Session(
                user=user,
                login_time=time.time(),
                last_activity=time.time()
            )
            
            # Update last login in database
            self.database.update_last_login(user.id)
            
            # Log successful login
            logger.info(f"User {username} logged in successfully")
            
            return True, "Login successful", user
            
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False, "An error occurred during login", None
    
    def logout(self):
        """Logout current user"""
        if self.current_session:
            logger.info(f"User {self.current_session.user.username} logged out")
            self.current_session = None
    
    def is_authenticated(self) -> bool:
        """Check if there's an active session"""
        if not self.current_session:
            return False
        
        if self.current_session.is_expired(self.session_timeout):
            logger.warning(f"Session expired for user {self.current_session.user.username}")
            self.current_session = None
            return False
        
        self.current_session.update_activity()
        return True
    
    def get_current_user(self) -> Optional[User]:
        """Get currently logged in user"""
        if self.is_authenticated():
            return self.current_session.user
        return None
    
    def has_permission(self, required_role: str) -> bool:
        """
        Check if current user has required permission
        Role hierarchy: admin > operator > viewer
        """
        if not self.is_authenticated():
            return False
        
        user = self.current_session.user
        role_hierarchy = {'viewer': 1, 'operator': 2, 'admin': 3}
        
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    def change_password(self, old_password: str, new_password: str) -> tuple[bool, str]:
        """Change password for current user"""
        if not self.is_authenticated():
            return False, "Not authenticated"
        
        user = self.current_session.user
        
        # Verify old password
        user_data = self.database.get_user_by_username(user.username)
        if not self.verify_password(old_password, user_data['password_hash']):
            return False, "Current password is incorrect"
        
        # Validate new password
        if len(new_password) < 8:
            return False, "New password must be at least 8 characters"
        
        # Update password
        new_hash = self.hash_password(new_password)
        if self.database.update_user_password(user.id, new_hash):
            logger.info(f"Password changed for user {user.username}")
            return True, "Password changed successfully"
        
        return False, "Failed to update password"