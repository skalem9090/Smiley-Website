"""
Security Error Classes

This module defines custom exception classes for security-related errors
to provide clear, consistent error handling and user feedback.
"""


class SecurityError(Exception):
    """Base class for all security-related errors."""
    
    def __init__(self, message: str, status_code: int = 400):
        """
        Initialize security error.
        
        Args:
            message: Error message to display to user
            status_code: HTTP status code to return
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class RateLimitExceeded(SecurityError):
    """Raised when a client exceeds the rate limit."""
    
    def __init__(self, retry_after: int):
        """
        Initialize rate limit error.
        
        Args:
            retry_after: Number of seconds until the client can retry
        """
        minutes = retry_after // 60
        if minutes > 0:
            message = f"Too many attempts. Please try again in {minutes} minute(s)."
        else:
            message = f"Too many attempts. Please try again in {retry_after} second(s)."
        
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class AccountLocked(SecurityError):
    """Raised when an account is locked due to failed login attempts."""
    
    def __init__(self, unlock_time_minutes: int):
        """
        Initialize account locked error.
        
        Args:
            unlock_time_minutes: Number of minutes until the account is unlocked
        """
        message = f"Account locked due to multiple failed login attempts. Try again in {unlock_time_minutes} minute(s)."
        super().__init__(message, status_code=403)
        self.unlock_time_minutes = unlock_time_minutes


class InvalidTOTP(SecurityError):
    """Raised when an invalid TOTP code is provided."""
    
    def __init__(self):
        """Initialize invalid TOTP error."""
        message = "Invalid authentication code. Please try again."
        super().__init__(message, status_code=401)


class SessionExpired(SecurityError):
    """Raised when a user's session has expired."""
    
    def __init__(self):
        """Initialize session expired error."""
        message = "Your session has expired. Please log in again."
        super().__init__(message, status_code=401)


class PasswordValidationError(SecurityError):
    """Raised when a password fails validation."""
    
    def __init__(self, errors: list):
        """
        Initialize password validation error.
        
        Args:
            errors: List of validation error messages
        """
        # Join all errors into a single message
        message = "Password does not meet requirements:\n" + "\n".join(f"- {error}" for error in errors)
        super().__init__(message, status_code=400)
        self.errors = errors
