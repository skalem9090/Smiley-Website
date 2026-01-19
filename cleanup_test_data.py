#!/usr/bin/env python3
"""
Clean up test data from Smiley's Blog database
"""

import os
from app import create_app
from models import db, NewsletterSubscription, Comment, SearchQuery

def cleanup_test_data():
    """Remove test data from the database"""
    
    # Set environment variables
    os.environ['SECRET_KEY'] = '85f58c823f8812dd4d4d24250b9e278900d3744e566ef92a97514ea6dbf64feb'
    os.environ['DATABASE_URL'] = 'sqlite:///C:\\Users\\skale\\OneDrive\\Desktop\\SmileyWebsite\\Smiley-Website\\instance\\site.db'
    
    app = create_app()
    with app.app_context():
        print("🧹 Cleaning up test data from Smiley's Blog...")
        print("=" * 50)
        
        # Count current data
        subscribers_before = NewsletterSubscription.query.count()
        comments_before = Comment.query.count()
        searches_before = SearchQuery.query.count()
        
        print(f"📊 Current data:")
        print(f"   Subscribers: {subscribers_before}")
        print(f"   Comments: {comments_before}")
        print(f"   Search queries: {searches_before}")
        print()
        
        # Ask for confirmation
        response = input("🗑️  Delete all test data? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ Cleanup cancelled.")
            return
        
        print("🧹 Cleaning up...")
        
        # Delete test newsletter subscriptions
        test_subscribers = NewsletterSubscription.query.filter(
            NewsletterSubscription.email.like('%@example.com')
        ).all()
        
        for sub in test_subscribers:
            db.session.delete(sub)
        
        # Delete test comments (if any)
        test_comments = Comment.query.filter(
            Comment.author_email.like('%@example.com')
        ).all()
        
        for comment in test_comments:
            db.session.delete(comment)
        
        # Delete old search queries (keep recent ones)
        old_searches = SearchQuery.query.limit(1000).all()  # Keep some for analytics
        for search in old_searches[:-50]:  # Keep last 50
            db.session.delete(search)
        
        # Commit changes
        db.session.commit()
        
        # Count after cleanup
        subscribers_after = NewsletterSubscription.query.count()
        comments_after = Comment.query.count()
        searches_after = SearchQuery.query.count()
        
        print("✅ Cleanup complete!")
        print()
        print(f"📊 After cleanup:")
        print(f"   Subscribers: {subscribers_after} (removed {subscribers_before - subscribers_after})")
        print(f"   Comments: {comments_after} (removed {comments_before - comments_after})")
        print(f"   Search queries: {searches_after} (removed {searches_before - searches_after})")
        print()
        print("🚀 Your blog is now clean and ready for real users!")

if __name__ == '__main__':
    cleanup_test_data()