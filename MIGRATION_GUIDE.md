# Legacy Tag Migration Guide

This guide explains how to migrate existing posts with comma-separated tag strings to proper database relationships using the new Tag model and post_tags association table.

## Overview

The legacy tag migration functionality converts existing posts that have comma-separated tag strings in the 'tags' field to proper database relationships while preserving the original tags field for backward compatibility.

## Features

- **Data Preservation**: All existing post data is preserved during migration
- **Backward Compatibility**: Legacy tags field is maintained for compatibility
- **Idempotent**: Safe to run multiple times without creating duplicates
- **Error Handling**: Continues processing even if individual posts fail
- **Case Insensitive**: Handles duplicate tags with different cases correctly
- **Slug Generation**: Automatically generates SEO-friendly URL slugs for tags

## Usage

### Method 1: Using the Migration Script

The migration script provides a command-line interface for running the migration:

```bash
# Dry run - see what would be migrated without making changes
python migrate_legacy_tags.py --dry-run --verbose

# Run the actual migration
python migrate_legacy_tags.py --verbose

# Run migration silently
python migrate_legacy_tags.py
```

**Options:**
- `--dry-run`: Show what would be migrated without making changes
- `--verbose` or `-v`: Show detailed migration progress

### Method 2: Using TagManager Directly

You can also run the migration programmatically using the TagManager class:

```python
from tag_manager import TagManager

# Run migration and get statistics
stats = TagManager.migrate_legacy_tags()

print(f"Posts processed: {stats['posts_processed']}")
print(f"Tags created: {stats['tags_created']}")
print(f"Associations created: {stats['associations_created']}")

if stats['errors']:
    print(f"Errors: {len(stats['errors'])}")
    for error in stats['errors']:
        print(f"  - {error}")
```

## Migration Process

The migration process follows these steps:

1. **Find Posts**: Identifies all posts with non-empty legacy tags fields
2. **Parse Tags**: Splits comma-separated tag strings and trims whitespace
3. **Create Tags**: Creates new Tag entities for unique tag names (case-insensitive)
4. **Generate Slugs**: Creates SEO-friendly URL slugs for each tag
5. **Handle Conflicts**: Ensures slug uniqueness by appending numbers if needed
6. **Create Associations**: Establishes many-to-many relationships between posts and tags
7. **Preserve Data**: Maintains original tags field for backward compatibility

## Example

**Before Migration:**
```
Post 1: tags = "Python, Web Development, Flask"
Post 2: tags = "Python, Django, Web Development"
```

**After Migration:**
```
Tags Table:
- Tag(id=1, name="Python", slug="python")
- Tag(id=2, name="Web Development", slug="web-development")  
- Tag(id=3, name="Flask", slug="flask")
- Tag(id=4, name="Django", slug="django")

Post-Tag Associations:
- Post 1 → [Python, Web Development, Flask]
- Post 2 → [Python, Django, Web Development]

Legacy fields preserved:
- Post 1: tags = "Python, Web Development, Flask"
- Post 2: tags = "Python, Django, Web Development"
```

## Migration Statistics

The migration returns detailed statistics:

```python
{
    'posts_processed': 15,      # Number of posts with legacy tags
    'tags_created': 25,         # Number of new Tag entities created
    'associations_created': 45, # Number of post-tag relationships created
    'errors': []                # List of any errors encountered
}
```

## Error Handling

The migration is designed to be robust:

- **Individual Post Errors**: If one post fails, others continue processing
- **Tag Creation Errors**: Failed tag creation is logged but doesn't stop migration
- **Database Errors**: Major database errors cause rollback and raise exceptions
- **Duplicate Handling**: Existing tags are reused, duplicates are avoided

## Safety Features

- **Dry Run Mode**: Test migration without making changes
- **Idempotent**: Safe to run multiple times
- **Rollback**: Database rollback on major errors
- **Data Preservation**: Original data is never modified, only relationships added
- **Validation**: Input validation and error checking throughout

## Requirements

- Flask application with SQLAlchemy
- Tag, Post, and post_tags models properly configured
- Database write permissions
- Python 3.6+ (for f-string support)

## Testing

The migration functionality includes comprehensive tests:

```bash
# Run unit tests
python -m pytest test_legacy_tag_migration.py -v

# Run integration test
python test_migration_integration.py

# Run all tag-related tests
python -m pytest test_tag_manager.py test_legacy_tag_migration.py -v
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Ensure database exists and is accessible
   - Check database URI configuration
   - Verify database permissions

2. **No Posts Processed**
   - Check if posts have non-empty tags fields
   - Verify Post model has 'tags' column
   - Ensure posts exist in database

3. **Slug Conflicts**
   - Migration automatically handles conflicts by appending numbers
   - Check for existing tags with conflicting slugs

4. **Permission Errors**
   - Ensure database write permissions
   - Check file system permissions for SQLite databases

### Debug Mode

For detailed debugging, use verbose mode:

```bash
python migrate_legacy_tags.py --dry-run --verbose
```

This will show:
- All posts that would be processed
- Tags that would be created
- Detailed analysis of existing data

## Best Practices

1. **Always run dry-run first** to see what will be migrated
2. **Backup your database** before running the migration
3. **Test in development** environment first
4. **Monitor for errors** and review migration statistics
5. **Verify results** by checking a few posts manually after migration

## Integration with Application

After migration, you can use the new tag relationships:

```python
# Get posts by tag
tag = Tag.query.filter_by(slug='python').first()
posts = TagManager.get_posts_by_tag(tag)

# Get popular tags
popular_tags = TagManager.get_popular_tags(limit=10)

# Search tags
matching_tags = TagManager.search_tags('web')
```

The legacy tags field remains available for backward compatibility, but new functionality should use the tag relationships.