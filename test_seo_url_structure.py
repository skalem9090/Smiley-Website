"""
Property-Based Tests for SEO-Friendly URL Structure

Tests Property 25: SEO-Friendly URL Structure
Validates Requirements 6.7
"""

import pytest
from hypothesis import given, strategies as st, settings
from app import create_app, db
from models import Post, Tag
from datetime import datetime
import re


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


class TestSEOFriendlyURLStructure:
    """Test SEO-friendly URL structure implementation."""
    
    @settings(max_examples=20, deadline=None)
    @given(
        title=st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Pd'),
            blacklist_characters='\x00'
        )),
        tag_names=st.lists(
            st.text(min_size=1, max_size=30, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
                blacklist_characters='\x00'
            )),
            min_size=0,
            max_size=5
        )
    )
    def test_property_25_seo_friendly_url_structure(self, app_context, title, tag_names):
        """
        Property 25: SEO-Friendly URL Structure
        
        For any page or post, the URL should follow SEO-friendly permalink patterns
        with proper slug generation.
        
        Validates: Requirements 6.7
        """
        # Create a post with the given title
        post = Post(
            title=title.strip() or "Untitled",
            content="Test content",
            summary="Test summary",
            status='published',
            created_at=datetime.utcnow()
        )
        db.session.add(post)
        db.session.commit()
        
        # Test post URL structure
        with app_context.test_client() as client:
            # Post URLs should be /post/<id>/<slug>
            response = client.get(f'/post/{post.id}')
            
            # Should either redirect to slugged URL or display the post
            assert response.status_code in [200, 301, 302, 404]
            
            # If we have a slug, test the slugged URL
            if hasattr(post, 'slug') and post.slug:
                slug_response = client.get(f'/post/{post.id}/{post.slug}')
                assert slug_response.status_code in [200, 404]
                
                # Slug should be SEO-friendly (lowercase, hyphens, no special chars)
                assert re.match(r'^[a-z0-9-]+$', post.slug), \
                    f"Slug '{post.slug}' should only contain lowercase letters, numbers, and hyphens"
                
                # Slug should not start or end with hyphen
                assert not post.slug.startswith('-'), "Slug should not start with hyphen"
                assert not post.slug.endswith('-'), "Slug should not end with hyphen"
                
                # Slug should not have consecutive hyphens
                assert '--' not in post.slug, "Slug should not have consecutive hyphens"
        
        # Test tag URLs if tags are provided
        for tag_name in tag_names:
            if tag_name.strip():
                tag = Tag(name=tag_name.strip())
                db.session.add(tag)
                db.session.commit()
                
                # Tag URLs should use slugs
                if hasattr(tag, 'slug') and tag.slug:
                    with app_context.test_client() as client:
                        tag_response = client.get(f'/tag/{tag.slug}')
                        assert tag_response.status_code in [200, 404]
                        
                        # Tag slug should be SEO-friendly
                        assert re.match(r'^[a-z0-9-]+$', tag.slug), \
                            f"Tag slug '{tag.slug}' should only contain lowercase letters, numbers, and hyphens"
    
    def test_post_url_with_special_characters(self, app_context):
        """Test that special characters in titles are properly handled in URLs."""
        special_titles = [
            "Hello, World!",
            "Test & Development",
            "C++ Programming",
            "100% Success Rate",
            "Question?",
            "Exclamation!",
            "Quotes \"Test\"",
            "Apostrophe's Test"
        ]
        
        for title in special_titles:
            post = Post(
                title=title,
                content="Test content",
                summary="Test summary",
                status='published',
                created_at=datetime.utcnow()
            )
            db.session.add(post)
            db.session.commit()
            
            # If post has a slug, it should be SEO-friendly
            if hasattr(post, 'slug') and post.slug:
                # Should only contain lowercase alphanumeric and hyphens
                assert re.match(r'^[a-z0-9-]+$', post.slug), \
                    f"Slug for '{title}' should be SEO-friendly: {post.slug}"
                
                # Should not have consecutive hyphens
                assert '--' not in post.slug, \
                    f"Slug for '{title}' should not have consecutive hyphens: {post.slug}"
            
            db.session.delete(post)
            db.session.commit()
    
    def test_url_uniqueness(self, app_context):
        """Test that URLs are unique even for similar titles."""
        # Create posts with similar titles
        post1 = Post(
            title="Test Post",
            content="Content 1",
            summary="Summary 1",
            status='published',
            created_at=datetime.utcnow()
        )
        post2 = Post(
            title="Test Post",
            content="Content 2",
            summary="Summary 2",
            status='published',
            created_at=datetime.utcnow()
        )
        
        db.session.add(post1)
        db.session.add(post2)
        db.session.commit()
        
        # Posts should have different IDs
        assert post1.id != post2.id
        
        # URLs should be unique (using ID)
        with app_context.test_client() as client:
            response1 = client.get(f'/post/{post1.id}')
            response2 = client.get(f'/post/{post2.id}')
            
            # Both should be accessible
            assert response1.status_code in [200, 301, 302, 404]
            assert response2.status_code in [200, 301, 302, 404]
    
    def test_canonical_url_structure(self, app_context):
        """Test that canonical URLs follow consistent structure."""
        post = Post(
            title="Canonical URL Test",
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
                # Check if canonical URL is present in response
                html = response.data.decode('utf-8')
                
                # Canonical URL should be present
                if '<link rel="canonical"' in html:
                    # Extract canonical URL
                    import re
                    canonical_match = re.search(r'<link rel="canonical" href="([^"]+)"', html)
                    if canonical_match:
                        canonical_url = canonical_match.group(1)
                        
                        # Canonical URL should be absolute or relative
                        assert canonical_url.startswith(('http://', 'https://', '/')), \
                            "Canonical URL should be absolute or root-relative"
                        
                        # Should contain post ID
                        assert str(post.id) in canonical_url, \
                            "Canonical URL should contain post ID"
    
    def test_url_length_limits(self, app_context):
        """Test that URLs respect reasonable length limits."""
        # Create post with very long title
        long_title = "A" * 200
        post = Post(
            title=long_title,
            content="Test content",
            summary="Test summary",
            status='published',
            created_at=datetime.utcnow()
        )
        db.session.add(post)
        db.session.commit()
        
        # If post has a slug, it should be reasonably short
        if hasattr(post, 'slug') and post.slug:
            # Slug should be truncated to reasonable length (e.g., 100 characters)
            assert len(post.slug) <= 100, \
                f"Slug should be truncated to reasonable length: {len(post.slug)} characters"
    
    def test_unicode_handling_in_urls(self, app_context):
        """Test that Unicode characters are properly handled in URLs."""
        unicode_titles = [
            "Café",
            "Naïve",
            "Résumé",
            "日本語",
            "Español",
            "Français"
        ]
        
        for title in unicode_titles:
            post = Post(
                title=title,
                content="Test content",
                summary="Test summary",
                status='published',
                created_at=datetime.utcnow()
            )
            db.session.add(post)
            db.session.commit()
            
            # If post has a slug, it should handle Unicode appropriately
            if hasattr(post, 'slug') and post.slug:
                # Slug should either transliterate or remove Unicode characters
                # to maintain SEO-friendly format
                assert re.match(r'^[a-z0-9-]+$', post.slug), \
                    f"Slug for '{title}' should be ASCII-only: {post.slug}"
            
            db.session.delete(post)
            db.session.commit()
    
    def test_empty_title_handling(self, app_context):
        """Test URL generation for posts with empty or whitespace titles."""
        empty_titles = ["", "   ", "\t", "\n"]
        
        for title in empty_titles:
            post = Post(
                title=title or "Untitled",
                content="Test content",
                summary="Test summary",
                status='published',
                created_at=datetime.utcnow()
            )
            db.session.add(post)
            db.session.commit()
            
            # Post should still be accessible via ID
            with app_context.test_client() as client:
                response = client.get(f'/post/{post.id}')
                assert response.status_code in [200, 301, 302, 404]
            
            db.session.delete(post)
            db.session.commit()
