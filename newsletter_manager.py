"""
Newsletter Manager for email subscription and digest functionality.

This module provides comprehensive newsletter management including subscription handling,
email confirmation, digest generation, and Resend integration for email delivery.
"""

import os
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from flask import url_for, render_template_string
from models import db, NewsletterSubscription, Post, User
from resend_email_service import ResendEmailService
import logging


class NewsletterManager:
    """Manager class for newsletter subscription and email functionality."""
    
    def __init__(self, app=None):
        """Initialize NewsletterManager with optional Flask app."""
        self.app = app
        self.email_service = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app configuration."""
        self.app = app
        
        # Resend email service configuration
        api_key = app.config.get('RESEND_API_KEY') or os.environ.get('RESEND_API_KEY')
        if api_key:
            self.email_service = ResendEmailService(
                api_key=api_key,
                from_email=app.config.get('RESEND_FROM_EMAIL', 'onboarding@resend.dev'),
                from_name=app.config.get('RESEND_FROM_NAME', 'Smileys Blog')
            )
        else:
            app.logger.warning("Resend API key not configured. Email functionality will be disabled.")
        
        # Newsletter configuration
        self.from_email = app.config.get('NEWSLETTER_FROM_EMAIL', 'noreply@example.com')
        self.from_name = app.config.get('NEWSLETTER_FROM_NAME', 'Smileys Blog')
        self.reply_to = app.config.get('NEWSLETTER_REPLY_TO', self.from_email)
        self.base_url = app.config.get('BASE_URL', 'http://localhost:5000')
        
        # Email templates configuration
        self.confirmation_subject = app.config.get('NEWSLETTER_CONFIRMATION_SUBJECT', 'Confirm your subscription')
        self.digest_subject_template = app.config.get('NEWSLETTER_DIGEST_SUBJECT', 'Weekly Digest - {date}')
        
        # Digest configuration
        self.digest_post_limit = app.config.get('NEWSLETTER_DIGEST_POST_LIMIT', 5)
        self.digest_excerpt_length = app.config.get('NEWSLETTER_DIGEST_EXCERPT_LENGTH', 200)
    
    def subscribe_email(self, email: str, frequency: str = 'weekly', 
                       ip_address: str = None, user_agent: str = None) -> Tuple[bool, str, Optional[NewsletterSubscription]]:
        """
        Subscribe an email address to the newsletter.
        
        Args:
            email: Email address to subscribe
            frequency: Subscription frequency ('weekly', 'bi-weekly', 'monthly')
            ip_address: Optional IP address of subscriber
            user_agent: Optional user agent string
            
        Returns:
            Tuple of (success, message, subscription_object)
        """
        try:
            # Validate email format
            if not self._is_valid_email(email):
                return False, "Invalid email address format", None
            
            # Check if already subscribed
            existing = NewsletterSubscription.query.filter_by(email=email).first()
            if existing:
                if existing.is_confirmed:
                    return False, "Email address is already subscribed", existing
                else:
                    # Resend confirmation for unconfirmed subscription
                    success, message = self._send_confirmation_email(existing)
                    if success:
                        return True, "Confirmation email resent", existing
                    else:
                        return False, f"Failed to send confirmation: {message}", existing
            
            # Create new subscription
            subscription = NewsletterSubscription(
                email=email,
                frequency=frequency,
                subscribed_at=datetime.now(timezone.utc)
            )
            
            db.session.add(subscription)
            db.session.commit()
            
            # Send confirmation email
            success, message = self._send_confirmation_email(subscription)
            if success:
                return True, "Subscription created. Please check your email to confirm.", subscription
            else:
                # Rollback subscription if email failed
                db.session.delete(subscription)
                db.session.commit()
                return False, f"Failed to send confirmation email: {message}", None
                
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error subscribing email {email}: {str(e)}")
            return False, "An error occurred during subscription", None
    
    def confirm_subscription(self, token: str) -> Tuple[bool, str, Optional[NewsletterSubscription]]:
        """
        Confirm a newsletter subscription using the confirmation token.
        
        Args:
            token: Confirmation token
            
        Returns:
            Tuple of (success, message, subscription_object)
        """
        try:
            subscription = NewsletterSubscription.query.filter_by(confirmation_token=token).first()
            
            if not subscription:
                return False, "Invalid confirmation token", None
            
            if subscription.is_confirmed:
                return True, "Subscription already confirmed", subscription
            
            # Check if token is expired (24 hours)
            # Make sure both datetimes are timezone-aware for comparison
            subscribed_at = subscription.subscribed_at
            if subscribed_at.tzinfo is None:
                # If stored datetime is naive, assume UTC
                subscribed_at = subscribed_at.replace(tzinfo=timezone.utc)
            
            expiry_time = datetime.now(timezone.utc) - timedelta(hours=24)
            if subscribed_at < expiry_time:
                return False, "Confirmation token has expired", subscription
            
            # Confirm subscription
            subscription.is_confirmed = True
            subscription.confirmed_at = datetime.now(timezone.utc)
            subscription.confirmation_token = None  # Clear token for security
            
            db.session.commit()
            
            # Send welcome email (don't fail if email fails)
            try:
                self._send_welcome_email(subscription)
            except Exception as email_error:
                if self.app:
                    self.app.logger.warning(f"Failed to send welcome email: {str(email_error)}")
                # Continue anyway - subscription is confirmed
            
            return True, "Subscription confirmed successfully", subscription
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error confirming subscription with token {token}: {str(e)}")
            return False, "An error occurred during confirmation", None
    
    def unsubscribe_email(self, token: str) -> Tuple[bool, str, Optional[NewsletterSubscription]]:
        """
        Unsubscribe an email using the unsubscribe token.
        
        Args:
            token: Unsubscribe token
            
        Returns:
            Tuple of (success, message, subscription_object)
        """
        try:
            subscription = NewsletterSubscription.query.filter_by(unsubscribe_token=token).first()
            
            if not subscription:
                return False, "Invalid unsubscribe token", None
            
            if not subscription.is_confirmed:
                # Delete unconfirmed subscription
                db.session.delete(subscription)
                db.session.commit()
                return True, "Unsubscribed successfully", None
            
            # Mark as unsubscribed
            subscription.is_active = False
            subscription.unsubscribed_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            return True, "Unsubscribed successfully", subscription
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error unsubscribing with token {token}: {str(e)}")
            return False, "An error occurred during unsubscription", None
    
    def update_subscription_frequency(self, email: str, frequency: str) -> Tuple[bool, str]:
        """
        Update subscription frequency for an email.
        
        Args:
            email: Email address
            frequency: New frequency ('weekly', 'bi-weekly', 'monthly')
            
        Returns:
            Tuple of (success, message)
        """
        try:
            subscription = NewsletterSubscription.query.filter_by(
                email=email, 
                is_confirmed=True, 
                is_active=True
            ).first()
            
            if not subscription:
                return False, "Subscription not found or not confirmed"
            
            if frequency not in ['weekly', 'bi-weekly', 'monthly']:
                return False, "Invalid frequency. Must be 'weekly', 'bi-weekly', or 'monthly'"
            
            subscription.frequency = frequency
            db.session.commit()
            
            return True, f"Subscription frequency updated to {frequency}"
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error updating frequency for {email}: {str(e)}")
            return False, "An error occurred while updating frequency"
    
    def generate_digest(self, frequency: str = 'weekly') -> Tuple[bool, str, Optional[Dict]]:
        """
        Generate newsletter digest content for a specific frequency.
        
        Args:
            frequency: Digest frequency ('weekly', 'bi-weekly', 'monthly')
            
        Returns:
            Tuple of (success, message, digest_data)
        """
        try:
            # Calculate date range based on frequency
            now = datetime.now(timezone.utc)
            if frequency == 'weekly':
                start_date = now - timedelta(days=7)
                period_name = "This Week"
            elif frequency == 'bi-weekly':
                start_date = now - timedelta(days=14)
                period_name = "Past Two Weeks"
            elif frequency == 'monthly':
                start_date = now - timedelta(days=30)
                period_name = "This Month"
            else:
                return False, "Invalid frequency", None
            
            # Get published posts from the period
            posts = Post.query.filter(
                Post.status == 'published',
                Post.published_at >= start_date,
                Post.published_at <= now
            ).order_by(Post.published_at.desc()).limit(self.digest_post_limit).all()
            
            if not posts:
                return False, f"No posts found for {frequency} digest", None
            
            # Generate digest data
            digest_data = {
                'frequency': frequency,
                'period_name': period_name,
                'start_date': start_date,
                'end_date': now,
                'posts': [],
                'total_posts': len(posts)
            }
            
            # Process posts for digest
            for post in posts:
                post_data = {
                    'id': post.id,
                    'title': post.title,
                    'excerpt': self._generate_excerpt(post.content),
                    'category': post.category,
                    'published_at': post.published_at,
                    'url': f"{self.base_url}{url_for('post_view', post_id=post.id)}",
                    'tags': post.tags.split(',') if post.tags else []
                }
                digest_data['posts'].append(post_data)
            
            return True, f"Digest generated with {len(posts)} posts", digest_data
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error generating {frequency} digest: {str(e)}")
            return False, "An error occurred while generating digest", None
    
    def send_digest_to_subscribers(self, frequency: str = 'weekly') -> Tuple[bool, str, Dict]:
        """
        Send digest email to all confirmed subscribers of a specific frequency.
        
        Args:
            frequency: Digest frequency
            
        Returns:
            Tuple of (success, message, stats)
        """
        try:
            # Generate digest content
            success, message, digest_data = self.generate_digest(frequency)
            if not success:
                return False, message, {'sent': 0, 'failed': 0}
            
            # Get subscribers for this frequency
            subscribers = NewsletterSubscription.query.filter_by(
                frequency=frequency,
                is_confirmed=True,
                is_active=True
            ).all()
            
            if not subscribers:
                return False, f"No confirmed subscribers for {frequency} digest", {'sent': 0, 'failed': 0}
            
            # Send emails
            sent_count = 0
            failed_count = 0
            
            for subscriber in subscribers:
                success, _ = self._send_digest_email(subscriber, digest_data)
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
            
            stats = {
                'sent': sent_count,
                'failed': failed_count,
                'total_subscribers': len(subscribers),
                'digest_posts': digest_data['total_posts']
            }
            
            return True, f"Digest sent to {sent_count} subscribers", stats
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error sending {frequency} digest: {str(e)}")
            return False, "An error occurred while sending digest", {'sent': 0, 'failed': 0}
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """
        Get newsletter subscription statistics.
        
        Returns:
            Dictionary with subscription statistics
        """
        try:
            total_subscriptions = NewsletterSubscription.query.count()
            confirmed_subscriptions = NewsletterSubscription.query.filter_by(is_confirmed=True, is_active=True).count()
            unconfirmed_subscriptions = NewsletterSubscription.query.filter_by(is_confirmed=False).count()
            unsubscribed_count = NewsletterSubscription.query.filter_by(is_active=False).count()
            
            # Frequency breakdown
            frequency_stats = {}
            for freq in ['weekly', 'bi-weekly', 'monthly']:
                count = NewsletterSubscription.query.filter_by(
                    frequency=freq, 
                    is_confirmed=True, 
                    is_active=True
                ).count()
                frequency_stats[freq] = count
            
            # Recent subscriptions (last 30 days)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            recent_subscriptions = NewsletterSubscription.query.filter(
                NewsletterSubscription.subscribed_at >= recent_cutoff,
                NewsletterSubscription.is_confirmed == True
            ).count()
            
            return {
                'total_subscriptions': total_subscriptions,
                'confirmed_subscriptions': confirmed_subscriptions,
                'unconfirmed_subscriptions': unconfirmed_subscriptions,
                'unsubscribed_count': unsubscribed_count,
                'frequency_breakdown': frequency_stats,
                'recent_subscriptions': recent_subscriptions,
                'confirmation_rate': (confirmed_subscriptions / total_subscriptions * 100) if total_subscriptions > 0 else 0
            }
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting subscription stats: {str(e)}")
            return {
                'total_subscriptions': 0,
                'confirmed_subscriptions': 0,
                'unconfirmed_subscriptions': 0,
                'unsubscribed_count': 0,
                'frequency_breakdown': {'weekly': 0, 'bi-weekly': 0, 'monthly': 0},
                'recent_subscriptions': 0,
                'confirmation_rate': 0
            }
    
    def _generate_token(self) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(32)
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _generate_excerpt(self, content: str) -> str:
        """Generate excerpt from post content."""
        if not content:
            return ""
        
        # Remove HTML tags
        import re
        clean_content = re.sub(r'<[^>]+>', ' ', content)
        
        # Normalize whitespace
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()
        
        # Truncate to desired length
        if len(clean_content) <= self.digest_excerpt_length:
            return clean_content
        
        # Find last complete word within limit
        truncated = clean_content[:self.digest_excerpt_length]
        last_space = truncated.rfind(' ')
        if last_space > 0:
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    def _send_confirmation_email(self, subscription: NewsletterSubscription) -> Tuple[bool, str]:
        """Send confirmation email to subscriber."""
        if not self.email_service:
            return False, "Email service not configured"
        
        try:
            return self.email_service.send_confirmation_email(
                email=subscription.email,
                token=subscription.confirmation_token
            )
        except Exception as e:
            error_msg = f"Error sending confirmation: {str(e)}"
            if self.app:
                self.app.logger.error(f"Error sending confirmation to {subscription.email}: {error_msg}")
            return False, error_msg
    
    def _send_welcome_email(self, subscription: NewsletterSubscription) -> Tuple[bool, str]:
        """Send welcome email to confirmed subscriber."""
        if not self.email_service:
            return False, "Email service not configured"
        
        try:
            return self.email_service.send_welcome_email(email=subscription.email)
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error sending welcome email to {subscription.email}: {str(e)}")
            return False, str(e)
    
    def _send_digest_email(self, subscription: NewsletterSubscription, digest_data: Dict) -> Tuple[bool, str]:
        """Send digest email to subscriber."""
        if not self.email_service:
            return False, "Email service not configured"
        
        try:
            unsubscribe_url = f"{self.base_url}{url_for('unsubscribe_newsletter', token=subscription.unsubscribe_token)}"
            
            # Format date for subject
            date_str = digest_data['end_date'].strftime('%B %d, %Y')
            subject = self.digest_subject_template.format(date=date_str)
            
            # Generate HTML and text content
            html_content = self._generate_digest_html(digest_data, unsubscribe_url)
            text_content = self._generate_digest_text(digest_data, unsubscribe_url)
            
            return self.email_service.send_digest_email(
                email=subscription.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                unsubscribe_url=unsubscribe_url
            )
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error sending digest to {subscription.email}: {str(e)}")
            return False, str(e)
    
    def _generate_digest_html(self, digest_data: Dict, unsubscribe_url: str) -> str:
        """Generate HTML content for digest email."""
        posts_html = ""
        for post in digest_data['posts']:
            tags_html = ""
            if post['tags']:
                tags_html = " • ".join(post['tags'])
                tags_html = f"<p style='font-size: 12px; color: #666; margin: 5px 0;'>{tags_html}</p>"
            
            category_html = ""
            if post['category']:
                category_html = f"<span style='background: #f0f0f0; padding: 2px 8px; border-radius: 4px; font-size: 12px; color: #666;'>{post['category'].title()}</span>"
            
            posts_html += f"""
            <div style="border-bottom: 1px solid #eee; padding: 20px 0;">
                <h3 style="margin: 0 0 10px 0;">
                    <a href="{post['url']}" style="color: #9b5e2b; text-decoration: none;">
                        {post['title']}
                    </a>
                </h3>
                <div style="margin-bottom: 10px;">
                    {category_html}
                    <span style="color: #666; font-size: 12px; margin-left: 10px;">
                        {post['published_at'].strftime('%B %d, %Y') if post['published_at'] else 'No date'}
                    </span>
                </div>
                <p style="color: #333; line-height: 1.6; margin: 10px 0;">
                    {post['excerpt']}
                </p>
                {tags_html}
                <a href="{post['url']}" style="color: #9b5e2b; text-decoration: none; font-weight: 600;">
                    Read More →
                </a>
            </div>
            """
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <header style="text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #9b5e2b;">
                    <h1 style="color: #9b5e2b; margin: 0;">{self.from_name}</h1>
                    <p style="color: #666; margin: 10px 0 0 0;">{digest_data['period_name']} Digest</p>
                </header>
                
                <div style="margin-bottom: 30px;">
                    <p>Here are the latest posts from {digest_data['period_name'].lower()}:</p>
                </div>
                
                {posts_html}
                
                <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
                    <p style="color: #666; font-size: 12px;">
                        You're receiving this because you subscribed to our newsletter.<br>
                        <a href="{unsubscribe_url}" style="color: #9b5e2b;">Unsubscribe</a>
                    </p>
                </footer>
            </div>
        </body>
        </html>
        """
    
    def _generate_digest_text(self, digest_data: Dict, unsubscribe_url: str) -> str:
        """Generate plain text content for digest email."""
        posts_text = ""
        for post in digest_data['posts']:
            tags_text = ""
            if post['tags']:
                tags_text = f"\nTags: {', '.join(post['tags'])}"
            
            category_text = ""
            if post['category']:
                category_text = f" [{post['category'].title()}]"
            
            posts_text += f"""
{post['title']}{category_text}
{post['published_at'].strftime('%B %d, %Y') if post['published_at'] else 'No date'}

{post['excerpt']}
{tags_text}

Read more: {post['url']}

---
"""
        
        return f"""
{self.from_name} - {digest_data['period_name']} Digest

Here are the latest posts from {digest_data['period_name'].lower()}:

{posts_text}

You're receiving this because you subscribed to our newsletter.
Unsubscribe: {unsubscribe_url}
        """