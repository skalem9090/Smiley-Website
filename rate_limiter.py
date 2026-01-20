"""
Rate Limiter Component

This module provides rate limiting functionality to prevent brute force attacks
by limiting the number of requests from a single IP address.
"""

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from security_config import RateLimiterConfig


def init_rate_limiter(app: Flask, config: RateLimiterConfig = None) -> Limiter:
    """
    Initialize rate limiter with Flask app.
    
    Args:
        app: Flask application instance
        config: RateLimiterConfig instance, defaults to loading from environment
        
    Returns:
        Configured Limiter instance
    """
    if config is None:
        config = RateLimiterConfig.from_env()
    
    # Initialize Flask-Limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=config.storage_uri,
        default_limits=[],  # No default limits, apply per-route
        headers_enabled=True,  # Include rate limit headers in responses
        swallow_errors=False  # Raise errors for debugging
    )
    
    # Store configuration on app for access in routes
    app.config['RATE_LIMIT_LOGIN'] = config.login_limit
    app.config['RATE_LIMIT_ADMIN'] = config.admin_limit
    app.config['RATE_LIMIT_PASSWORD_RESET'] = config.password_reset_limit
    
    return limiter


def get_rate_limit_config(app: Flask) -> dict:
    """
    Get rate limit configuration from app.
    
    Args:
        app: Flask application instance
        
    Returns:
        Dictionary with rate limit configurations
    """
    return {
        'login': app.config.get('RATE_LIMIT_LOGIN', '5 per minute'),
        'admin': app.config.get('RATE_LIMIT_ADMIN', '10 per minute'),
        'password_reset': app.config.get('RATE_LIMIT_PASSWORD_RESET', '3 per hour')
    }
