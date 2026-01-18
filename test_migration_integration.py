"""
Integration test for legacy tag migration functionality.

This test demonstrates the complete migration workflow from legacy
comma-separated tags to proper database relationships.
"""

import pytest
import tempfile
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import db, Tag, Post, User
from tag_manager import TagManager


def test_complete_migration_workflow():
    """Test the complete migration workflow with a temporary database."""
    
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    try:
        # Create Flask app with temporary database
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TESTING'] = True
        
        db.init_app(app)
        
        with app.app_context():
            # Create database tables
            db.create_all()
            
            # Create test user
            user = User(username='testuser')
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            # Create posts with legacy comma-separated tags
            posts_data = [
                {
                    'title': 'Python Tutorial',
                    'content': 'Learn Python programming',
                    'tags': 'Python, Programming, Tutorial',
                    'status': 'published'
                },
                {
                    'title': 'Web Development Guide',
                    'content': 'Build web applications',
                    'tags': 'Python, Web Development, Flask, HTML',
                    'status': 'published'
                },
                {
                    'title': 'JavaScript Basics',
                    'content': 'JavaScript fundamentals',
                    'tags': 'JavaScript, Programming, Web Development',
                    'status': 'draft'
                }
            ]
            
            created_posts = []
            for post_data in posts_data:
                post = Post(
                    title=post_data['title'],
                    content=post_data['content'],
                    tags=post_data['tags'],
                    status=post_data['status']
                )
                db.session.add(post)
                created_posts.append(post)
            
            db.session.commit()
            
            # Verify initial state - no tag relationships exist
            assert Tag.query.count() == 0
            for post in created_posts:
                assert len(post.tag_relationships) == 0
                assert post.tags is not None  # Legacy tags exist
            
            # Run migration
            stats = TagManager.migrate_legacy_tags()
            
            # Verify migration results
            assert stats['posts_processed'] == 3
            assert stats['tags_created'] == 7  # Python, Programming, Tutorial, Web Development, Flask, HTML, JavaScript
            assert stats['associations_created'] == 10  # 3 + 4 + 3
            assert len(stats['errors']) == 0
            
            # Verify tags were created
            all_tags = Tag.query.all()
            tag_names = {tag.name for tag in all_tags}
            expected_tags = {
                'Python', 'Programming', 'Tutorial', 
                'Web Development', 'Flask', 'HTML', 'JavaScript'
            }
            assert tag_names == expected_tags
            
            # Verify each tag has proper slug
            for tag in all_tags:
                assert tag.slug is not None
                assert len(tag.slug) > 0
                assert ' ' not in tag.slug  # No spaces in slugs
            
            # Verify post-tag associations
            posts = Post.query.all()
            for post in posts:
                if post.title == 'Python Tutorial':
                    post_tag_names = {tag.name for tag in post.tag_relationships}
                    assert post_tag_names == {'Python', 'Programming', 'Tutorial'}
                elif post.title == 'Web Development Guide':
                    post_tag_names = {tag.name for tag in post.tag_relationships}
                    assert post_tag_names == {'Python', 'Web Development', 'Flask', 'HTML'}
                elif post.title == 'JavaScript Basics':
                    post_tag_names = {tag.name for tag in post.tag_relationships}
                    assert post_tag_names == {'JavaScript', 'Programming', 'Web Development'}
                
                # Verify legacy tags field is preserved
                assert post.tags is not None
                assert len(post.tags) > 0
            
            # Verify migration is idempotent - run again
            stats2 = TagManager.migrate_legacy_tags()
            
            assert stats2['posts_processed'] == 3
            assert stats2['tags_created'] == 0  # No new tags created
            assert stats2['associations_created'] == 10  # Same associations recreated
            assert len(stats2['errors']) == 0
            
            # Verify final state is unchanged
            assert Tag.query.count() == 7  # Same number of tags
            for post in Post.query.all():
                if post.title == 'Python Tutorial':
                    assert len(post.tag_relationships) == 3
                elif post.title == 'Web Development Guide':
                    assert len(post.tag_relationships) == 4
                elif post.title == 'JavaScript Basics':
                    assert len(post.tag_relationships) == 3
            
            print("✅ Complete migration workflow test passed!")
            print(f"   - Processed {stats['posts_processed']} posts")
            print(f"   - Created {stats['tags_created']} tags")
            print(f"   - Created {stats['associations_created']} associations")
            print(f"   - Migration is idempotent ✓")
            print(f"   - Legacy data preserved ✓")
            
    finally:
        # Clean up temporary database file
        try:
            os.close(db_fd)
            os.unlink(db_path)
        except (OSError, PermissionError):
            # File cleanup failed, but test still passed
            pass


if __name__ == '__main__':
    test_complete_migration_workflow()
    print("\n🎉 All integration tests passed!")