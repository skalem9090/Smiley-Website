"""
Test RSS/Atom feed functionality.

This module tests the RSS and Atom feed generation, including proper XML structure,
content inclusion, and feed discovery links.
"""

import pytest
from app import create_app
from models import db, Post, User, AuthorProfile
from datetime import datetime, timezone
import xml.etree.ElementTree as ET


class TestRSSAtomFeeds:
    """Test RSS and Atom feed functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SITE_URL'] = 'http://testsite.com'
        
        with self.app.app_context():
            db.create_all()
            
            # Create admin user (check if exists first)
            admin = db.session.query(User).filter_by(username='testadmin').first()
            if not admin:
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
            
            # Create test posts
            post1 = Post(
                title="First Test Post",
                content="<p>This is the first test post with <strong>HTML content</strong>.</p>",
                summary="First test post summary",
                status='published',
                published_at=datetime.now(timezone.utc),
                category='testing'
            )
            
            post2 = Post(
                title="Second Test Post",
                content="<p>This is the second test post.</p><p>It has multiple paragraphs.</p>",
                status='published',
                published_at=datetime.now(timezone.utc),
                category='development'
            )
            
            # Draft post (should not appear in feeds)
            post3 = Post(
                title="Draft Post",
                content="<p>This is a draft post.</p>",
                status='draft'
            )
            
            db.session.add_all([post1, post2, post3])
            db.session.commit()
    
    def test_rss_feed_generation(self):
        """Test RSS feed generation and structure."""
        with self.app.app_context():
            client = self.app.test_client()
            response = client.get('/feed.xml')
            
            # Check response
            assert response.status_code == 200
            assert response.content_type == 'application/rss+xml; charset=utf-8'
            
            # Check caching headers
            assert 'Cache-Control' in response.headers
            assert 'ETag' in response.headers
            
            # Parse XML
            content = response.get_data(as_text=True)
            root = ET.fromstring(content)
            
            # Check RSS structure
            assert root.tag == 'rss'
            assert root.get('version') == '2.0'
            
            channel = root.find('channel')
            assert channel is not None
            
            # Check channel metadata
            title = channel.find('title')
            assert title is not None
            assert title.text == 'Blog Feed'
            
            description = channel.find('description')
            assert description is not None
            assert 'test RSS and Atom feeds' in description.text
            
            # Check items (should only include published posts)
            items = channel.findall('item')
            # Note: May include posts from previous tests or default content
            assert len(items) >= 2  # At least our test posts
            
            # Check first item
            first_item = items[0]
            item_title = first_item.find('title')
            assert item_title is not None
            assert 'Test Post' in item_title.text
            
            item_link = first_item.find('link')
            assert item_link is not None
            assert 'http://testsite.com/post/' in item_link.text
            
            item_description = first_item.find('description')
            assert item_description is not None
    
    def test_atom_feed_generation(self):
        """Test Atom feed generation and structure."""
        with self.app.app_context():
            client = self.app.test_client()
            response = client.get('/atom.xml')
            
            # Check response
            assert response.status_code == 200
            assert response.content_type == 'application/atom+xml; charset=utf-8'
            
            # Check caching headers
            assert 'Cache-Control' in response.headers
            assert 'ETag' in response.headers
            
            # Parse XML
            content = response.get_data(as_text=True)
            root = ET.fromstring(content)
            
            # Check Atom structure
            assert root.tag.endswith('feed')  # Namespace may be included
            
            # Check feed metadata
            title = root.find('.//{http://www.w3.org/2005/Atom}title')
            assert title is not None
            assert title.text == 'Blog Feed'
            
            # Check entries (should only include published posts)
            entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')
            assert len(entries) >= 2  # At least our test posts
    
    def test_feed_discovery_links(self):
        """Test that feed discovery links are present in HTML pages."""
        with self.app.app_context():
            client = self.app.test_client()
            
            # Test homepage
            response = client.get('/')
            assert response.status_code == 200
            
            content = response.get_data(as_text=True)
            
            # Check RSS discovery link
            assert 'rel="alternate"' in content
            assert 'type="application/rss+xml"' in content
            assert 'title="RSS Feed"' in content
            assert '/feed.xml' in content
            
            # Check Atom discovery link
            assert 'type="application/atom+xml"' in content
            assert 'title="Atom Feed"' in content
            assert '/atom.xml' in content
    
    def test_feed_content_filtering(self):
        """Test that only published posts appear in feeds."""
        with self.app.app_context():
            client = self.app.test_client()
            
            # Test RSS feed
            rss_response = client.get('/feed.xml')
            rss_content = rss_response.get_data(as_text=True)
            
            # Should contain published posts
            assert 'First Test Post' in rss_content
            assert 'Second Test Post' in rss_content
            
            # Should NOT contain draft posts
            assert 'Draft Post' not in rss_content
            
            # Test Atom feed
            atom_response = client.get('/atom.xml')
            atom_content = atom_response.get_data(as_text=True)
            
            # Should contain published posts
            assert 'First Test Post' in atom_content
            assert 'Second Test Post' in atom_content
            
            # Should NOT contain draft posts
            assert 'Draft Post' not in atom_content
    
    def test_feed_metadata_accuracy(self):
        """Test that feed metadata is accurate."""
        with self.app.app_context():
            client = self.app.test_client()
            response = client.get('/feed.xml')
            content = response.get_data(as_text=True)
            
            # Check author information
            assert 'Test Author' in content
            assert 'test@example.com' in content
            
            # Check site URL
            assert 'http://testsite.com' in content
            
            # Check copyright
            assert 'Copyright 2026' in content
    
    def test_feed_alternate_routes(self):
        """Test that alternate feed routes work."""
        with self.app.app_context():
            client = self.app.test_client()
            
            # Test /rss.xml route
            rss_response = client.get('/rss.xml')
            assert rss_response.status_code == 200
            assert rss_response.content_type == 'application/rss+xml; charset=utf-8'
            
            # Should be same as /feed.xml
            feed_response = client.get('/feed.xml')
            assert rss_response.get_data() == feed_response.get_data()
    
    def test_feed_error_handling(self):
        """Test feed error handling."""
        # This would test error scenarios, but for now we'll just ensure
        # feeds don't crash with empty content
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            
            # Create minimal author profile
            profile = AuthorProfile(
                name="Test Author",
                bio="Test bio",
                mission_statement="Test mission",
                email="test@example.com"
            )
            profile.set_expertise_areas(["Testing"])
            db.session.add(profile)
            db.session.commit()
            
            client = app.test_client()
            
            # Should work even with no posts
            response = client.get('/feed.xml')
            assert response.status_code == 200
            
            content = response.get_data(as_text=True)
            assert '<?xml version' in content
            assert '<rss' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])