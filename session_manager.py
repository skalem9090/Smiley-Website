"""
Session Manager Component

This module manages user session lifecycle with configurable inactivity timeouts.
"""

from typing import Optional
from flask import Flask, session, request
from flask_login import current_user, logout_user
from datetime import datetime, timezone, timedelta
from security_config import SessionConfig


class SessionManager:
    """Manages user session lifecycle and timeouts"""
    
    def __init__(self, app: Flask, config: SessionConfig):
        """
        Initialize session manager.
        
        Args:
            app: Flask application instance
            config: SessionConfig instance with timeout settings
        """
        self.app = app
        self.timeout_minutes = config.timeout
        
        # Register before_request handler
        app.before_request(self.check_session_timeout)
    
    def create_session(self, user, sess=None) -> None:
        """
        Create a new session for user.
        
        Args:
            user: User model instance
            sess: Session dict (for testing), or None to use Flask session
        """
        now = datetime.now(timezone.utc)
        session_dict = sess if sess is not None else session
        session_dict['user_id'] = user.id
        session_dict['created_at'] = now.isoformat()
        session_dict['last_activity'] = now.isoformat()
        if sess is None:
            session.permanent = True
    
    def update_activity(self) -> None:
        """Update last activity timestamp"""
        if current_user.is_authenticated:
            session['last_activity'] = datetime.now(timezone.utc).isoformat()
    
    def is_expired(self, sess=None) -> bool:
        """
        Check if current session has expired.
        
        Args:
            sess: Session dict (for testing), or None to use Flask session
        
        Returns:
            True if session has expired, False otherwise
        """
        # For testing, allow passing session dict
        if sess is not None:
            last_activity_str = sess.get('last_activity')
        else:
            if not current_user or not current_user.is_authenticated:
                return False
            last_activity_str = session.get('last_activity')
        
        if last_activity_str is None:
            return True
        
        try:
            last_activity = datetime.fromisoformat(last_activity_str)
            # Ensure timezone-aware
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            elapsed = (now - last_activity).total_seconds() / 60  # minutes
            
            return elapsed > self.timeout_minutes
        except (ValueError, TypeError):
            return True
    
    def invalidate_session(self, sess=None) -> None:
        """
        Invalidate current session
        
        Args:
            sess: Session dict (for testing), or None to use Flask session
        """
        if sess is not None:
            sess.clear()
        else:
            session.clear()
            if current_user and current_user.is_authenticated:
                logout_user()
    
    def get_remaining_time(self, sess=None) -> Optional[int]:
        """
        Get remaining session time in minutes.
        
        Args:
            sess: Session dict (for testing), or None to use Flask session
        
        Returns:
            Remaining time in minutes, or None if session is invalid
        """
        # For testing, allow passing session dict
        if sess is not None:
            last_activity_str = sess.get('last_activity')
        else:
            if not current_user or not current_user.is_authenticated:
                return None
            last_activity_str = session.get('last_activity')
        
        if last_activity_str is None:
            return None
        
        try:
            last_activity = datetime.fromisoformat(last_activity_str)
            # Ensure timezone-aware
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            elapsed = (now - last_activity).total_seconds() / 60  # minutes
            remaining = self.timeout_minutes - elapsed
            
            return max(0, int(remaining))
        except (ValueError, TypeError):
            return None
    
    def check_session_timeout(self) -> None:
        """
        Check and enforce session timeout on each request.
        This is called automatically via before_request handler.
        """
        # Skip for static files and non-authenticated requests
        if request.endpoint and request.endpoint.startswith('static'):
            return
        
        if not current_user.is_authenticated:
            return
        
        if self.is_expired():
            self.invalidate_session()
            # Note: In a real application, you would redirect to login page here
            # with a flash message about session expiration
        else:
            self.update_activity()
