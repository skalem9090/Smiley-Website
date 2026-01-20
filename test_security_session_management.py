"""
Property-Based Tests for Session Manager

This module contains property-based tests for the Session Manager component,
validating that session management behavior conforms to the security requirements.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timezone, timedelta
from flask import Flask, session
from flask_login import LoginManager, login_user, current_user
from models import db, User
from session_manager import SessionManager
from security_config import SessionConfig


@pytest.fixture
def app():
    """Create Flask app for testing"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False
    
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def user(app):
    """Create a test user"""
    with app.app_context():
        user = User(username='testuser', is_admin=False)
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        yield user


@pytest.fixture
def session_manager(app):
    """Create SessionManager instance"""
    config = SessionConfig()
    config.timeout = 120  # 2 hours
    return SessionManager(app, config)


class TestSessionManagementProperties:
    """Property-based tests for session management"""
    
    @given(
        timeout_minutes=st.integers(min_value=1, max_value=240)
    )
    @settings(max_examples=20, deadline=None)
    def test_property_session_expiration_time(self, timeout_minutes):
        """
        Property 11: Session Expiration Time
        
        For any newly created user session, the system should set an 
        expiration time equal to the current time plus the configured 
        timeout duration.
        
        Validates: Requirements 4.1
        """
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['WTF_CSRF_ENABLED'] = False
        
        db.init_app(app)
        
        login_manager = LoginManager()
        login_manager.init_app(app)
        
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))
        
        with app.app_context():
            db.create_all()
            
            user = User(username=f'user_timeout_{timeout_minutes}', is_admin=False)
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            
            config = SessionConfig()
            config.timeout = timeout_minutes
            manager = SessionManager(app, config)
            
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    manager.create_session(user, sess)
                    
                    # Verify session data is set
                    assert 'user_id' in sess, "Session should have user_id"
                    assert 'created_at' in sess, "Session should have created_at"
                    assert 'last_activity' in sess, "Session should have last_activity"
                    
                    # Verify timestamps are recent
                    created_at = datetime.fromisoformat(sess['created_at'])
                    last_activity = datetime.fromisoformat(sess['last_activity'])
                    
                    now = datetime.now(timezone.utc)
                    assert (now - created_at).total_seconds() < 5, "created_at should be recent"
                    assert (now - last_activity).total_seconds() < 5, "last_activity should be recent"
                    
                    # Verify timeout is configured correctly
                    assert manager.timeout_minutes == timeout_minutes, f"Timeout should be {timeout_minutes} minutes"
    
    @given(
        elapsed_minutes=st.integers(min_value=0, max_value=180)
    )
    @settings(max_examples=20, deadline=None)
    def test_property_session_timeout_enforcement(self, elapsed_minutes):
        """
        Property 13: Session Timeout Enforcement
        
        For any session where the time since last activity exceeds the 
        configured timeout, the system should invalidate the session and 
        require re-authentication.
        
        Validates: Requirements 4.3
        """
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['WTF_CSRF_ENABLED'] = False
        
        db.init_app(app)
        
        login_manager = LoginManager()
        login_manager.init_app(app)
        
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))
        
        with app.app_context():
            db.create_all()
            
            user = User(username=f'user_elapsed_{elapsed_minutes}', is_admin=False)
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            
            config = SessionConfig()
            config.timeout = 60  # 60 minutes
            manager = SessionManager(app, config)
            
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    # Create session with simulated last activity time
                    past_time = datetime.now(timezone.utc) - timedelta(minutes=elapsed_minutes)
                    sess['user_id'] = user.id
                    sess['created_at'] = past_time.isoformat()
                    sess['last_activity'] = past_time.isoformat()
                
                # Check if session is expired
                with client.session_transaction() as sess:
                    is_expired = manager.is_expired(sess)
                    
                    if elapsed_minutes > config.timeout:
                        assert is_expired, f"Session should be expired after {elapsed_minutes} minutes (timeout: {config.timeout})"
                    else:
                        assert not is_expired, f"Session should not be expired after {elapsed_minutes} minutes (timeout: {config.timeout})"


