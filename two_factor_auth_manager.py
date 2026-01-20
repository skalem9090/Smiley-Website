"""
Two-Factor Authentication Manager Component

This module manages TOTP-based two-factor authentication for enhanced
account security.
"""

from typing import Tuple, List
from flask_sqlalchemy import SQLAlchemy
from models import User, TwoFactorAuth
from werkzeug.security import generate_password_hash, check_password_hash
import pyotp
import secrets
import json
from datetime import datetime, timezone


class TwoFactorAuthManager:
    """Manages TOTP-based two-factor authentication"""
    
    def __init__(self, db: SQLAlchemy):
        """
        Initialize two-factor authentication manager.
        
        Args:
            db: SQLAlchemy database instance
        """
        self.db = db
    
    def generate_secret(self, user: User) -> str:
        """
        Generate a new TOTP secret for user.
        
        Args:
            user: User model instance
            
        Returns:
            Base32-encoded TOTP secret
        """
        # Generate a random base32 secret
        secret = pyotp.random_base32()
        
        # Create or update TwoFactorAuth record
        two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
        if two_fa is None:
            two_fa = TwoFactorAuth(
                user_id=user.id,
                secret=secret,
                enabled=False
            )
            self.db.session.add(two_fa)
        else:
            two_fa.secret = secret
        
        self.db.session.commit()
        return secret
    
    def get_provisioning_uri(self, user: User, issuer: str = "Smileys Blog") -> str:
        """
        Get provisioning URI for QR code generation.
        
        Args:
            user: User model instance
            issuer: Name of the issuing organization
            
        Returns:
            Provisioning URI string for QR code
        """
        two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
        if two_fa is None or two_fa.secret is None:
            raise ValueError("No 2FA secret found for user. Call generate_secret() first.")
        
        totp = pyotp.TOTP(two_fa.secret)
        return totp.provisioning_uri(name=user.username, issuer_name=issuer)
    
    def verify_totp(self, user: User, token: str) -> bool:
        """
        Verify a TOTP token.
        
        Args:
            user: User model instance
            token: 6-digit TOTP code
            
        Returns:
            True if token is valid, False otherwise
        """
        two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
        if two_fa is None or two_fa.secret is None:
            return False
        
        totp = pyotp.TOTP(two_fa.secret)
        # Verify with a window of 1 (allows for slight time drift)
        is_valid = totp.verify(token, valid_window=1)
        
        if is_valid and two_fa.enabled:
            # Update last_used timestamp
            two_fa.last_used = datetime.now(timezone.utc)
            self.db.session.commit()
        
        return is_valid
    
    def enable_2fa(self, user: User, token: str) -> Tuple[bool, List[str]]:
        """
        Enable 2FA after verifying initial token, return backup codes.
        
        Args:
            user: User model instance
            token: 6-digit TOTP code for verification
            
        Returns:
            Tuple of (success: bool, backup_codes: List[str])
        """
        # Verify the token first
        if not self.verify_totp(user, token):
            return (False, [])
        
        # Generate backup codes
        backup_codes = self.generate_backup_codes(count=10)
        
        # Hash backup codes before storing
        hashed_codes = [generate_password_hash(code) for code in backup_codes]
        
        # Enable 2FA
        two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
        if two_fa is None:
            return (False, [])
        
        two_fa.enabled = True
        two_fa.backup_codes = json.dumps(hashed_codes)
        self.db.session.commit()
        
        return (True, backup_codes)
    
    def disable_2fa(self, user: User, password: str, token: str) -> bool:
        """
        Disable 2FA after verifying password and token.
        
        Args:
            user: User model instance
            password: User's current password
            token: 6-digit TOTP code
            
        Returns:
            True if 2FA was disabled, False otherwise
        """
        # Verify password
        if not user.check_password(password):
            return False
        
        # Verify TOTP token
        if not self.verify_totp(user, token):
            return False
        
        # Disable 2FA
        two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
        if two_fa is None:
            return False
        
        two_fa.enabled = False
        two_fa.backup_codes = None
        self.db.session.commit()
        
        return True
    
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """
        Generate backup codes for account recovery.
        
        Args:
            count: Number of backup codes to generate
            
        Returns:
            List of backup codes (8 characters each)
        """
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = secrets.token_hex(4).upper()  # 8 hex characters
            codes.append(code)
        return codes
    
    def verify_backup_code(self, user: User, code: str) -> bool:
        """
        Verify and consume a backup code.
        
        Args:
            user: User model instance
            code: Backup code to verify
            
        Returns:
            True if code is valid and consumed, False otherwise
        """
        two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
        if two_fa is None or not two_fa.enabled or two_fa.backup_codes is None:
            return False
        
        try:
            hashed_codes = json.loads(two_fa.backup_codes)
        except (json.JSONDecodeError, TypeError):
            return False
        
        # Check each hashed code
        for i, hashed_code in enumerate(hashed_codes):
            if check_password_hash(hashed_code, code):
                # Remove the used code
                hashed_codes.pop(i)
                two_fa.backup_codes = json.dumps(hashed_codes)
                two_fa.last_used = datetime.now(timezone.utc)
                self.db.session.commit()
                return True
        
        return False
    
    def is_enabled(self, user: User) -> bool:
        """
        Check if 2FA is enabled for user.
        
        Args:
            user: User model instance
            
        Returns:
            True if 2FA is enabled, False otherwise
        """
        two_fa = TwoFactorAuth.query.filter_by(user_id=user.id).first()
        return two_fa is not None and two_fa.enabled
