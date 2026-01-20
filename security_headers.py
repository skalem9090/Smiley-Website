"""
Security Headers Module

This module initializes Flask-Talisman for comprehensive security header management
and HTTPS enforcement.
"""

from flask import Flask
from flask_talisman import Talisman
from security_config import SecurityHeaderConfig, HTTPSConfig


def init_security_headers(app: Flask, header_config: SecurityHeaderConfig, https_config: HTTPSConfig) -> Talisman:
    """
    Initialize security headers with Flask-Talisman.
    
    Args:
        app: Flask application instance
        header_config: SecurityHeaderConfig instance with header settings
        https_config: HTTPSConfig instance with HTTPS enforcement settings
    
    Returns:
        Talisman instance
    """
    # Determine if HTTPS should be enforced
    force_https = https_config.should_enforce()
    
    # Configure Content Security Policy
    csp = header_config.content_security_policy
    
    # Initialize Talisman with all security headers
    talisman = Talisman(
        app,
        force_https=force_https,
        strict_transport_security=header_config.strict_transport_security,
        strict_transport_security_max_age=header_config.hsts_max_age,
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src'],
        frame_options=header_config.x_frame_options,
        x_content_type_options=header_config.x_content_type_options,
        referrer_policy=header_config.referrer_policy,
        force_https_permanent=False,  # Use 302 redirects instead of 301 for flexibility
    )
    
    return talisman
