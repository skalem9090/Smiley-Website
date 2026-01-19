"""
Property-based test for comment administrative actions.

**Feature: blog-comprehensive-features, Property 19: Comment Administrative Actions**
**Validates: Requirements 5.8**

This module tests that for any comment in the moderation queue, administrators 
should be able to approve, reject, or delete it through the dashboard.
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


class TestCommentAdministrativeActions:
    """Test suite for comment administrative actions property."""
    
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
            
            # Create test users for moderation
            admin_user1 = User(username='admin1', is_admin=True)
            admin_user1.set_password('password')
            db.session.add(admin_user1)
            
            admin_user2 = User(username='admin2', is_admin=True)
            admin_user2.set_password('password')
            db.session.add(admin_user2)
            
            # Create a test post
            test_post = Post(
                title='Test Post',
                content='Test content',
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            db.session.add(test_post)
            db.session.commit()
            
        return app, test_post.id, admin_user1.id, admin_user2.id
    
    @given(comment_data=valid_comment_data())
    @settings(max_examples=15, deadline=3000)
    def test_comment_approval_administrative_action(self, comment_data):
        """
        **Property 19: Comment Administrative Actions (Approval)**
        
        For any comment in the moderation queue, administrators should be able
        to approve it, changing its status and making it visible.
        """
        app, post_id, admin1_id, admin2_id = self.create_app_and_db()
        
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
            assert not comment.is_approved, "Comment should not be approved initially"
            
            # Verify comment is in moderation queue
            pending_comments = comment_manager.get_pending_comments()
            assert comment in pending_comments, "Comment should be in moderation queue"
            
            # Administrator approves the comment
            approve_success, approve_message = comment_manager.approve_comment(comment.id, admin1_id)
            
            # Verify approval action succeeded
            assert approve_success, f"Comment approval should succeed: {approve_message}"
            
            # Refresh comment from database
            db.session.refresh(comment)
            
            # Verify comment state after approval
            assert comment.is_approved, "Comment should be approved after admin action"
            assert comment.approved_by == admin1_id, "Comment should record which admin approved it"
            assert comment.approved_at is not None, "Comment should have approval timestamp"
            assert not comment.is_spam, "Approved comment should not be marked as spam"
            
            # Verify comment visibility changes
            approved_comments = comment_manager.get_approved_comments(post_id)
            pending_comments_after = comment_manager.get_pending_comments()
            
            assert comment in approved_comments, "Approved comment should appear in public display"
            assert comment not in pending_comments_after, "Approved comment should be removed from moderation queue"
    
    @given(comment_data=valid_comment_data())
    @settings(max_examples=15, deadline=3000)
    def test_comment_rejection_administrative_action(self, comment_data):
        """
        **Property 19: Comment Administrative Actions (Rejection)**
        
        For any comment in the moderation queue, administrators should be able
        to reject it, preventing it from being displayed publicly.
        """
        app, post_id, admin1_id, admin2_id = self.create_app_and_db()
        
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
            
            # Administrator rejects the comment
            reject_success, reject_message = comment_manager.reject_comment(
                comment.id, admin2_id, mark_as_spam=True
            )
            
            # Verify rejection action succeeded
            assert reject_success, f"Comment rejection should succeed: {reject_message}"
            
            # Refresh comment from database
            db.session.refresh(comment)
            
            # Verify comment state after rejection
            assert not comment.is_approved, "Comment should not be approved after rejection"
            assert comment.is_spam, "Rejected comment should be marked as spam"
            assert comment.approved_by == admin2_id, "Comment should record which admin rejected it"
            assert comment.approved_at is not None, "Comment should have moderation timestamp"
            
            # Verify comment visibility
            approved_comments = comment_manager.get_approved_comments(post_id)
            pending_comments = comment_manager.get_pending_comments()
            
            assert comment not in approved_comments, "Rejected comment should not appear in public display"
            assert comment not in pending_comments, "Rejected comment should not appear in moderation queue"
    
    @given(comment_data=valid_comment_data())
    @settings(max_examples=10, deadline=3000)
    def test_comment_deletion_administrative_action(self, comment_data):
        """
        **Property 19: Comment Administrative Actions (Deletion)**
        
        For any comment in the moderation queue, administrators should be able
        to delete it permanently from the system.
        """
        app, post_id, admin1_id, admin2_id = self.create_app_and_db()
        
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
            comment_id = comment.id
            
            # Administrator deletes the comment
            delete_success, delete_message = comment_manager.delete_comment(comment_id, admin1_id)
            
            # Verify deletion action succeeded
            assert delete_success, f"Comment deletion should succeed: {delete_message}"
            
            # Verify comment is completely removed from database
            deleted_comment = Comment.query.get(comment_id)
            assert deleted_comment is None, "Deleted comment should not exist in database"
            
            # Verify comment doesn't appear anywhere
            approved_comments = comment_manager.get_approved_comments(post_id)
            pending_comments = comment_manager.get_pending_comments()
            
            assert len([c for c in approved_comments if c.id == comment_id]) == 0, \
                "Deleted comment should not appear in approved list"
            assert len([c for c in pending_comments if c.id == comment_id]) == 0, \
                "Deleted comment should not appear in pending list"
    
    @given(st.lists(valid_comment_data(), min_size=3, max_size=6))
    @settings(max_examples=10, deadline=3000)
    def test_bulk_administrative_actions(self, comments_data):
        """
        **Property 19: Comment Administrative Actions (Bulk Operations)**
        
        For any set of comments in the moderation queue, administrators should
        be able to perform bulk actions (approve/reject multiple comments).
        """
        app, post_id, admin1_id, admin2_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit multiple comments
            submitted_comments = []
            for i, comment_data in enumerate(comments_data):
                success, message, comment = comment_manager.submit_comment(
                    post_id=post_id,
                    author_name=f"{comment_data['author_name']} {i}",
                    author_email=comment_data['author_email'],
                    content=f"{comment_data['content']} - Comment {i}"
                )
                
                assert success and comment is not None, f"Comment {i} submission should succeed"
                submitted_comments.append(comment)
            
            # Verify all comments are in moderation queue
            pending_comments = comment_manager.get_pending_comments()
            for comment in submitted_comments:
                assert comment in pending_comments, "All comments should be in moderation queue"
            
            # Split comments for bulk operations
            mid_point = len(submitted_comments) // 2
            comments_to_approve = submitted_comments[:mid_point]
            comments_to_reject = submitted_comments[mid_point:]
            
            # Bulk approve some comments
            approve_ids = [c.id for c in comments_to_approve]
            successful_approvals, failed_approvals = comment_manager.bulk_approve_comments(
                approve_ids, admin1_id
            )
            
            # Verify bulk approval results
            assert successful_approvals == len(comments_to_approve), \
                "All selected comments should be approved"
            assert failed_approvals == 0, "No approvals should fail"
            
            # Bulk reject remaining comments
            reject_ids = [c.id for c in comments_to_reject]
            successful_rejections, failed_rejections = comment_manager.bulk_reject_comments(
                reject_ids, admin2_id, mark_as_spam=True
            )
            
            # Verify bulk rejection results
            assert successful_rejections == len(comments_to_reject), \
                "All selected comments should be rejected"
            assert failed_rejections == 0, "No rejections should fail"
            
            # Verify final states
            approved_comments = comment_manager.get_approved_comments(post_id)
            pending_comments_after = comment_manager.get_pending_comments()
            
            # Check approved comments
            for comment in comments_to_approve:
                db.session.refresh(comment)
                assert comment.is_approved, "Bulk approved comment should be approved"
                assert comment in approved_comments, "Bulk approved comment should appear in approved list"
            
            # Check rejected comments
            for comment in comments_to_reject:
                db.session.refresh(comment)
                assert not comment.is_approved, "Bulk rejected comment should not be approved"
                assert comment.is_spam, "Bulk rejected comment should be marked as spam"
                assert comment not in approved_comments, "Bulk rejected comment should not appear in approved list"
            
            # Verify moderation queue is empty
            assert len(pending_comments_after) == 0, "Moderation queue should be empty after bulk operations"
    
    @given(comment_data=valid_comment_data())
    @settings(max_examples=10, deadline=3000)
    def test_administrative_action_authorization(self, comment_data):
        """
        **Property 19: Comment Administrative Actions (Authorization)**
        
        For any comment administrative action, it should properly record which
        administrator performed the action and when.
        """
        app, post_id, admin1_id, admin2_id = self.create_app_and_db()
        
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
            
            # Record time before action
            action_time_before = datetime.now(timezone.utc)
            
            # Administrator performs action
            approve_success, _ = comment_manager.approve_comment(comment.id, admin1_id)
            assert approve_success, "Comment approval should succeed"
            
            # Record time after action
            action_time_after = datetime.now(timezone.utc)
            
            # Refresh comment from database
            db.session.refresh(comment)
            
            # Verify authorization tracking
            assert comment.approved_by == admin1_id, "Comment should record correct administrator ID"
            assert comment.approved_at is not None, "Comment should have action timestamp"
            
            # Verify timestamp is reasonable
            assert action_time_before <= comment.approved_at <= action_time_after, \
                "Action timestamp should be within reasonable time range"
            
            # Verify original creation time is preserved
            assert comment.created_at == original_created_at, \
                "Original creation timestamp should be preserved"
            
            # Verify different admin can be recorded for different actions
            # Submit another comment
            success2, message2, comment2 = comment_manager.submit_comment(
                post_id=post_id,
                author_name=f"{comment_data['author_name']} 2",
                author_email=comment_data['author_email'],
                content=f"{comment_data['content']} - Second comment"
            )
            
            if success2 and comment2:
                # Different admin rejects this comment
                reject_success, _ = comment_manager.reject_comment(comment2.id, admin2_id, mark_as_spam=True)
                assert reject_success, "Comment rejection should succeed"
                
                db.session.refresh(comment2)
                
                # Verify different admin is recorded
                assert comment2.approved_by == admin2_id, "Second comment should record different admin"
                assert comment2.approved_by != comment.approved_by, "Different admins should be recorded"


if __name__ == '__main__':
    pytest.main([__file__])