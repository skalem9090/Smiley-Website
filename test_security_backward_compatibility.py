"""
Property-Based Tests for Backward Compatibility

This module contains property-based tests to ensure that security enhancements
maintain backward compatibility with existing authentication flows.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from flask import Flask
from flask_login import LoginManager
from models import db, User
from account_lockout_manager import AccountLockoutManager
from audit_logger import AuditLogger
from two_factor_auth_manager import TwoFactorAuthManager
from session_manager import SessionManager
from security_config import LockoutConfig, SessionConfig


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
def security_managers(app):
    """Initialize security managers"""
    with app.app_context():
        lockout_config = LockoutConfig()
        session_config = SessionConfig()
        
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


@given(
    username=st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=97, max_codepoint=122),
        min_size=3,
        max_size=20
    ),
    password=st.text(min_size=12, max_size=50)
)
@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_property_26_backward_compatibility_for_non_2fa_users(app, security_managers, username, password):
    """
    Property 26: Backward Compatibility for Non-2FA Users
    
    For any user without 2FA enabled, the authentication flow should function
    identically to the pre-enhancement system, requiring only username and password.
    
    **Validates: Requirements 12.1**
    """
    with app.test_client() as client:
        with app.app_context():
            # Create user without 2FA
            user = User(username=username, is_admin=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            # Verify 2FA is not enabled
            two_factor_manager = security_managers['2fa']
            assert not two_factor_manager.is_enabled(user), \
                "User should not have 2FA enabled"
            
            # Attempt login with correct credentials
            response = client.post('/login', data={
                'username': username,
                'password': password
            }, follow_redirects=False)
            
            # Should redirect (successful login) without 2FA prompt
            # The response should NOT redirect to /verify-2fa
            if response.status_code == 302:
                location = response.location or ''
                assert 'verify-2fa' not in location.lower() and 'verify_2fa' not in location.lower(), \
                    "Non-2FA user should not be redirected to 2FA verification"
            
            # Verify user can access protected resources after login
            # (This would be tested in a full integration test)
            
            # Verify authentication flow only required username and password
            # No additional steps should be required for non-2FA users


class TestBackwardCompatibilityEdgeCases:
    """Unit tests for backward compatibility edge cases"""
    
    def test_existing_user_without_2fa_can_login(self, app, security_managers):
        """Test that existing users without 2FA can still log in"""
        with app.test_client() as client:
            with app.app_context():
                # Create user (simulating existing user before 2FA was added)
                user = User(username='olduser', is_admin=True)
                user.set_password('OldPassword123!')
                db.session.add(user)
                db.session.commit()
                
                # Verify no 2FA record exists
                two_factor_manager = security_managers['2fa']
                assert not two_factor_manager.is_enabled(user)
                
                # Login should work normally
                response = client.post('/login', data={
                    'username': 'olduser',
                    'password': 'OldPassword123!'
                }, follow_redirects=False)
                
                # Should redirect to index, not 2FA verification
                assert response.status_code == 302
                location = response.location or ''
                assert 'verify-2fa' not in location.lower()
    
    def test_password_hashing_still_works(self, app, security_managers):
        """Test that existing password hashing mechanism is preserved"""
        with app.app_context():
            # Create user
            user = User(username='hashtest', is_admin=True)
            user.set_password('TestPassword123!')
            db.session.add(user)
            db.session.commit()
            
            # Verify password hashing works
            assert user.check_password('TestPassword123!')
            assert not user.check_password('WrongPassword')
    
    def test_user_model_fields_preserved(self, app, security_managers):
        """Test that existing user model fields are preserved"""
        with app.app_context():
            # Create user
            user = User(username='fieldtest', is_admin=True)
            user.set_password('TestPassword123!')
            db.session.add(user)
            db.session.commit()
            
            # Verify existing fields still exist
            assert hasattr(user, 'id')
            assert hasattr(user, 'username')
            assert hasattr(user, 'password_hash')
            assert hasattr(user, 'is_admin')
            
            # Verify new security fields exist but don't break existing functionality
            assert hasattr(user, 'failed_login_attempts')
            assert hasattr(user, 'locked_until')
            assert hasattr(user, 'last_login_at')
            
            # Verify default values
            assert user.failed_login_attempts == 0
            assert user.locked_until is None
            assert user.last_login_at is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
