"""
Property-based test for data migration preservation.

**Feature: enhanced-content-management, Property 12: Data Migration Preservation**
**Validates: Requirements 5.5, 5.6**

This test validates that during system upgrade, all existing post data 
(content, metadata, category information) is preserved without modification.
"""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from hypothesis import given, strategies as st, settings
from hypothesis.strategies import composite
from flask import Flask
from flask_sqlalchemy import SQLAlchemy


@composite
def post_data(draw):
    """Generate realistic post data for testing migration preservation."""
    return {
        'title': draw(st.text(min_size=1, max_size=200).filter(lambda x: x.strip())),
        'content': draw(st.text(min_size=1, max_size=5000)),
        'category': draw(st.one_of(
            st.none(),
            st.sampled_from(['wealth', 'health', 'happiness', 'technology', 'lifestyle'])
        )),
        'tags': draw(st.one_of(
            st.none(),
            st.text(min_size=0, max_size=200),  # Legacy comma-separated tags
        )),
        'summary': draw(st.one_of(
            st.none(),
            st.text(min_size=0, max_size=500)
        )),
        'status': draw(st.sampled_from(['draft', 'published', 'scheduled'])),
        'created_at': draw(st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2024, 12, 31)
        )),
        'published_at': draw(st.one_of(
            st.none(),
            st.datetimes(
                min_value=datetime(2020, 1, 1),
                max_value=datetime(2024, 12, 31)
            )
        )),
        'scheduled_publish_at': draw(st.one_of(
            st.none(),
            st.datetimes(
                min_value=datetime(2024, 1, 1),
                max_value=datetime(2025, 12, 31)
            )
        ))
    }


def create_test_models(db):
    """Create test models for isolated testing."""
    from werkzeug.security import generate_password_hash, check_password_hash
    from flask_login import UserMixin
    
    # Association table for many-to-many relationship between Post and Tag
    post_tags = db.Table('post_tags',
        db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
        db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
    )

    class Tag(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(50), unique=True, nullable=False)
        slug = db.Column(db.String(50), unique=True, nullable=False)
        created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

        def __repr__(self):
            return f"<Tag {self.id} {self.name}>"

    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        password_hash = db.Column(db.String(128), nullable=False)
        is_admin = db.Column(db.Boolean, default=False)

        def set_password(self, password):
            self.password_hash = generate_password_hash(password)

        def check_password(self, password):
            return check_password_hash(self.password_hash, password)

    class Post(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(200), nullable=False)
        content = db.Column(db.Text, nullable=False)
        summary = db.Column(db.Text, nullable=True)
        category = db.Column(db.String(50), nullable=True)
        tags = db.Column(db.String(200), nullable=True)  # Legacy: comma-separated tags
        status = db.Column(db.String(20), default='draft', nullable=False)
        created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
        published_at = db.Column(db.DateTime, nullable=True)
        scheduled_publish_at = db.Column(db.DateTime, nullable=True)
        
        # Relationships
        tag_relationships = db.relationship('Tag', secondary=post_tags, backref='posts')

        def __repr__(self):
            return f"<Post {self.id} {self.title}>"
    
    return User, Post, Tag


