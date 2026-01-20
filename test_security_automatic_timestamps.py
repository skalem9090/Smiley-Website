"""
Property-based test for automatic timestamp assignment in security models.

**Feature: security-hardening, Property 25: Automatic Timestamp Assignment**
**Validates: Requirements 10.5, 10.6**

This module tests that LoginAttempt and AuditLog records automatically
receive timestamps when created.
"""

import pytest
from datetime import datetime, timezone, timedelta
from hypothesis import given, strategies as st, settings
from flask import Flask
from models import db, User, LoginAttempt, AuditLog


class TestAutomaticTimestampAssignment:
    """Test suite for automatic timestamp assignment property."""
    
    def create_app_and_db(self):
        """Create a test Flask app and database."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            
            # Create a test user
            test_user = User(username='testuser', is_admin=True)
            test_user.set_password('password')
            db.session.add(test_user)
            db.session.commit()
            
            user_id = test_user.id
            
        return app, user_id
    
    @given(
        username=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        ip_address=st.from_regex(r'^(\d{1,3}\.){3}\d{1,3}$', fullmatch=True),
        success=st.booleans(),
        failure_reason=st.one_of(st.none(), st.text(min_size=1, max_size=200))
    )
    @settings(max_examples=100, deadline=3000)
    def test_login_attempt_automatic_timestamp(self, username, ip_address, success, failure_reason):
        """
        **Property 25: Automatic Timestamp Assignment (LoginAttempt)**
        
        For any LoginAttempt record created without an explicit timestamp,
        the system should automatically set the timestamp to the current UTC time.
        """
        app, user_id = self.create_app_and_db()
        
        with app.app_context():
            # Record time before creating the record
            time_before = datetime.now(timezone.utc)
            
            # Create LoginAttempt without explicit timestamp
            login_attempt = LoginAttempt(
                user_id=user_id if success else None,
                username=username.strip(),
                ip_address=ip_address,
                success=success,
                failure_reason=failure_reason if not success else None
            )
            
            db.session.add(login_attempt)
            db.session.commit()
            
            # Record time after creating the record
            time_after = datetime.now(timezone.utc)
            
            # Verify timestamp was automatically assigned
            assert login_attempt.timestamp is not None, "Timestamp should be automatically assigned"
            
            # Verify timestamp is within reasonable range
            timestamp = login_attempt.timestamp
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            
            assert time_before <= timestamp <= time_after, \
                f"Timestamp should be between {time_before} and {time_after}, got {timestamp}"
    
    @given(
        action_type=st.sampled_from(['post_create', 'post_update', 'post_delete', 'media_upload', 'media_delete']),
        details=st.one_of(st.none(), st.text(min_size=1, max_size=500)),
        ip_address=st.from_regex(r'^(\d{1,3}\.){3}\d{1,3}$', fullmatch=True)
    )
    @settings(max_examples=100, deadline=3000)
    def test_audit_log_automatic_timestamp(self, action_type, details, ip_address):
        """
        **Property 25: Automatic Timestamp Assignment (AuditLog)**
        
        For any AuditLog record created without an explicit timestamp,
        the system should automatically set the timestamp to the current UTC time.
        """
        app, user_id = self.create_app_and_db()
        
        with app.app_context():
            # Get user for username
            user = User.query.get(user_id)
            
            # Record time before creating the record
            time_before = datetime.now(timezone.utc)
            
            # Create AuditLog without explicit timestamp
            audit_log = AuditLog(
                user_id=user_id,
                username=user.username,
                action_type=action_type,
                details=details,
                ip_address=ip_address
            )
            
            db.session.add(audit_log)
            db.session.commit()
            
            # Record time after creating the record
            time_after = datetime.now(timezone.utc)
            
            # Verify timestamp was automatically assigned
            assert audit_log.timestamp is not None, "Timestamp should be automatically assigned"
            
            # Verify timestamp is within reasonable range
            timestamp = audit_log.timestamp
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            
            assert time_before <= timestamp <= time_after, \
                f"Timestamp should be between {time_before} and {time_after}, got {timestamp}"
    
    @given(
        username=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        ip_address=st.from_regex(r'^(\d{1,3}\.){3}\d{1,3}$', fullmatch=True)
    )
    @settings(max_examples=50, deadline=3000)
    def test_explicit_timestamp_preserved(self, username, ip_address):
        """
        **Property 25: Explicit Timestamp Preservation**
        
        For any LoginAttempt or AuditLog record created with an explicit timestamp,
        the system should preserve the provided timestamp value.
        """
        app, user_id = self.create_app_and_db()
        
        with app.app_context():
            # Create a specific timestamp (1 hour ago)
            explicit_timestamp = datetime.now(timezone.utc) - timedelta(hours=1)
            
            # Create LoginAttempt with explicit timestamp
            login_attempt = LoginAttempt(
                user_id=user_id,
                username=username.strip(),
                ip_address=ip_address,
                success=True,
                timestamp=explicit_timestamp
            )
            
            db.session.add(login_attempt)
            db.session.commit()
            
            # Verify explicit timestamp was preserved
            saved_timestamp = login_attempt.timestamp
            if saved_timestamp.tzinfo is None:
                saved_timestamp = saved_timestamp.replace(tzinfo=timezone.utc)
            
            # Allow for small differences due to database precision
            time_diff = abs((saved_timestamp - explicit_timestamp).total_seconds())
            assert time_diff < 1, \
                f"Explicit timestamp should be preserved, expected {explicit_timestamp}, got {saved_timestamp}"


if __name__ == '__main__':
    pytest.main([__file__])
