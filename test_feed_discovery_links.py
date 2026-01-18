"""
Property-based test for feed discovery links.

This module tests the property that all pages on the site should include
RSS and Atom feed discovery links in the HTML head section.

**Feature: blog-comprehensive-features, Property 4: Feed Discovery Links**
**Validates: Requirements 2.6**
"""

import pytest
from hypothesis import given, strategies as st, settings
from app import create_app
from models import db, Post, User, AuthorProfile
from datetime import datetime, timezone
import re
import string


# Custom strategy for XML-safe text
def xml_safe_text(min_size=1, max_size=100):
    """Generate XML-safe text without control characters."""
    safe_chars = string.ascii_letters + string.digits + string.punctuation + ' '
    safe_chars = ''.join(c for c in safe_chars if ord(c) >= 32 and c not in '<>&"\'')
    return st.text(alphabet=safe_chars, min_size=min_size, max_size=max_size).filter(lambda x: x.strip())


class TestFeedDiscoveryLinks:
    """Property-based test for feed discovery links."""
    
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
    
    def _check_feed_discovery_links(self, html_content):
        """
        Check if HTML content contains proper feed discovery links.
        
        Args:
            html_content: HTML content to check
            
        Returns:
            tuple: (has_rss_link, has_atom_link, rss_details, atom_details)
        """
        # Check for RSS discovery link
        rss_pattern = r'<link[^>]*rel=["\']alternate["\'][^>]*type=["\']application/rss\+xml["\'][^>]*>'
        rss_matches = re.findall(rss_pattern, html_content, re.IGNORECASE)
        
        # Check for Atom discovery link  
        atom_pattern = r'<link[^>]*rel=["\']alternate["\'][^>]*type=["\']application/atom\+xml["\'][^>]*>'
        atom_matches = re.findall(atom_pattern, html_content, re.IGNORECASE)
        
        # Extract details
        rss_details = []
        for match in rss_matches:
            # Check if it has href and title
            href_match = re.search(r'href=["\']([^"\']*)["\']', match)
            title_match = re.search(r'title=["\']([^"\']*)["\']', match)
            rss_details.append({
                'href': href_match.group(1) if href_match else None,
                'title': title_match.group(1) if title_match else None,
                'full_tag': match
            })
        
        atom_details = []
        for match in atom_matches:
            # Check if it has href and title
            href_match = re.search(r'href=["\']([^"\']*)["\']', match)
            title_match = re.search(r'title=["\']([^"\']*)["\']', match)
            atom_details.append({
                'href': href_match.group(1) if href_match else None,
                'title': title_match.group(1) if title_match else None,
                'full_tag': match
            })
        
        return len(rss_matches) > 0, len(atom_matches) > 0, rss_details, atom_details
    
    def test_homepage_has_feed_discovery_links(self):
        """
        Property: The homepage should include RSS and Atom feed discovery links.
        
        **Validates: Requirements 2.6**
        """
        with self.app.app_context():
            client = self.app.test_client()
            response = client.get('/')
            
            assert response.status_code == 200
            html_content = response.get_data(as_text=True)
            
            has_rss, has_atom, rss_details, atom_details = self._check_feed_discovery_links(html_content)
            
            # Should have RSS discovery link
            assert has_rss, "Homepage should contain RSS feed discovery link"
            assert len(rss_details) >= 1, "Should have at least one RSS discovery link"
            
            # Check RSS link details
            rss_link = rss_details[0]
            assert rss_link['href'] is not None, "RSS discovery link should have href attribute"
            assert '/feed.xml' in rss_link['href'] or '/rss.xml' in rss_link['href'], "RSS discovery link should point to feed.xml or rss.xml"
            assert rss_link['title'] is not None, "RSS discovery link should have title attribute"
            assert 'RSS' in rss_link['title'], "RSS discovery link title should mention RSS"
            
            # Should have Atom discovery link
            assert has_atom, "Homepage should contain Atom feed discovery link"
            assert len(atom_details) >= 1, "Should have at least one Atom discovery link"
            
            # Check Atom link details
            atom_link = atom_details[0]
            assert atom_link['href'] is not None, "Atom discovery link should have href attribute"
            assert '/atom.xml' in atom_link['href'], "Atom discovery link should point to atom.xml"
            assert atom_link['title'] is not None, "Atom discovery link should have title attribute"
            assert 'Atom' in atom_link['title'], "Atom discovery link title should mention Atom"
    
    def test_about_page_has_feed_discovery_links(self):
        """
        Property: The about page should include RSS and Atom feed discovery links.
        
        **Validates: Requirements 2.6**
        """
        with self.app.app_context():
            client = self.app.test_client()
            response = client.get('/about')
            
            assert response.status_code == 200
            html_content = response.get_data(as_text=True)
            
            has_rss, has_atom, rss_details, atom_details = self._check_feed_discovery_links(html_content)
            
            # Should have RSS discovery link
            assert has_rss, "About page should contain RSS feed discovery link"
            
            # Should have Atom discovery link
            assert has_atom, "About page should contain Atom feed discovery link"
    
    @given(
        title=xml_safe_text(min_size=1, max_size=100),
        content=xml_safe_text(min_size=10, max_size=500)
    )
    @settings(max_examples=10, deadline=15000)
    def test_post_pages_have_feed_discovery_links(self, title, content):
        """
        Property: Individual post pages should include RSS and Atom feed discovery links.
        
        **Validates: Requirements 2.6**
        """
        with self.app.app_context():
            # Clear any existing posts
            db.session.query(Post).delete()
            db.session.commit()
            
            # Create a published post
            post = Post(
                title=title,
                content=f"<p>{content}</p>",
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            db.session.add(post)
            db.session.commit()
            
            client = self.app.test_client()
            response = client.get(f'/post/{post.id}')
            
            assert response.status_code == 200
            html_content = response.get_data(as_text=True)
            
            has_rss, has_atom, rss_details, atom_details = self._check_feed_discovery_links(html_content)
            
            # Should have RSS discovery link
            assert has_rss, f"Post page for '{title}' should contain RSS feed discovery link"
            
            # Should have Atom discovery link
            assert has_atom, f"Post page for '{title}' should contain Atom feed discovery link"
    
    def test_feed_discovery_links_in_head_section(self):
        """
        Property: Feed discovery links should be in the HTML head section.
        
        **Validates: Requirements 2.6**
        """
        with self.app.app_context():
            client = self.app.test_client()
            response = client.get('/')
            
            assert response.status_code == 200
            html_content = response.get_data(as_text=True)
            
            # Extract head section
            head_match = re.search(r'<head[^>]*>(.*?)</head>', html_content, re.DOTALL | re.IGNORECASE)
            assert head_match, "HTML should have a head section"
            
            head_content = head_match.group(1)
            
            # Check if feed discovery links are in head section
            has_rss, has_atom, rss_details, atom_details = self._check_feed_discovery_links(head_content)
            
            assert has_rss, "RSS feed discovery link should be in the head section"
            assert has_atom, "Atom feed discovery link should be in the head section"
    
    def test_feed_discovery_links_have_correct_attributes(self):
        """
        Property: Feed discovery links should have all required attributes.
        
        **Validates: Requirements 2.6**
        """
        with self.app.app_context():
            client = self.app.test_client()
            response = client.get('/')
            
            assert response.status_code == 200
            html_content = response.get_data(as_text=True)
            
            has_rss, has_atom, rss_details, atom_details = self._check_feed_discovery_links(html_content)
            
            # Check RSS link attributes
            assert has_rss, "Should have RSS discovery link"
            rss_link = rss_details[0]
            
            # Required attributes for RSS discovery link
            assert 'rel=' in rss_link['full_tag'], "RSS link should have rel attribute"
            assert 'alternate' in rss_link['full_tag'], "RSS link should have rel='alternate'"
            assert 'type=' in rss_link['full_tag'], "RSS link should have type attribute"
            assert 'application/rss+xml' in rss_link['full_tag'], "RSS link should have type='application/rss+xml'"
            assert 'href=' in rss_link['full_tag'], "RSS link should have href attribute"
            assert 'title=' in rss_link['full_tag'], "RSS link should have title attribute"
            
            # Check Atom link attributes
            assert has_atom, "Should have Atom discovery link"
            atom_link = atom_details[0]
            
            # Required attributes for Atom discovery link
            assert 'rel=' in atom_link['full_tag'], "Atom link should have rel attribute"
            assert 'alternate' in atom_link['full_tag'], "Atom link should have rel='alternate'"
            assert 'type=' in atom_link['full_tag'], "Atom link should have type attribute"
            assert 'application/atom+xml' in atom_link['full_tag'], "Atom link should have type='application/atom+xml'"
            assert 'href=' in atom_link['full_tag'], "Atom link should have href attribute"
            assert 'title=' in atom_link['full_tag'], "Atom link should have title attribute"
    
    def test_feed_discovery_links_point_to_working_feeds(self):
        """
        Property: Feed discovery links should point to working feed URLs.
        
        **Validates: Requirements 2.6**
        """
        with self.app.app_context():
            client = self.app.test_client()
            response = client.get('/')
            
            assert response.status_code == 200
            html_content = response.get_data(as_text=True)
            
            has_rss, has_atom, rss_details, atom_details = self._check_feed_discovery_links(html_content)
            
            # Test RSS feed URL
            assert has_rss, "Should have RSS discovery link"
            rss_href = rss_details[0]['href']
            
            # Extract path from href (remove domain if present)
            if rss_href.startswith('http'):
                from urllib.parse import urlparse
                rss_path = urlparse(rss_href).path
            else:
                rss_path = rss_href
            
            rss_feed_response = client.get(rss_path)
            assert rss_feed_response.status_code == 200, f"RSS feed URL {rss_path} should return 200"
            assert 'application/rss+xml' in rss_feed_response.content_type, "RSS feed should have correct content type"
            
            # Test Atom feed URL
            assert has_atom, "Should have Atom discovery link"
            atom_href = atom_details[0]['href']
            
            # Extract path from href (remove domain if present)
            if atom_href.startswith('http'):
                from urllib.parse import urlparse
                atom_path = urlparse(atom_href).path
            else:
                atom_path = atom_href
            
            atom_feed_response = client.get(atom_path)
            assert atom_feed_response.status_code == 200, f"Atom feed URL {atom_path} should return 200"
            assert 'application/atom+xml' in atom_feed_response.content_type, "Atom feed should have correct content type"
    
    @given(
        num_posts=st.integers(min_value=0, max_value=5)
    )
    @settings(max_examples=5, deadline=15000)
    def test_feed_discovery_links_present_regardless_of_content(self, num_posts):
        """
        Property: Feed discovery links should be present regardless of whether there are posts.
        
        **Validates: Requirements 2.6**
        """
        with self.app.app_context():
            # Clear any existing posts
            db.session.query(Post).delete()
            db.session.commit()
            
            # Create variable number of posts
            for i in range(num_posts):
                post = Post(
                    title=f"Test Post {i+1}",
                    content=f"<p>Content for test post {i+1}</p>",
                    status='published',
                    published_at=datetime.now(timezone.utc)
                )
                db.session.add(post)
            
            if num_posts > 0:
                db.session.commit()
            
            client = self.app.test_client()
            response = client.get('/')
            
            assert response.status_code == 200
            html_content = response.get_data(as_text=True)
            
            has_rss, has_atom, rss_details, atom_details = self._check_feed_discovery_links(html_content)
            
            # Should have feed discovery links regardless of content
            assert has_rss, f"Should have RSS discovery link even with {num_posts} posts"
            assert has_atom, f"Should have Atom discovery link even with {num_posts} posts"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])