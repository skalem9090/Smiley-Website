"""
Property-Based Tests for Open Graph Tag Inclusion

**Validates: Requirements 6.2**

This module tests that Open Graph tags are properly included in all page types
to ensure proper social media sharing functionality.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from flask import url_for
from bs4 import BeautifulSoup
from app import create_app
from models import db, Post, AuthorProfile, User
from post_manager import PostManager
from about_page_manager import AboutPageManager
from datetime import datetime, timezone


def create_test_app():
    """Create test Flask application."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app


class TestOpenGraphTagInclusion:
    """Property tests for Open Graph tag inclusion across all page types."""

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=20, max_size=1000).filter(lambda x: x.strip()),
        category=st.sampled_from(['wealth', 'health', 'happiness'])
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_post_pages_include_open_graph_tags(self, title, content, category):
        """
        Property: All post pages must include essential Open Graph tags.
        
        **Validates: Requirements 6.2**
        
        This test ensures that individual post pages include the required
        Open Graph meta tags for proper social media sharing.
        """
        app = create_test_app()
        
        with app.app_context():
            db.create_all()
            
            # Create admin user for tests
            admin = db.session.query(User).filter_by(username='testadmin').first()
            if not admin:
                admin = User(username='testadmin', is_admin=True)
                admin.set_password('testpass')
                db.session.add(admin)
                db.session.commit()
            
            # Create a published post
            post = PostManager.create_post(
                title=title,
                content=content,
                category=category,
                status='published'
            )
            
            # Get the post page
            with app.test_client() as client:
                response = client.get(f'/post/{post.id}')
                assert response.status_code == 200
                
                # Parse HTML content
                soup = BeautifulSoup(response.data, 'html.parser')
                
                # Check for essential Open Graph tags
                og_title = soup.find('meta', property='og:title')
                og_description = soup.find('meta', property='og:description')
                og_type = soup.find('meta', property='og:type')
                og_url = soup.find('meta', property='og:url')
                
                # Verify Open Graph tags are present
                assert og_title is not None, "Post pages must include og:title tag"
                assert og_description is not None, "Post pages must include og:description tag"
                assert og_type is not None, "Post pages must include og:type tag"
                assert og_url is not None, "Post pages must include og:url tag"
                
                # Verify tag content is meaningful
                assert og_title.get('content', '').strip() != '', "og:title must have content"
                assert og_description.get('content', '').strip() != '', "og:description must have content"
                assert og_type.get('content') == 'article', "Post pages must have og:type='article'"
                assert f'/post/{post.id}' in og_url.get('content', ''), "og:url must reference the post URL"
            
            # Clean up
            db.session.remove()
            db.drop_all()

    def test_homepage_includes_open_graph_tags(self):
        """
        Property: The homepage must include essential Open Graph tags.
        
        **Validates: Requirements 6.2**
        
        This test ensures that the homepage includes the required
        Open Graph meta tags for proper social media sharing.
        """
        app = create_test_app()
        
        with app.app_context():
            db.create_all()
            
            # Create admin user for tests
            admin = db.session.query(User).filter_by(username='testadmin').first()
            if not admin:
                admin = User(username='testadmin', is_admin=True)
                admin.set_password('testpass')
                db.session.add(admin)
                db.session.commit()
            
            with app.test_client() as client:
                response = client.get('/')
                assert response.status_code == 200
                
                # Parse HTML content
                soup = BeautifulSoup(response.data, 'html.parser')
                
                # Check for essential Open Graph tags
                og_title = soup.find('meta', property='og:title')
                og_description = soup.find('meta', property='og:description')
                og_type = soup.find('meta', property='og:type')
                og_url = soup.find('meta', property='og:url')
                
                # Verify Open Graph tags are present
                assert og_title is not None, "Homepage must include og:title tag"
                assert og_description is not None, "Homepage must include og:description tag"
                assert og_type is not None, "Homepage must include og:type tag"
                assert og_url is not None, "Homepage must include og:url tag"
                
                # Verify tag content is meaningful
                assert og_title.get('content', '').strip() != '', "og:title must have content"
                assert og_description.get('content', '').strip() != '', "og:description must have content"
                assert og_type.get('content') == 'website', "Homepage must have og:type='website'"
            
            # Clean up
            db.session.remove()
            db.drop_all()

    def test_about_page_includes_open_graph_tags(self):
        """
        Property: The about page must include essential Open Graph tags.
        
        **Validates: Requirements 6.2**
        
        This test ensures that the about page includes the required
        Open Graph meta tags for proper social media sharing.
        """
        app = create_test_app()
        
        with app.app_context():
            db.create_all()
            
            # Create admin user for tests
            admin = db.session.query(User).filter_by(username='testadmin').first()
            if not admin:
                admin = User(username='testadmin', is_admin=True)
                admin.set_password('testpass')
                db.session.add(admin)
                db.session.commit()
            
            # Ensure author profile exists
            about_manager = AboutPageManager(app)
            profile = about_manager.get_author_profile()
            
            with app.test_client() as client:
                response = client.get('/about')
                assert response.status_code == 200
                
                # Parse HTML content
                soup = BeautifulSoup(response.data, 'html.parser')
                
                # Check for essential Open Graph tags
                og_title = soup.find('meta', property='og:title')
                og_description = soup.find('meta', property='og:description')
                og_type = soup.find('meta', property='og:type')
                og_url = soup.find('meta', property='og:url')
                
                # Verify Open Graph tags are present
                assert og_title is not None, "About page must include og:title tag"
                assert og_description is not None, "About page must include og:description tag"
                assert og_type is not None, "About page must include og:type tag"
                assert og_url is not None, "About page must include og:url tag"
                
                # Verify tag content is meaningful
                assert og_title.get('content', '').strip() != '', "og:title must have content"
                assert og_description.get('content', '').strip() != '', "og:description must have content"
                assert og_type.get('content') == 'profile', "About page must have og:type='profile'"
                assert '/about' in og_url.get('content', ''), "og:url must reference the about URL"
            
            # Clean up
            db.session.remove()
            db.drop_all()

    @given(
        search_query=st.text(min_size=1, max_size=50).filter(lambda x: x.strip())
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_search_pages_include_open_graph_tags(self, search_query):
        """
        Property: Search result pages must include essential Open Graph tags.
        
        **Validates: Requirements 6.2**
        
        This test ensures that search result pages include the required
        Open Graph meta tags for proper social media sharing.
        """
        app = create_test_app()
        
        with app.app_context():
            db.create_all()
            
            # Create admin user for tests
            admin = db.session.query(User).filter_by(username='testadmin').first()
            if not admin:
                admin = User(username='testadmin', is_admin=True)
                admin.set_password('testpass')
                db.session.add(admin)
                db.session.commit()
            
            with app.test_client() as client:
                response = client.get(f'/search?q={search_query}')
                assert response.status_code == 200
                
                # Parse HTML content
                soup = BeautifulSoup(response.data, 'html.parser')
                
                # Check for essential Open Graph tags
                og_title = soup.find('meta', property='og:title')
                og_description = soup.find('meta', property='og:description')
                og_type = soup.find('meta', property='og:type')
                og_url = soup.find('meta', property='og:url')
                
                # Verify Open Graph tags are present
                assert og_title is not None, "Search pages must include og:title tag"
                assert og_description is not None, "Search pages must include og:description tag"
                assert og_type is not None, "Search pages must include og:type tag"
                assert og_url is not None, "Search pages must include og:url tag"
                
                # Verify tag content is meaningful
                assert og_title.get('content', '').strip() != '', "og:title must have content"
                assert og_description.get('content', '').strip() != '', "og:description must have content"
                assert og_type.get('content') == 'website', "Search pages must have og:type='website'"
            
            # Clean up
            db.session.remove()
            db.drop_all()

    @given(
        category=st.sampled_from(['wealth', 'health', 'happiness'])
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_category_pages_include_open_graph_tags(self, category):
        """
        Property: Category pages must include essential Open Graph tags.
        
        **Validates: Requirements 6.2**
        
        This test ensures that category pages include the required
        Open Graph meta tags for proper social media sharing.
        """
        app = create_test_app()
        
        with app.app_context():
            db.create_all()
            
            # Create admin user for tests
            admin = db.session.query(User).filter_by(username='testadmin').first()
            if not admin:
                admin = User(username='testadmin', is_admin=True)
                admin.set_password('testpass')
                db.session.add(admin)
                db.session.commit()
            
            with app.test_client() as client:
                response = client.get(f'/explore?category={category}')
                assert response.status_code == 200
                
                # Parse HTML content
                soup = BeautifulSoup(response.data, 'html.parser')
                
                # Check for essential Open Graph tags
                og_title = soup.find('meta', property='og:title')
                og_description = soup.find('meta', property='og:description')
                og_type = soup.find('meta', property='og:type')
                og_url = soup.find('meta', property='og:url')
                
                # Verify Open Graph tags are present
                assert og_title is not None, "Category pages must include og:title tag"
                assert og_description is not None, "Category pages must include og:description tag"
                assert og_type is not None, "Category pages must include og:type tag"
                assert og_url is not None, "Category pages must include og:url tag"
                
                # Verify tag content is meaningful
                assert og_title.get('content', '').strip() != '', "og:title must have content"
                assert og_description.get('content', '').strip() != '', "og:description must have content"
                assert og_type.get('content') == 'website', "Category pages must have og:type='website'"
            
            # Clean up
            db.session.remove()
            db.drop_all()

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=20, max_size=1000).filter(lambda x: x.strip()),
        category=st.sampled_from(['wealth', 'health', 'happiness'])
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_open_graph_image_tags_when_available(self, title, content, category):
        """
        Property: Open Graph image tags must be included when images are available.
        
        **Validates: Requirements 6.2**
        
        This test ensures that when posts have images, the appropriate
        Open Graph image tags are included for rich social media previews.
        """
        app = create_test_app()
        
        with app.app_context():
            db.create_all()
            
            # Create admin user for tests
            admin = db.session.query(User).filter_by(username='testadmin').first()
            if not admin:
                admin = User(username='testadmin', is_admin=True)
                admin.set_password('testpass')
                db.session.add(admin)
                db.session.commit()
            
            # Create a published post
            post = PostManager.create_post(
                title=title,
                content=content,
                category=category,
                status='published'
            )
            
            with app.test_client() as client:
                response = client.get(f'/post/{post.id}')
                assert response.status_code == 200
                
                # Parse HTML content
                soup = BeautifulSoup(response.data, 'html.parser')
                
                # Check if post content contains images
                post_images = soup.find_all('img')
                og_image = soup.find('meta', property='og:image')
                
                # If images exist in content, og:image should be present
                if post_images:
                    assert og_image is not None, "Posts with images must include og:image tag"
                    assert og_image.get('content', '').strip() != '', "og:image must have content when images are present"
                
                # Always check for optional og:image:alt if og:image exists
                if og_image:
                    og_image_alt = soup.find('meta', property='og:image:alt')
                    # og:image:alt is recommended but not required
                    if og_image_alt:
                        assert og_image_alt.get('content', '').strip() != '', "og:image:alt must have content when present"
            
            # Clean up
            db.session.remove()
            db.drop_all()

    def test_open_graph_site_name_consistency(self):
        """
        Property: Open Graph site name must be consistent across all pages.
        
        **Validates: Requirements 6.2**
        
        This test ensures that the og:site_name tag is consistent
        across all pages of the site.
        """
        app = create_test_app()
        
        with app.app_context():
            db.create_all()
            
            # Create admin user for tests
            admin = db.session.query(User).filter_by(username='testadmin').first()
            if not admin:
                admin = User(username='testadmin', is_admin=True)
                admin.set_password('testpass')
                db.session.add(admin)
                db.session.commit()
            
            pages_to_test = ['/', '/about']
            site_names = []
            
            with app.test_client() as client:
                for page in pages_to_test:
                    response = client.get(page)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.data, 'html.parser')
                        og_site_name = soup.find('meta', property='og:site_name')
                        
                        if og_site_name:
                            site_name = og_site_name.get('content', '').strip()
                            if site_name:
                                site_names.append(site_name)
                
                # If site names are found, they should all be the same
                if site_names:
                    assert len(set(site_names)) == 1, "og:site_name must be consistent across all pages"
                    assert site_names[0] != '', "og:site_name must not be empty"
            
            # Clean up
            db.session.remove()
            db.drop_all()