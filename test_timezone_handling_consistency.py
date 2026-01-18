"""
Property-based test for timezone handling consistency.

**Feature: enhanced-content-management, Property 13: Timezone Handling Consistency**

**Validates: Requirements 7.3**

This test validates that all datetime operations in the system handle timezones
consistently, ensuring scheduled posts work correctly regardless of server timezone
and that all timestamps are stored and compared in UTC.
"""

import pytest
from datetime import datetime, timezone, timedelta
from hypothesis import given, strategies as st, settings, HealthCheck
import pytz

from app import create_app
from models import db, Post, User
from post_manager import PostManager
from schedule_manager import ScheduleManager


class TestTimezoneHandlingConsistency:
    """Test timezone handling consistency using property-based testing."""

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

    @pytest.fixture
    def scheduler(self, app):
        """Create scheduler instance."""
        return ScheduleManager(app)

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        hours_future=st.integers(min_value=1, max_value=48)
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_utc_timezone_consistency_in_storage(self, app_context, title, content, hours_future):
        """
        **Property 13: Timezone Handling Consistency (UTC Storage)**
        
        For any scheduled post created with a timezone-aware datetime,
        the system should store all timestamps consistently in UTC.
        
        **Validates: Requirements 7.3**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create scheduled time in UTC
        utc_scheduled_time = datetime.now(timezone.utc) + timedelta(hours=hours_future)
        
        # Create scheduled post
        scheduled_post = PostManager.create_post(
            title=title,
            content=content,
            status='scheduled',
            scheduled_time=utc_scheduled_time,
            allow_past_schedule=False
        )
        
        # Verify stored time is consistent with UTC input
        stored_time = scheduled_post.scheduled_publish_at
        
        # The stored time should be equivalent to the input time when both are in UTC
        if stored_time.tzinfo is None:
            # If stored as naive, treat as UTC for comparison
            stored_utc_timestamp = stored_time.replace(tzinfo=timezone.utc).timestamp()
        else:
            stored_utc_timestamp = stored_time.timestamp()
        
        input_utc_timestamp = utc_scheduled_time.timestamp()
        
        assert abs(stored_utc_timestamp - input_utc_timestamp) < 1, "Stored time should be equivalent to input UTC time"
        
        # Verify created_at is also timezone-consistent
        created_at = scheduled_post.created_at
        assert created_at is not None, "Created timestamp should be set"
        
        # Created time should be close to current time
        now_timestamp = datetime.now(timezone.utc).timestamp()
        if created_at.tzinfo is None:
            created_utc_timestamp = created_at.replace(tzinfo=timezone.utc).timestamp()
        else:
            created_utc_timestamp = created_at.timestamp()
        
        assert abs(now_timestamp - created_utc_timestamp) < 60, "Created timestamp should be close to current UTC time"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        hours_future=st.integers(min_value=1, max_value=48)
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_timezone_conversion_consistency(self, app_context, title, content, hours_future):
        """
        **Property 13: Timezone Handling Consistency (Timezone Conversion)**
        
        For any scheduled post, the system should handle timezone conversions
        consistently when comparing times for publication readiness.
        
        **Validates: Requirements 7.3**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create the same time in different timezone representations
        utc_time = datetime.now(timezone.utc) + timedelta(hours=hours_future)
        
        # Create scheduled post with UTC time
        scheduled_post = PostManager.create_post(
            title=title,
            content=content,
            status='scheduled',
            scheduled_time=utc_time,
            allow_past_schedule=False
        )
        
        # Test that the system correctly identifies this as a future post
        ready_posts = PostManager.get_scheduled_posts_ready_for_publication()
        ready_ids = [p.id for p in ready_posts]
        
        assert scheduled_post.id not in ready_ids, "Future scheduled post should not be ready for publication"
        
        # Now create a post scheduled in the past
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        past_scheduled_post = PostManager.create_post(
            title=f"Past {title}",
            content=f"Past {content}",
            status='scheduled',
            scheduled_time=past_time,
            allow_past_schedule=True
        )
        
        # Test that the system correctly identifies this as ready
        ready_posts = PostManager.get_scheduled_posts_ready_for_publication()
        ready_ids = [p.id for p in ready_posts]
        
        assert past_scheduled_post.id in ready_ids, "Past scheduled post should be ready for publication"
        assert scheduled_post.id not in ready_ids, "Future scheduled post should still not be ready"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        minutes_past=st.integers(min_value=1, max_value=60)
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_publication_time_timezone_consistency(self, app_context, scheduler, title, content, minutes_past):
        """
        **Property 13: Timezone Handling Consistency (Publication Time)**
        
        When a scheduled post is published, the published_at timestamp should
        be set consistently in UTC regardless of the original scheduled time timezone.
        
        **Validates: Requirements 7.3**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create a scheduled post with past time
        scheduled_time = datetime.now(timezone.utc) - timedelta(minutes=minutes_past)
        scheduled_post = PostManager.create_post(
            title=title,
            content=content,
            status='scheduled',
            scheduled_time=scheduled_time,
            allow_past_schedule=True
        )
        
        # Record time before publication
        before_publication = datetime.now(timezone.utc)
        
        # Run scheduled post check to publish the post
        results = scheduler.check_scheduled_posts()
        
        # Record time after publication
        after_publication = datetime.now(timezone.utc)
        
        # Verify the post was published
        assert results['posts_published'] >= 1, "Post should have been published"
        
        # Refresh post from database
        db.session.refresh(scheduled_post)
        
        # Verify published_at timestamp is set and in reasonable range
        assert scheduled_post.status == 'published', "Post should be published"
        assert scheduled_post.published_at is not None, "Published timestamp should be set"
        
        # Check that published_at is between before and after publication times
        published_at = scheduled_post.published_at
        if published_at.tzinfo is None:
            published_utc_timestamp = published_at.replace(tzinfo=timezone.utc).timestamp()
        else:
            published_utc_timestamp = published_at.timestamp()
        
        before_timestamp = before_publication.timestamp()
        after_timestamp = after_publication.timestamp()
        
        assert before_timestamp <= published_utc_timestamp <= after_timestamp, \
            "Published timestamp should be between before and after publication times"
        
        # Verify scheduled time is cleared
        assert scheduled_post.scheduled_publish_at is None, "Scheduled time should be cleared after publication"

    def test_timezone_aware_vs_naive_datetime_handling(self, app_context):
        """
        **Property 13: Timezone Handling Consistency (Naive vs Aware)**
        
        The system should handle both timezone-aware and naive datetime objects
        consistently, treating naive datetimes as UTC.
        
        **Validates: Requirements 7.3**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create two posts: one with timezone-aware, one with naive datetime
        base_time = datetime.now(timezone.utc) + timedelta(hours=2)
        
        # Timezone-aware datetime
        aware_time = base_time
        aware_post = PostManager.create_post(
            title="Timezone Aware Post",
            content="Content with timezone-aware scheduling",
            status='scheduled',
            scheduled_time=aware_time,
            allow_past_schedule=False
        )
        
        # Naive datetime (should be treated as UTC)
        naive_time = base_time.replace(tzinfo=None)
        naive_post = PostManager.create_post(
            title="Naive Timezone Post",
            content="Content with naive datetime scheduling",
            status='scheduled',
            scheduled_time=naive_time,
            allow_past_schedule=False
        )
        
        # Both posts should be treated consistently
        ready_posts = PostManager.get_scheduled_posts_ready_for_publication()
        ready_ids = [p.id for p in ready_posts]
        
        # Neither should be ready (both are in the future)
        assert aware_post.id not in ready_ids, "Timezone-aware future post should not be ready"
        assert naive_post.id not in ready_ids, "Naive future post should not be ready"
        
        # Compare stored times - they should be equivalent
        aware_stored = aware_post.scheduled_publish_at
        naive_stored = naive_post.scheduled_publish_at
        
        # Convert both to UTC timestamps for comparison
        if aware_stored.tzinfo is None:
            aware_timestamp = aware_stored.replace(tzinfo=timezone.utc).timestamp()
        else:
            aware_timestamp = aware_stored.timestamp()
        
        if naive_stored.tzinfo is None:
            naive_timestamp = naive_stored.replace(tzinfo=timezone.utc).timestamp()
        else:
            naive_timestamp = naive_stored.timestamp()
        
        assert abs(aware_timestamp - naive_timestamp) < 1, \
            "Timezone-aware and naive datetimes should be stored consistently"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip())
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_timezone_consistency_across_operations(self, app_context, title, content):
        """
        **Property 13: Timezone Handling Consistency (Cross-Operation)**
        
        Timezone handling should remain consistent across different operations
        like creation, updating, and publication.
        
        **Validates: Requirements 7.3**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create a scheduled post
        original_time = datetime.now(timezone.utc) + timedelta(hours=2)
        scheduled_post = PostManager.create_post(
            title=title,
            content=content,
            status='scheduled',
            scheduled_time=original_time,
            allow_past_schedule=False
        )
        
        # Store original timestamp for comparison
        original_stored = scheduled_post.scheduled_publish_at
        if original_stored.tzinfo is None:
            original_timestamp = original_stored.replace(tzinfo=timezone.utc).timestamp()
        else:
            original_timestamp = original_stored.timestamp()
        
        # Update the post (should preserve timezone handling)
        updated_post = PostManager.update_post(
            scheduled_post.id,
            content=f"Updated {content}"
        )
        
        # Verify timezone consistency is maintained
        updated_stored = updated_post.scheduled_publish_at
        if updated_stored.tzinfo is None:
            updated_timestamp = updated_stored.replace(tzinfo=timezone.utc).timestamp()
        else:
            updated_timestamp = updated_stored.timestamp()
        
        assert abs(original_timestamp - updated_timestamp) < 1, \
            "Timezone handling should be consistent across updates"
        
        # Manually publish the post
        published_post = PostManager.publish_post(scheduled_post.id)
        
        # Verify published_at timestamp is timezone-consistent
        published_at = published_post.published_at
        assert published_at is not None, "Published timestamp should be set"
        
        # Published time should be close to current time
        now_timestamp = datetime.now(timezone.utc).timestamp()
        if published_at.tzinfo is None:
            published_timestamp = published_at.replace(tzinfo=timezone.utc).timestamp()
        else:
            published_timestamp = published_at.timestamp()
        
        assert abs(now_timestamp - published_timestamp) < 60, \
            "Published timestamp should be close to current UTC time"

    def test_daylight_saving_time_handling(self, app_context):
        """
        **Property 13: Timezone Handling Consistency (DST)**
        
        The system should handle daylight saving time transitions correctly
        by consistently using UTC for all internal operations.
        
        **Validates: Requirements 7.3**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create a post scheduled during a potential DST transition
        # Use a fixed UTC time that would be affected by DST in local timezones
        utc_time = datetime(2024, 3, 10, 7, 0, 0, tzinfo=timezone.utc)  # Spring DST transition in US
        
        scheduled_post = PostManager.create_post(
            title="DST Test Post",
            content="Testing daylight saving time handling",
            status='scheduled',
            scheduled_time=utc_time,
            allow_past_schedule=True  # Allow past time for testing
        )
        
        # Verify the time is stored correctly
        stored_time = scheduled_post.scheduled_publish_at
        
        if stored_time.tzinfo is None:
            stored_timestamp = stored_time.replace(tzinfo=timezone.utc).timestamp()
        else:
            stored_timestamp = stored_time.timestamp()
        
        expected_timestamp = utc_time.timestamp()
        
        assert abs(stored_timestamp - expected_timestamp) < 1, \
            "UTC time should be stored correctly regardless of DST"
        
        # Test that the post is correctly identified as ready for publication
        # (since it's in the past)
        ready_posts = PostManager.get_scheduled_posts_ready_for_publication()
        ready_ids = [p.id for p in ready_posts]
        
        assert scheduled_post.id in ready_ids, \
            "Past scheduled post should be ready regardless of DST considerations"

    @given(
        hours_offset=st.integers(min_value=-12, max_value=12)
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_timezone_offset_consistency(self, app_context, hours_offset):
        """
        **Property 13: Timezone Handling Consistency (Timezone Offsets)**
        
        The system should handle different timezone offsets consistently,
        always normalizing to UTC for storage and comparison.
        
        **Validates: Requirements 7.3**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create a timezone with the given offset
        offset_tz = timezone(timedelta(hours=hours_offset))
        
        # Create the same moment in time in both UTC and the offset timezone
        utc_time = datetime.now(timezone.utc) + timedelta(hours=2)
        offset_time = utc_time.astimezone(offset_tz)
        
        # Create two posts with the same moment but different timezone representations
        utc_post = PostManager.create_post(
            title="UTC Post",
            content="Post created with UTC time",
            status='scheduled',
            scheduled_time=utc_time,
            allow_past_schedule=False
        )
        
        offset_post = PostManager.create_post(
            title="Offset Post",
            content="Post created with offset time",
            status='scheduled',
            scheduled_time=offset_time,
            allow_past_schedule=False
        )
        
        # Both posts should be stored with equivalent times
        utc_stored = utc_post.scheduled_publish_at
        offset_stored = offset_post.scheduled_publish_at
        
        # Convert both to UTC timestamps for comparison
        if utc_stored.tzinfo is None:
            utc_timestamp = utc_stored.replace(tzinfo=timezone.utc).timestamp()
        else:
            utc_timestamp = utc_stored.timestamp()
        
        if offset_stored.tzinfo is None:
            offset_timestamp = offset_stored.replace(tzinfo=timezone.utc).timestamp()
        else:
            offset_timestamp = offset_stored.timestamp()
        
        assert abs(utc_timestamp - offset_timestamp) < 1, \
            f"Posts with same moment in different timezones should be stored equivalently (UTC vs UTC{hours_offset:+d})"
        
        # Both posts should have the same readiness status
        ready_posts = PostManager.get_scheduled_posts_ready_for_publication()
        ready_ids = [p.id for p in ready_posts]
        
        utc_ready = utc_post.id in ready_ids
        offset_ready = offset_post.id in ready_ids
        
        assert utc_ready == offset_ready, \
            "Posts scheduled for the same moment should have the same readiness status"

    def test_metadata_timezone_consistency(self, app_context):
        """
        **Property 13: Timezone Handling Consistency (Metadata)**
        
        Post metadata should display timezone information consistently,
        with all times normalized to a consistent timezone representation.
        
        **Validates: Requirements 7.3**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create posts with different statuses to test metadata consistency
        now = datetime.now(timezone.utc)
        
        # Draft post
        draft_post = PostManager.create_post(
            title="Draft Post",
            content="Draft content",
            status='draft'
        )
        
        # Published post
        published_post = PostManager.create_post(
            title="Published Post",
            content="Published content",
            status='published'
        )
        
        # Scheduled post
        scheduled_post = PostManager.create_post(
            title="Scheduled Post",
            content="Scheduled content",
            status='scheduled',
            scheduled_time=now + timedelta(hours=2),
            allow_past_schedule=False
        )
        
        # Get metadata for all posts
        draft_metadata = PostManager.get_post_metadata(draft_post.id)
        published_metadata = PostManager.get_post_metadata(published_post.id)
        scheduled_metadata = PostManager.get_post_metadata(scheduled_post.id)
        
        # Verify all metadata contains consistent timezone information
        assert draft_metadata['created_at'] is not None, "Draft metadata should have created_at"
        assert published_metadata['created_at'] is not None, "Published metadata should have created_at"
        assert scheduled_metadata['created_at'] is not None, "Scheduled metadata should have created_at"
        
        assert published_metadata['published_at'] is not None, "Published metadata should have published_at"
        assert scheduled_metadata['scheduled_publish_at'] is not None, "Scheduled metadata should have scheduled_publish_at"
        
        # All timestamps should be close to current time (within reasonable bounds)
        current_timestamp = now.timestamp()
        
        for metadata, post_type in [(draft_metadata, 'draft'), (published_metadata, 'published'), (scheduled_metadata, 'scheduled')]:
            created_at = metadata['created_at']
            if created_at.tzinfo is None:
                created_timestamp = created_at.replace(tzinfo=timezone.utc).timestamp()
            else:
                created_timestamp = created_at.timestamp()
            
            assert abs(current_timestamp - created_timestamp) < 60, \
                f"{post_type} post created_at should be close to current time"
            
            # Display date should be consistent
            display_date = metadata['display_date']
            assert display_date is not None, f"{post_type} post should have display_date"