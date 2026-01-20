"""
Property-Based Tests for Security Dashboard

This module tests the security dashboard functionality including audit logs
and login attempts display, filtering, and pagination.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime, timedelta, timezone
from flask import Flask
from models import db, User, AuditLog, LoginAttempt
from audit_logger import AuditLogger, ActionType
import uuid


@pytest.fixture(scope="function", autouse=True)
def app():
    """Create test Flask application with proper cleanup."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        # Clean up database state
        db.session.rollback()
        db.session.remove()
        db.drop_all()


@pytest.fixture
def audit_logger_instance(app):
    """Create audit logger instance."""
    with app.app_context():
        return AuditLogger(db)


def generate_unique_username(base='user'):
    """Generate a unique username using UUID."""
    return f'{base}_{uuid.uuid4().hex[:8]}'


class TestAuditLogChronologicalOrdering:
    """
    **Property 20: Audit Log Chronological Ordering**
    
    For any request to retrieve audit logs, the results should be ordered
    by timestamp in descending order (most recent first).
    
    **Validates: Requirements 9.1**
    """
    
    @given(
        log_count=st.integers(min_value=2, max_value=10)
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_20_audit_log_chronological_ordering(self, app, audit_logger_instance, log_count):
        """Test that audit logs are returned in reverse chronological order."""
        with app.app_context():
            # Create a test user with unique username
            username = generate_unique_username('testuser')
            user = User(username=username, is_admin=True)
            user.set_password('TestPassword123!')
            db.session.add(user)
            db.session.commit()
            
            # Create audit logs with different timestamps
            base_time = datetime.now(timezone.utc)
            timestamps = []
            
            for i in range(log_count):
                timestamp = base_time - timedelta(minutes=i * 10)
                timestamps.append(timestamp)
                
                log = AuditLog(
                    user_id=user.id,
                    username=user.username,
                    action_type=ActionType.POST_CREATE,
                    details=f'Test log {i}',
                    ip_address='127.0.0.1',
                    timestamp=timestamp
                )
                db.session.add(log)
            
            db.session.commit()
            
            # Retrieve logs
            logs = audit_logger_instance.get_recent_logs(limit=log_count)
            
            # Verify logs are in reverse chronological order (most recent first)
            assert len(logs) == log_count, "Should retrieve all logs"
            
            for i in range(len(logs) - 1):
                assert logs[i].timestamp >= logs[i + 1].timestamp, \
                    f"Logs should be in descending order: {logs[i].timestamp} >= {logs[i + 1].timestamp}"


class TestAuditLogDisplayCompleteness:
    """
    **Property 21: Audit Log Display Completeness**
    
    For any audit log entry displayed in the dashboard, all required fields
    (timestamp, user, action type, details) should be present and visible.
    
    **Validates: Requirements 9.2**
    """
    
    @given(
        action_type=st.sampled_from([
            ActionType.POST_CREATE, ActionType.POST_UPDATE, ActionType.POST_DELETE,
            ActionType.MEDIA_UPLOAD, ActionType.MEDIA_DELETE, ActionType.SETTINGS_CHANGE
        ]),
        details=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_21_audit_log_display_completeness(self, app, audit_logger_instance, action_type, details):
        """Test that all required fields are present in audit log entries."""
        with app.app_context():
            # Create a test user with unique username
            unique_username = generate_unique_username('testuser')
            user = User(username=unique_username, is_admin=True)
            user.set_password('TestPassword123!')
            db.session.add(user)
            db.session.commit()
            
            # Log an action
            audit_logger_instance.log_admin_action(
                user_id=user.id,
                username=unique_username,
                action_type=action_type,
                details={'message': details},
                ip_address='192.168.1.1'
            )
            
            # Retrieve logs
            logs = audit_logger_instance.get_recent_logs(limit=1)
            
            assert len(logs) == 1, "Should retrieve one log"
            log = logs[0]
            
            # Verify all required fields are present
            assert log.timestamp is not None, "Timestamp should be present"
            assert log.user_id == user.id, "User ID should be present"
            assert log.username == unique_username, "Username should be present"
            assert log.action_type == action_type, "Action type should be present"
            assert log.details is not None, "Details should be present"
            assert log.ip_address is not None, "IP address should be present"


class TestAuditLogPagination:
    """
    **Property 22: Audit Log Pagination**
    
    For any audit log page request, the system should return at most the
    configured page size (50 entries) and provide pagination controls for
    navigating additional pages.
    
    **Validates: Requirements 9.3**
    """
    
    @given(
        total_logs=st.integers(min_value=51, max_value=150),
        page_size=st.integers(min_value=10, max_value=50)
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_22_audit_log_pagination(self, app, audit_logger_instance, total_logs, page_size):
        """Test that pagination returns correct number of entries."""
        with app.app_context():
            # Create a test user with unique username
            username = generate_unique_username('testuser')
            user = User(username=username, is_admin=True)
            user.set_password('TestPassword123!')
            db.session.add(user)
            db.session.commit()
            
            # Create multiple audit logs
            for i in range(total_logs):
                log = AuditLog(
                    user_id=user.id,
                    username=user.username,
                    action_type=ActionType.POST_CREATE,
                    details=f'Test log {i}',
                    ip_address='127.0.0.1'
                )
                db.session.add(log)
            
            db.session.commit()
            
            # Test first page
            first_page = audit_logger_instance.get_recent_logs(limit=page_size, offset=0)
            assert len(first_page) == page_size, f"First page should have {page_size} entries"
            
            # Test second page
            second_page = audit_logger_instance.get_recent_logs(limit=page_size, offset=page_size)
            assert len(second_page) <= page_size, f"Second page should have at most {page_size} entries"
            
            # Verify no overlap between pages
            first_page_ids = {log.id for log in first_page}
            second_page_ids = {log.id for log in second_page}
            assert len(first_page_ids & second_page_ids) == 0, "Pages should not overlap"


class TestAuditLogFiltering:
    """
    **Property 23: Audit Log Filtering**
    
    For any audit log query with filters (date range, user, action type),
    the results should include only entries matching all specified filter criteria.
    
    **Validates: Requirements 9.4**
    """
    
    @given(
        user_count=st.integers(min_value=2, max_value=5),
        logs_per_user=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_23_audit_log_filtering(self, app, audit_logger_instance, user_count, logs_per_user):
        """Test that filtering returns only matching entries."""
        with app.app_context():
            # Create multiple users with unique usernames
            users = []
            for i in range(user_count):
                user = User(username=generate_unique_username(f'user{i}'), is_admin=True)
                user.set_password('TestPassword123!')
                db.session.add(user)
                users.append(user)
            
            db.session.commit()
            
            # Create logs for each user with different action types
            action_types = [ActionType.POST_CREATE, ActionType.POST_UPDATE, ActionType.POST_DELETE]
            
            for user in users:
                for j in range(logs_per_user):
                    action_type = action_types[j % len(action_types)]
                    log = AuditLog(
                        user_id=user.id,
                        username=user.username,
                        action_type=action_type,
                        details=f'Test log for {user.username}',
                        ip_address='127.0.0.1'
                    )
                    db.session.add(log)
            
            db.session.commit()
            
            # Test filtering by user_id
            target_user = users[0]
            filtered_logs = audit_logger_instance.get_recent_logs(
                limit=100,
                filters={'user_id': target_user.id}
            )
            
            assert len(filtered_logs) == logs_per_user, \
                f"Should retrieve {logs_per_user} logs for user {target_user.username}"
            
            for log in filtered_logs:
                assert log.user_id == target_user.id, \
                    f"All logs should belong to user {target_user.id}"
            
            # Test filtering by action_type
            target_action = ActionType.POST_CREATE
            filtered_logs = audit_logger_instance.get_recent_logs(
                limit=100,
                filters={'action_type': target_action}
            )
            
            for log in filtered_logs:
                assert log.action_type == target_action, \
                    f"All logs should have action type {target_action}"


class TestLoginAttemptDisplayCompleteness:
    """
    **Property 24: Login Attempt Display Completeness**
    
    For any login attempt entry displayed in the dashboard, all required fields
    (timestamp, username, IP address, success/failure status) should be present
    and visible.
    
    **Validates: Requirements 9.6**
    """
    
    @given(
        success=st.booleans(),
        ip_address=st.ip_addresses(v=4).map(str)
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_24_login_attempt_display_completeness(self, app, audit_logger_instance, success, ip_address):
        """Test that all required fields are present in login attempt entries."""
        with app.app_context():
            # Create a test user with unique username
            unique_username = generate_unique_username('testuser')
            user = User(username=unique_username, is_admin=True)
            user.set_password('TestPassword123!')
            db.session.add(user)
            db.session.commit()
            
            # Log a login attempt
            failure_reason = None if success else 'Invalid password'
            audit_logger_instance.log_login_attempt(
                username=unique_username,
                ip_address=ip_address,
                success=success,
                failure_reason=failure_reason,
                user_id=user.id
            )
            
            # Retrieve login attempts
            attempts = audit_logger_instance.get_login_attempts(limit=1)
            
            assert len(attempts) == 1, "Should retrieve one login attempt"
            attempt = attempts[0]
            
            # Verify all required fields are present
            assert attempt.timestamp is not None, "Timestamp should be present"
            assert attempt.username == unique_username, "Username should be present"
            assert attempt.ip_address == ip_address, "IP address should be present"
            assert attempt.success == success, "Success status should be present"
            
            if not success:
                assert attempt.failure_reason is not None, "Failure reason should be present for failed attempts"


class TestSecurityDashboardEdgeCases:
    """Unit tests for security dashboard edge cases."""
    
    def test_empty_audit_logs(self, app, audit_logger_instance):
        """Test retrieving audit logs when none exist."""
        with app.app_context():
            logs = audit_logger_instance.get_recent_logs(limit=50)
            assert len(logs) == 0, "Should return empty list when no logs exist"
    
    def test_empty_login_attempts(self, app, audit_logger_instance):
        """Test retrieving login attempts when none exist."""
        with app.app_context():
            attempts = audit_logger_instance.get_login_attempts(limit=50)
            assert len(attempts) == 0, "Should return empty list when no attempts exist"
    
    def test_pagination_beyond_available_logs(self, app, audit_logger_instance):
        """Test pagination when requesting page beyond available data."""
        with app.app_context():
            # Create a test user
            user = User(username='testuser', is_admin=True)
            user.set_password('TestPassword123!')
            db.session.add(user)
            db.session.commit()
            
            # Create only 5 logs
            for i in range(5):
                log = AuditLog(
                    user_id=user.id,
                    username=user.username,
                    action_type=ActionType.POST_CREATE,
                    details=f'Test log {i}',
                    ip_address='127.0.0.1'
                )
                db.session.add(log)
            
            db.session.commit()
            
            # Request page beyond available data
            logs = audit_logger_instance.get_recent_logs(limit=50, offset=100)
            assert len(logs) == 0, "Should return empty list when offset exceeds available data"
    
    def test_filter_with_no_matches(self, app, audit_logger_instance):
        """Test filtering with criteria that match no entries."""
        with app.app_context():
            # Create a test user
            user = User(username='testuser', is_admin=True)
            user.set_password('TestPassword123!')
            db.session.add(user)
            db.session.commit()
            
            # Create some logs
            log = AuditLog(
                user_id=user.id,
                username=user.username,
                action_type=ActionType.POST_CREATE,
                details='Test log',
                ip_address='127.0.0.1'
            )
            db.session.add(log)
            db.session.commit()
            
            # Filter with non-existent user_id
            logs = audit_logger_instance.get_recent_logs(
                limit=50,
                filters={'user_id': 99999}
            )
            assert len(logs) == 0, "Should return empty list when filter matches nothing"
    
    def test_date_range_filtering(self, app, audit_logger_instance):
        """Test filtering by date range."""
        with app.app_context():
            # Create a test user
            user = User(username='testuser', is_admin=True)
            user.set_password('TestPassword123!')
            db.session.add(user)
            db.session.commit()
            
            # Create logs with different timestamps
            base_time = datetime.now(timezone.utc)
            
            # Old log (outside range)
            old_log = AuditLog(
                user_id=user.id,
                username=user.username,
                action_type=ActionType.POST_CREATE,
                details='Old log',
                ip_address='127.0.0.1',
                timestamp=base_time - timedelta(days=10)
            )
            db.session.add(old_log)
            
            # Recent log (inside range)
            recent_log = AuditLog(
                user_id=user.id,
                username=user.username,
                action_type=ActionType.POST_UPDATE,
                details='Recent log',
                ip_address='127.0.0.1',
                timestamp=base_time - timedelta(days=2)
            )
            db.session.add(recent_log)
            
            db.session.commit()
            
            # Filter by date range (last 5 days)
            start_date = base_time - timedelta(days=5)
            logs = audit_logger_instance.get_recent_logs(
                limit=50,
                filters={'start_date': start_date}
            )
            
            assert len(logs) == 1, "Should return only logs within date range"
            assert logs[0].details == 'Recent log', "Should return the recent log"
