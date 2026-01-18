"""
Unit tests for TagManager class

Tests cover tag creation, retrieval, association management, and slug generation
functionality as specified in requirements 4.2, 4.3, and 4.4.
"""

import pytest
from unittest.mock import patch
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import db, Tag, Post, User
from tag_manager import TagManager


@pytest.fixture
def app():
    """Create test Flask application with in-memory database."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing."""
    with app.app_context():
        user = User(username='testuser')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()
        return user.id  # Return ID instead of object


@pytest.fixture
def sample_post(app, sample_user):
    """Create a sample post for testing."""
    with app.app_context():
        post = Post(
            title='Test Post',
            content='This is test content',
            status='published'
        )
        db.session.add(post)
        db.session.commit()
        return post.id  # Return ID instead of object


class TestSlugGeneration:
    """Test slug generation functionality."""
    
    def test_generate_slug_basic(self):
        """Test basic slug generation."""
        assert TagManager.generate_slug("Python Programming") == "python-programming"
        assert TagManager.generate_slug("Web Development") == "web-development"
        assert TagManager.generate_slug("JavaScript") == "javascript"
    
    def test_generate_slug_special_characters(self):
        """Test slug generation with special characters."""
        assert TagManager.generate_slug("C++ Programming") == "c-programming"
        assert TagManager.generate_slug("Web Dev & Design") == "web-dev-design"
        assert TagManager.generate_slug("Node.js") == "nodejs"
        assert TagManager.generate_slug("React/Vue") == "reactvue"
    
    def test_generate_slug_multiple_spaces(self):
        """Test slug generation with multiple spaces."""
        assert TagManager.generate_slug("Python   Programming") == "python-programming"
        assert TagManager.generate_slug("  Web Development  ") == "web-development"
    
    def test_generate_slug_empty_input(self):
        """Test slug generation with empty input."""
        assert TagManager.generate_slug("") == ""
        assert TagManager.generate_slug("   ") == ""
        assert TagManager.generate_slug(None) == ""
    
    def test_generate_slug_numbers(self):
        """Test slug generation with numbers."""
        assert TagManager.generate_slug("Python 3.9") == "python-39"
        assert TagManager.generate_slug("HTML5 CSS3") == "html5-css3"


class TestTagCreation:
    """Test tag creation and retrieval functionality."""
    
    def test_get_or_create_tag_new(self, app):
        """Test creating a new tag."""
        with app.app_context():
            tag = TagManager.get_or_create_tag("Python")
            
            assert tag.name == "Python"
            assert tag.slug == "python"
            assert tag.id is not None
            
            # Verify it's in the database
            db_tag = Tag.query.filter_by(name="Python").first()
            assert db_tag is not None
            assert db_tag.id == tag.id
    
    def test_get_or_create_tag_existing(self, app):
        """Test retrieving an existing tag."""
        with app.app_context():
            # Create initial tag
            tag1 = TagManager.get_or_create_tag("Python")
            tag1_id = tag1.id
            
            # Try to create same tag again
            tag2 = TagManager.get_or_create_tag("Python")
            
            assert tag2.id == tag1_id
            assert tag2.name == "Python"
            assert tag2.slug == "python"
            
            # Verify only one tag exists in database
            tag_count = Tag.query.filter_by(name="Python").count()
            assert tag_count == 1
    
    def test_get_or_create_tag_case_insensitive(self, app):
        """Test that tag creation is case-insensitive."""
        with app.app_context():
            tag1 = TagManager.get_or_create_tag("Python")
            tag2 = TagManager.get_or_create_tag("python")
            tag3 = TagManager.get_or_create_tag("PYTHON")
            
            assert tag1.id == tag2.id == tag3.id
            assert tag1.name == "Python"  # Original case preserved
    
    def test_get_or_create_tag_empty_name(self, app):
        """Test error handling for empty tag names."""
        with app.app_context():
            with pytest.raises(ValueError, match="Tag name cannot be empty"):
                TagManager.get_or_create_tag("")
            
            with pytest.raises(ValueError, match="Tag name cannot be empty"):
                TagManager.get_or_create_tag("   ")
    
    def test_get_or_create_tag_slug_uniqueness(self, app):
        """Test that slugs are made unique when conflicts occur."""
        with app.app_context():
            # Create a tag manually with a specific slug
            existing_tag = Tag(name="Test", slug="python")
            db.session.add(existing_tag)
            db.session.commit()
            
            # Now create a tag that would generate the same slug
            new_tag = TagManager.get_or_create_tag("Python")
            
            assert new_tag.slug == "python-1"
            assert new_tag.name == "Python"