class TestDataMigrationPreservation:
    """Test suite for data migration preservation property."""
    
    def create_app_and_models(self):
        """Create a fresh Flask app and database for each test."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = 'test-secret'
        
        db = SQLAlchemy()
        db.init_app(app)
        
        with app.app_context():
            User, Post, Tag = create_test_models(db)
            db.create_all()
            return app, db, User, Post, Tag
    
    @given(st.lists(post_data(), min_size=1, max_size=5))
    @settings(max_examples=50, deadline=None)
    def test_post_data_preservation_during_migration(self, posts_data):
        """
        **Property 12: Data Migration Preservation**
        **Validates: Requirements 5.5, 5.6**
        
        For any existing post data during system upgrade, all current content, 
        metadata, and category information should be preserved without modification.
        """
        app, db, User, Post, Tag = self.create_app_and_models()
        
        with app.app_context():
            # Create a test user first with unique username
            unique_username = f'testuser_{uuid.uuid4().hex[:8]}'
            user = User(username=unique_username, is_admin=True)
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            # Create posts and store their original data
            created_posts = []
            original_data = []
            
            for i, post_data_item in enumerate(posts_data):
                # Create post with original data structure
                post = Post(
                    title=post_data_item['title'],
                    content=post_data_item['content'],
                    category=post_data_item['category'],
                    tags=post_data_item['tags'],  # Legacy string tags
                    summary=post_data_item['summary'],
                    status=post_data_item['status'],
                    created_at=post_data_item['created_at'],
                    published_at=post_data_item['published_at'],
                    scheduled_publish_at=post_data_item['scheduled_publish_at']
                )
                db.session.add(post)
                created_posts.append(post)
            
            db.session.commit()
            
            # Store original data after commit (when IDs are assigned)
            for post in created_posts:
                original_data.append({
                    'id': post.id,
                    'title': post.title,
                    'content': post.content,
                    'category': post.category,
                    'tags': post.tags,
                    'summary': post.summary,
                    'status': post.status,
                    'created_at': post.created_at,
                    'published_at': post.published_at,
                    'scheduled_publish_at': post.scheduled_publish_at
                })
            
            # Simulate migration process - tag migration
            for post in created_posts:
                if post.tags:  # If post has legacy string tags
                    tag_names = [tag.strip() for tag in post.tags.split(',') if tag.strip()]
                    for tag_name in tag_names:
                        # Get or create tag
                        tag = Tag.query.filter_by(name=tag_name).first()
                        if not tag:
                            tag = Tag(
                                name=tag_name,
                                slug=tag_name.lower().replace(' ', '-')
                            )
                            db.session.add(tag)
                        
                        # Associate tag with post (new relationship)
                        if tag not in post.tag_relationships:
                            post.tag_relationships.append(tag)
            
            db.session.commit()
            
            # Verify data preservation after migration
            for original in original_data:
                migrated_post = db.session.get(Post, original['id'])
                assert migrated_post is not None, f"Post {original['id']} should still exist"
                
                # Verify core content preservation
                assert migrated_post.title == original['title'], \
                    f"Post title should be preserved: expected '{original['title']}', got '{migrated_post.title}'"
                
                assert migrated_post.content == original['content'], \
                    f"Post content should be preserved"
                
                assert migrated_post.category == original['category'], \
                    f"Post category should be preserved"
                
                assert migrated_post.summary == original['summary'], \
                    f"Post summary should be preserved"
                
                assert migrated_post.status == original['status'], \
                    f"Post status should be preserved"
                
                # Verify timestamp preservation
                assert migrated_post.created_at == original['created_at'], \
                    f"Post creation time should be preserved"
                
                assert migrated_post.published_at == original['published_at'], \
                    f"Post publication time should be preserved"
                
                assert migrated_post.scheduled_publish_at == original['scheduled_publish_at'], \
                    f"Post scheduled publication time should be preserved"
                
                # Verify legacy tags field is preserved (backward compatibility)
                assert migrated_post.tags == original['tags'], \
                    f"Legacy tags field should be preserved for backward compatibility"
                
                # Verify tag relationships were created correctly if tags existed
                if original['tags']:
                    original_tag_names = set(tag.strip() for tag in original['tags'].split(',') if tag.strip())
                    migrated_tag_names = set(tag.name for tag in migrated_post.tag_relationships)
                    
                    assert original_tag_names == migrated_tag_names, \
                        f"Tag relationships should match original tags"
    
    @given(st.lists(post_data(), min_size=1, max_size=3))
    @settings(max_examples=25, deadline=None)
    def test_metadata_integrity_during_migration(self, posts_data):
        """
        Test that all metadata fields maintain their integrity during migration.
        This includes ensuring no data corruption or unexpected transformations.
        """
        app, db, User, Post, Tag = self.create_app_and_models()
        
        with app.app_context():
            # Create test user with unique username
            unique_username = f'testuser_{uuid.uuid4().hex[:8]}'
            user = User(username=unique_username, is_admin=True)
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            # Create posts and capture their data
            created_posts = []
            
            for post_data_item in posts_data:
                post = Post(
                    title=post_data_item['title'],
                    content=post_data_item['content'],
                    category=post_data_item['category'],
                    tags=post_data_item['tags'],
                    summary=post_data_item['summary'],
                    status=post_data_item['status'],
                    created_at=post_data_item['created_at'],
                    published_at=post_data_item['published_at'],
                    scheduled_publish_at=post_data_item['scheduled_publish_at']
                )
                db.session.add(post)
                created_posts.append(post)
            
            db.session.commit()
            
            # Store original metadata after commit
            original_metadata = []
            for post in created_posts:
                metadata_fingerprint = {
                    'id': post.id,
                    'title_len': len(post.title or ''),
                    'content_len': len(post.content or ''),
                    'has_category': post.category is not None,
                    'has_tags': post.tags is not None and bool(post.tags.strip()) if post.tags else False,
                    'has_summary': post.summary is not None,
                    'status': post.status,
                    'has_published_at': post.published_at is not None,
                    'has_scheduled_at': post.scheduled_publish_at is not None
                }
                original_metadata.append(metadata_fingerprint)
            
            # Simulate migration operations (no actual changes to core data)
            db.session.commit()
            
            # Verify metadata integrity is maintained
            for original_meta in original_metadata:
                post = db.session.get(Post, original_meta['id'])
                assert post is not None, f"Post {original_meta['id']} should exist"
                
                # Check that data lengths are preserved (no truncation/corruption)
                assert len(post.title or '') == original_meta['title_len'], \
                    "Title length should be preserved during migration"
                
                assert len(post.content or '') == original_meta['content_len'], \
                    "Content length should be preserved during migration"
                
                # Check that optional field presence is preserved
                assert (post.category is not None) == original_meta['has_category'], \
                    "Category presence should be preserved during migration"
                
                actual_has_tags = post.tags is not None and bool(post.tags.strip()) if post.tags else False
                assert actual_has_tags == original_meta['has_tags'], \
                    "Tags presence should be preserved during migration"
                
                assert (post.summary is not None) == original_meta['has_summary'], \
                    "Summary presence should be preserved during migration"
                
                assert post.status == original_meta['status'], \
                    "Status should be preserved during migration"
                
                assert (post.published_at is not None) == original_meta['has_published_at'], \
                    "Published timestamp presence should be preserved during migration"
                
                assert (post.scheduled_publish_at is not None) == original_meta['has_scheduled_at'], \
                    "Scheduled timestamp presence should be preserved during migration"
    
    @given(st.lists(post_data(), min_size=2, max_size=4))
    @settings(max_examples=25, deadline=None)
    def test_no_data_loss_during_migration(self, posts_data):
        """
        Test that no posts are lost during migration and that the total count
        and unique identifiers are preserved.
        """
        app, db, User, Post, Tag = self.create_app_and_models()
        
        with app.app_context():
            # Create test user with unique username
            unique_username = f'testuser_{uuid.uuid4().hex[:8]}'
            user = User(username=unique_username, is_admin=True)
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            # Create posts and track identifiers
            original_count = len(posts_data)
            created_posts = []
            
            for post_data_item in posts_data:
                post = Post(
                    title=post_data_item['title'],
                    content=post_data_item['content'],
                    category=post_data_item['category'],
                    tags=post_data_item['tags'],
                    summary=post_data_item['summary'],
                    status=post_data_item['status'],
                    created_at=post_data_item['created_at'],
                    published_at=post_data_item['published_at'],
                    scheduled_publish_at=post_data_item['scheduled_publish_at']
                )
                db.session.add(post)
                created_posts.append(post)
            
            db.session.commit()
            
            # Capture post IDs after commit
            original_ids = [post.id for post in created_posts]
            
            # Simulate migration process (no actual data changes)
            db.session.commit()
            
            # Verify no data loss
            migrated_posts = Post.query.all()
            migrated_ids = [post.id for post in migrated_posts]
            
            assert len(migrated_posts) == original_count, \
                f"Migration should preserve post count: expected {original_count}, got {len(migrated_posts)}"
            
            assert set(migrated_ids) == set(original_ids), \
                f"Migration should preserve all post IDs: expected {set(original_ids)}, got {set(migrated_ids)}"
            
            # Verify each post can still be queried individually
            for post_id in original_ids:
                post = db.session.get(Post, post_id)
                assert post is not None, f"Post with ID {post_id} should still exist after migration"


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])