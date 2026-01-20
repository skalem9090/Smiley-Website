"""
Property tests for newsletter functionality.

This module contains property-based tests that validate the newsletter system's
correctness properties across various scenarios and data inputs.
"""

import pytest
import hypothesis.strategies as st
from hypothesis import given, assume, settings, HealthCheck
from datetime import datetime, timezone, timedelta
import tempfile
import os
from flask import Flask
from models import db, NewsletterSubscription, Post, User
from newsletter_manager import NewsletterManager
import string
import re


@pytest.fixture
def app():
    """Create test Flask app with in-memory database."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['BASE_URL'] = 'http://localhost:5000'
    app.config['NEWSLETTER_FROM_EMAIL'] = 'test@example.com'
    app.config['NEWSLETTER_FROM_NAME'] = 'Test Blog'
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def newsletter_manager(app):
    """Create NewsletterManager instance for testing."""
    with app.app_context():
        return NewsletterManager(app)


# Strategy for generating valid email addresses
email_strategy = st.builds(
    lambda local, domain: f"{local}@{domain}.com",
    local=st.text(alphabet=string.ascii_lowercase + string.digits, min_size=3, max_size=20),
    domain=st.text(alphabet=string.ascii_lowercase, min_size=3, max_size=15)
)

# Strategy for generating frequencies
frequency_strategy = st.sampled_from(['weekly', 'bi-weekly', 'monthly'])

# Strategy for generating post content
post_content_strategy = st.text(
    alphabet=string.ascii_letters + string.digits + string.punctuation + ' \n\t',
    min_size=50,
    max_size=500
)


class TestNewsletterSubscriptionWorkflow:
    """Property 11: Newsletter Subscription Workflow - Validates Requirements 4.2, 4.3"""
    
    @given(
        email=email_strategy,
        frequency=frequency_strategy
    )
    @settings(max_examples=30, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_subscription_creates_unconfirmed_record(self, app, newsletter_manager, email, frequency):
        """Property: Subscription must create an unconfirmed record with tokens."""
        with app.app_context():
            success, message, subscription = newsletter_manager.subscribe_email(
                email=email,
                frequency=frequency,
                ip_address='127.0.0.1'
            )
            
            # Subscription should be created successfully (even without SendGrid)
            assert success or "Email service not configured" in message
            
            if success:
                assert subscription is not None
                assert subscription.email == email
                assert subscription.frequency == frequency
                assert not subscription.confirmed
                assert subscription.confirmation_token is not None
                assert subscription.unsubscribe_token is not None
                assert subscription.subscribed_at is not None
                
                # Verify record exists in database
                db_subscription = NewsletterSubscription.query.filter_by(email=email).first()
                assert db_subscription is not None
                assert db_subscription.id == subscription.id
    
    @given(
        email=email_strategy,
        frequency=frequency_strategy
    )
    @settings(max_examples=20, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_duplicate_subscription_handling(self, app, newsletter_manager, email, frequency):
        """Property: Duplicate subscriptions must be handled gracefully."""
        with app.app_context():
            # First subscription
            success1, message1, subscription1 = newsletter_manager.subscribe_email(
                email=email,
                frequency=frequency
            )
            
            # Second subscription with same email
            success2, message2, subscription2 = newsletter_manager.subscribe_email(
                email=email,
                frequency='monthly'  # Different frequency
            )
            
            if success1:
                # Should not create duplicate
                assert "already subscribed" in message2.lower() or "confirmation email resent" in message2.lower()
                
                # Should be same subscription record
                if subscription2:
                    assert subscription1.id == subscription2.id
                
                # Only one record should exist
                count = NewsletterSubscription.query.filter_by(email=email).count()
                assert count == 1
    
    @given(
        email=email_strategy,
        frequency=frequency_strategy
    )
    @settings(max_examples=20, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_confirmation_workflow(self, app, newsletter_manager, email, frequency):
        """Property: Confirmation must properly activate subscription."""
        with app.app_context():
            # Subscribe
            success, message, subscription = newsletter_manager.subscribe_email(
                email=email,
                frequency=frequency
            )
            
            assume(success and subscription is not None)
            
            # Confirm subscription
            token = subscription.confirmation_token
            confirm_success, confirm_message, confirmed_sub = newsletter_manager.confirm_subscription(token)
            
            assert confirm_success
            assert confirmed_sub is not None
            assert confirmed_sub.confirmed
            assert confirmed_sub.confirmed_at is not None
            assert confirmed_sub.confirmation_token is None  # Token should be cleared
            
            # Verify in database
            db_subscription = NewsletterSubscription.query.filter_by(email=email).first()
            assert db_subscription.confirmed
            assert db_subscription.confirmed_at is not None
    
    @given(
        email=email_strategy,
        frequency=frequency_strategy
    )
    @settings(max_examples=15, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_confirmation_token(self, app, newsletter_manager, email, frequency):
        """Property: Invalid confirmation tokens must be rejected."""
        with app.app_context():
            # Try to confirm with invalid token
            invalid_token = "invalid_token_12345"
            success, message, subscription = newsletter_manager.confirm_subscription(invalid_token)
            
            assert not success
            assert "invalid" in message.lower()
            assert subscription is None


class TestNewsletterDigestGeneration:
    """Property 12: Newsletter Digest Generation - Validates Requirements 4.4, 4.6"""
    
    @given(
        frequency=frequency_strategy,
        num_posts=st.integers(min_value=1, max_value=8)
    )
    @settings(max_examples=20, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_digest_includes_recent_posts(self, app, newsletter_manager, frequency, num_posts):
        """Property: Digest must include recent published posts within the frequency period."""
        with app.app_context():
            # Create posts within the frequency period
            now = datetime.now(timezone.utc)
            if frequency == 'weekly':
                start_date = now - timedelta(days=7)
            elif frequency == 'bi-weekly':
                start_date = now - timedelta(days=14)
            else:  # monthly
                start_date = now - timedelta(days=30)
            
            created_posts = []
            for i in range(num_posts):
                # Create posts within the period
                post_date = start_date + timedelta(
                    days=i * (now - start_date).days // num_posts
                )
                
                post = Post(
                    title=f"Test Post {i}",
                    content=f"Content for test post {i} with sufficient length for digest.",
                    status='published',
                    created_at=post_date,
                    published_at=post_date
                )
                created_posts.append(post)
                db.session.add(post)
            
            db.session.commit()
            
            # Generate digest
            success, message, digest_data = newsletter_manager.generate_digest(frequency)
            
            assert success
            assert digest_data is not None
            assert digest_data['frequency'] == frequency
            assert digest_data['total_posts'] == num_posts
            assert len(digest_data['posts']) == num_posts
            
            # Verify all created posts are included
            digest_post_ids = [post['id'] for post in digest_data['posts']]
            for post in created_posts:
                assert post.id in digest_post_ids
    
    @given(
        frequency=frequency_strategy,
        num_old_posts=st.integers(min_value=1, max_value=5),
        num_new_posts=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=15, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_digest_excludes_old_posts(self, app, newsletter_manager, frequency, num_old_posts, num_new_posts):
        """Property: Digest must exclude posts outside the frequency period."""
        with app.app_context():
            now = datetime.now(timezone.utc)
            
            # Determine period boundaries
            if frequency == 'weekly':
                period_start = now - timedelta(days=7)
                old_date = now - timedelta(days=14)  # Outside period
            elif frequency == 'bi-weekly':
                period_start = now - timedelta(days=14)
                old_date = now - timedelta(days=21)  # Outside period
            else:  # monthly
                period_start = now - timedelta(days=30)
                old_date = now - timedelta(days=45)  # Outside period
            
            # Create old posts (outside period)
            old_posts = []
            for i in range(num_old_posts):
                post = Post(
                    title=f"Old Post {i}",
                    content=f"Old content {i}",
                    status='published',
                    created_at=old_date,
                    published_at=old_date
                )
                old_posts.append(post)
                db.session.add(post)
            
            # Create new posts (within period)
            new_posts = []
            for i in range(num_new_posts):
                post_date = period_start + timedelta(
                    days=i * (now - period_start).days // num_new_posts
                )
                post = Post(
                    title=f"New Post {i}",
                    content=f"New content {i}",
                    status='published',
                    created_at=post_date,
                    published_at=post_date
                )
                new_posts.append(post)
                db.session.add(post)
            
            db.session.commit()
            
            # Generate digest
            success, message, digest_data = newsletter_manager.generate_digest(frequency)
            
            assert success
            assert digest_data['total_posts'] == num_new_posts
            
            # Verify only new posts are included
            digest_post_ids = [post['id'] for post in digest_data['posts']]
            
            for post in new_posts:
                assert post.id in digest_post_ids
            
            for post in old_posts:
                assert post.id not in digest_post_ids
    
    @given(
        frequency=frequency_strategy
    )
    @settings(max_examples=10, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_empty_digest_handling(self, app, newsletter_manager, frequency):
        """Property: Empty digest (no posts) must be handled gracefully."""
        with app.app_context():
            # Don't create any posts
            success, message, digest_data = newsletter_manager.generate_digest(frequency)
            
            assert not success
            assert "no posts found" in message.lower()
            assert digest_data is None


class TestNewsletterUnsubscribeAvailability:
    """Property 13: Newsletter Unsubscribe Availability - Validates Requirements 4.7"""
    
    @given(
        email=email_strategy,
        frequency=frequency_strategy
    )
    @settings(max_examples=20, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_unsubscribe_token_always_available(self, app, newsletter_manager, email, frequency):
        """Property: Every subscription must have a valid unsubscribe token."""
        with app.app_context():
            success, message, subscription = newsletter_manager.subscribe_email(
                email=email,
                frequency=frequency
            )
            
            assume(success and subscription is not None)
            
            # Unsubscribe token must exist
            assert subscription.unsubscribe_token is not None
            assert len(subscription.unsubscribe_token) > 10  # Reasonable token length
            
            # Token must be unique
            other_subscription = NewsletterSubscription(
                email="other@example.com",
                frequency=frequency,
                confirmation_token=newsletter_manager._generate_token(),
                unsubscribe_token=newsletter_manager._generate_token()
            )
            db.session.add(other_subscription)
            db.session.commit()
            
            assert subscription.unsubscribe_token != other_subscription.unsubscribe_token
    
    @given(
        email=email_strategy,
        frequency=frequency_strategy
    )
    @settings(max_examples=15, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_unsubscribe_workflow(self, app, newsletter_manager, email, frequency):
        """Property: Unsubscribe must properly deactivate subscription."""
        with app.app_context():
            # Subscribe and confirm
            success, message, subscription = newsletter_manager.subscribe_email(
                email=email,
                frequency=frequency
            )
            
            assume(success and subscription is not None)
            
            # Confirm subscription
            newsletter_manager.confirm_subscription(subscription.confirmation_token)
            
            # Unsubscribe
            token = subscription.unsubscribe_token
            unsub_success, unsub_message, unsub_sub = newsletter_manager.unsubscribe_email(token)
            
            assert unsub_success
            assert unsub_sub is not None
            assert unsub_sub.unsubscribed
            assert unsub_sub.unsubscribed_at is not None
            
            # Verify in database
            db_subscription = NewsletterSubscription.query.filter_by(email=email).first()
            assert db_subscription.unsubscribed
            assert db_subscription.unsubscribed_at is not None
    
    @given(
        email=email_strategy,
        frequency=frequency_strategy
    )
    @settings(max_examples=10, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_unsubscribe_unconfirmed_subscription(self, app, newsletter_manager, email, frequency):
        """Property: Unsubscribing unconfirmed subscription must delete the record."""
        with app.app_context():
            # Subscribe but don't confirm
            success, message, subscription = newsletter_manager.subscribe_email(
                email=email,
                frequency=frequency
            )
            
            assume(success and subscription is not None)
            assert not subscription.confirmed
            
            # Unsubscribe
            token = subscription.unsubscribe_token
            unsub_success, unsub_message, unsub_sub = newsletter_manager.unsubscribe_email(token)
            
            assert unsub_success
            
            # Record should be deleted
            db_subscription = NewsletterSubscription.query.filter_by(email=email).first()
            assert db_subscription is None


class TestNewsletterServiceIntegration:
    """Property 14: Newsletter Service Integration - Validates Requirements 4.8, 4.9"""
    
    @given(
        email=email_strategy,
        frequency=frequency_strategy
    )
    @settings(max_examples=15, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_subscription_stats_accuracy(self, app, newsletter_manager, email, frequency):
        """Property: Subscription statistics must accurately reflect database state."""
        with app.app_context():
            # Get initial stats
            initial_stats = newsletter_manager.get_subscription_stats()
            
            # Subscribe
            success, message, subscription = newsletter_manager.subscribe_email(
                email=email,
                frequency=frequency
            )
            
            assume(success and subscription is not None)
            
            # Stats after subscription
            after_sub_stats = newsletter_manager.get_subscription_stats()
            assert after_sub_stats['total_subscriptions'] == initial_stats['total_subscriptions'] + 1
            assert after_sub_stats['unconfirmed_subscriptions'] == initial_stats['unconfirmed_subscriptions'] + 1
            
            # Confirm subscription
            newsletter_manager.confirm_subscription(subscription.confirmation_token)
            
            # Stats after confirmation
            after_confirm_stats = newsletter_manager.get_subscription_stats()
            assert after_confirm_stats['confirmed_subscriptions'] == initial_stats['confirmed_subscriptions'] + 1
            assert after_confirm_stats['unconfirmed_subscriptions'] == initial_stats['unconfirmed_subscriptions']
            
            # Verify frequency breakdown
            assert after_confirm_stats['frequency_breakdown'][frequency] == initial_stats['frequency_breakdown'][frequency] + 1
    
    @given(
        emails=st.lists(email_strategy, min_size=2, max_size=5, unique=True),
        frequency=frequency_strategy
    )
    @settings(max_examples=10, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_bulk_subscription_stats(self, app, newsletter_manager, emails, frequency):
        """Property: Statistics must remain accurate with multiple subscriptions."""
        with app.app_context():
            confirmed_count = 0
            unsubscribed_count = 0
            
            for i, email in enumerate(emails):
                # Subscribe
                success, message, subscription = newsletter_manager.subscribe_email(
                    email=email,
                    frequency=frequency
                )
                
                if success and subscription:
                    # Confirm some subscriptions
                    if i % 2 == 0:
                        newsletter_manager.confirm_subscription(subscription.confirmation_token)
                        confirmed_count += 1
                        
                        # Unsubscribe some confirmed subscriptions
                        if i % 4 == 0:
                            newsletter_manager.unsubscribe_email(subscription.unsubscribe_token)
                            unsubscribed_count += 1
                            confirmed_count -= 1
            
            # Verify final stats
            final_stats = newsletter_manager.get_subscription_stats()
            assert final_stats['confirmed_subscriptions'] == confirmed_count
            assert final_stats['unsubscribed_count'] == unsubscribed_count
            assert final_stats['frequency_breakdown'][frequency] == confirmed_count
    
    def test_email_service_configuration_handling(self, app, newsletter_manager):
        """Property: System must handle missing email service configuration gracefully."""
        with app.app_context():
            # Newsletter manager without SendGrid should still work for basic operations
            assert newsletter_manager.sg is None  # No SendGrid configured in test
            
            # Should still be able to create subscriptions
            success, message, subscription = newsletter_manager.subscribe_email(
                email="test@example.com",
                frequency="weekly"
            )
            
            # Should fail gracefully for email operations
            if not success:
                assert "email service not configured" in message.lower()
            
            # Stats should still work
            stats = newsletter_manager.get_subscription_stats()
            assert isinstance(stats, dict)
            assert 'total_subscriptions' in stats