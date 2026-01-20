"""
Account Lockout Manager Component

This module manages account lockout after repeated failed login attempts
to prevent credential stuffing attacks.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from flask_sqlalchemy import SQLAlchemy
from models import User
from security_config import LockoutConfig


class AccountLockoutManager:
    """Manages account lockout after failed login attempts"""
    
    def __init__(self, db: SQLAlchemy, config: LockoutConfig = None):
        """
        Initialize account lockout manager.
        
        Args:
            db: SQLAlchemy database instance
            config: LockoutConfig instance, defaults to loading from environment
        """
        self.db = db
        
        if config is None:
            config = LockoutConfig.from_env()
        
        self.threshold = config.threshold
        self.duration_minutes = config.duration
    
    def record_failed_attempt(self, user: User, ip_address: str = None) -> None:
        """
        Record a failed login attempt and lock account if threshold exceeded.
        
        Args:
            user: User model instance
            ip_address: Optional IP address of the failed attempt
        """
        # Increment failed attempt counter
        user.failed_login_attempts += 1
        
        # Check if threshold exceeded
        if user.failed_login_attempts >= self.threshold:
            # Lock the account
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=self.duration_minutes)
        
        self.db.session.commit()
    
    def record_successful_login(self, user: User) -> None:
        """
        Reset failed attempt counter on successful login.
        
        Args:
            user: User model instance
        """
        user.reset_failed_attempts()
        user.last_login_at = datetime.now(timezone.utc)
        self.db.session.commit()
    
    def is_locked(self, user: User) -> bool:
        """
        Check if account is currently locked.
        
        Args:
            user: User model instance
            
        Returns:
            True if account is locked, False otherwise
        """
        return user.is_locked()
    
    def get_unlock_time(self, user: User) -> Optional[datetime]:
        """
        Get the time when account will be unlocked.
        
        Args:
            user: User model instance
            
        Returns:
            DateTime when account will unlock, or None if not locked
        """
        if user.locked_until is None:
            return None
        
        # Ensure both datetimes are timezone-aware for comparison
        now = datetime.now(timezone.utc)
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            # If locked_until is naive, assume it's UTC
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        
        # If lock has expired, return None
        if now >= locked_until:
            return None
        
        return locked_until
    
    def get_remaining_lockout_time(self, user: User) -> Optional[int]:
        """
        Get remaining lockout time in minutes.
        
        Args:
            user: User model instance
            
        Returns:
            Remaining minutes until unlock, or None if not locked
        """
        unlock_time = self.get_unlock_time(user)
        if unlock_time is None:
            return None
        
        remaining = unlock_time - datetime.now(timezone.utc)
        return max(0, int(remaining.total_seconds() / 60))
    
    def unlock_account(self, user: User) -> None:
        """
        Manually unlock an account.
        
        Args:
            user: User model instance
        """
        user.reset_failed_attempts()
        self.db.session.commit()
    
    def get_failed_attempts(self, user: User) -> int:
        """
        Get number of failed login attempts for user.
        
        Args:
            user: User model instance
            
        Returns:
            Number of failed attempts
        """
        return user.failed_login_attempts
    
    def get_lockout_message(self, user: User) -> str:
        """
        Get user-friendly lockout message.
        
        Args:
            user: User model instance
            
        Returns:
            Lockout message string
        """
        if not self.is_locked(user):
            return ""
        
        remaining_minutes = self.get_remaining_lockout_time(user)
        if remaining_minutes is None or remaining_minutes == 0:
            return "Account locked. Please try again."
        
        return f"Account locked due to multiple failed login attempts. Try again in {remaining_minutes} minutes."
