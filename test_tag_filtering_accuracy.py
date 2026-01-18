"""
Property-based test for tag filtering accuracy

This module tests Property 11: Tag Filtering Accuracy
**Validates: Requirements 4.6**

The property tests that for any tag selection, the system should return exactly 
the posts that are associated with that tag through the relationship table.
"""

import pytest
import uuid
from datetime import datetime
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import db, Tag, Post, User, post_tags
from tag_manager import TagManager


@composite
def valid_tag_name(draw):
    """Generate valid tag names for testing."""
    # Generate base name with letters, numbers, spaces, and common punctuation
    base_chars = st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')),
        min_size=1,
        max_size=30
    )
    name = draw(base_chars).strip()
    
    # Ensure we have a non-empty name after stripping
    assume(len(name) > 0)
    assume(not name.isspace())
    
    return name


@composite
def post_data(draw):
    """Generate post data for testing."""
    title = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    content = draw(st.text(min_size=1, max_size=500).filter(lambda x: x.strip()))
    status = draw(st.sampled_from(['draft', 'published', 'scheduled']))
    
    return {
        'title': title,
        'content': content,
        'status': status
    }


@composite
def tag_name_list(draw):
    """Generate a list of unique tag names."""
    tag_names = draw(st.lists(
        valid_tag_name(),
        min_size=1,
        max_size=8,
        unique_by=lambda x: x.lower()
    ))
    return tag_names


