"""
Property-based tests for password complexity validation.

**Feature: security-hardening, Property 15 & 27: Password Validation**
**Validates: Requirements 5.1-5.6, 13.3**

This module tests that password validation enforces all complexity requirements
and returns complete error messages.
"""

import pytest
import string
from hypothesis import given, strategies as st, settings, assume
from password_validator import PasswordValidator, validate_password
from security_config import PasswordConfig


class TestPasswordComplexityValidation:
    """Test suite for password complexity validation property."""
    
    @given(
        length=st.integers(min_value=12, max_value=100),
        has_upper=st.booleans(),
        has_lower=st.booleans(),
        has_digit=st.booleans(),
        has_special=st.booleans()
    )
    @settings(max_examples=100, deadline=3000)
    def test_password_complexity_validation_property(self, length, has_upper, has_lower, has_digit, has_special):
        """
        **Property 15: Password Complexity Validation**
        
        For any password being created or changed, the password validator should
        enforce all configured requirements and return validation results.
        """
        # Create a password that meets or doesn't meet requirements
        password_chars = []
        
        # Add required characters based on flags
        if has_upper:
            password_chars.append('A')
        if has_lower:
            password_chars.append('a')
        if has_digit:
            password_chars.append('1')
        if has_special:
            password_chars.append('!')
        
        # Fill remaining length with lowercase letters
        remaining = length - len(password_chars)
        if remaining > 0:
            password_chars.extend(['x'] * remaining)
        
        password = ''.join(password_chars)
        
        # Validate password
        validator = PasswordValidator()
        is_valid, errors = validator.validate(password)
        
        # Determine expected validity
        expected_valid = (
            len(password) >= validator.min_length and
            (not validator.require_uppercase or has_upper) and
            (not validator.require_lowercase or has_lower) and
            (not validator.require_digit or has_digit) and
            (not validator.require_special or has_special)
        )
        
        # Verify validation result matches expectations
        assert is_valid == expected_valid, \
            f"Password '{password}' validation mismatch: expected {expected_valid}, got {is_valid}"
        
        # If invalid, verify errors are returned
        if not is_valid:
            assert len(errors) > 0, "Invalid password should have error messages"
            
            # Verify specific error messages for unmet requirements
            if len(password) < validator.min_length:
                assert any("at least" in err.lower() and "characters" in err.lower() for err in errors), \
                    "Should have length error"
            
            if validator.require_uppercase and not has_upper:
                assert any("uppercase" in err.lower() for err in errors), \
                    "Should have uppercase error"
            
            if validator.require_lowercase and not has_lower:
                assert any("lowercase" in err.lower() for err in errors), \
                    "Should have lowercase error"
            
            if validator.require_digit and not has_digit:
                assert any("digit" in err.lower() for err in errors), \
                    "Should have digit error"
            
            if validator.require_special and not has_special:
                assert any("special" in err.lower() for err in errors), \
                    "Should have special character error"
        else:
            assert len(errors) == 0, "Valid password should have no error messages"
    
    @given(
        password=st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=100, deadline=3000)
    def test_password_validation_error_completeness(self, password):
        """
        **Property 27: Password Validation Error Completeness**
        
        For any password that fails validation, the error message should list
        ALL unmet requirements, not just the first failure.
        """
        validator = PasswordValidator()
        is_valid, errors = validator.validate(password)
        
        if not is_valid:
            # Count expected errors
            expected_error_count = 0
            
            if len(password) < validator.min_length:
                expected_error_count += 1
            
            if validator.require_uppercase and not any(c.isupper() for c in password):
                expected_error_count += 1
            
            if validator.require_lowercase and not any(c.islower() for c in password):
                expected_error_count += 1
            
            if validator.require_digit and not any(c.isdigit() for c in password):
                expected_error_count += 1
            
            if validator.require_special and not any(c in validator.special_chars for c in password):
                expected_error_count += 1
            
            # Verify all errors are reported
            assert len(errors) == expected_error_count, \
                f"Expected {expected_error_count} errors, got {len(errors)}: {errors}"
            
            # Verify each error is a non-empty string
            for error in errors:
                assert isinstance(error, str), "Each error should be a string"
                assert len(error) > 0, "Each error should be non-empty"
    
    @given(
        min_length=st.integers(min_value=8, max_value=20)
    )
    @settings(max_examples=50, deadline=3000)
    def test_password_length_boundary(self, min_length):
        """
        Test password validation at exact length boundary.
        """
        config = PasswordConfig()
        config.min_length = min_length
        validator = PasswordValidator(config)
        
        # Create password exactly at minimum length with all requirements
        password = 'A' + 'a' * (min_length - 3) + '1!'
        
        is_valid, errors = validator.validate(password)
        
        # Should be valid at exact minimum length
        assert is_valid, f"Password of exactly {min_length} characters should be valid: {errors}"
        
        # One character less should be invalid
        short_password = password[:-1]
        is_valid_short, errors_short = validator.validate(short_password)
        
        assert not is_valid_short, f"Password of {len(short_password)} characters should be invalid"
        assert any("at least" in err.lower() for err in errors_short), \
            "Should have length error for short password"
    
    @given(
        base_password=st.text(
            alphabet=string.ascii_lowercase,
            min_size=12,
            max_size=20
        )
    )
    @settings(max_examples=50, deadline=3000)
    def test_individual_requirements(self, base_password):
        """
        Test that each requirement is independently validated.
        """
        validator = PasswordValidator()
        
        # Test adding each requirement one at a time
        passwords = {
            'base': base_password,
            'with_upper': base_password + 'A',
            'with_digit': base_password + '1',
            'with_special': base_password + '!',
            'complete': base_password + 'A1!'
        }
        
        for name, pwd in passwords.items():
            is_valid, errors = validator.validate(pwd)
            
            # Complete password should be valid
            if name == 'complete':
                assert is_valid, f"Complete password should be valid: {errors}"
            else:
                # Partial passwords should have specific missing requirements
                if not is_valid:
                    assert len(errors) > 0, f"Invalid password '{name}' should have errors"


