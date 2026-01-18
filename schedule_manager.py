"""
Schedule Management System for Enhanced Content Management

This module provides the ScheduleManager class for handling background task scheduling
including automatic post publication, task management, and error handling.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from flask import Flask

from models import db, Post
from post_manager import PostManager


class ScheduleManager:
    """
    Manages background task scheduling for the blog system including
    automatic post publication, task monitoring, and error handling.
    """
    
    def __init__(self, app: Flask = None):
        """
        Initialize APScheduler with Flask app.
        
        Args:
            app: Flask application instance (optional)
            
        Requirements: 7.1
        """
        self.scheduler = None
        self.app = None
        self.logger = logging.getLogger(__name__)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """
        Initialize scheduler with Flask application.
        
        Args:
            app: Flask application instance
            
        Requirements: 7.1
        """
        self.app = app
        
        # Configure scheduler
        self.scheduler = BackgroundScheduler(
            timezone='UTC',
            job_defaults={
                'coalesce': True,  # Combine multiple pending executions
                'max_instances': 1,  # Only one instance of each job at a time
                'misfire_grace_time': 300  # 5 minutes grace time for missed jobs
            }
        )
        
        # Add event listeners for logging
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
        
        # Store scheduler in app context
        app.extensions = getattr(app, 'extensions', {})
        app.extensions['scheduler'] = self
        
        # Set up recurring publication check
        self.schedule_publication_check()
    
    def start(self) -> None:
        """Start the background scheduler."""
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            self.logger.info("Background scheduler started")
    
    def shutdown(self) -> None:
        """Shutdown the background scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.logger.info("Background scheduler shutdown")
    
    def schedule_publication_check(self) -> None:
        """
        Set up recurring task for checking publications.
        
        This task runs every minute to check for posts ready for publication.
        
        Requirements: 7.1, 7.2
        """
        if not self.scheduler:
            return
        
        # Remove existing job if it exists
        try:
            self.scheduler.remove_job('publication_check')
        except:
            pass
        
        # Add recurring publication check job
        self.scheduler.add_job(
            func=self._check_scheduled_posts_wrapper,
            trigger=IntervalTrigger(minutes=1),
            id='publication_check',
            name='Check Scheduled Posts',
            replace_existing=True
        )
        
        self.logger.info("Scheduled recurring publication check every minute")
    
    def _check_scheduled_posts_wrapper(self) -> None:
        """
        Wrapper for checking scheduled posts with Flask app context.
        
        This method ensures the database operations run within the Flask app context.
        """
        if not self.app:
            self.logger.error("No Flask app context available for scheduled task")
            return
        
        with self.app.app_context():
            self.check_scheduled_posts()
    
    def check_scheduled_posts(self) -> Dict[str, Any]:
        """
        Background task to check and publish scheduled posts.
        
        Returns:
            Dictionary with publication results
            
        Requirements: 1.2, 1.5, 7.2, 7.3, 7.4
        """
        results = {
            'checked_at': datetime.now(timezone.utc),
            'posts_published': 0,
            'posts_failed': 0,
            'errors': []
        }
        
        try:
            # Get posts ready for publication
            ready_posts = PostManager.get_scheduled_posts_ready_for_publication()
            
            self.logger.info(f"Found {len(ready_posts)} posts ready for publication")
            
            for post in ready_posts:
                try:
                    # Publish the post
                    published_post = self.publish_scheduled_post(post.id)
                    
                    if published_post:
                        results['posts_published'] += 1
                        self.logger.info(f"Published post {post.id}: '{post.title}'")
                        
                        # Log publication event
                        self._log_publication_event(post, success=True)
                    else:
                        results['posts_failed'] += 1
                        error_msg = f"Failed to publish post {post.id}: Post not found"
                        results['errors'].append(error_msg)
                        self.logger.error(error_msg)
                        
                        # Log publication failure
                        self._log_publication_event(post, success=False, error=error_msg)
                
                except Exception as e:
                    results['posts_failed'] += 1
                    error_msg = f"Error publishing post {post.id}: {str(e)}"
                    results['errors'].append(error_msg)
                    self.logger.error(error_msg)
                    
                    # Log publication failure
                    self._log_publication_event(post, success=False, error=error_msg)
                    
                    # Schedule retry if configured
                    self._schedule_retry(post.id, str(e))
        
        except Exception as e:
            error_msg = f"Error in scheduled post check: {str(e)}"
            results['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return results
    
    def publish_scheduled_post(self, post_id: int) -> Optional[Post]:
        """
        Publish a specific scheduled post.
        
        Args:
            post_id: ID of the post to publish
            
        Returns:
            Published Post object or None if failed
            
        Requirements: 1.2, 1.5, 7.2
        """
        try:
            return PostManager.publish_post(post_id)
        except Exception as e:
            self.logger.error(f"Error publishing post {post_id}: {str(e)}")
            return None
    
    def schedule_post_publication(self, post_id: int, publish_time: datetime) -> bool:
        """
        Schedule a specific post for publication at a specific time.
        
        Args:
            post_id: ID of the post to schedule
            publish_time: When to publish the post
            
        Returns:
            True if scheduled successfully, False otherwise
            
        Requirements: 1.2, 7.2
        """
        if not self.scheduler:
            return False
        
        try:
            job_id = f"publish_post_{post_id}"
            
            # Remove existing job if it exists
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
            
            # Schedule the publication
            self.scheduler.add_job(
                func=self._publish_post_wrapper,
                trigger=DateTrigger(run_date=publish_time),
                args=[post_id],
                id=job_id,
                name=f"Publish Post {post_id}",
                replace_existing=True
            )
            
            self.logger.info(f"Scheduled post {post_id} for publication at {publish_time}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error scheduling post {post_id}: {str(e)}")
            return False
    
    def _publish_post_wrapper(self, post_id: int) -> None:
        """
        Wrapper for publishing a post with Flask app context.
        
        Args:
            post_id: ID of the post to publish
        """
        if not self.app:
            self.logger.error(f"No Flask app context available for publishing post {post_id}")
            return
        
        with self.app.app_context():
            self.publish_scheduled_post(post_id)
    
    def cancel_scheduled_publication(self, post_id: int) -> bool:
        """
        Cancel a scheduled publication for a specific post.
        
        Args:
            post_id: ID of the post to cancel
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        if not self.scheduler:
            return False
        
        try:
            job_id = f"publish_post_{post_id}"
            self.scheduler.remove_job(job_id)
            self.logger.info(f"Cancelled scheduled publication for post {post_id}")
            return True
        except:
            return False
    
    def _schedule_retry(self, post_id: int, error: str, retry_count: int = 1) -> None:
        """
        Schedule retry for failed publication.
        
        Args:
            post_id: ID of the post that failed
            error: Error message
            retry_count: Current retry attempt
            
        Requirements: 7.5
        """
        max_retries = 3
        retry_delay_minutes = 5 * retry_count  # Exponential backoff
        
        if retry_count > max_retries:
            self.logger.error(f"Max retries exceeded for post {post_id}")
            return
        
        try:
            retry_time = datetime.now(timezone.utc).replace(
                minute=datetime.now(timezone.utc).minute + retry_delay_minutes
            )
            
            job_id = f"retry_publish_{post_id}_{retry_count}"
            
            self.scheduler.add_job(
                func=self._retry_publish_wrapper,
                trigger=DateTrigger(run_date=retry_time),
                args=[post_id, retry_count],
                id=job_id,
                name=f"Retry Publish Post {post_id} (Attempt {retry_count})",
                replace_existing=True
            )
            
            self.logger.info(f"Scheduled retry {retry_count} for post {post_id} at {retry_time}")
            
        except Exception as e:
            self.logger.error(f"Error scheduling retry for post {post_id}: {str(e)}")
    
    def _retry_publish_wrapper(self, post_id: int, retry_count: int) -> None:
        """
        Wrapper for retrying post publication with Flask app context.
        
        Args:
            post_id: ID of the post to retry
            retry_count: Current retry attempt
        """
        if not self.app:
            self.logger.error(f"No Flask app context available for retry {retry_count} of post {post_id}")
            return
        
        with self.app.app_context():
            try:
                published_post = self.publish_scheduled_post(post_id)
                
                if published_post:
                    self.logger.info(f"Successfully published post {post_id} on retry {retry_count}")
                    self._log_publication_event(published_post, success=True, retry_count=retry_count)
                else:
                    error_msg = f"Retry {retry_count} failed for post {post_id}: Post not found"
                    self.logger.error(error_msg)
                    self._schedule_retry(post_id, error_msg, retry_count + 1)
                    
            except Exception as e:
                error_msg = f"Retry {retry_count} failed for post {post_id}: {str(e)}"
                self.logger.error(error_msg)
                self._schedule_retry(post_id, error_msg, retry_count + 1)
    
    def _log_publication_event(self, post: Post, success: bool, error: str = None, retry_count: int = 0) -> None:
        """
        Log publication events for audit purposes.
        
        Args:
            post: Post object
            success: Whether publication was successful
            error: Error message if failed
            retry_count: Retry attempt number
            
        Requirements: 7.4
        """
        event_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'post_id': post.id,
            'post_title': post.title,
            'success': success,
            'retry_count': retry_count
        }
        
        if error:
            event_data['error'] = error
        
        if success:
            self.logger.info(f"Publication event: {event_data}")
        else:
            self.logger.error(f"Publication failure: {event_data}")
    
    def _job_executed(self, event) -> None:
        """Handle successful job execution events."""
        self.logger.debug(f"Job {event.job_id} executed successfully")
    
    def _job_error(self, event) -> None:
        """Handle job error events."""
        self.logger.error(f"Job {event.job_id} failed: {event.exception}")
    
    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """
        Get information about currently scheduled jobs.
        
        Returns:
            List of job information dictionaries
        """
        if not self.scheduler:
            return []
        
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return jobs
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Get current scheduler status and statistics.
        
        Returns:
            Dictionary with scheduler status information
        """
        if not self.scheduler:
            return {'running': False, 'jobs': 0}
        
        return {
            'running': self.scheduler.running,
            'jobs': len(self.scheduler.get_jobs()),
            'state': str(self.scheduler.state)
        }