class TestTagFilteringAccuracy:
    """
    Property-based tests for tag filtering accuracy.
    
    **Feature: enhanced-content-management, Property 11: Tag Filtering Accuracy**
    **Validates: Requirements 4.6**
    
    Tests that for any tag selection, the system returns exactly the posts 
    that are associated with that tag through the relationship table.
    """

    def create_app_and_db(self):
        """Create a fresh Flask app and database for each test."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = 'test-secret'
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            return app

    @given(
        st.lists(post_data(), min_size=2, max_size=6),
        st.lists(tag_name_list(), min_size=2, max_size=4)
    )
    @settings(max_examples=15, deadline=None)
    def test_tag_filtering_returns_exactly_associated_posts(self, posts_data, tag_groups):
        """
        **Property 11: Tag Filtering Accuracy**
        **Validates: Requirements 4.6**
        
        For any tag selection, the system should return exactly the posts 
        that are associated with that tag through the relationship table.
        
        This test:
        1. Creates multiple posts with different tag associations
        2. For each tag, verifies that get_posts_by_tag returns exactly 
           the posts that were associated with that tag
        3. Ensures no false positives (posts not associated with the tag)
        4. Ensures no false negatives (missing posts that should be associated)
        """
        app = self.create_app_and_db()
        with app.app_context():
            # Flatten and deduplicate all tag names
            all_tag_names = []
            for tag_group in tag_groups:
                all_tag_names.extend(tag_group)
            unique_tag_names = list(set(tag_name.lower() for tag_name in all_tag_names))
            assume(len(unique_tag_names) >= 2)  # Need at least 2 unique tags
            
            # Create posts and track their tag associations
            created_posts = []
            post_tag_mapping = {}  # post_id -> set of tag names (lowercase)
            
            for i, post_info in enumerate(posts_data):
                # Create post
                post = Post(
                    title=f"{post_info['title']}_{uuid.uuid4().hex[:8]}",
                    content=post_info['content'],
                    status=post_info['status']
                )
                db.session.add(post)
                db.session.commit()
                created_posts.append(post)
                
                # Assign tags from corresponding tag group (cycle if needed)
                tag_group_index = i % len(tag_groups)
                assigned_tags = tag_groups[tag_group_index]
                
                # Associate tags with post
                TagManager.associate_tags(post.id, assigned_tags)
                
                # Track the association (normalize to lowercase for comparison)
                post_tag_mapping[post.id] = set(tag.lower() for tag in assigned_tags)
            
            # Test filtering accuracy for each unique tag
            all_tags = Tag.query.all()
            
            for tag in all_tags:
                tag_name_lower = tag.name.lower()
                
                # Get posts by tag using the system under test
                filtered_posts = TagManager.get_posts_by_tag(tag, status='published')
                filtered_post_ids = set(post.id for post in filtered_posts)
                
                # Determine expected posts (those that should have this tag)
                expected_post_ids = set()
                for post_id, associated_tag_names in post_tag_mapping.items():
                    if tag_name_lower in associated_tag_names:
                        # Only include published posts in expected results
                        post = db.session.get(Post, post_id)
                        if post and post.status == 'published':
                            expected_post_ids.add(post_id)
                
                # Verify exact match: no false positives, no false negatives
                assert filtered_post_ids == expected_post_ids, (
                    f"Tag filtering accuracy failed for tag '{tag.name}':\n"
                    f"Expected post IDs: {expected_post_ids}\n"
                    f"Actual post IDs: {filtered_post_ids}\n"
                    f"False positives (unexpected): {filtered_post_ids - expected_post_ids}\n"
                    f"False negatives (missing): {expected_post_ids - filtered_post_ids}\n"
                    f"Post-tag mapping: {post_tag_mapping}"
                )

    @given(
        st.lists(post_data(), min_size=3, max_size=5),
        tag_name_list()
    )
    @settings(max_examples=12, deadline=None)
    def test_tag_filtering_respects_post_status(self, posts_data, tag_names):
        """
        **Property 11: Tag Filtering Accuracy (Status Filtering)**
        **Validates: Requirements 4.6**
        
        Tag filtering should respect post status and only return posts 
        with the specified status (default: published).
        """
        app = self.create_app_and_db()
        with app.app_context():
            assume(len(tag_names) >= 1)
            
            # Create posts with different statuses
            created_posts = []
            published_post_ids = set()
            draft_post_ids = set()
            
            for i, post_info in enumerate(posts_data):
                post = Post(
                    title=f"{post_info['title']}_{uuid.uuid4().hex[:8]}",
                    content=post_info['content'],
                    status=post_info['status']
                )
                db.session.add(post)
                db.session.commit()
                created_posts.append(post)
                
                # Associate all posts with the same tag for testing
                TagManager.associate_tags(post.id, [tag_names[0]])
                
                # Track posts by status
                if post.status == 'published':
                    published_post_ids.add(post.id)
                elif post.status == 'draft':
                    draft_post_ids.add(post.id)
            
            # Get the tag we're testing with
            test_tag = Tag.query.filter_by(name=tag_names[0]).first()
            assume(test_tag is not None)
            
            # Test filtering by published status (default)
            published_posts = TagManager.get_posts_by_tag(test_tag, status='published')
            published_result_ids = set(post.id for post in published_posts)
            
            assert published_result_ids == published_post_ids, (
                f"Published post filtering failed:\n"
                f"Expected: {published_post_ids}\n"
                f"Actual: {published_result_ids}"
            )
            
            # Test filtering by draft status
            draft_posts = TagManager.get_posts_by_tag(test_tag, status='draft')
            draft_result_ids = set(post.id for post in draft_posts)
            
            assert draft_result_ids == draft_post_ids, (
                f"Draft post filtering failed:\n"
                f"Expected: {draft_post_ids}\n"
                f"Actual: {draft_result_ids}"
            )

    @given(
        st.lists(post_data(), min_size=2, max_size=4),
        st.lists(valid_tag_name(), min_size=2, max_size=5, unique_by=lambda x: x.lower())
    )
    @settings(max_examples=10, deadline=None)
    def test_tag_filtering_handles_multiple_tag_associations(self, posts_data, tag_names):
        """
        **Property 11: Tag Filtering Accuracy (Multiple Associations)**
        **Validates: Requirements 4.6**
        
        When posts are associated with multiple tags, filtering by any single tag
        should return exactly the posts associated with that specific tag.
        """
        app = self.create_app_and_db()
        with app.app_context():
            assume(len(tag_names) >= 2)
            
            # Create posts with overlapping tag associations
            created_posts = []
            tag_to_posts = {}  # tag_name -> set of post_ids
            
            for tag_name in tag_names:
                tag_to_posts[tag_name.lower()] = set()
            
            for i, post_info in enumerate(posts_data):
                post = Post(
                    title=f"{post_info['title']}_{uuid.uuid4().hex[:8]}",
                    content=post_info['content'],
                    status='published'  # Use published for consistent testing
                )
                db.session.add(post)
                db.session.commit()
                created_posts.append(post)
                
                # Assign a subset of tags to each post (create overlapping associations)
                num_tags_to_assign = min(len(tag_names), (i % 3) + 1)  # 1-3 tags per post
                assigned_tags = tag_names[:num_tags_to_assign]
                
                TagManager.associate_tags(post.id, assigned_tags)
                
                # Track which posts are associated with which tags
                for tag_name in assigned_tags:
                    tag_to_posts[tag_name.lower()].add(post.id)
            
            # Test filtering accuracy for each tag
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                assume(tag is not None)
                
                # Get posts by this specific tag
                filtered_posts = TagManager.get_posts_by_tag(tag, status='published')
                filtered_post_ids = set(post.id for post in filtered_posts)
                
                # Expected posts for this tag
                expected_post_ids = tag_to_posts[tag_name.lower()]
                
                assert filtered_post_ids == expected_post_ids, (
                    f"Multiple tag association filtering failed for tag '{tag_name}':\n"
                    f"Expected post IDs: {expected_post_ids}\n"
                    f"Actual post IDs: {filtered_post_ids}\n"
                    f"Tag-to-posts mapping: {tag_to_posts}"
                )

    @given(valid_tag_name())
    @settings(max_examples=15, deadline=None)
    def test_tag_filtering_handles_nonexistent_and_empty_tags(self, tag_name):
        """
        **Property 11: Tag Filtering Accuracy (Edge Cases)**
        **Validates: Requirements 4.6**
        
        Tag filtering should handle edge cases like nonexistent tags and 
        tags with no associated posts correctly.
        """
        app = self.create_app_and_db()
        with app.app_context():
            # Test with nonexistent tag (None)
            posts_for_none = TagManager.get_posts_by_tag(None)
            assert posts_for_none == [], (
                "Filtering with None tag should return empty list"
            )
            
            # Create a tag but don't associate it with any posts
            orphan_tag = TagManager.get_or_create_tag(tag_name)
            
            # Test filtering with tag that has no associations
            posts_for_orphan = TagManager.get_posts_by_tag(orphan_tag)
            assert posts_for_orphan == [], (
                f"Filtering with unassociated tag '{tag_name}' should return empty list"
            )
            
            # Create a post and associate it with the tag
            post = Post(
                title=f"Test Post {uuid.uuid4().hex[:8]}",
                content="Test content",
                status='published'
            )
            db.session.add(post)
            db.session.commit()
            
            TagManager.associate_tags(post.id, [tag_name])
            
            # Now the tag should return exactly one post
            posts_after_association = TagManager.get_posts_by_tag(orphan_tag)
            assert len(posts_after_association) == 1, (
                f"Tag '{tag_name}' should return exactly 1 post after association"
            )
            assert posts_after_association[0].id == post.id, (
                f"Tag '{tag_name}' should return the correct associated post"
            )