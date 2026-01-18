"""
Property-based test for tag creation and association.

**Feature: enhanced-content-management, Property 10: Tag Creation and Association**
**Validates: Requirements 4.3, 4.4**

This test validates that for any new tag name, the system should create a unique 
database entity and properly establish many-to-many relationships with associated posts.
"""

import pytest
import uuid
from datetime import datetime
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import db, Post, Tag, User
from tag_manager import TagManager


@composite
def valid_tag_name(draw):
    """Generate valid tag names for testing."""
    return draw(st.one_of(
        # Common realistic tag names
        st.sampled_from([
            'Python', 'JavaScript', 'React', 'Flask', 'Django', 'Node.js',
            'Web Development', 'Machine Learning', 'Data Science', 'AI',
            'Frontend', 'Backend', 'Database', 'API', 'Testing', 'DevOps',
            'CSS', 'HTML', 'TypeScript', 'Vue.js', 'Angular', 'Docker',
            'Kubernetes', 'AWS', 'Cloud Computing', 'Microservices'
        ]),
        # Generated tag names with realistic patterns (ASCII only to avoid empty slug issues)
        st.text(
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),  # ASCII printable characters
            min_size=1, 
            max_size=30
        ).filter(lambda x: x.strip() and not x.isspace() and any(c.isalnum() for c in x))
    ))


@composite
def tag_name_list(draw):
    """Generate a list of unique tag names."""
    # Generate 1-8 tag names
    num_tags = draw(st.integers(min_value=1, max_value=8))
    tag_names = []
    
    for _ in range(num_tags):
        tag_name = draw(valid_tag_name())
        # Ensure uniqueness (case-insensitive)
        if not any(existing.lower() == tag_name.lower() for existing in tag_names):
            tag_names.append(tag_name)
    
    # Ensure we have at least one tag
    if not tag_names:
        tag_names = ['Default Tag']
    
    return tag_names


@composite
def post_data(draw):
    """Generate post data for testing."""
    return {
        'title': draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip())),
        'content': draw(st.text(min_size=1, max_size=1000)),
        'category': draw(st.one_of(
            st.none(),
            st.sampled_from(['wealth', 'health', 'happiness', 'technology', 'lifestyle'])
        )),
        'status': draw(st.sampled_from(['draft', 'published', 'scheduled'])),
        'created_at': draw(st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2024, 12, 31)
        ))
    }


