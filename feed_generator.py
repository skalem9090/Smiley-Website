"""
Feed Generator for RSS/Atom feeds.

This module provides functionality for generating RSS 2.0 and Atom 1.0 feeds
from blog posts, with proper metadata and caching support.
"""

from datetime import datetime, timezone
from feedgen.feed import FeedGenerator as BaseFeedGenerator
from feedgen.entry import FeedEntry
from models import db, Post
from about_page_manager import AboutPageManager
import re
import html


class FeedGenerator:
    """Manager class for RSS/Atom feed generation."""
    
    def __init__(self, app=None):
        """Initialize FeedGenerator with optional Flask app."""
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app configuration."""
        self.app = app
        self.site_url = app.config.get('SITE_URL', 'http://localhost:5000')
        self.max_feed_items = app.config.get('MAX_FEED_ITEMS', 20)
        self.feed_cache_timeout = app.config.get('FEED_CACHE_TIMEOUT', 3600)  # 1 hour
    
    def _sanitize_xml_text(self, text):
        """
        Sanitize text for XML compatibility.
        
        Args:
            text: Input text that may contain XML-unsafe characters
            
        Returns:
            str: XML-safe text
        """
        if not text:
            return ""
        
        # Remove control characters except tab, newline, and carriage return
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Escape HTML entities
        text = html.escape(text, quote=False)
        
        return text
    
    def generate_rss_feed(self):
        """
        Generate RSS 2.0 feed.
        
        Returns:
            str: RSS feed XML content
        """
        fg = self._create_base_feed()
        
        # Set RSS-specific properties
        fg.rss_str(pretty=True)
        
        # Add feed items
        self._add_feed_items(fg)
        
        return fg.rss_str(pretty=True)
    
    def generate_atom_feed(self):
        """
        Generate Atom 1.0 feed.
        
        Returns:
            str: Atom feed XML content
        """
        fg = self._create_base_feed()
        
        # Add feed items
        self._add_feed_items(fg)
        
        return fg.atom_str(pretty=True)
    
    def _create_base_feed(self):
        """
        Create base feed generator with site metadata.
        
        Returns:
            FeedGenerator: Configured feed generator
        """
        fg = BaseFeedGenerator()
        
        # Get author profile for feed metadata
        about_manager = AboutPageManager(self.app)
        profile = about_manager.get_author_profile()
        
        # Basic feed information
        fg.id(self.site_url)
        fg.title(self._get_site_title())
        fg.link(href=self.site_url, rel='alternate')
        fg.link(href=f"{self.site_url}/feed.xml", rel='self')
        fg.description(self._get_site_description(profile))
        fg.language('en')
        
        # Author information
        fg.author(name=profile.name, email=profile.email)
        fg.managingEditor(f"{profile.email} ({profile.name})")
        fg.webMaster(f"{profile.email} ({profile.name})")
        
        # Feed metadata
        fg.generator('Flask Blog Feed Generator')
        fg.lastBuildDate(datetime.now(timezone.utc))
        fg.ttl(60)  # Time to live in minutes
        
        # Copyright and category
        current_year = datetime.now().year
        fg.copyright(f"Copyright {current_year} {profile.name}")
        
        return fg
    
    def _add_feed_items(self, fg):
        """
        Add blog posts as feed items.
        
        Args:
            fg: FeedGenerator instance
        """
        # Get published posts for feed
        posts = self._get_feed_posts()
        
        for post in posts:
            fe = fg.add_entry()
            
            # Basic entry information
            fe.id(f"{self.site_url}/post/{post.id}")
            fe.title(self._sanitize_xml_text(post.title))
            fe.link(href=f"{self.site_url}/post/{post.id}")
            
            # Content
            if post.summary:
                fe.description(self._sanitize_xml_text(post.summary))
                fe.content(content=self._sanitize_xml_text(post.content), type='html')
            else:
                # Use first paragraph or truncated content as description
                description = self._extract_description(post.content)
                fe.description(self._sanitize_xml_text(description))
                fe.content(content=self._sanitize_xml_text(post.content), type='html')
            
            # Dates
            pub_date = post.published_at if post.published_at else post.created_at
            # Ensure timezone awareness
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            fe.pubDate(pub_date)
            
            # Author
            about_manager = AboutPageManager(self.app)
            profile = about_manager.get_author_profile()
            fe.author(name=profile.name, email=profile.email)
            
            # Categories/Tags
            if hasattr(post, 'tag_relationships') and post.tag_relationships:
                for tag_rel in post.tag_relationships:
                    fe.category(term=self._sanitize_xml_text(tag_rel.name))
            elif post.tags:  # Fallback to legacy tags
                tags = [tag.strip() for tag in post.tags.split(',') if tag.strip()]
                for tag in tags:
                    fe.category(term=self._sanitize_xml_text(tag))
            
            # Category
            if post.category:
                fe.category(term=self._sanitize_xml_text(post.category))
            
            # GUID (unique identifier)
            fe.guid(f"{self.site_url}/post/{post.id}", permalink=True)
    
    def _get_feed_posts(self):
        """
        Get published posts for feed inclusion.
        
        Returns:
            List[Post]: Published posts ordered by publication date (newest first)
        """
        posts = db.session.query(Post).filter(
            Post.status == 'published'
        ).order_by(
            Post.published_at.desc().nullslast(),
            Post.created_at.desc()
        ).limit(self.max_feed_items).all()
        
        # Reverse the list because feedgen sorts entries by publication date in ascending order
        # We want newest posts first in the feed, so we reverse the order here
        return list(reversed(posts))
    
    def _get_site_title(self):
        """
        Get site title for feed.
        
        Returns:
            str: Site title
        """
        # You can customize this based on your site configuration
        return "Blog Feed"
    
    def _get_site_description(self, profile):
        """
        Get site description for feed.
        
        Args:
            profile: AuthorProfile instance
            
        Returns:
            str: Site description
        """
        if profile.mission_statement:
            return profile.mission_statement
        elif profile.bio:
            # Use first sentence of bio
            sentences = profile.bio.split('.')
            if sentences:
                return sentences[0].strip() + '.'
        
        return "Latest blog posts and updates"
    
    def _extract_description(self, content, max_length=200):
        """
        Extract description from post content.
        
        Args:
            content: HTML content
            max_length: Maximum description length
            
        Returns:
            str: Extracted description
        """
        if not content:
            return ""
        
        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', '', content)
        
        # Get first paragraph or sentence
        paragraphs = clean_text.split('\n\n')
        if paragraphs:
            first_paragraph = paragraphs[0].strip()
            if first_paragraph:
                # Truncate if too long
                if len(first_paragraph) > max_length:
                    # Find last complete word within limit
                    truncated = first_paragraph[:max_length]
                    last_space = truncated.rfind(' ')
                    if last_space > 0:
                        truncated = truncated[:last_space]
                    return truncated + '...'
                return first_paragraph
        
        # Fallback: truncate entire content
        if len(clean_text) > max_length:
            truncated = clean_text[:max_length]
            last_space = truncated.rfind(' ')
            if last_space > 0:
                truncated = truncated[:last_space]
            return truncated + '...'
        
        return clean_text
    
    def get_feed_metadata(self):
        """
        Get feed metadata for display/debugging.
        
        Returns:
            dict: Feed metadata
        """
        posts = self._get_feed_posts()
        about_manager = AboutPageManager(self.app)
        profile = about_manager.get_author_profile()
        
        return {
            'title': self._get_site_title(),
            'description': self._get_site_description(profile),
            'author': profile.name,
            'email': profile.email,
            'post_count': len(posts),
            'latest_post_date': posts[0].published_at if posts else None,
            'site_url': self.site_url,
            'feed_url': f"{self.site_url}/feed.xml"
        }