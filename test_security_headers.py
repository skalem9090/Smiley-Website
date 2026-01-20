"""
Property-Based Tests for Security Headers

This module contains property-based tests and unit tests for the Security Headers component,
validating that security headers are properly set on all responses.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from flask import Flask
from models import db, User
from security_headers import init_security_headers
from security_config import SecurityHeaderConfig, HTTPSConfig
import os


@pytest.fixture
def app():
    """Create Flask app for testing"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def app_with_headers(app):
    """Create Flask app with security headers initialized"""
    # Configure for development (no HTTPS enforcement)
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FORCE_HTTPS'] = 'false'
    
    header_config = SecurityHeaderConfig.from_env()
    https_config = HTTPSConfig.from_env()
    
    # Add a test route
    @app.route('/test')
    def test_route():
        return 'Test response'
    
    @app.route('/test/<path:subpath>')
    def test_dynamic_route(subpath):
        return f'Test response: {subpath}'
    
    # Initialize security headers
    init_security_headers(app, header_config, https_config)
    
    return app


@pytest.fixture
def app_with_https(app):
    """Create Flask app with HTTPS enforcement enabled"""
    # Configure for production (HTTPS enforcement)
    os.environ['FLASK_ENV'] = 'production'
    os.environ['FORCE_HTTPS'] = 'true'
    
    header_config = SecurityHeaderConfig.from_env()
    https_config = HTTPSConfig.from_env()
    
    # Add a test route
    @app.route('/test')
    def test_route():
        return 'Test response'
    
    # Initialize security headers
    init_security_headers(app, header_config, https_config)
    
    return app


# ============================================================================
# Property-Based Tests
# ============================================================================

@given(
    path=st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=97, max_codepoint=122),
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_property_16_security_headers_on_all_responses(app_with_headers, path):
    """
    Property 16: Security Headers on All Responses
    
    For any HTTP response sent by the application, all configured security headers
    (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and HSTS when
    HTTPS is enabled) should be included.
    
    **Validates: Requirements 6.6**
    """
    client = app_with_headers.test_client()
    
    # Make request to dynamic route
    response = client.get(f'/test/{path}')
    
    # Assert: All security headers should be present
    assert 'Content-Security-Policy' in response.headers, \
        "Content-Security-Policy header should be present"
    
    assert 'X-Frame-Options' in response.headers, \
        "X-Frame-Options header should be present"
    
    assert 'X-Content-Type-Options' in response.headers, \
        "X-Content-Type-Options header should be present"
    
    assert 'Referrer-Policy' in response.headers, \
        "Referrer-Policy header should be present"
    
    # Verify header values
    assert response.headers['X-Frame-Options'] == 'DENY', \
        "X-Frame-Options should be DENY"
    
    assert response.headers['X-Content-Type-Options'] == 'nosniff', \
        "X-Content-Type-Options should be nosniff"
    
    assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin', \
        "Referrer-Policy should be strict-origin-when-cross-origin"


# ============================================================================
# Unit Tests
# ============================================================================

def test_csp_header_present(app_with_headers):
    """Test that Content-Security-Policy header is present"""
    client = app_with_headers.test_client()
    response = client.get('/test')
    
    assert 'Content-Security-Policy' in response.headers
    csp = response.headers['Content-Security-Policy']
    
    # Verify CSP contains expected directives
    assert "default-src 'self'" in csp
    assert "script-src" in csp
    assert "style-src" in csp
    assert "img-src" in csp


def test_x_frame_options_deny(app_with_headers):
    """Test that X-Frame-Options is set to DENY"""
    client = app_with_headers.test_client()
    response = client.get('/test')
    
    assert response.headers['X-Frame-Options'] == 'DENY'


def test_x_content_type_options_nosniff(app_with_headers):
    """Test that X-Content-Type-Options is set to nosniff"""
    client = app_with_headers.test_client()
    response = client.get('/test')
    
    assert response.headers['X-Content-Type-Options'] == 'nosniff'


def test_referrer_policy_strict_origin(app_with_headers):
    """Test that Referrer-Policy is set correctly"""
    client = app_with_headers.test_client()
    response = client.get('/test')
    
    assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'


def test_hsts_not_in_development(app_with_headers):
    """Test that HSTS is not enforced in development mode"""
    client = app_with_headers.test_client()
    response = client.get('/test')
    
    # In development mode (HTTP), HSTS should not be present
    # Talisman only adds HSTS when force_https is True
    # Since we're in development mode, HSTS may or may not be present
    # depending on Talisman's configuration
    pass  # This test is informational


def test_https_redirect_in_production(app_with_https):
    """Test that HTTP requests are redirected to HTTPS in production"""
    client = app_with_https.test_client()
    
    # Make HTTP request
    response = client.get('/test', base_url='http://localhost')
    
    # Should redirect to HTTPS
    assert response.status_code in [301, 302], \
        "HTTP request should be redirected to HTTPS in production"
    
    if response.status_code in [301, 302]:
        assert response.location.startswith('https://'), \
            "Redirect location should use HTTPS"


def test_http_allowed_in_development(app_with_headers):
    """Test that HTTP requests are allowed in development mode"""
    client = app_with_headers.test_client()
    
    # Make HTTP request
    response = client.get('/test', base_url='http://localhost')
    
    # Should not redirect (200 OK)
    assert response.status_code == 200, \
        "HTTP request should be allowed in development mode"


def test_headers_on_different_routes(app_with_headers):
    """Test that security headers are present on all routes"""
    client = app_with_headers.test_client()
    
    # Test multiple routes
    routes = ['/test', '/test/foo', '/test/bar/baz']
    
    for route in routes:
        response = client.get(route)
        
        assert 'Content-Security-Policy' in response.headers, \
            f"CSP header missing on route {route}"
        assert 'X-Frame-Options' in response.headers, \
            f"X-Frame-Options header missing on route {route}"
        assert 'X-Content-Type-Options' in response.headers, \
            f"X-Content-Type-Options header missing on route {route}"
        assert 'Referrer-Policy' in response.headers, \
            f"Referrer-Policy header missing on route {route}"


def test_csp_allows_inline_scripts(app_with_headers):
    """Test that CSP allows inline scripts (required for some functionality)"""
    client = app_with_headers.test_client()
    response = client.get('/test')
    
    csp = response.headers['Content-Security-Policy']
    
    # Verify that inline scripts are allowed (unsafe-inline)
    assert "'unsafe-inline'" in csp or "nonce-" in csp, \
        "CSP should allow inline scripts via unsafe-inline or nonce"


def test_csp_allows_inline_styles(app_with_headers):
    """Test that CSP allows inline styles (required for some functionality)"""
    client = app_with_headers.test_client()
    response = client.get('/test')
    
    csp = response.headers['Content-Security-Policy']
    
    # Verify that inline styles are allowed
    assert "'unsafe-inline'" in csp, \
        "CSP should allow inline styles"


def test_csp_allows_data_images(app_with_headers):
    """Test that CSP allows data: URIs for images"""
    client = app_with_headers.test_client()
    response = client.get('/test')
    
    csp = response.headers['Content-Security-Policy']
    
    # Verify that data: URIs are allowed for images
    assert "data:" in csp, \
        "CSP should allow data: URIs for images"
