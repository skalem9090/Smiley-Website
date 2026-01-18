"""
Property-based test for draft post visibility.

**Feature: enhanced-content-management, Property 2: Draft Post Visibility**

**Validates: Requirements 1.3**

This test validates that posts with draft status are properly managed at the data layer
and that the PostManager correctly handles draft post filtering and status management.
"""

import pytest
from datetime import datetime, timezone
from hypothesis import given, strategies as st, settings, HealthCheck

from app import create_app
from models import db, Post, User
from post_manager import PostManager


class TestDraftPostVisibility:
    """Test draft post visibility using property-based testing."""

    @pytest.fixture
    def app(self):
        """Create test Flask application."""
        app = create_app()
        app.config['TESTING'] = True
        # Use a unique in-memory database for each test
        import uuid
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///:memory:?cache=shared&uri=true&id={uuid.uuid4()}'
        app.config['WTF_CSRF_ENABLED'] = False
        return app

    @pytest.fixture
    def app_context(self, app):
        """Create application context for testing."""
        with app.app_context():
            db.create_all()
            
            # Clear any existing posts
            Post.query.delete()
            db.session.commit()
            
            # Create test user
            user = User(username='testuser', is_admin=True)
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            yield app
            
            # Clean up database
            db.session.remove()
            db.drop_all()

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        category=st.text(min_size=3, max_size=20).filter(lambda x: x.strip())
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_draft_posts_filtered_by_status_query(self, app_context, title, content, category):
        """
        **Property 2: Draft Post Visibility (Status Filtering)**
        
        For any post with draft status, it should be excluded from queries
        that retrieve published posts only.
        
        **Validates: Requirements 1.3**
        """
        # Create a draft post
        draft_post = PostManager.create_post(
            title=title,
            content=content,
            category=category,
            status='draft'
        )
        
        # Create a published post for comparison
        published_post = PostManager.create_post(
            title=f"Published {title}",
            content=f"Published {content}",
            category=category,
            status='published'
        )
        
        # Verify posts were created with correct status
        assert draft_post.status == 'draft', "Draft post should have draft status"
        assert published_post.status == 'published', "Published post should have published status"
        
        # Test PostManager status filtering
        draft_posts = PostManager.get_posts_by_status('draft')
        published_posts = PostManager.get_posts_by_status('published')
        
        # Verify draft post appears only in draft query
        draft_ids = [p.id for p in draft_posts]
        published_ids = [p.id for p in published_posts]
        
        assert draft_post.id in draft_ids, "Draft post should appear in draft posts query"
        assert draft_post.id not in published_ids, "Draft post should not appear in published posts query"
        assert published_post.id in published_ids, "Published post should appear in published posts query"
        assert published_post.id not in draft_ids, "Published post should not appear in draft posts query"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip())
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_draft_posts_have_no_published_timestamp(self, app_context, title, content):
        """
        **Property 2: Draft Post Visibility (Publication Timestamp)**
        
        For any post with draft status, it should not have a published_at timestamp,
        indicating it has never been made public.
        
        **Validates: Requirements 1.3**
        """
        # Create a draft post
        draft_post = PostManager.create_post(
            title=title,
            content=content,
            status='draft'
        )
        
        # Verify draft post has no publication timestamp
        assert draft_post.status == 'draft', "Post should have draft status"
        assert draft_post.published_at is None, "Draft post should not have published_at timestamp"
        assert draft_post.created_at is not None, "Draft post should have created_at timestamp"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        category=st.text(min_size=3, max_size=20).filter(lambda x: x.strip())
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_draft_posts_visible_in_admin_organized_view(self, app_context, title, content, category):
        """
        **Property 2: Draft Post Visibility (Admin Organization)**
        
        For any post with draft status, it should be included in the organized
        posts view that admin users can access.
        
        **Validates: Requirements 1.3**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create a draft post
        draft_post = PostManager.create_post(
            title=title,
            content=content,
            category=category,
            status='draft'
        )
        
        # Get organized posts (simulating admin dashboard data)
        organized_posts = PostManager.get_posts_organized_by_status()
        
        # Verify draft post appears in the draft section
        assert 'draft' in organized_posts, "Organized posts should have draft section"
        assert 'published' in organized_posts, "Organized posts should have published section"
        assert 'scheduled' in organized_posts, "Organized posts should have scheduled section"
        
        draft_section = organized_posts['draft']
        draft_titles = [post['title'] for post in draft_section]
        
        # Use the actual stored title (which may be trimmed)
        stored_title = draft_post.title
        assert stored_title in draft_titles, f"Draft post should appear in draft section of organized posts. Expected '{stored_title}' in {draft_titles}"
        
        # Verify it doesn't appear in published section
        published_section = organized_posts['published']
        published_titles = [post['title'] for post in published_section]
        
        assert stored_title not in published_titles, "Draft post should not appear in published section"

    @given(
        num_drafts=st.integers(min_value=1, max_value=5),
        num_published=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_draft_post_filtering_accuracy(self, app_context, num_drafts, num_published):
        """
        **Property 2: Draft Post Visibility (Filtering Accuracy)**
        
        The PostManager should accurately filter draft posts from published
        post queries while including them in draft-specific queries.
        
        **Validates: Requirements 1.3**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        draft_posts = []
        published_posts = []
        
        # Create draft posts
        for i in range(num_drafts):
            post = PostManager.create_post(
                title=f"Draft Post {i}",
                content=f"Draft content {i}",
                status='draft'
            )
            draft_posts.append(post)
        
        # Create published posts
        for i in range(num_published):
            post = PostManager.create_post(
                title=f"Published Post {i}",
                content=f"Published content {i}",
                status='published'
            )
            published_posts.append(post)
        
        # Test status-based filtering
        retrieved_drafts = PostManager.get_posts_by_status('draft')
        retrieved_published = PostManager.get_posts_by_status('published')
        
        # Verify correct number of posts in each category
        assert len(retrieved_drafts) == num_drafts, f"Should retrieve {num_drafts} draft posts, got {len(retrieved_drafts)}"
        assert len(retrieved_published) == num_published, f"Should retrieve {num_published} published posts, got {len(retrieved_published)}"
        
        # Verify no cross-contamination
        draft_ids = {p.id for p in retrieved_drafts}
        published_ids = {p.id for p in retrieved_published}
        
        for post in draft_posts:
            assert post.id in draft_ids, f"Draft post {post.id} should be in draft results"
            assert post.id not in published_ids, f"Draft post {post.id} should not be in published results"
        
        for post in published_posts:
            assert post.id in published_ids, f"Published post {post.id} should be in published results"
            assert post.id not in draft_ids, f"Published post {post.id} should not be in draft results"

    def test_draft_status_persistence_across_operations(self, app_context):
        """
        **Property 2: Draft Post Visibility (Status Persistence)**
        
        Draft status should persist across various operations and not accidentally
        change to published status.
        
        **Validates: Requirements 1.3**
        """
        # Create a draft post
        draft_post = PostManager.create_post(
            title="Persistent Draft",
            content="This should remain a draft",
            status='draft'
        )
        
        original_id = draft_post.id
        
        # Perform various operations that shouldn't affect status
        
        # 1. Update post content
        updated_post = PostManager.update_post(
            original_id,
            content="Updated draft content"
        )
        assert updated_post.status == 'draft', "Post should remain draft after content update"
        assert updated_post.published_at is None, "Draft should still have no published_at timestamp"
        
        # 2. Update post title
        updated_post = PostManager.update_post(
            original_id,
            title="Updated Persistent Draft"
        )
        assert updated_post.status == 'draft', "Post should remain draft after title update"
        assert updated_post.published_at is None, "Draft should still have no published_at timestamp"
        
        # 3. Add tags to the post
        updated_post = PostManager.update_post(original_id, tags=['test', 'draft'])
        assert updated_post.status == 'draft', "Post should remain draft after adding tags"
        assert updated_post.published_at is None, "Draft should still have no published_at timestamp"
        
        # 4. Update category
        updated_post = PostManager.update_post(original_id, category='test-category')
        assert updated_post.status == 'draft', "Post should remain draft after category update"
        assert updated_post.published_at is None, "Draft should still have no published_at timestamp"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip())
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_draft_to_published_status_transition(self, app_context, title, content):
        """
        **Property 2: Draft Post Visibility (Status Transition)**
        
        When a draft post is published, it should transition to published status
        and receive a published_at timestamp.
        
        **Validates: Requirements 1.3**
        """
        # Create a draft post
        draft_post = PostManager.create_post(
            title=title,
            content=content,
            status='draft'
        )
        
        # Verify initial draft state
        assert draft_post.status == 'draft', "Post should initially be draft"
        assert draft_post.published_at is None, "Draft should have no published_at timestamp"
        
        # Publish the post
        published_post = PostManager.update_post(
            draft_post.id,
            status='published'
        )
        
        # Verify published state
        assert published_post.status == 'published', "Post should be published after update"
        assert published_post.published_at is not None, "Published post should have published_at timestamp"
        
        # Verify it now appears in published posts query
        published_posts = PostManager.get_posts_by_status('published')
        published_ids = [p.id for p in published_posts]
        assert published_post.id in published_ids, "Published post should appear in published posts query"
        
        # Verify it no longer appears in draft posts query
        draft_posts = PostManager.get_posts_by_status('draft')
        draft_ids = [p.id for p in draft_posts]
        assert published_post.id not in draft_ids, "Published post should not appear in draft posts query"

    def test_scheduled_posts_behave_like_drafts_until_published(self, app_context):
        """
        **Property 2: Draft Post Visibility (Scheduled Posts)**
        
        Scheduled posts should behave like draft posts in terms of visibility
        until they are automatically published.
        
        **Validates: Requirements 1.3**
        """
        # Create a scheduled post for the future
        future_time = datetime.now(timezone.utc).replace(hour=23, minute=59)
        scheduled_post = PostManager.create_post(
            title="Future Scheduled Post",
            content="This is scheduled for the future",
            status='scheduled',
            scheduled_time=future_time,
            allow_past_schedule=False
        )
        
        # Verify scheduled post behaves like draft (not published)
        assert scheduled_post.status == 'scheduled', "Post should have scheduled status"
        assert scheduled_post.published_at is None, "Scheduled post should not have published_at timestamp"
        
        # Verify it doesn't appear in published posts query
        published_posts = PostManager.get_posts_by_status('published')
        published_ids = [p.id for p in published_posts]
        assert scheduled_post.id not in published_ids, "Scheduled post should not appear in published posts query"
        
        # Verify it appears in scheduled posts query
        scheduled_posts = PostManager.get_posts_by_status('scheduled')
        scheduled_ids = [p.id for p in scheduled_posts]
        assert scheduled_post.id in scheduled_ids, "Scheduled post should appear in scheduled posts query"
        
        # Verify organized posts view shows it in scheduled section
        organized_posts = PostManager.get_posts_organized_by_status()
        scheduled_section = organized_posts['scheduled']
        scheduled_titles = [post['title'] for post in scheduled_section]
        
        assert "Future Scheduled Post" in scheduled_titles, "Scheduled post should appear in scheduled section"
        
        # Verify it doesn't appear in published section
        published_section = organized_posts['published']
        published_titles = [post['title'] for post in published_section]
        
        assert "Future Scheduled Post" not in published_titles, "Scheduled post should not appear in published section"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip())
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_draft_post_metadata_excludes_publication_info(self, app_context, title, content):
        """
        **Property 2: Draft Post Visibility (Metadata)**
        
        Draft posts should have metadata that clearly indicates their unpublished status.
        
        **Validates: Requirements 1.3**
        """
        # Create a draft post
        draft_post = PostManager.create_post(
            title=title,
            content=content,
            status='draft'
        )
        
        # Get post metadata
        metadata = PostManager.get_post_metadata(draft_post.id)
        
        assert metadata is not None, "Should be able to get metadata for draft post"
        assert metadata['status'] == 'draft', "Metadata should show draft status"
        assert metadata['published_at'] is None, "Metadata should show no publication date"
        assert metadata['scheduled_publish_at'] is None, "Metadata should show no scheduled publication"
        assert metadata['created_at'] is not None, "Metadata should show creation date"
        assert metadata['display_date'] == metadata['created_at'], "Display date should be creation date for drafts"