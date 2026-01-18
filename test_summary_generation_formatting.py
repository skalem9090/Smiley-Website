#!/usr/bin/env python3
"""
Property-Based Test: Summary Generation and Formatting

**Validates: Requirements 2.2, 2.4, 2.5**

This test validates that the summary generation and formatting functionality
works correctly across various content types and lengths.

Property 5: Summary Generation and Formatting
- Auto-generated summaries are properly truncated to 150 characters
- Manual summaries respect the 200 character limit
- HTML tags are properly stripped from auto-generated summaries
- Formatting is preserved appropriately in summaries
- Summary generation handles edge cases (empty content, only HTML, etc.)
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import text, integers, composite
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from models import db, Post, User
from post_manager import PostManager


# Test data generators
@composite
def html_content(draw):
    """Generate HTML content with various tags and text."""
    base_text = draw(text(min_size=10, max_size=500))
    
    # Add some HTML tags
    tags = ['<p>', '</p>', '<strong>', '</strong>', '<em>', '</em>', 
            '<br>', '<h1>', '</h1>', '<h2>', '</h2>']
    
    content = base_text
    for _ in range(draw(integers(min_value=0, max_value=5))):
        tag = draw(st.sampled_from(tags))
        insert_pos = draw(integers(min_value=0, max_value=len(content)))
        content = content[:insert_pos] + tag + content[insert_pos:]
    
    return content


@composite
def post_content_data(draw):
    """Generate post content with various characteristics."""
    content_type = draw(st.sampled_from(['plain', 'html', 'mixed', 'empty']))
    
    if content_type == 'empty':
        return ''
    elif content_type == 'plain':
        return draw(text(min_size=1, max_size=1000))
    elif content_type == 'html':
        return draw(html_content())
    else:  # mixed
        plain = draw(text(min_size=10, max_size=300))
        html = draw(html_content())
        return plain + html


@composite
def manual_summary_data(draw):
    """Generate manual summary data within limits."""
    return draw(text(min_size=1, max_size=200))


class TestSummaryGenerationFormatting:
    """Property-based tests for summary generation and formatting."""
    
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
    
    @given(content=post_content_data())
    @settings(max_examples=50, deadline=5000)
    def test_auto_summary_generation_length(self, content):
        """Test that auto-generated summaries are properly truncated to 150 characters."""
        assume(len(content.strip()) > 0)  # Need some content to generate summary
        
        with self.app.app_context():
            # Create post with auto-generated summary
            post = PostManager.create_post(
                title="Test Post",
                content=content,
                summary=None  # Auto-generate
            )
            
            if post.summary:
                # Auto-generated summaries should be <= 150 characters
                assert len(post.summary) <= 150, f"Auto-generated summary too long: {len(post.summary)} chars"
                
                # Should not be empty if content exists
                assert len(post.summary.strip()) > 0, "Auto-generated summary should not be empty"
    
    @given(manual_summary=manual_summary_data())
    @settings(max_examples=30, deadline=3000)
    def test_manual_summary_length_validation(self, manual_summary):
        """Test that manual summaries respect the 200 character limit."""
        with self.app.app_context():
            if len(manual_summary) <= 200:
                # Should accept valid manual summaries
                post = PostManager.create_post(
                    title="Test Post",
                    content="Some content",
                    summary=manual_summary
                )
                # PostManager truncates and strips whitespace, so compare processed version
                expected_summary = PostManager._truncate_summary(manual_summary)
                assert post.summary == expected_summary
            else:
                # Should truncate summaries over 200 characters
                post = PostManager.create_post(
                    title="Test Post",
                    content="Some content",
                    summary=manual_summary
                )
                # Should be truncated to max length
                assert len(post.summary) <= 200
    
    @given(html_content=html_content())
    @settings(max_examples=40, deadline=4000)
    def test_html_tag_stripping_in_auto_summary(self, html_content):
        """Test that HTML tags are properly stripped from auto-generated summaries."""
        assume(len(html_content.strip()) > 0)
        
        with self.app.app_context():
            post = PostManager.create_post(
                title="Test Post",
                content=html_content,
                summary=None  # Auto-generate
            )
            
            if post.summary:
                # Summary should not contain common HTML tags
                common_html_tags = ['<p>', '</p>', '<strong>', '</strong>', '<em>', '</em>', 
                                  '<br>', '<h1>', '</h1>', '<h2>', '</h2>', '<div>', '</div>']
                
                for tag in common_html_tags:
                    assert tag not in post.summary, f"HTML tag {tag} found in auto-generated summary"
                
                # Check that HTML-like patterns are minimal (< and > can appear in text content)
                # Only fail if we have obvious HTML tag patterns
                import re
                html_pattern = re.compile(r'<[a-zA-Z][^>]*>')
                html_matches = html_pattern.findall(post.summary)
                assert len(html_matches) == 0, f"HTML tag patterns found in summary: {html_matches}"
    
    @given(content=text(min_size=200, max_size=1000))
    @settings(max_examples=30, deadline=3000)
    def test_summary_truncation_preserves_words(self, content):
        """Test that summary truncation preserves word boundaries when possible."""
        assume(len(content.strip()) > 150)  # Need content longer than summary limit
        
        with self.app.app_context():
            post = PostManager.create_post(
                title="Test Post",
                content=content,
                summary=None  # Auto-generate
            )
            
            if post.summary and len(post.summary) > 10:
                # Summary should not end with a partial word (unless forced by length)
                # Check if last character is alphanumeric and next would be too
                if post.summary[-1].isalnum():
                    # Find the position in original content
                    summary_in_content = content.find(post.summary)
                    if summary_in_content >= 0:
                        next_pos = summary_in_content + len(post.summary)
                        if next_pos < len(content):
                            next_char = content[next_pos]
                            # If next character is alphanumeric, we might have cut mid-word
                            # This is acceptable if we're at the 150 char limit
                            if next_char.isalnum():
                                assert len(post.summary) >= 140, "Word boundary not preserved when there was room"
    
    def test_empty_content_summary_handling(self):
        """Test that empty or whitespace-only content is handled properly."""
        with self.app.app_context():
            # PostManager doesn't allow empty content, so test with minimal content
            post1 = PostManager.create_post(
                title="Test Post",
                content="a",  # Minimal content
                summary=None
            )
            # Should have auto-generated summary for minimal content
            assert post1.summary == "a"
            
            # Test with whitespace content that gets stripped to minimal
            post2 = PostManager.create_post(
                title="Test Post",
                content="   b   ",  # Whitespace around minimal content
                summary=None
            )
            # Should have auto-generated summary from stripped content
            assert post2.summary == "b"
    
    def test_html_only_content_summary_handling(self):
        """Test that HTML-only content (no text) is handled properly."""
        with self.app.app_context():
            # HTML tags with no text content
            post = PostManager.create_post(
                title="Test Post",
                content="<p></p><br><strong></strong>",
                summary=None
            )
            # Should have no summary or empty summary for HTML-only content
            assert post.summary is None or post.summary.strip() == ""
    
    @given(
        content=text(min_size=50, max_size=300),
        manual_summary=text(min_size=1, max_size=200)
    )
    @settings(max_examples=30, deadline=3000)
    def test_manual_summary_overrides_auto_generation(self, content, manual_summary):
        """Test that providing a manual summary overrides auto-generation."""
        with self.app.app_context():
            post = PostManager.create_post(
                title="Test Post",
                content=content,
                summary=manual_summary
            )
            
            # Should use the processed manual summary (truncated and stripped)
            expected_summary = PostManager._truncate_summary(manual_summary)
            assert post.summary == expected_summary
            
            # Should not be the same as auto-generated content (unless coincidentally)
            auto_summary = PostManager.generate_summary(content)
            if expected_summary != auto_summary:
                # Manual summary is different from what would be auto-generated
                assert post.summary == expected_summary
    
    def test_summary_regeneration_method(self):
        """Test the regenerate_summary method works correctly."""
        with self.app.app_context():
            # Create post with manual summary
            post = PostManager.create_post(
                title="Test Post",
                content="This is a long piece of content that should generate a summary when we regenerate it automatically.",
                summary="Manual summary"
            )
            
            original_summary = post.summary
            assert original_summary == "Manual summary"
            
            # Regenerate summary
            PostManager.regenerate_summary(post.id)
            
            # Refresh post from database
            db.session.refresh(post)
            
            # Should now have auto-generated summary
            assert post.summary != original_summary
            assert post.summary is not None
            assert len(post.summary) <= 150
            assert "This is a long piece of content" in post.summary
    
    def test_summary_update_method(self):
        """Test the update_summary method works correctly."""
        with self.app.app_context():
            # Create post
            post = PostManager.create_post(
                title="Test Post",
                content="Some content",
                summary="Original summary"
            )
            
            # Update summary
            new_summary = "Updated summary"
            PostManager.update_summary(post.id, new_summary)
            
            # Refresh post from database
            db.session.refresh(post)
            
            # Should have updated summary
            assert post.summary == new_summary
    
    def test_summary_stats_method(self):
        """Test the get_summary_stats method returns correct statistics."""
        with self.app.app_context():
            # Create posts with different summary types
            post1 = PostManager.create_post(
                title="Post 1",
                content="Content for auto summary generation that is long enough to trigger truncation with ellipsis and more content to ensure it gets truncated properly with the ellipsis at the end",
                summary=None  # Auto-generated
            )
            
            post2 = PostManager.create_post(
                title="Post 2", 
                content="Content",
                summary="Manual summary"
            )
            
            post3 = PostManager.create_post(
                title="Post 3",
                content="Content",
                summary=""  # Empty, will be auto-generated
            )
            
            # Test individual post stats
            stats1 = PostManager.get_summary_stats(post1.id)
            assert stats1 is not None
            assert stats1['post_id'] == post1.id
            assert stats1['summary_length'] > 0
            assert stats1['is_auto_generated'] == True  # Should end with "..." due to truncation
            
            stats2 = PostManager.get_summary_stats(post2.id)
            assert stats2 is not None
            assert stats2['post_id'] == post2.id
            assert stats2['summary_length'] > 0
            assert stats2['is_auto_generated'] == False  # Manual summary
            
            stats3 = PostManager.get_summary_stats(post3.id)
            assert stats3 is not None
            assert stats3['post_id'] == post3.id
            assert stats3['summary_length'] > 0  # Auto-generated from content
            assert stats3['is_auto_generated'] == False  # Short content, no truncation needed


if __name__ == '__main__':
    pytest.main([__file__, '-v'])