class TestTagAssociation:
    """Test post-tag association functionality."""
    
    def test_associate_tags_basic(self, app, sample_post):
        """Test basic tag association."""
        with app.app_context():
            post = db.session.get(Post, sample_post)
            tag_names = ["Python", "Web Development", "Flask"]
            
            associated_tags = TagManager.associate_tags(post.id, tag_names)
            
            assert len(associated_tags) == 3
            assert len(post.tag_relationships) == 3
            
            tag_names_result = [tag.name for tag in associated_tags]
            assert "Python" in tag_names_result
            assert "Web Development" in tag_names_result
            assert "Flask" in tag_names_result
    
    def test_associate_tags_empty_list(self, app, sample_post):
        """Test associating empty tag list."""
        with app.app_context():
            post = db.session.get(Post, sample_post)
            
            associated_tags = TagManager.associate_tags(post.id, [])
            
            assert len(associated_tags) == 0
            assert len(post.tag_relationships) == 0
    
    def test_associate_tags_replaces_existing(self, app, sample_post):
        """Test that new associations replace existing ones."""
        with app.app_context():
            post = db.session.get(Post, sample_post)
            
            # First association
            TagManager.associate_tags(post.id, ["Python", "Flask"])
            assert len(post.tag_relationships) == 2
            
            # Second association should replace first
            TagManager.associate_tags(post.id, ["JavaScript", "React"])
            assert len(post.tag_relationships) == 2
            
            tag_names = [tag.name for tag in post.tag_relationships]
            assert "JavaScript" in tag_names
            assert "React" in tag_names
            assert "Python" not in tag_names
            assert "Flask" not in tag_names
    
    def test_associate_tags_invalid_post(self, app):
        """Test error handling for invalid post ID."""
        with app.app_context():
            with pytest.raises(ValueError, match="Post with ID 999 not found"):
                TagManager.associate_tags(999, ["Python"])
    
    def test_associate_tags_filters_empty_names(self, app, sample_post):
        """Test that empty tag names are filtered out."""
        with app.app_context():
            post = db.session.get(Post, sample_post)
            tag_names = ["Python", "", "  ", "Flask", None]
            
            associated_tags = TagManager.associate_tags(post.id, tag_names)
            
            assert len(associated_tags) == 2
            tag_names_result = [tag.name for tag in associated_tags]
            assert "Python" in tag_names_result
            assert "Flask" in tag_names_result


class TestTagRetrieval:
    """Test tag retrieval and search functionality."""
    
    def test_get_popular_tags(self, app, sample_post):
        """Test getting popular tags."""
        with app.app_context():
            post = db.session.get(Post, sample_post)
            
            # Create some tags and associations
            TagManager.associate_tags(post.id, ["Python", "Flask"])
            
            # Create another post for more associations
            post2 = Post(title='Test Post 2', content='Content 2', status='published')
            db.session.add(post2)
            db.session.commit()
            
            TagManager.associate_tags(post2.id, ["Python", "JavaScript"])
            
            popular_tags = TagManager.get_popular_tags(limit=10)
            
            assert len(popular_tags) == 3
            # Python should be most popular (used twice)
            assert popular_tags[0][0].name == "Python"
            assert popular_tags[0][1] == 2  # usage count
    
    def test_search_tags(self, app):
        """Test tag search functionality."""
        with app.app_context():
            # Create some tags
            TagManager.get_or_create_tag("Python Programming")
            TagManager.get_or_create_tag("JavaScript")
            TagManager.get_or_create_tag("Java")
            TagManager.get_or_create_tag("C++ Programming")
            
            # Search for tags containing "java"
            results = TagManager.search_tags("java")
            
            assert len(results) == 2
            tag_names = [tag.name for tag in results]
            assert "JavaScript" in tag_names
            assert "Java" in tag_names
    
    def test_get_tag_by_slug(self, app):
        """Test retrieving tag by slug."""
        with app.app_context():
            original_tag = TagManager.get_or_create_tag("Python Programming")
            
            retrieved_tag = TagManager.get_tag_by_slug("python-programming")
            
            assert retrieved_tag is not None
            assert retrieved_tag.id == original_tag.id
            assert retrieved_tag.name == "Python Programming"
    
    def test_get_posts_by_tag(self, app, sample_post):
        """Test getting posts by tag."""
        with app.app_context():
            post = db.session.get(Post, sample_post)
            
            # Associate tags with post
            TagManager.associate_tags(post.id, ["Python"])
            
            # Get the Python tag
            python_tag = Tag.query.filter_by(name="Python").first()
            
            # Get posts by tag
            posts = TagManager.get_posts_by_tag(python_tag)
            
            assert len(posts) == 1
            assert posts[0].id == post.id


