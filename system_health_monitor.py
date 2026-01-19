"""
System Health Monitor for comprehensive system status monitoring.

This module provides health checks for all major system components including
database connectivity, search indexing, email services, feed generation,
and overall system performance metrics.
"""

import os
import time
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple, Optional
from flask import current_app
from models import db, Post, Comment, NewsletterSubscription, SearchQuery
from sqlalchemy import text
import sendgrid
from python_http_client.exceptions import HTTPError


class SystemHealthMonitor:
    """Monitor system health across all components."""
    
    def __init__(self, app=None):
        """Initialize SystemHealthMonitor with optional Flask app."""
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app configuration."""
        self.app = app
        
        # Health check configuration
        self.check_timeout = app.config.get('HEALTH_CHECK_TIMEOUT', 5)  # seconds
        self.database_timeout = app.config.get('DATABASE_TIMEOUT', 3)
        self.email_timeout = app.config.get('EMAIL_TIMEOUT', 10)
        
        # Performance thresholds
        self.slow_query_threshold = app.config.get('SLOW_QUERY_THRESHOLD', 1.0)  # seconds
        self.high_memory_threshold = app.config.get('HIGH_MEMORY_THRESHOLD', 500)  # MB
        
        # Service configurations
        self.sendgrid_api_key = app.config.get('SENDGRID_API_KEY') or os.environ.get('SENDGRID_API_KEY')
        self.base_url = app.config.get('BASE_URL', 'http://localhost:5000')
    
    def get_overall_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status.
        
        Returns:
            Dictionary with overall health status and component details
        """
        try:
            start_time = time.time()
            
            # Run all health checks
            health_checks = {
                'database': self.check_database_health(),
                'search_index': self.check_search_index_health(),
                'email_service': self.check_email_service_health(),
                'feed_generation': self.check_feed_generation_health(),
                'file_system': self.check_file_system_health(),
                'performance': self.check_performance_metrics()
            }
            
            # Calculate overall status
            all_statuses = [check['status'] for check in health_checks.values()]
            
            if all(status == 'healthy' for status in all_statuses):
                overall_status = 'healthy'
            elif any(status == 'critical' for status in all_statuses):
                overall_status = 'critical'
            elif any(status == 'warning' for status in all_statuses):
                overall_status = 'warning'
            else:
                overall_status = 'unknown'
            
            # Calculate check duration
            check_duration = time.time() - start_time
            
            return {
                'overall_status': overall_status,
                'check_timestamp': datetime.now(timezone.utc).isoformat(),
                'check_duration': round(check_duration, 3),
                'components': health_checks,
                'summary': self._generate_health_summary(health_checks)
            }
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting overall health: {str(e)}")
            
            return {
                'overall_status': 'critical',
                'check_timestamp': datetime.now(timezone.utc).isoformat(),
                'check_duration': 0,
                'components': {},
                'error': str(e),
                'summary': {'healthy': 0, 'warning': 0, 'critical': 1, 'total': 1}
            }
    
    def check_database_health(self) -> Dict[str, Any]:
        """
        Check database connectivity and performance.
        
        Returns:
            Dictionary with database health status
        """
        try:
            start_time = time.time()
            
            # Test basic connectivity
            db.session.execute(text('SELECT 1')).scalar()
            
            # Test table access
            post_count = db.session.query(Post).count()
            comment_count = db.session.query(Comment).count()
            subscription_count = db.session.query(NewsletterSubscription).count()
            
            # Check for recent activity
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_posts = db.session.query(Post).filter(
                Post.created_at >= recent_cutoff
            ).count()
            
            query_time = time.time() - start_time
            
            # Determine status
            if query_time > self.slow_query_threshold:
                status = 'warning'
                message = f"Database queries are slow ({query_time:.2f}s)"
            else:
                status = 'healthy'
                message = "Database is responsive"
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'query_time': round(query_time, 3),
                    'post_count': post_count,
                    'comment_count': comment_count,
                    'subscription_count': subscription_count,
                    'recent_posts': recent_posts,
                    'connection_pool': self._get_connection_pool_info()
                },
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Database health check failed: {str(e)}")
            
            return {
                'status': 'critical',
                'message': f"Database connection failed: {str(e)}",
                'details': {'error': str(e)},
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
    
    def check_search_index_health(self) -> Dict[str, Any]:
        """
        Check search index status and performance.
        
        Returns:
            Dictionary with search index health status
        """
        try:
            start_time = time.time()
            
            # Check if FTS table exists
            fts_exists = db.session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='post_search_fts'")
            ).scalar()
            
            if not fts_exists:
                return {
                    'status': 'critical',
                    'message': "Search index table does not exist",
                    'details': {'fts_table_exists': False},
                    'last_checked': datetime.now(timezone.utc).isoformat()
                }
            
            # Count indexed posts
            indexed_count = db.session.execute(
                text("SELECT COUNT(*) FROM post_search_fts")
            ).scalar()
            
            # Count published posts
            published_count = db.session.query(Post).filter(
                Post.status == 'published'
            ).count()
            
            # Test search functionality
            test_query_time = None
            try:
                test_start = time.time()
                db.session.execute(
                    text("SELECT COUNT(*) FROM post_search_fts WHERE post_search_fts MATCH 'test'")
                ).scalar()
                test_query_time = time.time() - test_start
            except Exception as search_error:
                return {
                    'status': 'critical',
                    'message': f"Search query failed: {str(search_error)}",
                    'details': {
                        'indexed_count': indexed_count,
                        'published_count': published_count,
                        'search_error': str(search_error)
                    },
                    'last_checked': datetime.now(timezone.utc).isoformat()
                }
            
            check_time = time.time() - start_time
            
            # Calculate index coverage
            coverage = (indexed_count / published_count * 100) if published_count > 0 else 0
            
            # Determine status
            if coverage < 90:
                status = 'warning'
                message = f"Search index coverage is low ({coverage:.1f}%)"
            elif test_query_time and test_query_time > 0.5:
                status = 'warning'
                message = f"Search queries are slow ({test_query_time:.2f}s)"
            else:
                status = 'healthy'
                message = "Search index is functioning properly"
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'indexed_count': indexed_count,
                    'published_count': published_count,
                    'coverage_percentage': round(coverage, 1),
                    'test_query_time': round(test_query_time, 3) if test_query_time else None,
                    'check_time': round(check_time, 3)
                },
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Search index health check failed: {str(e)}")
            
            return {
                'status': 'critical',
                'message': f"Search index check failed: {str(e)}",
                'details': {'error': str(e)},
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
    
    def check_email_service_health(self) -> Dict[str, Any]:
        """
        Check email service connectivity and configuration.
        
        Returns:
            Dictionary with email service health status
        """
        try:
            if not self.sendgrid_api_key:
                return {
                    'status': 'warning',
                    'message': "SendGrid API key not configured",
                    'details': {'configured': False},
                    'last_checked': datetime.now(timezone.utc).isoformat()
                }
            
            start_time = time.time()
            
            # Test SendGrid API connectivity
            sg = sendgrid.SendGridAPIClient(api_key=self.sendgrid_api_key)
            
            try:
                # Get API key info (this doesn't send an email)
                response = sg.client.api_keys.get()
                api_test_time = time.time() - start_time
                
                if response.status_code == 200:
                    status = 'healthy'
                    message = "Email service is connected and ready"
                else:
                    status = 'warning'
                    message = f"Email service responded with status {response.status_code}"
                
            except HTTPError as e:
                if e.status_code == 401:
                    status = 'critical'
                    message = "Email service authentication failed"
                else:
                    status = 'warning'
                    message = f"Email service error: {e.reason}"
                api_test_time = time.time() - start_time
            
            # Get recent email statistics
            recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            recent_subscriptions = db.session.query(NewsletterSubscription).filter(
                NewsletterSubscription.subscribed_at >= recent_cutoff
            ).count()
            
            confirmed_subscriptions = db.session.query(NewsletterSubscription).filter(
                NewsletterSubscription.is_confirmed == True,
                NewsletterSubscription.is_active == True
            ).count()
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'configured': True,
                    'api_test_time': round(api_test_time, 3),
                    'recent_subscriptions': recent_subscriptions,
                    'active_subscriptions': confirmed_subscriptions
                },
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Email service health check failed: {str(e)}")
            
            return {
                'status': 'critical',
                'message': f"Email service check failed: {str(e)}",
                'details': {'error': str(e)},
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
    
    def check_feed_generation_health(self) -> Dict[str, Any]:
        """
        Check RSS/Atom feed generation capability.
        
        Returns:
            Dictionary with feed generation health status
        """
        try:
            start_time = time.time()
            
            # Test feed generation
            from feed_generator import FeedGenerator
            
            feed_gen = FeedGenerator(self.app)
            
            # Test RSS generation
            rss_start = time.time()
            try:
                rss_content = feed_gen.generate_rss_feed()  # Generate feed
                rss_time = time.time() - rss_start
                rss_success = len(rss_content) > 0
                rss_error_msg = None
            except Exception as rss_error:
                rss_time = time.time() - rss_start
                rss_success = False
                rss_error_msg = str(rss_error)
            
            # Test Atom generation
            atom_start = time.time()
            try:
                atom_content = feed_gen.generate_atom_feed()  # Generate feed
                atom_time = time.time() - atom_start
                atom_success = len(atom_content) > 0
                atom_error_msg = None
            except Exception as atom_error:
                atom_time = time.time() - atom_start
                atom_success = False
                atom_error_msg = str(atom_error)
            
            total_time = time.time() - start_time
            
            # Determine status
            if not rss_success and not atom_success:
                status = 'critical'
                message = "Both RSS and Atom feed generation failed"
            elif not rss_success or not atom_success:
                status = 'warning'
                message = "One feed type failed to generate"
            elif total_time > 5.0:
                status = 'warning'
                message = f"Feed generation is slow ({total_time:.2f}s)"
            else:
                status = 'healthy'
                message = "Feed generation is working properly"
            
            details = {
                'rss_success': rss_success,
                'atom_success': atom_success,
                'rss_generation_time': round(rss_time, 3),
                'atom_generation_time': round(atom_time, 3),
                'total_time': round(total_time, 3)
            }
            
            # Add error messages if any
            if not rss_success:
                details['rss_error'] = rss_error_msg
            if not atom_success:
                details['atom_error'] = atom_error_msg
            
            return {
                'status': status,
                'message': message,
                'details': details,
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Feed generation health check failed: {str(e)}")
            
            return {
                'status': 'critical',
                'message': f"Feed generation check failed: {str(e)}",
                'details': {'error': str(e)},
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
    
    def check_file_system_health(self) -> Dict[str, Any]:
        """
        Check file system health and disk space.
        
        Returns:
            Dictionary with file system health status
        """
        try:
            import shutil
            
            # Check upload directory
            upload_dir = os.path.join(self.app.static_folder, 'uploads')
            upload_dir_exists = os.path.exists(upload_dir)
            upload_dir_writable = os.access(upload_dir, os.W_OK) if upload_dir_exists else False
            
            # Check disk space
            total, used, free = shutil.disk_usage(self.app.root_path)
            
            # Convert to GB
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            usage_percent = (used / total) * 100
            
            # Check database file size
            db_path = self.app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
            db_size_mb = 0
            if db_path and os.path.exists(db_path):
                db_size_mb = os.path.getsize(db_path) / (1024**2)
            
            # Count uploaded files
            uploaded_files = 0
            if upload_dir_exists:
                try:
                    uploaded_files = len([f for f in os.listdir(upload_dir) 
                                        if os.path.isfile(os.path.join(upload_dir, f))])
                except:
                    uploaded_files = 0
            
            # Determine status
            if not upload_dir_exists or not upload_dir_writable:
                status = 'critical'
                message = "Upload directory is not accessible"
            elif usage_percent > 90:
                status = 'critical'
                message = f"Disk space critically low ({usage_percent:.1f}% used)"
            elif usage_percent > 80:
                status = 'warning'
                message = f"Disk space running low ({usage_percent:.1f}% used)"
            else:
                status = 'healthy'
                message = "File system is healthy"
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'upload_dir_exists': upload_dir_exists,
                    'upload_dir_writable': upload_dir_writable,
                    'disk_total_gb': round(total_gb, 2),
                    'disk_used_gb': round(used_gb, 2),
                    'disk_free_gb': round(free_gb, 2),
                    'disk_usage_percent': round(usage_percent, 1),
                    'database_size_mb': round(db_size_mb, 2),
                    'uploaded_files_count': uploaded_files
                },
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"File system health check failed: {str(e)}")
            
            return {
                'status': 'critical',
                'message': f"File system check failed: {str(e)}",
                'details': {'error': str(e)},
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
    
    def check_performance_metrics(self) -> Dict[str, Any]:
        """
        Check system performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        try:
            import psutil
            
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024**2)
            memory_total_mb = memory.total / (1024**2)
            
            # Get process info
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / (1024**2)
            process_cpu_percent = process.cpu_percent()
            
            # Check recent search performance
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_searches = db.session.query(SearchQuery).filter(
                SearchQuery.created_at >= recent_cutoff
            ).count()
            
            # Determine status
            if memory_percent > 90 or cpu_percent > 90:
                status = 'critical'
                message = "System resources critically high"
            elif memory_percent > 80 or cpu_percent > 80:
                status = 'warning'
                message = "System resources running high"
            elif process_memory_mb > self.high_memory_threshold:
                status = 'warning'
                message = f"Application memory usage high ({process_memory_mb:.1f}MB)"
            else:
                status = 'healthy'
                message = "System performance is good"
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'cpu_percent': round(cpu_percent, 1),
                    'memory_percent': round(memory_percent, 1),
                    'memory_used_mb': round(memory_used_mb, 1),
                    'memory_total_mb': round(memory_total_mb, 1),
                    'process_memory_mb': round(process_memory_mb, 1),
                    'process_cpu_percent': round(process_cpu_percent, 1),
                    'recent_searches': recent_searches
                },
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
            
        except ImportError:
            # psutil not available, provide basic metrics
            return {
                'status': 'warning',
                'message': "Performance monitoring not available (psutil not installed)",
                'details': {'psutil_available': False},
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Performance metrics check failed: {str(e)}")
            
            return {
                'status': 'warning',
                'message': f"Performance check failed: {str(e)}",
                'details': {'error': str(e)},
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
    
    def _get_connection_pool_info(self) -> Dict[str, Any]:
        """Get database connection pool information."""
        try:
            # For SQLite, connection pooling is minimal
            # This is a placeholder for more complex database setups
            return {
                'pool_size': 1,  # SQLite typically uses single connection
                'checked_out': 0,
                'overflow': 0,
                'checked_in': 1
            }
        except:
            return {}
    
    def _generate_health_summary(self, health_checks: Dict[str, Dict]) -> Dict[str, int]:
        """Generate summary statistics from health checks."""
        summary = {'healthy': 0, 'warning': 0, 'critical': 0, 'total': 0}
        
        for check in health_checks.values():
            status = check.get('status', 'unknown')
            if status in summary:
                summary[status] += 1
            summary['total'] += 1
        
        return summary
    
    def get_health_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get health check history for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of historical health check results
        """
        # This would typically be stored in a separate health_checks table
        # For now, return empty list as this is a basic implementation
        return []
    
    def run_health_check_endpoint(self) -> Tuple[Dict[str, Any], int]:
        """
        Run health check suitable for HTTP endpoint.
        
        Returns:
            Tuple of (health_data, http_status_code)
        """
        health_data = self.get_overall_health()
        
        # Determine HTTP status code based on overall health
        status_code_map = {
            'healthy': 200,
            'warning': 200,  # Still operational
            'critical': 503,  # Service unavailable
            'unknown': 500   # Internal server error
        }
        
        status_code = status_code_map.get(health_data['overall_status'], 500)
        
        return health_data, status_code