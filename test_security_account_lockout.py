"""
Property-Based Tests for Account Lockout Manager

This module contains property-based tests for the Account Lockout Manager component,
validating that account lockout behavior conforms to the security requirements.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timezone, timedelta
from flask import Flask
from models import db, User
from account_lockout_manager import AccountLockoutManager
from security_config import LockoutConfig


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
def lockout_manager(app):
    """Create AccountLockoutManager instance"""
    with app.app_context():
        config = LockoutConfig()
        config.threshold = 5
        config.duration = 15
        return AccountLockoutManager(db, config)


@pytest.fixture
def user(app):
    """Create a test user"""
    with app.app_context():
        user = User(username='testuser', is_admin=False)
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


class TestAccountLockoutProperties:
    """Property-based tests for account lockout"""
    
    @given(
        failed_attempts=st.integers(min_value=1, max_value=20),
        threshold=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_account_lockout_after_failed_attempts(self, failed_attempts, threshold):
        """
        Property 2: Account Lockout After Failed Attempts
        
        For any user account, when the number of consecutive failed login attempts 
        reaches the configured threshold, the account should be locked for the 
        configured duration and all login attempts during the lockout period should 
        be rejected with a descriptive error message.
        
        Validates: Requirements 2.1, 2.2
        """
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            user = User(username=f'user_{failed_attempts}_{threshold}', is_admin=False)
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            
            config = LockoutConfig()
            config.threshold = threshold
            config.duration = 15
            manager = AccountLockoutManager(db, config)
            
            for i in range(failed_attempts):
                manager.record_failed_attempt(user, f'192.168.1.{i}')
                db.session.refresh(user)
            
            is_locked = manager.is_locked(user)
            
            if failed_attempts >= threshold:
                assert is_locked, f"Account should be locked after {failed_attempts} failed attempts (threshold: {threshold})"
                assert user.locked_until is not None, "locked_until should be set when account is locked"
                
                # Ensure timezone-aware comparison
                locked_until = user.locked_until
                if locked_until.tzinfo is None:
                    locked_until = locked_until.replace(tzinfo=timezone.utc)
                assert locked_until > datetime.now(timezone.utc), "locked_until should be in the future"
                
                message = manager.get_lockout_message(user)
                assert "locked" in message.lower(), "Error message should mention 'locked'"
                assert "minutes" in message.lower() or "try again" in message.lower(), "Error message should be descriptive"
            else:
                assert not is_locked, f"Account should not be locked after {failed_attempts} failed attempts (threshold: {threshold})"
                assert user.locked_until is None, "locked_until should be None when account is not locked"

    
    @given(
        lockout_duration=st.integers(min_value=1, max_value=60),
        time_elapsed=st.integers(min_value=0, max_value=120)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_account_lockout_expiration(self, lockout_duration, time_elapsed):
        """
        Property 3: Account Lockout Expiration
        
        For any locked user account, when the current time exceeds the lockout 
        expiration time, the account should be automatically unlocked and login 
        attempts should be allowed.
        
        Validates: Requirements 2.3
        """
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            user = User(username=f'user_exp_{lockout_duration}_{time_elapsed}', is_admin=False)
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            
            config = LockoutConfig()
            config.threshold = 5
            config.duration = lockout_duration
            manager = AccountLockoutManager(db, config)
            
            for i in range(5):
                manager.record_failed_attempt(user, '192.168.1.1')
                db.session.refresh(user)
            
            assert manager.is_locked(user), "Account should be locked after threshold exceeded"
            
            simulated_lockout_time = datetime.now(timezone.utc) - timedelta(minutes=time_elapsed) + timedelta(minutes=lockout_duration)
            user.locked_until = simulated_lockout_time
            db.session.commit()
            db.session.refresh(user)
            
            is_locked = manager.is_locked(user)
            
            if time_elapsed >= lockout_duration:
                assert not is_locked, f"Account should be unlocked after {time_elapsed} minutes (duration: {lockout_duration})"
            else:
                assert is_locked, f"Account should still be locked after {time_elapsed} minutes (duration: {lockout_duration})"
    
    @given(
        failed_attempts_before=st.integers(min_value=1, max_value=4)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_failed_attempt_counter_reset(self, failed_attempts_before):
        """
        Property 4: Failed Attempt Counter Reset
        
        For any user account with failed login attempts, when a successful login 
        occurs, the failed attempt counter should be reset to zero and the 
        locked_until field should be cleared.
        
        Validates: Requirements 2.4
        """
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            user = User(username=f'user_reset_{failed_attempts_before}', is_admin=False)
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            
            config = LockoutConfig()
            config.threshold = 5
            config.duration = 15
            manager = AccountLockoutManager(db, config)
            
            for i in range(failed_attempts_before):
                manager.record_failed_attempt(user, '192.168.1.1')
                db.session.refresh(user)
            
            assert user.failed_login_attempts == failed_attempts_before, "Failed attempts should be recorded"
            
            manager.record_successful_login(user)
            db.session.refresh(user)
            
            assert user.failed_login_attempts == 0, "Failed attempt counter should be reset to 0 after successful login"
            assert user.locked_until is None, "locked_until should be cleared after successful login"
            assert user.last_login_at is not None, "last_login_at should be set after successful login"


class TestAccountLockoutEdgeCases:
    """Unit tests for account lockout edge cases"""
    
    def test_lockout_at_exact_threshold(self, app, lockout_manager, user):
        """Test that account is locked at exactly the threshold"""
        with app.app_context():
            # Re-query user in this context
            test_user = db.session.get(User, user.id)
            
            for i in range(4):
                lockout_manager.record_failed_attempt(test_user, '192.168.1.1')
                db.session.refresh(test_user)
            
            assert not lockout_manager.is_locked(test_user), "Account should not be locked before threshold"
            
            lockout_manager.record_failed_attempt(test_user, '192.168.1.1')
            db.session.refresh(test_user)
            
            assert lockout_manager.is_locked(test_user), "Account should be locked at exact threshold"
    
    def test_lockout_expiration_at_exact_time(self, app, lockout_manager, user):
        """Test that account is unlocked at exactly the expiration time"""
        with app.app_context():
            # Re-query user in this context
            test_user = db.session.get(User, user.id)
            
            for i in range(5):
                lockout_manager.record_failed_attempt(test_user, '192.168.1.1')
                db.session.refresh(test_user)
            
            assert lockout_manager.is_locked(test_user), "Account should be locked"
            
            test_user.locked_until = datetime.now(timezone.utc)
            db.session.commit()
            db.session.refresh(test_user)
            
            assert not lockout_manager.is_locked(test_user), "Account should be unlocked at exact expiration time"
    
    @pytest.mark.parametrize("threshold,duration", [
        (3, 10),
        (5, 15),
        (10, 30),
    ])
    def test_different_threshold_configurations(self, app, threshold, duration):
        """Test that lockout works with different threshold configurations"""
        with app.app_context():
            user = User(username=f'user_config_{threshold}_{duration}', is_admin=False)
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            
            config = LockoutConfig()
            config.threshold = threshold
            config.duration = duration
            manager = AccountLockoutManager(db, config)
            
            for i in range(threshold - 1):
                manager.record_failed_attempt(user, '192.168.1.1')
                db.session.refresh(user)
            
            assert not manager.is_locked(user), f"Account should not be locked before threshold {threshold}"
            
            manager.record_failed_attempt(user, '192.168.1.1')
            db.session.refresh(user)
            
            assert manager.is_locked(user), f"Account should be locked at threshold {threshold}"
            
            remaining = manager.get_remaining_lockout_time(user)
            assert remaining is not None, "Remaining time should not be None"
            assert remaining <= duration, f"Remaining time should be <= {duration} minutes"
    
    def test_manual_unlock(self, app, lockout_manager, user):
        """Test that admin can manually unlock an account"""
        with app.app_context():
            # Re-query user in this context
            test_user = db.session.get(User, user.id)
            
            for i in range(5):
                lockout_manager.record_failed_attempt(test_user, '192.168.1.1')
                db.session.refresh(test_user)
            
            assert lockout_manager.is_locked(test_user), "Account should be locked"
            
            lockout_manager.unlock_account(test_user)
            db.session.refresh(test_user)
            
            assert not lockout_manager.is_locked(test_user), "Account should be unlocked after manual unlock"
            assert test_user.failed_login_attempts == 0, "Failed attempts should be reset"
            assert test_user.locked_until is None, "locked_until should be cleared"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
