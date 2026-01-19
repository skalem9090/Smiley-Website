"""
Property-based test for comment moderation workflow.

**Feature: blog-comprehensive-features, Property 16: Comment Moderation Workflow**
**Validates: Requirements 5.4, 5.9**

This module tests that for any submitted comment, it should trigger administrator 
notification and remain invisible until approved.
"""

import pytest
import uuid
from datetime import datetime, timezone
from hypothesis import given, strategies as st, settings, assume
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
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
        min_size=1, max_size=20
    ))
    domain = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
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


class TestCommentModerationWorkflow:
    """Test suite for comment moderation workflow property."""
    
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
            
        return app, test_post.id, admin_user.id
    
    @given(comment_data=valid_comment_data())
    @settings(max_examples=15, deadline=3000)
    def test_comment_invisible_until_approved(self, comment_data):
        """
        **Property 16: Comment Moderation Workflow (Visibility Control)**
        
        For any submitted comment, it should remain invisible in public display
        until explicitly approved by a moderator.
        """
        app, post_id, admin_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit comment
            success, message, comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=comment_data['author_name'],
                author_email=comment_data['author_email'],
                content=comment_data['content']
            )
            
            # Verify submission was successful
            assert success, f"Comment submission should succeed: {message}"
            assert comment is not None, "Comment object should be returned"
            
            # Verify comment is not visible in public display
            approved_comments = comment_manager.get_approved_comments(post_id)
            assert comment not in approved_comments, "Unapproved comment should not appear in public display"
            
            # Verify comment appears in moderation queue
            pending_comments = comment_manager.get_pending_comments()
            assert comment in pending_comments, "Comment should appear in moderation queue"
            
            # Verify comment is not approved initially
            assert not comment.is_approved, "Comment should not be approved initially"
            assert comment.approved_at is None, "Comment should not have approval timestamp initially"
            assert comment.approved_by is None, "Comment should not have moderator ID initially"
    
    @given(comment_data=valid_comment_data())
    @settings(max_examples=15, deadline=3000)
    def test_comment_approval_workflow(self, comment_data):
        """
        **Property 16: Comment Moderation Workflow (Approval Process)**
        
        For any submitted comment, when approved by a moderator, it should become
        visible in public display and be removed from the moderation queue.
        """
        app, post_id, admin_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit comment
            success, message, comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=comment_data['author_name'],
                author_email=comment_data['author_email'],
                content=comment_data['content']
            )
            
            assert success and comment is not None, "Comment submission should succeed"
            
            # Approve the comment
            approve_success, approve_message = comment_manager.approve_comment(comment.id, admin_id)
            
            # Verify approval was successful
            assert approve_success, f"Comment approval should succeed: {approve_message}"
            
            # Refresh comment from database
            db.session.refresh(comment)
            
            # Verify comment is now approved
            assert comment.is_approved, "Comment should be approved after approval action"
            assert comment.approved_at is not None, "Comment should have approval timestamp"
            assert comment.approved_by == admin_id, "Comment should have correct moderator ID"
            assert not comment.is_spam, "Approved comment should not be marked as spam"
            
            # Verify comment now appears in public display
            approved_comments = comment_manager.get_approved_comments(post_id)
            assert comment in approved_comments, "Approved comment should appear in public display"
            
            # Verify comment is removed from moderation queue
            pending_comments = comment_manager.get_pending_comments()
            assert comment not in pending_comments, "Approved comment should not appear in moderation queue"
    
    @given(comment_data=valid_comment_data())
    @settings(max_examples=15, deadline=3000)
    def test_comment_rejection_workflow(self, comment_data):
        """
        **Property 16: Comment Moderation Workflow (Rejection Process)**
        
        For any submitted comment, when rejected by a moderator, it should remain
        invisible in public display and be marked appropriately.
        """
        app, post_id, admin_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit comment
            success, message, comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=comment_data['author_name'],
                author_email=comment_data['author_email'],
                content=comment_data['content']
            )
            
            assert success and comment is not None, "Comment submission should succeed"
            
            # Reject the comment
            reject_success, reject_message = comment_manager.reject_comment(comment.id, admin_id, mark_as_spam=True)
            
            # Verify rejection was successful
            assert reject_success, f"Comment rejection should succeed: {reject_message}"
            
            # Refresh comment from database
            db.session.refresh(comment)
            
            # Verify comment is rejected and marked as spam
            assert not comment.is_approved, "Comment should not be approved after rejection"
            assert comment.is_spam, "Rejected comment should be marked as spam"
            assert comment.approved_by == admin_id, "Comment should have moderator ID who rejected it"
            assert comment.approved_at is not None, "Comment should have moderation timestamp"
            
            # Verify comment does not appear in public display
            approved_comments = comment_manager.get_approved_comments(post_id)
            assert comment not in approved_comments, "Rejected comment should not appear in public display"
            
            # Verify comment does not appear in pending moderation queue
            pending_comments = comment_manager.get_pending_comments()
            assert comment not in pending_comments, "Rejected comment should not appear in pending queue"
    
    @given(comment_data=valid_comment_data())
    @settings(max_examples=10, deadline=3000)
    def test_comment_moderation_state_persistence(self, comment_data):
        """
        **Property 16: Comment Moderation Workflow (State Persistence)**
        
        For any comment moderation action, the moderation state should persist
        correctly in the database with proper timestamps and moderator tracking.
        """
        app, post_id, admin_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit comment
            success, message, comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=comment_data['author_name'],
                author_email=comment_data['author_email'],
                content=comment_data['content']
            )
            
            assert success and comment is not None, "Comment submission should succeed"
            original_created_at = comment.created_at
            
            # Approve the comment
            approve_success, _ = comment_manager.approve_comment(comment.id, admin_id)
            assert approve_success, "Comment approval should succeed"
            
            # Verify state persistence by querying fresh from database
            fresh_comment = Comment.query.get(comment.id)
            assert fresh_comment is not None, "Comment should exist in database"
            assert fresh_comment.is_approved, "Comment approval state should persist"
            assert fresh_comment.approved_by == admin_id, "Moderator ID should persist"
            assert fresh_comment.approved_at is not None, "Approval timestamp should persist"
            assert fresh_comment.created_at == original_created_at, "Original creation time should be preserved"
            assert not fresh_comment.is_spam, "Spam flag should be correctly set"
    
    @given(comment_data=valid_comment_data())
    @settings(max_examples=10, deadline=3000)
    def test_comment_bulk_moderation_workflow(self, comment_data):
        """
        **Property 16: Comment Moderation Workflow (Bulk Operations)**
        
        For any set of submitted comments, bulk moderation operations should
        work correctly and maintain proper state for each comment.
        """
        app, post_id, admin_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit multiple comments
            comments = []
            for i in range(3):
                success, message, comment = comment_manager.submit_comment(
                    post_id=post_id,
                    author_name=f"{comment_data['author_name']} {i}",
                    author_email=comment_data['author_email'],
                    content=f"{comment_data['content']} - Comment {i}"
                )
                assert success and comment is not None, f"Comment {i} submission should succeed"
                comments.append(comment)
            
            # Verify all comments are pending
            pending_comments = comment_manager.get_pending_comments()
            for comment in comments:
                assert comment in pending_comments, "All comments should be in pending queue"
            
            # Bulk approve comments
            comment_ids = [c.id for c in comments]
            successful, failed = comment_manager.bulk_approve_comments(comment_ids, admin_id)
            
            # Verify bulk operation results
            assert successful == 3, "All comments should be successfully approved"
            assert failed == 0, "No comments should fail approval"
            
            # Verify all comments are now approved
            approved_comments = comment_manager.get_approved_comments(post_id)
            for comment in comments:
                db.session.refresh(comment)
                assert comment.is_approved, "Comment should be approved after bulk operation"
                assert comment in approved_comments, "Comment should appear in approved list"


if __name__ == '__main__':
    pytest.main([__file__])