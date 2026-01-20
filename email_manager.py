"""
Email Manager Component

This module handles all email sending functionality including newsletters,
notifications, and transactional emails.
"""

from flask import current_app, render_template_string
from flask_mail import Message
from datetime import datetime, timezone
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class EmailManager:
    """Manages email sending for newsletters and notifications"""
    
    def __init__(self, mail, db):
        """
        Initialize email manager.
        
        Args:
            mail: Flask-Mail instance
            db: SQLAlchemy database instance
        """
        self.mail = mail
        self.db = db
    
    def send_email(self, subject: str, recipients: List[str], 
                   body: str = None, html: str = None) -> bool:
        """
        Send an email to one or more recipients.
        
        Args:
            subject: Email subject line
            recipients: List of recipient email addresses
            body: Plain text email body (optional)
            html: HTML email body (optional)
        
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            msg = Message(
                subject=subject,
                recipients=recipients,
                body=body,
                html=html,
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@example.com')
            )
            
            self.mail.send(msg)
            logger.info(f"Email sent successfully to {len(recipients)} recipient(s)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def send_newsletter(self, subscribers: List, subject: str, content: str) -> dict:
        """
        Send newsletter to multiple subscribers.
        
        Args:
            subscribers: List of NewsletterSubscription objects
            subject: Newsletter subject line
            content: HTML content of newsletter
        
        Returns:
            Dictionary with success/failure counts
        """
        results = {
            'sent': 0,
            'failed': 0,
            'errors': []
        }
        
        for subscriber in subscribers:
            if not subscriber.is_active or not subscriber.is_confirmed:
                continue
            
            # Personalize content with unsubscribe link
            personalized_content = self._add_unsubscribe_link(
                content, 
                subscriber.unsubscribe_token
            )
            
            success = self.send_email(
                subject=subject,
                recipients=[subscriber.email],
                html=personalized_content
            )
            
            if success:
                results['sent'] += 1
                subscriber.last_email_sent = datetime.now(timezone.utc)
            else:
                results['failed'] += 1
                results['errors'].append(subscriber.email)
        
        # Commit database changes
        try:
            self.db.session.commit()
        except Exception as e:
            logger.error(f"Failed to update subscriber records: {str(e)}")
        
        return results
    
    def send_newsletter_confirmation(self, email: str, token: str) -> bool:
        """
        Send newsletter subscription confirmation email.
        
        Args:
            email: Subscriber email address
            token: Confirmation token
        
        Returns:
            True if sent successfully, False otherwise
        """
        site_url = current_app.config.get('SITE_URL', 'http://localhost:5000')
        confirmation_url = f"{site_url}/newsletter/confirm/{token}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #9b5e2b;">Confirm Your Newsletter Subscription</h2>
            
            <p>Thank you for subscribing to our newsletter!</p>
            
            <p>Please confirm your subscription by clicking the button below:</p>
            
            <p style="text-align: center; margin: 30px 0;">
                <a href="{confirmation_url}" 
                   style="background-color: #9b5e2b; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Confirm Subscription
                </a>
            </p>
            
            <p style="color: #666; font-size: 14px;">
                If the button doesn't work, copy and paste this link into your browser:<br>
                <a href="{confirmation_url}">{confirmation_url}</a>
            </p>
            
            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                If you didn't subscribe to this newsletter, you can safely ignore this email.
            </p>
        </body>
        </html>
        """
        
        return self.send_email(
            subject="Confirm Your Newsletter Subscription",
            recipients=[email],
            html=html_content
        )
    
    def send_welcome_email(self, email: str) -> bool:
        """
        Send welcome email to new confirmed subscriber.
        
        Args:
            email: Subscriber email address
        
        Returns:
            True if sent successfully, False otherwise
        """
        html_content = """
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #9b5e2b;">Welcome to Our Newsletter!</h2>
            
            <p>Thank you for confirming your subscription!</p>
            
            <p>You'll now receive our latest posts and updates directly in your inbox.</p>
            
            <p>We're excited to have you as part of our community!</p>
            
            <p style="margin-top: 30px;">
                Best regards,<br>
                The Blog Team
            </p>
        </body>
        </html>
        """
        
        return self.send_email(
            subject="Welcome to Our Newsletter!",
            recipients=[email],
            html=html_content
        )
    
    def send_password_reset(self, email: str, reset_token: str) -> bool:
        """
        Send password reset email.
        
        Args:
            email: User email address
            reset_token: Password reset token
        
        Returns:
            True if sent successfully, False otherwise
        """
        site_url = current_app.config.get('SITE_URL', 'http://localhost:5000')
        reset_url = f"{site_url}/reset-password/{reset_token}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #9b5e2b;">Password Reset Request</h2>
            
            <p>We received a request to reset your password.</p>
            
            <p>Click the button below to reset your password:</p>
            
            <p style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" 
                   style="background-color: #9b5e2b; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Reset Password
                </a>
            </p>
            
            <p style="color: #666; font-size: 14px;">
                This link will expire in 1 hour for security reasons.
            </p>
            
            <p style="color: #666; font-size: 14px;">
                If the button doesn't work, copy and paste this link into your browser:<br>
                <a href="{reset_url}">{reset_url}</a>
            </p>
            
            <p style="color: #dc3545; font-size: 14px; margin-top: 30px;">
                If you didn't request a password reset, please ignore this email or contact support if you're concerned.
            </p>
        </body>
        </html>
        """
        
        return self.send_email(
            subject="Password Reset Request",
            recipients=[email],
            html=html_content
        )
    
    def _add_unsubscribe_link(self, content: str, token: str) -> str:
        """
        Add unsubscribe link to email content.
        
        Args:
            content: Original HTML content
            token: Unsubscribe token
        
        Returns:
            Content with unsubscribe link appended
        """
        site_url = current_app.config.get('SITE_URL', 'http://localhost:5000')
        unsubscribe_url = f"{site_url}/newsletter/unsubscribe/{token}"
        
        unsubscribe_footer = f"""
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; 
                    color: #666; font-size: 12px; text-align: center;">
            <p>
                You're receiving this email because you subscribed to our newsletter.
            </p>
            <p>
                <a href="{unsubscribe_url}" style="color: #666;">Unsubscribe</a> from future emails
            </p>
        </div>
        """
        
        # Insert before closing body tag if present, otherwise append
        if '</body>' in content:
            return content.replace('</body>', f'{unsubscribe_footer}</body>')
        else:
            return content + unsubscribe_footer
    
    def test_email_configuration(self) -> dict:
        """
        Test email configuration by sending a test email.
        
        Returns:
            Dictionary with test results
        """
        test_email = current_app.config.get('MAIL_USERNAME', 'test@example.com')
        
        result = {
            'success': False,
            'message': '',
            'config': {
                'server': current_app.config.get('MAIL_SERVER'),
                'port': current_app.config.get('MAIL_PORT'),
                'use_tls': current_app.config.get('MAIL_USE_TLS'),
                'sender': current_app.config.get('MAIL_DEFAULT_SENDER')
            }
        }
        
        try:
            success = self.send_email(
                subject="Email Configuration Test",
                recipients=[test_email],
                html="<p>This is a test email. Your email configuration is working correctly!</p>"
            )
            
            if success:
                result['success'] = True
                result['message'] = f"Test email sent successfully to {test_email}"
            else:
                result['message'] = "Failed to send test email"
                
        except Exception as e:
            result['message'] = f"Error: {str(e)}"
        
        return result
