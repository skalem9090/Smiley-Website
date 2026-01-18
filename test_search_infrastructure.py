"""
Test search infrastructure setup.

This module tests that the FTS5 search infrastructure is properly set up
and working correctly.
"""

import pytest
from app import create_app
from models import db, Post, User, AuthorProfile
from search_engine import SearchEngine
from datetime import datetime, timezone


class TestSearchInfrastructure:
    """Test search infrastructure setup and basic functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with self.app.app_context():
            db.create_all()
            
            # Clear any existing data
            db.session.query(User).delete()
            db.session.query(AuthorProfile).delete()
            db.session.query(Post).delete()
            
            # Create admin user
            admin = User(username='testadmin', is_admin=True)
            admin.set_password('testpass')
            db.session.add(admin)
            
            # Create author profile
            profile = AuthorProfile(
                name="Test Author",
                bio="A test author for search testing.",
                mission_statement="To test search functionality thoroughly.",
                email="test@example.com"
            )
            profile.set_expertise_areas(["Testing", "Search", "FTS5"])
            db.session.add(profile)
            db.session.commit()
            
            # Initialize search engine
            self.search_engine = SearchEngine(self.app)
            self.search_engine.create_search_index()
    
    def test_search_index_creation(self):
        """Test that the search index is created successfully."""
        with self.app.app_context():
            # Check if FTS5 table exists
            result = db.session.execute(
                db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='post_search_fts'")
            ).fetchone()
            
            assert result is not None, "FTS5 search table should be created"
            assert result[0] == 'post_search_fts', "FTS5 table should be named 'post_search_fts'"
    
    def test_post_indexing_on_creation(self):
        """Test that published posts are automatically indexed."""
        with self.app.app_context():
            # Create a published post
            post = Post(
                title="Test Search Post",
                content="<p>This is a test post for search functionality.</p>",
                summary="A test post summary",
                status='published',
                published_at=datetime.now(timezone.utc),
                category='testing'
            )
            db.session.add(post)
            db.session.commit()
            
            # Check if post is in search index
            result = db.session.execute(
                db.text("SELECT COUNT(*) FROM post_search_fts WHERE post_id = :post_id"),
                {'post_id': post.id}
            ).scalar()
            
            assert result == 1, "Published post should be automatically indexed"
    
    def test_draft_post_not_indexed(self):
        """Test that draft posts are not indexed."""
        with self.app.app_context():
            # Create a draft post
            post = Post(
                title="Draft Search Post",
                content="<p>This is a draft post that should not be indexed.</p>",
                status='draft'
            )
            db.session.add(post)
            db.session.commit()
            
            # Check if post is NOT in search index
            result = db.session.execute(
                db.text("SELECT COUNT(*) FROM post_search_fts WHERE post_id = :post_id"),
                {'post_id': post.id}
            ).scalar()
            
            assert result == 0, "Draft post should not be indexed"
    
    def test_post_update_reindexing(self):
        """Test that post updates trigger reindexing."""
        with self.app.app_context():
            # Create a published post
            post = Post(
                title="Original Title",
                content="<p>Original content</p>",
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            db.session.add(post)
            db.session.commit()
            
            # Update the post
            post.title = "Updated Title"
            post.content = "<p>Updated content</p>"
            db.session.commit()
            
            # Check if updated content is in search index
            result = db.session.execute(
                db.text("SELECT title FROM post_search_fts WHERE post_id = :post_id"),
                {'post_id': post.id}
            ).fetchone()
            
            assert result is not None, "Updated post should be in search index"
            assert result[0] == "Updated Title", "Search index should contain updated title"
    
    def test_post_status_change_indexing(self):
        """Test that changing post status updates search index correctly."""
        with self.app.app_context():
            # Create a draft post
            post = Post(
                title="Status Change Post",
                content="<p>This post will change status</p>",
                status='draft'
            )
            db.session.add(post)
            db.session.commit()
            
            # Verify not indexed
            result = db.session.execute(
                db.text("SELECT COUNT(*) FROM post_search_fts WHERE post_id = :post_id"),
                {'post_id': post.id}
            ).scalar()
            assert result == 0, "Draft post should not be indexed"
            
            # Change to published
            post.status = 'published'
            post.published_at = datetime.now(timezone.utc)
            db.session.commit()
            
            # Verify now indexed
            result = db.session.execute(
                db.text("SELECT COUNT(*) FROM post_search_fts WHERE post_id = :post_id"),
                {'post_id': post.id}
            ).scalar()
            assert result == 1, "Published post should be indexed"
            
            # Change back to draft
            post.status = 'draft'
            db.session.commit()
            
            # Verify removed from index
            result = db.session.execute(
                db.text("SELECT COUNT(*) FROM post_search_fts WHERE post_id = :post_id"),
                {'post_id': post.id}
            ).scalar()
            assert result == 0, "Draft post should be removed from index"
    
    def test_post_deletion_removes_from_index(self):
        """Test that deleting a post removes it from search index."""
        with self.app.app_context():
            # Create a published post
            post = Post(
                title="Post to Delete",
                content="<p>This post will be deleted</p>",
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            db.session.add(post)
            db.session.commit()
            
            post_id = post.id
            
            # Verify indexed
            result = db.session.execute(
                db.text("SELECT COUNT(*) FROM post_search_fts WHERE post_id = :post_id"),
                {'post_id': post_id}
            ).scalar()
            assert result == 1, "Published post should be indexed"
            
            # Delete the post
            db.session.delete(post)
            db.session.commit()
            
            # Verify removed from index
            result = db.session.execute(
                db.text("SELECT COUNT(*) FROM post_search_fts WHERE post_id = :post_id"),
                {'post_id': post_id}
            ).scalar()
            assert result == 0, "Deleted post should be removed from index"
    
    def test_basic_search_functionality(self):
        """Test basic search functionality."""
        with self.app.app_context():
            # Create test posts
            post1 = Post(
                title="Python Programming Guide",
                content="<p>Learn Python programming with this comprehensive guide.</p>",
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            
            post2 = Post(
                title="JavaScript Tutorial",
                content="<p>Master JavaScript with practical examples.</p>",
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            
            db.session.add_all([post1, post2])
            db.session.commit()
            
            # Test search
            results = self.search_engine.search_posts("Python")
            
            assert results['total_results'] == 1, "Should find 1 post matching 'Python'"
            assert results['posts'][0]['post'].title == "Python Programming Guide"
            
            # Test search for common word
            results = self.search_engine.search_posts("programming")
            
            assert results['total_results'] >= 1, "Should find posts containing 'programming'"
    
    def test_search_engine_stats(self):
        """Test search engine statistics."""
        with self.app.app_context():
            # Create some test posts
            for i in range(3):
                post = Post(
                    title=f"Test Post {i+1}",
                    content=f"<p>Content for test post {i+1}</p>",
                    status='published',
                    published_at=datetime.now(timezone.utc)
                )
                db.session.add(post)
            
            db.session.commit()
            
            # Get stats
            stats = self.search_engine.get_search_stats()
            
            assert stats['indexed_posts'] == 3, "Should have 3 indexed posts"
            assert stats['published_posts'] == 3, "Should have 3 published posts"
            assert stats['index_coverage'] == 100.0, "Should have 100% index coverage"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])