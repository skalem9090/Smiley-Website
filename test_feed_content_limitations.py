"""
Property-based test for feed content limitations.

This module tests the property that feeds should contain exactly the most recent
20 published posts and exclude all draft or scheduled posts.

**Feature: blog-comprehensive-features, Property 3: Feed Content Limitations**
**Validates: Requirements 2.5, 2.8**
"""

import pytest
from hypothesis import given, strategies as st, settings
from app import create_app
from models import db, Post, User, AuthorProfile
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET
import string


# Custom strategy for XML-safe text
def xml_safe_text(min_size=1, max_size=100):
    """Generate XML-safe text without control characters."""
    safe_chars = string.ascii_letters + string.digits + string.punctuation + ' '
    safe_chars = ''.join(c for c in safe_chars if ord(c) >= 32 and c not in '<>&"\'')
    return st.text(alphabet=safe_chars, min_size=min_size, max_size=max_size).filter(lambda x: x.strip())


class TestFeedContentLimitations:
    """Property-based test for feed content limitations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SITE_URL'] = 'http://testsite.com'
        self.app.config['MAX_FEED_ITEMS'] = 20  # Ensure we test the limit
        
        with self.app.app_context():
            db.create_all()
            
            # Clear any existing data
            db.session.query(User).delete()
            db.session.query(AuthorProfile).delete()
            db.session.query(Post).delete()
            
            # Create admin user
            admin = User(username='testadmin', is_admin=True)
            admin.set_password('testpass')
            db.session.add(admin)
            
            # Create author profile
            profile = AuthorProfile(
                name="Test Author",
                bio="A test author for feed testing.",
                mission_statement="To test RSS and Atom feeds thoroughly.",
                email="test@example.com"
            )
            profile.set_expertise_areas(["Testing", "RSS", "Atom"])
            db.session.add(profile)
            db.session.commit()
    
    @given(
        num_published_posts=st.integers(min_value=25, max_value=30),
        num_draft_posts=st.integers(min_value=1, max_value=5),
        num_scheduled_posts=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=10, deadline=20000)
    def test_feed_limits_to_recent_published_posts_only(self, num_published_posts, num_draft_posts, num_scheduled_posts):
        """
        Property: Feeds should contain exactly the most recent 20 published posts
        and exclude all draft or scheduled posts.
        
        **Validates: Requirements 2.5, 2.8**
        """
        with self.app.app_context():
            # Clear any existing posts
            db.session.query(Post).delete()
            db.session.commit()
            
            # Create published posts with different publication dates
            published_posts = []
            base_date = datetime.now(timezone.utc)
            
            for i in range(num_published_posts):
                post = Post(
                    title=f"Published Post {i+1}",
                    content=f"<p>Content for published post {i+1}</p>",
                    summary=f"Summary for published post {i+1}",
                    status='published',
                    published_at=base_date - timedelta(hours=i),  # Newer posts first
                    category='published'
                )
                db.session.add(post)
                published_posts.append(post)
            
            # Create draft posts (should not appear in feeds)
            draft_posts = []
            for i in range(num_draft_posts):
                post = Post(
                    title=f"Draft Post {i+1}",
                    content=f"<p>Content for draft post {i+1}</p>",
                    status='draft',
                    category='draft'
                )
                db.session.add(post)
                draft_posts.append(post)
            
            # Create scheduled posts (should not appear in feeds)
            scheduled_posts = []
            future_date = base_date + timedelta(days=1)
            for i in range(num_scheduled_posts):
                post = Post(
                    title=f"Scheduled Post {i+1}",
                    content=f"<p>Content for scheduled post {i+1}</p>",
                    status='scheduled',
                    published_at=future_date + timedelta(hours=i),
                    category='scheduled'
                )
                db.session.add(post)
                scheduled_posts.append(post)
            
            db.session.commit()
            
            client = self.app.test_client()
            
            # Test RSS feed
            rss_response = client.get('/feed.xml')
            assert rss_response.status_code == 200
            rss_content = rss_response.get_data(as_text=True)
            
            # Parse RSS XML
            rss_root = ET.fromstring(rss_content)
            rss_items = rss_root.findall('.//item')
            
            # Should contain exactly 20 items (the limit)
            assert len(rss_items) == 20, f"RSS feed should contain exactly 20 items, got {len(rss_items)}"
            
            # All items should be published posts (check titles)
            rss_titles = []
            for item in rss_items:
                title_elem = item.find('title')
                if title_elem is not None:
                    rss_titles.append(title_elem.text)
            
            # Should contain the 20 most recent published posts
            expected_titles = [f"Published Post {i+1}" for i in range(20)]  # First 20 posts
            for expected_title in expected_titles:
                assert expected_title in rss_titles, f"Expected title '{expected_title}' not found in RSS feed"
            
            # Should NOT contain any draft posts
            for draft_post in draft_posts:
                assert draft_post.title not in rss_content, f"Draft post '{draft_post.title}' should not appear in RSS feed"
            
            # Should NOT contain any scheduled posts
            for scheduled_post in scheduled_posts:
                assert scheduled_post.title not in rss_content, f"Scheduled post '{scheduled_post.title}' should not appear in RSS feed"
            
            # Test Atom feed
            atom_response = client.get('/atom.xml')
            assert atom_response.status_code == 200
            atom_content = atom_response.get_data(as_text=True)
            
            # Parse Atom XML
            atom_root = ET.fromstring(atom_content)
            atom_entries = atom_root.findall('.//{http://www.w3.org/2005/Atom}entry')
            
            # Should contain exactly 20 entries (the limit)
            assert len(atom_entries) == 20, f"Atom feed should contain exactly 20 entries, got {len(atom_entries)}"
            
            # All entries should be published posts
            atom_titles = []
            for entry in atom_entries:
                title_elem = entry.find('.//{http://www.w3.org/2005/Atom}title')
                if title_elem is not None:
                    atom_titles.append(title_elem.text)
            
            # Should contain the 20 most recent published posts
            for expected_title in expected_titles:
                assert expected_title in atom_titles, f"Expected title '{expected_title}' not found in Atom feed"
            
            # Should NOT contain any draft posts
            for draft_post in draft_posts:
                assert draft_post.title not in atom_content, f"Draft post '{draft_post.title}' should not appear in Atom feed"
            
            # Should NOT contain any scheduled posts
            for scheduled_post in scheduled_posts:
                assert scheduled_post.title not in atom_content, f"Scheduled post '{scheduled_post.title}' should not appear in Atom feed"
    
    def test_feed_respects_published_status_only(self):
        """
        Property: Only posts with status='published' should appear in feeds.
        
        **Validates: Requirements 2.8**
        """
        with self.app.app_context():
            # Clear any existing posts
            db.session.query(Post).delete()
            db.session.commit()
            
            # Create posts with different statuses
            statuses = ['published', 'draft', 'scheduled', 'archived', 'private']
            posts_by_status = {}
            
            for status in statuses:
                post = Post(
                    title=f"Post with {status} status",
                    content=f"<p>Content for {status} post</p>",
                    status=status,
                    published_at=datetime.now(timezone.utc) if status == 'published' else None
                )
                db.session.add(post)
                posts_by_status[status] = post
            
            db.session.commit()
            
            client = self.app.test_client()
            
            # Test RSS feed
            rss_response = client.get('/feed.xml')
            assert rss_response.status_code == 200
            rss_content = rss_response.get_data(as_text=True)
            
            # Only published post should appear
            assert "Post with published status" in rss_content
            
            # All other statuses should NOT appear
            for status in ['draft', 'scheduled', 'archived', 'private']:
                assert f"Post with {status} status" not in rss_content, f"Post with status '{status}' should not appear in RSS feed"
            
            # Test Atom feed
            atom_response = client.get('/atom.xml')
            assert atom_response.status_code == 200
            atom_content = atom_response.get_data(as_text=True)
            
            # Only published post should appear
            assert "Post with published status" in atom_content
            
            # All other statuses should NOT appear
            for status in ['draft', 'scheduled', 'archived', 'private']:
                assert f"Post with {status} status" not in atom_content, f"Post with status '{status}' should not appear in Atom feed"
    
    @given(
        num_posts=st.integers(min_value=1, max_value=15)
    )
    @settings(max_examples=10, deadline=15000)
    def test_feed_contains_all_posts_when_under_limit(self, num_posts):
        """
        Property: When there are fewer than 20 published posts, all should appear in feeds.
        
        **Validates: Requirements 2.5**
        """
        with self.app.app_context():
            # Clear any existing posts
            db.session.query(Post).delete()
            db.session.commit()
            
            # Create published posts (fewer than the limit)
            created_posts = []
            for i in range(num_posts):
                post = Post(
                    title=f"Test Post {i+1}",
                    content=f"<p>Content for test post {i+1}</p>",
                    status='published',
                    published_at=datetime.now(timezone.utc) - timedelta(hours=i)
                )
                db.session.add(post)
                created_posts.append(post)
            
            db.session.commit()
            
            client = self.app.test_client()
            
            # Test RSS feed
            rss_response = client.get('/feed.xml')
            assert rss_response.status_code == 200
            rss_content = rss_response.get_data(as_text=True)
            
            # Parse RSS XML
            rss_root = ET.fromstring(rss_content)
            rss_items = rss_root.findall('.//item')
            
            # Should contain exactly the number of posts we created
            assert len(rss_items) == num_posts, f"RSS feed should contain {num_posts} items, got {len(rss_items)}"
            
            # All created posts should appear
            for post in created_posts:
                assert post.title in rss_content, f"Post '{post.title}' should appear in RSS feed"
            
            # Test Atom feed
            atom_response = client.get('/atom.xml')
            assert atom_response.status_code == 200
            atom_content = atom_response.get_data(as_text=True)
            
            # Parse Atom XML
            atom_root = ET.fromstring(atom_content)
            atom_entries = atom_root.findall('.//{http://www.w3.org/2005/Atom}entry')
            
            # Should contain exactly the number of posts we created
            assert len(atom_entries) == num_posts, f"Atom feed should contain {num_posts} entries, got {len(atom_entries)}"
            
            # All created posts should appear
            for post in created_posts:
                assert post.title in atom_content, f"Post '{post.title}' should appear in Atom feed"
    
    def test_feed_ordering_by_publication_date(self):
        """
        Property: Feed items should be ordered by publication date (newest first).
        
        **Validates: Requirements 2.5**
        """
        with self.app.app_context():
            # Clear any existing posts
            db.session.query(Post).delete()
            db.session.commit()
            
            # Create posts with specific publication dates
            base_date = datetime.now(timezone.utc)
            posts_data = [
                ("Oldest Post", base_date - timedelta(days=3)),
                ("Middle Post", base_date - timedelta(days=1)),
                ("Newest Post", base_date)
            ]
            
            for title, pub_date in posts_data:
                post = Post(
                    title=title,
                    content=f"<p>Content for {title}</p>",
                    status='published',
                    published_at=pub_date
                )
                db.session.add(post)
            
            db.session.commit()
            
            client = self.app.test_client()
            
            # Test RSS feed ordering
            rss_response = client.get('/feed.xml')
            assert rss_response.status_code == 200
            rss_content = rss_response.get_data(as_text=True)
            
            # Parse RSS XML
            rss_root = ET.fromstring(rss_content)
            rss_items = rss_root.findall('.//item')
            
            # Extract titles in order
            rss_titles = []
            for item in rss_items:
                title_elem = item.find('title')
                if title_elem is not None:
                    rss_titles.append(title_elem.text)
            
            # Should be ordered newest first
            expected_order = ["Newest Post", "Middle Post", "Oldest Post"]
            assert rss_titles == expected_order, f"RSS feed items not in correct order. Expected {expected_order}, got {rss_titles}"
            
            # Test Atom feed ordering
            atom_response = client.get('/atom.xml')
            assert atom_response.status_code == 200
            atom_content = atom_response.get_data(as_text=True)
            
            # Parse Atom XML
            atom_root = ET.fromstring(atom_content)
            atom_entries = atom_root.findall('.//{http://www.w3.org/2005/Atom}entry')
            
            # Extract titles in order
            atom_titles = []
            for entry in atom_entries:
                title_elem = entry.find('.//{http://www.w3.org/2005/Atom}title')
                if title_elem is not None:
                    atom_titles.append(title_elem.text)
            
            # Should be ordered newest first
            assert atom_titles == expected_order, f"Atom feed entries not in correct order. Expected {expected_order}, got {atom_titles}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])