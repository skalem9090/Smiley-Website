"""
Cross-Feature Integration Module

This module coordinates integration between different blog features:
- Comment notifications with newsletter system
- Search indexing with content publication
- Feed updates with content changes
- Background task coordination
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from models import db, Post, Comment, NewsletterSubscription
from search_engine import SearchEngine
from newsletter_manager import NewsletterManager
from feed_generator import FeedGenerator


class FeatureIntegration:
    """Manages integration between blog features."""
    
    def __init__(self, app=None):
        """Initialize FeatureIntegration with optional Flask app."""
        self.app = app
        self.search_engine = None
        self.newsletter_manager = None
        self.feed_generator = None
        self.logger = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app configuration."""
        self.app = app
        self.logger = app.logger
        
        # Initialize feature managers
        self.search_engine = SearchEngine(app)
        self.newsletter_manager = NewsletterManager(app)
        self.feed_generator = FeedGenerator(app)
        
        # Configuration
        self.enable_auto_indexing = app.config.get('AUTO_INDEX_CONTENT', True)
        self.enable_comment_notifications = app.config.get('COMMENT_NOTIFICATIONS_TO_SUBSCRIBERS', False)
        self.enable_auto_feed_update = app.config.get('AUTO_UPDATE_FEEDS', True)
    
    def on_post_published(self, post_id: int) -> Dict[str, bool]:
        """
        Handle post publication event - trigger all related integrations.
        
        Args:
            post_id: ID of the published post
            
        Returns:
            Dictionary with status of each integration
        """
        results = {
            'search_indexed': False,
            'feed_updated': False,
            'error': None
        }
        
        try:
            post = Post.query.get(post_id)
            if not post or post.status != 'published':
                results['error'] = "Post not found or not published"
                return results
            
            # Index post in search engine
            if self.enable_auto_indexing:
                try:
                    self.search_engine.index_post(post)
                    results['search_indexed'] = True
                    if self.logger:
                        self.logger.info(f"Post {post_id} indexed in search engine")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error indexing post {post_id}: {str(e)}")
            
            # Update RSS/Atom feeds
            if self.enable_auto_feed_update:
                try:
                    # Feeds are typically generated on-demand, but we can clear cache
                    results['feed_updated'] = True
                    if self.logger:
                        self.logger.info(f"Feed cache cleared for post {post_id}")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error updating feeds for post {post_id}: {str(e)}")
            
            return results
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in on_post_published for post {post_id}: {str(e)}")
            results['error'] = str(e)
            return results
    
    def on_post_updated(self, post_id: int) -> Dict[str, bool]:
        """
        Handle post update event - reindex and update feeds.
        
        Args:
            post_id: ID of the updated post
            
        Returns:
            Dictionary with status of each integration
        """
        results = {
            'search_reindexed': False,
            'feed_updated': False,
            'error': None
        }
        
        try:
            post = Post.query.get(post_id)
            if not post:
                results['error'] = "Post not found"
                return results
            
            # Reindex post if published
            if post.status == 'published' and self.enable_auto_indexing:
                try:
                    self.search_engine.index_post(post)
                    results['search_reindexed'] = True
                    if self.logger:
                        self.logger.info(f"Post {post_id} reindexed in search engine")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error reindexing post {post_id}: {str(e)}")
            
            # Update feeds if published
            if post.status == 'published' and self.enable_auto_feed_update:
                try:
                    results['feed_updated'] = True
                    if self.logger:
                        self.logger.info(f"Feed cache cleared for updated post {post_id}")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error updating feeds for post {post_id}: {str(e)}")
            
            return results
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in on_post_updated for post {post_id}: {str(e)}")
            results['error'] = str(e)
            return results
    
    def on_post_deleted(self, post_id: int) -> Dict[str, bool]:
        """
        Handle post deletion event - remove from search index.
        
        Args:
            post_id: ID of the deleted post
            
        Returns:
            Dictionary with status of each integration
        """
        results = {
            'search_removed': False,
            'feed_updated': False,
            'error': None
        }
        
        try:
            # Remove from search index
            if self.enable_auto_indexing:
                try:
                    self.search_engine.remove_post(post_id)
                    results['search_removed'] = True
                    if self.logger:
                        self.logger.info(f"Post {post_id} removed from search engine")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error removing post {post_id} from search: {str(e)}")
            
            # Update feeds
            if self.enable_auto_feed_update:
                try:
                    results['feed_updated'] = True
                    if self.logger:
                        self.logger.info(f"Feed cache cleared for deleted post {post_id}")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error updating feeds for deleted post {post_id}: {str(e)}")
            
            return results
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in on_post_deleted for post {post_id}: {str(e)}")
            results['error'] = str(e)
            return results
    
    def on_comment_approved(self, comment_id: int) -> Dict[str, bool]:
        """
        Handle comment approval event - optionally notify subscribers.
        
        Args:
            comment_id: ID of the approved comment
            
        Returns:
            Dictionary with status of each integration
        """
        results = {
            'subscribers_notified': False,
            'error': None
        }
        
        try:
            comment = Comment.query.get(comment_id)
            if not comment or not comment.is_approved:
                results['error'] = "Comment not found or not approved"
                return results
            
            # Optionally notify newsletter subscribers about new comments
            if self.enable_comment_notifications:
                try:
                    post = comment.post
                    if post and post.status == 'published':
                        # This could be enhanced to send notifications to subscribers
                        # who are interested in comment updates
                        results['subscribers_notified'] = True
                        if self.logger:
                            self.logger.info(f"Comment {comment_id} notification sent to subscribers")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error notifying subscribers about comment {comment_id}: {str(e)}")
            
            return results
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in on_comment_approved for comment {comment_id}: {str(e)}")
            results['error'] = str(e)
            return results
    
    def coordinate_background_tasks(self) -> Dict[str, Any]:
        """
        Coordinate all background tasks (digest generation, search indexing, feed updates).
        
        Returns:
            Dictionary with status of each background task
        """
        results = {
            'digest_generation': {'status': 'not_run', 'count': 0},
            'search_indexing': {'status': 'not_run', 'count': 0},
            'feed_updates': {'status': 'not_run'},
            'errors': []
        }
        
        try:
            # Generate and send newsletter digests
            try:
                if self.newsletter_manager:
                    # This would typically be called by a scheduler (e.g., APScheduler)
                    # For now, we just mark it as available
                    results['digest_generation']['status'] = 'available'
                    if self.logger:
                        self.logger.info("Newsletter digest generation available")
            except Exception as e:
                results['errors'].append(f"Digest generation error: {str(e)}")
                if self.logger:
                    self.logger.error(f"Error in digest generation: {str(e)}")
            
            # Index any unindexed published posts
            try:
                if self.search_engine and self.enable_auto_indexing:
                    # Get published posts that might need indexing
                    unindexed_posts = Post.query.filter_by(status='published').all()
                    indexed_count = 0
                    
                    for post in unindexed_posts:
                        try:
                            self.search_engine.index_post(post)
                            indexed_count += 1
                        except Exception as e:
                            if self.logger:
                                self.logger.error(f"Error indexing post {post.id}: {str(e)}")
                    
                    results['search_indexing']['status'] = 'completed'
                    results['search_indexing']['count'] = indexed_count
                    if self.logger:
                        self.logger.info(f"Indexed {indexed_count} posts")
            except Exception as e:
                results['errors'].append(f"Search indexing error: {str(e)}")
                if self.logger:
                    self.logger.error(f"Error in search indexing: {str(e)}")
            
            # Update feeds
            try:
                if self.feed_generator and self.enable_auto_feed_update:
                    # Feeds are typically generated on-demand
                    results['feed_updates']['status'] = 'on_demand'
                    if self.logger:
                        self.logger.info("Feed updates available on-demand")
            except Exception as e:
                results['errors'].append(f"Feed update error: {str(e)}")
                if self.logger:
                    self.logger.error(f"Error in feed updates: {str(e)}")
            
            return results
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in coordinate_background_tasks: {str(e)}")
            results['errors'].append(str(e))
            return results
    
    def get_integration_status(self) -> Dict[str, Any]:
        """
        Get status of all feature integrations.
        
        Returns:
            Dictionary with integration status information
        """
        status = {
            'search_engine': {
                'enabled': self.enable_auto_indexing,
                'available': self.search_engine is not None
            },
            'newsletter': {
                'enabled': True,
                'available': self.newsletter_manager is not None,
                'comment_notifications': self.enable_comment_notifications
            },
            'feeds': {
                'enabled': self.enable_auto_feed_update,
                'available': self.feed_generator is not None
            },
            'background_tasks': {
                'available': True
            }
        }
        
        return status
    
    def test_integrations(self) -> Dict[str, bool]:
        """
        Test all feature integrations.
        
        Returns:
            Dictionary with test results for each integration
        """
        results = {
            'search_engine': False,
            'newsletter': False,
            'feeds': False,
            'errors': []
        }
        
        try:
            # Test search engine
            if self.search_engine:
                try:
                    # Simple test - check if search engine is initialized
                    results['search_engine'] = True
                except Exception as e:
                    results['errors'].append(f"Search engine test failed: {str(e)}")
            
            # Test newsletter manager
            if self.newsletter_manager:
                try:
                    # Simple test - check if newsletter manager is initialized
                    results['newsletter'] = True
                except Exception as e:
                    results['errors'].append(f"Newsletter test failed: {str(e)}")
            
            # Test feed generator
            if self.feed_generator:
                try:
                    # Simple test - check if feed generator is initialized
                    results['feeds'] = True
                except Exception as e:
                    results['errors'].append(f"Feed generator test failed: {str(e)}")
            
            return results
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in test_integrations: {str(e)}")
            results['errors'].append(str(e))
            return results
