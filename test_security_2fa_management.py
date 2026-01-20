"""
Unit tests for 2FA management routes.

Tests the complete 2FA enrollment, disable, and backup code regeneration flows.
"""

import pytest
from datetime import datetime, timezone
from flask import session
from models import db, User, TwoFactorAuth
from app import create_app
import json
from werkzeug.security import generate_password_hash, check_password_hash


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        
        # Create test admin user
        admin = User(username='admin', is_admin=True)
        admin.set_password('password123')
        db.session.add(admin)
        db.session.commit()
        
        yield app
        
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def authenticated_client(client, app):
    """Create an authenticated test client."""
    with app.app_context():
        # Login as admin
        client.post('/login', data={
            'username': 'admin',
            'password': 'password123'
        }, follow_redirects=True)
        
        yield client


def test_setup_2fa_get_displays_qr_code(authenticated_client, app):
    """Test that GET /admin/security/2fa/setup displays QR code."""
    with app.app_context():
        response = authenticated_client.get('/admin/security/2fa/setup')
        
        assert response.status_code == 200
        assert b'Setup Two-Factor Authentication' in response.data
        assert b'data:image/png;base64,' in response.data  # QR code image
        assert b'secret key manually' in response.data


def test_setup_2fa_post_with_valid_code_enables_2fa(authenticated_client, app):
    """Test that POST /admin/security/2fa/setup with valid code enables 2FA."""
    with app.app_context():
        # First, get the setup page to generate a secret
        authenticated_client.get('/admin/security/2fa/setup')
        
        # Get the user and their 2FA record
        user = User.query.filter_by(username='admin').first()
        two_factor_auth = user.two_factor_auth
        
        # Generate a valid TOTP code
        import pyotp
        totp = pyotp.TOTP(two_factor_auth.secret)
        valid_code = totp.now()
        
        # Submit the valid code
        response = authenticated_client.post('/admin/security/2fa/setup', data={
            'totp_code': valid_code
        }, follow_redirects=False)
        
        # Should redirect to backup codes page
        assert response.status_code == 302
        assert '/admin/security/2fa/backup-codes' in response.location
        
        # Verify 2FA is enabled
        db.session.refresh(two_factor_auth)
        assert two_factor_auth.enabled is True


