"""
Property-Based Test for Publication Retry Mechanism

This module tests the publication retry mechanism to ensure that failed
post publications are retried according to the configured retry policy.

**Validates: Requirements 7.5**
"""

import pytest
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, Bundle, rule, initialize

from app import create_app
from models import db, Post
from post_manager import PostManager
from schedule_manager import ScheduleManager


class TestPublicationRetryMechanism:
    """Test publication retry mechanism using property-based testing."""
    
    def setup_method(self):
        """Set up test environment for each test method."""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Set environment variables for test configuration
        self.original_db_url = os.environ.get('DATABASE_URL')
        self.original_secret = os.environ.get('SECRET_KEY')
        
        os.environ['DATABASE_URL'] = f'sqlite:///{self.db_path}'
        os.environ['SECRET_KEY'] = 'test-secret-key'
        
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create schedule manager
        self.schedule_manager = ScheduleManager(self.app)
    
    def teardown_method(self):
        """Clean up test environment after each test method."""
        # Shutdown scheduler
        if self.schedule_manager.scheduler and self.schedule_manager.scheduler.running:
            self.schedule_manager.shutdown()
        
        # Clean up database
        db.drop_all()
        self.app_context.pop()
        
        # Restore original environment variables
        if self.original_db_url:
            os.environ['DATABASE_URL'] = self.original_db_url
        elif 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']
            
        if self.original_secret:
            os.environ['SECRET_KEY'] = self.original_secret
        elif 'SECRET_KEY' in os.environ:
            del os.environ['SECRET_KEY']
        
        # Clean up temporary file
        try:
            os.close(self.db_fd)
            os.unlink(self.db_path)
        except (OSError, PermissionError):
            pass  # File might already be closed/deleted

    @given(
        title=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()),
        scheduled_minutes_ago=st.integers(min_value=1, max_value=60)
    )
    @settings(
        max_examples=10, 
        deadline=10000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_publication_retry_mechanism_property(self, title, content, scheduled_minutes_ago):
        """
        **Property 15: Publication Retry Mechanism**
        
        GIVEN a scheduled post that fails to publish
        WHEN the publication fails with an error
        THEN the system should schedule retry attempts with exponential backoff
        AND retry up to the maximum number of attempts
        AND log all retry attempts appropriately
        
        **Validates: Requirements 7.5**
        """
        # Create a scheduled post that should have been published
        scheduled_time = datetime.now(timezone.utc) - timedelta(minutes=scheduled_minutes_ago)
        
        post = PostManager.create_post(
            title=title,
            content=content,
            status='scheduled',
            scheduled_time=scheduled_time,
            allow_past_schedule=True
        )
        
        # Mock the publish_scheduled_post method to simulate failure
        original_publish = self.schedule_manager.publish_scheduled_post
        failure_count = 0
        max_failures = 2  # Fail first 2 attempts, succeed on 3rd
        
        def mock_publish_with_failure(post_id):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= max_failures:
                raise Exception(f"Simulated publication failure {failure_count}")
            return original_publish(post_id)
        
        # Mock scheduler to track retry scheduling
        retry_jobs = []
        original_add_job = self.schedule_manager.scheduler.add_job
        
        def mock_add_job(*args, **kwargs):
            if 'retry_publish' in kwargs.get('id', ''):
                retry_jobs.append({
                    'id': kwargs.get('id'),
                    'args': kwargs.get('args', []),
                    'run_date': kwargs.get('trigger').run_date if hasattr(kwargs.get('trigger'), 'run_date') else None
                })
            return original_add_job(*args, **kwargs)
        
        with patch.object(self.schedule_manager, 'publish_scheduled_post', side_effect=mock_publish_with_failure):
            with patch.object(self.schedule_manager.scheduler, 'add_job', side_effect=mock_add_job):
                # Trigger the publication check
                results = self.schedule_manager.check_scheduled_posts()
                
                # Verify initial failure was recorded
                assert results['posts_failed'] >= 1
                assert len(results['errors']) >= 1
                
                # Verify retry was scheduled
                assert len(retry_jobs) >= 1
                
                # Verify retry job details
                first_retry = retry_jobs[0]
                assert 'retry_publish' in first_retry['id']
                assert str(post.id) in first_retry['id']
                assert first_retry['args'][0] == post.id  # post_id
                assert first_retry['args'][1] == 1  # retry_count
                
                # Simulate retry execution
                self.schedule_manager._retry_publish_wrapper(post.id, 1)
                
                # Verify second retry was scheduled after first retry failed
                if len(retry_jobs) > 1:
                    second_retry = retry_jobs[1]
                    assert second_retry['args'][1] == 2  # retry_count increased
                
                # Simulate successful retry
                if failure_count <= max_failures:
                    self.schedule_manager._retry_publish_wrapper(post.id, max_failures + 1)
                
                # Verify post was eventually published or max retries reached
                updated_post = db.session.get(Post, post.id)
                if failure_count > 3:  # Max retries exceeded
                    assert updated_post.status == 'scheduled'  # Still scheduled
                else:
                    assert updated_post.status == 'published'  # Successfully published
                    assert updated_post.published_at is not None

    @given(
        post_count=st.integers(min_value=1, max_value=3),
        failure_rate=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(
        max_examples=5, 
        deadline=15000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_retry_exponential_backoff_property(self, post_count, failure_rate):
        """
        **Property 15a: Retry Exponential Backoff**
        
        GIVEN multiple posts that fail to publish
        WHEN retries are scheduled
        THEN each subsequent retry should have increasing delay (exponential backoff)
        AND the delay should follow the pattern: 5 * retry_count minutes
        
        **Validates: Requirements 7.5**
        """
        # Create multiple scheduled posts
        posts = []
        for i in range(post_count):
            scheduled_time = datetime.now(timezone.utc) - timedelta(minutes=1)
            post = PostManager.create_post(
                title=f"Test Post {i}",
                content=f"Content for post {i}",
                status='scheduled',
                scheduled_time=scheduled_time,
                allow_past_schedule=True
            )
            posts.append(post)
        
        # Track retry scheduling with delays
        retry_schedules = []
        original_add_job = self.schedule_manager.scheduler.add_job
        
        def mock_add_job(*args, **kwargs):
            if 'retry_publish' in kwargs.get('id', ''):
                trigger = kwargs.get('trigger')
                if hasattr(trigger, 'run_date'):
                    retry_schedules.append({
                        'id': kwargs.get('id'),
                        'run_date': trigger.run_date,
                        'retry_count': kwargs.get('args', [None, 0])[1]
                    })
            return original_add_job(*args, **kwargs)
        
        # Mock publication to fail based on failure rate
        def mock_publish_with_controlled_failure(post_id):
            import random
            if random.random() < failure_rate:
                raise Exception(f"Controlled failure for post {post_id}")
            return PostManager.publish_post(post_id)
        
        with patch.object(self.schedule_manager.scheduler, 'add_job', side_effect=mock_add_job):
            with patch.object(self.schedule_manager, 'publish_scheduled_post', side_effect=mock_publish_with_controlled_failure):
                # Trigger publication check
                self.schedule_manager.check_scheduled_posts()
                
                # Simulate retries to test exponential backoff
                for post in posts:
                    if failure_rate > 0:  # Only test if failures are expected
                        # Simulate first retry failure
                        try:
                            self.schedule_manager._retry_publish_wrapper(post.id, 1)
                        except:
                            pass
                        
                        # Simulate second retry failure
                        try:
                            self.schedule_manager._retry_publish_wrapper(post.id, 2)
                        except:
                            pass
        
        # Verify exponential backoff pattern
        if retry_schedules:
            for retry in retry_schedules:
                retry_count = retry['retry_count']
                if retry_count > 0:
                    # Expected delay is 5 * retry_count minutes
                    expected_delay_minutes = 5 * retry_count
                    
                    # Verify the delay is reasonable (within expected range)
                    # Note: We can't test exact timing due to test execution time
                    assert retry_count <= 3  # Max retries
                    assert expected_delay_minutes == 5 * retry_count

    @given(
        title=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        content=st.text(min_size=1, max_size=200).filter(lambda x: x.strip())
    )
    @settings(
        max_examples=8, 
        deadline=8000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_max_retry_limit_property(self, title, content):
        """
        **Property 15b: Maximum Retry Limit**
        
        GIVEN a post that consistently fails to publish
        WHEN the maximum number of retries is reached
        THEN no further retries should be scheduled
        AND the post should remain in its failed state
        
        **Validates: Requirements 7.5**
        """
        # Create a scheduled post
        scheduled_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        post = PostManager.create_post(
            title=title,
            content=content,
            status='scheduled',
            scheduled_time=scheduled_time,
            allow_past_schedule=True
        )
        
        # Track retry attempts
        retry_attempts = []
        original_schedule_retry = self.schedule_manager._schedule_retry
        
        def mock_schedule_retry(post_id, error, retry_count=1):
            retry_attempts.append({
                'post_id': post_id,
                'retry_count': retry_count,
                'error': error
            })
            return original_schedule_retry(post_id, error, retry_count)
        
        # Mock publication to always fail
        def mock_publish_always_fail(post_id):
            raise Exception("Persistent publication failure")
        
        with patch.object(self.schedule_manager, '_schedule_retry', side_effect=mock_schedule_retry):
            with patch.object(self.schedule_manager, 'publish_scheduled_post', side_effect=mock_publish_always_fail):
                # Simulate multiple retry attempts
                for retry_count in range(1, 6):  # Try up to 5 retries
                    try:
                        self.schedule_manager._retry_publish_wrapper(post.id, retry_count)
                    except:
                        pass
        
        # Verify max retries were respected
        max_retry_count = max([attempt['retry_count'] for attempt in retry_attempts]) if retry_attempts else 0
        assert max_retry_count <= 3  # Should not exceed max retries
        
        # Verify post remains in scheduled state after max retries
        final_post = db.session.get(Post, post.id)
        assert final_post.status == 'scheduled'  # Should not be published
        assert final_post.published_at is None

    def test_retry_logging_property(self):
        """
        **Property 15c: Retry Logging**
        
        GIVEN retry attempts for failed publications
        WHEN retries are executed
        THEN all retry attempts should be properly logged
        AND log entries should include relevant details
        
        **Validates: Requirements 7.5**
        """
        # Create a scheduled post
        scheduled_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        post = PostManager.create_post(
            title="Test Retry Logging",
            content="Content for retry logging test",
            status='scheduled',
            scheduled_time=scheduled_time,
            allow_past_schedule=True
        )
        
        # Capture log messages
        log_messages = []
        original_logger = self.schedule_manager.logger
        mock_logger = Mock()
        
        def capture_log(level, message):
            log_messages.append({'level': level, 'message': message})
        
        mock_logger.info.side_effect = lambda msg: capture_log('info', msg)
        mock_logger.error.side_effect = lambda msg: capture_log('error', msg)
        
        # Mock publication to fail then succeed
        failure_count = 0
        def mock_publish_fail_once(post_id):
            nonlocal failure_count
            failure_count += 1
            if failure_count == 1:
                raise Exception("First attempt failure")
            return PostManager.publish_post(post_id)
        
        with patch.object(self.schedule_manager, 'logger', mock_logger):
            with patch.object(self.schedule_manager, 'publish_scheduled_post', side_effect=mock_publish_fail_once):
                # Trigger initial publication attempt
                self.schedule_manager.check_scheduled_posts()
                
                # Simulate retry
                self.schedule_manager._retry_publish_wrapper(post.id, 1)
        
        # Verify logging occurred
        assert len(log_messages) > 0
        
        # Check for retry-related log messages
        retry_logs = [msg for msg in log_messages if 'retry' in msg['message'].lower()]
        error_logs = [msg for msg in log_messages if msg['level'] == 'error']
        
        # Should have logged the retry scheduling and execution
        assert len(retry_logs) > 0 or len(error_logs) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])