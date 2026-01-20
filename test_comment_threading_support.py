"""
Property-based test for comment threading support.

**Feature: blog-comprehensive-features, Property 20: Comment Threading Support**
**Validates: Requirements 5.10**

This module tests that for any comment reply (if threading is enabled), it should 
maintain proper parent-child relationships and display hierarchically.
"""

import pytest
import uuid
from datetime import datetime, timezone
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


class TestCommentThreadingSupport:
    """Test suite for comment threading support property."""
    
    def create_app_and_db(self, enable_threading=True):
        """Create a test Flask app and database."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['COMMENT_ENABLE_THREADING'] = enable_threading
        
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
    
    @given(
        parent_data=valid_comment_data(),
        reply_data=valid_comment_data()
    )
    @settings(max_examples=15, deadline=3000, suppress_health_check=[HealthCheck.data_too_large])
    def test_comment_parent_child_relationship(self, parent_data, reply_data):
        """
        **Property 20: Comment Threading Support (Parent-Child Relationships)**
        
        For any comment reply when threading is enabled, it should maintain proper
        parent-child relationships in the database.
        """
        app, post_id, admin_id = self.create_app_and_db(enable_threading=True)
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit parent comment
            parent_success, parent_message, parent_comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=parent_data['author_name'],
                author_email=parent_data['author_email'],
                content=parent_data['content']
            )
            
            assert parent_success and parent_comment is not None, "Parent comment submission should succeed"
            
            # Approve parent comment
            approve_success, _ = comment_manager.approve_comment(parent_comment.id, admin_id)
            assert approve_success, "Parent comment approval should succeed"
            
            # Submit reply comment
            reply_success, reply_message, reply_comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=reply_data['author_name'],
                author_email=reply_data['author_email'],
                content=reply_data['content'],
                parent_id=parent_comment.id
            )
            
            assert reply_success and reply_comment is not None, "Reply comment submission should succeed"
            
            # Approve reply comment
            reply_approve_success, _ = comment_manager.approve_comment(reply_comment.id, admin_id)
            assert reply_approve_success, "Reply comment approval should succeed"
            
            # Refresh comments from database
            db.session.refresh(parent_comment)
            db.session.refresh(reply_comment)
            
            # Verify parent-child relationship
            assert reply_comment.parent_id == parent_comment.id, "Reply should reference correct parent"
            assert reply_comment.parent == parent_comment, "Reply should have correct parent relationship"
            assert reply_comment in parent_comment.replies, "Parent should include reply in replies collection"
            
            # Verify parent comment has no parent
            assert parent_comment.parent_id is None, "Parent comment should have no parent"
            assert parent_comment.parent is None, "Parent comment should have no parent relationship"
    
    @given(st.lists(valid_comment_data(), min_size=2, max_size=4))
    @settings(max_examples=10, deadline=3000, suppress_health_check=[HealthCheck.data_too_large])
    def test_comment_hierarchical_display(self, comments_data):
        """
        **Property 20: Comment Threading Support (Hierarchical Display)**
        
        For any set of threaded comments, they should be displayed hierarchically
        with proper nesting in the comment tree structure.
        """
        app, post_id, admin_id = self.create_app_and_db(enable_threading=True)
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit and approve parent comment
            parent_data = comments_data[0]
            parent_success, _, parent_comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=parent_data['author_name'],
                author_email=parent_data['author_email'],
                content=parent_data['content']
            )
            
            assert parent_success and parent_comment is not None, "Parent comment should be created"
            approve_success, _ = comment_manager.approve_comment(parent_comment.id, admin_id)
            assert approve_success, "Parent comment should be approved"
            
            # Submit and approve reply comments
            reply_comments = []
            for i, reply_data in enumerate(comments_data[1:], 1):
                reply_success, _, reply_comment = comment_manager.submit_comment(
                    post_id=post_id,
                    author_name=f"{reply_data['author_name']} {i}",
                    author_email=reply_data['author_email'],
                    content=f"{reply_data['content']} - Reply {i}",
                    parent_id=parent_comment.id
                )
                
                assert reply_success and reply_comment is not None, f"Reply {i} should be created"
                
                reply_approve_success, _ = comment_manager.approve_comment(reply_comment.id, admin_id)
                assert reply_approve_success, f"Reply {i} should be approved"
                
                reply_comments.append(reply_comment)
            
            # Get comment tree
            comment_tree = comment_manager.get_comment_tree(post_id)
            
            # Verify tree structure
            assert len(comment_tree) == 1, "Should have one root comment in tree"
            
            root_comment = comment_tree[0]
            assert root_comment['id'] == parent_comment.id, "Root should be the parent comment"
            assert 'replies' in root_comment, "Root comment should have replies field"
            assert len(root_comment['replies']) == len(reply_comments), "Root should have all replies"
            
            # Verify all replies are nested under parent
            reply_ids_in_tree = [reply['id'] for reply in root_comment['replies']]
            expected_reply_ids = [reply.id for reply in reply_comments]
            
            for expected_id in expected_reply_ids:
                assert expected_id in reply_ids_in_tree, f"Reply {expected_id} should be in tree"
            
            # Verify replies don't have their own replies (flat threading)
            for reply in root_comment['replies']:
                assert reply.get('replies', []) == [], "Replies should not have sub-replies in this test"
    
    @given(
        parent_data=valid_comment_data(),
        reply_data=valid_comment_data()
    )
    @settings(max_examples=10, deadline=3000, suppress_health_check=[HealthCheck.data_too_large])
    def test_threading_disabled_behavior(self, parent_data, reply_data):
        """
        **Property 20: Comment Threading Support (Threading Disabled)**
        
        For any comment reply attempt when threading is disabled, the system
        should ignore parent_id and treat all comments as top-level.
        """
        app, post_id, admin_id = self.create_app_and_db(enable_threading=False)
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit parent comment
            parent_success, _, parent_comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=parent_data['author_name'],
                author_email=parent_data['author_email'],
                content=parent_data['content']
            )
            
            assert parent_success and parent_comment is not None, "Parent comment should be created"
            approve_success, _ = comment_manager.approve_comment(parent_comment.id, admin_id)
            assert approve_success, "Parent comment should be approved"
            
            # Attempt to submit reply with parent_id (should be ignored)
            reply_success, _, reply_comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=reply_data['author_name'],
                author_email=reply_data['author_email'],
                content=reply_data['content'],
                parent_id=parent_comment.id  # This should be ignored
            )
            
            assert reply_success and reply_comment is not None, "Reply comment should be created"
            reply_approve_success, _ = comment_manager.approve_comment(reply_comment.id, admin_id)
            assert reply_approve_success, "Reply comment should be approved"
            
            # Verify threading is disabled
            db.session.refresh(reply_comment)
            assert reply_comment.parent_id is None, "Reply should have no parent when threading disabled"
            
            # Get comment tree
            comment_tree = comment_manager.get_comment_tree(post_id)
            
            # Verify both comments are at root level
            assert len(comment_tree) == 2, "Should have two root comments when threading disabled"
            
            root_comment_ids = [comment['id'] for comment in comment_tree]
            assert parent_comment.id in root_comment_ids, "Parent should be at root level"
            assert reply_comment.id in root_comment_ids, "Reply should also be at root level"
            
            # Verify no nesting
            for comment in comment_tree:
                assert comment.get('replies', []) == [], "No comments should have replies when threading disabled"
    
    @given(
        parent_data=valid_comment_data(),
        reply_data=valid_comment_data()
    )
    @settings(max_examples=10, deadline=3000, suppress_health_check=[HealthCheck.data_too_large])
    def test_reply_to_unapproved_comment_validation(self, parent_data, reply_data):
        """
        **Property 20: Comment Threading Support (Reply Validation)**
        
        For any reply attempt to an unapproved comment, the system should reject
        the reply to maintain proper threading integrity.
        """
        app, post_id, admin_id = self.create_app_and_db(enable_threading=True)
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit parent comment but don't approve it
            parent_success, _, parent_comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=parent_data['author_name'],
                author_email=parent_data['author_email'],
                content=parent_data['content']
            )
            
            assert parent_success and parent_comment is not None, "Parent comment should be created"
            assert not parent_comment.is_approved, "Parent comment should not be approved"
            
            # Attempt to reply to unapproved comment
            reply_success, reply_message, reply_comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=reply_data['author_name'],
                author_email=reply_data['author_email'],
                content=reply_data['content'],
                parent_id=parent_comment.id
            )
            
            # Reply should fail validation
            assert not reply_success, "Reply to unapproved comment should fail"
            assert reply_comment is None, "No reply comment should be created"
            assert "unapproved" in reply_message.lower(), "Error message should mention unapproved parent"
    
    @given(
        parent_data=valid_comment_data(),
        reply_data=valid_comment_data()
    )
    @settings(max_examples=10, deadline=3000, suppress_health_check=[HealthCheck.data_too_large])
    def test_cross_post_reply_validation(self, parent_data, reply_data):
        """
        **Property 20: Comment Threading Support (Cross-Post Validation)**
        
        For any reply attempt to a comment from a different post, the system
        should reject the reply to maintain proper post boundaries.
        """
        app, post_id, admin_id = self.create_app_and_db(enable_threading=True)
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Create second post
            second_post = Post(
                title='Second Test Post',
                content='Second test content',
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            db.session.add(second_post)
            db.session.commit()
            
            # Submit parent comment on first post
            parent_success, _, parent_comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=parent_data['author_name'],
                author_email=parent_data['author_email'],
                content=parent_data['content']
            )
            
            assert parent_success and parent_comment is not None, "Parent comment should be created"
            approve_success, _ = comment_manager.approve_comment(parent_comment.id, admin_id)
            assert approve_success, "Parent comment should be approved"
            
            # Attempt to reply from second post to first post's comment
            reply_success, reply_message, reply_comment = comment_manager.submit_comment(
                post_id=second_post.id,  # Different post
                author_name=reply_data['author_name'],
                author_email=reply_data['author_email'],
                content=reply_data['content'],
                parent_id=parent_comment.id  # Parent from different post
            )
            
            # Reply should fail validation
            assert not reply_success, "Cross-post reply should fail"
            assert reply_comment is None, "No reply comment should be created"
            assert "different post" in reply_message.lower(), "Error message should mention different post"
    
    def test_nested_reply_depth_handling(self):
        """
        **Property 20: Comment Threading Support (Nested Reply Depth)**
        
        The system should handle nested replies properly, maintaining the
        hierarchical structure even with multiple levels of nesting.
        """
        app, post_id, admin_id = self.create_app_and_db(enable_threading=True)
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Create a chain of nested replies
            comments = []
            
            # Root comment
            root_success, _, root_comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name='Root User',
                author_email='root@example.com',
                content='Root comment'
            )
            
            assert root_success and root_comment is not None, "Root comment should be created"
            approve_success, _ = comment_manager.approve_comment(root_comment.id, admin_id)
            assert approve_success, "Root comment should be approved"
            comments.append(root_comment)
            
            # Create nested replies (reply to previous comment)
            for i in range(3):
                parent_comment = comments[-1]
                reply_success, _, reply_comment = comment_manager.submit_comment(
                    post_id=post_id,
                    author_name=f'Reply User {i+1}',
                    author_email=f'reply{i+1}@example.com',
                    content=f'Reply level {i+1}',
                    parent_id=parent_comment.id
                )
                
                assert reply_success and reply_comment is not None, f"Reply {i+1} should be created"
                reply_approve_success, _ = comment_manager.approve_comment(reply_comment.id, admin_id)
                assert reply_approve_success, f"Reply {i+1} should be approved"
                comments.append(reply_comment)
            
            # Verify parent-child relationships
            for i in range(1, len(comments)):
                child_comment = comments[i]
                parent_comment = comments[i-1]
                
                db.session.refresh(child_comment)
                assert child_comment.parent_id == parent_comment.id, f"Comment {i} should have correct parent"
            
            # Get comment tree and verify structure
            comment_tree = comment_manager.get_comment_tree(post_id)
            
            # Should have one root comment
            assert len(comment_tree) == 1, "Should have one root comment"
            
            # Navigate through nested structure
            current_level = comment_tree[0]
            assert current_level['id'] == root_comment.id, "Root should be correct"
            
            # Each level should have one reply
            for i in range(1, len(comments)):
                assert 'replies' in current_level, f"Level {i-1} should have replies"
                assert len(current_level['replies']) == 1, f"Level {i-1} should have exactly one reply"
                
                current_level = current_level['replies'][0]
                assert current_level['id'] == comments[i].id, f"Level {i} should have correct comment"


if __name__ == '__main__':
    pytest.main([__file__])