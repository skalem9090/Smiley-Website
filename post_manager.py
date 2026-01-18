"""
Post Management System for Enhanced Content Management

This module provides the PostManager class for handling post operations including:
- Post creation, updating, and status management
- Draft and scheduling functionality
- Summary generation and management
- Post status transitions and validation
"""

import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from models import db, Post, Tag
from tag_manager import TagManager


class PostManager:
    """
    Manages post operations for the blog system including creation, updating,
    status management, scheduling, and draft handling.
    """

    # Valid post statuses
    VALID_STATUSES = {'draft', 'published', 'scheduled'}
    
    # Default summary length
    DEFAULT_SUMMARY_LENGTH = 150
    MAX_SUMMARY_LENGTH = 200

    @staticmethod
    def create_post(
        title: str,
        content: str,
        category: str = None,
        summary: str = None,
        status: str = 'draft',
        scheduled_time: datetime = None,
        tags: List[str] = None,
        allow_past_schedule: bool = False
    ) -> Post:
        """
        Create new post with status and scheduling support.
        
        Args:
            title: Post title
            content: Post content
            category: Post category (optional)
            summary: Manual summary (optional, auto-generated if not provided)
            status: Post status ('draft', 'published', 'scheduled')
            scheduled_time: Scheduled publication time (required if status is 'scheduled')
            tags: List of tag names to associate with the post
            allow_past_schedule: Allow scheduling in the past (for testing purposes)
            
        Returns:
            Created Post object
            
        Raises:
            ValueError: If invalid status or missing scheduled_time for scheduled posts
            
        Requirements: 1.1, 1.3, 1.6
        """
        if not title or not title.strip():
            raise ValueError("Post title cannot be empty")
        
        if not content or not content.strip():
            raise ValueError("Post content cannot be empty")
        
        if status not in PostManager.VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(PostManager.VALID_STATUSES)}")
        
        if status == 'scheduled' and not scheduled_time:
            raise ValueError("Scheduled posts must have a scheduled_time")
        
        if status == 'scheduled' and scheduled_time and not allow_past_schedule:
            # Ensure we can compare datetimes by normalizing to UTC
            if scheduled_time.tzinfo is None:
                # Treat naive datetime as UTC
                scheduled_time_utc = scheduled_time.replace(tzinfo=timezone.utc)
            else:
                scheduled_time_utc = scheduled_time.astimezone(timezone.utc)
            
            if scheduled_time_utc <= datetime.now(timezone.utc):
                raise ValueError("Scheduled time must be in the future")
        
        # Generate summary if not provided
        if not summary:
            summary = PostManager.generate_summary(content)
        else:
            summary = PostManager._truncate_summary(summary)
        
        # Normalize scheduled_time to UTC if provided
        if scheduled_time:
            if scheduled_time.tzinfo is None:
                # Treat naive datetime as UTC
                normalized_scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
            else:
                # Convert to UTC
                normalized_scheduled_time = scheduled_time.astimezone(timezone.utc)
            # Store as naive datetime in UTC (database doesn't store timezone info)
            normalized_scheduled_time = normalized_scheduled_time.replace(tzinfo=None)
        else:
            normalized_scheduled_time = None
        
        # Create the post
        post = Post(
            title=title.strip(),
            content=content.strip(),
            category=category.strip() if category else None,
            summary=summary,
            status=status,
            scheduled_publish_at=normalized_scheduled_time
        )
        
        # Set published_at for immediately published posts
        if status == 'published':
            post.published_at = datetime.now(timezone.utc)
        
        db.session.add(post)
        db.session.commit()
        
        # Associate tags if provided
        if tags:
            TagManager.associate_tags(post.id, tags)
        
        return post

    @staticmethod
    def update_post(post_id: int, **kwargs) -> Optional[Post]:
        """
        Update existing post while preserving relationships and handling status changes.
        
        Args:
            post_id: ID of the post to update
            **kwargs: Fields to update (title, content, category, summary, status, scheduled_time, tags)
            
        Returns:
            Updated Post object or None if not found
            
        Raises:
            ValueError: If invalid status or scheduling parameters
            
        Requirements: 1.1, 1.3, 1.6
        """
        post = db.session.get(Post, post_id)
        if not post:
            return None
        
        # Store original values for comparison
        original_status = post.status
        original_scheduled_time = post.scheduled_publish_at
        
        # Update basic fields
        if 'title' in kwargs:
            if not kwargs['title'] or not kwargs['title'].strip():
                raise ValueError("Post title cannot be empty")
            post.title = kwargs['title'].strip()
        
        if 'content' in kwargs:
            if not kwargs['content'] or not kwargs['content'].strip():
                raise ValueError("Post content cannot be empty")
            post.content = kwargs['content'].strip()
            
            # Regenerate summary if content changed and no new summary provided
            if 'summary' not in kwargs:
                post.summary = PostManager.generate_summary(post.content)
        
        if 'category' in kwargs:
            post.category = kwargs['category'].strip() if kwargs['category'] else None
        
        if 'summary' in kwargs:
            if kwargs['summary']:
                post.summary = PostManager._truncate_summary(kwargs['summary'])
            else:
                post.summary = PostManager.generate_summary(post.content)
        
        # Handle status changes
        if 'status' in kwargs:
            new_status = kwargs['status']
            if new_status not in PostManager.VALID_STATUSES:
                raise ValueError(f"Invalid status '{new_status}'. Must be one of: {', '.join(PostManager.VALID_STATUSES)}")
            
            post.status = new_status
            
            # Handle status-specific logic
            if new_status == 'published' and original_status != 'published':
                post.published_at = datetime.now(timezone.utc)
                post.scheduled_publish_at = None  # Clear scheduled time
            elif new_status == 'draft':
                post.scheduled_publish_at = None  # Clear scheduled time
        
        # Handle scheduled time updates
        if 'scheduled_time' in kwargs:
            scheduled_time = kwargs['scheduled_time']
            
            if post.status == 'scheduled' or (post.status != 'scheduled' and scheduled_time):
                if not scheduled_time:
                    raise ValueError("Scheduled posts must have a scheduled_time")
                
                # Normalize scheduled time for comparison
                if scheduled_time.tzinfo is None:
                    # Treat naive datetime as UTC
                    scheduled_time_utc = scheduled_time.replace(tzinfo=timezone.utc)
                else:
                    scheduled_time_utc = scheduled_time.astimezone(timezone.utc)
                
                if scheduled_time_utc <= datetime.now(timezone.utc):
                    raise ValueError("Scheduled time must be in the future")
                
                # Store as naive datetime in UTC
                post.scheduled_publish_at = scheduled_time_utc.replace(tzinfo=None)
                if post.status != 'scheduled':
                    post.status = 'scheduled'
        
        # Preserve scheduled time during editing unless explicitly changed
        # (Requirement 1.6: Schedule Preservation During Editing)
        if 'scheduled_time' not in kwargs and original_status == 'scheduled':
            # Keep the original scheduled time unless status is being changed away from scheduled
            if post.status == 'scheduled':
                post.scheduled_publish_at = original_scheduled_time
        
        db.session.commit()
        
        # Update tags if provided
        if 'tags' in kwargs:
            TagManager.associate_tags(post.id, kwargs['tags'])
        
        return post

    @staticmethod
    def publish_post(post_id: int) -> Optional[Post]:
        """
        Immediately publish a draft or scheduled post.
        
        Args:
            post_id: ID of the post to publish
            
        Returns:
            Published Post object or None if not found
            
        Requirements: 1.2, 1.5
        """
        post = db.session.get(Post, post_id)
        if not post:
            return None
        
        if post.status == 'published':
            return post  # Already published
        
        post.status = 'published'
        post.published_at = datetime.now(timezone.utc)
        post.scheduled_publish_at = None  # Clear scheduled time
        
        db.session.commit()
        return post

    @staticmethod
    def schedule_post(post_id: int, publish_time: datetime) -> Optional[Post]:
        """
        Schedule post for future publication.
        
        Args:
            post_id: ID of the post to schedule
            publish_time: When to publish the post
            
        Returns:
            Scheduled Post object or None if not found
            
        Raises:
            ValueError: If publish_time is in the past
            
        Requirements: 1.2, 1.6
        """
        # Normalize publish_time for comparison
        if publish_time.tzinfo is None:
            # Treat naive datetime as UTC
            publish_time_utc = publish_time.replace(tzinfo=timezone.utc)
        else:
            publish_time_utc = publish_time.astimezone(timezone.utc)
        
        if publish_time_utc <= datetime.now(timezone.utc):
            raise ValueError("Scheduled time must be in the future")
        
        post = db.session.get(Post, post_id)
        if not post:
            return None
        
        post.status = 'scheduled'
        # Store as naive datetime in UTC
        post.scheduled_publish_at = publish_time_utc.replace(tzinfo=None)
        post.published_at = None  # Clear published time
        
        db.session.commit()
        return post

    @staticmethod
    def generate_summary(content: str, max_length: int = None) -> str:
        """
        Auto-generate post summary from content.
        
        Args:
            content: Post content to generate summary from
            max_length: Maximum length for summary (default: 150 chars)
            
        Returns:
            Generated summary string
            
        Requirements: 2.2, 2.4, 2.5
        """
        if not content:
            return ""
        
        if max_length is None:
            max_length = PostManager.DEFAULT_SUMMARY_LENGTH
        
        # Remove HTML tags for summary generation
        clean_content = re.sub(r'<[^>]+>', '', content)
        
        # Remove extra whitespace and normalize
        clean_content = ' '.join(clean_content.split())
        
        if len(clean_content) <= max_length:
            return clean_content
        
        # Truncate at word boundary
        truncated = clean_content[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:  # If we can find a reasonable word boundary
            truncated = truncated[:last_space]
        
        return truncated + "..."

    @staticmethod
    def _truncate_summary(summary: str) -> str:
        """
        Truncate summary to maximum length with ellipsis.
        
        Args:
            summary: Summary text to truncate
            
        Returns:
            Truncated summary string
            
        Requirements: 2.4
        """
        if not summary:
            return ""
        
        # Preserve line breaks and basic formatting
        summary = summary.strip()
        
        if len(summary) <= PostManager.MAX_SUMMARY_LENGTH:
            return summary
        
        # Truncate and add ellipsis
        truncated = summary[:PostManager.MAX_SUMMARY_LENGTH - 3]
        last_space = truncated.rfind(' ')
        
        if last_space > PostManager.MAX_SUMMARY_LENGTH * 0.8:
            truncated = truncated[:last_space]
        
        return truncated + "..."

    @staticmethod
    def get_posts_by_status(status: str) -> List[Post]:
        """
        Get all posts with a specific status.
        
        Args:
            status: Post status to filter by
            
        Returns:
            List of Post objects with the specified status
            
        Requirements: 1.4, 6.1, 6.2
        """
        if status not in PostManager.VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(PostManager.VALID_STATUSES)}")
        
        return Post.query.filter_by(status=status).order_by(Post.created_at.desc()).all()

    @staticmethod
    def get_scheduled_posts_ready_for_publication() -> List[Post]:
        """
        Get all scheduled posts that are ready for publication.
        
        Returns:
            List of Post objects ready to be published
            
        Requirements: 1.2, 1.5, 7.2
        """
        now = datetime.now(timezone.utc)
        return Post.query.filter(
            Post.status == 'scheduled',
            Post.scheduled_publish_at <= now
        ).all()

    @staticmethod
    def get_post_metadata(post_id: int) -> Optional[Dict[str, Any]]:
        """
        Get post metadata for dashboard display.
        
        Args:
            post_id: ID of the post
            
        Returns:
            Dictionary with post metadata or None if not found
            
        Requirements: 6.2, 6.4
        """
        post = db.session.get(Post, post_id)
        if not post:
            return None
        
        # Count associated tags
        tag_count = len(post.tag_relationships)
        
        # Determine display date
        display_date = post.published_at or post.scheduled_publish_at or post.created_at
        
        return {
            'id': post.id,
            'title': post.title,
            'status': post.status,
            'category': post.category,
            'created_at': post.created_at,
            'published_at': post.published_at,
            'scheduled_publish_at': post.scheduled_publish_at,
            'display_date': display_date,
            'tag_count': tag_count,
            'summary': post.summary,
            'content_length': len(post.content) if post.content else 0
        }

    @staticmethod
    def regenerate_summary(post_id: int, max_length: int = None) -> Optional[str]:
        """
        Regenerate summary for an existing post.
        
        Args:
            post_id: ID of the post to regenerate summary for
            max_length: Maximum length for the new summary
            
        Returns:
            New summary string or None if post not found
            
        Requirements: 2.2, 2.4, 2.5
        """
        post = db.session.get(Post, post_id)
        if not post:
            return None
        
        # Generate new summary from current content
        new_summary = PostManager.generate_summary(post.content, max_length)
        post.summary = new_summary
        
        db.session.commit()
        return new_summary

    @staticmethod
    def update_summary(post_id: int, summary: str) -> Optional[str]:
        """
        Update summary for an existing post with manual content.
        
        Args:
            post_id: ID of the post to update
            summary: New summary content
            
        Returns:
            Processed summary string or None if post not found
            
        Requirements: 2.1, 2.4
        """
        post = db.session.get(Post, post_id)
        if not post:
            return None
        
        # Process and truncate the manual summary
        processed_summary = PostManager._truncate_summary(summary) if summary else PostManager.generate_summary(post.content)
        post.summary = processed_summary
        
        db.session.commit()
        return processed_summary

    @staticmethod
    def get_summary_stats(post_id: int) -> Optional[Dict[str, Any]]:
        """
        Get summary statistics for a post.
        
        Args:
            post_id: ID of the post
            
        Returns:
            Dictionary with summary statistics or None if post not found
            
        Requirements: 2.2, 2.4, 2.5
        """
        post = db.session.get(Post, post_id)
        if not post:
            return None
        
        summary = post.summary or ""
        content = post.content or ""
        
        # Check if summary was auto-generated (ends with "...")
        is_auto_generated = summary.endswith("...")
        
        return {
            'post_id': post_id,
            'summary_length': len(summary),
            'content_length': len(content),
            'is_auto_generated': is_auto_generated,
            'is_truncated': len(summary) >= PostManager.MAX_SUMMARY_LENGTH - 3,
            'max_length': PostManager.MAX_SUMMARY_LENGTH,
            'default_length': PostManager.DEFAULT_SUMMARY_LENGTH
        }

    @staticmethod
    def bulk_update_status(post_ids: List[int], new_status: str) -> Dict[str, Any]:
        """
        Update status for multiple posts.
        
        Args:
            post_ids: List of post IDs to update
            new_status: New status to set
            
        Returns:
            Dictionary with update results
            
        Raises:
            ValueError: If invalid status
            
        Requirements: 6.3
        """
        if new_status not in PostManager.VALID_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of: {', '.join(PostManager.VALID_STATUSES)}")
        
        updated_count = 0
        errors = []
        
        for post_id in post_ids:
            try:
                post = db.session.get(Post, post_id)
                if post:
                    post.status = new_status
                    
                    # Handle status-specific logic
                    if new_status == 'published':
                        post.published_at = datetime.now(timezone.utc)
                        post.scheduled_publish_at = None
                    elif new_status == 'draft':
                        post.scheduled_publish_at = None
                    
                    updated_count += 1
                else:
                    errors.append(f"Post {post_id} not found")
            except Exception as e:
                errors.append(f"Error updating post {post_id}: {str(e)}")
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'updated_count': 0,
                'errors': [f"Database error: {str(e)}"]
            }
        
        return {
            'success': len(errors) == 0,
            'updated_count': updated_count,
            'errors': errors
        }

    @staticmethod
    def get_posts_organized_by_status() -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all posts organized by status for dashboard display.
        
        Returns:
            Dictionary with posts organized by status
            
        Requirements: 1.4, 6.1, 6.2, 6.4
        """
        organized_posts = {
            'draft': [],
            'published': [],
            'scheduled': []
        }
        
        for status in PostManager.VALID_STATUSES:
            posts = PostManager.get_posts_by_status(status)
            for post in posts:
                metadata = PostManager.get_post_metadata(post.id)
                if metadata:
                    organized_posts[status].append(metadata)
        
        return organized_posts