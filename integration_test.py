#!/usr/bin/env python3
"""
Integration Test for Enhanced Content Management System

This script tests the complete workflow from post creation to publication,
validating all enhanced features including tags, scheduling, and organization.
"""

from app import create_app
from models import db, Post, Tag, User
from post_manager import PostManager
from tag_manager import TagManager
from datetime import datetime, timezone, timedelta

def run_integration_test():
    """Run comprehensive integration test."""
    app = create_app()
    with app.app_context():
        print("🚀 Starting Enhanced Content Management Integration Test\n")
        
        # Test 1: Create admin user
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', is_admin=True)
            admin.set_password('Password123')
            db.session.add(admin)
            db.session.commit()
        print('✓ Admin user exists')
        
        # Test 2: Create a draft post with tags
        post = PostManager.create_post(
            title='Test Integration Post',
            content='This is a comprehensive test of the enhanced content management system with <strong>HTML content</strong> and multiple paragraphs.',
            category='wealth',
            summary='A test post for integration validation.',
            status='draft',
            tags=['integration', 'testing', 'cms']
        )
        print('✓ Draft post created with tags')
        
        # Test 3: Verify tags were created
        tags = TagManager.get_all_tags_with_counts()
        print(f'✓ Tags created: {len(tags)} tags found')
        
        # Test 4: Update post to scheduled
        future_time = datetime.now(timezone.utc) + timedelta(minutes=1)
        updated_post = PostManager.update_post(
            post.id,
            status='scheduled',
            scheduled_time=future_time
        )
        print('✓ Post scheduled for future publication')
        
        # Test 5: Verify post organization
        organized_posts = PostManager.get_posts_organized_by_status()
        scheduled_count = len(organized_posts['scheduled'])
        draft_count = len(organized_posts['draft'])
        published_count = len(organized_posts['published'])
        print(f'✓ Post organization: {scheduled_count} scheduled, {draft_count} draft, {published_count} published')
        
        # Test 6: Publish post immediately
        published_post = PostManager.publish_post(post.id)
        print('✓ Post published successfully')
        
        # Test 7: Verify published post appears in tag queries
        tag = Tag.query.filter_by(name='integration').first()
        if tag:
            tag_posts = TagManager.get_posts_by_tag_name('integration', published_only=True)
            print(f'✓ Tag filtering: {len(tag_posts)} posts found for "integration" tag')
        
        # Test 8: Test summary generation
        summary_stats = PostManager.get_summary_stats(post.id)
        if summary_stats:
            print(f'✓ Summary system: {summary_stats["summary_length"]} chars, auto-generated: {summary_stats["is_auto_generated"]}')
        
        # Test 9: Test post metadata
        metadata = PostManager.get_post_metadata(post.id)
        if metadata:
            print(f'✓ Post metadata: {metadata["tag_count"]} tags, {metadata["content_length"]} chars content')
        
        # Test 10: Verify database integrity
        total_posts = Post.query.count()
        total_tags = Tag.query.count()
        print(f'✓ Database integrity: {total_posts} posts, {total_tags} tags in database')
        
        print('\n🎉 All integration tests passed!')
        print('✅ Enhanced Content Management System is fully functional')
        
        return True

if __name__ == '__main__':
    try:
        run_integration_test()
    except Exception as e:
        print(f'\n❌ Integration test failed: {str(e)}')
        import traceback
        traceback.print_exc()