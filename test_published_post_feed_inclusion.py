"""
Property-based test for published post feed inclusion.

This module tests the property that any published post should automatically
appear in both RSS and Atom feeds with all required metadata.

**Feature: blog-comprehensive-features, Property 2: Published Post Feed Inclusion**
**Validates: Requirements 2.3, 2.4**
"""

import pytest
from hypothesis import given, strategies as st, settings
from app import create_app
from models import db, Post, User, AuthorProfile
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import re
import string


# Custom strategy for XML-safe text
def xml_safe_text(min_size=1, max_size=200):
    """Generate XML-safe text without control characters."""
    # Use printable ASCII characters excluding control characters
    safe_chars = string.ascii_letters + string.digits + string.punctuation + ' '
    # Remove characters that might cause XML issues
    safe_chars = ''.join(c for c in safe_chars if ord(c) >= 32 and c not in '<>&"\'')
    return st.text(alphabet=safe_chars, min_size=min_size, max_size=max_size).filter(lambda x: x.strip())


class TestPublishedPostFeedInclusion:
    """Property-based test for published post feed inclusion."""
    
    def setup_method(self):
        """Set up test environment."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SITE_URL'] = 'http://testsite.com'
        
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
        title=xml_safe_text(min_size=1, max_size=100),
        content=xml_safe_text(min_size=10, max_size=500),
        summary=st.one_of(st.none(), xml_safe_text(min_size=1, max_size=200)),
        category=st.one_of(st.none(), xml_safe_text(min_size=1, max_size=30)),
        tags=st.one_of(st.none(), xml_safe_text(min_size=1, max_size=50))
    )
    @settings(max_examples=20, deadline=15000)
    def test_published_post_appears_in_feeds(self, title, content, summary, category, tags):
        """
        Property: Any published post should appear in both RSS and Atom feeds
        with all required metadata (title, summary, publication date, author, categories).
        
        **Validates: Requirements 2.3, 2.4**
        """
        with self.app.app_context():
            # Clear any existing posts
            db.session.query(Post).delete()
            db.session.commit()
            
            # Create a published post with the generated data
            post = Post(
                title=title,
                content=f"<p>{content}</p>",
                summary=summary,
                status='published',
                published_at=datetime.now(timezone.utc),
                category=category,
                tags=tags
            )
            db.session.add(post)
            db.session.commit()
            
            client = self.app.test_client()
            
            # Test RSS feed
            rss_response = client.get('/feed.xml')
            assert rss_response.status_code == 200
            rss_content = rss_response.get_data(as_text=True)
            
            # Parse RSS XML
            rss_root = ET.fromstring(rss_content)
            rss_items = rss_root.findall('.//item')
            
            # Post should appear in RSS feed
            assert len(rss_items) >= 1, f"Published post '{title}' not found in RSS feed"
            
            # Find our specific post in RSS
            post_found_in_rss = False
            for item in rss_items:
                item_title = item.find('title')
                if item_title is not None and item_title.text == title:
                    post_found_in_rss = True
                    
                    # Verify required metadata in RSS
                    # Title
                    assert item_title.text == title
                    
                    # Link
                    item_link = item.find('link')
                    assert item_link is not None
                    assert f"/post/{post.id}" in item_link.text
                    
                    # Description (summary or content excerpt)
                    item_description = item.find('description')
                    assert item_description is not None
                    if summary:
                        assert summary in item_description.text
                    else:
                        # Should contain content excerpt
                        clean_content = re.sub(r'<[^>]+>', '', content)
                        assert any(word in item_description.text for word in clean_content.split()[:3])
                    
                    # Publication date
                    item_pubdate = item.find('pubDate')
                    assert item_pubdate is not None
                    assert item_pubdate.text is not None
                    
                    # Author
                    item_author = item.find('author')
                    if item_author is not None:
                        assert 'test@example.com' in item_author.text
                    
                    # Category (if provided)
                    if category:
                        item_categories = item.findall('category')
                        category_texts = [cat.text for cat in item_categories if cat.text]
                        assert category in category_texts
                    
                    # GUID
                    item_guid = item.find('guid')
                    assert item_guid is not None
                    assert f"/post/{post.id}" in item_guid.text
                    
                    break
            
            assert post_found_in_rss, f"Published post '{title}' not found in RSS feed items"
            
            # Test Atom feed
            atom_response = client.get('/atom.xml')
            assert atom_response.status_code == 200
            atom_content = atom_response.get_data(as_text=True)
            
            # Parse Atom XML
            atom_root = ET.fromstring(atom_content)
            atom_entries = atom_root.findall('.//{http://www.w3.org/2005/Atom}entry')
            
            # Post should appear in Atom feed
            assert len(atom_entries) >= 1, f"Published post '{title}' not found in Atom feed"
            
            # Find our specific post in Atom
            post_found_in_atom = False
            for entry in atom_entries:
                entry_title = entry.find('.//{http://www.w3.org/2005/Atom}title')
                if entry_title is not None and entry_title.text == title:
                    post_found_in_atom = True
                    
                    # Verify required metadata in Atom
                    # Title
                    assert entry_title.text == title
                    
                    # Link
                    entry_link = entry.find('.//{http://www.w3.org/2005/Atom}link')
                    assert entry_link is not None
                    href = entry_link.get('href')
                    assert href is not None
                    assert f"/post/{post.id}" in href
                    
                    # Summary or content
                    entry_summary = entry.find('.//{http://www.w3.org/2005/Atom}summary')
                    entry_content = entry.find('.//{http://www.w3.org/2005/Atom}content')
                    assert entry_summary is not None or entry_content is not None
                    
                    if summary and entry_summary is not None:
                        assert summary in entry_summary.text
                    
                    # Publication date
                    entry_published = entry.find('.//{http://www.w3.org/2005/Atom}published')
                    entry_updated = entry.find('.//{http://www.w3.org/2005/Atom}updated')
                    assert entry_published is not None or entry_updated is not None
                    
                    # Author
                    entry_author = entry.find('.//{http://www.w3.org/2005/Atom}author')
                    if entry_author is not None:
                        author_name = entry_author.find('.//{http://www.w3.org/2005/Atom}name')
                        author_email = entry_author.find('.//{http://www.w3.org/2005/Atom}email')
                        assert author_name is not None or author_email is not None
                        if author_email is not None:
                            assert 'test@example.com' in author_email.text
                    
                    # ID
                    entry_id = entry.find('.//{http://www.w3.org/2005/Atom}id')
                    assert entry_id is not None
                    assert f"/post/{post.id}" in entry_id.text
                    
                    break
            
            assert post_found_in_atom, f"Published post '{title}' not found in Atom feed entries"
    
    @given(
        num_posts=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=10, deadline=20000)
    def test_multiple_published_posts_all_appear_in_feeds(self, num_posts):
        """
        Property: All published posts should appear in feeds, regardless of quantity.
        
        **Validates: Requirements 2.3, 2.4**
        """
        with self.app.app_context():
            # Clear any existing posts
            db.session.query(Post).delete()
            db.session.commit()
            
            # Create multiple published posts
            created_posts = []
            for i in range(num_posts):
                post = Post(
                    title=f"Test Post {i+1}",
                    content=f"<p>This is test post number {i+1} content.</p>",
                    summary=f"Summary for test post {i+1}",
                    status='published',
                    published_at=datetime.now(timezone.utc),
                    category=f"category{i+1}"
                )
                db.session.add(post)
                created_posts.append(post)
            
            db.session.commit()
            
            client = self.app.test_client()
            
            # Test RSS feed
            rss_response = client.get('/feed.xml')
            assert rss_response.status_code == 200
            rss_content = rss_response.get_data(as_text=True)
            
            # All posts should appear in RSS
            for post in created_posts:
                assert post.title in rss_content, f"Post '{post.title}' missing from RSS feed"
            
            # Test Atom feed
            atom_response = client.get('/atom.xml')
            assert atom_response.status_code == 200
            atom_content = atom_response.get_data(as_text=True)
            
            # All posts should appear in Atom
            for post in created_posts:
                assert post.title in atom_content, f"Post '{post.title}' missing from Atom feed"
    
    def test_draft_posts_excluded_from_feeds(self):
        """
        Property: Draft posts should never appear in feeds, only published posts.
        
        **Validates: Requirements 2.3, 2.8**
        """
        with self.app.app_context():
            # Clear any existing posts
            db.session.query(Post).delete()
            db.session.commit()
            
            # Create a published post
            published_post = Post(
                title="Published Post",
                content="<p>This is a published post.</p>",
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            
            # Create a draft post
            draft_post = Post(
                title="Draft Post",
                content="<p>This is a draft post.</p>",
                status='draft'
            )
            
            db.session.add_all([published_post, draft_post])
            db.session.commit()
            
            client = self.app.test_client()
            
            # Test RSS feed
            rss_response = client.get('/feed.xml')
            rss_content = rss_response.get_data(as_text=True)
            
            # Published post should appear
            assert "Published Post" in rss_content
            # Draft post should NOT appear
            assert "Draft Post" not in rss_content
            
            # Test Atom feed
            atom_response = client.get('/atom.xml')
            atom_content = atom_response.get_data(as_text=True)
            
            # Published post should appear
            assert "Published Post" in atom_content
            # Draft post should NOT appear
            assert "Draft Post" not in atom_content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])