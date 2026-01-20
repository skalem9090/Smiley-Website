"""
Password Validator Component

This module provides password complexity validation to enforce strong
password requirements and prevent weak passwords.
"""

from typing import Tuple, List
from security_config import PasswordConfig


class PasswordValidator:
    """Validates password complexity requirements"""
    
    def __init__(self, config: PasswordConfig = None):
        """
        Initialize password validator with configuration.
        
        Args:
            config: PasswordConfig instance, defaults to loading from environment
        """
        if config is None:
            config = PasswordConfig.from_env()
        
        self.min_length = config.min_length
        self.require_uppercase = config.require_uppercase
        self.require_lowercase = config.require_lowercase
        self.require_digit = config.require_digit
        self.require_special = config.require_special
        self.special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    def validate(self, password: str) -> Tuple[bool, List[str]]:
        """
        Validate password against all configured requirements.
        
        Args:
            password: Password string to validate
            
        Returns:
            Tuple of (is_valid, list_of_error_messages)
            - is_valid: True if password meets all requirements, False otherwise
            - list_of_error_messages: List of strings describing unmet requirements
        """
        errors = []
        
        # Check minimum length
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        
        # Check for uppercase letter
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter (A-Z)")
        
        # Check for lowercase letter
        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter (a-z)")
        
        # Check for digit
        if self.require_digit and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit (0-9)")
        
        # Check for special character
        if self.require_special and not any(c in self.special_chars for c in password):
            errors.append(f"Password must contain at least one special character ({self.special_chars})")
        
        return (len(errors) == 0, errors)
    
    def get_requirements_text(self) -> str:
        """
        Get human-readable description of password requirements.
        
        Returns:
            String describing all password requirements
        """
        requirements = []
        
        requirements.append(f"At least {self.min_length} characters long")
        
        if self.require_uppercase:
            requirements.append("At least one uppercase letter (A-Z)")
        
        if self.require_lowercase:
            requirements.append("At least one lowercase letter (a-z)")
        
        if self.require_digit:
            requirements.append("At least one digit (0-9)")
        
        if self.require_special:
            requirements.append(f"At least one special character ({self.special_chars})")
        
        return "Password must contain:\n" + "\n".join(f"• {req}" for req in requirements)
    
    def get_requirements_list(self) -> List[str]:
        """
        Get list of password requirements.
        
        Returns:
            List of requirement strings
        """
        requirements = []
        
        requirements.append(f"At least {self.min_length} characters long")
        
        if self.require_uppercase:
            requirements.append("At least one uppercase letter (A-Z)")
        
        if self.require_lowercase:
            requirements.append("At least one lowercase letter (a-z)")
        
        if self.require_digit:
            requirements.append("At least one digit (0-9)")
        
        if self.require_special:
            requirements.append(f"At least one special character ({self.special_chars})")
        
        return requirements


# Convenience function for quick validation
def validate_password(password: str, config: PasswordConfig = None) -> Tuple[bool, List[str]]:
    """
    Validate a password against configured requirements.
    
    Args:
        password: Password string to validate
        config: Optional PasswordConfig instance
        
    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    validator = PasswordValidator(config)
    return validator.validate(password)
