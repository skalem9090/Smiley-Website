"""Create search infrastructure with FTS5 virtual table

Revision ID: create_search_infrastructure
Revises: add_search_query_model
Create Date: 2026-01-18 04:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'create_search_infrastructure'
down_revision = 'add_search_query_model'
branch_labels = None
depends_on = None


def upgrade():
    """Create FTS5 virtual table and triggers for search functionality."""
    
    # Get database connection
    connection = op.get_bind()
    
    # Create FTS5 virtual table for full-text search
    connection.execute(text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS post_search_fts USING fts5(
            title,
            content,
            summary,
            category,
            tags,
            post_id UNINDEXED
        );
    """))
    
    # Create trigger for INSERT operations
    connection.execute(text("""
        CREATE TRIGGER IF NOT EXISTS post_search_insert AFTER INSERT ON post
        WHEN NEW.status = 'published'
        BEGIN
            INSERT INTO post_search_fts(title, content, summary, category, tags, post_id)
            VALUES (NEW.title, NEW.content, COALESCE(NEW.summary, ''), 
                   COALESCE(NEW.category, ''), COALESCE(NEW.tags, ''), NEW.id);
        END;
    """))
    
    # Create trigger for UPDATE operations
    connection.execute(text("""
        CREATE TRIGGER IF NOT EXISTS post_search_update AFTER UPDATE ON post
        BEGIN
            -- Remove old entry
            DELETE FROM post_search_fts WHERE post_id = OLD.id;
            
            -- Add new entry only if published
            INSERT INTO post_search_fts(title, content, summary, category, tags, post_id)
            SELECT NEW.title, NEW.content, COALESCE(NEW.summary, ''), 
                   COALESCE(NEW.category, ''), COALESCE(NEW.tags, ''), NEW.id
            WHERE NEW.status = 'published';
        END;
    """))
    
    # Create trigger for DELETE operations
    connection.execute(text("""
        CREATE TRIGGER IF NOT EXISTS post_search_delete AFTER DELETE ON post
        BEGIN
            DELETE FROM post_search_fts WHERE post_id = OLD.id;
        END;
    """))
    
    # Populate the search index with existing published posts
    connection.execute(text("""
        INSERT INTO post_search_fts(title, content, summary, category, tags, post_id)
        SELECT title, content, COALESCE(summary, ''), COALESCE(category, ''), 
               COALESCE(tags, ''), id
        FROM post 
        WHERE status = 'published';
    """))


def downgrade():
    """Remove FTS5 virtual table and triggers."""
    
    # Get database connection
    connection = op.get_bind()
    
    # Drop triggers
    connection.execute(text("DROP TRIGGER IF EXISTS post_search_insert;"))
    connection.execute(text("DROP TRIGGER IF EXISTS post_search_update;"))
    connection.execute(text("DROP TRIGGER IF EXISTS post_search_delete;"))
    
    # Drop FTS5 virtual table
    connection.execute(text("DROP TABLE IF EXISTS post_search_fts;"))