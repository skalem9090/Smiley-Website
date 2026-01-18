"""
Property-based test for scheduled post automatic publication.

**Feature: enhanced-content-management, Property 1: Scheduled Post Automatic Publication**

**Validates: Requirements 1.2, 1.5, 7.2**

This test validates that posts with scheduled publication times that have passed
are automatically updated to published status and made publicly accessible.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from app import create_app
from models import db, Post, User
from post_manager import PostManager
from schedule_manager import ScheduleManager


class TestScheduledPostPublication:
    """Test scheduled post automatic publication using property-based testing."""

    @pytest.fixture
    def app(self):
        """Create test Flask application."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        return app

    @pytest.fixture
    def app_context(self, app):
        """Create application context for testing."""
        with app.app_context():
            db.create_all()
            
            # Create test user
            user = User(username='testuser', is_admin=True)
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            yield app
            db.session.remove()
            db.drop_all()

    @pytest.fixture
    def scheduler(self, app):
        """Create scheduler instance."""
        return ScheduleManager(app)

    def create_scheduled_post(self, title: str, content: str, scheduled_time: datetime) -> Post:
        """Helper method to create a scheduled post."""
        return PostManager.create_post(
            title=title,
            content=content,
            status='scheduled',
            scheduled_time=scheduled_time,
            allow_past_schedule=True  # Allow past times for testing
        )

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        minutes_past=st.integers(min_value=1, max_value=1440)  # 1 minute to 24 hours past
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_scheduled_posts_past_time_are_published(self, app_context, scheduler, title, content, minutes_past):
        """
        **Property 1: Scheduled Post Automatic Publication (Past Time)**
        
        For any post with a scheduled publication time that has passed,
        the system should automatically update the post status to published
        and make it publicly accessible.
        
        **Validates: Requirements 1.2, 1.5, 7.2**
        """
        # Create a scheduled time in the past
        scheduled_time = datetime.now(timezone.utc) - timedelta(minutes=minutes_past)
        
        # Create scheduled post
        post = self.create_scheduled_post(title, content, scheduled_time)
        
        # Verify post is initially scheduled
        assert post.status == 'scheduled', "Post should initially be scheduled"
        
        # Compare times by converting both to UTC timestamps to handle timezone differences
        expected_timestamp = scheduled_time.timestamp()
        actual_timestamp = post.scheduled_publish_at.replace(tzinfo=timezone.utc).timestamp()
        assert abs(expected_timestamp - actual_timestamp) < 1, "Scheduled time should be set correctly"
        
        assert post.published_at is None, "Post should not have published_at initially"
        
        # Run the scheduled post check
        results = scheduler.check_scheduled_posts()
        
        # Verify the post was published
        db.session.refresh(post)
        assert post.status == 'published', "Post should be published after scheduled time passes"
        assert post.published_at is not None, "Post should have published_at timestamp"
        assert post.scheduled_publish_at is None, "Scheduled time should be cleared after publication"
        
        # Verify results indicate successful publication
        assert results['posts_published'] >= 1, "At least one post should be published"
        assert len(results['errors']) == 0, "No errors should occur during publication"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        minutes_future=st.integers(min_value=1, max_value=1440)  # 1 minute to 24 hours future
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_scheduled_posts_future_time_remain_scheduled(self, app_context, scheduler, title, content, minutes_future):
        """
        **Property 1: Scheduled Post Automatic Publication (Future Time)**
        
        For any post with a scheduled publication time in the future,
        the system should leave the post in scheduled status.
        
        **Validates: Requirements 1.2, 1.5, 7.2**
        """
        # Create a scheduled time in the future
        scheduled_time = datetime.now(timezone.utc) + timedelta(minutes=minutes_future)
        
        # Create scheduled post
        post = self.create_scheduled_post(title, content, scheduled_time)
        
        # Verify post is initially scheduled
        assert post.status == 'scheduled', "Post should initially be scheduled"
        
        # Compare times by converting both to UTC timestamps to handle timezone differences
        expected_timestamp = scheduled_time.timestamp()
        actual_timestamp = post.scheduled_publish_at.replace(tzinfo=timezone.utc).timestamp()
        assert abs(expected_timestamp - actual_timestamp) < 1, "Scheduled time should be set correctly"
        
        assert post.published_at is None, "Post should not have published_at initially"
        
        # Run the scheduled post check
        results = scheduler.check_scheduled_posts()
        
        # Verify the post remains scheduled
        db.session.refresh(post)
        assert post.status == 'scheduled', "Post should remain scheduled for future time"
        assert post.published_at is None, "Post should not have published_at timestamp"
        
        # Compare times by converting both to UTC timestamps to handle timezone differences
        expected_timestamp = scheduled_time.timestamp()
        actual_timestamp = post.scheduled_publish_at.replace(tzinfo=timezone.utc).timestamp()
        assert abs(expected_timestamp - actual_timestamp) < 1, "Scheduled time should remain unchanged"
        
        # Verify no posts were published
        assert results['posts_published'] == 0, "No posts should be published for future times"

    @given(
        num_posts=st.integers(min_value=2, max_value=5),
        minutes_past_range=st.integers(min_value=1, max_value=60)
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_multiple_scheduled_posts_publication(self, app_context, scheduler, num_posts, minutes_past_range):
        """
        **Property 1: Scheduled Post Automatic Publication (Multiple Posts)**
        
        For any number of posts with scheduled publication times that have passed,
        the system should publish all of them in a single check operation.
        
        **Validates: Requirements 1.2, 1.5, 7.2**
        """
        created_posts = []
        
        # Create multiple scheduled posts with past times
        for i in range(num_posts):
            # Ensure all posts have past scheduled times
            scheduled_time = datetime.now(timezone.utc) - timedelta(minutes=minutes_past_range + i)
            post = self.create_scheduled_post(
                title=f"Test Post {i}",
                content=f"Content for test post {i}",
                scheduled_time=scheduled_time
            )
            created_posts.append(post)
        
        # Verify all posts are initially scheduled
        for post in created_posts:
            assert post.status == 'scheduled', f"Post {post.id} should initially be scheduled"
            assert post.published_at is None, f"Post {post.id} should not have published_at initially"
        
        # Run the scheduled post check
        results = scheduler.check_scheduled_posts()
        
        # Verify all posts were published
        for post in created_posts:
            db.session.refresh(post)
            assert post.status == 'published', f"Post {post.id} should be published"
            assert post.published_at is not None, f"Post {post.id} should have published_at timestamp"
            assert post.scheduled_publish_at is None, f"Post {post.id} scheduled time should be cleared"
        
        # Verify results indicate all posts were published
        assert results['posts_published'] == num_posts, f"All {num_posts} posts should be published"
        assert results['posts_failed'] == 0, "No posts should fail to publish"
        assert len(results['errors']) == 0, "No errors should occur during publication"

    def test_publication_preserves_post_content_and_metadata(self, app_context, scheduler):
        """
        **Property 1: Scheduled Post Automatic Publication (Content Preservation)**
        
        When a scheduled post is published, all content and metadata should be preserved.
        
        **Validates: Requirements 1.2, 1.5**
        """
        # Create scheduled post with specific content
        title = "Test Post Title"
        content = "This is the test post content with <strong>HTML</strong> formatting."
        category = "test"
        summary = "This is a test summary"
        scheduled_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        post = PostManager.create_post(
            title=title,
            content=content,
            category=category,
            summary=summary,
            status='scheduled',
            scheduled_time=scheduled_time,
            allow_past_schedule=True  # Allow past times for testing
        )
        
        original_id = post.id
        original_created_at = post.created_at
        
        # Run the scheduled post check
        scheduler.check_scheduled_posts()
        
        # Verify content and metadata are preserved
        db.session.refresh(post)
        assert post.id == original_id, "Post ID should be preserved"
        assert post.title == title, "Post title should be preserved"
        assert post.content == content, "Post content should be preserved"
        assert post.category == category, "Post category should be preserved"
        assert post.summary == summary, "Post summary should be preserved"
        assert post.created_at == original_created_at, "Post creation time should be preserved"
        
        # Verify status change
        assert post.status == 'published', "Post status should be updated to published"
        assert post.published_at is not None, "Post should have published_at timestamp"

    def test_publication_with_database_error_handling(self, app_context, scheduler):
        """
        **Property 1: Scheduled Post Automatic Publication (Error Handling)**
        
        When database errors occur during publication, the system should handle them gracefully.
        
        **Validates: Requirements 7.5**
        """
        # Create scheduled post
        scheduled_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        post = self.create_scheduled_post("Test Post", "Test Content", scheduled_time)
        
        # Mock database error during publication
        with patch.object(PostManager, 'publish_post', side_effect=Exception("Database error")):
            results = scheduler.check_scheduled_posts()
        
        # Verify error handling
        assert results['posts_failed'] >= 1, "Failed post should be recorded"
        assert len(results['errors']) >= 1, "Error should be recorded"
        
        # Check that some error related to the failed publication occurred
        error_messages = ' '.join(results['errors'])
        assert "Failed to publish post" in error_messages, f"Publication failure should be recorded. Actual errors: {results['errors']}"
        
        # Verify post remains in original state
        db.session.refresh(post)
        assert post.status == 'scheduled', "Post should remain scheduled after error"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip())
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_manual_publication_of_scheduled_post(self, app_context, scheduler, title, content):
        """
        **Property 1: Scheduled Post Automatic Publication (Manual Override)**
        
        A scheduled post should be publishable manually before its scheduled time.
        
        **Validates: Requirements 1.2, 1.5**
        """
        # Create scheduled post for future time
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=1)
        post = self.create_scheduled_post(title, content, scheduled_time)
        
        # Manually publish the post
        published_post = PostManager.publish_post(post.id)
        
        # Verify manual publication worked
        assert published_post is not None, "Manual publication should succeed"
        assert published_post.status == 'published', "Post should be published"
        assert published_post.published_at is not None, "Post should have published_at timestamp"
        assert published_post.scheduled_publish_at is None, "Scheduled time should be cleared"
        
        # Verify automatic check doesn't affect already published post
        results = scheduler.check_scheduled_posts()
        
        db.session.refresh(post)
        assert post.status == 'published', "Post should remain published"
        assert results['posts_published'] == 0, "No additional posts should be published"

    def test_scheduled_post_identification_accuracy(self, app_context, scheduler):
        """
        **Property 1: Scheduled Post Automatic Publication (Identification)**
        
        The system should accurately identify only posts that are scheduled and past due.
        
        **Validates: Requirements 1.2, 7.2**
        """
        now = datetime.now(timezone.utc)
        
        # Create posts with different statuses and times
        draft_post = PostManager.create_post("Draft Post", "Draft content", status='draft')
        published_post = PostManager.create_post("Published Post", "Published content", status='published')
        future_scheduled = self.create_scheduled_post("Future Post", "Future content", now + timedelta(hours=1))
        past_scheduled = self.create_scheduled_post("Past Post", "Past content", now - timedelta(minutes=5))
        
        # Get posts ready for publication
        ready_posts = PostManager.get_scheduled_posts_ready_for_publication()
        
        # Verify only the past scheduled post is identified
        ready_ids = [post.id for post in ready_posts]
        assert past_scheduled.id in ready_ids, "Past scheduled post should be identified"
        assert draft_post.id not in ready_ids, "Draft post should not be identified"
        assert published_post.id not in ready_ids, "Published post should not be identified"
        assert future_scheduled.id not in ready_ids, "Future scheduled post should not be identified"
        
        # Run publication check
        results = scheduler.check_scheduled_posts()
        
        # Verify only the correct post was published
        assert results['posts_published'] == 1, "Only one post should be published"
        
        # Verify final states
        db.session.refresh(draft_post)
        db.session.refresh(published_post)
        db.session.refresh(future_scheduled)
        db.session.refresh(past_scheduled)
        
        assert draft_post.status == 'draft', "Draft post should remain draft"
        assert published_post.status == 'published', "Published post should remain published"
        assert future_scheduled.status == 'scheduled', "Future scheduled post should remain scheduled"
        assert past_scheduled.status == 'published', "Past scheduled post should be published"