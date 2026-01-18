#!/usr/bin/env python3
"""
Legacy Tag Migration Script

This script migrates existing posts with comma-separated tag strings to proper
database relationships using the new Tag model and post_tags association table.

The migration preserves existing tag data while creating proper database 
relationships as specified in requirement 4.1.

Usage:
    python migrate_legacy_tags.py [--dry-run] [--verbose]
    
Options:
    --dry-run    Show what would be migrated without making changes
    --verbose    Show detailed migration progress
"""

import argparse
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import db, Post, Tag
from tag_manager import TagManager


def create_app():
    """Create Flask application for migration."""
    app = Flask(__name__)
    
    # Configure database - adjust as needed for your environment
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'  # Default SQLite
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    return app


def analyze_legacy_data(verbose=False):
    """
    Analyze existing legacy tag data to show what will be migrated.
    
    Args:
        verbose: Show detailed analysis
        
    Returns:
        Dictionary with analysis results
    """
    analysis = {
        'total_posts': Post.query.count(),
        'posts_with_legacy_tags': 0,
        'unique_legacy_tags': set(),
        'posts_with_relationships': 0,
        'sample_posts': []
    }
    
    # Find posts with legacy tags
    posts_with_tags = Post.query.filter(
        Post.tags.isnot(None),
        Post.tags != ''
    ).all()
    
    analysis['posts_with_legacy_tags'] = len(posts_with_tags)
    
    # Analyze legacy tags
    for post in posts_with_tags:
        tag_names = [tag.strip() for tag in post.tags.split(',') if tag.strip()]
        analysis['unique_legacy_tags'].update(tag_names)
        
        if len(analysis['sample_posts']) < 5:  # Show first 5 as samples
            analysis['sample_posts'].append({
                'id': post.id,
                'title': post.title[:50] + '...' if len(post.title) > 50 else post.title,
                'legacy_tags': post.tags,
                'parsed_tags': tag_names
            })
    
    # Count posts that already have tag relationships
    posts_with_relationships = Post.query.join(Post.tag_relationships).distinct().count()
    analysis['posts_with_relationships'] = posts_with_relationships
    
    return analysis


def print_analysis(analysis, verbose=False):
    """Print migration analysis results."""
    print("=== Legacy Tag Migration Analysis ===")
    print(f"Total posts in database: {analysis['total_posts']}")
    print(f"Posts with legacy comma-separated tags: {analysis['posts_with_legacy_tags']}")
    print(f"Posts with existing tag relationships: {analysis['posts_with_relationships']}")
    print(f"Unique legacy tags found: {len(analysis['unique_legacy_tags'])}")
    
    if verbose and analysis['unique_legacy_tags']:
        print("\nUnique legacy tags:")
        for tag in sorted(analysis['unique_legacy_tags']):
            print(f"  - {tag}")
    
    if analysis['sample_posts']:
        print("\nSample posts with legacy tags:")
        for post in analysis['sample_posts']:
            print(f"  Post {post['id']}: {post['title']}")
            print(f"    Legacy tags: {post['legacy_tags']}")
            print(f"    Parsed tags: {', '.join(post['parsed_tags'])}")
            print()


def run_migration(dry_run=False, verbose=False):
    """
    Run the legacy tag migration.
    
    Args:
        dry_run: If True, show what would be done without making changes
        verbose: Show detailed progress
        
    Returns:
        Migration statistics
    """
    if dry_run:
        print("=== DRY RUN MODE - No changes will be made ===")
    else:
        print("=== Running Legacy Tag Migration ===")
    
    if dry_run:
        # For dry run, just analyze the data
        analysis = analyze_legacy_data(verbose)
        print_analysis(analysis, verbose)
        
        # Estimate what would be created
        existing_tags = {tag.name.lower() for tag in Tag.query.all()}
        new_tags_needed = set()
        
        posts_with_tags = Post.query.filter(
            Post.tags.isnot(None),
            Post.tags != ''
        ).all()
        
        for post in posts_with_tags:
            tag_names = [tag.strip() for tag in post.tags.split(',') if tag.strip()]
            for tag_name in tag_names:
                if tag_name.lower() not in existing_tags:
                    new_tags_needed.add(tag_name)
        
        print(f"\nDry run results:")
        print(f"  Posts to be processed: {len(posts_with_tags)}")
        print(f"  New tags to be created: {len(new_tags_needed)}")
        print(f"  Estimated associations to be created: {sum(len([t.strip() for t in post.tags.split(',') if t.strip()]) for post in posts_with_tags)}")
        
        if verbose and new_tags_needed:
            print("\nNew tags that would be created:")
            for tag in sorted(new_tags_needed):
                print(f"  - {tag}")
        
        return {
            'posts_processed': len(posts_with_tags),
            'tags_created': len(new_tags_needed),
            'associations_created': sum(len([t.strip() for t in post.tags.split(',') if t.strip()]) for post in posts_with_tags),
            'errors': []
        }
    else:
        # Run actual migration
        try:
            stats = TagManager.migrate_legacy_tags()
            
            print(f"Migration completed successfully!")
            print(f"  Posts processed: {stats['posts_processed']}")
            print(f"  New tags created: {stats['tags_created']}")
            print(f"  Tag associations created: {stats['associations_created']}")
            
            if stats['errors']:
                print(f"  Errors encountered: {len(stats['errors'])}")
                if verbose:
                    print("\nErrors:")
                    for error in stats['errors']:
                        print(f"  - {error}")
            
            return stats
            
        except Exception as e:
            print(f"Migration failed: {str(e)}")
            return {
                'posts_processed': 0,
                'tags_created': 0,
                'associations_created': 0,
                'errors': [str(e)]
            }


def main():
    """Main migration script entry point."""
    parser = argparse.ArgumentParser(
        description='Migrate legacy comma-separated tags to database relationships'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be migrated without making changes'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed migration progress'
    )
    
    args = parser.parse_args()
    
    # Create Flask app and initialize database
    app = create_app()
    
    with app.app_context():
        try:
            # Verify database connection
            with db.engine.connect() as connection:
                connection.execute(db.text('SELECT 1'))
            
            # Run migration
            stats = run_migration(dry_run=args.dry_run, verbose=args.verbose)
            
            # Exit with error code if there were errors
            if stats['errors']:
                sys.exit(1)
            else:
                sys.exit(0)
                
        except Exception as e:
            print(f"Failed to connect to database or run migration: {str(e)}")
            sys.exit(1)


if __name__ == '__main__':
    main()