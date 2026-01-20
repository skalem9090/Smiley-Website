"""
Integration Tests for Complete Login Flow

This module contains integration tests for the complete login flow with all
security features integrated: rate limiting, account lockout, 2FA, and session management.
"""

import pytest
from flask import Flask, session
from flask_login import LoginManager
from datetime import datetime, timezone, timedelta
from models import db, User, TwoFactorAuth
from account_lockout_manager import AccountLockoutManager
from audit_logger import AuditLogger
from two_factor_auth_manager import TwoFactorAuthManager
from session_manager import SessionManager
from security_config import LockoutConfig, SessionConfig
import pyotp


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
        user = User(username='testuser', is_admin=True)
        user.set_password('ValidPassword123!')
        db.session.add(user)
        db.session.commit()
        
        # Re-query to get fresh instance
        user = User.query.filter_by(username='testuser').first()
        yield user


@pytest.fixture
def user_with_2fa(app):
    """Create a test user with 2FA enabled"""
    with app.app_context():
        user = User(username='user2fa', is_admin=True)
        user.set_password('ValidPassword123!')
        db.session.add(user)
        db.session.commit()
        
        # Enable 2FA
        two_factor_manager = TwoFactorAuthManager(db)
        secret = two_factor_manager.generate_secret(user)
        
        # Generate a valid TOTP code
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        # Enable 2FA with the valid code
        success, backup_codes = two_factor_manager.enable_2fa(user, valid_code)
        assert success, "2FA should be enabled successfully"
        
        db.session.commit()
        
        # Re-query to get fresh instance
        user = User.query.filter_by(username='user2fa').first()
        yield user


@pytest.fixture
def security_managers(app):
    """Initialize security managers"""
    with app.app_context():
        lockout_config = LockoutConfig()
        lockout_config.threshold = 3
        lockout_config.duration = 15
        
        session_config = SessionConfig()
        session_config.timeout = 120
        
        lockout_manager = AccountLockoutManager(db, lockout_config)
        audit_logger = AuditLogger(db)
        two_factor_manager = TwoFactorAuthManager(db)
        session_manager = SessionManager(app, session_config)
        
        yield {
            'lockout': lockout_manager,
            'audit': audit_logger,
            '2fa': two_factor_manager,
            'session': session_manager
        }


class TestLoginFlowWithoutTwoFactor:
    """Integration tests for login flow without 2FA"""
    
    def test_successful_login_without_2fa(self, app, user, security_managers):
        """Test successful login for user without 2FA"""
        with app.test_client() as client:
            with app.app_context():
                # Simulate login
                response = client.post('/login', data={
                    'username': 'testuser',
                    'password': 'ValidPassword123!'
                }, follow_redirects=False)
                
                # Should redirect (successful login)
                assert response.status_code in [302, 200]
                
                # Verify user's last_login_at is updated
                user = User.query.filter_by(username='testuser').first()
                assert user.last_login_at is not None
                
                # Verify failed attempts are reset
                assert user.failed_login_attempts == 0
                assert user.locked_until is None
    
    def test_failed_login_increments_counter(self, app, user, security_managers):
        """Test that failed login increments failed attempt counter"""
        with app.test_client() as client:
            with app.app_context():
                # Attempt login with wrong password
                response = client.post('/login', data={
                    'username': 'testuser',
                    'password': 'WrongPassword'
                }, follow_redirects=True)
                
                # Verify failed attempts incremented
                user = User.query.filter_by(username='testuser').first()
                assert user.failed_login_attempts == 1


class TestLoginFlowWithTwoFactor:
    """Integration tests for login flow with 2FA"""
    
    def test_login_with_2fa_prompts_for_code(self, app, user_with_2fa, security_managers):
        """Test that login with 2FA prompts for TOTP code"""
        with app.test_client() as client:
            with app.app_context():
                # Attempt login with correct password
                response = client.post('/login', data={
                    'username': 'user2fa',
                    'password': 'ValidPassword123!'
                }, follow_redirects=False)
                
                # Should redirect to 2FA verification
                assert response.status_code == 302
                assert '/verify-2fa' in response.location or 'verify_2fa' in response.location
    
    def test_successful_2fa_verification(self, app, user_with_2fa, security_managers):
        """Test successful 2FA verification completes login"""
        with app.test_client() as client:
            with app.app_context():
                # First, login with password
                response = client.post('/login', data={
                    'username': 'user2fa',
                    'password': 'ValidPassword123!'
                }, follow_redirects=False)
                
                # Get the 2FA secret
                user = User.query.filter_by(username='user2fa').first()
                two_fa_record = TwoFactorAuth.query.filter_by(user_id=user.id).first()
                
                # Generate valid TOTP code
                totp = pyotp.TOTP(two_fa_record.secret)
                valid_code = totp.now()
                
                # Verify 2FA
                response = client.post('/verify-2fa', data={
                    'totp_code': valid_code
                }, follow_redirects=False)
                
                # Should redirect to index (successful login)
                assert response.status_code == 302


class TestLoginFlowWithAccountLockout:
    """Integration tests for login flow with account lockout"""
    
    def test_account_locks_after_threshold(self, app, user, security_managers):
        """Test that account locks after exceeding failed attempt threshold"""
        with app.test_client() as client:
            with app.app_context():
                lockout_manager = security_managers['lockout']
                
                # Make 3 failed attempts (threshold is 3)
                for i in range(3):
                    response = client.post('/login', data={
                        'username': 'testuser',
                        'password': 'WrongPassword'
                    }, follow_redirects=True)
                
                # Verify account is locked
                user = User.query.filter_by(username='testuser').first()
                assert lockout_manager.is_locked(user)
                assert user.locked_until is not None
    
    def test_locked_account_prevents_login(self, app, user, security_managers):
        """Test that locked account prevents login even with correct password"""
        with app.test_client() as client:
            with app.app_context():
                lockout_manager = security_managers['lockout']
                
                # Lock the account
                user = User.query.filter_by(username='testuser').first()
                user.failed_login_attempts = 3
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                db.session.commit()
                
                # Attempt login with correct password
                response = client.post('/login', data={
                    'username': 'testuser',
                    'password': 'ValidPassword123!'
                }, follow_redirects=True)
                
                # Should show lockout message
                assert b'locked' in response.data.lower() or b'Account locked' in response.data


class TestLoginFlowWithSessionManagement:
    """Integration tests for login flow with session management"""
    
    def test_session_created_on_login(self, app, user, security_managers):
        """Test that session is created on successful login"""
        with app.test_client() as client:
            with app.app_context():
                # Login
                response = client.post('/login', data={
                    'username': 'testuser',
                    'password': 'ValidPassword123!'
                }, follow_redirects=False)
                
                # Check session data
                with client.session_transaction() as sess:
                    assert 'user_id' in sess or '_user_id' in sess
                    # Session manager creates these fields
                    if 'created_at' in sess:
                        assert 'last_activity' in sess


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
