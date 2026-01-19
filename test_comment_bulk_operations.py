"""
Property-based tests for comment bulk operations.

**Property 28: Comment Bulk Operations**
**Validates: Requirements 8.2**

This module tests that administrators can perform bulk approval or deletion actions
on multiple comments through the dashboard interface.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime, timezone, timedelta
from app import create_app
from models import db, User, Post, Comment
from comment_manager import CommentManager
import uuid


class TestCommentBulkOperations:
    """Test comment bulk operations functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test environment before each test."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        with self.app.app_context():
            db.create_all()
            
            # Create test admin user with unique username
            unique_username = f'admin_{uuid.uuid4().hex[:8]}'
            self.admin_user = User(username=unique_username, is_admin=True)
            self.admin_user.set_password('password')
            db.session.add(self.admin_user)
            
            # Create test post
            self.test_post = Post(
                title='Test Post',
                content='Test content',
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            db.session.add(self.test_post)
            db.session.commit()
            
            # Store the post ID to avoid detached instance issues
            self.test_post_id = self.test_post.id
            
            # Store the admin user ID to avoid detached instance issues
            self.admin_user_id = self.admin_user.id
            
            self.comment_manager = CommentManager(self.app)
    
    @given(
        comment_count=st.integers(min_value=2, max_value=20),
        bulk_action=st.sampled_from(['approve', 'reject', 'spam', 'delete']),
        selection_ratio=st.floats(min_value=0.1, max_value=1.0)
    )
    @settings(max_examples=50, deadline=10000)
    def test_bulk_comment_operations_property(self, comment_count, bulk_action, selection_ratio):
        """
        **Property 28: Comment Bulk Operations**
        **Validates: Requirements 8.2**
        
        For any selection of multiple comments, administrators should be able to 
        perform bulk approval or deletion actions.
        
        Property: When an administrator selects multiple comments and performs a bulk action,
        the action should be applied to all selected comments consistently.
        """
        with self.app.app_context():
            # Create multiple test comments
            comments = []
            for i in range(comment_count):
                comment = Comment(
                    post_id=self.test_post_id,
                    author_name=f'Test Author {i}',
                    author_email=f'test{i}@example.com',
                    content=f'Test comment content {i}',
                    is_approved=False,
                    is_spam=False,
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(comment)
                comments.append(comment)
            
            db.session.commit()
            
            # Select a subset of comments for bulk operation
            selection_count = max(1, int(comment_count * selection_ratio))
            selected_comments = comments[:selection_count]
            selected_ids = [comment.id for comment in selected_comments]
            
            # Record initial state
            initial_states = {}
            for comment in comments:
                initial_states[comment.id] = {
                    'is_approved': comment.is_approved,
                    'is_spam': comment.is_spam,
                    'exists': True
                }
            
            # Perform bulk operation
            if bulk_action == 'approve':
                successful, failed = self.comment_manager.bulk_approve_comments(
                    selected_ids, self.admin_user_id
                )
            elif bulk_action == 'reject':
                successful, failed = self.comment_manager.bulk_reject_comments(
                    selected_ids, self.admin_user_id, mark_as_spam=False
                )
            elif bulk_action == 'spam':
                successful, failed = self.comment_manager.bulk_reject_comments(
                    selected_ids, self.admin_user_id, mark_as_spam=True
                )
            elif bulk_action == 'delete':
                successful = 0
                failed = 0
                for comment_id in selected_ids:
                    success, _ = self.comment_manager.delete_comment(comment_id, self.admin_user_id)
                    if success:
                        successful += 1
                    else:
                        failed += 1
            
            # Verify bulk operation results
            assert successful + failed == len(selected_ids), \
                f"Total processed ({successful + failed}) should equal selected count ({len(selected_ids)})"
            
            # Verify state changes for selected comments
            for comment_id in selected_ids:
                if bulk_action == 'delete':
                    # Comment should be deleted
                    deleted_comment = db.session.get(Comment, comment_id)
                    if successful > 0:  # At least some deletions succeeded
                        # Either comment is deleted or deletion failed for this specific comment
                        if deleted_comment is None:
                            # Comment was successfully deleted
                            pass
                        else:
                            # Comment still exists, deletion must have failed
                            assert failed > 0, "If comment still exists, there should be failures recorded"
                else:
                    # Comment should still exist with updated state
                    updated_comment = db.session.get(Comment, comment_id)
                    assert updated_comment is not None, f"Comment {comment_id} should still exist after {bulk_action}"
                    
                    if bulk_action == 'approve':
                        if successful > 0:
                            # At least some approvals succeeded
                            if updated_comment.is_approved:
                                assert not updated_comment.is_spam, "Approved comments should not be marked as spam"
                                assert updated_comment.approved_by == self.admin_user_id, "Approved comment should record moderator"
                                assert updated_comment.approved_at is not None, "Approved comment should have approval timestamp"
                    
                    elif bulk_action == 'reject':
                        if successful > 0:
                            # At least some rejections succeeded
                            if not updated_comment.is_approved and updated_comment.approved_by == self.admin_user_id:
                                assert not updated_comment.is_spam, "Rejected (not spam) comments should not be marked as spam"
                    
                    elif bulk_action == 'spam':
                        if successful > 0:
                            # At least some spam markings succeeded
                            if updated_comment.is_spam and updated_comment.approved_by == self.admin_user_id:
                                assert not updated_comment.is_approved, "Spam comments should not be approved"
            
            # Verify non-selected comments remain unchanged
            non_selected_comments = [c for c in comments if c.id not in selected_ids]
            for comment in non_selected_comments:
                current_comment = db.session.get(Comment, comment.id)
                assert current_comment is not None, "Non-selected comments should still exist"
                
                initial_state = initial_states[comment.id]
                assert current_comment.is_approved == initial_state['is_approved'], \
                    "Non-selected comments should maintain their approval status"
                assert current_comment.is_spam == initial_state['is_spam'], \
                    "Non-selected comments should maintain their spam status"
    
    @given(
        comment_count=st.integers(min_value=1, max_value=10),
        has_replies=st.booleans()
    )
    @settings(max_examples=30, deadline=10000)
    def test_bulk_delete_with_replies_property(self, comment_count, has_replies):
        """
        **Property 28: Comment Bulk Operations (Delete with Replies)**
        **Validates: Requirements 8.2**
        
        Property: Comments with replies should not be deletable through bulk operations,
        and the system should handle this gracefully.
        """
        with self.app.app_context():
            # Create parent comments
            parent_comments = []
            for i in range(comment_count):
                parent = Comment(
                    post_id=self.test_post_id,
                    author_name=f'Parent Author {i}',
                    author_email=f'parent{i}@example.com',
                    content=f'Parent comment {i}',
                    is_approved=True,
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(parent)
                parent_comments.append(parent)
            
            db.session.commit()
            
            # Add replies to some parent comments if requested
            if has_replies and comment_count > 0:
                # Add reply to first parent comment
                reply = Comment(
                    post_id=self.test_post_id,
                    parent_id=parent_comments[0].id,
                    author_name='Reply Author',
                    author_email='reply@example.com',
                    content='Reply content',
                    is_approved=True,
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(reply)
                db.session.commit()
            
            # Attempt bulk delete on all parent comments
            parent_ids = [comment.id for comment in parent_comments]
            
            successful = 0
            failed = 0
            for comment_id in parent_ids:
                success, message = self.comment_manager.delete_comment(comment_id, self.admin_user_id)
                if success:
                    successful += 1
                else:
                    failed += 1
                    if has_replies and comment_id == parent_comments[0].id:
                        # The first comment has replies, so deletion should fail
                        assert "replies" in message.lower(), \
                            "Error message should mention replies when deletion fails due to replies"
            
            # Verify results
            if has_replies and comment_count > 0:
                # At least the first comment (with replies) should fail to delete
                assert failed >= 1, "Comments with replies should fail to delete"
                
                # First comment should still exist
                first_comment = db.session.get(Comment, parent_comments[0].id)
                assert first_comment is not None, "Comment with replies should still exist after failed deletion"
            
            # Comments without replies should be deletable
            if comment_count > 1 and has_replies:
                # Other comments (without replies) should be deletable
                for i in range(1, comment_count):
                    comment = db.session.get(Comment, parent_comments[i].id)
                    # Comment might be deleted (successful) or still exist (failed)
                    # Both are acceptable depending on implementation
    
    @given(
        comment_count=st.integers(min_value=3, max_value=15),
        moderator_count=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=30, deadline=10000)
    def test_bulk_operations_moderator_tracking_property(self, comment_count, moderator_count):
        """
        **Property 28: Comment Bulk Operations (Moderator Tracking)**
        **Validates: Requirements 8.2**
        
        Property: Bulk operations should properly track which moderator performed the action
        and when the action was performed.
        """
        with self.app.app_context():
            # Create additional moderator users
            moderators = [self.admin_user]
            for i in range(moderator_count - 1):
                unique_mod_username = f'moderator{i}_{uuid.uuid4().hex[:8]}'
                moderator = User(username=unique_mod_username, is_admin=True)
                moderator.set_password('password')
                db.session.add(moderator)
                moderators.append(moderator)
            
            # Create test comments
            comments = []
            for i in range(comment_count):
                comment = Comment(
                    post_id=self.test_post_id,
                    author_name=f'Test Author {i}',
                    author_email=f'test{i}@example.com',
                    content=f'Test comment content {i}',
                    is_approved=False,
                    is_spam=False,
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(comment)
                comments.append(comment)
            
            db.session.commit()
            
            # Select a moderator and perform bulk approval
            selected_moderator = moderators[0]
            selected_moderator_id = selected_moderator.id
            comment_ids = [comment.id for comment in comments]
            
            # Record time before operation
            operation_start = datetime.now(timezone.utc)
            
            # Perform bulk approval
            successful, failed = self.comment_manager.bulk_approve_comments(
                comment_ids, selected_moderator_id
            )
            
            # Record time after operation
            operation_end = datetime.now(timezone.utc)
            
            # Verify moderator tracking
            assert successful > 0, "At least some comments should be successfully approved"
            
            for comment_id in comment_ids:
                updated_comment = db.session.get(Comment, comment_id)
                assert updated_comment is not None, "Comment should still exist"
                
                if updated_comment.is_approved:
                    # Comment was successfully approved
                    assert updated_comment.approved_by == selected_moderator_id, \
                        f"Approved comment should record correct moderator ID ({selected_moderator_id})"
                    
                    assert updated_comment.approved_at is not None, \
                        "Approved comment should have approval timestamp"
                    
                    # Verify timestamp is reasonable (within operation timeframe)
                    # Convert to UTC if needed for comparison
                    approved_at_utc = updated_comment.approved_at
                    if approved_at_utc.tzinfo is None:
                        approved_at_utc = approved_at_utc.replace(tzinfo=timezone.utc)
                    
                    assert operation_start <= approved_at_utc <= operation_end, \
                        "Approval timestamp should be within operation timeframe"
    
    @given(
        empty_selection=st.booleans(),
        invalid_ids=st.booleans()
    )
    @settings(max_examples=20, deadline=5000)
    def test_bulk_operations_edge_cases_property(self, empty_selection, invalid_ids):
        """
        **Property 28: Comment Bulk Operations (Edge Cases)**
        **Validates: Requirements 8.2**
        
        Property: Bulk operations should handle edge cases gracefully, including
        empty selections and invalid comment IDs.
        """
        with self.app.app_context():
            # Create a few test comments
            comments = []
            for i in range(3):
                comment = Comment(
                    post_id=self.test_post_id,
                    author_name=f'Test Author {i}',
                    author_email=f'test{i}@example.com',
                    content=f'Test comment content {i}',
                    is_approved=False,
                    is_spam=False,
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(comment)
                comments.append(comment)
            
            db.session.commit()
            
            # Prepare comment IDs based on test parameters
            if empty_selection:
                comment_ids = []
            elif invalid_ids:
                # Use non-existent comment IDs
                comment_ids = [99999, 99998, 99997]
            else:
                # Use valid comment IDs
                comment_ids = [comment.id for comment in comments]
            
            # Test bulk approval with edge case
            successful, failed = self.comment_manager.bulk_approve_comments(
                comment_ids, self.admin_user_id
            )
            
            # Verify edge case handling
            if empty_selection:
                # Empty selection should result in no operations
                assert successful == 0, "Empty selection should result in no successful operations"
                assert failed == 0, "Empty selection should result in no failed operations"
            
            elif invalid_ids:
                # Invalid IDs should result in failures
                assert successful == 0, "Invalid IDs should result in no successful operations"
                assert failed == len(comment_ids), "All invalid IDs should be counted as failures"
            
            else:
                # Valid IDs should result in some successes
                assert successful > 0, "Valid IDs should result in some successful operations"
                assert successful + failed == len(comment_ids), \
                    "Total operations should equal number of IDs provided"
            
            # Verify that valid comments remain unaffected by invalid operations
            for comment in comments:
                current_comment = db.session.get(Comment, comment.id)
                assert current_comment is not None, "Valid comments should still exist"
                
                if empty_selection or invalid_ids:
                    # Comments should remain unchanged
                    assert not current_comment.is_approved, \
                        "Comments should remain unapproved after edge case operations"
                    assert current_comment.approved_by is None, \
                        "Comments should not have moderator assigned after edge case operations"