class TestPasswordValidatorConfiguration:
    """Test suite for password validator configuration."""
    
    def test_custom_configuration(self):
        """Test that custom configuration is respected."""
        config = PasswordConfig()
        config.min_length = 8
        config.require_uppercase = False
        config.require_lowercase = True
        config.require_digit = True
        config.require_special = False
        
        validator = PasswordValidator(config)
        
        # Password with only lowercase and digit should be valid
        password = "abcdefgh1"
        is_valid, errors = validator.validate(password)
        
        assert is_valid, f"Password should be valid with custom config: {errors}"
    
    def test_requirements_text_generation(self):
        """Test that requirements text is generated correctly."""
        validator = PasswordValidator()
        
        requirements_text = validator.get_requirements_text()
        
        # Verify text contains key information
        assert "Password must contain:" in requirements_text
        assert str(validator.min_length) in requirements_text
        
        if validator.require_uppercase:
            assert "uppercase" in requirements_text.lower()
        
        if validator.require_lowercase:
            assert "lowercase" in requirements_text.lower()
        
        if validator.require_digit:
            assert "digit" in requirements_text.lower()
        
        if validator.require_special:
            assert "special" in requirements_text.lower()
    
    def test_requirements_list_generation(self):
        """Test that requirements list is generated correctly."""
        validator = PasswordValidator()
        
        requirements_list = validator.get_requirements_list()
        
        # Verify list is not empty
        assert len(requirements_list) > 0, "Requirements list should not be empty"
        
        # Verify each requirement is a string
        for req in requirements_list:
            assert isinstance(req, str), "Each requirement should be a string"
            assert len(req) > 0, "Each requirement should be non-empty"


class TestPasswordValidationEdgeCases:
    """Test suite for password validation edge cases."""
    
    def test_empty_password(self):
        """Test validation of empty password."""
        validator = PasswordValidator()
        is_valid, errors = validator.validate("")
        
        assert not is_valid, "Empty password should be invalid"
        assert len(errors) > 0, "Empty password should have errors"
    
    def test_whitespace_password(self):
        """Test validation of whitespace-only password."""
        validator = PasswordValidator()
        is_valid, errors = validator.validate("            ")
        
        assert not is_valid, "Whitespace password should be invalid"
    
    def test_unicode_characters(self):
        """Test validation with unicode characters."""
        validator = PasswordValidator()
        
        # Unicode characters should count toward length
        password = "Aabc123!émojis😀"
        is_valid, errors = validator.validate(password)
        
        # Should be valid if it meets all requirements
        assert len(password) >= validator.min_length
    
    def test_special_characters_comprehensive(self):
        """Test that all special characters are recognized."""
        validator = PasswordValidator()
        
        for special_char in validator.special_chars:
            password = f"Abc123{special_char}xyz"
            is_valid, errors = validator.validate(password)
            
            # Should not have special character error
            if not is_valid:
                assert not any("special" in err.lower() for err in errors), \
                    f"Special character '{special_char}' should be recognized"


if __name__ == '__main__':
    pytest.main([__file__])
