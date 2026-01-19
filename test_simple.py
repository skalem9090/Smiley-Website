"""
Simple test to verify basic functionality.
"""

import pytest
from flask import Flask
from models import db, Post, NewsletterSubscription
from search_engine import SearchEngine
from newsletter_manager import NewsletterManager
from datetime import datetime, timezone


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


def test_search_engine_creation(app):
    """Test that SearchEngine can be created and initialized."""
    with app.app_context():
        search_engine = SearchEngine(app)
        search_engine.create_search_index()
        
        # Test basic functionality
        stats = search_engine.get_search_stats()
        assert 'indexed_posts' in stats
        assert 'published_posts' in stats


def test_newsletter_manager_creation(app):
    """Test that NewsletterManager can be created and initialized."""
    with app.app_context():
        newsletter_manager = NewsletterManager(app)
        
        # Test basic functionality
        stats = newsletter_manager.get_subscription_stats()
        assert 'total_subscriptions' in stats
        assert 'confirmed_subscriptions' in stats


def test_post_creation(app):
    """Test that Post model works correctly."""
    with app.app_context():
        post = Post(
            title="Test Post",
            content="This is test content",
            status='published',
            created_at=datetime.now(timezone.utc),
            published_at=datetime.now(timezone.utc)
        )
        db.session.add(post)
        db.session.commit()
        
        # Verify post was created
        saved_post = Post.query.first()
        assert saved_post is not None
        assert saved_post.title == "Test Post"
        assert saved_post.status == 'published'


def test_newsletter_subscription_creation(app):
    """Test that NewsletterSubscription model works correctly."""
    with app.app_context():
        subscription = NewsletterSubscription(
            email="test@example.com",
            frequency="weekly",
            confirmation_token="test_token",
            unsubscribe_token="unsubscribe_token",
            subscribed_at=datetime.now(timezone.utc)
        )
        db.session.add(subscription)
        db.session.commit()
        
        # Verify subscription was created
        saved_subscription = NewsletterSubscription.query.first()
        assert saved_subscription is not None
        assert saved_subscription.email == "test@example.com"
        assert saved_subscription.frequency == "weekly"


def test_search_basic_functionality(app):
    """Test basic search functionality."""
    with app.app_context():
        # Create a search engine
        search_engine = SearchEngine(app)
        search_engine.create_search_index()
        
        # Create a test post
        post = Post(
            title="Python Programming",
            content="This is a post about Python programming language",
            status='published',
            created_at=datetime.now(timezone.utc),
            published_at=datetime.now(timezone.utc)
        )
        db.session.add(post)
        db.session.commit()
        
        # Index the post
        search_engine.index_post(post)
        db.session.commit()
        
        # Search for the post
        results = search_engine.search_posts("Python")
        
        # Verify results
        assert results['total_results'] >= 1
        assert len(results['posts']) >= 1
        
        found_post = results['posts'][0]['post']
        assert found_post.title == "Python Programming"


def test_newsletter_subscription_workflow(app):
    """Test basic newsletter subscription workflow."""
    with app.app_context():
        newsletter_manager = NewsletterManager(app)
        
        # Test subscription (will fail without SendGrid, but should handle gracefully)
        success, message, subscription = newsletter_manager.subscribe_email(
            email="test@example.com",
            frequency="weekly"
        )
        
        # Should either succeed or fail gracefully with email service message
        if not success:
            assert "email service not configured" in message.lower()
        else:
            assert subscription is not None
            assert subscription.email == "test@example.com"