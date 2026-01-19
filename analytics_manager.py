"""
Analytics Manager for comprehensive analytics and reporting.

This module provides analytics collection, processing, and reporting for all
system components including content performance, user engagement, search analytics,
newsletter metrics, and growth tracking.
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict
from models import db, Post, Comment, NewsletterSubscription, SearchQuery, User
from sqlalchemy import func, text, and_, or_
import json


class AnalyticsManager:
    """Manager class for comprehensive analytics and reporting."""
    
    def __init__(self, app=None):
        """Initialize AnalyticsManager with optional Flask app."""
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app configuration."""
        self.app = app
        
        # Analytics configuration
        self.default_period_days = app.config.get('ANALYTICS_DEFAULT_PERIOD', 30)
        self.popular_content_limit = app.config.get('ANALYTICS_POPULAR_LIMIT', 10)
        self.growth_tracking_periods = app.config.get('ANALYTICS_GROWTH_PERIODS', [7, 30, 90])
    
    def get_comprehensive_analytics(self, days: int = None) -> Dict[str, Any]:
        """
        Get comprehensive analytics across all system components.
        
        Args:
            days: Number of days to analyze (defaults to configured period)
            
        Returns:
            Dictionary with comprehensive analytics data
        """
        days = days or self.default_period_days
        
        try:
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            analytics = {
                'period': {
                    'days': days,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'content': self.get_content_analytics(start_date, end_date),
                'engagement': self.get_engagement_analytics(start_date, end_date),
                'search': self.get_search_analytics(start_date, end_date),
                'newsletter': self.get_newsletter_analytics(start_date, end_date),
                'growth': self.get_growth_metrics(days),
                'performance': self.get_performance_analytics(start_date, end_date),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
            return analytics
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting comprehensive analytics: {str(e)}")
            
            return {
                'error': str(e),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
    
    def get_content_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Get content creation and performance analytics.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            Dictionary with content analytics
        """
        try:
            # Calculate days for rate calculations
            days = (end_date - start_date).days
            
            # Posts created in period
            posts_created = db.session.query(Post).filter(
                Post.created_at >= start_date,
                Post.created_at <= end_date
            ).count()
            
            # Posts published in period
            posts_published = db.session.query(Post).filter(
                Post.published_at >= start_date,
                Post.published_at <= end_date,
                Post.status == 'published'
            ).count()
            
            # Total published posts
            total_published = db.session.query(Post).filter(
                Post.status == 'published'
            ).count()
            
            # Posts by category in period
            category_stats = db.session.query(
                Post.category,
                func.count(Post.id).label('count')
            ).filter(
                Post.published_at >= start_date,
                Post.published_at <= end_date,
                Post.status == 'published'
            ).group_by(Post.category).all()
            
            # Posts by status
            status_stats = db.session.query(
                Post.status,
                func.count(Post.id).label('count')
            ).group_by(Post.status).all()
            
            # Most commented posts in period
            most_commented = db.session.query(
                Post.title,
                Post.id,
                func.count(Comment.id).label('comment_count')
            ).join(Comment).filter(
                Comment.created_at >= start_date,
                Comment.created_at <= end_date,
                Comment.is_approved == True
            ).group_by(Post.id, Post.title).order_by(
                func.count(Comment.id).desc()
            ).limit(self.popular_content_limit).all()
            
            # Average post length
            avg_content_length = db.session.query(
                func.avg(func.length(Post.content))
            ).filter(
                Post.published_at >= start_date,
                Post.published_at <= end_date,
                Post.status == 'published'
            ).scalar() or 0
            
            # Posts with summaries vs auto-generated
            posts_with_manual_summary = db.session.query(Post).filter(
                Post.published_at >= start_date,
                Post.published_at <= end_date,
                Post.status == 'published',
                Post.summary.isnot(None),
                Post.summary != ''
            ).count()
            
            return {
                'posts_created': posts_created,
                'posts_published': posts_published,
                'total_published': total_published,
                'publishing_rate': round((posts_published / days) if days > 0 else 0, 2),
                'category_breakdown': [
                    {'category': cat or 'Uncategorized', 'count': count}
                    for cat, count in category_stats
                ],
                'status_breakdown': [
                    {'status': status, 'count': count}
                    for status, count in status_stats
                ],
                'most_commented_posts': [
                    {
                        'title': title,
                        'post_id': post_id,
                        'comment_count': comment_count
                    }
                    for title, post_id, comment_count in most_commented
                ],
                'avg_content_length': round(avg_content_length, 0),
                'posts_with_manual_summary': posts_with_manual_summary,
                'summary_usage_rate': round(
                    (posts_with_manual_summary / posts_published * 100) if posts_published > 0 else 0, 1
                )
            }
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting content analytics: {str(e)}")
            return {'error': str(e)}
    
    def get_engagement_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Get user engagement analytics.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            Dictionary with engagement analytics
        """
        try:
            # Calculate days for rate calculations
            days = (end_date - start_date).days
            
            # Comments in period
            comments_submitted = db.session.query(Comment).filter(
                Comment.created_at >= start_date,
                Comment.created_at <= end_date
            ).count()
            
            comments_approved = db.session.query(Comment).filter(
                Comment.created_at >= start_date,
                Comment.created_at <= end_date,
                Comment.is_approved == True
            ).count()
            
            comments_spam = db.session.query(Comment).filter(
                Comment.created_at >= start_date,
                Comment.created_at <= end_date,
                Comment.is_spam == True
            ).count()
            
            # Total comments
            total_comments = db.session.query(Comment).filter(
                Comment.is_approved == True
            ).count()
            
            # Unique commenters in period
            unique_commenters = db.session.query(
                func.count(func.distinct(Comment.author_email))
            ).filter(
                Comment.created_at >= start_date,
                Comment.created_at <= end_date,
                Comment.is_approved == True
            ).scalar() or 0
            
            # Comments per day
            daily_comments = db.session.query(
                func.date(Comment.created_at).label('date'),
                func.count(Comment.id).label('count')
            ).filter(
                Comment.created_at >= start_date,
                Comment.created_at <= end_date,
                Comment.is_approved == True
            ).group_by(func.date(Comment.created_at)).all()
            
            # Most active commenters
            top_commenters = db.session.query(
                Comment.author_name,
                Comment.author_email,
                func.count(Comment.id).label('comment_count')
            ).filter(
                Comment.created_at >= start_date,
                Comment.created_at <= end_date,
                Comment.is_approved == True
            ).group_by(
                Comment.author_name, Comment.author_email
            ).order_by(
                func.count(Comment.id).desc()
            ).limit(10).all()
            
            # Average comments per post
            posts_with_comments = db.session.query(
                func.count(func.distinct(Comment.post_id))
            ).filter(
                Comment.created_at >= start_date,
                Comment.created_at <= end_date,
                Comment.is_approved == True
            ).scalar() or 0
            
            avg_comments_per_post = round(
                (comments_approved / posts_with_comments) if posts_with_comments > 0 else 0, 2
            )
            
            # Approval rate
            approval_rate = round(
                (comments_approved / comments_submitted * 100) if comments_submitted > 0 else 0, 1
            )
            
            # Spam rate
            spam_rate = round(
                (comments_spam / comments_submitted * 100) if comments_submitted > 0 else 0, 1
            )
            
            return {
                'comments_submitted': comments_submitted,
                'comments_approved': comments_approved,
                'comments_spam': comments_spam,
                'total_comments': total_comments,
                'unique_commenters': unique_commenters,
                'approval_rate': approval_rate,
                'spam_rate': spam_rate,
                'avg_comments_per_post': avg_comments_per_post,
                'comments_per_day': round(comments_approved / days if days > 0 else 0, 2),
                'daily_comment_trend': [
                    {'date': str(date), 'count': count}
                    for date, count in daily_comments
                ],
                'top_commenters': [
                    {
                        'name': name,
                        'email': email[:3] + '***@' + email.split('@')[1] if '@' in email else email,  # Privacy
                        'comment_count': count
                    }
                    for name, email, count in top_commenters
                ]
            }
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting engagement analytics: {str(e)}")
            return {'error': str(e)}
    
    def get_search_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Get search analytics and popular queries.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            Dictionary with search analytics
        """
        try:
            # Calculate days for rate calculations
            days = (end_date - start_date).days
            
            # Total searches in period
            total_searches = db.session.query(SearchQuery).filter(
                SearchQuery.created_at >= start_date,
                SearchQuery.created_at <= end_date
            ).count()
            
            # Unique search terms
            unique_queries = db.session.query(
                func.count(func.distinct(SearchQuery.query_text))
            ).filter(
                SearchQuery.created_at >= start_date,
                SearchQuery.created_at <= end_date
            ).scalar() or 0
            
            # Popular search terms
            popular_searches = db.session.query(
                SearchQuery.query_text,
                func.count(SearchQuery.id).label('search_count'),
                func.avg(SearchQuery.results_count).label('avg_results')
            ).filter(
                SearchQuery.created_at >= start_date,
                SearchQuery.created_at <= end_date
            ).group_by(
                SearchQuery.query_text
            ).order_by(
                func.count(SearchQuery.id).desc()
            ).limit(self.popular_content_limit).all()
            
            # Searches with no results
            no_result_searches = db.session.query(SearchQuery).filter(
                SearchQuery.created_at >= start_date,
                SearchQuery.created_at <= end_date,
                SearchQuery.results_count == 0
            ).count()
            
            # Average results per search
            avg_results = db.session.query(
                func.avg(SearchQuery.results_count)
            ).filter(
                SearchQuery.created_at >= start_date,
                SearchQuery.created_at <= end_date
            ).scalar() or 0
            
            # Daily search trend
            daily_searches = db.session.query(
                func.date(SearchQuery.created_at).label('date'),
                func.count(SearchQuery.id).label('count')
            ).filter(
                SearchQuery.created_at >= start_date,
                SearchQuery.created_at <= end_date
            ).group_by(func.date(SearchQuery.created_at)).all()
            
            # Search success rate (searches with results)
            success_rate = round(
                ((total_searches - no_result_searches) / total_searches * 100) if total_searches > 0 else 0, 1
            )
            
            return {
                'total_searches': total_searches,
                'unique_queries': unique_queries,
                'searches_per_day': round(total_searches / days if days > 0 else 0, 2),
                'avg_results_per_search': round(avg_results, 1),
                'no_result_searches': no_result_searches,
                'success_rate': success_rate,
                'popular_searches': [
                    {
                        'query': query,
                        'search_count': count,
                        'avg_results': round(avg_results, 1)
                    }
                    for query, count, avg_results in popular_searches
                ],
                'daily_search_trend': [
                    {'date': str(date), 'count': count}
                    for date, count in daily_searches
                ]
            }
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting search analytics: {str(e)}")
            return {'error': str(e)}
    
    def get_newsletter_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Get newsletter subscription and engagement analytics.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            Dictionary with newsletter analytics
        """
        try:
            # Calculate days for rate calculations
            days = (end_date - start_date).days
            
            # Subscriptions in period
            new_subscriptions = db.session.query(NewsletterSubscription).filter(
                NewsletterSubscription.subscribed_at >= start_date,
                NewsletterSubscription.subscribed_at <= end_date
            ).count()
            
            # Confirmations in period
            confirmations = db.session.query(NewsletterSubscription).filter(
                NewsletterSubscription.confirmed_at >= start_date,
                NewsletterSubscription.confirmed_at <= end_date,
                NewsletterSubscription.is_confirmed == True
            ).count()
            
            # Unsubscribes in period (assuming we track this)
            # For now, we'll count inactive subscriptions
            unsubscribes = db.session.query(NewsletterSubscription).filter(
                NewsletterSubscription.subscribed_at >= start_date,
                NewsletterSubscription.subscribed_at <= end_date,
                NewsletterSubscription.is_active == False
            ).count()
            
            # Total active subscriptions
            total_active = db.session.query(NewsletterSubscription).filter(
                NewsletterSubscription.is_confirmed == True,
                NewsletterSubscription.is_active == True
            ).count()
            
            # Subscription frequency breakdown
            frequency_breakdown = db.session.query(
                NewsletterSubscription.frequency,
                func.count(NewsletterSubscription.id).label('count')
            ).filter(
                NewsletterSubscription.is_confirmed == True,
                NewsletterSubscription.is_active == True
            ).group_by(NewsletterSubscription.frequency).all()
            
            # Daily subscription trend
            daily_subscriptions = db.session.query(
                func.date(NewsletterSubscription.subscribed_at).label('date'),
                func.count(NewsletterSubscription.id).label('count')
            ).filter(
                NewsletterSubscription.subscribed_at >= start_date,
                NewsletterSubscription.subscribed_at <= end_date
            ).group_by(func.date(NewsletterSubscription.subscribed_at)).all()
            
            # Confirmation rate
            confirmation_rate = round(
                (confirmations / new_subscriptions * 100) if new_subscriptions > 0 else 0, 1
            )
            
            # Growth rate
            net_growth = new_subscriptions - unsubscribes
            growth_rate = round(
                (net_growth / total_active * 100) if total_active > 0 else 0, 1
            )
            
            # Average time to confirm (for confirmed subscriptions in period)
            confirmed_subs = db.session.query(NewsletterSubscription).filter(
                NewsletterSubscription.confirmed_at >= start_date,
                NewsletterSubscription.confirmed_at <= end_date,
                NewsletterSubscription.is_confirmed == True,
                NewsletterSubscription.subscribed_at.isnot(None),
                NewsletterSubscription.confirmed_at.isnot(None)
            ).all()
            
            if confirmed_subs:
                confirmation_times = [
                    (sub.confirmed_at - sub.subscribed_at).total_seconds() / 3600  # hours
                    for sub in confirmed_subs
                    if sub.confirmed_at and sub.subscribed_at
                ]
                avg_confirmation_time = sum(confirmation_times) / len(confirmation_times) if confirmation_times else 0
            else:
                avg_confirmation_time = 0
            
            return {
                'new_subscriptions': new_subscriptions,
                'confirmations': confirmations,
                'unsubscribes': unsubscribes,
                'net_growth': net_growth,
                'total_active': total_active,
                'confirmation_rate': confirmation_rate,
                'growth_rate': growth_rate,
                'subscriptions_per_day': round(new_subscriptions / days if days > 0 else 0, 2),
                'avg_confirmation_time_hours': round(avg_confirmation_time, 1),
                'frequency_breakdown': [
                    {'frequency': freq, 'count': count}
                    for freq, count in frequency_breakdown
                ],
                'daily_subscription_trend': [
                    {'date': str(date), 'count': count}
                    for date, count in daily_subscriptions
                ]
            }
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting newsletter analytics: {str(e)}")
            return {'error': str(e)}
    
    def get_growth_metrics(self, days: int) -> Dict[str, Any]:
        """
        Get growth metrics across different time periods.
        
        Args:
            days: Current analysis period
            
        Returns:
            Dictionary with growth metrics
        """
        try:
            growth_metrics = {}
            
            for period in self.growth_tracking_periods:
                if period <= days:  # Only calculate for periods within our analysis range
                    end_date = datetime.now(timezone.utc)
                    start_date = end_date - timedelta(days=period)
                    
                    # Posts growth
                    posts_current = db.session.query(Post).filter(
                        Post.published_at >= start_date,
                        Post.published_at <= end_date,
                        Post.status == 'published'
                    ).count()
                    
                    # Comments growth
                    comments_current = db.session.query(Comment).filter(
                        Comment.created_at >= start_date,
                        Comment.created_at <= end_date,
                        Comment.is_approved == True
                    ).count()
                    
                    # Newsletter growth
                    newsletter_current = db.session.query(NewsletterSubscription).filter(
                        NewsletterSubscription.confirmed_at >= start_date,
                        NewsletterSubscription.confirmed_at <= end_date,
                        NewsletterSubscription.is_confirmed == True
                    ).count()
                    
                    # Search activity growth
                    searches_current = db.session.query(SearchQuery).filter(
                        SearchQuery.created_at >= start_date,
                        SearchQuery.created_at <= end_date
                    ).count()
                    
                    growth_metrics[f'{period}_days'] = {
                        'posts': posts_current,
                        'comments': comments_current,
                        'newsletter_subscribers': newsletter_current,
                        'searches': searches_current,
                        'posts_per_day': round(posts_current / period, 2),
                        'comments_per_day': round(comments_current / period, 2),
                        'subscribers_per_day': round(newsletter_current / period, 2),
                        'searches_per_day': round(searches_current / period, 2)
                    }
            
            return growth_metrics
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting growth metrics: {str(e)}")
            return {'error': str(e)}
    
    def get_performance_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Get system performance analytics.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            Dictionary with performance analytics
        """
        try:
            # Calculate days for rate calculations
            days = (end_date - start_date).days
            
            # Database query performance (simplified)
            # In a real implementation, you'd track query times
            
            # Content creation velocity
            posts_created = db.session.query(Post).filter(
                Post.created_at >= start_date,
                Post.created_at <= end_date
            ).count()
            
            posts_published = db.session.query(Post).filter(
                Post.published_at >= start_date,
                Post.published_at <= end_date,
                Post.status == 'published'
            ).count()
            
            # Publishing efficiency (published vs created)
            publishing_efficiency = round(
                (posts_published / posts_created * 100) if posts_created > 0 else 0, 1
            )
            
            # Comment moderation efficiency
            comments_submitted = db.session.query(Comment).filter(
                Comment.created_at >= start_date,
                Comment.created_at <= end_date
            ).count()
            
            comments_moderated = db.session.query(Comment).filter(
                Comment.created_at >= start_date,
                Comment.created_at <= end_date,
                Comment.approved_at.isnot(None)
            ).count()
            
            moderation_efficiency = round(
                (comments_moderated / comments_submitted * 100) if comments_submitted > 0 else 0, 1
            )
            
            # Search performance
            total_searches = db.session.query(SearchQuery).filter(
                SearchQuery.created_at >= start_date,
                SearchQuery.created_at <= end_date
            ).count()
            
            successful_searches = db.session.query(SearchQuery).filter(
                SearchQuery.created_at >= start_date,
                SearchQuery.created_at <= end_date,
                SearchQuery.results_count > 0
            ).count()
            
            search_success_rate = round(
                (successful_searches / total_searches * 100) if total_searches > 0 else 0, 1
            )
            
            return {
                'content_creation_velocity': round(posts_created / days if days > 0 else 0, 2),
                'publishing_velocity': round(posts_published / days if days > 0 else 0, 2),
                'publishing_efficiency': publishing_efficiency,
                'comment_moderation_efficiency': moderation_efficiency,
                'search_success_rate': search_success_rate,
                'total_system_activity': {
                    'posts_created': posts_created,
                    'posts_published': posts_published,
                    'comments_submitted': comments_submitted,
                    'searches_performed': total_searches
                }
            }
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting performance analytics: {str(e)}")
            return {'error': str(e)}
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get a summary of key metrics for dashboard display.
        
        Returns:
            Dictionary with key dashboard metrics
        """
        try:
            # Get 30-day analytics
            analytics = self.get_comprehensive_analytics(30)
            
            if 'error' in analytics:
                return analytics
            
            # Extract key metrics
            summary = {
                'content': {
                    'total_posts': analytics['content']['total_published'],
                    'recent_posts': analytics['content']['posts_published'],
                    'publishing_rate': analytics['content']['publishing_rate']
                },
                'engagement': {
                    'total_comments': analytics['engagement']['total_comments'],
                    'recent_comments': analytics['engagement']['comments_approved'],
                    'approval_rate': analytics['engagement']['approval_rate']
                },
                'newsletter': {
                    'total_subscribers': analytics['newsletter']['total_active'],
                    'recent_subscribers': analytics['newsletter']['new_subscriptions'],
                    'growth_rate': analytics['newsletter']['growth_rate']
                },
                'search': {
                    'recent_searches': analytics['search']['total_searches'],
                    'success_rate': analytics['search']['success_rate'],
                    'popular_query': analytics['search']['popular_searches'][0]['query'] if analytics['search']['popular_searches'] else 'N/A'
                },
                'performance': {
                    'publishing_efficiency': analytics['performance']['publishing_efficiency'],
                    'search_success_rate': analytics['performance']['search_success_rate']
                }
            }
            
            return summary
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting dashboard summary: {str(e)}")
            return {'error': str(e)}
    
    def export_analytics_report(self, days: int = 30, format: str = 'json') -> str:
        """
        Export comprehensive analytics report.
        
        Args:
            days: Number of days to include in report
            format: Export format ('json' or 'csv')
            
        Returns:
            Formatted analytics report as string
        """
        try:
            analytics = self.get_comprehensive_analytics(days)
            
            if format.lower() == 'json':
                return json.dumps(analytics, indent=2, default=str)
            elif format.lower() == 'csv':
                # For CSV, we'd need to flatten the data structure
                # This is a simplified implementation
                return "CSV export not yet implemented"
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error exporting analytics report: {str(e)}")
            return f"Error exporting report: {str(e)}"