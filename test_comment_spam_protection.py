"""
Property-based test for comment spam protection.

**Feature: blog-comprehensive-features, Property 18: Comment Spam Protection**
**Validates: Requirements 5.7**

This module tests that for any comment submission, it should be processed through 
spam detection filters before entering the moderation queue.
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
def spam_comment_data(draw):
    """Generate comment data that should trigger spam detection."""
    spam_type = draw(st.sampled_from(['keywords', 'links', 'caps', 'repeated_chars', 'suspicious_email']))
    
    base_name = draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    base_email = 'test@example.com'
    base_content = draw(st.text(min_size=10, max_size=100).filter(lambda x: x.strip()))
    
    assume(len(base_name) > 0 and len(base_content) > 0)
    
    if spam_type == 'keywords':
        # Include spam keywords
        spam_keywords = ['viagra', 'casino', 'lottery', 'winner', 'free money', 'click here']
        keyword = draw(st.sampled_from(spam_keywords))
        return {
            'author_name': base_name,
            'author_email': base_email,
            'content': f'{base_content} {keyword} more text',
            'expected_spam': True,
            'spam_reason': 'keywords'
        }
    elif spam_type == 'links':
        # Include excessive links
        links = ['http://spam1.com', 'https://spam2.com', 'http://spam3.com', 'https://spam4.com']
        content_with_links = f'{base_content} {' '.join(links)}'
        return {
            'author_name': base_name,
            'author_email': base_email,
            'content': content_with_links,
            'expected_spam': True,
            'spam_reason': 'excessive_links'
        }
    elif spam_type == 'caps':
        # Excessive capitalization
        caps_content = base_content.upper()
        return {
            'author_name': base_name,
            'author_email': base_email,
            'content': caps_content,
            'expected_spam': True,
            'spam_reason': 'excessive_caps'
        }
    elif spam_type == 'repeated_chars':
        # Repeated characters
        repeated_content = f'{base_content} aaaaaaa bbbbbbbb'
        return {
            'author_name': base_name,
            'author_email': base_email,
            'content': repeated_content,
            'expected_spam': True,
            'spam_reason': 'repeated_chars'
        }
    else:  # suspicious_email
        # Suspicious email with many numbers
        suspicious_email = '12345678@example.com'
        return {
            'author_name': base_name,
            'author_email': suspicious_email,
            'content': base_content,
            'expected_spam': True,
            'spam_reason': 'suspicious_email'
        }


@composite
def legitimate_comment_data(draw):
    """Generate comment data that should NOT trigger spam detection."""
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
    
    # Generate clean content without spam indicators
    content = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Po')),
        min_size=10, max_size=500
    ).filter(lambda x: x.strip()))
    
    # Ensure content doesn't accidentally contain spam keywords
    spam_keywords = ['viagra', 'casino', 'lottery', 'winner', 'free money', 'click here']
    content_lower = content.lower()
    assume(not any(keyword in content_lower for keyword in spam_keywords))
    
    # Ensure not too many links
    link_count = content.count('http://') + content.count('https://')
    assume(link_count <= 1)
    
    # Ensure not excessive caps
    if len(content) > 20:
        caps_ratio = sum(1 for c in content if c.isupper()) / len(content)
        assume(caps_ratio < 0.5)
    
    # Ensure all fields are non-empty after stripping
    assume(len(author_name) > 0)
    assume(len(content) > 0)
    assume('@' in author_email and '.' in author_email)
    
    return {
        'author_name': author_name,
        'author_email': author_email,
        'content': content,
        'expected_spam': False,
        'spam_reason': 'none'
    }


class TestCommentSpamProtection:
    """Test suite for comment spam protection property."""
    
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
    
    @given(comment_data=spam_comment_data())
    @settings(max_examples=15, deadline=3000)
    def test_spam_detection_triggers(self, comment_data):
        """
        **Property 18: Comment Spam Protection (Spam Detection)**
        
        For any comment submission containing spam indicators, the spam detection
        system should identify it and mark it appropriately.
        """
        app, post_id, admin_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Test spam detection directly
            is_spam = comment_manager.check_spam({
                'author_name': comment_data['author_name'],
                'author_email': comment_data['author_email'],
                'content': comment_data['content']
            })
            
            # Verify spam detection works
            assert is_spam == comment_data['expected_spam'], \
                f"Spam detection should identify spam content (reason: {comment_data['spam_reason']})"
            
            # Submit comment and verify spam handling
            success, message, comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=comment_data['author_name'],
                author_email=comment_data['author_email'],
                content=comment_data['content']
            )
            
            # Comment submission should still succeed but be marked as spam
            assert success, "Comment submission should succeed even for spam"
            assert comment is not None, "Comment object should be created"
            
            # Verify spam comment is marked correctly
            if comment_data['expected_spam']:
                assert comment.is_spam, "Spam comment should be marked as spam"
                assert not comment.is_approved, "Spam comment should not be auto-approved"
                
                # Verify spam comment doesn't appear in pending moderation
                pending_comments = comment_manager.get_pending_comments()
                assert comment not in pending_comments, "Spam comment should not appear in pending queue"
                
                # Verify spam comment doesn't appear in approved comments
                approved_comments = comment_manager.get_approved_comments(post_id)
                assert comment not in approved_comments, "Spam comment should not appear in approved list"
    
    @given(comment_data=legitimate_comment_data())
    @settings(max_examples=15, deadline=3000)
    def test_legitimate_comments_pass_spam_filter(self, comment_data):
        """
        **Property 18: Comment Spam Protection (False Positive Prevention)**
        
        For any legitimate comment submission without spam indicators, the spam
        detection system should not flag it as spam.
        """
        app, post_id, admin_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Test spam detection directly
            is_spam = comment_manager.check_spam({
                'author_name': comment_data['author_name'],
                'author_email': comment_data['author_email'],
                'content': comment_data['content']
            })
            
            # Verify legitimate content is not flagged as spam
            assert not is_spam, "Legitimate comment should not be flagged as spam"
            
            # Submit comment and verify normal handling
            success, message, comment = comment_manager.submit_comment(
                post_id=post_id,
                author_name=comment_data['author_name'],
                author_email=comment_data['author_email'],
                content=comment_data['content']
            )
            
            # Comment submission should succeed
            assert success, "Legitimate comment submission should succeed"
            assert comment is not None, "Comment object should be created"
            
            # Verify legitimate comment is not marked as spam
            assert not comment.is_spam, "Legitimate comment should not be marked as spam"
            assert not comment.is_approved, "Comment should still require moderation"
            
            # Verify legitimate comment appears in pending moderation
            pending_comments = comment_manager.get_pending_comments()
            assert comment in pending_comments, "Legitimate comment should appear in pending queue"
            
            # Verify legitimate comment doesn't appear in approved comments yet
            approved_comments = comment_manager.get_approved_comments(post_id)
            assert comment not in approved_comments, "Unapproved comment should not appear in approved list"
    
    @given(st.lists(st.one_of(spam_comment_data(), legitimate_comment_data()), min_size=2, max_size=5))
    @settings(max_examples=10, deadline=3000)
    def test_mixed_comment_spam_filtering(self, comments_data):
        """
        **Property 18: Comment Spam Protection (Mixed Content Filtering)**
        
        For any mix of spam and legitimate comments, the spam detection system
        should correctly classify each comment independently.
        """
        app, post_id, admin_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            submitted_comments = []
            expected_spam_count = 0
            expected_legitimate_count = 0
            
            # Submit all comments
            for i, comment_data in enumerate(comments_data):
                success, message, comment = comment_manager.submit_comment(
                    post_id=post_id,
                    author_name=f"{comment_data['author_name']} {i}",
                    author_email=comment_data['author_email'],
                    content=comment_data['content']
                )
                
                assert success and comment is not None, f"Comment {i} submission should succeed"
                submitted_comments.append((comment, comment_data['expected_spam']))
                
                if comment_data['expected_spam']:
                    expected_spam_count += 1
                else:
                    expected_legitimate_count += 1
            
            # Verify spam classification for each comment
            actual_spam_count = 0
            actual_legitimate_count = 0
            
            for comment, expected_spam in submitted_comments:
                if expected_spam:
                    assert comment.is_spam, f"Comment {comment.id} should be marked as spam"
                    actual_spam_count += 1
                else:
                    assert not comment.is_spam, f"Comment {comment.id} should not be marked as spam"
                    actual_legitimate_count += 1
            
            # Verify counts match expectations
            assert actual_spam_count == expected_spam_count, "Spam count should match expected"
            assert actual_legitimate_count == expected_legitimate_count, "Legitimate count should match expected"
            
            # Verify pending queue only contains legitimate comments
            pending_comments = comment_manager.get_pending_comments()
            assert len(pending_comments) == expected_legitimate_count, \
                "Pending queue should only contain legitimate comments"
            
            for comment in pending_comments:
                assert not comment.is_spam, "Pending comments should not be marked as spam"
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=10, deadline=3000)
    def test_spam_detection_robustness(self, random_content):
        """
        **Property 18: Comment Spam Protection (Robustness)**
        
        For any random content input, the spam detection system should handle
        it gracefully without errors or exceptions.
        """
        app, post_id, admin_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Test spam detection with random content
            try:
                is_spam = comment_manager.check_spam({
                    'author_name': 'Test User',
                    'author_email': 'test@example.com',
                    'content': random_content
                })
                
                # Spam detection should return a boolean
                assert isinstance(is_spam, bool), "Spam detection should return boolean"
                
                # Should not raise any exceptions
                spam_detection_works = True
                
            except Exception as e:
                spam_detection_works = False
                print(f"Spam detection failed with: {e}")
            
            assert spam_detection_works, "Spam detection should handle any input gracefully"
    
    def test_spam_keyword_detection(self):
        """
        **Property 18: Comment Spam Protection (Keyword Detection)**
        
        The spam detection system should correctly identify known spam keywords
        in comment content and author names.
        """
        app, post_id, admin_id = self.create_app_and_db()
        
        with app.app_context():
            comment_manager = CommentManager(app)
            
            # Test known spam keywords
            spam_keywords = ['viagra', 'casino', 'lottery', 'winner', 'free money', 'click here']
            
            for keyword in spam_keywords:
                # Test keyword in content
                is_spam_content = comment_manager.check_spam({
                    'author_name': 'Test User',
                    'author_email': 'test@example.com',
                    'content': f'This is a test with {keyword} in it'
                })
                
                assert is_spam_content, f"Content with '{keyword}' should be detected as spam"
                
                # Test keyword in author name
                is_spam_name = comment_manager.check_spam({
                    'author_name': f'{keyword} user',
                    'author_email': 'test@example.com',
                    'content': 'This is normal content'
                })
                
                assert is_spam_name, f"Author name with '{keyword}' should be detected as spam"


if __name__ == '__main__':
    pytest.main([__file__])