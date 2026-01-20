"""
Property-Based Tests for Audit Logger

This module contains property-based tests for the Audit Logger component,
validating that audit logging behavior conforms to the security requirements.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timezone, timedelta
from flask import Flask
from models import db, User, AuditLog, LoginAttempt
from audit_logger import AuditLogger, ActionType


@pytest.fixture
def app():
    """Create Flask app for testing"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def audit_logger(app):
    """Create AuditLogger instance"""
    with app.app_context():
        return AuditLogger(db)


@pytest.fixture
def user(app):
    """Create a test user"""
    with app.app_context():
        user = User(username='testuser', is_admin=True)
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


class TestAuditLoggingProperties:
    """Property-based tests for audit logging"""
    
    @given(
        action_type=st.sampled_from([
            ActionType.POST_CREATE,
            ActionType.POST_UPDATE,
            ActionType.POST_DELETE,
            ActionType.MEDIA_UPLOAD,
            ActionType.MEDIA_DELETE,
            ActionType.SETTINGS_CHANGE
        ]),
        post_id=st.integers(min_value=1, max_value=1000)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_admin_action_audit_logging(self, action_type, post_id):
        """
        Property 17: Admin Action Audit Logging
        
        For any administrative action (post create/update/delete, media upload/delete,
        settings change), an audit log entry should be created containing the timestamp,
        user ID, username, action type, relevant details, and IP address.
        
        Validates: Requirements 8.1-8.6
        """
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            user = User(username=f'admin_{action_type}_{post_id}', is_admin=True)
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            
            logger = AuditLogger(db)
            
            # Log an admin action
            details = {"post_id": post_id} if "post" in action_type.lower() else {"file_name": f"file_{post_id}.jpg"}
            ip_address = f"192.168.1.{post_id % 255}"
            
            logger.log_admin_action(
                user_id=user.id,
                username=user.username,
                action_type=action_type,
                details=details,
                ip_address=ip_address
            )
            
            # Verify log entry was created
            log_entry = AuditLog.query.filter_by(user_id=user.id).first()
            
            assert log_entry is not None, "Audit log entry should be created"
            assert log_entry.user_id == user.id, "Log should contain correct user_id"
            assert log_entry.username == user.username, "Log should contain correct username"
            assert log_entry.action_type == action_type, "Log should contain correct action_type"
            assert log_entry.ip_address == ip_address, "Log should contain correct IP address"
            assert log_entry.timestamp is not None, "Log should have a timestamp"
            assert log_entry.details is not None, "Log should contain details"
            
            # Verify timestamp is recent (within last minute)
            now = datetime.now(timezone.utc)
            log_time = log_entry.timestamp
            if log_time.tzinfo is None:
                log_time = log_time.replace(tzinfo=timezone.utc)
            time_diff = (now - log_time).total_seconds()
            assert time_diff < 60, "Timestamp should be recent"
    
    @given(
        username=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        success=st.booleans()
    )
    @settings(max_examples=50, deadline=None)
    def test_property_login_attempt_recording(self, username, success):
        """
        Property 18: Login Attempt Recording
        
        For any login attempt (successful or failed), a LoginAttempt record should be
        created containing the timestamp, username, IP address, success status, and
        failure reason (if applicable).
        
        Validates: Requirements 8.7, 8.8
        """
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            
            # Create user if needed
            user = None
            if success:
                user = User(username=username, is_admin=False)
                user.set_password('password123')
                db.session.add(user)
                db.session.commit()
                db.session.refresh(user)
            
            logger = AuditLogger(db)
            
            # Log login attempt
            ip_address = "192.168.1.100"
            failure_reason = None if success else "Invalid password"
            user_id = user.id if user else None
            
            logger.log_login_attempt(
                username=username,
                ip_address=ip_address,
                success=success,
                failure_reason=failure_reason,
                user_id=user_id
            )
            
            # Verify login attempt was recorded
            attempt = LoginAttempt.query.filter_by(username=username).first()
            
            assert attempt is not None, "Login attempt should be recorded"
            assert attempt.username == username, "Attempt should contain correct username"
            assert attempt.ip_address == ip_address, "Attempt should contain correct IP address"
            assert attempt.success == success, "Attempt should contain correct success status"
            assert attempt.timestamp is not None, "Attempt should have a timestamp"
            
            if success:
                assert attempt.user_id == user_id, "Successful attempt should have user_id"
                assert attempt.failure_reason is None, "Successful attempt should not have failure_reason"
            else:
                assert attempt.failure_reason == failure_reason, "Failed attempt should have failure_reason"
    
    @given(
        event_type=st.sampled_from(['account_lockout', '2fa_enable', '2fa_disable'])
    )
    @settings(max_examples=30, deadline=None)
    def test_property_security_event_audit_logging(self, event_type):
        """
        Property 19: Security Event Audit Logging
        
        For any security-relevant event (account lockout, 2FA enable/disable), an audit
        log entry should be created containing the timestamp, user ID, username, action
        type, and relevant details.
        
        Validates: Requirements 8.9, 8.10
        """
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            user = User(username=f'user_{event_type}', is_admin=False)
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            
            logger = AuditLogger(db)
            
            # Log security event
            if event_type == 'account_lockout':
                logger.log_account_lockout(
                    user_id=user.id,
                    username=user.username,
                    ip_address="192.168.1.50"
                )
                expected_action_type = ActionType.ACCOUNT_LOCKOUT
            elif event_type == '2fa_enable':
                logger.log_2fa_change(
                    user_id=user.id,
                    username=user.username,
                    enabled=True
                )
                expected_action_type = ActionType.TWO_FACTOR_ENABLE
            else:  # 2fa_disable
                logger.log_2fa_change(
                    user_id=user.id,
                    username=user.username,
                    enabled=False
                )
                expected_action_type = ActionType.TWO_FACTOR_DISABLE
            
            # Verify audit log entry was created
            log_entry = AuditLog.query.filter_by(user_id=user.id).first()
            
            assert log_entry is not None, "Audit log entry should be created for security event"
            assert log_entry.user_id == user.id, "Log should contain correct user_id"
            assert log_entry.username == user.username, "Log should contain correct username"
            assert log_entry.action_type == expected_action_type, f"Log should have action_type {expected_action_type}"
            assert log_entry.timestamp is not None, "Log should have a timestamp"
            assert log_entry.details is not None, "Log should contain details"
    
    @given(
        num_failed_attempts=st.integers(min_value=5, max_value=10)
    )
    @settings(max_examples=20, deadline=None)
    def test_property_lockout_event_logging(self, num_failed_attempts):
        """
        Property 5: Lockout Event Logging
        
        For any account lockout event, an audit log entry should be created containing
        the timestamp, username, user ID, and IP address.
        
        Validates: Requirements 2.6
        """
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            user = User(username=f'lockout_user_{num_failed_attempts}', is_admin=False)
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            
            logger = AuditLogger(db)
            ip_address = "192.168.1.75"
            
            # Log account lockout
            logger.log_account_lockout(
                user_id=user.id,
                username=user.username,
                ip_address=ip_address
            )
            
            # Verify lockout was logged
            log_entry = AuditLog.query.filter_by(
                user_id=user.id,
                action_type=ActionType.ACCOUNT_LOCKOUT
            ).first()
            
            assert log_entry is not None, "Lockout event should be logged"
            assert log_entry.user_id == user.id, "Log should contain user_id"
            assert log_entry.username == user.username, "Log should contain username"
            assert log_entry.ip_address == ip_address, "Log should contain IP address"
            assert log_entry.timestamp is not None, "Log should have timestamp"


class TestAuditLoggingRetrieval:
    """Unit tests for audit log retrieval"""
    
    def test_get_recent_logs_chronological_order(self, app, audit_logger, user):
        """Test that logs are returned in reverse chronological order"""
        with app.app_context():
            test_user = db.session.get(User, user.id)
            
            # Create multiple log entries
            for i in range(5):
                audit_logger.log_admin_action(
                    user_id=test_user.id,
                    username=test_user.username,
                    action_type=ActionType.POST_CREATE,
                    details={"post_id": i},
                    ip_address="192.168.1.1"
                )
            
            # Retrieve logs
            logs = audit_logger.get_recent_logs(limit=5)
            
            assert len(logs) == 5, "Should retrieve all 5 logs"
            
            # Verify chronological order (most recent first)
            for i in range(len(logs) - 1):
                assert logs[i].timestamp >= logs[i + 1].timestamp, \
                    "Logs should be in reverse chronological order"
    
    def test_get_recent_logs_with_filters(self, app, audit_logger):
        """Test filtering audit logs"""
        with app.app_context():
            # Create users and logs
            user1 = User(username='user1', is_admin=True)
            user1.set_password('pass')
            user2 = User(username='user2', is_admin=True)
            user2.set_password('pass')
            db.session.add_all([user1, user2])
            db.session.commit()
            db.session.refresh(user1)
            db.session.refresh(user2)
            
            # Create logs for different users and action types
            audit_logger.log_admin_action(user1.id, user1.username, ActionType.POST_CREATE, {}, "192.168.1.1")
            audit_logger.log_admin_action(user1.id, user1.username, ActionType.POST_UPDATE, {}, "192.168.1.1")
            audit_logger.log_admin_action(user2.id, user2.username, ActionType.POST_CREATE, {}, "192.168.1.2")
            
            # Filter by user_id
            logs = audit_logger.get_recent_logs(filters={'user_id': user1.id})
            assert len(logs) == 2, "Should return only user1's logs"
            assert all(log.user_id == user1.id for log in logs)
            
            # Filter by action_type
            logs = audit_logger.get_recent_logs(filters={'action_type': ActionType.POST_CREATE})
            assert len(logs) == 2, "Should return only POST_CREATE logs"
            assert all(log.action_type == ActionType.POST_CREATE for log in logs)
    
    def test_get_login_attempts_with_filters(self, app, audit_logger):
        """Test filtering login attempts"""
        with app.app_context():
            # Create login attempts
            audit_logger.log_login_attempt('user1', '192.168.1.1', True)
            audit_logger.log_login_attempt('user1', '192.168.1.1', False, 'Invalid password')
            audit_logger.log_login_attempt('user2', '192.168.1.2', True)
            
            # Filter by username
            attempts = audit_logger.get_login_attempts(filters={'username': 'user1'})
            assert len(attempts) == 2, "Should return only user1's attempts"
            assert all(attempt.username == 'user1' for attempt in attempts)
            
            # Filter by success
            attempts = audit_logger.get_login_attempts(filters={'success': True})
            assert len(attempts) == 2, "Should return only successful attempts"
            assert all(attempt.success for attempt in attempts)
    
    def test_pagination(self, app, audit_logger, user):
        """Test pagination of audit logs"""
        with app.app_context():
            test_user = db.session.get(User, user.id)
            
            # Create 10 log entries
            for i in range(10):
                audit_logger.log_admin_action(
                    user_id=test_user.id,
                    username=test_user.username,
                    action_type=ActionType.POST_CREATE,
                    details={"post_id": i},
                    ip_address="192.168.1.1"
                )
            
            # Get first page
            page1 = audit_logger.get_recent_logs(limit=5, offset=0)
            assert len(page1) == 5, "First page should have 5 logs"
            
            # Get second page
            page2 = audit_logger.get_recent_logs(limit=5, offset=5)
            assert len(page2) == 5, "Second page should have 5 logs"
            
            # Verify no overlap
            page1_ids = {log.id for log in page1}
            page2_ids = {log.id for log in page2}
            assert len(page1_ids & page2_ids) == 0, "Pages should not overlap"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
