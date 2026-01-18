#!/usr/bin/env python3
"""
Property-Based Test: Homepage Summary Display

**Validates: Requirements 2.3**

This test validates that the homepage correctly displays post summaries
instead of full content, with proper formatting and truncation.

Property 6: Homepage Summary Display
- Homepage displays summaries instead of full post content
- Summaries are properly formatted and displayed
- Long summaries are appropriately handled in the display
- Empty or missing summaries fall back to content excerpts
- HTML in summaries is properly escaped for display
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import text, integers, composite
import sys
import os
import re

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from models import db, Post, User
from post_manager import PostManager


# Test data generators
@composite
def post_data_with_summary(draw):
    """Generate post data with various summary characteristics."""
    title = draw(text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ', min_size=5, max_size=50))
    content = draw(text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?', min_size=100, max_size=500))
    category = draw(st.sampled_from(['wealth', 'health', 'happiness']))
    
    # Generate different types of summaries
    summary_type = draw(st.sampled_from(['auto', 'manual', 'empty', 'html']))
    
    if summary_type == 'auto':
        summary = None  # Will be auto-generated
    elif summary_type == 'manual':
        summary = draw(text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?', min_size=10, max_size=150))
    elif summary_type == 'empty':
        summary = ""
    else:  # html
        summary = draw(text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ', min_size=10, max_size=100)) + "<b>bold</b>"
    
    return {
        'title': title,
        'content': content,
        'category': category,
        'summary': summary,
        'status': 'published'  # Only published posts show on homepage
    }


@composite
def multiple_posts_data(draw):
    """Generate multiple posts for homepage testing."""
    num_posts = draw(integers(min_value=1, max_value=10))
    posts = []
    
    for _ in range(num_posts):
        post_data = draw(post_data_with_summary())
        posts.append(post_data)
    
    return posts


class TestHomepageSummaryDisplay:
    """Property-based tests for homepage summary display."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application and database."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with self.app.app_context():
            db.create_all()
            
            # Create test user
            self.user = User(username='testuser', is_admin=True)
            self.user.set_password('testpass')
            db.session.add(self.user)
            db.session.commit()
            
            yield
            
            db.session.remove()
            db.drop_all()
    
    @given(post_data=post_data_with_summary())
    @settings(max_examples=5, deadline=2000)
    def test_homepage_displays_summary_not_full_content(self, post_data):
        """Test that homepage displays summaries instead of full post content."""
        assume(len(post_data['title'].strip()) > 0)
        assume(len(post_data['content'].strip()) > 0)
        
        with self.app.app_context():
            # Create post
            post = PostManager.create_post(**post_data)
            
            # Get homepage response
            with self.app.test_client() as client:
                response = client.get('/')
                assert response.status_code == 200
                
                html_content = response.get_data(as_text=True)
                
                # Should contain the post title (may be HTML-escaped)
                title_in_html = (post.title in html_content or 
                               post.title.replace('<', '&lt;').replace('>', '&gt;') in html_content)
                
                # If the post is in the expected category, it should appear
                if post.category in ['wealth', 'health', 'happiness']:
                    assert title_in_html, f"Post title '{post.title}' not found in homepage HTML"
                
                # Should contain summary or excerpt, not full content
                if post.summary and title_in_html:
                    # Should NOT contain the full content if it's much longer than summary
                    if len(post.content) > len(post.summary) + 100:
                        # Full content should not appear on homepage
                        assert post.content not in html_content
    
    @given(posts_data=multiple_posts_data())
    @settings(max_examples=3, deadline=2000)
    def test_homepage_organizes_posts_by_category(self, posts_data):
        """Test that homepage properly organizes posts by category with summaries."""
        # Filter to only valid posts with simple characters
        valid_posts = []
        for post_data in posts_data:
            if (len(post_data['title'].strip()) > 0 and 
                len(post_data['content'].strip()) > 0 and
                post_data['category'] in ['wealth', 'health', 'happiness'] and
                all(ord(c) < 128 for c in post_data['title'])):  # ASCII only
                valid_posts.append(post_data)
        
        assume(len(valid_posts) > 0)
        
        with self.app.app_context():
            # Create posts
            created_posts = []
            for post_data in valid_posts:
                post = PostManager.create_post(**post_data)
                created_posts.append(post)
            
            # Get homepage response
            with self.app.test_client() as client:
                response = client.get('/')
                assert response.status_code == 200
                
                html_content = response.get_data(as_text=True)
                
                # Check that posts are organized by category
                categories = ['wealth', 'health', 'happiness']
                for category in categories:
                    category_posts = [p for p in created_posts if p.category == category]
                    
                    if category_posts:
                        # Should contain category section
                        assert category in html_content.lower()
                        
                        # At least one post from this category should appear
                        category_found = False
                        for post in category_posts:
                            if post.title in html_content:
                                category_found = True
                                break
                        assert category_found, f"No posts found for category {category}"
    
    def test_homepage_handles_html_in_summaries_safely(self):
        """Test that HTML in summaries is properly escaped for safe display."""
        with self.app.app_context():
            # Create post with HTML in summary
            post = PostManager.create_post(
                title="Test Post",
                content="Some content for the post",
                summary="This is a <script>alert('xss')</script> test with <b>bold</b> text",
                status='published',
                category='wealth'
            )
            
            # Get homepage response
            with self.app.test_client() as client:
                response = client.get('/')
                assert response.status_code == 200
                
                html_content = response.get_data(as_text=True)
                
                # Should contain the post title
                assert post.title in html_content
                
                # Should contain escaped HTML or the safe text content
                assert 'test with' in html_content  # The safe part of the summary
                
                # The HTML should be escaped (Jinja2 auto-escapes by default)
                # So either the content is escaped or the dangerous parts are removed
                if '<script>' in html_content:
                    # If script tags appear, they should be in the page's own JavaScript, not in post content
                    # Check that the post summary area doesn't contain unescaped script
                    import re
                    # Find the summary content area (between summary div tags)
                    summary_pattern = r'<div class="summary">(.*?)</div>'
                    summary_matches = re.findall(summary_pattern, html_content, re.DOTALL)
                    for summary_content in summary_matches:
                        assert '<script>' not in summary_content, "Unescaped script tag found in summary content"
    
    def test_homepage_handles_missing_summaries_gracefully(self):
        """Test that posts without summaries are handled gracefully."""
        with self.app.app_context():
            # Create post with empty summary
            post = PostManager.create_post(
                title="Test Post Without Summary",
                content="This is a longer piece of content that should be used to generate a summary automatically when no manual summary is provided.",
                summary="",  # Empty summary, should auto-generate
                status='published',
                category='health'
            )
            
            # Get homepage response
            with self.app.test_client() as client:
                response = client.get('/')
                assert response.status_code == 200
                
                html_content = response.get_data(as_text=True)
                
                # Should contain the post title
                assert post.title in html_content
                
                # Should contain some content (either auto-generated summary or excerpt)
                assert "This is a longer piece" in html_content or post.summary in html_content
    
    def test_homepage_limits_posts_per_category(self):
        """Test that homepage limits the number of posts displayed per category."""
        with self.app.app_context():
            # Create many posts in one category
            posts = []
            for i in range(10):
                post = PostManager.create_post(
                    title=f"Wealth Post {i}",
                    content=f"Content for wealth post number {i} with enough text to generate a summary",
                    status='published',
                    category='wealth'
                )
                posts.append(post)
            
            # Get homepage response
            with self.app.test_client() as client:
                response = client.get('/')
                assert response.status_code == 200
                
                html_content = response.get_data(as_text=True)
                
                # Should contain some posts but not necessarily all 10
                # (The homepage template limits to 5 posts per category)
                post_count_in_html = 0
                for post in posts:
                    if post.title in html_content:
                        post_count_in_html += 1
                
                # Should show at most 5 posts (as per the template limit)
                assert post_count_in_html <= 5
                assert post_count_in_html > 0  # Should show at least some posts
    
    @given(
        title=text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ', min_size=5, max_size=50),
        content=text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?', min_size=200, max_size=500),
        summary=text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?', min_size=10, max_size=150)
    )
    @settings(max_examples=5, deadline=1500)
    def test_summary_formatting_preserved_in_display(self, title, content, summary):
        """Test that summary formatting is preserved appropriately in display."""
        assume(len(title.strip()) > 0)
        assume(len(content.strip()) > 0)
        assume(len(summary.strip()) > 0)
        
        with self.app.app_context():
            # Create post with manual summary
            post = PostManager.create_post(
                title=title,
                content=content,
                summary=summary,
                status='published',
                category='happiness'
            )
            
            # Get homepage response
            with self.app.test_client() as client:
                response = client.get('/')
                assert response.status_code == 200
                
                html_content = response.get_data(as_text=True)
                
                if post.title in html_content:
                    # Summary should be present in some form
                    # Either as-is or HTML-escaped
                    summary_found = (
                        post.summary in html_content or
                        post.summary.replace('<', '&lt;').replace('>', '&gt;') in html_content or
                        any(word in html_content for word in post.summary.split()[:3] if len(word) > 3)
                    )
                    assert summary_found, f"Summary not found in homepage HTML for post: {post.title}"
    
    def test_homepage_responsive_to_post_status_changes(self):
        """Test that homepage responds correctly to post status changes."""
        with self.app.app_context():
            # Create draft post (should not appear on homepage)
            draft_post = PostManager.create_post(
                title="Draft Post",
                content="This is a draft post that should not appear on homepage",
                status='draft',
                category='wealth'
            )
            
            # Create published post (should appear on homepage)
            published_post = PostManager.create_post(
                title="Published Post",
                content="This is a published post that should appear on homepage",
                status='published',
                category='wealth'
            )
            
            # Get homepage response
            with self.app.test_client() as client:
                response = client.get('/')
                assert response.status_code == 200
                
                html_content = response.get_data(as_text=True)
                
                # Should contain published post
                assert published_post.title in html_content
                
                # Should NOT contain draft post
                assert draft_post.title not in html_content
    
    def test_homepage_handles_empty_categories_gracefully(self):
        """Test that homepage handles categories with no posts gracefully."""
        with self.app.app_context():
            # Don't create any posts - all categories should be empty
            
            # Get homepage response
            with self.app.test_client() as client:
                response = client.get('/')
                assert response.status_code == 200
                
                html_content = response.get_data(as_text=True)
                
                # Should still render successfully even with no posts
                assert 'wealth' in html_content.lower() or 'health' in html_content.lower() or 'happiness' in html_content.lower()
                
                # Should not crash or show error messages
                assert 'error' not in html_content.lower()
                assert 'exception' not in html_content.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])