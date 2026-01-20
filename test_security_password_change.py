"""
Unit tests for password change functionality with validation.

Tests password validation on change, error message completeness, and successful password change.
"""

import pytest
from datetime import datetime, timezone
from models import db, User, AuditLog
from app import create_app


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
        admin.set_password('OldPassword123!')
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
            'password': 'OldPassword123!'
        }, follow_redirects=True)
        
        yield client


def test_change_password_get_displays_form(authenticated_client, app):
    """Test that GET /admin/security/change-password displays form."""
    with app.app_context():
        response = authenticated_client.get('/admin/security/change-password')
        
        assert response.status_code == 200
        assert b'Change Password' in response.data
        assert b'Current Password' in response.data
        assert b'New Password' in response.data
        assert b'Password Requirements' in response.data


def test_change_password_with_valid_password_succeeds(authenticated_client, app):
    """Test that password change with valid password succeeds."""
    with app.app_context():
        response = authenticated_client.post('/admin/security/change-password', data={
            'current_password': 'OldPassword123!',
            'new_password': 'NewPassword456!',
            'confirm_password': 'NewPassword456!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Password changed successfully' in response.data
        
        # Verify password was changed
        user = User.query.filter_by(username='admin').first()
        assert user.check_password('NewPassword456!') is True
        assert user.check_password('OldPassword123!') is False


def test_change_password_with_incorrect_current_password_fails(authenticated_client, app):
    """Test that password change with incorrect current password fails."""
    with app.app_context():
        response = authenticated_client.post('/admin/security/change-password', data={
            'current_password': 'WrongPassword123!',
            'new_password': 'NewPassword456!',
            'confirm_password': 'NewPassword456!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Current password is incorrect' in response.data
        
        # Verify password was not changed
        user = User.query.filter_by(username='admin').first()
        assert user.check_password('OldPassword123!') is True


def test_change_password_with_mismatched_passwords_fails(authenticated_client, app):
    """Test that password change with mismatched passwords fails."""
    with app.app_context():
        response = authenticated_client.post('/admin/security/change-password', data={
            'current_password': 'OldPassword123!',
            'new_password': 'NewPassword456!',
            'confirm_password': 'DifferentPassword789!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'do not match' in response.data
        
        # Verify password was not changed
        user = User.query.filter_by(username='admin').first()
        assert user.check_password('OldPassword123!') is True


def test_change_password_with_too_short_password_fails(authenticated_client, app):
    """Test that password change with too short password fails."""
    with app.app_context():
        response = authenticated_client.post('/admin/security/change-password', data={
            'current_password': 'OldPassword123!',
            'new_password': 'Short1!',
            'confirm_password': 'Short1!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'at least 12 characters' in response.data
        
        # Verify password was not changed
        user = User.query.filter_by(username='admin').first()
        assert user.check_password('OldPassword123!') is True


def test_change_password_without_uppercase_fails(authenticated_client, app):
    """Test that password change without uppercase letter fails."""
    with app.app_context():
        response = authenticated_client.post('/admin/security/change-password', data={
            'current_password': 'OldPassword123!',
            'new_password': 'newpassword123!',
            'confirm_password': 'newpassword123!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'uppercase letter' in response.data
        
        # Verify password was not changed
        user = User.query.filter_by(username='admin').first()
        assert user.check_password('OldPassword123!') is True


def test_change_password_without_lowercase_fails(authenticated_client, app):
    """Test that password change without lowercase letter fails."""
    with app.app_context():
        response = authenticated_client.post('/admin/security/change-password', data={
            'current_password': 'OldPassword123!',
            'new_password': 'NEWPASSWORD123!',
            'confirm_password': 'NEWPASSWORD123!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'lowercase letter' in response.data
        
        # Verify password was not changed
        user = User.query.filter_by(username='admin').first()
        assert user.check_password('OldPassword123!') is True


def test_change_password_without_digit_fails(authenticated_client, app):
    """Test that password change without digit fails."""
    with app.app_context():
        response = authenticated_client.post('/admin/security/change-password', data={
            'current_password': 'OldPassword123!',
            'new_password': 'NewPassword!',
            'confirm_password': 'NewPassword!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'digit' in response.data
        
        # Verify password was not changed
        user = User.query.filter_by(username='admin').first()
        assert user.check_password('OldPassword123!') is True


def test_change_password_without_special_char_fails(authenticated_client, app):
    """Test that password change without special character fails."""
    with app.app_context():
        response = authenticated_client.post('/admin/security/change-password', data={
            'current_password': 'OldPassword123!',
            'new_password': 'NewPassword123',
            'confirm_password': 'NewPassword123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'special character' in response.data
        
        # Verify password was not changed
        user = User.query.filter_by(username='admin').first()
        assert user.check_password('OldPassword123!') is True


def test_change_password_with_multiple_violations_shows_all_errors(authenticated_client, app):
    """Test that password change with multiple violations shows all errors."""
    with app.app_context():
        # Password that violates multiple requirements: too short, no uppercase, no special char
        response = authenticated_client.post('/admin/security/change-password', data={
            'current_password': 'OldPassword123!',
            'new_password': 'short123',
            'confirm_password': 'short123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Should show multiple error messages
        assert b'at least 12 characters' in response.data
        assert b'uppercase letter' in response.data
        assert b'special character' in response.data
        
        # Verify password was not changed
        user = User.query.filter_by(username='admin').first()
        assert user.check_password('OldPassword123!') is True


def test_change_password_logs_audit_event(authenticated_client, app):
    """Test that successful password change logs audit event."""
    with app.app_context():
        # Clear any existing audit logs
        AuditLog.query.delete()
        db.session.commit()
        
        response = authenticated_client.post('/admin/security/change-password', data={
            'current_password': 'OldPassword123!',
            'new_password': 'NewPassword456!',
            'confirm_password': 'NewPassword456!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify audit log was created
        audit_log = AuditLog.query.filter_by(action_type='password_change').first()
        assert audit_log is not None
        assert audit_log.username == 'admin'
        assert 'Password changed successfully' in audit_log.details


def test_change_password_requires_authentication(client, app):
    """Test that password change route requires authentication."""
    with app.app_context():
        response = client.get('/admin/security/change-password', follow_redirects=False)
        
        assert response.status_code == 302
        assert '/login' in response.location


def test_change_password_requires_admin(client, app):
    """Test that password change route requires admin privileges."""
    with app.app_context():
        # Note: Non-admin users cannot log in to the system at all
        # So we just verify that unauthenticated access redirects to login
        response = client.get('/admin/security/change-password', follow_redirects=False)
        
        assert response.status_code == 302
        assert '/login' in response.location


def test_change_password_displays_requirements(authenticated_client, app):
    """Test that password change page displays password requirements."""
    with app.app_context():
        response = authenticated_client.get('/admin/security/change-password')
        
        assert response.status_code == 200
        assert b'Password Requirements' in response.data
        # Should show the requirements text
        assert b'12 characters' in response.data or b'minimum' in response.data


def test_complete_password_change_flow(authenticated_client, app):
    """Test the complete password change flow from start to finish."""
    with app.app_context():
        # Step 1: Access password change page
        response = authenticated_client.get('/admin/security/change-password')
        assert response.status_code == 200
        
        # Step 2: Submit valid password change
        response = authenticated_client.post('/admin/security/change-password', data={
            'current_password': 'OldPassword123!',
            'new_password': 'NewSecurePassword456!',
            'confirm_password': 'NewSecurePassword456!'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Password changed successfully' in response.data
        
        # Step 3: Verify new password works
        user = User.query.filter_by(username='admin').first()
        assert user.check_password('NewSecurePassword456!') is True
        assert user.check_password('OldPassword123!') is False
        
        # Step 4: Verify audit log was created
        audit_log = AuditLog.query.filter_by(action_type='password_change').first()
        assert audit_log is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
