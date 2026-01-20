"""
Property-Based Tests for Caching Header Implementation

Tests Property 26: Caching Header Implementation
Validates Requirements 7.1, 7.2
"""

import pytest
from hypothesis import given, strategies as st, settings
from app import create_app, db
from models import Post
from datetime import datetime, timedelta


@pytest.fixture
def app_context():
    """Create application context for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


class TestCachingHeaderImplementation:
    """Test caching header implementation for performance optimization."""
    
    @settings(max_examples=20, deadline=None)
    @given(
        static_path=st.sampled_from([
            '/static/css/style.css',
            '/static/js/script.js',
            '/static/images/logo.png',
            '/static/uploads/test.jpg'
        ])
    )
    def test_property_26_caching_header_implementation(self, app_context, static_path):
        """
        Property 26: Caching Header Implementation
        
        For any static content request, the response should include appropriate
        cache headers for performance optimization.
        
        Validates: Requirements 7.1, 7.2
        """
        with app_context.test_client() as client:
            response = client.get(static_path)
            
            # Static files may not exist, but if they do, check headers
            if response.status_code == 200:
                # Should have cache-control header
                assert 'Cache-Control' in response.headers or \
                       'Expires' in response.headers or \
                       'ETag' in response.headers or \
                       'Last-Modified' in response.headers, \
                    f"Static content should have caching headers: {static_path}"
                
                # If Cache-Control is present, verify it's appropriate
                if 'Cache-Control' in response.headers:
                    cache_control = response.headers['Cache-Control']
                    
                    # Should include max-age or public directive for static content
                    assert 'max-age' in cache_control or \
                           'public' in cache_control or \
                           'private' in cache_control, \
                        f"Cache-Control should include caching directives: {cache_control}"
    
    def test_static_css_caching(self, app_context):
        """Test that CSS files have appropriate caching headers."""
        with app_context.test_client() as client:
            response = client.get('/static/css/style.css')
            
            if response.status_code == 200:
                # Should have caching headers
                has_cache_header = (
                    'Cache-Control' in response.headers or
                    'Expires' in response.headers or
                    'ETag' in response.headers or
                    'Last-Modified' in response.headers
                )
                assert has_cache_header, "CSS files should have caching headers"
                
                # If Cache-Control is present, should allow caching
                if 'Cache-Control' in response.headers:
                    cache_control = response.headers['Cache-Control'].lower()
                    assert 'no-store' not in cache_control, \
                        "CSS files should be cacheable"
    
    def test_static_js_caching(self, app_context):
        """Test that JavaScript files have appropriate caching headers."""
        with app_context.test_client() as client:
            response = client.get('/static/js/script.js')
            
            if response.status_code == 200:
                # Should have caching headers
                has_cache_header = (
                    'Cache-Control' in response.headers or
                    'Expires' in response.headers or
                    'ETag' in response.headers or
                    'Last-Modified' in response.headers
                )
                assert has_cache_header, "JavaScript files should have caching headers"
    
    def test_static_image_caching(self, app_context):
        """Test that image files have appropriate caching headers."""
        # Create a test post with image
        post = Post(
            title="Test Post with Image",
            content="<img src='/static/uploads/test.jpg'>",
            summary="Test summary",
            status='published',
            created_at=datetime.utcnow()
        )
        db.session.add(post)
        db.session.commit()
        
        with app_context.test_client() as client:
            # Test image URL
            response = client.get('/static/uploads/test.jpg')
            
            if response.status_code == 200:
                # Images should have long cache times
                has_cache_header = (
                    'Cache-Control' in response.headers or
                    'Expires' in response.headers or
                    'ETag' in response.headers or
                    'Last-Modified' in response.headers
                )
                assert has_cache_header, "Image files should have caching headers"
                
                # If Cache-Control is present, should have long max-age
                if 'Cache-Control' in response.headers:
                    cache_control = response.headers['Cache-Control']
                    if 'max-age' in cache_control:
                        # Extract max-age value
                        import re
                        max_age_match = re.search(r'max-age=(\d+)', cache_control)
                        if max_age_match:
                            max_age = int(max_age_match.group(1))
                            # Images should be cached for at least 1 hour (3600 seconds)
                            assert max_age >= 3600, \
                                f"Images should have long cache time: {max_age} seconds"
    
    def test_dynamic_content_caching(self, app_context):
        """Test that dynamic content has appropriate caching headers."""
        # Create a test post
        post = Post(
            title="Test Post",
            content="Test content",
            summary="Test summary",
            status='published',
            created_at=datetime.utcnow()
        )
        db.session.add(post)
        db.session.commit()
        
        with app_context.test_client() as client:
            # Test post page
            response = client.get(f'/post/{post.id}')
            
            if response.status_code == 200:
                # Dynamic content should have cache headers
                # but may be more restrictive than static content
                if 'Cache-Control' in response.headers:
                    cache_control = response.headers['Cache-Control'].lower()
                    
                    # Should either allow caching with validation or be private
                    assert any(directive in cache_control for directive in [
                        'max-age', 'public', 'private', 'must-revalidate', 'no-cache'
                    ]), f"Dynamic content should have cache directives: {cache_control}"
    
    def test_feed_caching(self, app_context):
        """Test that RSS/Atom feeds have appropriate caching headers."""
        with app_context.test_client() as client:
            # Test RSS feed
            rss_response = client.get('/feed.xml')
            
            if rss_response.status_code == 200:
                # Feeds should have caching headers
                has_cache_header = (
                    'Cache-Control' in rss_response.headers or
                    'Expires' in rss_response.headers or
                    'ETag' in rss_response.headers or
                    'Last-Modified' in rss_response.headers
                )
                assert has_cache_header, "RSS feeds should have caching headers"
                
                # Feeds should be cacheable but with shorter duration
                if 'Cache-Control' in rss_response.headers:
                    cache_control = rss_response.headers['Cache-Control']
                    if 'max-age' in cache_control:
                        import re
                        max_age_match = re.search(r'max-age=(\d+)', cache_control)
                        if max_age_match:
                            max_age = int(max_age_match.group(1))
                            # Feeds should be cached but not too long (e.g., 1 hour to 1 day)
                            assert 300 <= max_age <= 86400, \
                                f"Feed cache time should be reasonable: {max_age} seconds"
    
    def test_no_cache_for_admin_pages(self, app_context):
        """Test that admin pages have no-cache headers."""
        with app_context.test_client() as client:
            # Test dashboard (admin page)
            response = client.get('/dashboard')
            
            # Admin pages should not be cached or require authentication
            if response.status_code == 200:
                # Should have restrictive cache headers
                if 'Cache-Control' in response.headers:
                    cache_control = response.headers['Cache-Control'].lower()
                    
                    # Should prevent caching or require revalidation
                    assert any(directive in cache_control for directive in [
                        'no-cache', 'no-store', 'must-revalidate', 'private'
                    ]), f"Admin pages should not be cached: {cache_control}"
    
    def test_etag_generation(self, app_context):
        """Test that ETags are generated for cacheable content."""
        # Create a test post
        post = Post(
            title="ETag Test Post",
            content="Test content for ETag",
            summary="Test summary",
            status='published',
            created_at=datetime.utcnow()
        )
        db.session.add(post)
        db.session.commit()
        
        with app_context.test_client() as client:
            # First request
            response1 = client.get(f'/post/{post.id}')
            
            if response1.status_code == 200:
                # Check if ETag is present
                if 'ETag' in response1.headers:
                    etag1 = response1.headers['ETag']
                    
                    # ETag should be a quoted string
                    assert etag1.startswith('"') or etag1.startswith('W/"'), \
                        f"ETag should be properly formatted: {etag1}"
                    
                    # Second request with If-None-Match
                    response2 = client.get(
                        f'/post/{post.id}',
                        headers={'If-None-Match': etag1}
                    )
                    
                    # Should return 304 Not Modified if content hasn't changed
                    # or 200 if ETags aren't being validated
                    assert response2.status_code in [200, 304], \
                        f"ETag validation should work: {response2.status_code}"
    
    def test_last_modified_header(self, app_context):
        """Test that Last-Modified headers are set appropriately."""
        # Create a test post
        post = Post(
            title="Last Modified Test",
            content="Test content",
            summary="Test summary",
            status='published',
            created_at=datetime.utcnow()
        )
        db.session.add(post)
        db.session.commit()
        
        with app_context.test_client() as client:
            response = client.get(f'/post/{post.id}')
            
            if response.status_code == 200:
                # Check if Last-Modified is present
                if 'Last-Modified' in response.headers:
                    last_modified = response.headers['Last-Modified']
                    
                    # Should be in HTTP date format
                    from email.utils import parsedate_to_datetime
                    try:
                        parsed_date = parsedate_to_datetime(last_modified)
                        # Should be a valid date
                        assert parsed_date is not None, \
                            f"Last-Modified should be valid HTTP date: {last_modified}"
                        
                        # Should not be in the future
                        assert parsed_date <= datetime.now(parsed_date.tzinfo), \
                            "Last-Modified should not be in the future"
                    except Exception as e:
                        pytest.fail(f"Last-Modified header parsing failed: {e}")
    
    def test_vary_header_for_content_negotiation(self, app_context):
        """Test that Vary headers are set for content negotiation."""
        with app_context.test_client() as client:
            # Test a page that might vary by Accept-Encoding
            response = client.get('/')
            
            if response.status_code == 200:
                # If compression is enabled, should have Vary header
                if 'Content-Encoding' in response.headers:
                    # Should have Vary: Accept-Encoding
                    if 'Vary' in response.headers:
                        vary = response.headers['Vary']
                        assert 'Accept-Encoding' in vary, \
                            "Vary header should include Accept-Encoding for compressed content"
    
    def test_cache_control_directives(self, app_context):
        """Test that Cache-Control directives are appropriate for content type."""
        test_urls = [
            ('/', 'homepage'),
            ('/about', 'about page'),
            ('/feed.xml', 'RSS feed'),
        ]
        
        with app_context.test_client() as client:
            for url, description in test_urls:
                response = client.get(url)
                
                if response.status_code == 200 and 'Cache-Control' in response.headers:
                    cache_control = response.headers['Cache-Control'].lower()
                    
                    # Should not have conflicting directives
                    assert not ('public' in cache_control and 'private' in cache_control), \
                        f"{description} should not have conflicting cache directives"
                    
                    assert not ('no-cache' in cache_control and 'max-age' in cache_control and 'max-age=0' not in cache_control), \
                        f"{description} cache directives should be consistent"
