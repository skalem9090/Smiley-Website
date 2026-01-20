"""
Background Task Coordination Module

This module coordinates all background tasks including:
- Newsletter digest generation and sending
- Search index maintenance
- Feed cache updates
- Comment moderation notifications
- System health monitoring
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from models import db, Post, Comment, NewsletterSubscription
from newsletter_manager import NewsletterManager
from search_engine import SearchEngine
from feature_integration import FeatureIntegration


class BackgroundTaskCoordinator:
    """Coordinates all background tasks for the blog system."""
    
    def __init__(self, app=None):
        """Initialize BackgroundTaskCoordinator with optional Flask app."""
        self.app = app
        self.scheduler = None
        self.newsletter_manager = None
        self.search_engine = None
        self.feature_integration = None
        self.logger = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app configuration."""
        self.app = app
        self.logger = app.logger
        
        # Initialize managers
        self.newsletter_manager = NewsletterManager(app)
        self.search_engine = SearchEngine(app)
        self.feature_integration = FeatureIntegration(app)
        
        # Initialize scheduler
        self.scheduler = BackgroundScheduler(
            daemon=True,
            timezone='UTC'
        )
        
        # Configuration
        self.enable_digest_generation = app.config.get('ENABLE_DIGEST_GENERATION', True)
        self.enable_search_indexing = app.config.get('ENABLE_SEARCH_INDEXING', True)
        self.enable_feed_updates = app.config.get('ENABLE_FEED_UPDATES', True)
        
        # Schedule tasks
        self._schedule_tasks()
    
    def _schedule_tasks(self):
        """Schedule all background tasks."""
        if not self.scheduler:
            return
        
        # Weekly newsletter digest (every Monday at 9 AM UTC)
        if self.enable_digest_generation:
            self.scheduler.add_job(
                func=self._generate_weekly_digest,
                trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),
                id='weekly_digest',
                name='Generate Weekly Newsletter Digest',
                replace_existing=True
            )
            if self.logger:
                self.logger.info("Scheduled weekly newsletter digest task")
        
        # Bi-weekly newsletter digest (every other Monday at 9 AM UTC)
        if self.enable_digest_generation:
            self.scheduler.add_job(
                func=self._generate_biweekly_digest,
                trigger=CronTrigger(day_of_week='mon', hour=9, minute=0, week='*/2'),
                id='biweekly_digest',
                name='Generate Bi-weekly Newsletter Digest',
                replace_existing=True
            )
            if self.logger:
                self.logger.info("Scheduled bi-weekly newsletter digest task")
        
        # Monthly newsletter digest (first Monday of month at 9 AM UTC)
        if self.enable_digest_generation:
            self.scheduler.add_job(
                func=self._generate_monthly_digest,
                trigger=CronTrigger(day_of_week='mon', day='1-7', hour=9, minute=0),
                id='monthly_digest',
                name='Generate Monthly Newsletter Digest',
                replace_existing=True
            )
            if self.logger:
                self.logger.info("Scheduled monthly newsletter digest task")
        
        # Search index maintenance (daily at 2 AM UTC)
        if self.enable_search_indexing:
            self.scheduler.add_job(
                func=self._maintain_search_index,
                trigger=CronTrigger(hour=2, minute=0),
                id='search_index_maintenance',
                name='Maintain Search Index',
                replace_existing=True
            )
            if self.logger:
                self.logger.info("Scheduled search index maintenance task")
        
        # Feed cache cleanup (every 6 hours)
        if self.enable_feed_updates:
            self.scheduler.add_job(
                func=self._cleanup_feed_cache,
                trigger=IntervalTrigger(hours=6),
                id='feed_cache_cleanup',
                name='Cleanup Feed Cache',
                replace_existing=True
            )
            if self.logger:
                self.logger.info("Scheduled feed cache cleanup task")
        
        # Comment moderation reminder (daily at 10 AM UTC)
        self.scheduler.add_job(
            func=self._send_moderation_reminder,
            trigger=CronTrigger(hour=10, minute=0),
            id='moderation_reminder',
            name='Send Comment Moderation Reminder',
            replace_existing=True
        )
        if self.logger:
            self.logger.info("Scheduled comment moderation reminder task")
        
        # System health check (every hour)
        self.scheduler.add_job(
            func=self._check_system_health,
            trigger=IntervalTrigger(hours=1),
            id='system_health_check',
            name='Check System Health',
            replace_existing=True
        )
        if self.logger:
            self.logger.info("Scheduled system health check task")
    
    def start(self):
        """Start the background task scheduler."""
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            if self.logger:
                self.logger.info("Background task scheduler started")
    
    def stop(self):
        """Stop the background task scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            if self.logger:
                self.logger.info("Background task scheduler stopped")
    
    def _generate_weekly_digest(self):
        """Generate and send weekly newsletter digest."""
        try:
            if self.logger:
                self.logger.info("Starting weekly digest generation")
            
            with self.app.app_context():
                # Get subscribers with weekly frequency
                subscribers = NewsletterSubscription.query.filter_by(
                    is_confirmed=True,
                    frequency='weekly'
                ).all()
                
                if not subscribers:
                    if self.logger:
                        self.logger.info("No weekly subscribers found")
                    return
                
                # Get posts from last week
                week_ago = datetime.now(timezone.utc) - timedelta(days=7)
                recent_posts = Post.query.filter(
                    Post.status == 'published',
                    Post.created_at >= week_ago
                ).order_by(Post.created_at.desc()).all()
                
                if not recent_posts:
                    if self.logger:
                        self.logger.info("No posts from last week for weekly digest")
                    return
                
                # Generate and send digest
                success_count = 0
                for subscriber in subscribers:
                    try:
                        success, message = self.newsletter_manager.send_digest(
                            subscriber.email,
                            recent_posts,
                            'weekly'
                        )
                        if success:
                            success_count += 1
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Error sending weekly digest to {subscriber.email}: {str(e)}")
                
                if self.logger:
                    self.logger.info(f"Weekly digest sent to {success_count}/{len(subscribers)} subscribers")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in weekly digest generation: {str(e)}")
    
    def _generate_biweekly_digest(self):
        """Generate and send bi-weekly newsletter digest."""
        try:
            if self.logger:
                self.logger.info("Starting bi-weekly digest generation")
            
            with self.app.app_context():
                # Get subscribers with bi-weekly frequency
                subscribers = NewsletterSubscription.query.filter_by(
                    is_confirmed=True,
                    frequency='biweekly'
                ).all()
                
                if not subscribers:
                    if self.logger:
                        self.logger.info("No bi-weekly subscribers found")
                    return
                
                # Get posts from last two weeks
                two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)
                recent_posts = Post.query.filter(
                    Post.status == 'published',
                    Post.created_at >= two_weeks_ago
                ).order_by(Post.created_at.desc()).all()
                
                if not recent_posts:
                    if self.logger:
                        self.logger.info("No posts from last two weeks for bi-weekly digest")
                    return
                
                # Generate and send digest
                success_count = 0
                for subscriber in subscribers:
                    try:
                        success, message = self.newsletter_manager.send_digest(
                            subscriber.email,
                            recent_posts,
                            'biweekly'
                        )
                        if success:
                            success_count += 1
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Error sending bi-weekly digest to {subscriber.email}: {str(e)}")
                
                if self.logger:
                    self.logger.info(f"Bi-weekly digest sent to {success_count}/{len(subscribers)} subscribers")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in bi-weekly digest generation: {str(e)}")
    
    def _generate_monthly_digest(self):
        """Generate and send monthly newsletter digest."""
        try:
            if self.logger:
                self.logger.info("Starting monthly digest generation")
            
            with self.app.app_context():
                # Get subscribers with monthly frequency
                subscribers = NewsletterSubscription.query.filter_by(
                    is_confirmed=True,
                    frequency='monthly'
                ).all()
                
                if not subscribers:
                    if self.logger:
                        self.logger.info("No monthly subscribers found")
                    return
                
                # Get posts from last month
                month_ago = datetime.now(timezone.utc) - timedelta(days=30)
                recent_posts = Post.query.filter(
                    Post.status == 'published',
                    Post.created_at >= month_ago
                ).order_by(Post.created_at.desc()).all()
                
                if not recent_posts:
                    if self.logger:
                        self.logger.info("No posts from last month for monthly digest")
                    return
                
                # Generate and send digest
                success_count = 0
                for subscriber in subscribers:
                    try:
                        success, message = self.newsletter_manager.send_digest(
                            subscriber.email,
                            recent_posts,
                            'monthly'
                        )
                        if success:
                            success_count += 1
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Error sending monthly digest to {subscriber.email}: {str(e)}")
                
                if self.logger:
                    self.logger.info(f"Monthly digest sent to {success_count}/{len(subscribers)} subscribers")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in monthly digest generation: {str(e)}")
    
    def _maintain_search_index(self):
        """Maintain and optimize search index."""
        try:
            if self.logger:
                self.logger.info("Starting search index maintenance")
            
            with self.app.app_context():
                # Reindex all published posts
                published_posts = Post.query.filter_by(status='published').all()
                
                indexed_count = 0
                for post in published_posts:
                    try:
                        self.search_engine.index_post(post)
                        indexed_count += 1
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Error indexing post {post.id}: {str(e)}")
                
                if self.logger:
                    self.logger.info(f"Search index maintenance completed: {indexed_count} posts indexed")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in search index maintenance: {str(e)}")
    
    def _cleanup_feed_cache(self):
        """Cleanup feed cache."""
        try:
            if self.logger:
                self.logger.info("Starting feed cache cleanup")
            
            # Feed cache cleanup logic would go here
            # For now, this is a placeholder since feeds are generated on-demand
            
            if self.logger:
                self.logger.info("Feed cache cleanup completed")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in feed cache cleanup: {str(e)}")
    
    def _send_moderation_reminder(self):
        """Send reminder about pending comments to moderators."""
        try:
            if self.logger:
                self.logger.info("Checking for pending comments")
            
            with self.app.app_context():
                # Get pending comments count
                pending_count = Comment.query.filter_by(
                    is_approved=False,
                    is_spam=False
                ).count()
                
                if pending_count > 0:
                    if self.logger:
                        self.logger.info(f"Found {pending_count} pending comments")
                    # Email notification logic would go here
                else:
                    if self.logger:
                        self.logger.info("No pending comments")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in moderation reminder: {str(e)}")
    
    def _check_system_health(self):
        """Check system health and log status."""
        try:
            with self.app.app_context():
                health_status = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'database': self._check_database_health(),
                    'search_engine': self._check_search_engine_health(),
                    'newsletter': self._check_newsletter_health()
                }
                
                # Log health status
                if all(health_status.values()):
                    if self.logger:
                        self.logger.debug("System health check: All systems operational")
                else:
                    if self.logger:
                        self.logger.warning(f"System health check: Issues detected - {health_status}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in system health check: {str(e)}")
    
    def _check_database_health(self) -> bool:
        """Check database connectivity."""
        try:
            db.session.execute(db.text('SELECT 1'))
            return True
        except Exception:
            return False
    
    def _check_search_engine_health(self) -> bool:
        """Check search engine status."""
        try:
            return self.search_engine is not None
        except Exception:
            return False
    
    def _check_newsletter_health(self) -> bool:
        """Check newsletter service status."""
        try:
            return self.newsletter_manager is not None
        except Exception:
            return False
    
    def get_task_status(self) -> Dict[str, Any]:
        """
        Get status of all scheduled tasks.
        
        Returns:
            Dictionary with task status information
        """
        if not self.scheduler:
            return {'error': 'Scheduler not initialized'}
        
        jobs = self.scheduler.get_jobs()
        task_status = {
            'scheduler_running': self.scheduler.running,
            'total_jobs': len(jobs),
            'jobs': []
        }
        
        for job in jobs:
            task_status['jobs'].append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return task_status
    
    def run_task_now(self, task_id: str) -> Dict[str, Any]:
        """
        Run a scheduled task immediately.
        
        Args:
            task_id: ID of the task to run
            
        Returns:
            Dictionary with execution result
        """
        try:
            if not self.scheduler:
                return {'success': False, 'error': 'Scheduler not initialized'}
            
            job = self.scheduler.get_job(task_id)
            if not job:
                return {'success': False, 'error': f'Task {task_id} not found'}
            
            # Run the job immediately
            job.func()
            
            return {
                'success': True,
                'message': f'Task {task_id} executed successfully',
                'task_name': job.name
            }
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error running task {task_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
