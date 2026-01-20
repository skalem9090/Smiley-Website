"""
Property-based test for comment display format.

**Feature: blog-comprehensive-features, Property 17: Comment Display Format**
**Validates: Requirements 5.5, 5.6**

This module tests that for any approved comment, it should display commenter name, 
date, and content in chronological order below the post.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.strategies import composite

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import db, Comment, Post, User
from comment_manager import CommentManager


@composite
def valid_comment_data(draw):
    """Generate valid comment data for testing."""
    author_name = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    
    # Generate valid email
    local_part = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        min_size=1, max_size=20
    ))
    domain = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        min_size=1, max_size=20
    ))
    tld = draw(st.sampled_from(['com', 'org', 'net', 'edu', 'gov']))
    author_email = f"{local_part}@{domain}.{tld}".lower()
    
    content = draw(st.text(min_size=1, max_size=2000).filter(lambda x: x.strip()))
    
    # Ensure all fields are non-empty after stripping
    assume(len(author_name) > 0)
    assume(len(content) > 0)
    assume('@' in author_email and '.' in author_email)
    
    return {
        'author_name': author_name,
        'author_email': author_email,
        'content': content
    }


class TestCommentDisplayFormat:
    """Test suite for comment display format property."""
    
    def create_app_and_db(self):
        """Create a test Flask app and database."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['WTF_CSRF_ENABLED'] = False
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            
            # Create a test user for moderation
            admin_user = User(username='admin', is_admin=True)
            admin_user.set_password('password')
            db.session.add(admin_user)
            
            # Create a test post
            test_post = Post(
                title='Test Post',
                content='Test content',
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            db.session.add(test_post)
            db.session.commit()
            
            # Store IDs before leaving context
            post_id = test_post.id
            admin_id = admin_user.id
            
        return app, post_id, admin_id
    
    @given(comment_data=valid_comment_data())
    @settings(max_examples=15, deadline=3000, suppress_health_check=[HealthCheck.data_too_large])
    def test_approved_comment_display_format(self, comment_data):
        """
        **Property 17: Comment Display Format (Basic Display)**
        
        For any approved comment, it should display commenter name, date, and content
        with all required information properly formatted.
        """
        app, post_id, admin_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit and approve comment
            success, message, comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=comment_data['author_name'],
                author_email=comment_data['author_email'],
                content=comment_data['content']
            )
            
            assert success and comment is not None, "Comment submission should succeed"
            
            # Approve the comment
            approve_success, _ = comment_manager.approve_comment(comment.id, admin_id)
            assert approve_success, "Comment approval should succeed"
            
            # Get approved comments for display
            approved_comments = comment_manager.get_approved_comments(post_id)
            
            # Verify comment appears in approved list
            assert comment in approved_comments, "Approved comment should appear in display list"
            
            # Verify comment has all required display information
            db.session.refresh(comment)
            assert comment.author_name == comment_data['author_name'], "Comment should preserve author name"
            assert comment.author_email == comment_data['author_email'].lower(), "Comment should preserve author email"
            assert comment.content == comment_data['content'], "Comment should preserve content"
            assert comment.created_at is not None, "Comment should have creation timestamp"
            assert isinstance(comment.created_at, datetime), "Creation timestamp should be datetime object"
            
            # Verify comment tree structure includes required fields
            comment_tree = comment_manager.get_comment_tree(post_id)
            assert len(comment_tree) > 0, "Comment tree should contain approved comments"
            
            # Find our comment in the tree
            our_comment_data = None
            for comment_dict in comment_tree:
                if comment_dict['id'] == comment.id:
                    our_comment_data = comment_dict
                    break
            
            assert our_comment_data is not None, "Comment should appear in comment tree"
            assert 'author_name' in our_comment_data, "Comment tree should include author name"
            assert 'content' in our_comment_data, "Comment tree should include content"
            assert 'created_at' in our_comment_data, "Comment tree should include creation date"
            assert our_comment_data['author_name'] == comment_data['author_name'], "Tree should preserve author name"
            assert our_comment_data['content'] == comment_data['content'], "Tree should preserve content"
    
    @given(st.lists(valid_comment_data(), min_size=2, max_size=5))
    @settings(max_examples=10, deadline=3000, suppress_health_check=[HealthCheck.data_too_large])
    def test_chronological_comment_ordering(self, comments_data):
        """
        **Property 17: Comment Display Format (Chronological Order)**
        
        For any set of approved comments, they should be displayed in chronological
        order (oldest first) below the post.
        """
        app, post_id, admin_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit comments with slight time delays to ensure different timestamps
            submitted_comments = []
            for i, comment_data in enumerate(comments_data):
                # Add a small delay to ensure different timestamps
                import time
                if i > 0:
                    time.sleep(0.01)
                
                success, message, comment = comment_manager.submit_comment(
                    post_id=post_id,
                    author_name=f"{comment_data['author_name']} {i}",
                    author_email=comment_data['author_email'],
                    content=f"{comment_data['content']} - Comment {i}"
                )
                
                assert success and comment is not None, f"Comment {i} submission should succeed"
                
                # Approve the comment
                approve_success, _ = comment_manager.approve_comment(comment.id, admin_id)
                assert approve_success, f"Comment {i} approval should succeed"
                
                submitted_comments.append(comment)
            
            # Get approved comments
            approved_comments = comment_manager.get_approved_comments(post_id)
            
            # Verify all comments are in the approved list
            assert len(approved_comments) == len(submitted_comments), "All comments should be approved"
            
            # Verify chronological ordering (oldest first)
            for i in range(len(approved_comments) - 1):
                current_comment = approved_comments[i]
                next_comment = approved_comments[i + 1]
                
                assert current_comment.created_at <= next_comment.created_at, \
                    f"Comments should be in chronological order: {current_comment.created_at} <= {next_comment.created_at}"
            
            # Verify comment tree also maintains chronological order
            comment_tree = comment_manager.get_comment_tree(post_id)
            assert len(comment_tree) == len(submitted_comments), "Comment tree should contain all comments"
            
            # Parse timestamps from comment tree and verify ordering
            tree_timestamps = []
            for comment_dict in comment_tree:
                timestamp_str = comment_dict['created_at']
                # Parse ISO format timestamp
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                tree_timestamps.append(timestamp)
            
            # Verify tree timestamps are in chronological order
            for i in range(len(tree_timestamps) - 1):
                assert tree_timestamps[i] <= tree_timestamps[i + 1], \
                    "Comment tree should maintain chronological order"
    
    @given(comment_data=valid_comment_data())
    @settings(max_examples=10, deadline=3000, suppress_health_check=[HealthCheck.data_too_large])
    def test_comment_content_preservation(self, comment_data):
        """
        **Property 17: Comment Display Format (Content Preservation)**
        
        For any approved comment, the display format should preserve the original
        content without modification while maintaining proper formatting.
        """
        app, post_id, admin_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Test with content that includes special characters and formatting
            special_content = f"{comment_data['content']}\\n\\nWith newlines\\nAnd special chars: @#$%^&*()"
            
            # Submit and approve comment
            success, message, comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=comment_data['author_name'],
                author_email=comment_data['author_email'],
                content=special_content
            )
            
            assert success and comment is not None, "Comment submission should succeed"
            
            # Approve the comment
            approve_success, _ = comment_manager.approve_comment(comment.id, admin_id)
            assert approve_success, "Comment approval should succeed"
            
            # Verify content preservation in database
            db.session.refresh(comment)
            assert comment.content == special_content, "Comment content should be preserved exactly"
            
            # Verify content preservation in comment tree
            comment_tree = comment_manager.get_comment_tree(post_id)
            assert len(comment_tree) == 1, "Should have one comment in tree"
            
            tree_comment = comment_tree[0]
            assert tree_comment['content'] == special_content, "Comment tree should preserve original content"
            
            # Verify no HTML escaping or modification occurred
            assert '\\n' in tree_comment['content'], "Newline characters should be preserved"
            assert '@#$%^&*()' in tree_comment['content'], "Special characters should be preserved"
    
    @given(comment_data=valid_comment_data())
    @settings(max_examples=10, deadline=3000, suppress_health_check=[HealthCheck.data_too_large])
    def test_unapproved_comment_exclusion(self, comment_data):
        """
        **Property 17: Comment Display Format (Visibility Control)**
        
        For any unapproved comment, it should not appear in the display format
        regardless of its content or metadata.
        """
        app, post_id, admin_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit comment but don't approve it
            success, message, comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=comment_data['author_name'],
                author_email=comment_data['author_email'],
                content=comment_data['content']
            )
            
            assert success and comment is not None, "Comment submission should succeed"
            assert not comment.is_approved, "Comment should not be approved initially"
            
            # Get approved comments for display
            approved_comments = comment_manager.get_approved_comments(post_id)
            
            # Verify unapproved comment does not appear
            assert comment not in approved_comments, "Unapproved comment should not appear in display"
            assert len(approved_comments) == 0, "No comments should be in approved display"
            
            # Verify comment tree excludes unapproved comments
            comment_tree = comment_manager.get_comment_tree(post_id)
            assert len(comment_tree) == 0, "Comment tree should not include unapproved comments"
            
            # Submit and approve a second comment to verify filtering works correctly
            success2, message2, comment2 = comment_manager.submit_comment(
                post_id=post_id,
                author_name=f"{comment_data['author_name']} 2",
                author_email=comment_data['author_email'],
                content=f"{comment_data['content']} - Approved"
            )
            
            assert success2 and comment2 is not None, "Second comment submission should succeed"
            
            # Approve only the second comment
            approve_success, _ = comment_manager.approve_comment(comment2.id, admin_id)
            assert approve_success, "Second comment approval should succeed"
            
            # Verify only approved comment appears
            approved_comments_after = comment_manager.get_approved_comments(post_id)
            assert len(approved_comments_after) == 1, "Only approved comment should appear"
            assert comment2 in approved_comments_after, "Approved comment should appear"
            assert comment not in approved_comments_after, "Unapproved comment should still not appear"
            
            # Verify comment tree only includes approved comment
            comment_tree_after = comment_manager.get_comment_tree(post_id)
            assert len(comment_tree_after) == 1, "Comment tree should only include approved comment"
            assert comment_tree_after[0]['id'] == comment2.id, "Tree should contain the approved comment"


if __name__ == '__main__':
    pytest.main([__file__])