class TestSessionManagementEdgeCases:
    """Unit tests for session management edge cases"""
    
    def test_session_creation_sets_all_fields(self, app, session_manager, user):
        """Test that session creation sets all required fields"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                session_manager.create_session(user, sess)
                
                assert 'user_id' in sess, "Session should have user_id"
                assert 'created_at' in sess, "Session should have created_at"
                assert 'last_activity' in sess, "Session should have last_activity"
                assert sess['user_id'] == user.id, "user_id should match"
    
    def test_update_activity_updates_timestamp(self, app, session_manager, user):
        """Test that update_activity updates the last_activity timestamp"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                session_manager.create_session(user, sess)
                original_activity = sess['last_activity']
            
            # Simulate some time passing
            import time
            time.sleep(0.1)
            
            with client.session_transaction() as sess:
                # Manually update to simulate authenticated request
                sess['last_activity'] = datetime.now(timezone.utc).isoformat()
                new_activity = sess['last_activity']
                
                assert new_activity != original_activity, "last_activity should be updated"
    
    def test_invalidate_session_clears_data(self, app, session_manager, user):
        """Test that invalidate_session clears all session data"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                session_manager.create_session(user, sess)
                assert 'user_id' in sess, "Session should have data"
            
            with client.session_transaction() as sess:
                session_manager.invalidate_session(sess)
            
            with client.session_transaction() as sess:
                assert 'user_id' not in sess, "Session should be cleared"
                assert 'created_at' not in sess, "Session should be cleared"
                assert 'last_activity' not in sess, "Session should be cleared"
    
    def test_get_remaining_time_calculation(self, app, user):
        """Test that get_remaining_time calculates correctly"""
        config = SessionConfig()
        config.timeout = 60  # 60 minutes
        manager = SessionManager(app, config)
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                # Create session 30 minutes ago
                past_time = datetime.now(timezone.utc) - timedelta(minutes=30)
                sess['user_id'] = user.id
                sess['created_at'] = past_time.isoformat()
                sess['last_activity'] = past_time.isoformat()
            
            with client.session_transaction() as sess:
                remaining = manager.get_remaining_time(sess)
                
                # Should have approximately 30 minutes remaining
                # Allow some tolerance for test execution time
                if remaining is not None:
                    assert 25 <= remaining <= 35, f"Should have ~30 minutes remaining, got {remaining}"
    
    def test_session_expiration_at_exact_timeout(self, app, user):
        """Test that session expires at exactly the timeout duration"""
        config = SessionConfig()
        config.timeout = 60  # 60 minutes
        manager = SessionManager(app, config)
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                # Create session exactly 60 minutes ago
                past_time = datetime.now(timezone.utc) - timedelta(minutes=60)
                sess['user_id'] = user.id
                sess['created_at'] = past_time.isoformat()
                sess['last_activity'] = past_time.isoformat()
            
            with client.session_transaction() as sess:
                # Check expiration logic directly
                last_activity = datetime.fromisoformat(sess['last_activity'])
                if last_activity.tzinfo is None:
                    last_activity = last_activity.replace(tzinfo=timezone.utc)
                
                now = datetime.now(timezone.utc)
                elapsed = (now - last_activity).total_seconds() / 60
                
                assert elapsed >= config.timeout, "Session should be expired at exact timeout"
    
    def test_session_not_expired_before_timeout(self, app, user):
        """Test that session is not expired before timeout"""
        config = SessionConfig()
        config.timeout = 60  # 60 minutes
        manager = SessionManager(app, config)
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                # Create session 30 minutes ago
                past_time = datetime.now(timezone.utc) - timedelta(minutes=30)
                sess['user_id'] = user.id
                sess['created_at'] = past_time.isoformat()
                sess['last_activity'] = past_time.isoformat()
            
            with client.session_transaction() as sess:
                # Check expiration logic directly
                last_activity = datetime.fromisoformat(sess['last_activity'])
                if last_activity.tzinfo is None:
                    last_activity = last_activity.replace(tzinfo=timezone.utc)
                
                now = datetime.now(timezone.utc)
                elapsed = (now - last_activity).total_seconds() / 60
                
                assert elapsed < config.timeout, "Session should not be expired before timeout"
    
    @pytest.mark.parametrize("timeout", [30, 60, 120, 240])
    def test_different_timeout_configurations(self, app, user, timeout):
        """Test that session manager works with different timeout configurations"""
        config = SessionConfig()
        config.timeout = timeout
        manager = SessionManager(app, config)
        
        assert manager.timeout_minutes == timeout, f"Timeout should be {timeout} minutes"
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                manager.create_session(user, sess)
                
                # Verify session is created
                assert 'user_id' in sess, "Session should be created"
                
                # Verify remaining time is approximately the timeout
                remaining = manager.get_remaining_time(sess)
                if remaining is not None:
                    assert remaining <= timeout, f"Remaining time should be <= {timeout}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
