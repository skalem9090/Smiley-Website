"""
Property-based test for comment submission requirements.

**Feature: blog-comprehensive-features, Property 15: Comment Submission Requirements**
**Validates: Requirements 5.1, 5.2, 5.3**

This module tests that for any comment submission, the system should require name, 
email, and content fields and be held for moderation before public display.
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


@composite
def invalid_comment_data(draw):
    """Generate invalid comment data for testing validation."""
    # Choose what to make invalid
    invalid_field = draw(st.sampled_from(['name', 'email', 'content', 'all']))
    
    if invalid_field == 'name':
        return {
            'author_name': '',  # Empty name
            'author_email': 'valid@example.com',
            'content': 'Valid content'
        }
    elif invalid_field == 'email':
        return {
            'author_name': 'Valid Name',
            'author_email': 'invalid-email',  # Invalid email format
            'content': 'Valid content'
        }
    elif invalid_field == 'content':
        return {
            'author_name': 'Valid Name',
            'author_email': 'valid@example.com',
            'content': ''  # Empty content
        }
    else:  # all invalid
        return {
            'author_name': '',
            'author_email': 'invalid',
            'content': ''
        }


class TestCommentSubmissionRequirements:
    """Test suite for comment submission requirements property."""
    
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
            
        return app, test_post.id
    
    @given(comment_data=valid_comment_data())
    @settings(max_examples=20, deadline=3000)
    def test_valid_comment_submission_requires_moderation(self, comment_data):
        """
        **Property 15: Comment Submission Requirements (Valid Submission)**
        
        For any valid comment submission with required fields (name, email, content),
        the comment should be successfully submitted but held for moderation
        (is_approved=False) before public display.
        """
        app, post_id = self.create_app_and_db()
        
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
            assert success, f"Comment submission should succeed with valid data: {message}"
            assert comment is not None, "Comment object should be returned"
            
            # Verify comment is held for moderation
            assert not comment.is_approved, "Comment should not be approved initially"
            assert comment.author_name == comment_data['author_name']
            assert comment.author_email == comment_data['author_email'].lower()
            assert comment.content == comment_data['content']
            assert comment.post_id == post_id
            
            # Verify comment is not visible in approved comments
            approved_comments = comment_manager.get_approved_comments(post_id)
            assert comment not in approved_comments, "Unapproved comment should not appear in approved list"
            
            # Verify comment appears in pending moderation
            pending_comments = comment_manager.get_pending_comments()
            assert comment in pending_comments, "Comment should appear in pending moderation queue"
    
    @given(comment_data=invalid_comment_data())
    @settings(max_examples=15, deadline=3000)
    def test_invalid_comment_submission_fails_validation(self, comment_data):
        """
        **Property 15: Comment Submission Requirements (Invalid Submission)**
        
        For any comment submission missing required fields (name, email, or content),
        the submission should fail validation and not create a comment record.
        """
        app, post_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit invalid comment
            success, message, comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=comment_data['author_name'],
                author_email=comment_data['author_email'],
                content=comment_data['content']
            )
            
            # Verify submission failed
            assert not success, "Comment submission should fail with invalid data"
            assert comment is None, "No comment object should be returned for invalid data"
            assert len(message) > 0, "Error message should be provided"
            
            # Verify no comment was created in database
            total_comments = Comment.query.count()
            assert total_comments == 0, "No comment should be created with invalid data"
    
    @given(
        comment_data=valid_comment_data(),
        ip_address=st.one_of(st.none(), st.ip_addresses(v=4).map(str)),
        user_agent=st.one_of(st.none(), st.text(max_size=255))
    )
    @settings(max_examples=15, deadline=3000)
    def test_comment_metadata_storage(self, comment_data, ip_address, user_agent):
        """
        **Property 15: Comment Submission Requirements (Metadata Storage)**
        
        For any comment submission, the system should store optional metadata
        (IP address, user agent) for spam detection and moderation purposes.
        """
        app, post_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit comment with metadata
            success, message, comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=comment_data['author_name'],
                author_email=comment_data['author_email'],
                content=comment_data['content'],
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Verify submission was successful
            assert success, f"Comment submission should succeed: {message}"
            assert comment is not None, "Comment object should be returned"
            
            # Verify metadata is stored correctly
            assert comment.ip_address == ip_address
            assert comment.user_agent == user_agent
            
            # Verify timestamp is set
            assert comment.created_at is not None
            assert isinstance(comment.created_at, datetime)
    
    @given(comment_data=valid_comment_data())
    @settings(max_examples=10, deadline=3000)
    def test_comment_requires_published_post(self, comment_data):
        """
        **Property 15: Comment Submission Requirements (Published Post Only)**
        
        For any comment submission, comments should only be allowed on published posts,
        not on draft or scheduled posts.
        """
        app, _ = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Create a draft post
            draft_post = Post(
                title='Draft Post',
                content='Draft content',
                status='draft'
            )
            db.session.add(draft_post)
            db.session.commit()
            
            # Try to submit comment on draft post
            success, message, comment = comment_manager.submit_comment(
                post_id=draft_post.id,
                author_name=comment_data['author_name'],
                author_email=comment_data['author_email'],
                content=comment_data['content']
            )
            
            # Verify submission failed
            assert not success, "Comment submission should fail on unpublished post"
            assert comment is None, "No comment should be created on unpublished post"
            assert "not allowed" in message.lower() or "unpublished" in message.lower()
    
    @given(comment_data=valid_comment_data())
    @settings(max_examples=10, deadline=3000)
    def test_comment_email_normalization(self, comment_data):
        """
        **Property 15: Comment Submission Requirements (Email Normalization)**
        
        For any comment submission, email addresses should be normalized to lowercase
        for consistent storage and comparison.
        """
        app, post_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Submit comment with mixed case email
            mixed_case_email = comment_data['author_email'].upper()
            
            success, message, comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=comment_data['author_name'],
                author_email=mixed_case_email,
                content=comment_data['content']
            )
            
            # Verify submission was successful
            assert success, f"Comment submission should succeed: {message}"
            assert comment is not None, "Comment object should be returned"
            
            # Verify email is normalized to lowercase
            assert comment.author_email == mixed_case_email.lower()
            assert comment.author_email.islower()
    
    @given(
        comment_data=valid_comment_data(),
        content_length=st.integers(min_value=2001, max_value=5000)
    )
    @settings(max_examples=10, deadline=3000)
    def test_comment_length_validation(self, comment_data, content_length):
        """
        **Property 15: Comment Submission Requirements (Length Validation)**
        
        For any comment submission with content exceeding the maximum length,
        the submission should fail validation.
        """
        app, post_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Create content that exceeds maximum length
            long_content = 'x' * content_length
            
            success, message, comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=comment_data['author_name'],
                author_email=comment_data['author_email'],
                content=long_content
            )
            
            # Verify submission failed due to length
            assert not success, "Comment submission should fail with content too long"
            assert comment is None, "No comment should be created with content too long"
            assert "too long" in message.lower() or "maximum" in message.lower()


if __name__ == '__main__':
    pytest.main([__file__])