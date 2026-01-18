"""
Unit tests for legacy tag migration functionality.

Tests the migrate_legacy_tags method in TagManager to ensure it correctly
converts comma-separated tag strings to proper database relationships
while preserving existing data.

Requirements: 4.1
"""

import pytest
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
        return user.id


class TestLegacyTagMigration:
    """Test suite for legacy tag migration functionality."""
    
    def test_migrate_empty_database(self, app):
        """Test migration with no posts in database."""
        with app.app_context():
            stats = TagManager.migrate_legacy_tags()
            
            assert stats['posts_processed'] == 0
            assert stats['tags_created'] == 0
            assert stats['associations_created'] == 0
            assert len(stats['errors']) == 0
    
    def test_migrate_posts_without_legacy_tags(self, app, sample_user):
        """Test migration with posts that have no legacy tags."""
        with app.app_context():
            # Create posts without legacy tags
            post1 = Post(title='Post 1', content='Content 1', status='published')
            post2 = Post(title='Post 2', content='Content 2', tags='', status='published')
            post3 = Post(title='Post 3', content='Content 3', tags=None, status='published')
            
            db.session.add_all([post1, post2, post3])
            db.session.commit()
            
            stats = TagManager.migrate_legacy_tags()
            
            assert stats['posts_processed'] == 0
            assert stats['tags_created'] == 0
            assert stats['associations_created'] == 0
            assert len(stats['errors']) == 0
    
    def test_migrate_single_post_with_tags(self, app, sample_user):
        """Test migration of a single post with comma-separated tags."""
        with app.app_context():
            # Create post with legacy tags
            post = Post(
                title='Test Post',
                content='Test content',
                tags='Python, Web Development, Flask',
                status='published'
            )
            db.session.add(post)
            db.session.commit()
            
            # Run migration
            stats = TagManager.migrate_legacy_tags()
            
            # Verify statistics
            assert stats['posts_processed'] == 1
            assert stats['tags_created'] == 3
            assert stats['associations_created'] == 3
            assert len(stats['errors']) == 0
            
            # Verify tags were created
            python_tag = Tag.query.filter_by(name='Python').first()
            web_dev_tag = Tag.query.filter_by(name='Web Development').first()
            flask_tag = Tag.query.filter_by(name='Flask').first()
            
            assert python_tag is not None
            assert python_tag.slug == 'python'
            assert web_dev_tag is not None
            assert web_dev_tag.slug == 'web-development'
            assert flask_tag is not None
            assert flask_tag.slug == 'flask'
            
            # Verify post-tag associations
            post = Post.query.first()
            assert len(post.tag_relationships) == 3
            
            tag_names = {tag.name for tag in post.tag_relationships}
            assert tag_names == {'Python', 'Web Development', 'Flask'}
            
            # Verify legacy tags field is preserved
            assert post.tags == 'Python, Web Development, Flask'
    
    def test_migrate_multiple_posts_with_overlapping_tags(self, app, sample_user):
        """Test migration of multiple posts with some overlapping tags."""
        with app.app_context():
            # Create posts with overlapping tags
            post1 = Post(
                title='Post 1',
                content='Content 1',
                tags='Python, Flask, Web Development',
                status='published'
            )
            post2 = Post(
                title='Post 2',
                content='Content 2',
                tags='Python, Django, Web Development',
                status='published'
            )
            post3 = Post(
                title='Post 3',
                content='Content 3',
                tags='JavaScript, React',
                status='published'
            )
            
            db.session.add_all([post1, post2, post3])
            db.session.commit()
            
            # Run migration
            stats = TagManager.migrate_legacy_tags()
            
            # Verify statistics
            assert stats['posts_processed'] == 3
            assert stats['tags_created'] == 6  # Python, Flask, Web Development, Django, JavaScript, React
            assert stats['associations_created'] == 8  # 3 + 3 + 2
            assert len(stats['errors']) == 0
            
            # Verify unique tags were created
            all_tags = Tag.query.all()
            tag_names = {tag.name for tag in all_tags}
            expected_tags = {'Python', 'Flask', 'Web Development', 'Django', 'JavaScript', 'React'}
            assert tag_names == expected_tags
            
            # Verify each post has correct associations
            posts = Post.query.all()
            for post in posts:
                if post.title == 'Post 1':
                    post_tag_names = {tag.name for tag in post.tag_relationships}
                    assert post_tag_names == {'Python', 'Flask', 'Web Development'}
                elif post.title == 'Post 2':
                    post_tag_names = {tag.name for tag in post.tag_relationships}
                    assert post_tag_names == {'Python', 'Django', 'Web Development'}
                elif post.title == 'Post 3':
                    post_tag_names = {tag.name for tag in post.tag_relationships}
                    assert post_tag_names == {'JavaScript', 'React'}
    
    def test_migrate_with_existing_tags(self, app, sample_user):
        """Test migration when some tags already exist in the database."""
        with app.app_context():
            # Create existing tags
            existing_tag = TagManager.get_or_create_tag('Python')
            
            # Create post with mix of existing and new tags
            post = Post(
                title='Test Post',
                content='Test content',
                tags='Python, New Tag, Another Tag',
                status='published'
            )
            db.session.add(post)
            db.session.commit()
            
            # Run migration
            stats = TagManager.migrate_legacy_tags()
            
            # Verify statistics
            assert stats['posts_processed'] == 1
            assert stats['tags_created'] == 2  # Only new tags created
            assert stats['associations_created'] == 3
            assert len(stats['errors']) == 0
            
            # Verify existing tag was reused
            python_tag = Tag.query.filter_by(name='Python').first()
            assert python_tag.id == existing_tag.id
            
            # Verify new tags were created
            new_tag = Tag.query.filter_by(name='New Tag').first()
            another_tag = Tag.query.filter_by(name='Another Tag').first()
            assert new_tag is not None
            assert another_tag is not None
            
            # Verify associations
            post = Post.query.first()
            tag_names = {tag.name for tag in post.tag_relationships}
            assert tag_names == {'Python', 'New Tag', 'Another Tag'}
    
    def test_migrate_with_whitespace_and_empty_tags(self, app, sample_user):
        """Test migration handles whitespace and empty tags correctly."""
        with app.app_context():
            # Create post with messy tag string
            post = Post(
                title='Test Post',
                content='Test content',
                tags='  Python  , , Web Development,   ,Flask,  ',
                status='published'
            )
            db.session.add(post)
            db.session.commit()
            
            # Run migration
            stats = TagManager.migrate_legacy_tags()
            
            # Verify statistics
            assert stats['posts_processed'] == 1
            assert stats['tags_created'] == 3  # Empty strings should be filtered out
            assert stats['associations_created'] == 3
            assert len(stats['errors']) == 0
            
            # Verify only valid tags were created
            post = Post.query.first()
            tag_names = {tag.name for tag in post.tag_relationships}
            assert tag_names == {'Python', 'Web Development', 'Flask'}
    
    def test_migrate_case_insensitive_tag_matching(self, app, sample_user):
        """Test that migration handles case-insensitive tag matching."""
        with app.app_context():
            # Create existing tag with specific case
            existing_tag = TagManager.get_or_create_tag('Python')
            
            # Create post with different case
            post = Post(
                title='Test Post',
                content='Test content',
                tags='python, PYTHON, Python',
                status='published'
            )
            db.session.add(post)
            db.session.commit()
            
            # Run migration
            stats = TagManager.migrate_legacy_tags()
            
            # Verify statistics
            assert stats['posts_processed'] == 1
            assert stats['tags_created'] == 0  # No new tags should be created
            assert stats['associations_created'] == 1  # Only one association (duplicates removed)
            assert len(stats['errors']) == 0
            
            # Verify only one tag exists and it's the original
            python_tags = Tag.query.filter_by(name='Python').all()
            assert len(python_tags) == 1
            assert python_tags[0].id == existing_tag.id
            
            # Verify single association
            post = Post.query.first()
            assert len(post.tag_relationships) == 1
            assert post.tag_relationships[0].name == 'Python'
    
    def test_migrate_preserves_legacy_tags_field(self, app, sample_user):
        """Test that migration preserves the original legacy tags field."""
        with app.app_context():
            original_tags = 'Python, Web Development, Flask'
            
            post = Post(
                title='Test Post',
                content='Test content',
                tags=original_tags,
                status='published'
            )
            db.session.add(post)
            db.session.commit()
            
            # Run migration
            TagManager.migrate_legacy_tags()
            
            # Verify legacy field is preserved
            post = Post.query.first()
            assert post.tags == original_tags
    
    def test_migrate_clears_existing_relationships(self, app, sample_user):
        """Test that migration clears existing tag relationships before creating new ones."""
        with app.app_context():
            # Create post and manually add some tag relationships
            post = Post(
                title='Test Post',
                content='Test content',
                tags='Python, Flask',
                status='published'
            )
            db.session.add(post)
            db.session.commit()
            
            # Manually create some existing relationships
            old_tag = TagManager.get_or_create_tag('Old Tag')
            post.tag_relationships.append(old_tag)
            db.session.commit()
            
            # Verify old relationship exists
            assert len(post.tag_relationships) == 1
            assert post.tag_relationships[0].name == 'Old Tag'
            
            # Run migration
            stats = TagManager.migrate_legacy_tags()
            
            # Verify old relationships were cleared and new ones created
            post = Post.query.first()
            tag_names = {tag.name for tag in post.tag_relationships}
            assert tag_names == {'Python', 'Flask'}
            assert 'Old Tag' not in tag_names
    
    def test_migrate_handles_slug_conflicts(self, app, sample_user):
        """Test that migration handles slug conflicts correctly."""
        with app.app_context():
            # Create existing tag with specific slug
            existing_tag = Tag(name='Test', slug='python')
            db.session.add(existing_tag)
            db.session.commit()
            
            # Create post with tag that would generate conflicting slug
            post = Post(
                title='Test Post',
                content='Test content',
                tags='Python',  # Would normally generate 'python' slug
                status='published'
            )
            db.session.add(post)
            db.session.commit()
            
            # Run migration
            stats = TagManager.migrate_legacy_tags()
            
            # Verify migration succeeded
            assert stats['posts_processed'] == 1
            assert stats['tags_created'] == 1
            assert len(stats['errors']) == 0
            
            # Verify new tag got unique slug
            python_tag = Tag.query.filter_by(name='Python').first()
            assert python_tag is not None
            assert python_tag.slug == 'python-1'  # Should get incremented slug
    
    def test_migrate_multiple_runs_idempotent(self, app, sample_user):
        """Test that running migration multiple times is safe (idempotent)."""
        with app.app_context():
            # Create post with tags
            post = Post(
                title='Test Post',
                content='Test content',
                tags='Python, Flask',
                status='published'
            )
            db.session.add(post)
            db.session.commit()
            
            # Run migration first time
            stats1 = TagManager.migrate_legacy_tags()
            
            # Verify first run
            assert stats1['posts_processed'] == 1
            assert stats1['tags_created'] == 2
            assert stats1['associations_created'] == 2
            
            # Run migration second time
            stats2 = TagManager.migrate_legacy_tags()
            
            # Verify second run processes the same post but creates no new tags
            assert stats2['posts_processed'] == 1
            assert stats2['tags_created'] == 0  # No new tags created
            assert stats2['associations_created'] == 2  # Same associations recreated
            
            # Verify final state is correct
            post = Post.query.first()
            tag_names = {tag.name for tag in post.tag_relationships}
            assert tag_names == {'Python', 'Flask'}
            
            # Verify no duplicate tags were created
            all_tags = Tag.query.all()
            assert len(all_tags) == 2


class TestMigrationErrorHandling:
    """Test error handling in migration functionality."""
    
    def test_migration_continues_on_individual_post_errors(self, app, sample_user):
        """Test that migration continues processing other posts if one fails."""
        with app.app_context():
            # Create valid posts
            post1 = Post(
                title='Valid Post 1',
                content='Content 1',
                tags='Python, Flask',
                status='published'
            )
            post2 = Post(
                title='Valid Post 2',
                content='Content 2',
                tags='JavaScript, React',
                status='published'
            )
            
            db.session.add_all([post1, post2])
            db.session.commit()
            
            # Run migration
            stats = TagManager.migrate_legacy_tags()
            
            # Verify migration processed valid posts
            assert stats['posts_processed'] == 2
            assert stats['tags_created'] == 4
            assert stats['associations_created'] == 4
            
            # Verify tags were created for both posts
            all_tags = Tag.query.all()
            tag_names = {tag.name for tag in all_tags}
            assert tag_names == {'Python', 'Flask', 'JavaScript', 'React'}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])