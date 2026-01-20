"""
Security Configuration Module

This module provides configuration classes for all security features,
loading settings from environment variables with sensible defaults.
"""

import os
from typing import Optional


class RateLimiterConfig:
    """Configuration for rate limiting"""
    
    def __init__(self):
        self.login_limit: str = os.getenv('RATE_LIMIT_LOGIN', '5 per minute')
        self.admin_limit: str = os.getenv('RATE_LIMIT_ADMIN', '10 per minute')
        self.password_reset_limit: str = os.getenv('RATE_LIMIT_PASSWORD_RESET', '3 per hour')
        self.storage_uri: str = os.getenv('RATE_LIMIT_STORAGE_URI', 'memory://')
    
    @classmethod
    def from_env(cls) -> 'RateLimiterConfig':
        """Load configuration from environment variables"""
        return cls()


class LockoutConfig:
    """Configuration for account lockout"""
    
    def __init__(self):
        self.threshold: int = int(os.getenv('ACCOUNT_LOCKOUT_THRESHOLD', '5'))
        self.duration: int = int(os.getenv('ACCOUNT_LOCKOUT_DURATION', '15'))  # minutes
    
    @classmethod
    def from_env(cls) -> 'LockoutConfig':
        """Load configuration from environment variables"""
        return cls()


class SessionConfig:
    """Configuration for session management"""
    
    def __init__(self):
        self.timeout: int = int(os.getenv('SESSION_TIMEOUT', '120'))  # minutes
    
    @classmethod
    def from_env(cls) -> 'SessionConfig':
        """Load configuration from environment variables"""
        return cls()


class PasswordConfig:
    """Configuration for password validation"""
    
    def __init__(self):
        self.min_length: int = int(os.getenv('PASSWORD_MIN_LENGTH', '12'))
        self.require_uppercase: bool = os.getenv('PASSWORD_REQUIRE_UPPERCASE', 'true').lower() == 'true'
        self.require_lowercase: bool = os.getenv('PASSWORD_REQUIRE_LOWERCASE', 'true').lower() == 'true'
        self.require_digit: bool = os.getenv('PASSWORD_REQUIRE_DIGIT', 'true').lower() == 'true'
        self.require_special: bool = os.getenv('PASSWORD_REQUIRE_SPECIAL', 'true').lower() == 'true'
    
    @classmethod
    def from_env(cls) -> 'PasswordConfig':
        """Load configuration from environment variables"""
        return cls()


class SecurityHeaderConfig:
    """Configuration for security headers"""
    
    def __init__(self):
        self.force_https: bool = os.getenv('FORCE_HTTPS', 'true').lower() == 'true'
        self.strict_transport_security: bool = True
        self.hsts_max_age: int = 31536000  # 1 year
        self.content_security_policy: dict = {
            'default-src': "'self'",
            'script-src': ["'self'", "'unsafe-inline'"],
            'style-src': ["'self'", "'unsafe-inline'"],
            'img-src': ["'self'", "data:", "https:"],
            'font-src': ["'self'", "data:"],
        }
        self.x_frame_options: str = "DENY"
        self.x_content_type_options: bool = True
        self.referrer_policy: str = "strict-origin-when-cross-origin"
    
    @classmethod
    def from_env(cls) -> 'SecurityHeaderConfig':
        """Load configuration from environment variables"""
        return cls()


class HTTPSConfig:
    """Configuration for HTTPS enforcement"""
    
    def __init__(self):
        self.force_https: bool = os.getenv('FORCE_HTTPS', 'true').lower() == 'true'
        self.environment: str = os.getenv('FLASK_ENV', 'production')
    
    @classmethod
    def from_env(cls) -> 'HTTPSConfig':
        """Load configuration from environment variables"""
        return cls()
    
    def should_enforce(self) -> bool:
        """Determine if HTTPS should be enforced"""
        return self.force_https and self.environment == 'production'


class TwoFactorConfig:
    """Configuration for two-factor authentication"""
    
    def __init__(self):
        self.enabled: bool = os.getenv('ENABLE_2FA', 'true').lower() == 'true'
        self.issuer_name: str = os.getenv('2FA_ISSUER_NAME', 'Smileys Blog')
    
    @classmethod
    def from_env(cls) -> 'TwoFactorConfig':
        """Load configuration from environment variables"""
        return cls()


class SecurityConfig:
    """Master security configuration"""
    
    def __init__(self):
        self.rate_limiter = RateLimiterConfig.from_env()
        self.lockout = LockoutConfig.from_env()
        self.session = SessionConfig.from_env()
        self.password = PasswordConfig.from_env()
        self.security_headers = SecurityHeaderConfig.from_env()
        self.https = HTTPSConfig.from_env()
        self.two_factor = TwoFactorConfig.from_env()
    
    @classmethod
    def from_env(cls) -> 'SecurityConfig':
        """Load all security configuration from environment variables"""
        return cls()
