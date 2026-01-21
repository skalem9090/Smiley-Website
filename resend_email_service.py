"""
Resend Email Service

This module provides email sending functionality using Resend API.
Resend offers 3,000 emails/month free with 100 emails/day limit.
"""

import resend
import logging
from typing import List, Dict, Optional, Tuple
from flask import current_app

logger = logging.getLogger(__name__)


class ResendEmailService:
    """Email service using Resend API"""
    
    def __init__(self, api_key: str = None, from_email: str = None, from_name: str = None):
        """
        Initialize Resend email service.
        
        Args:
            api_key: Resend API key (optional, will use env var if not provided)
            from_email: Default sender email address
            from_name: Default sender name
        """
        self.api_key = api_key or current_app.config.get('RESEND_API_KEY')
        self.from_email = from_email or current_app.config.get('RESEND_FROM_EMAIL', 'noreply@example.com')
        self.from_name = from_name or current_app.config.get('RESEND_FROM_NAME', 'Smileys Blog')
        
        if self.api_key:
            resend.api_key = self.api_key
        else:
            logger.warning("Resend API key not configured")
    
    def send_email(self, 
                   to: str | List[str],
                   subject: str,
                   html: str = None,
                   text: str = None,
                   reply_to: str = None) -> Tuple[bool, str]:
        """
        Send an email using Resend.
        
        Args:
            to: Recipient email address or list of addresses
            subject: Email subject
            html: HTML email content
            text: Plain text email content
            reply_to: Reply-to email address
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.api_key:
            return False, "Resend API key not configured"
        
        try:
            # Ensure to is a list
            if isinstance(to, str):
                to = [to]
            
            # Build email params
            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": to,
                "subject": subject,
            }
            
            if html:
                params["html"] = html
            if text:
                params["text"] = text
            if reply_to:
                params["reply_to"] = reply_to
            
            # Send email
            response = resend.Emails.send(params)
            
            logger.info(f"Email sent successfully to {len(to)} recipient(s). ID: {response.get('id')}")
            return True, f"Email sent successfully. ID: {response.get('id')}"
            
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def send_confirmation_email(self, email: str, token: str) -> Tuple[bool, str]:
        """
        Send newsletter subscription confirmation email.
        
        Args:
            email: Subscriber email address
            token: Confirmation token
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        site_url = current_app.config.get('SITE_URL', 'http://localhost:5000')
        confirmation_url = f"{site_url}/newsletter/confirm/{token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #faf7f0; border: 2px solid #e8e3d8; border-radius: 8px; padding: 30px;">
                <h2 style="color: #8b4513; margin-top: 0;">Confirm Your Newsletter Subscription</h2>
                
                <p>Thank you for subscribing to Smileys Blog!</p>
                
                <p>Please confirm your subscription by clicking the button below:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{confirmation_url}" 
                       style="background-color: #8b4513; color: white; padding: 14px 32px; 
                              text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 600;">
                        Confirm Subscription
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px; border-top: 1px solid #e8e3d8; padding-top: 20px; margin-top: 30px;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{confirmation_url}" style="color: #8b4513; word-break: break-all;">{confirmation_url}</a>
                </p>
                
                <p style="color: #999; font-size: 12px; margin-top: 20px;">
                    If you didn't subscribe to this newsletter, you can safely ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Confirm Your Newsletter Subscription
        
        Thank you for subscribing to Smileys Blog!
        
        Please confirm your subscription by visiting this link:
        {confirmation_url}
        
        If you didn't subscribe to this newsletter, you can safely ignore this email.
        """
        
        return self.send_email(
            to=email,
            subject="Confirm Your Newsletter Subscription - Smileys Blog",
            html=html_content,
            text=text_content
        )
    
    def send_welcome_email(self, email: str) -> Tuple[bool, str]:
        """
        Send welcome email to new confirmed subscriber.
        
        Args:
            email: Subscriber email address
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        site_url = current_app.config.get('SITE_URL', 'http://localhost:5000')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #faf7f0; border: 2px solid #e8e3d8; border-radius: 8px; padding: 30px;">
                <h2 style="color: #8b4513; margin-top: 0;">Welcome to Smileys Blog! 😊</h2>
                
                <p>Thank you for confirming your subscription!</p>
                
                <p>You'll now receive our latest posts and updates about:</p>
                <ul style="line-height: 1.8;">
                    <li>💰 <strong>Wealth:</strong> Financial wisdom and prosperity</li>
                    <li>💚 <strong>Health:</strong> Physical and mental wellness</li>
                    <li>😊 <strong>Happiness:</strong> Life satisfaction and personal growth</li>
                </ul>
                
                <p>We're excited to have you as part of our community!</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{site_url}" 
                       style="background-color: #8b4513; color: white; padding: 14px 32px; 
                              text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 600;">
                        Visit Our Blog
                    </a>
                </div>
                
                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>The Smileys Blog Team</strong>
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to Smileys Blog!
        
        Thank you for confirming your subscription!
        
        You'll now receive our latest posts and updates about:
        - Wealth: Financial wisdom and prosperity
        - Health: Physical and mental wellness
        - Happiness: Life satisfaction and personal growth
        
        We're excited to have you as part of our community!
        
        Visit our blog: {site_url}
        
        Best regards,
        The Smileys Blog Team
        """
        
        return self.send_email(
            to=email,
            subject="Welcome to Smileys Blog! 😊",
            html=html_content,
            text=text_content
        )
    
    def send_digest_email(self, email: str, subject: str, html_content: str, 
                         text_content: str = None, unsubscribe_url: str = None) -> Tuple[bool, str]:
        """
        Send newsletter digest email.
        
        Args:
            email: Subscriber email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text content (optional)
            unsubscribe_url: Unsubscribe URL to add to footer
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Add unsubscribe footer if URL provided
        if unsubscribe_url:
            html_content = self._add_unsubscribe_footer(html_content, unsubscribe_url)
            if text_content:
                text_content += f"\n\n---\nUnsubscribe: {unsubscribe_url}"
        
        return self.send_email(
            to=email,
            subject=subject,
            html=html_content,
            text=text_content
        )
    
    def send_comment_notification(self, admin_email: str, comment_data: Dict) -> Tuple[bool, str]:
        """
        Send notification email to admin about new comment.
        
        Args:
            admin_email: Administrator email address
            comment_data: Dictionary with comment information
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        site_url = current_app.config.get('SITE_URL', 'http://localhost:5000')
        post_url = comment_data.get('post_url', '')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #faf7f0; border: 2px solid #e8e3d8; border-radius: 8px; padding: 30px;">
                <h2 style="color: #8b4513; margin-top: 0;">New Comment on Your Blog</h2>
                
                <p><strong>Post:</strong> {comment_data.get('post_title', 'Unknown')}</p>
                <p><strong>Author:</strong> {comment_data.get('author_name', 'Anonymous')}</p>
                <p><strong>Email:</strong> {comment_data.get('author_email', 'N/A')}</p>
                
                <div style="background: white; border-left: 4px solid #8b4513; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0;">{comment_data.get('content', '')}</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{post_url}" 
                       style="background-color: #8b4513; color: white; padding: 12px 28px; 
                              text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 600;">
                        View Comment
                    </a>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(
            to=admin_email,
            subject=f"New Comment: {comment_data.get('post_title', 'Your Post')}",
            html=html_content
        )
    
    def _add_unsubscribe_footer(self, html_content: str, unsubscribe_url: str) -> str:
        """
        Add unsubscribe footer to HTML email.
        
        Args:
            html_content: Original HTML content
            unsubscribe_url: Unsubscribe URL
        
        Returns:
            HTML content with unsubscribe footer
        """
        footer = f"""
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e8e3d8; 
                    color: #999; font-size: 12px; text-align: center;">
            <p>You're receiving this email because you subscribed to Smileys Blog newsletter.</p>
            <p>
                <a href="{unsubscribe_url}" style="color: #8b4513; text-decoration: underline;">
                    Unsubscribe from future emails
                </a>
            </p>
        </div>
        """
        
        # Insert before closing body tag if present, otherwise append
        if '</body>' in html_content:
            return html_content.replace('</body>', f'{footer}</body>')
        else:
            return html_content + footer
    
    def test_configuration(self) -> Dict:
        """
        Test Resend configuration by sending a test email.
        
        Returns:
            Dictionary with test results
        """
        result = {
            'success': False,
            'message': '',
            'config': {
                'api_key_set': bool(self.api_key),
                'from_email': self.from_email,
                'from_name': self.from_name
            }
        }
        
        if not self.api_key:
            result['message'] = "Resend API key not configured"
            return result
        
        try:
            # Send test email to the from_email address
            success, message = self.send_email(
                to=self.from_email,
                subject="Resend Configuration Test - Smileys Blog",
                html="<p>This is a test email. Your Resend configuration is working correctly!</p>",
                text="This is a test email. Your Resend configuration is working correctly!"
            )
            
            result['success'] = success
            result['message'] = message
                
        except Exception as e:
            result['message'] = f"Error: {str(e)}"
        
        return result
