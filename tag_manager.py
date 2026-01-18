"""
Tag Management System for Enhanced Content Management

This module provides the TagManager class for handling tag operations including:
- Tag creation with automatic slug generation
- Tag retrieval and searching
- Post-tag association management
- SEO-friendly URL slug generation
"""

import re
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import func
from models import db, Tag, Post, post_tags


class TagManager:
    """
    Manages tag operations for the blog system including creation, retrieval,
    and association management with SEO-friendly URL slug generation.
    """

    @staticmethod
    def generate_slug(name: str) -> str:
        """
        Generate SEO-friendly URL slug from tag name.
        
        Args:
            name: The tag name to convert to slug
            
        Returns:
            SEO-friendly slug string
            
        Examples:
            >>> TagManager.generate_slug("Python Programming")
            'python-programming'
            >>> TagManager.generate_slug("Web Dev & Design")
            'web-dev-design'
        """
        if not name or not name.strip():
            return ""
            
        # Convert to lowercase and replace spaces with hyphens
        slug = name.lower().strip()
        
        # Remove special characters except hyphens and alphanumeric
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        
        # Replace multiple spaces/hyphens with single hyphen
        slug = re.sub(r'[\s-]+', '-', slug)
        
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        
        # If slug is empty after cleaning, use a fallback based on the original name
        if not slug and name and name.strip():
            # Create a fallback slug using the hash of the original name
            import hashlib
            hash_suffix = hashlib.md5(name.encode('utf-8')).hexdigest()[:8]
            slug = f"tag-{hash_suffix}"
        
        return slug

    @staticmethod
    def get_or_create_tag(tag_name: str) -> Tag:
        """
        Get existing tag or create new one with automatic slug generation.
        
        Args:
            tag_name: Name of the tag to get or create
            
        Returns:
            Tag object (existing or newly created)
            
        Raises:
            ValueError: If tag_name is empty or invalid
        """
        if not tag_name or not tag_name.strip():
            raise ValueError("Tag name cannot be empty")
            
        tag_name = tag_name.strip()
        
        # Check if tag already exists (case-insensitive)
        existing_tag = Tag.query.filter(func.lower(Tag.name) == func.lower(tag_name)).first()
        if existing_tag:
            return existing_tag
            
        # Create new tag with generated slug
        slug = TagManager.generate_slug(tag_name)
        
        # Ensure slug uniqueness by appending number if needed
        base_slug = slug
        counter = 1
        while Tag.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
            
        new_tag = Tag(name=tag_name, slug=slug)
        db.session.add(new_tag)
        db.session.commit()
        
        return new_tag

    @staticmethod
    def associate_tags(post_id: int, tag_names: List[str]) -> List[Tag]:
        """
        Create post-tag associations for given tag names.
        
        Args:
            post_id: ID of the post to associate tags with
            tag_names: List of tag names to associate
            
        Returns:
            List of Tag objects that were associated
            
        Raises:
            ValueError: If post_id is invalid or post doesn't exist
        """
        if not post_id:
            raise ValueError("Post ID cannot be empty")
            
        post = db.session.get(Post, post_id)
        if not post:
            raise ValueError(f"Post with ID {post_id} not found")
            
        if not tag_names:
            return []
            
        # Clear existing tag associations
        post.tag_relationships.clear()
        
        # Create or get tags and associate them
        associated_tags = []
        for tag_name in tag_names:
            if tag_name and tag_name.strip():
                tag = TagManager.get_or_create_tag(tag_name.strip())
                post.tag_relationships.append(tag)
                associated_tags.append(tag)
                
        db.session.commit()
        return associated_tags

    @staticmethod
    def get_popular_tags(limit: int = 20) -> List[Tuple[Tag, int]]:
        """
        Get most frequently used tags with their usage counts.
        
        Args:
            limit: Maximum number of tags to return (default: 20)
            
        Returns:
            List of tuples containing (Tag, usage_count) ordered by usage count descending
        """
        if limit <= 0:
            return []
            
        # Query tags with their usage counts
        popular_tags = (
            db.session.query(Tag, func.count(post_tags.c.post_id).label('usage_count'))
            .join(post_tags, Tag.id == post_tags.c.tag_id)
            .group_by(Tag.id)
            .order_by(func.count(post_tags.c.post_id).desc())
            .limit(limit)
            .all()
        )
        
        return popular_tags

    @staticmethod
    def search_tags(query: str, limit: int = 10) -> List[Tag]:
        """
        Search for tags by name (case-insensitive partial match).
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of matching Tag objects
        """
        if not query or not query.strip():
            return []
            
        search_term = f"%{query.strip().lower()}%"
        
        matching_tags = (
            Tag.query
            .filter(func.lower(Tag.name).like(search_term))
            .order_by(Tag.name)
            .limit(limit)
            .all()
        )
        
        return matching_tags

    @staticmethod
    def get_tag_by_slug(slug: str) -> Optional[Tag]:
        """
        Get tag by its URL slug.
        
        Args:
            slug: URL slug of the tag
            
        Returns:
            Tag object if found, None otherwise
        """
        if not slug:
            return None
            
        return Tag.query.filter_by(slug=slug).first()

    @staticmethod
    def get_posts_by_tag(tag: Tag, status: str = 'published') -> List[Post]:
        """
        Get all posts associated with a specific tag.
        
        Args:
            tag: Tag object to get posts for
            status: Post status to filter by (default: 'published')
            
        Returns:
            List of Post objects associated with the tag
        """
        if not tag:
            return []
            
        posts = (
            Post.query
            .join(post_tags, Post.id == post_tags.c.post_id)
            .filter(post_tags.c.tag_id == tag.id)
            .filter(Post.status == status)
            .order_by(Post.created_at.desc())
            .all()
        )
        
        return posts

    @staticmethod
    def get_posts_by_tag_name(tag_name: str, published_only: bool = True) -> List[Post]:
        """
        Get all posts associated with a specific tag by name.
        
        Args:
            tag_name: Name of the tag to get posts for
            published_only: Whether to only return published posts
            
        Returns:
            List of Post objects associated with the tag
        """
        if not tag_name:
            return []
        
        tag = Tag.query.filter_by(name=tag_name).first()
        if not tag:
            return []
        
        status_filter = 'published' if published_only else None
        return TagManager.get_posts_by_tag(tag, status_filter) if status_filter else TagManager.get_posts_by_tag(tag)

    @staticmethod
    def get_all_tags_with_counts() -> List[Dict[str, Any]]:
        """
        Get all tags with their post counts.
        
        Returns:
            List of dictionaries containing tag data with post counts
        """
        # Query tags with post counts using a join
        tags_with_counts = (
            db.session.query(Tag, db.func.count(post_tags.c.post_id).label('post_count'))
            .outerjoin(post_tags, Tag.id == post_tags.c.tag_id)
            .outerjoin(Post, post_tags.c.post_id == Post.id)
            .filter(db.or_(Post.status == 'published', Post.id.is_(None)))  # Only count published posts
            .group_by(Tag.id)
            .order_by(db.func.count(post_tags.c.post_id).desc(), Tag.name)
            .all()
        )
        
        result = []
        for tag, count in tags_with_counts:
            if count > 0:  # Only include tags that have posts
                result.append({
                    'id': tag.id,
                    'name': tag.name,
                    'slug': tag.slug,
                    'post_count': count
                })
        
        return result

    @staticmethod
    def remove_tag_association(post_id: int, tag_id: int) -> bool:
        """
        Remove association between a post and a tag.
        
        Args:
            post_id: ID of the post
            tag_id: ID of the tag
            
        Returns:
            True if association was removed, False if it didn't exist
        """
        post = db.session.get(Post, post_id)
        tag = db.session.get(Tag, tag_id)
        
        if not post or not tag:
            return False
            
        if tag in post.tag_relationships:
            post.tag_relationships.remove(tag)
            db.session.commit()
            return True
            
        return False

    @staticmethod
    def delete_unused_tags() -> int:
        """
        Delete tags that are not associated with any posts.
        
        Returns:
            Number of tags deleted
        """
        # Find tags with no post associations
        unused_tags = (
            Tag.query
            .outerjoin(post_tags, Tag.id == post_tags.c.tag_id)
            .filter(post_tags.c.tag_id.is_(None))
            .all()
        )
        
        count = len(unused_tags)
        for tag in unused_tags:
            db.session.delete(tag)
            
        db.session.commit()
        return count

    @staticmethod
    def get_all_tags() -> List[Tag]:
        """
        Get all tags ordered by name.
        
        Returns:
            List of all Tag objects ordered alphabetically
        """
        return Tag.query.order_by(Tag.name).all()

    @staticmethod
    def migrate_legacy_tags() -> dict:
        """
        Convert comma-separated tag strings to proper database relationships.
        
        This migration function processes all posts that have legacy comma-separated
        tag strings in the 'tags' field and creates proper Tag entities and 
        post-tag associations while preserving the original tags field for 
        backward compatibility.
        
        Returns:
            Dictionary with migration statistics:
            - posts_processed: Number of posts that had legacy tags
            - tags_created: Number of new Tag entities created
            - associations_created: Number of post-tag associations created
            - errors: List of any errors encountered during migration
            
        Requirements: 4.1
        """
        stats = {
            'posts_processed': 0,
            'tags_created': 0,
            'associations_created': 0,
            'errors': []
        }
        
        try:
            # Find all posts with legacy comma-separated tags
            posts_with_legacy_tags = Post.query.filter(
                Post.tags.isnot(None),
                Post.tags != ''
            ).all()
            
            for post in posts_with_legacy_tags:
                try:
                    # Parse comma-separated tags
                    tag_names = [tag.strip() for tag in post.tags.split(',') if tag.strip()]
                    
                    if not tag_names:
                        continue
                        
                    stats['posts_processed'] += 1
                    
                    # Clear existing tag relationships to avoid duplicates
                    post.tag_relationships.clear()
                    
                    # Process each tag name
                    for tag_name in tag_names:
                        try:
                            # Check if tag already exists (case-insensitive)
                            existing_tag = Tag.query.filter(
                                func.lower(Tag.name) == func.lower(tag_name)
                            ).first()
                            
                            if existing_tag:
                                tag = existing_tag
                            else:
                                # Create new tag with generated slug
                                slug = TagManager.generate_slug(tag_name)
                                
                                # Ensure slug uniqueness
                                base_slug = slug
                                counter = 1
                                while Tag.query.filter_by(slug=slug).first():
                                    slug = f"{base_slug}-{counter}"
                                    counter += 1
                                
                                tag = Tag(name=tag_name, slug=slug)
                                db.session.add(tag)
                                stats['tags_created'] += 1
                            
                            # Create post-tag association if not already exists
                            if tag not in post.tag_relationships:
                                post.tag_relationships.append(tag)
                                stats['associations_created'] += 1
                                
                        except Exception as e:
                            error_msg = f"Error processing tag '{tag_name}' for post {post.id}: {str(e)}"
                            stats['errors'].append(error_msg)
                            continue
                    
                except Exception as e:
                    error_msg = f"Error processing post {post.id}: {str(e)}"
                    stats['errors'].append(error_msg)
                    continue
            
            # Commit all changes
            db.session.commit()
            
        except Exception as e:
            # Rollback on major error
            db.session.rollback()
            error_msg = f"Migration failed with error: {str(e)}"
            stats['errors'].append(error_msg)
            raise RuntimeError(error_msg)
        
        return stats

    @staticmethod
    def update_tag(tag_id: int, name: str = None, slug: str = None) -> Optional[Tag]:
        """
        Update tag name and/or slug.
        
        Args:
            tag_id: ID of the tag to update
            name: New name for the tag (optional)
            slug: New slug for the tag (optional)
            
        Returns:
            Updated Tag object if successful, None if tag not found
            
        Raises:
            ValueError: If slug already exists for another tag
        """
        tag = db.session.get(Tag, tag_id)
        if not tag:
            return None
            
        if name is not None:
            tag.name = name.strip()
            
        if slug is not None:
            # Check if slug is already used by another tag
            existing_tag = Tag.query.filter(Tag.slug == slug, Tag.id != tag_id).first()
            if existing_tag:
                raise ValueError(f"Slug '{slug}' is already used by another tag")
            tag.slug = slug
            
        db.session.commit()
        return tag