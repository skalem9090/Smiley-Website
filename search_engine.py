"""
Search Engine for full-text search functionality.

This module provides SQLite FTS5-based full-text search capabilities for blog posts,
including search indexing, query processing, autocomplete, and analytics.
"""

import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from models import db, Post, SearchQuery
from sqlalchemy import text
import re
import html


class SearchEngine:
    """Manager class for full-text search functionality using SQLite FTS5."""
    
    def __init__(self, app=None):
        """Initialize SearchEngine with optional Flask app."""
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app configuration."""
        self.app = app
        self.search_results_per_page = app.config.get('SEARCH_RESULTS_PER_PAGE', 10)
        self.max_autocomplete_suggestions = app.config.get('MAX_AUTOCOMPLETE_SUGGESTIONS', 5)
        self.search_excerpt_length = app.config.get('SEARCH_EXCERPT_LENGTH', 200)
    
    def create_search_index(self, populate=True):
        """
        Create FTS5 virtual table for full-text search indexing.
        
        Args:
            populate: Whether to populate the index with existing posts (default True)
        
        This creates a virtual table that indexes post titles, content, summaries,
        categories, and tags for fast full-text search.
        """
        try:
            # Create FTS5 virtual table
            create_fts_sql = """
            CREATE VIRTUAL TABLE IF NOT EXISTS post_search_fts USING fts5(
                title,
                content,
                summary,
                category,
                tags,
                post_id UNINDEXED
            );
            """
            
            db.session.execute(text(create_fts_sql))
            
            # Create triggers to keep FTS5 table in sync with posts table
            self._create_fts_triggers()
            
            # Populate existing posts into the search index only if requested
            if populate:
                self._populate_search_index()
            
            db.session.commit()
            
            if self.app:
                self.app.logger.info("Search index created successfully")
                
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error creating search index: {str(e)}")
            raise
    
    def _create_fts_triggers(self):
        """Create triggers to keep FTS5 table synchronized with posts table."""
        
        # Trigger for INSERT
        insert_trigger_sql = """
        CREATE TRIGGER IF NOT EXISTS post_search_insert AFTER INSERT ON post
        WHEN NEW.status = 'published'
        BEGIN
            INSERT INTO post_search_fts(title, content, summary, category, tags, post_id)
            VALUES (NEW.title, NEW.content, COALESCE(NEW.summary, ''), 
                   COALESCE(NEW.category, ''), COALESCE(NEW.tags, ''), NEW.id);
        END;
        """
        
        # Trigger for UPDATE
        update_trigger_sql = """
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
        """
        
        # Trigger for DELETE
        delete_trigger_sql = """
        CREATE TRIGGER IF NOT EXISTS post_search_delete AFTER DELETE ON post
        BEGIN
            DELETE FROM post_search_fts WHERE post_id = OLD.id;
        END;
        """
        
        db.session.execute(text(insert_trigger_sql))
        db.session.execute(text(update_trigger_sql))
        db.session.execute(text(delete_trigger_sql))
    
    def _populate_search_index(self):
        """Populate the search index with existing published posts."""
        
        # Clear existing index
        db.session.execute(text("DELETE FROM post_search_fts"))
        
        # Get all published posts
        published_posts = db.session.query(Post).filter(Post.status == 'published').all()
        
        # Insert each post into the search index
        for post in published_posts:
            self.index_post(post)
    
    def index_post(self, post):
        """
        Add or update a post in the search index.
        
        Args:
            post: Post object to index
        """
        if post.status != 'published':
            # Remove from index if not published
            self.remove_post_from_index(post.id)
            return
        
        try:
            # Remove existing entry
            self.remove_post_from_index(post.id)
            
            # Add new entry
            insert_sql = """
            INSERT INTO post_search_fts(title, content, summary, category, tags, post_id)
            VALUES (:title, :content, :summary, :category, :tags, :post_id)
            """
            
            db.session.execute(text(insert_sql), {
                'title': post.title or '',
                'content': self._clean_html_content(post.content) or '',
                'summary': post.summary or '',
                'category': post.category or '',
                'tags': post.tags or '',
                'post_id': post.id
            })
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error indexing post {post.id}: {str(e)}")
            raise
    
    def remove_post_from_index(self, post_id):
        """
        Remove a post from the search index.
        
        Args:
            post_id: ID of the post to remove
        """
        try:
            delete_sql = "DELETE FROM post_search_fts WHERE post_id = :post_id"
            db.session.execute(text(delete_sql), {'post_id': post_id})
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error removing post {post_id} from index: {str(e)}")
            raise
    
    def _clean_html_content(self, html_content):
        """
        Clean HTML content for search indexing.
        
        Args:
            html_content: HTML content to clean
            
        Returns:
            str: Plain text content
        """
        if not html_content:
            return ""
        
        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', ' ', html_content)
        
        # Decode HTML entities
        clean_text = html.unescape(clean_text)
        
        # Normalize whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        return clean_text
    
    def search_posts(self, query, filters=None, page=1, per_page=None):
        """
        Perform full-text search with filtering and pagination.
        
        Args:
            query: Search query string
            filters: Optional dict with 'category', 'tags', 'date_from', 'date_to'
            page: Page number (1-based)
            per_page: Results per page (defaults to configured value)
            
        Returns:
            dict: Search results with posts, pagination info, and metadata
        """
        if not query or not query.strip():
            return {
                'posts': [],
                'total_results': 0,
                'page': page,
                'per_page': per_page or self.search_results_per_page,
                'total_pages': 0,
                'has_prev': False,
                'has_next': False,
                'query': query
            }
        
        per_page = per_page or self.search_results_per_page
        offset = (page - 1) * per_page
        
        try:
            # Sanitize query for FTS5
            sanitized_query = self._sanitize_fts_query(query)
            
            # Build base search query
            search_sql = """
            SELECT post_id, title, content, summary, category, tags,
                   rank, snippet(post_search_fts, 1, '<mark>', '</mark>', '...', 32) as excerpt
            FROM post_search_fts
            WHERE post_search_fts MATCH :query
            ORDER BY rank
            """
            
            # Execute search
            search_results = db.session.execute(text(search_sql), {'query': sanitized_query}).fetchall()
            
            # Get actual post objects and apply additional filters
            post_ids = [row[0] for row in search_results]
            posts_query = db.session.query(Post).filter(
                Post.id.in_(post_ids),
                Post.status == 'published'
            )
            
            # Apply additional filters
            if filters:
                if filters.get('category'):
                    posts_query = posts_query.filter(Post.category == filters['category'])
                
                if filters.get('date_from'):
                    posts_query = posts_query.filter(Post.published_at >= filters['date_from'])
                
                if filters.get('date_to'):
                    posts_query = posts_query.filter(Post.published_at <= filters['date_to'])
            
            # Get all matching posts
            all_posts = posts_query.all()
            
            # Create a mapping of post_id to post object
            posts_dict = {post.id: post for post in all_posts}
            
            # Create results with search metadata
            results_with_metadata = []
            for row in search_results:
                post_id = row[0]
                if post_id in posts_dict:
                    post = posts_dict[post_id]
                    post_data = {
                        'post': post,
                        'excerpt': row[7] if row[7] else self._generate_excerpt(post.content, query),
                        'rank': row[6]
                    }
                    results_with_metadata.append(post_data)
            
            # Apply pagination
            total_results = len(results_with_metadata)
            paginated_results = results_with_metadata[offset:offset + per_page]
            
            # Calculate pagination info
            total_pages = (total_results + per_page - 1) // per_page
            has_prev = page > 1
            has_next = page < total_pages
            
            return {
                'posts': paginated_results,
                'total_results': total_results,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'has_prev': has_prev,
                'has_next': has_next,
                'query': query
            }
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error performing search for '{query}': {str(e)}")
            
            # Return empty results on error
            return {
                'posts': [],
                'total_results': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0,
                'has_prev': False,
                'has_next': False,
                'query': query,
                'error': str(e)
            }
    
    def _sanitize_fts_query(self, query):
        """
        Sanitize query string for FTS5 to prevent syntax errors.
        
        Args:
            query: Raw query string
            
        Returns:
            str: Sanitized query string
        """
        if not query:
            return ""
        
        # For FTS5, hyphens and other special characters can cause issues
        # The safest approach is to wrap queries with special characters in quotes
        # Check if query contains problematic characters
        if re.search(r'[-*"()]', query):
            # Escape any quotes in the query and wrap in quotes
            escaped_query = query.replace('"', '""')
            return f'"{escaped_query}"'
        
        # Check if query is all digits - wrap in quotes for exact match
        if query.isdigit():
            return f'"{query}"'
        
        # Remove other special FTS5 characters that could cause syntax errors
        sanitized = re.sub(r'[^\w\s]', ' ', query)
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # If query is empty after sanitization, wrap original in quotes
        if not sanitized:
            escaped_query = query.replace('"', '""')
            return f'"{escaped_query}"'
        
        return sanitized
    
    def _generate_excerpt(self, content, query, max_length=None):
        """
        Generate search excerpt with highlighted terms.
        
        Args:
            content: Post content
            query: Search query
            max_length: Maximum excerpt length
            
        Returns:
            str: Excerpt with highlighted search terms
        """
        max_length = max_length or self.search_excerpt_length
        
        if not content:
            return ""
        
        # Clean HTML content
        clean_content = self._clean_html_content(content)
        
        if not clean_content:
            return ""
        
        # Find query terms in content
        query_terms = query.lower().split()
        content_lower = clean_content.lower()
        
        # Find the best position to start the excerpt
        best_pos = 0
        max_matches = 0
        
        # Look for the position with the most query term matches
        for i in range(0, len(clean_content) - max_length + 1, 50):
            excerpt_section = content_lower[i:i + max_length]
            matches = sum(1 for term in query_terms if term in excerpt_section)
            if matches > max_matches:
                max_matches = matches
                best_pos = i
        
        # Extract excerpt
        excerpt = clean_content[best_pos:best_pos + max_length]
        
        # Add ellipsis if needed
        if best_pos > 0:
            excerpt = "..." + excerpt
        if best_pos + max_length < len(clean_content):
            excerpt = excerpt + "..."
        
        # Highlight query terms
        for term in query_terms:
            if len(term) > 2:  # Only highlight terms longer than 2 characters
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                excerpt = pattern.sub(f'<mark>{term}</mark>', excerpt)
        
        return excerpt
    
    def get_search_suggestions(self, partial_query, limit=None):
        """
        Generate autocomplete suggestions based on partial query.
        
        Args:
            partial_query: Partial search query
            limit: Maximum number of suggestions
            
        Returns:
            list: List of suggested search terms
        """
        limit = limit or self.max_autocomplete_suggestions
        
        if not partial_query or len(partial_query) < 2:
            return []
        
        try:
            # Get suggestions from previous search queries
            query_suggestions = db.session.query(SearchQuery.query_text).filter(
                SearchQuery.query_text.like(f'{partial_query}%')
            ).group_by(SearchQuery.query_text).order_by(
                db.func.count(SearchQuery.id).desc()
            ).limit(limit).all()
            
            suggestions = [row[0] for row in query_suggestions]
            
            # If we don't have enough suggestions, add some from post titles
            if len(suggestions) < limit:
                remaining_limit = limit - len(suggestions)
                
                title_suggestions = db.session.query(Post.title).filter(
                    Post.status == 'published',
                    Post.title.like(f'%{partial_query}%')
                ).limit(remaining_limit).all()
                
                for row in title_suggestions:
                    if row[0] not in suggestions:
                        suggestions.append(row[0])
            
            return suggestions[:limit]
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting search suggestions for '{partial_query}': {str(e)}")
            return []
    
    def log_search_query(self, query, results_count, ip_address=None, user_agent=None):
        """
        Log search query for analytics.
        
        Args:
            query: Search query string
            results_count: Number of results returned
            ip_address: Optional IP address of searcher
            user_agent: Optional user agent string
        """
        try:
            search_log = SearchQuery(
                query_text=query,
                results_count=results_count,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.now(timezone.utc)
            )
            
            db.session.add(search_log)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error logging search query '{query}': {str(e)}")
    
    def get_popular_searches(self, limit=10, days=30):
        """
        Get most popular search queries.
        
        Args:
            limit: Maximum number of queries to return
            days: Number of days to look back
            
        Returns:
            list: List of tuples (query, count)
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            popular_queries = db.session.query(
                SearchQuery.query_text,
                db.func.count(SearchQuery.id).label('count')
            ).filter(
                SearchQuery.created_at >= cutoff_date
            ).group_by(
                SearchQuery.query_text
            ).order_by(
                db.func.count(SearchQuery.id).desc()
            ).limit(limit).all()
            
            return [(row[0], row[1]) for row in popular_queries]
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting popular searches: {str(e)}")
            return []
    
    def rebuild_search_index(self):
        """
        Rebuild the entire search index from scratch.
        
        This is useful for maintenance or after schema changes.
        """
        try:
            # Drop existing FTS table
            db.session.execute(text("DROP TABLE IF EXISTS post_search_fts"))
            
            # Recreate the search index
            self.create_search_index()
            
            if self.app:
                self.app.logger.info("Search index rebuilt successfully")
                
        except Exception as e:
            db.session.rollback()
            if self.app:
                self.app.logger.error(f"Error rebuilding search index: {str(e)}")
            raise
    
    def get_search_stats(self):
        """
        Get search system statistics.
        
        Returns:
            dict: Statistics about the search system
        """
        try:
            # Count indexed posts
            indexed_count = db.session.execute(
                text("SELECT COUNT(*) FROM post_search_fts")
            ).scalar()
            
            # Count total published posts
            published_count = db.session.query(Post).filter(
                Post.status == 'published'
            ).count()
            
            # Count total search queries
            total_searches = db.session.query(SearchQuery).count()
            
            # Get recent search activity
            from datetime import timedelta
            recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            recent_searches = db.session.query(SearchQuery).filter(
                SearchQuery.created_at >= recent_cutoff
            ).count()
            
            return {
                'indexed_posts': indexed_count,
                'published_posts': published_count,
                'index_coverage': (indexed_count / published_count * 100) if published_count > 0 else 0,
                'total_searches': total_searches,
                'recent_searches': recent_searches
            }
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f"Error getting search stats: {str(e)}")
            return {
                'indexed_posts': 0,
                'published_posts': 0,
                'index_coverage': 0,
                'total_searches': 0,
                'recent_searches': 0
            }