class TestTagManagement:
    """Test tag management operations."""
    
    def test_remove_tag_association(self, app, sample_post):
        """Test removing tag association."""
        with app.app_context():
            post = db.session.get(Post, sample_post)
            
            # Create association
            TagManager.associate_tags(post.id, ["Python", "Flask"])
            python_tag = Tag.query.filter_by(name="Python").first()
            
            # Remove association
            result = TagManager.remove_tag_association(post.id, python_tag.id)
            
            assert result is True
            assert len(post.tag_relationships) == 1
            assert post.tag_relationships[0].name == "Flask"
    
    def test_delete_unused_tags(self, app):
        """Test deleting unused tags."""
        with app.app_context():
            # Create some tags
            tag1 = TagManager.get_or_create_tag("Used Tag")
            tag2 = TagManager.get_or_create_tag("Unused Tag 1")
            tag3 = TagManager.get_or_create_tag("Unused Tag 2")
            
            # Associate one tag with a post
            post = Post(title='Test', content='Content', status='published')
            db.session.add(post)
            db.session.commit()
            
            TagManager.associate_tags(post.id, ["Used Tag"])
            
            # Delete unused tags
            deleted_count = TagManager.delete_unused_tags()
            
            assert deleted_count == 2
            
            # Verify only used tag remains
            remaining_tags = Tag.query.all()
            assert len(remaining_tags) == 1
            assert remaining_tags[0].name == "Used Tag"
    
    def test_update_tag(self, app):
        """Test updating tag name and slug."""
        with app.app_context():
            tag = TagManager.get_or_create_tag("Old Name")
            original_id = tag.id
            
            # Update name
            updated_tag = TagManager.update_tag(tag.id, name="New Name")
            
            assert updated_tag is not None
            assert updated_tag.id == original_id
            assert updated_tag.name == "New Name"
            
            # Update slug
            updated_tag = TagManager.update_tag(tag.id, slug="custom-slug")
            
            assert updated_tag.slug == "custom-slug"
    
    def test_get_all_tags(self, app):
        """Test getting all tags."""
        with app.app_context():
            # Create some tags
            TagManager.get_or_create_tag("Zebra")
            TagManager.get_or_create_tag("Alpha")
            TagManager.get_or_create_tag("Beta")
            
            all_tags = TagManager.get_all_tags()
            
            assert len(all_tags) == 3
            # Should be ordered alphabetically
            assert all_tags[0].name == "Alpha"
            assert all_tags[1].name == "Beta"
            assert all_tags[2].name == "Zebra"


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_whitespace_handling(self, app):
        """Test proper whitespace handling in tag names."""
        with app.app_context():
            tag = TagManager.get_or_create_tag("  Python Programming  ")
            
            assert tag.name == "Python Programming"
            assert tag.slug == "python-programming"
    
    def test_duplicate_slug_handling(self, app):
        """Test handling of duplicate slug generation."""
        with app.app_context():
            # Create tag with specific slug manually
            existing_tag = Tag(name="Existing", slug="test-slug")
            db.session.add(existing_tag)
            db.session.commit()
            
            # Mock generate_slug to return conflicting slug
            with patch.object(TagManager, 'generate_slug', return_value='test-slug'):
                new_tag = TagManager.get_or_create_tag("Test Slug")
                
                assert new_tag.slug == "test-slug-1"
    
    def test_large_tag_name(self, app):
        """Test handling of very long tag names."""
        with app.app_context():
            long_name = "A" * 100  # Very long tag name
            tag = TagManager.get_or_create_tag(long_name)
            
            assert tag.name == long_name
            assert len(tag.slug) > 0  # Should generate some slug
    
    def test_unicode_tag_names(self, app):
        """Test handling of unicode characters in tag names."""
        with app.app_context():
            unicode_name = "Python 🐍 Programming"
            tag = TagManager.get_or_create_tag(unicode_name)
            
            assert tag.name == unicode_name
            # Slug should be cleaned of unicode
            assert "🐍" not in tag.slug