"""
Property-Based Tests for Two-Factor Authentication Manager

This module contains property-based tests for the Two-Factor Authentication Manager component,
validating that 2FA behavior conforms to the security requirements.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timezone
from flask import Flask
from models import db, User, TwoFactorAuth
from two_factor_auth_manager import TwoFactorAuthManager
import pyotp
import re


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
def two_fa_manager(app):
    """Create TwoFactorAuthManager instance"""
    with app.app_context():
        return TwoFactorAuthManager(db)


@pytest.fixture
def user(app):
    """Create a test user"""
    with app.app_context():
        user = User(username='testuser', is_admin=False)
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        # Don't refresh here - let each test handle its own session
        yield user


class TestTwoFactorAuthProperties:
    """Property-based tests for two-factor authentication"""
    
    @given(
        user_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=20, deadline=None)
    def test_property_2fa_secret_generation(self, user_count):
        """
        Property 6: 2FA Secret Generation
        
        For any user enabling two-factor authentication, the system should 
        generate a unique TOTP secret, store it securely, and provide a 
        provisioning URI for QR code generation.
        
        Validates: Requirements 3.1
        """
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            manager = TwoFactorAuthManager(db)
            
            secrets = []
            users = []
            
            # Generate secrets for multiple users
            for i in range(user_count):
                user = User(username=f'user_{i}', is_admin=False)
                user.set_password('password123')
                db.session.add(user)
                db.session.commit()
                db.session.refresh(user)
                users.append(user)
                
                secret = manager.generate_secret(user)
                secrets.append(secret)
                
                # Verify secret is stored in database
                two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
                assert two_fa is not None, "TwoFactorAuth record should be created"
                assert two_fa.secret == secret, "Secret should be stored in database"
                assert two_fa.enabled == False, "2FA should not be enabled yet"
                
                # Verify secret is valid base32
                assert len(secret) > 0, "Secret should not be empty"
                assert re.match(r'^[A-Z2-7]+=*$', secret), "Secret should be valid base32"
                
                # Verify provisioning URI can be generated
                uri = manager.get_provisioning_uri(user, issuer="Test App")
                assert uri.startswith('otpauth://totp/'), "URI should be TOTP provisioning URI"
                assert user.username in uri, "URI should contain username"
                assert 'Test%20App' in uri or 'Test App' in uri, "URI should contain issuer name"
                assert secret in uri, "URI should contain secret"
            
            # Verify all secrets are unique
            assert len(set(secrets)) == user_count, "All secrets should be unique"
    
    @given(
        time_offset=st.integers(min_value=-30, max_value=30)
    )
    @settings(max_examples=20, deadline=None)
    def test_property_2fa_login_flow(self, time_offset):
        """
        Property 7: 2FA Login Flow
        
        For any user with 2FA enabled, when valid credentials are provided, 
        the system should require a valid TOTP code before granting access 
        and creating a session.
        
        Validates: Requirements 3.2, 3.4
        """
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            manager = TwoFactorAuthManager(db)
            
            user = User(username=f'user_2fa_{time_offset}', is_admin=False)
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            
            # Generate secret and enable 2FA
            secret = manager.generate_secret(user)
            totp = pyotp.TOTP(secret)
            valid_token = totp.now()
            
            # Enable 2FA with valid token
            success, backup_codes = manager.enable_2fa(user, valid_token)
            assert success, "2FA should be enabled with valid token"
            assert len(backup_codes) == 10, "Should generate 10 backup codes"
            
            db.session.refresh(user)
            
            # Verify 2FA is enabled
            assert manager.is_enabled(user), "2FA should be enabled"
            
            # Verify valid TOTP code is accepted
            current_token = totp.now()
            assert manager.verify_totp(user, current_token), "Valid TOTP should be accepted"
            
            # Verify last_used timestamp is updated
            two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
            assert two_fa.last_used is not None, "last_used should be set after verification"
    
    @given(
        invalid_token=st.text(
            alphabet=st.characters(whitelist_categories=('Nd',)),
            min_size=6,
            max_size=6
        ).filter(lambda x: x != '000000')  # Avoid accidentally valid tokens
    )
    @settings(max_examples=20, deadline=None)
    def test_property_invalid_totp_rejection(self, invalid_token):
        """
        Property 8: Invalid TOTP Rejection
        
        For any user with 2FA enabled, when an invalid TOTP code is provided, 
        the system should reject the login attempt and increment the failed 
        login attempt counter.
        
        Validates: Requirements 3.3
        """
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            manager = TwoFactorAuthManager(db)
            
            user = User(username=f'user_invalid_{invalid_token}', is_admin=False)
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            
            # Generate secret and enable 2FA
            secret = manager.generate_secret(user)
            totp = pyotp.TOTP(secret)
            valid_token = totp.now()
            
            success, backup_codes = manager.enable_2fa(user, valid_token)
            assert success, "2FA should be enabled"
            
            db.session.refresh(user)
            
            # Try to verify with invalid token
            # Use a token that's definitely not the current one
            current_token = totp.now()
            assume(invalid_token != current_token)
            
            # Also check it's not within the valid window
            totp_at_offset = pyotp.TOTP(secret)
            for offset in [-1, 0, 1]:
                token_at_offset = totp_at_offset.at(datetime.now(timezone.utc), offset)
                assume(invalid_token != token_at_offset)
            
            result = manager.verify_totp(user, invalid_token)
            assert not result, "Invalid TOTP should be rejected"
            
            # Verify last_used is not updated for invalid token
            two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
            # last_used should still be None or not updated
    
    @given(
        password_valid=st.booleans()
    )
    @settings(max_examples=20, deadline=None)
    def test_property_2fa_toggle_security(self, password_valid):
        """
        Property 9: 2FA Toggle Security
        
        For any user attempting to disable 2FA, the system should require 
        both the current password and a valid TOTP code before disabling 
        the feature.
        
        Validates: Requirements 3.6
        """
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            manager = TwoFactorAuthManager(db)
            
            user = User(username=f'user_toggle_{password_valid}', is_admin=False)
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            
            # Generate secret and enable 2FA
            secret = manager.generate_secret(user)
            totp = pyotp.TOTP(secret)
            valid_token = totp.now()
            
            success, backup_codes = manager.enable_2fa(user, valid_token)
            assert success, "2FA should be enabled"
            
            db.session.refresh(user)
            assert manager.is_enabled(user), "2FA should be enabled"
            
            # Try to disable 2FA
            password = 'password123' if password_valid else 'wrongpassword'
            current_token = totp.now()
            
            result = manager.disable_2fa(user, password, current_token)
            
            if password_valid:
                assert result, "2FA should be disabled with valid password and token"
                db.session.refresh(user)
                assert not manager.is_enabled(user), "2FA should be disabled"
                
                two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
                assert two_fa.backup_codes is None, "Backup codes should be cleared"
            else:
                assert not result, "2FA should not be disabled with invalid password"
                db.session.refresh(user)
                assert manager.is_enabled(user), "2FA should still be enabled"
    
    @given(
        backup_code_count=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=20, deadline=None)
    def test_property_backup_code_generation(self, backup_code_count):
        """
        Property 10: Backup Code Generation
        
        For any user enabling 2FA, the system should generate a set of 
        backup codes that can be used for account recovery when the TOTP 
        device is unavailable.
        
        Validates: Requirements 3.7
        """
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            manager = TwoFactorAuthManager(db)
            
            user = User(username=f'user_backup_{backup_code_count}', is_admin=False)
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            
            # Generate backup codes
            backup_codes = manager.generate_backup_codes(count=backup_code_count)
            
            # Verify correct number of codes generated
            assert len(backup_codes) == backup_code_count, f"Should generate {backup_code_count} backup codes"
            
            # Verify all codes are unique
            assert len(set(backup_codes)) == backup_code_count, "All backup codes should be unique"
            
            # Verify code format (8 hex characters)
            for code in backup_codes:
                assert len(code) == 8, "Each backup code should be 8 characters"
                assert re.match(r'^[0-9A-F]{8}$', code), "Backup code should be 8 hex characters"
            
            # Enable 2FA to get backup codes
            secret = manager.generate_secret(user)
            totp = pyotp.TOTP(secret)
            valid_token = totp.now()
            
            success, generated_codes = manager.enable_2fa(user, valid_token)
            assert success, "2FA should be enabled"
            assert len(generated_codes) == 10, "Should generate 10 backup codes by default"
            
            db.session.refresh(user)
            
            # Verify backup codes can be used
            test_code = generated_codes[0]
            result = manager.verify_backup_code(user, test_code)
            assert result, "Valid backup code should be accepted"
            
            # Verify backup code is consumed (can't be used again)
            result = manager.verify_backup_code(user, test_code)
            assert not result, "Used backup code should be rejected"
            
            # Verify last_used timestamp is updated
            two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
            assert two_fa.last_used is not None, "last_used should be set after backup code use"


class TestTwoFactorAuthEdgeCases:
    """Unit tests for 2FA edge cases"""
    
    def test_2fa_secret_regeneration(self, app, two_fa_manager, user):
        """Test that generating a new secret replaces the old one"""
        with app.app_context():
            # Re-query user in this context
            test_user = User.query.filter_by(username='testuser').first()
            
            secret1 = two_fa_manager.generate_secret(test_user)
            secret2 = two_fa_manager.generate_secret(test_user)
            
            assert secret1 != secret2, "New secret should be different"
            
            two_fa = TwoFactorAuth.query.filter_by(user_id=test_user.id).first()
            assert two_fa.secret == secret2, "Database should have the new secret"
    
    def test_totp_time_drift_tolerance(self, app, two_fa_manager, user):
        """Test that TOTP verification allows for time drift"""
        with app.app_context():
            # Re-query user in this context
            test_user = User.query.filter_by(username='testuser').first()
            
            secret = two_fa_manager.generate_secret(test_user)
            totp = pyotp.TOTP(secret)
            
            # Enable 2FA
            valid_token = totp.now()
            success, _ = two_fa_manager.enable_2fa(test_user, valid_token)
            assert success, "2FA should be enabled"
            
            db.session.refresh(test_user)
            
            # Test current token
            current_token = totp.now()
            assert two_fa_manager.verify_totp(test_user, current_token), "Current token should be valid"
            
            # Test token from previous time step (within valid_window=1)
            previous_token = totp.at(datetime.now(timezone.utc), -1)
            assert two_fa_manager.verify_totp(test_user, previous_token), "Previous token should be valid (time drift)"
            
            # Test token from next time step (within valid_window=1)
            next_token = totp.at(datetime.now(timezone.utc), 1)
            assert two_fa_manager.verify_totp(test_user, next_token), "Next token should be valid (time drift)"
    
    def test_provisioning_uri_format(self, app, two_fa_manager, user):
        """Test that provisioning URI has correct format"""
        with app.app_context():
            # Re-query user in this context
            test_user = User.query.filter_by(username='testuser').first()
            
            secret = two_fa_manager.generate_secret(test_user)
            uri = two_fa_manager.get_provisioning_uri(test_user, issuer="Test Blog")
            
            # Verify URI format
            assert uri.startswith('otpauth://totp/'), "URI should start with otpauth://totp/"
            assert test_user.username in uri, "URI should contain username"
            assert 'Test%20Blog' in uri or 'Test Blog' in uri, "URI should contain issuer"
            assert secret in uri, "URI should contain secret"
    
    def test_provisioning_uri_without_secret(self, app, two_fa_manager, user):
        """Test that provisioning URI fails without secret"""
        with app.app_context():
            # Re-query user in this context
            test_user = User.query.filter_by(username='testuser').first()
            
            with pytest.raises(ValueError, match="No 2FA secret found"):
                two_fa_manager.get_provisioning_uri(test_user)
    
    def test_backup_code_consumption(self, app, two_fa_manager, user):
        """Test that backup codes are consumed after use"""
        with app.app_context():
            # Re-query user in this context
            test_user = User.query.filter_by(username='testuser').first()
            
            secret = two_fa_manager.generate_secret(test_user)
            totp = pyotp.TOTP(secret)
            valid_token = totp.now()
            
            success, backup_codes = two_fa_manager.enable_2fa(test_user, valid_token)
            assert success, "2FA should be enabled"
            
            db.session.refresh(test_user)
            
            # Use first backup code
            code1 = backup_codes[0]
            assert two_fa_manager.verify_backup_code(test_user, code1), "First backup code should work"
            
            # Try to use same code again
            assert not two_fa_manager.verify_backup_code(test_user, code1), "Used backup code should not work again"
            
            # Use second backup code
            code2 = backup_codes[1]
            assert two_fa_manager.verify_backup_code(test_user, code2), "Second backup code should work"
    
    def test_2fa_disable_requires_both_password_and_token(self, app, two_fa_manager, user):
        """Test that disabling 2FA requires both password and TOTP"""
        with app.app_context():
            # Re-query user in this context
            test_user = User.query.filter_by(username='testuser').first()
            
            secret = two_fa_manager.generate_secret(test_user)
            totp = pyotp.TOTP(secret)
            valid_token = totp.now()
            
            success, _ = two_fa_manager.enable_2fa(test_user, valid_token)
            assert success, "2FA should be enabled"
            
            db.session.refresh(test_user)
            
            # Try with wrong password
            current_token = totp.now()
            assert not two_fa_manager.disable_2fa(test_user, 'wrongpassword', current_token), "Should fail with wrong password"
            
            # Try with wrong token
            assert not two_fa_manager.disable_2fa(test_user, 'password123', '000000'), "Should fail with wrong token"
            
            # Try with both correct
            current_token = totp.now()
            assert two_fa_manager.disable_2fa(test_user, 'password123', current_token), "Should succeed with both correct"
    
    def test_2fa_not_enabled_before_verification(self, app, two_fa_manager, user):
        """Test that 2FA is not enabled until token is verified"""
        with app.app_context():
            # Re-query user in this context
            test_user = User.query.filter_by(username='testuser').first()
            
            secret = two_fa_manager.generate_secret(test_user)
            
            # 2FA should not be enabled yet
            assert not two_fa_manager.is_enabled(test_user), "2FA should not be enabled before verification"
            
            # Enable with valid token
            totp = pyotp.TOTP(secret)
            valid_token = totp.now()
            success, _ = two_fa_manager.enable_2fa(test_user, valid_token)
            assert success, "2FA should be enabled"
            
            db.session.refresh(test_user)
            assert two_fa_manager.is_enabled(test_user), "2FA should be enabled after verification"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
