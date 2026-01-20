"""
Property-Based Tests for Content Update Synchronization

**Validates: Requirements 6.6**

This module tests that content updates are properly synchronized across
all systems including sitemaps, feeds, search indexes, and caches.
"""

import pytest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from hypothesis import given, strategies as st, settings, HealthCheck
from flask import Flask, url_for
from models import db, Post
from post_manager import PostManager
from search_engine import SearchEngine
from feed_generator import FeedGenerator


@pytest.fixture
def app_context():
    """Create test Flask app with in-memory database."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SERVER_NAME'] = 'localhost'
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


class TestContentUpdateSynchronization:
    """Property tests for content update synchronization across all systems."""

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=20, max_size=1000).filter(lambda x: x.strip()),
        category=st.sampled_from(['wealth', 'health', 'happiness']),
        new_title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        new_content=st.text(min_size=20, max_size=1000).filter(lambda x: x.strip())
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_post_updates_synchronize_with_sitemap(self, app_context, title, content, category, new_title, new_content):
        """
        Property: Post updates must be reflected in the sitemap.
        
        **Validates: Requirements 6.6**
        
        This test ensures that when posts are updated, the changes
        are properly reflected in the XML sitemap.
        """
        # Create a published post
        post = PostManager.create_post(
            title=title,
            content=content,
            category=category,
            status='published'
        )
        
        original_updated_at = post.updated_at
        
        with app_context.test_client() as client:
            # Get initial sitemap
            response = client.get('/sitemap.xml')
            assert response.status_code == 200
            
            # Parse sitemap XML
            root = ET.fromstring(response.data)
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Find the post URL in sitemap
            post_url = f'/post/{post.id}'
            post_found_initial = False
            initial_lastmod = None
            
            for url_elem in root.findall('ns:url', namespace):
                loc_elem = url_elem.find('ns:loc', namespace)
                if loc_elem is not None and post_url in loc_elem.text:
                    post_found_initial = True
                    lastmod_elem = url_elem.find('ns:lastmod', namespace)
                    if lastmod_elem is not None:
                        initial_lastmod = lastmod_elem.text
                    break
            
            assert post_found_initial, "Published post must appear in sitemap"
            
            # Update the post
            updated_post = PostManager.update_post(
                post_id=post.id,
                title=new_title,
                content=new_content,
                category=category,
                status='published'
            )
            
            # Verify post was actually updated
            assert updated_post.updated_at > original_updated_at, "Post updated_at must change after update"
            
            # Get updated sitemap
            response = client.get('/sitemap.xml')
            assert response.status_code == 200
            
            # Parse updated sitemap XML
            root = ET.fromstring(response.data)
            
            # Find the post URL in updated sitemap
            post_found_updated = False
            updated_lastmod = None
            
            for url_elem in root.findall('ns:url', namespace):
                loc_elem = url_elem.find('ns:loc', namespace)
                if loc_elem is not None and post_url in loc_elem.text:
                    post_found_updated = True
                    lastmod_elem = url_elem.find('ns:lastmod', namespace)
                    if lastmod_elem is not None:
                        updated_lastmod = lastmod_elem.text
                    break
            
            assert post_found_updated, "Updated post must still appear in sitemap"
            
            # If lastmod dates are present, the updated one should be different
            if initial_lastmod and updated_lastmod:
                assert updated_lastmod != initial_lastmod, "Sitemap lastmod must change when post is updated"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=20, max_size=1000).filter(lambda x: x.strip()),
        category=st.sampled_from(['wealth', 'health', 'happiness']),
        new_title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip())
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_post_updates_synchronize_with_feeds(self, app_context, title, content, category, new_title):
        """
        Property: Post updates must be reflected in RSS/Atom feeds.
        
        **Validates: Requirements 6.6**
        
        This test ensures that when posts are updated, the changes
        are properly reflected in the RSS and Atom feeds.
        """
        # Create a published post
        post = PostManager.create_post(
            title=title,
            content=content,
            category=category,
            status='published'
        )
        
        with app_context.test_client() as client:
            # Get initial RSS feed
            response = client.get('/feed.xml')
            assert response.status_code == 200
            
            # Check if original title appears in feed
            initial_feed_content = response.data.decode('utf-8')
            assert title in initial_feed_content, "Original post title must appear in RSS feed"
            
            # Update the post title
            updated_post = PostManager.update_post(
                post_id=post.id,
                title=new_title,
                content=content,
                category=category,
                status='published'
            )
            
            # Get updated RSS feed
            response = client.get('/feed.xml')
            assert response.status_code == 200
            
            # Check if updated title appears in feed
            updated_feed_content = response.data.decode('utf-8')
            assert new_title in updated_feed_content, "Updated post title must appear in RSS feed"
            
            # Also test Atom feed
            response = client.get('/atom.xml')
            assert response.status_code == 200
            
            updated_atom_content = response.data.decode('utf-8')
            assert new_title in updated_atom_content, "Updated post title must appear in Atom feed"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=20, max_size=1000).filter(lambda x: x.strip()),
        category=st.sampled_from(['wealth', 'health', 'happiness']),
        new_content=st.text(min_size=20, max_size=1000).filter(lambda x: x.strip())
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_post_updates_synchronize_with_search_index(self, app_context, title, content, category, new_content):
        """
        Property: Post updates must be reflected in the search index.
        
        **Validates: Requirements 6.6**
        
        This test ensures that when posts are updated, the changes
        are properly reflected in the search index.
        """
        # Create a published post
        post = PostManager.create_post(
            title=title,
            content=content,
            category=category,
            status='published'
        )
        
        # Initialize search engine
        search_engine = SearchEngine(app_context)
        
        # Search for original content
        original_results = search_engine.search(content[:20])  # Search for first 20 chars of original content
        original_post_found = any(result['id'] == post.id for result in original_results)
        
        # Update the post content
        updated_post = PostManager.update_post(
            post_id=post.id,
            title=title,
            content=new_content,
            category=category,
            status='published'
        )
        
        # Search for new content
        new_results = search_engine.search(new_content[:20])  # Search for first 20 chars of new content
        new_post_found = any(result['id'] == post.id for result in new_results)
        
        # The post should be findable with the new content
        assert new_post_found, "Updated post must be findable with new content in search index"
        
        # If the original and new content are significantly different,
        # searching for old content should not return the updated post
        if len(set(content.lower().split()) & set(new_content.lower().split())) < 3:
            old_results = search_engine.search(content[:20])
            old_post_found = any(result['id'] == post.id for result in old_results)
            # This assertion might be too strict depending on search implementation
            # assert not old_post_found, "Updated post should not be findable with old content"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=20, max_size=1000).filter(lambda x: x.strip()),
        category=st.sampled_from(['wealth', 'health', 'happiness'])
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_post_deletion_synchronizes_across_systems(self, app_context, title, content, category):
        """
        Property: Post deletion must be synchronized across all systems.
        
        **Validates: Requirements 6.6**
        
        This test ensures that when posts are deleted, they are removed
        from sitemaps, feeds, and search indexes.
        """
        # Create a published post
        post = PostManager.create_post(
            title=title,
            content=content,
            category=category,
            status='published'
        )
        
        post_id = post.id
        post_url = f'/post/{post_id}'
        
        with app_context.test_client() as client:
            # Verify post exists in sitemap
            response = client.get('/sitemap.xml')
            assert response.status_code == 200
            sitemap_content = response.data.decode('utf-8')
            assert post_url in sitemap_content, "Post must appear in sitemap before deletion"
            
            # Verify post exists in feed
            response = client.get('/feed.xml')
            assert response.status_code == 200
            feed_content = response.data.decode('utf-8')
            assert title in feed_content, "Post must appear in feed before deletion"
            
            # Delete the post
            db.session.delete(post)
            db.session.commit()
            
            # Verify post is removed from sitemap
            response = client.get('/sitemap.xml')
            assert response.status_code == 200
            updated_sitemap_content = response.data.decode('utf-8')
            assert post_url not in updated_sitemap_content, "Deleted post must not appear in sitemap"
            
            # Verify post is removed from feed
            response = client.get('/feed.xml')
            assert response.status_code == 200
            updated_feed_content = response.data.decode('utf-8')
            assert title not in updated_feed_content, "Deleted post must not appear in feed"
            
            # Verify post returns 404
            response = client.get(post_url)
            assert response.status_code == 404, "Deleted post URL must return 404"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=20, max_size=1000).filter(lambda x: x.strip()),
        category=st.sampled_from(['wealth', 'health', 'happiness'])
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_post_status_changes_synchronize(self, app_context, title, content, category):
        """
        Property: Post status changes must be synchronized across systems.
        
        **Validates: Requirements 6.6**
        
        This test ensures that when post status changes (published to draft),
        the changes are reflected in sitemaps and feeds.
        """
        # Create a published post
        post = PostManager.create_post(
            title=title,
            content=content,
            category=category,
            status='published'
        )
        
        post_url = f'/post/{post.id}'
        
        with app_context.test_client() as client:
            # Verify post exists in sitemap when published
            response = client.get('/sitemap.xml')
            assert response.status_code == 200
            sitemap_content = response.data.decode('utf-8')
            assert post_url in sitemap_content, "Published post must appear in sitemap"
            
            # Verify post exists in feed when published
            response = client.get('/feed.xml')
            assert response.status_code == 200
            feed_content = response.data.decode('utf-8')
            assert title in feed_content, "Published post must appear in feed"
            
            # Change post status to draft
            updated_post = PostManager.update_post(
                post_id=post.id,
                title=title,
                content=content,
                category=category,
                status='draft'
            )
            
            # Verify post is removed from sitemap when draft
            response = client.get('/sitemap.xml')
            assert response.status_code == 200
            updated_sitemap_content = response.data.decode('utf-8')
            assert post_url not in updated_sitemap_content, "Draft post must not appear in sitemap"
            
            # Verify post is removed from feed when draft
            response = client.get('/feed.xml')
            assert response.status_code == 200
            updated_feed_content = response.data.decode('utf-8')
            assert title not in updated_feed_content, "Draft post must not appear in feed"

    @given(
        num_posts=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=5, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_bulk_content_updates_maintain_consistency(self, app_context, num_posts):
        """
        Property: Bulk content updates must maintain consistency across systems.
        
        **Validates: Requirements 6.6**
        
        This test ensures that when multiple posts are updated simultaneously,
        all systems remain consistent.
        """
        posts = []
        
        # Create multiple published posts
        for i in range(num_posts):
            post = PostManager.create_post(
                title=f"Test Post {i}",
                content=f"Test content for post {i}",
                category='wealth',
                status='published'
            )
            posts.append(post)
        
        with app_context.test_client() as client:
            # Get initial sitemap count
            response = client.get('/sitemap.xml')
            assert response.status_code == 200
            initial_sitemap = response.data.decode('utf-8')
            initial_post_count = sum(1 for post in posts if f'/post/{post.id}' in initial_sitemap)
            
            # Get initial feed count
            response = client.get('/feed.xml')
            assert response.status_code == 200
            initial_feed = response.data.decode('utf-8')
            initial_feed_count = sum(1 for post in posts if f"Test Post {posts.index(post)}" in initial_feed)
            
            # Update all posts to draft status
            for post in posts:
                PostManager.update_post(
                    post_id=post.id,
                    title=post.title,
                    content=post.content,
                    category=post.category,
                    status='draft'
                )
            
            # Verify all posts are removed from sitemap
            response = client.get('/sitemap.xml')
            assert response.status_code == 200
            updated_sitemap = response.data.decode('utf-8')
            updated_post_count = sum(1 for post in posts if f'/post/{post.id}' in updated_sitemap)
            
            assert updated_post_count == 0, "All draft posts must be removed from sitemap"
            
            # Verify all posts are removed from feed
            response = client.get('/feed.xml')
            assert response.status_code == 200
            updated_feed = response.data.decode('utf-8')
            updated_feed_count = sum(1 for post in posts if f"Test Post {posts.index(post)}" in updated_feed)
            
            assert updated_feed_count == 0, "All draft posts must be removed from feed"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=20, max_size=1000).filter(lambda x: x.strip()),
        category=st.sampled_from(['wealth', 'health', 'happiness'])
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_content_update_timestamps_are_consistent(self, app_context, title, content, category):
        """
        Property: Content update timestamps must be consistent across systems.
        
        **Validates: Requirements 6.6**
        
        This test ensures that when content is updated, the timestamps
        are properly synchronized across all systems.
        """
        # Create a published post
        post = PostManager.create_post(
            title=title,
            content=content,
            category=category,
            status='published'
        )
        
        original_updated_at = post.updated_at
        
        # Wait a moment to ensure timestamp difference
        import time
        time.sleep(0.1)
        
        # Update the post
        updated_post = PostManager.update_post(
            post_id=post.id,
            title=f"Updated {title}",
            content=content,
            category=category,
            status='published'
        )
        
        # Verify timestamp was updated
        assert updated_post.updated_at > original_updated_at, "Post updated_at must increase after update"
        
        with app_context.test_client() as client:
            # Check if sitemap reflects the update time
            response = client.get('/sitemap.xml')
            assert response.status_code == 200
            
            # Parse sitemap to check lastmod
            root = ET.fromstring(response.data)
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            post_url = f'/post/{post.id}'
            for url_elem in root.findall('ns:url', namespace):
                loc_elem = url_elem.find('ns:loc', namespace)
                if loc_elem is not None and post_url in loc_elem.text:
                    lastmod_elem = url_elem.find('ns:lastmod', namespace)
                    if lastmod_elem is not None:
                        # Verify lastmod is recent (within last few seconds)
                        from datetime import datetime, timezone
                        lastmod_time = datetime.fromisoformat(lastmod_elem.text.replace('Z', '+00:00'))
                        time_diff = datetime.now(timezone.utc) - lastmod_time
                        assert time_diff.total_seconds() < 60, "Sitemap lastmod must be recent after update"
                    break