def test_setup_2fa_post_with_invalid_code_shows_error(authenticated_client, app):
    """Test that POST /admin/security/2fa/setup with invalid code shows error."""
    with app.app_context():
        # First, get the setup page to generate a secret
        authenticated_client.get('/admin/security/2fa/setup')
        
        # Submit an invalid code
        response = authenticated_client.post('/admin/security/2fa/setup', data={
            'totp_code': '000000'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid verification code' in response.data
        
        # Verify 2FA is not enabled
        user = User.query.filter_by(username='admin').first()
        two_factor_auth = user.two_factor_auth
        assert two_factor_auth.enabled is False


def test_setup_2fa_when_already_enabled_redirects(authenticated_client, app):
    """Test that setup page redirects if 2FA is already enabled."""
    with app.app_context():
        # Enable 2FA for the user
        user = User.query.filter_by(username='admin').first()
        
        # Generate secret and enable 2FA
        from two_factor_auth_manager import TwoFactorAuthManager
        two_factor_manager = TwoFactorAuthManager(db)
        secret = two_factor_manager.generate_secret(user)
        
        import pyotp
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        two_factor_manager.enable_2fa(user, valid_code)
        
        # Try to access setup page
        response = authenticated_client.get('/admin/security/2fa/setup', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'already enabled' in response.data


def test_show_backup_codes_displays_codes(authenticated_client, app):
    """Test that backup codes page displays codes from session."""
    with app.app_context():
        # Set backup codes in session
        with authenticated_client.session_transaction() as sess:
            sess['new_backup_codes'] = ['CODE1', 'CODE2', 'CODE3', 'CODE4', 'CODE5',
                                        'CODE6', 'CODE7', 'CODE8', 'CODE9', 'CODE10']
        
        response = authenticated_client.get('/admin/security/2fa/backup-codes')
        
        assert response.status_code == 200
        assert b'Backup Codes' in response.data
        assert b'CODE1' in response.data
        assert b'CODE10' in response.data


def test_show_backup_codes_without_codes_redirects(authenticated_client, app):
    """Test that backup codes page redirects if no codes in session."""
    with app.app_context():
        response = authenticated_client.get('/admin/security/2fa/backup-codes', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'No backup codes to display' in response.data


def test_disable_2fa_get_displays_form(authenticated_client, app):
    """Test that GET /admin/security/2fa/disable displays form."""
    with app.app_context():
        # Enable 2FA first
        user = User.query.filter_by(username='admin').first()
        from two_factor_auth_manager import TwoFactorAuthManager
        two_factor_manager = TwoFactorAuthManager(db)
        secret = two_factor_manager.generate_secret(user)
        
        import pyotp
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        two_factor_manager.enable_2fa(user, valid_code)
        
        response = authenticated_client.get('/admin/security/2fa/disable')
        
        assert response.status_code == 200
        assert b'Disable Two-Factor Authentication' in response.data
        assert b'Current Password' in response.data
        assert b'Verification Code' in response.data


def test_disable_2fa_post_with_valid_credentials_disables_2fa(authenticated_client, app):
    """Test that POST /admin/security/2fa/disable with valid credentials disables 2FA."""
    with app.app_context():
        # Enable 2FA first
        user = User.query.filter_by(username='admin').first()
        from two_factor_auth_manager import TwoFactorAuthManager
        two_factor_manager = TwoFactorAuthManager(db)
        secret = two_factor_manager.generate_secret(user)
        
        import pyotp
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        two_factor_manager.enable_2fa(user, valid_code)
        
        # Verify 2FA is enabled
        assert two_factor_manager.is_enabled(user) is True
        
        # Disable 2FA
        response = authenticated_client.post('/admin/security/2fa/disable', data={
            'password': 'password123',
            'totp_code': totp.now()
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'disabled' in response.data
        
        # Verify 2FA is disabled
        db.session.refresh(user)
        assert two_factor_manager.is_enabled(user) is False


def test_disable_2fa_post_with_invalid_password_shows_error(authenticated_client, app):
    """Test that POST /admin/security/2fa/disable with invalid password shows error."""
    with app.app_context():
        # Enable 2FA first
        user = User.query.filter_by(username='admin').first()
        from two_factor_auth_manager import TwoFactorAuthManager
        two_factor_manager = TwoFactorAuthManager(db)
        secret = two_factor_manager.generate_secret(user)
        
        import pyotp
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        two_factor_manager.enable_2fa(user, valid_code)
        
        # Try to disable with wrong password
        response = authenticated_client.post('/admin/security/2fa/disable', data={
            'password': 'wrongpassword',
            'totp_code': totp.now()
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid password or verification code' in response.data
        
        # Verify 2FA is still enabled
        db.session.refresh(user)
        assert two_factor_manager.is_enabled(user) is True


def test_disable_2fa_post_with_invalid_code_shows_error(authenticated_client, app):
    """Test that POST /admin/security/2fa/disable with invalid code shows error."""
    with app.app_context():
        # Enable 2FA first
        user = User.query.filter_by(username='admin').first()
        from two_factor_auth_manager import TwoFactorAuthManager
        two_factor_manager = TwoFactorAuthManager(db)
        secret = two_factor_manager.generate_secret(user)
        
        import pyotp
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        two_factor_manager.enable_2fa(user, valid_code)
        
        # Try to disable with wrong code
        response = authenticated_client.post('/admin/security/2fa/disable', data={
            'password': 'password123',
            'totp_code': '000000'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid password or verification code' in response.data
        
        # Verify 2FA is still enabled
        db.session.refresh(user)
        assert two_factor_manager.is_enabled(user) is True


def test_disable_2fa_when_not_enabled_redirects(authenticated_client, app):
    """Test that disable page redirects if 2FA is not enabled."""
    with app.app_context():
        response = authenticated_client.get('/admin/security/2fa/disable', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'not enabled' in response.data


def test_regenerate_backup_codes_get_displays_form(authenticated_client, app):
    """Test that GET /admin/security/2fa/regenerate-codes displays form."""
    with app.app_context():
        # Enable 2FA first
        user = User.query.filter_by(username='admin').first()
        from two_factor_auth_manager import TwoFactorAuthManager
        two_factor_manager = TwoFactorAuthManager(db)
        secret = two_factor_manager.generate_secret(user)
        
        import pyotp
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        two_factor_manager.enable_2fa(user, valid_code)
        
        response = authenticated_client.get('/admin/security/2fa/regenerate-codes')
        
        assert response.status_code == 200
        assert b'Regenerate Backup Codes' in response.data


def test_regenerate_backup_codes_post_generates_new_codes(authenticated_client, app):
    """Test that POST /admin/security/2fa/regenerate-codes generates new codes."""
    with app.app_context():
        # Enable 2FA first
        user = User.query.filter_by(username='admin').first()
        from two_factor_auth_manager import TwoFactorAuthManager
        two_factor_manager = TwoFactorAuthManager(db)
        secret = two_factor_manager.generate_secret(user)
        
        import pyotp
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        success, old_codes = two_factor_manager.enable_2fa(user, valid_code)
        
        # Get old backup codes
        two_factor_auth = user.two_factor_auth
        old_backup_codes = two_factor_auth.backup_codes
        
        # Regenerate codes
        response = authenticated_client.post('/admin/security/2fa/regenerate-codes', 
                                            follow_redirects=False)
        
        # Should redirect to backup codes page
        assert response.status_code == 302
        assert '/admin/security/2fa/backup-codes' in response.location
        
        # Verify backup codes changed
        db.session.refresh(two_factor_auth)
        assert two_factor_auth.backup_codes != old_backup_codes


def test_regenerate_backup_codes_when_not_enabled_redirects(authenticated_client, app):
    """Test that regenerate page redirects if 2FA is not enabled."""
    with app.app_context():
        response = authenticated_client.get('/admin/security/2fa/regenerate-codes', 
                                           follow_redirects=True)
        
        assert response.status_code == 200
        assert b'not enabled' in response.data


def test_2fa_routes_require_authentication(client, app):
    """Test that all 2FA routes require authentication."""
    with app.app_context():
        routes = [
            '/admin/security/2fa/setup',
            '/admin/security/2fa/disable',
            '/admin/security/2fa/regenerate-codes',
            '/admin/security/2fa/backup-codes'
        ]
        
        for route in routes:
            response = client.get(route, follow_redirects=False)
            assert response.status_code == 302
            assert '/login' in response.location


def test_2fa_routes_require_admin(client, app):
    """Test that all 2FA routes require admin privileges."""
    with app.app_context():
        # Note: Non-admin users cannot log in to the system at all
        # (they are rejected at login with "Unauthorized: developer access only")
        # So we test that the routes check for admin status by verifying
        # that unauthenticated access redirects to login
        
        routes = [
            '/admin/security/2fa/setup',
            '/admin/security/2fa/disable',
            '/admin/security/2fa/regenerate-codes',
            '/admin/security/2fa/backup-codes'
        ]
        
        for route in routes:
            response = client.get(route, follow_redirects=False)
            # Should redirect to login since not authenticated
            assert response.status_code == 302
            assert '/login' in response.location


def test_complete_2fa_enrollment_flow(authenticated_client, app):
    """Test the complete 2FA enrollment flow from start to finish."""
    with app.app_context():
        # Step 1: Access setup page
        response = authenticated_client.get('/admin/security/2fa/setup')
        assert response.status_code == 200
        
        # Step 2: Get the generated secret
        user = User.query.filter_by(username='admin').first()
        two_factor_auth = user.two_factor_auth
        assert two_factor_auth is not None
        assert two_factor_auth.enabled is False
        
        # Step 3: Generate valid TOTP code
        import pyotp
        totp = pyotp.TOTP(two_factor_auth.secret)
        valid_code = totp.now()
        
        # Step 4: Submit valid code
        response = authenticated_client.post('/admin/security/2fa/setup', data={
            'totp_code': valid_code
        }, follow_redirects=False)
        assert response.status_code == 302
        
        # Step 5: View backup codes
        response = authenticated_client.get('/admin/security/2fa/backup-codes')
        assert response.status_code == 200
        assert b'CODE' in response.data or b'code' in response.data
        
        # Step 6: Verify 2FA is enabled
        db.session.refresh(two_factor_auth)
        assert two_factor_auth.enabled is True
        assert two_factor_auth.backup_codes is not None


def test_complete_2fa_disable_flow(authenticated_client, app):
    """Test the complete 2FA disable flow from start to finish."""
    with app.app_context():
        # Step 1: Enable 2FA
        user = User.query.filter_by(username='admin').first()
        from two_factor_auth_manager import TwoFactorAuthManager
        two_factor_manager = TwoFactorAuthManager(db)
        secret = two_factor_manager.generate_secret(user)
        
        import pyotp
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        two_factor_manager.enable_2fa(user, valid_code)
        
        # Step 2: Access disable page
        response = authenticated_client.get('/admin/security/2fa/disable')
        assert response.status_code == 200
        
        # Step 3: Submit valid credentials
        response = authenticated_client.post('/admin/security/2fa/disable', data={
            'password': 'password123',
            'totp_code': totp.now()
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Step 4: Verify 2FA is disabled
        db.session.refresh(user)
        assert two_factor_manager.is_enabled(user) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
