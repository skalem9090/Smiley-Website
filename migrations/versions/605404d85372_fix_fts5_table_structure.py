"""Fix FTS5 table structure

Revision ID: 605404d85372
Revises: create_search_infrastructure
Create Date: 2026-01-17 21:37:05.271915

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '605404d85372'
down_revision = 'create_search_infrastructure'
branch_labels = None
depends_on = None


def upgrade():
    """Fix FTS5 table structure by recreating without contentless options."""
    
    # Get database connection
    connection = op.get_bind()
    
    # Drop existing FTS5 table and triggers
    connection.execute(text("DROP TRIGGER IF EXISTS post_search_insert;"))
    connection.execute(text("DROP TRIGGER IF EXISTS post_search_update;"))
    connection.execute(text("DROP TRIGGER IF EXISTS post_search_delete;"))
    connection.execute(text("DROP TABLE IF EXISTS post_search_fts;"))
    
    # Create FTS5 virtual table with correct structure (content-storing)
    connection.execute(text("""
        CREATE VIRTUAL TABLE post_search_fts USING fts5(
            title,
            content,
            summary,
            category,
            tags,
            post_id UNINDEXED
        );
    """))
    
    # Recreate triggers
    connection.execute(text("""
        CREATE TRIGGER post_search_insert AFTER INSERT ON post
        WHEN NEW.status = 'published'
        BEGIN
            INSERT INTO post_search_fts(title, content, summary, category, tags, post_id)
            VALUES (NEW.title, NEW.content, COALESCE(NEW.summary, ''), 
                   COALESCE(NEW.category, ''), COALESCE(NEW.tags, ''), NEW.id);
        END;
    """))
    
    connection.execute(text("""
        CREATE TRIGGER post_search_update AFTER UPDATE ON post
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
    
    connection.execute(text("""
        CREATE TRIGGER post_search_delete AFTER DELETE ON post
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
    """Revert to the previous FTS5 table structure."""
    
    # Get database connection
    connection = op.get_bind()
    
    # Drop current structure
    connection.execute(text("DROP TRIGGER IF EXISTS post_search_insert;"))
    connection.execute(text("DROP TRIGGER IF EXISTS post_search_update;"))
    connection.execute(text("DROP TRIGGER IF EXISTS post_search_delete;"))
    connection.execute(text("DROP TABLE IF EXISTS post_search_fts;"))
    
    # Recreate with contentless structure (original)
    connection.execute(text("""
        CREATE VIRTUAL TABLE post_search_fts USING fts5(
            title,
            content,
            summary,
            category,
            tags,
            post_id UNINDEXED,
            content='',
            contentless_delete=1
        );
    """))
    
    # Recreate original triggers
    connection.execute(text("""
        CREATE TRIGGER post_search_insert AFTER INSERT ON post
        WHEN NEW.status = 'published'
        BEGIN
            INSERT INTO post_search_fts(title, content, summary, category, tags, post_id)
            VALUES (NEW.title, NEW.content, COALESCE(NEW.summary, ''), 
                   COALESCE(NEW.category, ''), COALESCE(NEW.tags, ''), NEW.id);
        END;
    """))
    
    connection.execute(text("""
        CREATE TRIGGER post_search_update AFTER UPDATE ON post
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
    
    connection.execute(text("""
        CREATE TRIGGER post_search_delete AFTER DELETE ON post
        BEGIN
            DELETE FROM post_search_fts WHERE post_id = OLD.id;
        END;
    """))
