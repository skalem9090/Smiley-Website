"""
Comment Manager for comment submission, moderation, and spam detection.

This module provides comprehensive comment management including submission handling,
moderation workflow, spam detection, and administrative actions for the blog system.
"""

import os
import re
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from flask import request, url_for, render_template_string
from models import db, Comment, Post, User
from resend_email_service import ResendEmailService
import logging


class CommentManager:
    """Manager class for comment submission, moderation, and spam detection."""
    
    def __init__(self, app=None):
        """Initialize CommentManager with optional Flask app."""
        self.app = app
        self.email_service = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app configuration."""
        self.app = app
        
        # Resend email service configuration for notifications
        api_key = app.config.get('RESEND_API_KEY') or os.environ.get('RESEND_API_KEY')
        if api_key:
            self.email_service = ResendEmailService(
                api_key=api_key,
                from_email=app.config.get('RESEND_FROM_EMAIL', 'onboarding@resend.dev'),
                from_name=app.config.get('RESEND_FROM_NAME', 'Smileys Blog')
            )
        else:
            app.logger.warning("Resend API key not configured. Comment notification emails will be disabled.")
        
        # Email configuration
        self.admin_email = app.config.get('ADMIN_EMAIL', 'admin@example.com')
        self.base_url = app.config.get('BASE_URL', 'http://localhost:5000')
        
        # Comment configuration
        self.require_moderation = app.config.get('COMMENT_REQUIRE_MODERATION', True)
        self.max_comment_length = app.config.get('COMMENT_MAX_LENGTH', 2000)
        self.enable_threading = app.config.get('COMMENT_ENABLE_THREADING', True)
        
        # Spam detection configuration
        self.spam_keywords = app.config.get('COMMENT_SPAM_KEYWORDS', [
            'viagra', 'casino', 'lottery', 'winner', 'congratulations',
            'click here', 'free money', 'make money fast', 'work from home'
        ])
        self.max_links_per_comment = app.config.get('COMMENT_MAX_LINKS', 2)
    
    def submit_comment(self, post_id: int, author_name: str, author_email: str, 
                      content: str, parent_id: int = None, ip_address: str = None, 
                      user_agent: str = None) -> Tuple[bool, str, Optional[Comment]]:
        """
        Submit a new comment for moderation.
        
        Args:
            post_id: ID of the post being commented on
            author_name: Name of the comment author
            author_email: Email of the comment author
            content: Comment content
            parent_id: Optional parent comment ID for threading
            ip_address: Optional IP address of commenter
            user_agent: Optional user agent string
            
        Returns:
            Tuple of (success, message, comment_object)
        """
        try:
            # Validate inputs
            validation_result = self._validate_comment_data(
                post_id, author_name, author_email, content, parent_id
            )
            if not validation_result[0]:
                return validation_result
            
            # Check for spam
            is_spam = self.check_spam({
                'author_name': author_name,
                'author_email': author_email,
                'content': content,
                'ip_address': ip_address,
                'user_agent': user_agent
            })
            
            # Create comment
            comment = Comment(
                post_id=post_id,
                author_name=author_name.strip(),
                author_email=author_email.strip().lower(),
                content=content.strip(),
                parent_id=parent_id if self.enable_threading else None,
                is_spam=is_spam,
                is_approved=not self.require_moderation and not is_spam,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.now(timezone.utc)
            )
            
            db.session.add(comment)
            db.session.commit()
            
            # Send notification email to administrators
            if not is_spam:
                self._send_notification_email(comment)
            
            if is_spam:
                return True, "Comment submitted but flagged as spam and requires review.", comment
            elif self.require_moderation:
                return True, "Comment submitted successfully and is awaiting moderation.", comment
            else:
                return True, "Comment posted successfully.", comment
                
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error submitting comment: {str(e)}")
            return False, "An error occurred while submitting your comment.", None
    
    def approve_comment(self, comment_id: int, moderator_id: int) -> Tuple[bool, str]:
        """
        Approve a comment and make it public.
        
        Args:
            comment_id: ID of the comment to approve
            moderator_id: ID of the moderating user
            
        Returns:
            Tuple of (success, message)
        """
        try:
            comment = Comment.query.get(comment_id)
            if not comment:
                return False, "Comment not found"
            
            if comment.is_approved:
                return True, "Comment is already approved"
            
            comment.is_approved = True
            comment.is_spam = False
            comment.approved_at = datetime.now(timezone.utc)
            comment.approved_by = moderator_id
            
            db.session.commit()
            
            return True, "Comment approved successfully"
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error approving comment {comment_id}: {str(e)}")
            return False, "An error occurred while approving the comment"
    
    def reject_comment(self, comment_id: int, moderator_id: int, mark_as_spam: bool = True) -> Tuple[bool, str]:
        """
        Reject a comment and optionally mark as spam.
        
        Args:
            comment_id: ID of the comment to reject
            moderator_id: ID of the moderating user
            mark_as_spam: Whether to mark the comment as spam
            
        Returns:
            Tuple of (success, message)
        """
        try:
            comment = Comment.query.get(comment_id)
            if not comment:
                return False, "Comment not found"
            
            comment.is_approved = False
            comment.is_spam = mark_as_spam
            comment.approved_by = moderator_id
            comment.approved_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            action = "rejected and marked as spam" if mark_as_spam else "rejected"
            return True, f"Comment {action} successfully"
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error rejecting comment {comment_id}: {str(e)}")
            return False, "An error occurred while rejecting the comment"
    
    def delete_comment(self, comment_id: int, moderator_id: int) -> Tuple[bool, str]:
        """
        Delete a comment permanently.
        
        Args:
            comment_id: ID of the comment to delete
            moderator_id: ID of the moderating user
            
        Returns:
            Tuple of (success, message)
        """
        try:
            comment = Comment.query.get(comment_id)
            if not comment:
                return False, "Comment not found"
            
            # If comment has replies, we might want to handle this differently
            if comment.replies:
                return False, "Cannot delete comment with replies. Consider rejecting instead."
            
            db.session.delete(comment)
            db.session.commit()
            
            return True, "Comment deleted successfully"
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error deleting comment {comment_id}: {str(e)}")
            return False, "An error occurred while deleting the comment"
    
    def get_pending_comments(self, limit: int = 50) -> List[Comment]:
        """
        Get comments awaiting moderation.
        
        Args:
            limit: Maximum number of comments to return
            
        Returns:
            List of pending comments
        """
        try:
            return Comment.query.filter_by(
                is_approved=False,
                is_spam=False
            ).order_by(Comment.created_at.desc()).limit(limit).all()
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting pending comments: {str(e)}")
            return []
    
    def get_approved_comments(self, post_id: int, include_replies: bool = True) -> List[Comment]:
        """
        Get approved comments for a post.
        
        Args:
            post_id: ID of the post
            include_replies: Whether to include threaded replies
            
        Returns:
            List of approved comments
        """
        try:
            query = Comment.query.filter_by(
                post_id=post_id,
                is_approved=True
            )
            
            if not include_replies or not self.enable_threading:
                query = query.filter_by(parent_id=None)
            
            return query.order_by(Comment.created_at.asc()).all()
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting approved comments for post {post_id}: {str(e)}")
            return []
    
    def get_comment_tree(self, post_id: int) -> List[Dict]:
        """
        Get comments organized in a tree structure for threading display.
        
        Args:
            post_id: ID of the post
            
        Returns:
            List of comment dictionaries with nested replies
        """
        try:
            if not self.enable_threading:
                comments = self.get_approved_comments(post_id, include_replies=False)
                return [self._comment_to_dict(comment) for comment in comments]
            
            # Get all approved comments for the post
            all_comments = Comment.query.filter_by(
                post_id=post_id,
                is_approved=True
            ).order_by(Comment.created_at.asc()).all()
            
            # Build comment tree
            comment_dict = {comment.id: self._comment_to_dict(comment) for comment in all_comments}
            root_comments = []
            
            for comment in all_comments:
                comment_data = comment_dict[comment.id]
                if comment.parent_id and comment.parent_id in comment_dict:
                    parent = comment_dict[comment.parent_id]
                    if 'replies' not in parent:
                        parent['replies'] = []
                    parent['replies'].append(comment_data)
                else:
                    root_comments.append(comment_data)
            
            return root_comments
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error building comment tree for post {post_id}: {str(e)}")
            return []
    
    def check_spam(self, comment_data: Dict[str, Any]) -> bool:
        """
        Basic spam detection using simple heuristics.
        
        Args:
            comment_data: Dictionary containing comment information
            
        Returns:
            True if comment is likely spam, False otherwise
        """
        try:
            content = comment_data.get('content', '').lower()
            author_name = comment_data.get('author_name', '').lower()
            author_email = comment_data.get('author_email', '').lower()
            
            # Check for spam keywords
            for keyword in self.spam_keywords:
                if keyword.lower() in content or keyword.lower() in author_name:
                    return True
            
            # Check for excessive links
            link_count = len(re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content))
            if link_count > self.max_links_per_comment:
                return True
            
            # Check for suspicious email patterns
            if re.search(r'[0-9]{5,}@', author_email):  # Email with many consecutive numbers
                return True
            
            # Check for excessive capitalization
            if len(content) > 20 and sum(1 for c in content if c.isupper()) / len(content) > 0.7:
                return True
            
            # Check for repeated characters
            if re.search(r'(.)\1{4,}', content):  # Same character repeated 5+ times
                return True
            
            return False
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error in spam detection: {str(e)}")
            return False  # Default to not spam if detection fails
    
    def bulk_approve_comments(self, comment_ids: List[int], moderator_id: int) -> Tuple[int, int]:
        """
        Approve multiple comments in bulk.
        
        Args:
            comment_ids: List of comment IDs to approve
            moderator_id: ID of the moderating user
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        successful = 0
        failed = 0
        
        for comment_id in comment_ids:
            success, _ = self.approve_comment(comment_id, moderator_id)
            if success:
                successful += 1
            else:
                failed += 1
        
        return successful, failed
    
    def bulk_reject_comments(self, comment_ids: List[int], moderator_id: int, mark_as_spam: bool = True) -> Tuple[int, int]:
        """
        Reject multiple comments in bulk.
        
        Args:
            comment_ids: List of comment IDs to reject
            moderator_id: ID of the moderating user
            mark_as_spam: Whether to mark comments as spam
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        successful = 0
        failed = 0
        
        for comment_id in comment_ids:
            success, _ = self.reject_comment(comment_id, moderator_id, mark_as_spam)
            if success:
                successful += 1
            else:
                failed += 1
        
        return successful, failed
    
    def get_comment_stats(self) -> Dict[str, Any]:
        """
        Get comment statistics for dashboard display.
        
        Returns:
            Dictionary with comment statistics
        """
        try:
            total_comments = Comment.query.count()
            approved_comments = Comment.query.filter_by(is_approved=True).count()
            pending_comments = Comment.query.filter_by(is_approved=False, is_spam=False).count()
            spam_comments = Comment.query.filter_by(is_spam=True).count()
            
            # Recent comments (last 30 days)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            recent_comments = Comment.query.filter(
                Comment.created_at >= recent_cutoff
            ).count()
            
            # Comments by post (top 5)
            from sqlalchemy import func
            top_posts = db.session.query(
                Post.title,
                func.count(Comment.id).label('comment_count')
            ).join(Comment).filter(
                Comment.is_approved == True
            ).group_by(Post.id, Post.title).order_by(
                func.count(Comment.id).desc()
            ).limit(5).all()
            
            return {
                'total_comments': total_comments,
                'approved_comments': approved_comments,
                'pending_comments': pending_comments,
                'spam_comments': spam_comments,
                'recent_comments': recent_comments,
                'approval_rate': (approved_comments / total_comments * 100) if total_comments > 0 else 0,
                'top_commented_posts': [{'title': title, 'count': count} for title, count in top_posts]
            }
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting comment stats: {str(e)}")
            return {
                'total_comments': 0,
                'approved_comments': 0,
                'pending_comments': 0,
                'spam_comments': 0,
                'recent_comments': 0,
                'approval_rate': 0,
                'top_commented_posts': []
            }
    
    def _validate_comment_data(self, post_id: int, author_name: str, author_email: str, 
                              content: str, parent_id: int = None) -> Tuple[bool, str, None]:
        """Validate comment submission data."""
        # Check if post exists
        post = Post.query.get(post_id)
        if not post:
            return False, "Post not found", None
        
        if post.status != 'published':
            return False, "Comments are not allowed on unpublished posts", None
        
        # Validate required fields
        if not author_name or not author_name.strip():
            return False, "Name is required", None
        
        if not author_email or not author_email.strip():
            return False, "Email is required", None
        
        if not content or not content.strip():
            return False, "Comment content is required", None
        
        # Validate email format
        if not self._is_valid_email(author_email):
            return False, "Invalid email address format", None
        
        # Validate content length
        if len(content.strip()) > self.max_comment_length:
            return False, f"Comment is too long (maximum {self.max_comment_length} characters)", None
        
        # Validate parent comment if threading is enabled
        if parent_id and self.enable_threading:
            parent_comment = Comment.query.get(parent_id)
            if not parent_comment:
                return False, "Parent comment not found", None
            if parent_comment.post_id != post_id:
                return False, "Parent comment belongs to a different post", None
            if not parent_comment.is_approved:
                return False, "Cannot reply to unapproved comment", None
        
        return True, "Valid", None
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _comment_to_dict(self, comment: Comment) -> Dict[str, Any]:
        """Convert comment object to dictionary for JSON serialization."""
        return {
            'id': comment.id,
            'author_name': comment.author_name,
            'content': comment.content,
            'created_at': comment.created_at.isoformat(),
            'parent_id': comment.parent_id,
            'replies': []  # Will be populated by get_comment_tree if needed
        }
    
    def _send_notification_email(self, comment: Comment) -> Tuple[bool, str]:
        """Send notification email to administrators about new comment."""
        if not self.email_service or not self.admin_email:
            return False, "Email service not configured"
        
        try:
            post = comment.post
            comment_url = f"{self.base_url}{url_for('post_view', post_id=post.id)}#comment-{comment.id}"
            
            comment_data = {
                'post_title': post.title,
                'post_url': comment_url,
                'author_name': comment.author_name,
                'author_email': comment.author_email,
                'content': comment.content
            }
            
            return self.email_service.send_comment_notification(
                admin_email=self.admin_email,
                comment_data=comment_data
            )
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error sending comment notification: {str(e)}")
            return False, str(e)