class TestTagCreationAndAssociation:
    """Test suite for tag creation and association property."""
    
    def create_app_and_db(self):
        """Create a fresh Flask app and database for each test."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = 'test-secret'
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            return app
    
    @given(st.lists(valid_tag_name(), min_size=1, max_size=5, unique_by=lambda x: x.lower()))
    @settings(max_examples=15, deadline=None)
    def test_tag_creation_creates_unique_database_entities(self, tag_names):
        """
        **Property 10: Tag Creation and Association**
        **Validates: Requirements 4.3, 4.4**
        
        For any new tag name, the system should create a unique database entity
        and properly establish many-to-many relationships with associated posts.
        
        This test focuses on the tag creation aspect - ensuring unique entities are created.
        """
        app = self.create_app_and_db()
        
        with app.app_context():
            # Verify database starts empty
            initial_tag_count = Tag.query.count()
            assert initial_tag_count == 0, "Database should start with no tags"
            
            # Create tags using TagManager
            created_tags = []
            for tag_name in tag_names:
                tag = TagManager.get_or_create_tag(tag_name)
                created_tags.append(tag)
            
            # Verify each tag was created as a unique database entity
            final_tag_count = Tag.query.count()
            expected_count = len(set(name.lower() for name in tag_names))  # Case-insensitive uniqueness
            
            assert final_tag_count == expected_count, \
                f"Should have {expected_count} unique tags in database, got {final_tag_count}"
            
            # Verify each tag has proper database entity properties
            for i, tag_name in enumerate(tag_names):
                tag = created_tags[i]
                
                # Verify tag has unique ID
                assert tag.id is not None, f"Tag '{tag_name}' should have a database ID"
                assert isinstance(tag.id, int), f"Tag '{tag_name}' ID should be an integer"
                
                # Verify tag name is preserved
                assert tag.name == tag_name, f"Tag name should be preserved: expected '{tag_name}', got '{tag.name}'"
                
                # Verify tag has a valid slug
                assert tag.slug is not None, f"Tag '{tag_name}' should have a slug"
                assert tag.slug.strip() != '', f"Tag '{tag_name}' should have a non-empty slug"
                assert isinstance(tag.slug, str), f"Tag '{tag_name}' slug should be a string"
                
                # Verify tag has creation timestamp
                assert tag.created_at is not None, f"Tag '{tag_name}' should have a creation timestamp"
                
                # Verify tag can be retrieved from database
                db_tag = db.session.get(Tag, tag.id)
                assert db_tag is not None, f"Tag '{tag_name}' should be retrievable from database"
                assert db_tag.name == tag_name, f"Retrieved tag should have correct name"
                assert db_tag.slug == tag.slug, f"Retrieved tag should have correct slug"
            
            # Verify tag uniqueness - no duplicates should exist
            all_tag_names = [tag.name for tag in Tag.query.all()]
            all_tag_slugs = [tag.slug for tag in Tag.query.all()]
            
            # Check name uniqueness (case-insensitive as per TagManager implementation)
            unique_names_case_insensitive = set(name.lower() for name in all_tag_names)
            assert len(all_tag_names) == len(unique_names_case_insensitive), \
                f"All tag names should be unique (case-insensitive): {all_tag_names}"
            
            # Check slug uniqueness
            assert len(all_tag_slugs) == len(set(all_tag_slugs)), \
                f"All tag slugs should be unique: {all_tag_slugs}"
    
    @given(post_data(), tag_name_list())
    @settings(max_examples=15, deadline=None)
    def test_tag_association_creates_proper_many_to_many_relationships(self, post_info, tag_names):
        """
        **Property 10: Tag Creation and Association**
        **Validates: Requirements 4.3, 4.4**
        
        For any new tag name, the system should create a unique database entity
        and properly establish many-to-many relationships with associated posts.
        
        This test focuses on the association aspect - ensuring proper many-to-many relationships.
        """
        app = self.create_app_and_db()
        
        with app.app_context():
            # Create a test user
            unique_username = f'testuser_{uuid.uuid4().hex[:8]}'
            user = User(username=unique_username, is_admin=True)
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            # Create a post
            post = Post(
                title=post_info['title'],
                content=post_info['content'],
                category=post_info['category'],
                status=post_info['status'],
                created_at=post_info['created_at']
            )
            db.session.add(post)
            db.session.commit()
            
            # Associate tags with the post
            associated_tags = TagManager.associate_tags(post.id, tag_names)
            
            # Verify correct number of tags were associated
            expected_unique_tags = len(set(name.lower() for name in tag_names))  # Case-insensitive uniqueness
            assert len(associated_tags) == expected_unique_tags, \
                f"Should associate {expected_unique_tags} unique tags, got {len(associated_tags)}"
            
            # Verify each tag was created as a database entity
            for tag_name in tag_names:
                # Find the tag entity (case-insensitive search as per TagManager)
                # Note: TagManager strips whitespace, so we need to compare stripped versions
                stripped_tag_name = tag_name.strip()
                tag_entity = None
                for tag in associated_tags:
                    if tag.name.lower() == stripped_tag_name.lower():
                        tag_entity = tag
                        break
                
                assert tag_entity is not None, f"Tag '{stripped_tag_name}' (from '{tag_name}') should be created as database entity"
                
                # Verify tag entity properties
                assert tag_entity.id is not None, f"Tag '{stripped_tag_name}' should have database ID"
                assert tag_entity.slug is not None, f"Tag '{stripped_tag_name}' should have slug"
                assert tag_entity.created_at is not None, f"Tag '{stripped_tag_name}' should have creation timestamp"
            
            # Verify many-to-many relationships are properly established
            post_fresh = db.session.get(Post, post.id)
            assert len(post_fresh.tag_relationships) == expected_unique_tags, \
                f"Post should have {expected_unique_tags} tag relationships"
            
            # Verify bidirectional relationship
            for tag in associated_tags:
                # Tag should reference the post
                assert post_fresh in tag.posts, \
                    f"Tag '{tag.name}' should reference the post in its posts collection"
                
                # Post should reference the tag
                assert tag in post_fresh.tag_relationships, \
                    f"Post should reference tag '{tag.name}' in its tag_relationships"
            
            # Verify relationship persistence in database
            # Query through association table to verify many-to-many relationship
            from models import post_tags
            association_count = db.session.query(post_tags).filter_by(post_id=post.id).count()
            assert association_count == expected_unique_tags, \
                f"Should have {expected_unique_tags} associations in post_tags table, got {association_count}"
            
            # Verify each tag can be used to find the post
            for tag in associated_tags:
                posts_with_tag = TagManager.get_posts_by_tag(tag, status=post_info['status'])
                assert post_fresh in posts_with_tag, \
                    f"Tag '{tag.name}' should be able to find the associated post"
    
    @given(st.lists(post_data(), min_size=2, max_size=4), tag_name_list())
    @settings(max_examples=10, deadline=None)
    def test_tag_association_supports_multiple_posts(self, posts_info, tag_names):
        """
        Test that tags can be associated with multiple posts, demonstrating
        the many-to-many relationship works in both directions.
        """
        app = self.create_app_and_db()
        
        with app.app_context():
            # Create test user
            unique_username = f'testuser_{uuid.uuid4().hex[:8]}'
            user = User(username=unique_username, is_admin=True)
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            # Create multiple posts
            created_posts = []
            for post_info in posts_info:
                post = Post(
                    title=post_info['title'],
                    content=post_info['content'],
                    category=post_info['category'],
                    status=post_info['status'],
                    created_at=post_info['created_at']
                )
                db.session.add(post)
                created_posts.append(post)
            
            db.session.commit()
            
            # Associate the same tags with all posts
            all_associated_tags = []
            for post in created_posts:
                associated_tags = TagManager.associate_tags(post.id, tag_names)
                all_associated_tags.append(associated_tags)
            
            # Verify tags are shared across posts (same entities, not duplicates)
            expected_unique_tags = len(set(name.lower() for name in tag_names))
            total_unique_tags_in_db = Tag.query.count()
            
            assert total_unique_tags_in_db == expected_unique_tags, \
                f"Should have {expected_unique_tags} unique tag entities total, got {total_unique_tags_in_db}"
            
            # Verify each tag is associated with all posts
            for tag_name in tag_names:
                # Find the tag entity (accounting for TagManager's whitespace stripping)
                stripped_tag_name = tag_name.strip()
                tag_entity = None
                for associated_tags in all_associated_tags:
                    for tag in associated_tags:
                        if tag.name.lower() == stripped_tag_name.lower():
                            tag_entity = tag
                            break
                    if tag_entity:
                        break
                
                assert tag_entity is not None, f"Tag '{stripped_tag_name}' (from '{tag_name}') should exist as database entity"
                
                # Verify tag is associated with all posts
                assert len(tag_entity.posts) == len(created_posts), \
                    f"Tag '{stripped_tag_name}' should be associated with all {len(created_posts)} posts"
                
                for post in created_posts:
                    post_fresh = db.session.get(Post, post.id)
                    assert tag_entity in post_fresh.tag_relationships, \
                        f"Tag '{stripped_tag_name}' should be associated with post {post.id}"
                    assert post_fresh in tag_entity.posts, \
                        f"Post {post.id} should be in tag '{stripped_tag_name}' posts collection"
    
    @given(valid_tag_name())
    @settings(max_examples=20, deadline=None)
    def test_tag_creation_handles_case_sensitivity_correctly(self, tag_name):
        """
        Test that tag creation properly handles case sensitivity - 
        same tag names with different cases should result in the same entity.
        """
        app = self.create_app_and_db()
        
        with app.app_context():
            # Create variations of the same tag name with different cases
            variations = [
                tag_name,
                tag_name.lower(),
                tag_name.upper(),
                tag_name.title() if len(tag_name) > 0 else tag_name
            ]
            
            # Remove duplicates while preserving order
            unique_variations = []
            seen = set()
            for variation in variations:
                if variation not in seen:
                    unique_variations.append(variation)
                    seen.add(variation)
            
            # Create tags for all variations
            created_tags = []
            for variation in unique_variations:
                tag = TagManager.get_or_create_tag(variation)
                created_tags.append(tag)
            
            # Verify all variations result in the same tag entity
            if len(unique_variations) > 1:
                first_tag_id = created_tags[0].id
                for i, tag in enumerate(created_tags[1:], 1):
                    assert tag.id == first_tag_id, \
                        f"Tag variation '{unique_variations[i]}' should result in same entity as '{unique_variations[0]}'"
            
            # Verify only one tag entity exists in database
            total_tags = Tag.query.count()
            assert total_tags == 1, f"Should have only 1 tag entity for all case variations, got {total_tags}"
            
            # Verify the tag preserves the original case (first occurrence after stripping)
            db_tag = Tag.query.first()
            expected_name = unique_variations[0].strip()  # TagManager strips whitespace
            assert db_tag.name == expected_name, \
                f"Tag should preserve original case (after stripping): expected '{expected_name}', got '{db_tag.name}'"
    
    @given(post_data(), st.lists(valid_tag_name(), min_size=1, max_size=3, unique_by=lambda x: x.lower()), st.lists(valid_tag_name(), min_size=1, max_size=3, unique_by=lambda x: x.lower()))
    @settings(max_examples=15, deadline=None)
    def test_tag_association_replacement_behavior(self, post_info, initial_tags, new_tags):
        """
        Test that associating new tags with a post replaces existing associations
        rather than adding to them, as per TagManager.associate_tags behavior.
        """
        # Ensure we have different tag sets for meaningful test
        assume(set(tag.lower() for tag in initial_tags) != set(tag.lower() for tag in new_tags))
        
        app = self.create_app_and_db()
        
        with app.app_context():
            # Create test user
            unique_username = f'testuser_{uuid.uuid4().hex[:8]}'
            user = User(username=unique_username, is_admin=True)
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            # Create post
            post = Post(
                title=post_info['title'],
                content=post_info['content'],
                category=post_info['category'],
                status=post_info['status'],
                created_at=post_info['created_at']
            )
            db.session.add(post)
            db.session.commit()
            
            # Associate initial tags
            initial_associated = TagManager.associate_tags(post.id, initial_tags)
            initial_count = len(set(tag.lower() for tag in initial_tags))
            
            # Verify initial associations
            post_fresh = db.session.get(Post, post.id)
            assert len(post_fresh.tag_relationships) == initial_count, \
                f"Should have {initial_count} initial tag associations"
            
            # Associate new tags (should replace, not add)
            new_associated = TagManager.associate_tags(post.id, new_tags)
            new_count = len(set(tag.lower() for tag in new_tags))
            
            # Verify associations were replaced
            post_fresh = db.session.get(Post, post.id)
            assert len(post_fresh.tag_relationships) == new_count, \
                f"Should have {new_count} tag associations after replacement, got {len(post_fresh.tag_relationships)}"
            
            # Verify new tags are associated (accounting for TagManager's whitespace stripping)
            current_tag_names = set(tag.name.lower() for tag in post_fresh.tag_relationships)
            expected_tag_names = set(tag.strip().lower() for tag in new_tags)  # Strip whitespace like TagManager does
            
            assert current_tag_names == expected_tag_names, \
                f"Post should have new tag associations: expected {expected_tag_names}, got {current_tag_names}"
            
            # Verify only tags that are NOT in the new set are no longer associated
            initial_tag_names_lower = set(tag.strip().lower() for tag in initial_tags)  # Strip whitespace
            new_tag_names_lower = set(tag.strip().lower() for tag in new_tags)  # Strip whitespace
            tags_that_should_be_removed = initial_tag_names_lower - new_tag_names_lower
            
            for initial_tag in initial_associated:
                if initial_tag.name.lower() in tags_that_should_be_removed:
                    assert initial_tag not in post_fresh.tag_relationships, \
                        f"Initial tag '{initial_tag.name}' should no longer be associated with post"


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])