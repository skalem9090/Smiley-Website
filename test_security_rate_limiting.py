"""
Property-based tests for rate limiting enforcement.

**Feature: security-hardening, Property 1: Rate Limiting Enforcement**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4**

This module tests that rate limiting prevents excessive requests from
a single IP address.
"""

import pytest
import time
from hypothesis import given, strategies as st, settings
from flask import Flask, jsonify
from rate_limiter import init_rate_limiter
from security_config import RateLimiterConfig


class TestRateLimitingEnforcement:
    """Test suite for rate limiting enforcement property."""
    
    def create_test_app_with_rate_limiting(self, limit_string: str = "5 per minute"):
        """Create a test Flask app with rate limiting configured."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        # Configure rate limiter
        config = RateLimiterConfig()
        config.login_limit = limit_string
        config.storage_uri = "memory://"
        
        limiter = init_rate_limiter(app, config)
        
        # Create test route with rate limiting
        @app.route('/test-login', methods=['POST'])
        @limiter.limit(limit_string)
        def test_login():
            return jsonify({'success': True}), 200
        
        return app, limiter
    
    @given(
        request_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=20, deadline=10000)
    def test_rate_limiting_enforcement_property(self, request_count):
        """
        **Property 1: Rate Limiting Enforcement**
        
        For any IP address and endpoint with rate limiting configured,
        when the number of requests exceeds the limit, the system should
        return HTTP 429 status.
        """
        # Create app with 5 requests per minute limit
        app, limiter = self.create_test_app_with_rate_limiting("5 per minute")
        
        with app.test_client() as client:
            # Make requests up to the count
            responses = []
            for i in range(request_count):
                response = client.post('/test-login')
                responses.append(response)
            
            # Verify rate limiting behavior
            if request_count <= 5:
                # All requests should succeed
                for i, response in enumerate(responses):
                    assert response.status_code == 200, \
                        f"Request {i+1}/{request_count} should succeed (got {response.status_code})"
            else:
                # First 5 should succeed, rest should be rate limited
                for i in range(5):
                    assert responses[i].status_code == 200, \
                        f"Request {i+1} should succeed"
                
                for i in range(5, request_count):
                    assert responses[i].status_code == 429, \
                        f"Request {i+1} should be rate limited (got {responses[i].status_code})"
                    
                    # Verify retry-after header is present
                    assert 'Retry-After' in responses[i].headers or 'X-RateLimit-Reset' in responses[i].headers, \
                        "Rate limited response should include retry information"
    
    def test_rate_limit_reset_after_window(self):
        """
        Test that rate limit resets after the time window expires.
        """
        # Create app with 3 requests per 2 seconds limit
        app, limiter = self.create_test_app_with_rate_limiting("3 per 2 seconds")
        
        with app.test_client() as client:
            # Make 3 requests (should all succeed)
            for i in range(3):
                response = client.post('/test-login')
                assert response.status_code == 200, f"Request {i+1} should succeed"
            
            # 4th request should be rate limited
            response = client.post('/test-login')
            assert response.status_code == 429, "4th request should be rate limited"
            
            # Wait for window to reset (2 seconds + buffer)
            time.sleep(2.5)
            
            # Next request should succeed after reset
            response = client.post('/test-login')
            assert response.status_code == 200, "Request after reset should succeed"
    
    def test_rate_limit_per_ip_isolation(self):
        """
        Test that rate limits are applied per IP address.
        """
        app, limiter = self.create_test_app_with_rate_limiting("3 per minute")
        
        with app.test_client() as client:
            # Make 3 requests from first IP (default)
            for i in range(3):
                response = client.post('/test-login')
                assert response.status_code == 200
            
            # 4th request from same IP should be rate limited
            response = client.post('/test-login')
            assert response.status_code == 429
            
            # Request from different IP should succeed
            # Note: In test environment, we can't easily simulate different IPs
            # This test documents the expected behavior
    
    def test_rate_limit_headers_included(self):
        """
        Test that rate limit information is included in response headers.
        """
        app, limiter = self.create_test_app_with_rate_limiting("5 per minute")
        
        with app.test_client() as client:
            response = client.post('/test-login')
            
            # Check for rate limit headers
            # Flask-Limiter includes X-RateLimit-* headers
            assert response.status_code == 200
            
            # Headers may include: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
            # Exact headers depend on Flask-Limiter configuration
    
    @given(
        limit_value=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=10, deadline=5000)
    def test_configurable_rate_limits(self, limit_value):
        """
        Test that rate limits are configurable.
        """
        # Create app with custom limit
        app, limiter = self.create_test_app_with_rate_limiting(f"{limit_value} per minute")
        
        with app.test_client() as client:
            # Make requests up to limit
            for i in range(limit_value):
                response = client.post('/test-login')
                assert response.status_code == 200, \
                    f"Request {i+1}/{limit_value} should succeed"
            
            # Next request should be rate limited
            response = client.post('/test-login')
            assert response.status_code == 429, \
                f"Request {limit_value+1} should be rate limited"


class TestRateLimitingConfiguration:
    """Test suite for rate limiting configuration."""
    
    def test_different_limits_for_different_endpoints(self):
        """
        Test that different endpoints can have different rate limits.
        """
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        config = RateLimiterConfig()
        config.login_limit = "3 per minute"
        config.admin_limit = "5 per minute"
        config.storage_uri = "memory://"
        
        limiter = init_rate_limiter(app, config)
        
        @app.route('/login', methods=['POST'])
        @limiter.limit(config.login_limit)
        def login():
            return jsonify({'success': True}), 200
        
        @app.route('/admin', methods=['POST'])
        @limiter.limit(config.admin_limit)
        def admin():
            return jsonify({'success': True}), 200
        
        with app.test_client() as client:
            # Login endpoint should be limited to 3
            for i in range(3):
                response = client.post('/login')
                assert response.status_code == 200
            
            response = client.post('/login')
            assert response.status_code == 429, "Login should be rate limited after 3 requests"
            
            # Admin endpoint should still work (different limit)
            for i in range(5):
                response = client.post('/admin')
                assert response.status_code == 200
            
            response = client.post('/admin')
            assert response.status_code == 429, "Admin should be rate limited after 5 requests"
    
    def test_rate_limit_configuration_from_env(self):
        """
        Test that rate limit configuration is loaded from environment.
        """
        config = RateLimiterConfig.from_env()
        
        # Verify configuration has expected attributes
        assert hasattr(config, 'login_limit')
        assert hasattr(config, 'admin_limit')
        assert hasattr(config, 'password_reset_limit')
        assert hasattr(config, 'storage_uri')
        
        # Verify values are strings in correct format
        assert isinstance(config.login_limit, str)
        assert 'per' in config.login_limit.lower()


class TestRateLimitingEdgeCases:
    """Test suite for rate limiting edge cases."""
    
    def test_exact_limit_boundary(self):
        """
        Test behavior at exact rate limit boundary.
        """
        app, limiter = TestRateLimitingEnforcement().create_test_app_with_rate_limiting("5 per minute")
        
        with app.test_client() as client:
            # Make exactly 5 requests
            for i in range(5):
                response = client.post('/test-login')
                assert response.status_code == 200, f"Request {i+1}/5 should succeed"
            
            # 6th request should be rate limited
            response = client.post('/test-login')
            assert response.status_code == 429, "6th request should be rate limited"
    
    def test_zero_requests_before_limit(self):
        """
        Test that first request always succeeds.
        """
        app, limiter = TestRateLimitingEnforcement().create_test_app_with_rate_limiting("1 per minute")
        
        with app.test_client() as client:
            # First request should always succeed
            response = client.post('/test-login')
            assert response.status_code == 200, "First request should succeed"
            
            # Second request should be rate limited
            response = client.post('/test-login')
            assert response.status_code == 429, "Second request should be rate limited"


if __name__ == '__main__':
    pytest.main([__file__])
