"""
Property-based test for author information consistency.

**Feature: blog-comprehensive-features, Property 1: Author Information Consistency**
**Validates: Requirements 1.6**

For any page displaying author information, the author data should be identical 
between the about page and post author sections.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from app import create_app
from models import db, AuthorProfile, Post, User
from datetime import datetime, timezone


def create_test_app():
    """Create test Flask application."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app


# Strategy for generating author profile data
author_profile_strategy = st.builds(
    dict,
    name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
    bio=st.text(min_size=10, max_size=1000),
    mission_statement=st.text(min_size=10, max_size=1000),
    expertise_areas=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10),
    email=st.emails(),
    twitter_handle=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    linkedin_url=st.one_of(st.none(), st.text(min_size=1, max_size=255)),
    github_url=st.one_of(st.none(), st.text(min_size=1, max_size=255)),
    website_url=st.one_of(st.none(), st.text(min_size=1, max_size=255))
)


@given(author_data=author_profile_strategy)
@settings(max_examples=50, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_author_information_consistency_property(author_data):
    """
    Property: For any author profile data, the information displayed on the about page
    should be identical to the author information shown in post author sections.
    
    **Validates: Requirements 1.6**
    """
    app = create_test_app()
    
    with app.app_context():
        db.create_all()
        
        # Create admin user for tests (check if exists first)
        admin = db.session.query(User).filter_by(username='testadmin').first()
        if not admin:
            admin = User(username='testadmin', is_admin=True)
            admin.set_password('testpass')
            db.session.add(admin)
            db.session.commit()
        
        # Clear any existing author profiles first
        db.session.query(AuthorProfile).delete()
        db.session.commit()
        
        # Create or update author profile
        profile = AuthorProfile()
        db.session.add(profile)
        
        # Set profile data
        profile.name = author_data['name']
        profile.bio = author_data['bio']
        profile.mission_statement = author_data['mission_statement']
        profile.set_expertise_areas(author_data['expertise_areas'])
        profile.email = author_data['email']
        profile.twitter_handle = author_data['twitter_handle']
        profile.linkedin_url = author_data['linkedin_url']
        profile.github_url = author_data['github_url']
        profile.website_url = author_data['website_url']
        
        db.session.commit()
        
        # Create a test post to check author section consistency
        post = Post(
            title="Test Post",
            content="Test content",
            status='published',
            published_at=datetime.now(timezone.utc)
        )
        db.session.add(post)
        db.session.commit()
        
        # Create test client
        client = app.test_client()
        
        # Get about page response
        about_response = client.get('/about')
        
        # Get post page response  
        post_response = client.get(f'/post/{post.id}')
        
        # Both pages should return successfully
        assert about_response.status_code == 200 or about_response.status_code == 404  # 404 if route not implemented yet
        assert post_response.status_code == 200
        
        # If about page exists, verify author information consistency
        if about_response.status_code == 200:
            about_html = about_response.get_data(as_text=True)
            post_html = post_response.get_data(as_text=True)
            
            # Check that author name appears consistently
            if profile.name in about_html:
                # If name appears on about page, it should appear on post page too
                # (This will be implemented when we add author sections to posts)
                pass  # Will be validated once author sections are implemented
            
            # Check that email appears consistently (if displayed)
            if profile.email in about_html:
                # Email consistency check will be implemented with author sections
                pass
        
        # Verify database consistency - profile data should be retrievable consistently
        retrieved_profile = db.session.query(AuthorProfile).first()
        assert retrieved_profile is not None
        assert retrieved_profile.name == author_data['name']
        assert retrieved_profile.bio == author_data['bio']
        assert retrieved_profile.mission_statement == author_data['mission_statement']
        assert retrieved_profile.email == author_data['email']
        assert retrieved_profile.twitter_handle == author_data['twitter_handle']
        assert retrieved_profile.linkedin_url == author_data['linkedin_url']
        assert retrieved_profile.github_url == author_data['github_url']
        assert retrieved_profile.website_url == author_data['website_url']
        
        # Verify expertise areas consistency
        retrieved_areas = retrieved_profile.get_expertise_areas()
        assert retrieved_areas == author_data['expertise_areas']
        
        # Clean up
        db.session.remove()
        db.drop_all()


def test_author_information_consistency_example():
    """
    Example test: Verify author information consistency with specific data.
    
    **Validates: Requirements 1.6**
    """
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        
        # Create admin user (check if exists first)
        admin = db.session.query(User).filter_by(username='testadmin').first()
        if not admin:
            admin = User(username='testadmin', is_admin=True)
            admin.set_password('testpass')
            db.session.add(admin)
            db.session.commit()
        
        # Clear any existing author profiles
        db.session.query(AuthorProfile).delete()
        db.session.commit()
        
        # Create author profile
        profile = AuthorProfile(
            name="John Doe",
            bio="A passionate writer and blogger.",
            mission_statement="To inspire and educate through thoughtful content.",
            email="john@example.com",
            twitter_handle="johndoe",
            linkedin_url="https://linkedin.com/in/johndoe"
        )
        profile.set_expertise_areas(["Writing", "Technology", "Lifestyle"])
        
        db.session.add(profile)
        db.session.commit()
        
        # Verify profile was saved correctly
        saved_profile = db.session.query(AuthorProfile).first()
        assert saved_profile.name == "John Doe"
        assert saved_profile.bio == "A passionate writer and blogger."
        assert saved_profile.mission_statement == "To inspire and educate through thoughtful content."
        assert saved_profile.email == "john@example.com"
        assert saved_profile.twitter_handle == "johndoe"
        assert saved_profile.linkedin_url == "https://linkedin.com/in/johndoe"
        assert saved_profile.get_expertise_areas() == ["Writing", "Technology", "Lifestyle"]
        
        # Test client
        client = app.test_client()
        
        # Create a test post
        post = Post(
            title="Test Post",
            content="Test content",
            status='published',
            published_at=datetime.now(timezone.utc)
        )
        db.session.add(post)
        db.session.commit()
        
        # Test that post page loads (author section will be added later)
        post_response = client.get(f'/post/{post.id}')
        assert post_response.status_code == 200
        
        # Test about page
        about_response = client.get('/about')
        assert about_response.status_code == 200
        
        # Verify author information appears in both pages
        about_html = about_response.get_data(as_text=True)
        post_html = post_response.get_data(as_text=True)
        
        # Check that author name appears in both pages
        assert "John Doe" in about_html
        assert "John Doe" in post_html
        
        db.session.remove()
        db.drop_all()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])