"""
Audit Logger Component

This module logs security-relevant events to the database for compliance
and investigation purposes.
"""

from typing import Optional, List
from flask_sqlalchemy import SQLAlchemy
from models import AuditLog, LoginAttempt
import json


class ActionType:
    """Constants for audit log action types"""
    POST_CREATE = "post_create"
    POST_UPDATE = "post_update"
    POST_DELETE = "post_delete"
    MEDIA_UPLOAD = "media_upload"
    MEDIA_DELETE = "media_delete"
    SETTINGS_CHANGE = "settings_change"
    ACCOUNT_LOCKOUT = "account_lockout"
    TWO_FACTOR_ENABLE = "2fa_enable"
    TWO_FACTOR_DISABLE = "2fa_disable"


class AuditLogger:
    """Logs security-relevant events to database"""
    
    def __init__(self, db: SQLAlchemy):
        """
        Initialize audit logger.
        
        Args:
            db: SQLAlchemy database instance
        """
        self.db = db
    
    def log_login_attempt(
        self,
        username: str,
        ip_address: str,
        success: bool,
        failure_reason: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> None:
        """
        Log a login attempt.
        
        Args:
            username: Username attempting to log in
            ip_address: IP address of the attempt
            success: Whether the login was successful
            failure_reason: Reason for failure (if applicable)
            user_id: User ID (if user exists)
        """
        attempt = LoginAttempt(
            username=username,
            ip_address=ip_address,
            success=success,
            failure_reason=failure_reason,
            user_id=user_id
        )
        self.db.session.add(attempt)
        self.db.session.commit()
    
    def log_admin_action(
        self,
        user_id: int,
        username: str,
        action_type: str,
        details: dict,
        ip_address: str
    ) -> None:
        """
        Log an administrative action.
        
        Args:
            user_id: ID of the user performing the action
            username: Username of the user
            action_type: Type of action (from ActionType constants)
            details: Dictionary of action details
            ip_address: IP address of the user
        """
        log_entry = AuditLog(
            user_id=user_id,
            username=username,
            action_type=action_type,
            details=json.dumps(details) if details else None,
            ip_address=ip_address
        )
        self.db.session.add(log_entry)
        self.db.session.commit()
    
    def log_account_lockout(
        self,
        user_id: int,
        username: str,
        ip_address: str
    ) -> None:
        """
        Log an account lockout event.
        
        Args:
            user_id: ID of the locked user
            username: Username of the locked user
            ip_address: IP address that triggered the lockout
        """
        self.log_admin_action(
            user_id=user_id,
            username=username,
            action_type=ActionType.ACCOUNT_LOCKOUT,
            details={"reason": "Multiple failed login attempts"},
            ip_address=ip_address
        )
    
    def log_2fa_change(
        self,
        user_id: int,
        username: str,
        enabled: bool
    ) -> None:
        """
        Log 2FA enable/disable event.
        
        Args:
            user_id: ID of the user
            username: Username of the user
            enabled: Whether 2FA was enabled (True) or disabled (False)
        """
        action_type = ActionType.TWO_FACTOR_ENABLE if enabled else ActionType.TWO_FACTOR_DISABLE
        self.log_admin_action(
            user_id=user_id,
            username=username,
            action_type=action_type,
            details={"enabled": enabled},
            ip_address="127.0.0.1"  # Default for user-initiated actions
        )
    
    def get_recent_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[dict] = None
    ) -> List[AuditLog]:
        """
        Retrieve recent audit logs with optional filtering.
        
        Args:
            limit: Maximum number of logs to return
            offset: Number of logs to skip
            filters: Optional dictionary of filters:
                - user_id: Filter by user ID
                - action_type: Filter by action type
                - start_date: Filter by start date
                - end_date: Filter by end date
        
        Returns:
            List of AuditLog objects
        """
        query = AuditLog.query
        
        if filters:
            if 'user_id' in filters:
                query = query.filter(AuditLog.user_id == filters['user_id'])
            
            if 'action_type' in filters:
                query = query.filter(AuditLog.action_type == filters['action_type'])
            
            if 'start_date' in filters:
                query = query.filter(AuditLog.timestamp >= filters['start_date'])
            
            if 'end_date' in filters:
                query = query.filter(AuditLog.timestamp <= filters['end_date'])
        
        # Order by timestamp descending (most recent first)
        query = query.order_by(AuditLog.timestamp.desc())
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    def get_login_attempts(
        self,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[dict] = None
    ) -> List[LoginAttempt]:
        """
        Retrieve recent login attempts with optional filtering.
        
        Args:
            limit: Maximum number of attempts to return
            offset: Number of attempts to skip
            filters: Optional dictionary of filters:
                - username: Filter by username
                - success: Filter by success status (True/False)
                - start_date: Filter by start date
                - end_date: Filter by end date
        
        Returns:
            List of LoginAttempt objects
        """
        query = LoginAttempt.query
        
        if filters:
            if 'username' in filters:
                query = query.filter(LoginAttempt.username == filters['username'])
            
            if 'success' in filters:
                query = query.filter(LoginAttempt.success == filters['success'])
            
            if 'start_date' in filters:
                query = query.filter(LoginAttempt.timestamp >= filters['start_date'])
            
            if 'end_date' in filters:
                query = query.filter(LoginAttempt.timestamp <= filters['end_date'])
        
        # Order by timestamp descending (most recent first)
        query = query.order_by(LoginAttempt.timestamp.desc())
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        return query.all()
