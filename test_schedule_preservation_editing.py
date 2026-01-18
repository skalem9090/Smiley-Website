"""
Property-based test for schedule preservation during editing.

**Feature: enhanced-content-management, Property 4: Schedule Preservation During Editing**

**Validates: Requirements 1.6**

This test validates that when editing scheduled posts, the scheduled publication time
is preserved unless explicitly changed, ensuring posts don't lose their scheduling
due to content updates.
"""

import pytest
from datetime import datetime, timezone, timedelta
from hypothesis import given, strategies as st, settings, HealthCheck

from app import create_app
from models import db, Post, User
from post_manager import PostManager


class TestSchedulePreservationDuringEditing:
    """Test schedule preservation during editing using property-based testing."""

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
        new_content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        hours_future=st.integers(min_value=1, max_value=48)
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_schedule_preserved_during_content_update(self, app_context, title, content, new_content, hours_future):
        """
        **Property 4: Schedule Preservation During Editing (Content Update)**
        
        For any scheduled post, when updating only the content, the scheduled
        publication time should remain unchanged.
        
        **Validates: Requirements 1.6**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create a scheduled post
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=hours_future)
        scheduled_post = PostManager.create_post(
            title=title,
            content=content,
            status='scheduled',
            scheduled_time=scheduled_time,
            allow_past_schedule=False
        )
        
        # Store original scheduled time for comparison
        original_scheduled_time = scheduled_post.scheduled_publish_at
        original_id = scheduled_post.id
        
        # Update only the content
        updated_post = PostManager.update_post(
            original_id,
            content=new_content
        )
        
        # Verify schedule is preserved
        assert updated_post is not None, "Post should be successfully updated"
        assert updated_post.status == 'scheduled', "Post should remain scheduled"
        assert updated_post.content == new_content.strip(), "Content should be updated"
        
        # Compare scheduled times using timestamps to handle timezone differences
        original_timestamp = original_scheduled_time.replace(tzinfo=timezone.utc).timestamp()
        updated_timestamp = updated_post.scheduled_publish_at.replace(tzinfo=timezone.utc).timestamp()
        assert abs(original_timestamp - updated_timestamp) < 1, "Scheduled time should be preserved during content update"
        
        # Verify other fields remain unchanged
        assert updated_post.title == title.strip(), "Title should remain unchanged"
        assert updated_post.published_at is None, "Published timestamp should remain None"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        new_title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        hours_future=st.integers(min_value=1, max_value=48)
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_schedule_preserved_during_title_update(self, app_context, title, content, new_title, hours_future):
        """
        **Property 4: Schedule Preservation During Editing (Title Update)**
        
        For any scheduled post, when updating only the title, the scheduled
        publication time should remain unchanged.
        
        **Validates: Requirements 1.6**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create a scheduled post
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=hours_future)
        scheduled_post = PostManager.create_post(
            title=title,
            content=content,
            status='scheduled',
            scheduled_time=scheduled_time,
            allow_past_schedule=False
        )
        
        # Store original scheduled time for comparison
        original_scheduled_time = scheduled_post.scheduled_publish_at
        original_id = scheduled_post.id
        
        # Update only the title
        updated_post = PostManager.update_post(
            original_id,
            title=new_title
        )
        
        # Verify schedule is preserved
        assert updated_post is not None, "Post should be successfully updated"
        assert updated_post.status == 'scheduled', "Post should remain scheduled"
        assert updated_post.title == new_title.strip(), "Title should be updated"
        
        # Compare scheduled times using timestamps to handle timezone differences
        original_timestamp = original_scheduled_time.replace(tzinfo=timezone.utc).timestamp()
        updated_timestamp = updated_post.scheduled_publish_at.replace(tzinfo=timezone.utc).timestamp()
        assert abs(original_timestamp - updated_timestamp) < 1, "Scheduled time should be preserved during title update"
        
        # Verify other fields remain unchanged
        assert updated_post.content == content.strip(), "Content should remain unchanged"
        assert updated_post.published_at is None, "Published timestamp should remain None"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        category=st.text(min_size=3, max_size=20).filter(lambda x: x.strip()),
        new_category=st.text(min_size=3, max_size=20).filter(lambda x: x.strip()),
        hours_future=st.integers(min_value=1, max_value=48)
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_schedule_preserved_during_category_update(self, app_context, title, content, category, new_category, hours_future):
        """
        **Property 4: Schedule Preservation During Editing (Category Update)**
        
        For any scheduled post, when updating only the category, the scheduled
        publication time should remain unchanged.
        
        **Validates: Requirements 1.6**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create a scheduled post
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=hours_future)
        scheduled_post = PostManager.create_post(
            title=title,
            content=content,
            category=category,
            status='scheduled',
            scheduled_time=scheduled_time,
            allow_past_schedule=False
        )
        
        # Store original scheduled time for comparison
        original_scheduled_time = scheduled_post.scheduled_publish_at
        original_id = scheduled_post.id
        
        # Update only the category
        updated_post = PostManager.update_post(
            original_id,
            category=new_category
        )
        
        # Verify schedule is preserved
        assert updated_post is not None, "Post should be successfully updated"
        assert updated_post.status == 'scheduled', "Post should remain scheduled"
        assert updated_post.category == new_category.strip(), "Category should be updated"
        
        # Compare scheduled times using timestamps to handle timezone differences
        original_timestamp = original_scheduled_time.replace(tzinfo=timezone.utc).timestamp()
        updated_timestamp = updated_post.scheduled_publish_at.replace(tzinfo=timezone.utc).timestamp()
        assert abs(original_timestamp - updated_timestamp) < 1, "Scheduled time should be preserved during category update"
        
        # Verify other fields remain unchanged
        assert updated_post.title == title.strip(), "Title should remain unchanged"
        assert updated_post.content == content.strip(), "Content should remain unchanged"
        assert updated_post.published_at is None, "Published timestamp should remain None"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        summary=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        new_summary=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        hours_future=st.integers(min_value=1, max_value=48)
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_schedule_preserved_during_summary_update(self, app_context, title, content, summary, new_summary, hours_future):
        """
        **Property 4: Schedule Preservation During Editing (Summary Update)**
        
        For any scheduled post, when updating only the summary, the scheduled
        publication time should remain unchanged.
        
        **Validates: Requirements 1.6**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create a scheduled post
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=hours_future)
        scheduled_post = PostManager.create_post(
            title=title,
            content=content,
            summary=summary,
            status='scheduled',
            scheduled_time=scheduled_time,
            allow_past_schedule=False
        )
        
        # Store original scheduled time for comparison
        original_scheduled_time = scheduled_post.scheduled_publish_at
        original_id = scheduled_post.id
        
        # Update only the summary
        updated_post = PostManager.update_post(
            original_id,
            summary=new_summary
        )
        
        # Verify schedule is preserved
        assert updated_post is not None, "Post should be successfully updated"
        assert updated_post.status == 'scheduled', "Post should remain scheduled"
        
        # Compare scheduled times using timestamps to handle timezone differences
        original_timestamp = original_scheduled_time.replace(tzinfo=timezone.utc).timestamp()
        updated_timestamp = updated_post.scheduled_publish_at.replace(tzinfo=timezone.utc).timestamp()
        assert abs(original_timestamp - updated_timestamp) < 1, "Scheduled time should be preserved during summary update"
        
        # Verify other fields remain unchanged
        assert updated_post.title == title.strip(), "Title should remain unchanged"
        assert updated_post.content == content.strip(), "Content should remain unchanged"
        assert updated_post.published_at is None, "Published timestamp should remain None"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        hours_future=st.integers(min_value=1, max_value=48)
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_schedule_preserved_during_tag_update(self, app_context, title, content, hours_future):
        """
        **Property 4: Schedule Preservation During Editing (Tag Update)**
        
        For any scheduled post, when updating only the tags, the scheduled
        publication time should remain unchanged.
        
        **Validates: Requirements 1.6**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create a scheduled post
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=hours_future)
        scheduled_post = PostManager.create_post(
            title=title,
            content=content,
            status='scheduled',
            scheduled_time=scheduled_time,
            tags=['original', 'tags'],
            allow_past_schedule=False
        )
        
        # Store original scheduled time for comparison
        original_scheduled_time = scheduled_post.scheduled_publish_at
        original_id = scheduled_post.id
        
        # Update only the tags
        updated_post = PostManager.update_post(
            original_id,
            tags=['new', 'updated', 'tags']
        )
        
        # Verify schedule is preserved
        assert updated_post is not None, "Post should be successfully updated"
        assert updated_post.status == 'scheduled', "Post should remain scheduled"
        
        # Compare scheduled times using timestamps to handle timezone differences
        original_timestamp = original_scheduled_time.replace(tzinfo=timezone.utc).timestamp()
        updated_timestamp = updated_post.scheduled_publish_at.replace(tzinfo=timezone.utc).timestamp()
        assert abs(original_timestamp - updated_timestamp) < 1, "Scheduled time should be preserved during tag update"
        
        # Verify other fields remain unchanged
        assert updated_post.title == title.strip(), "Title should remain unchanged"
        assert updated_post.content == content.strip(), "Content should remain unchanged"
        assert updated_post.published_at is None, "Published timestamp should remain None"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        new_title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        new_content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        hours_future=st.integers(min_value=1, max_value=48)
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_schedule_preserved_during_multiple_field_update(self, app_context, title, content, new_title, new_content, hours_future):
        """
        **Property 4: Schedule Preservation During Editing (Multiple Fields)**
        
        For any scheduled post, when updating multiple fields simultaneously
        (but not the schedule), the scheduled publication time should remain unchanged.
        
        **Validates: Requirements 1.6**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create a scheduled post
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=hours_future)
        scheduled_post = PostManager.create_post(
            title=title,
            content=content,
            status='scheduled',
            scheduled_time=scheduled_time,
            allow_past_schedule=False
        )
        
        # Store original scheduled time for comparison
        original_scheduled_time = scheduled_post.scheduled_publish_at
        original_id = scheduled_post.id
        
        # Update multiple fields but not the schedule
        updated_post = PostManager.update_post(
            original_id,
            title=new_title,
            content=new_content,
            category='updated-category'
        )
        
        # Verify schedule is preserved
        assert updated_post is not None, "Post should be successfully updated"
        assert updated_post.status == 'scheduled', "Post should remain scheduled"
        assert updated_post.title == new_title.strip(), "Title should be updated"
        assert updated_post.content == new_content.strip(), "Content should be updated"
        assert updated_post.category == 'updated-category', "Category should be updated"
        
        # Compare scheduled times using timestamps to handle timezone differences
        original_timestamp = original_scheduled_time.replace(tzinfo=timezone.utc).timestamp()
        updated_timestamp = updated_post.scheduled_publish_at.replace(tzinfo=timezone.utc).timestamp()
        assert abs(original_timestamp - updated_timestamp) < 1, "Scheduled time should be preserved during multiple field update"
        
        # Verify published timestamp remains None
        assert updated_post.published_at is None, "Published timestamp should remain None"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        hours_future_1=st.integers(min_value=1, max_value=24),
        hours_future_2=st.integers(min_value=25, max_value=48)
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_schedule_updated_when_explicitly_changed(self, app_context, title, content, hours_future_1, hours_future_2):
        """
        **Property 4: Schedule Preservation During Editing (Explicit Schedule Change)**
        
        For any scheduled post, when explicitly updating the scheduled time,
        the new scheduled time should be applied.
        
        **Validates: Requirements 1.6**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create a scheduled post
        original_scheduled_time = datetime.now(timezone.utc) + timedelta(hours=hours_future_1)
        scheduled_post = PostManager.create_post(
            title=title,
            content=content,
            status='scheduled',
            scheduled_time=original_scheduled_time,
            allow_past_schedule=False
        )
        
        original_id = scheduled_post.id
        
        # Update with a new scheduled time
        new_scheduled_time = datetime.now(timezone.utc) + timedelta(hours=hours_future_2)
        updated_post = PostManager.update_post(
            original_id,
            scheduled_time=new_scheduled_time
        )
        
        # Verify new schedule is applied
        assert updated_post is not None, "Post should be successfully updated"
        assert updated_post.status == 'scheduled', "Post should remain scheduled"
        
        # Compare scheduled times using timestamps
        new_timestamp = new_scheduled_time.timestamp()
        updated_timestamp = updated_post.scheduled_publish_at.replace(tzinfo=timezone.utc).timestamp()
        assert abs(new_timestamp - updated_timestamp) < 1, "New scheduled time should be applied"
        
        # Verify it's different from the original time
        original_timestamp = original_scheduled_time.timestamp()
        assert abs(original_timestamp - updated_timestamp) > 3600, "Scheduled time should be different from original"
        
        # Verify other fields remain unchanged
        assert updated_post.title == title.strip(), "Title should remain unchanged"
        assert updated_post.content == content.strip(), "Content should remain unchanged"
        assert updated_post.published_at is None, "Published timestamp should remain None"

    def test_schedule_cleared_when_status_changed_to_draft(self, app_context):
        """
        **Property 4: Schedule Preservation During Editing (Status Change to Draft)**
        
        When a scheduled post's status is changed to draft, the scheduled time
        should be cleared.
        
        **Validates: Requirements 1.6**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create a scheduled post
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=2)
        scheduled_post = PostManager.create_post(
            title="Scheduled Post",
            content="This is scheduled content",
            status='scheduled',
            scheduled_time=scheduled_time,
            allow_past_schedule=False
        )
        
        original_id = scheduled_post.id
        
        # Change status to draft
        updated_post = PostManager.update_post(
            original_id,
            status='draft'
        )
        
        # Verify schedule is cleared
        assert updated_post is not None, "Post should be successfully updated"
        assert updated_post.status == 'draft', "Post should be changed to draft"
        assert updated_post.scheduled_publish_at is None, "Scheduled time should be cleared when changed to draft"
        assert updated_post.published_at is None, "Published timestamp should remain None"

    def test_schedule_cleared_when_status_changed_to_published(self, app_context):
        """
        **Property 4: Schedule Preservation During Editing (Status Change to Published)**
        
        When a scheduled post's status is changed to published, the scheduled time
        should be cleared and published_at should be set.
        
        **Validates: Requirements 1.6**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create a scheduled post
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=2)
        scheduled_post = PostManager.create_post(
            title="Scheduled Post",
            content="This is scheduled content",
            status='scheduled',
            scheduled_time=scheduled_time,
            allow_past_schedule=False
        )
        
        original_id = scheduled_post.id
        
        # Change status to published
        updated_post = PostManager.update_post(
            original_id,
            status='published'
        )
        
        # Verify schedule is cleared and published_at is set
        assert updated_post is not None, "Post should be successfully updated"
        assert updated_post.status == 'published', "Post should be changed to published"
        assert updated_post.scheduled_publish_at is None, "Scheduled time should be cleared when published"
        assert updated_post.published_at is not None, "Published timestamp should be set when published"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=10, max_size=500).filter(lambda x: x.strip()),
        hours_future=st.integers(min_value=1, max_value=48)
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_schedule_preservation_across_multiple_edits(self, app_context, title, content, hours_future):
        """
        **Property 4: Schedule Preservation During Editing (Multiple Sequential Edits)**
        
        For any scheduled post, the scheduled time should be preserved across
        multiple sequential edits that don't explicitly change the schedule.
        
        **Validates: Requirements 1.6**
        """
        # Clear any existing posts from previous test examples
        Post.query.delete()
        db.session.commit()
        
        # Create a scheduled post
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=hours_future)
        scheduled_post = PostManager.create_post(
            title=title,
            content=content,
            status='scheduled',
            scheduled_time=scheduled_time,
            allow_past_schedule=False
        )
        
        # Store original scheduled time for comparison
        original_scheduled_time = scheduled_post.scheduled_publish_at
        original_id = scheduled_post.id
        
        # Perform multiple sequential edits
        
        # Edit 1: Update title
        updated_post = PostManager.update_post(
            original_id,
            title=f"Updated {title}"
        )
        
        # Verify schedule is preserved after first edit
        assert updated_post.status == 'scheduled', "Post should remain scheduled after first edit"
        first_edit_timestamp = updated_post.scheduled_publish_at.replace(tzinfo=timezone.utc).timestamp()
        original_timestamp = original_scheduled_time.replace(tzinfo=timezone.utc).timestamp()
        assert abs(original_timestamp - first_edit_timestamp) < 1, "Scheduled time should be preserved after first edit"
        
        # Edit 2: Update content
        updated_post = PostManager.update_post(
            original_id,
            content=f"Updated {content}"
        )
        
        # Verify schedule is preserved after second edit
        assert updated_post.status == 'scheduled', "Post should remain scheduled after second edit"
        second_edit_timestamp = updated_post.scheduled_publish_at.replace(tzinfo=timezone.utc).timestamp()
        assert abs(original_timestamp - second_edit_timestamp) < 1, "Scheduled time should be preserved after second edit"
        
        # Edit 3: Update category
        updated_post = PostManager.update_post(
            original_id,
            category='updated-category'
        )
        
        # Verify schedule is preserved after third edit
        assert updated_post.status == 'scheduled', "Post should remain scheduled after third edit"
        third_edit_timestamp = updated_post.scheduled_publish_at.replace(tzinfo=timezone.utc).timestamp()
        assert abs(original_timestamp - third_edit_timestamp) < 1, "Scheduled time should be preserved after third edit"
        
        # Verify final state
        assert updated_post.title == f"Updated {title}".strip(), "Final title should reflect all updates"
        assert updated_post.content == f"Updated {content}".strip(), "Final content should reflect all updates"
        assert updated_post.category == 'updated-category', "Final category should reflect all updates"
        assert updated_post.published_at is None, "Published timestamp should remain None"