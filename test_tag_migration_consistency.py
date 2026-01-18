"""
Property-based test for tag migration consistency.

**Feature: enhanced-content-management, Property 9: Tag Migration Consistency**
**Validates: Requirements 4.1**

This test validates that for any existing post with comma-separated tag strings,
the migration process creates equivalent tag relationships without data loss.
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
def legacy_tag_string(draw):
    """Generate realistic comma-separated tag strings for testing."""
    # Generate 1-5 tag names
    num_tags = draw(st.integers(min_value=1, max_value=5))
    
    # Generate individual tag names (realistic blog tags)
    tag_names = []
    for _ in range(num_tags):
        tag_name = draw(st.one_of(
            # Common programming/tech tags
            st.sampled_from([
                'Python', 'JavaScript', 'React', 'Flask', 'Django', 'Node.js',
                'Web Development', 'Machine Learning', 'Data Science', 'AI',
                'Frontend', 'Backend', 'Database', 'API', 'Testing'
            ]),
            # Generated tag names with realistic patterns (ASCII only to avoid empty slug issues)
            st.text(
                alphabet=st.characters(min_codepoint=32, max_codepoint=126),  # ASCII printable characters
                min_size=2, 
                max_size=20
            ).filter(lambda x: x.strip() and not x.isspace() and any(c.isalnum() for c in x))
        ))
        if tag_name.strip() and any(c.isalnum() for c in tag_name):  # Ensure tag has alphanumeric content
            tag_names.append(tag_name.strip())
    
    # Remove duplicates while preserving order
    unique_tags = []
    seen = set()
    for tag in tag_names:
        tag_lower = tag.lower()
        if tag_lower not in seen:
            unique_tags.append(tag)
            seen.add(tag_lower)
    
    if not unique_tags:
        unique_tags = ['Default Tag']  # Ensure at least one tag
    
    # Add some realistic whitespace variations
    whitespace_variation = draw(st.sampled_from([
        lambda tags: ', '.join(tags),  # Standard format
        lambda tags: ','.join(tags),   # No spaces
        lambda tags: ' , '.join(tags), # Extra spaces
        lambda tags: ', '.join(f' {tag} ' for tag in tags),  # Padded tags
        lambda tags: ',  '.join(tags), # Inconsistent spacing
    ]))
    
    return whitespace_variation(unique_tags)


@composite
def post_with_legacy_tags(draw):
    """Generate a post with legacy comma-separated tags."""
    return {
        'title': draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip())),
        'content': draw(st.text(min_size=1, max_size=1000)),
        'category': draw(st.one_of(
            st.none(),
            st.sampled_from(['wealth', 'health', 'happiness', 'technology', 'lifestyle'])
        )),
        'tags': draw(legacy_tag_string()),  # Legacy comma-separated tags
        'status': draw(st.sampled_from(['draft', 'published', 'scheduled'])),
        'created_at': draw(st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2024, 12, 31)
        ))
    }


class TestTagMigrationConsistency:
    """Test suite for tag migration consistency property."""
    
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
    
    def parse_legacy_tags(self, tag_string):
        """Parse legacy comma-separated tag string into normalized tag names."""
        if not tag_string:
            return []
        
        tag_names = [tag.strip() for tag in tag_string.split(',') if tag.strip()]
        
        # Remove duplicates while preserving order (case-insensitive)
        unique_tags = []
        seen = set()
        for tag in tag_names:
            tag_lower = tag.lower()
            if tag_lower not in seen:
                unique_tags.append(tag)
                seen.add(tag_lower)
        
        return unique_tags
    
    @given(st.lists(post_with_legacy_tags(), min_size=1, max_size=5))
    @settings(max_examples=15, deadline=None)
    def test_tag_migration_creates_equivalent_relationships(self, posts_data):
        """
        **Property 9: Tag Migration Consistency**
        **Validates: Requirements 4.1**
        
        For any existing post with comma-separated tag strings, the migration 
        process should create equivalent tag relationships without data loss.
        """
        app = self.create_app_and_db()
        
        with app.app_context():
            # Create a test user with unique username
            unique_username = f'testuser_{uuid.uuid4().hex[:8]}'
            user = User(username=unique_username, is_admin=True)
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            # Create posts with legacy tag strings and track expected outcomes
            created_posts = []
            expected_tag_mappings = []
            
            for post_data in posts_data:
                # Create post with legacy tags
                post = Post(
                    title=post_data['title'],
                    content=post_data['content'],
                    category=post_data['category'],
                    tags=post_data['tags'],  # Legacy comma-separated string
                    status=post_data['status'],
                    created_at=post_data['created_at']
                )
                db.session.add(post)
                created_posts.append(post)
                
                # Parse expected tags from legacy string
                expected_tags = self.parse_legacy_tags(post_data['tags'])
                expected_tag_mappings.append({
                    'post': post,
                    'original_tags_string': post_data['tags'],
                    'expected_tag_names': expected_tags
                })
            
            db.session.commit()
            
            # Store post IDs after commit
            for i, post in enumerate(created_posts):
                expected_tag_mappings[i]['post_id'] = post.id
            
            # Run the migration
            migration_stats = TagManager.migrate_legacy_tags()
            
            # Verify migration statistics are reasonable
            assert migration_stats['posts_processed'] == len(posts_data), \
                f"Migration should process all {len(posts_data)} posts with legacy tags"
            
            assert migration_stats['posts_processed'] > 0, \
                "Migration should process at least one post"
            
            assert len(migration_stats['errors']) == 0, \
                f"Migration should complete without errors, but got: {migration_stats['errors']}"
            
            # Verify each post's tag relationships match expected tags
            for mapping in expected_tag_mappings:
                post = db.session.get(Post, mapping['post_id'])
                assert post is not None, f"Post {mapping['post_id']} should still exist after migration"
                
                # Verify legacy tags field is preserved (backward compatibility)
                assert post.tags == mapping['original_tags_string'], \
                    f"Legacy tags field should be preserved: expected '{mapping['original_tags_string']}', got '{post.tags}'"
                
                # Get actual tag names from relationships
                actual_tag_names = [tag.name for tag in post.tag_relationships]
                expected_tag_names = mapping['expected_tag_names']
                
                # Verify tag count matches
                assert len(actual_tag_names) == len(expected_tag_names), \
                    f"Post {mapping['post_id']} should have {len(expected_tag_names)} tag relationships, got {len(actual_tag_names)}"
                
                # Verify tag names match (case-sensitive, order-independent)
                actual_tag_set = set(actual_tag_names)
                expected_tag_set = set(expected_tag_names)
                
                assert actual_tag_set == expected_tag_set, \
                    f"Post {mapping['post_id']} tag relationships should match expected tags.\n" \
                    f"Expected: {expected_tag_set}\n" \
                    f"Actual: {actual_tag_set}\n" \
                    f"Original string: '{mapping['original_tags_string']}'"
                
                # Verify each tag has proper database entity
                for tag_name in expected_tag_names:
                    tag_entity = Tag.query.filter_by(name=tag_name).first()
                    assert tag_entity is not None, \
                        f"Tag '{tag_name}' should exist as database entity"
                    
                    assert tag_entity.slug is not None and tag_entity.slug != '', \
                        f"Tag '{tag_name}' should have a non-empty slug"
                    
                    # Verify the tag is actually associated with the post
                    assert tag_entity in post.tag_relationships, \
                        f"Tag '{tag_name}' should be associated with post {mapping['post_id']}"
    
    @given(st.lists(post_with_legacy_tags(), min_size=2, max_size=4))
    @settings(max_examples=15, deadline=None)
    def test_migration_handles_overlapping_tags_correctly(self, posts_data):
        """
        Test that migration correctly handles cases where multiple posts
        share some of the same tags, ensuring no duplicate Tag entities
        are created and relationships are properly established.
        """
        app = self.create_app_and_db()
        
        with app.app_context():
            # Create test user
            unique_username = f'testuser_{uuid.uuid4().hex[:8]}'
            user = User(username=unique_username, is_admin=True)
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            # Create posts and track all expected unique tags
            created_posts = []
            all_expected_tags = set()
            post_tag_mappings = []
            
            for post_data in posts_data:
                post = Post(
                    title=post_data['title'],
                    content=post_data['content'],
                    category=post_data['category'],
                    tags=post_data['tags'],
                    status=post_data['status'],
                    created_at=post_data['created_at']
                )
                db.session.add(post)
                created_posts.append(post)
                
                # Parse expected tags
                expected_tags = self.parse_legacy_tags(post_data['tags'])
                post_tag_mappings.append({
                    'post': post,
                    'expected_tags': expected_tags
                })
                
                # Add to global set (case-insensitive uniqueness)
                for tag in expected_tags:
                    all_expected_tags.add(tag)
            
            db.session.commit()
            
            # Update mappings with post IDs
            for i, post in enumerate(created_posts):
                post_tag_mappings[i]['post_id'] = post.id
            
            # Run migration
            migration_stats = TagManager.migrate_legacy_tags()
            
            # Verify no errors occurred
            assert len(migration_stats['errors']) == 0, \
                f"Migration should complete without errors: {migration_stats['errors']}"
            
            # Verify correct number of unique tags were created
            total_tags_in_db = Tag.query.count()
            expected_unique_count = len(all_expected_tags)
            
            # Account for case-insensitive uniqueness in database
            unique_tags_case_insensitive = set()
            for tag in all_expected_tags:
                # Find if any existing tag matches case-insensitively
                existing_match = None
                for existing in unique_tags_case_insensitive:
                    if existing.lower() == tag.lower():
                        existing_match = existing
                        break
                
                if existing_match is None:
                    unique_tags_case_insensitive.add(tag)
            
            assert total_tags_in_db == len(unique_tags_case_insensitive), \
                f"Should have {len(unique_tags_case_insensitive)} unique tags in database, got {total_tags_in_db}"
            
            # Verify each post has correct relationships
            for mapping in post_tag_mappings:
                post = db.session.get(Post, mapping['post_id'])
                actual_tag_names = [tag.name for tag in post.tag_relationships]
                expected_tag_names = mapping['expected_tags']
                
                assert len(actual_tag_names) == len(expected_tag_names), \
                    f"Post {mapping['post_id']} should have {len(expected_tag_names)} relationships"
                
                # Verify tag names match (accounting for case-insensitive deduplication)
                for expected_tag in expected_tag_names:
                    # Find the actual tag that matches (case-insensitive)
                    matching_actual_tag = None
                    for actual_tag in actual_tag_names:
                        if actual_tag.lower() == expected_tag.lower():
                            matching_actual_tag = actual_tag
                            break
                    
                    assert matching_actual_tag is not None, \
                        f"Post {mapping['post_id']} should have tag matching '{expected_tag}'"
    
    @given(post_with_legacy_tags())
    @settings(max_examples=20, deadline=None)
    def test_migration_preserves_tag_case_and_whitespace_handling(self, post_data):
        """
        Test that migration correctly handles various whitespace and case
        scenarios in tag strings, preserving the first occurrence's case
        while properly normalizing for uniqueness.
        """
        app = self.create_app_and_db()
        
        with app.app_context():
            # Create test user
            unique_username = f'testuser_{uuid.uuid4().hex[:8]}'
            user = User(username=unique_username, is_admin=True)
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            # Create post with legacy tags
            post = Post(
                title=post_data['title'],
                content=post_data['content'],
                category=post_data['category'],
                tags=post_data['tags'],
                status=post_data['status'],
                created_at=post_data['created_at']
            )
            db.session.add(post)
            db.session.commit()
            
            # Parse expected tags manually
            expected_tags = self.parse_legacy_tags(post_data['tags'])
            
            # Skip if no tags to test
            assume(len(expected_tags) > 0)
            
            # Run migration
            migration_stats = TagManager.migrate_legacy_tags()
            
            # Verify migration completed successfully
            assert len(migration_stats['errors']) == 0, \
                f"Migration should complete without errors: {migration_stats['errors']}"
            
            # Verify post relationships
            post = Post.query.first()
            actual_tag_names = [tag.name for tag in post.tag_relationships]
            
            assert len(actual_tag_names) == len(expected_tags), \
                f"Should have {len(expected_tags)} tag relationships, got {len(actual_tag_names)}"
            
            # Verify each expected tag has a corresponding relationship
            for expected_tag in expected_tags:
                # Find matching tag (case-insensitive)
                matching_tag = None
                for actual_tag_name in actual_tag_names:
                    if actual_tag_name.lower() == expected_tag.lower():
                        matching_tag = actual_tag_name
                        break
                
                assert matching_tag is not None, \
                    f"Should have tag relationship for '{expected_tag}'"
                
                # Verify tag entity exists with proper slug
                tag_entity = Tag.query.filter_by(name=matching_tag).first()
                assert tag_entity is not None, \
                    f"Tag entity should exist for '{matching_tag}'"
                
                assert tag_entity.slug is not None and tag_entity.slug.strip() != '', \
                    f"Tag '{matching_tag}' should have a valid slug"
    
    @given(st.lists(post_with_legacy_tags(), min_size=1, max_size=3))
    @settings(max_examples=10, deadline=None)
    def test_migration_is_idempotent(self, posts_data):
        """
        Test that running migration multiple times produces the same result
        and doesn't create duplicate relationships or entities.
        """
        app = self.create_app_and_db()
        
        with app.app_context():
            # Create test user
            unique_username = f'testuser_{uuid.uuid4().hex[:8]}'
            user = User(username=unique_username, is_admin=True)
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            # Create posts with legacy tags
            created_posts = []
            for post_data in posts_data:
                post = Post(
                    title=post_data['title'],
                    content=post_data['content'],
                    category=post_data['category'],
                    tags=post_data['tags'],
                    status=post_data['status'],
                    created_at=post_data['created_at']
                )
                db.session.add(post)
                created_posts.append(post)
            
            db.session.commit()
            
            # Run migration first time
            stats1 = TagManager.migrate_legacy_tags()
            
            # Capture state after first migration
            first_migration_state = {}
            for post in created_posts:
                post_fresh = db.session.get(Post, post.id)
                first_migration_state[post.id] = {
                    'tag_count': len(post_fresh.tag_relationships),
                    'tag_names': set(tag.name for tag in post_fresh.tag_relationships),
                    'legacy_tags': post_fresh.tags
                }
            
            total_tags_after_first = Tag.query.count()
            
            # Run migration second time
            stats2 = TagManager.migrate_legacy_tags()
            
            # Verify second migration stats
            assert len(stats2['errors']) == 0, \
                f"Second migration should complete without errors: {stats2['errors']}"
            
            # Verify state is identical after second migration
            for post in created_posts:
                post_fresh = db.session.get(Post, post.id)
                first_state = first_migration_state[post.id]
                
                assert len(post_fresh.tag_relationships) == first_state['tag_count'], \
                    f"Post {post.id} should have same number of tag relationships after second migration"
                
                current_tag_names = set(tag.name for tag in post_fresh.tag_relationships)
                assert current_tag_names == first_state['tag_names'], \
                    f"Post {post.id} should have same tag relationships after second migration"
                
                assert post_fresh.tags == first_state['legacy_tags'], \
                    f"Post {post.id} legacy tags field should be unchanged after second migration"
            
            # Verify no additional tags were created
            total_tags_after_second = Tag.query.count()
            assert total_tags_after_second == total_tags_after_first, \
                f"Second migration should not create additional tags: {total_tags_after_first} vs {total_tags_after_second}"


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])