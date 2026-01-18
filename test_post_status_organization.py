"""
Property-Based Test: Post Status Organization

**Property 3: Post Status Organization**
**Validates: Requirements 1.4, 6.1, 6.2, 6.4**

This test validates that posts are correctly organized by status in the dashboard
interface, ensuring proper categorization and metadata display.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime, timezone, timedelta
from models import db, Post
from post_manager import PostManager
from app import create_app


# Test data generators
@st.composite
def post_data(draw):
    """Generate valid post data with various statuses."""
    title = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    content = draw(st.text(min_size=1, max_size=500).filter(lambda x: x.strip()))
    category = draw(st.one_of(st.none(), st.sampled_from(['wealth', 'health', 'happiness'])))
    status = draw(st.sampled_from(['draft', 'published', 'scheduled']))
    
    # Generate scheduled time for scheduled posts
    scheduled_time = None
    if status == 'scheduled':
        future_time = datetime.now(timezone.utc) + timedelta(hours=draw(st.integers(1, 168)))  # 1 hour to 1 week
        scheduled_time = future_time
    
    return {
        'title': title,
        'content': content,
        'category': category,
        'status': status,
        'scheduled_time': scheduled_time
    }


@st.composite
def multiple_posts_data(draw):
    """Generate multiple posts with different statuses."""
    num_posts = draw(st.integers(min_value=1, max_value=8))  # Reduced for faster tests
    posts = []
    
    for _ in range(num_posts):
        post = draw(post_data())
        posts.append(post)
    
    return posts


class TestPostStatusOrganization:
    """Test post status organization functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application and database."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with self.app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()
    
    def _clean_database(self):
        """Clean all data from the database."""
        # Delete all posts and related data
        from models import post_tags, Tag
        db.session.execute(post_tags.delete())
        db.session.query(Post).delete()
        db.session.query(Tag).delete()
        db.session.commit()
    
    @given(multiple_posts_data())
    @settings(max_examples=20, deadline=5000)  # Reduced examples for faster execution
    def test_posts_organized_by_status_property(self, posts_data):
        """
        **Property 3: Post Status Organization**
        **Validates: Requirements 1.4, 6.1, 6.2, 6.4**
        
        Property: Posts are correctly organized by status with proper metadata.
        
        For any collection of posts with different statuses:
        1. Posts are grouped correctly by their status
        2. Each status group contains only posts with that status
        3. Post metadata is correctly calculated and included
        4. Status groups are properly structured for dashboard display
        """
        with self.app.app_context():
            self._clean_database()  # Clean database before test
            created_posts = []
            
            # Create posts using PostManager
            for post_data in posts_data:
                try:
                    post = PostManager.create_post(
                        title=post_data['title'],
                        content=post_data['content'],
                        category=post_data['category'],
                        status=post_data['status'],
                        scheduled_time=post_data['scheduled_time'],
                        allow_past_schedule=True  # Allow for testing
                    )
                    created_posts.append(post)
                except ValueError:
                    # Skip invalid posts (e.g., scheduled without time)
                    continue
            
            assume(len(created_posts) > 0)  # Need at least one valid post
            
            # Get organized posts
            organized_posts = PostManager.get_posts_organized_by_status()
            
            # Verify structure
            assert isinstance(organized_posts, dict)
            assert set(organized_posts.keys()) == {'draft', 'published', 'scheduled'}
            
            # Count posts by status from created posts
            expected_counts = {'draft': 0, 'published': 0, 'scheduled': 0}
            for post in created_posts:
                expected_counts[post.status] += 1
            
            # Verify each status group
            for status in ['draft', 'published', 'scheduled']:
                status_posts = organized_posts[status]
                assert isinstance(status_posts, list)
                assert len(status_posts) == expected_counts[status]
                
                # Verify each post in the status group
                for post_metadata in status_posts:
                    assert isinstance(post_metadata, dict)
                    
                    # Find the corresponding created post
                    created_post = next(p for p in created_posts if p.id == post_metadata['id'])
                    
                    # Verify metadata correctness
                    assert post_metadata['title'] == created_post.title
                    assert post_metadata['status'] == status
                    assert post_metadata['category'] == created_post.category
                    assert post_metadata['created_at'] == created_post.created_at
                    assert post_metadata['published_at'] == created_post.published_at
                    assert post_metadata['scheduled_publish_at'] == created_post.scheduled_publish_at
                    
                    # Verify tag count (should be 0 for new posts)
                    assert post_metadata['tag_count'] == 0
                    
                    # Verify summary is present
                    assert 'summary' in post_metadata
                    assert post_metadata['summary'] is not None
                    
                    # Verify content length
                    assert post_metadata['content_length'] == len(created_post.content)
                    
                    # Verify display date logic
                    expected_display_date = (
                        created_post.published_at or 
                        created_post.scheduled_publish_at or 
                        created_post.created_at
                    )
                    assert post_metadata['display_date'] == expected_display_date
    
    @given(st.integers(min_value=0, max_value=5))
    @settings(max_examples=10, deadline=3000)
    def test_empty_status_groups_property(self, num_posts):
        """
        Property: Empty status groups are handled correctly.
        
        When there are no posts for a particular status, the organized
        posts should still include that status with an empty list.
        """
        with self.app.app_context():
            self._clean_database()  # Clean database before test
            # Create posts with only one status
            if num_posts > 0:
                for i in range(num_posts):
                    PostManager.create_post(
                        title=f'Test Post {i}',
                        content=f'Content {i}',
                        status='draft'  # Only create draft posts
                    )
            
            organized_posts = PostManager.get_posts_organized_by_status()
            
            # Verify structure is always complete
            assert set(organized_posts.keys()) == {'draft', 'published', 'scheduled'}
            
            # Verify draft posts exist if we created any
            assert len(organized_posts['draft']) == num_posts
            
            # Verify other statuses are empty
            assert len(organized_posts['published']) == 0
            assert len(organized_posts['scheduled']) == 0
            
            # Verify all values are lists
            for status_posts in organized_posts.values():
                assert isinstance(status_posts, list)
    
    @given(st.sampled_from(['draft', 'published', 'scheduled']))
    @settings(max_examples=15, deadline=3000)
    def test_single_status_organization_property(self, status):
        """
        Property: Posts with a single status are organized correctly.
        
        When all posts have the same status, they should all appear
        in the correct status group with proper metadata.
        """
        with self.app.app_context():
            self._clean_database()  # Clean database before test
            num_posts = 3
            created_posts = []
            
            for i in range(num_posts):
                scheduled_time = None
                if status == 'scheduled':
                    scheduled_time = datetime.now(timezone.utc) + timedelta(hours=i + 1)
                
                post = PostManager.create_post(
                    title=f'Test Post {i}',
                    content=f'Content for post {i}',
                    status=status,
                    scheduled_time=scheduled_time,
                    allow_past_schedule=True
                )
                created_posts.append(post)
            
            organized_posts = PostManager.get_posts_organized_by_status()
            
            # Verify the target status has all posts
            assert len(organized_posts[status]) == num_posts
            
            # Verify other statuses are empty
            for other_status in ['draft', 'published', 'scheduled']:
                if other_status != status:
                    assert len(organized_posts[other_status]) == 0
            
            # Verify post order (should be by creation time, descending)
            status_posts = organized_posts[status]
            for i in range(len(status_posts) - 1):
                current_post = status_posts[i]
                next_post = status_posts[i + 1]
                # Posts should be ordered by creation time (newest first)
                assert current_post['created_at'] >= next_post['created_at']
    
    def test_post_metadata_completeness_property(self):
        """
        Property: Post metadata includes all required fields.
        
        Every post in the organized structure should have complete
        metadata for dashboard display.
        """
        with self.app.app_context():
            self._clean_database()  # Clean database before test
            # Create a post with all possible fields
            post = PostManager.create_post(
                title='Complete Test Post',
                content='This is a complete test post with all fields.',
                category='wealth',
                summary='Custom summary',
                status='published'
            )
            
            organized_posts = PostManager.get_posts_organized_by_status()
            published_posts = organized_posts['published']
            
            assert len(published_posts) == 1
            post_metadata = published_posts[0]
            
            # Verify all required metadata fields are present
            required_fields = [
                'id', 'title', 'status', 'category', 'created_at',
                'published_at', 'scheduled_publish_at', 'display_date',
                'tag_count', 'summary', 'content_length'
            ]
            
            for field in required_fields:
                assert field in post_metadata, f"Missing required field: {field}"
            
            # Verify field types and values
            assert isinstance(post_metadata['id'], int)
            assert isinstance(post_metadata['title'], str)
            assert isinstance(post_metadata['status'], str)
            assert post_metadata['category'] in [None, 'wealth', 'health', 'happiness']
            assert isinstance(post_metadata['tag_count'], int)
            assert isinstance(post_metadata['summary'], str)
            assert isinstance(post_metadata['content_length'], int)
            
            # Verify published post has published_at set
            assert post_metadata['published_at'] is not None
            assert post_metadata['scheduled_publish_at'] is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])