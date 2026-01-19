"""
SEO Manager for Blog Comprehensive Features

This module provides SEO enhancement functionality including:
- Meta tag generation for all page types
- Open Graph tags for social media sharing
- Structured data (JSON-LD) markup
- XML sitemap generation and management
- Canonical URL generation
"""

import json
from datetime import datetime, timezone
from urllib.parse import urljoin
from flask import url_for, request, current_app
from models import db, Post, Tag, AuthorProfile


class SEOManager:
    """Manages SEO enhancements and optimization features."""
    
    def __init__(self, app=None):
        """Initialize SEO manager with Flask app."""
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app context."""
        self.app = app
        
        # Default SEO configuration
        app.config.setdefault('SEO_SITE_NAME', 'Smileys Blog')
        app.config.setdefault('SEO_SITE_DESCRIPTION', 'Short essays and practical tips about wealth, health & happiness')
        app.config.setdefault('SEO_SITE_URL', 'https://smileys-blog.com')
        app.config.setdefault('SEO_DEFAULT_IMAGE', '/static/images/default-og-image.jpg')
        app.config.setdefault('SEO_TWITTER_HANDLE', '@smileys_blog')
        app.config.setdefault('SEO_FACEBOOK_APP_ID', None)
    
    def generate_meta_tags(self, page_type='website', content=None, **kwargs):
        """
        Generate meta tags for different page types.
        
        Args:
            page_type: Type of page ('website', 'post', 'about', 'search', 'tag')
            content: Content object (Post, Tag, etc.) if applicable
            **kwargs: Additional meta tag data
        
        Returns:
            dict: Meta tag data for template rendering
        """
        site_name = self.app.config.get('SEO_SITE_NAME')
        site_description = self.app.config.get('SEO_SITE_DESCRIPTION')
        site_url = self.app.config.get('SEO_SITE_URL')
        
        meta_tags = {
            'title': site_name,
            'description': site_description,
            'keywords': 'wealth, health, happiness, blog, essays, tips',
            'canonical_url': self._get_canonical_url(),
            'robots': 'index, follow',
            'author': site_name,
            'viewport': 'width=device-width, initial-scale=1'
        }
        
        if page_type == 'post' and content:
            meta_tags.update(self._generate_post_meta_tags(content))
        elif page_type == 'about' and content:
            meta_tags.update(self._generate_about_meta_tags(content))
        elif page_type == 'tag' and content:
            meta_tags.update(self._generate_tag_meta_tags(content))
        elif page_type == 'search':
            meta_tags.update(self._generate_search_meta_tags(kwargs.get('query', '')))
        
        # Override with any provided kwargs
        meta_tags.update(kwargs)
        
        return meta_tags
    
    def _generate_post_meta_tags(self, post):
        """Generate meta tags specific to blog posts."""
        # Create post title with site name
        title = f"{post.title} | {self.app.config.get('SEO_SITE_NAME')}"
        
        # Use post summary or generate excerpt from content
        description = post.summary
        if not description and post.content:
            # Generate excerpt from content (first 160 characters)
            description = self._generate_excerpt(post.content, 160)
        
        # Generate keywords from tags and category
        keywords = []
        if post.category:
            keywords.append(post.category.lower())
        
        # Add tags from relationships
        if hasattr(post, 'tag_relationships') and post.tag_relationships:
            keywords.extend([tag.name.lower() for tag in post.tag_relationships])
        
        # Add legacy tags if present
        if post.tags:
            legacy_tags = [tag.strip().lower() for tag in post.tags.split(',') if tag.strip()]
            keywords.extend(legacy_tags)
        
        # Add default keywords
        keywords.extend(['wealth', 'health', 'happiness', 'blog'])
        
        return {
            'title': title,
            'description': description,
            'keywords': ', '.join(set(keywords)),  # Remove duplicates
            'author': self.app.config.get('SEO_SITE_NAME'),
            'article_published_time': post.published_at.isoformat() if post.published_at else None,
            'article_modified_time': post.created_at.isoformat(),
            'article_section': post.category,
            'article_tag': ', '.join(set(keywords))
        }
    
    def _generate_about_meta_tags(self, author_profile):
        """Generate meta tags for the about page."""
        title = f"About | {self.app.config.get('SEO_SITE_NAME')}"
        description = author_profile.mission_statement or author_profile.bio
        
        # Truncate description if too long
        if len(description) > 160:
            description = self._generate_excerpt(description, 160)
        
        keywords = ['about', 'author', 'mission', 'biography']
        expertise_areas = author_profile.get_expertise_areas()
        if expertise_areas:
            keywords.extend([area.lower() for area in expertise_areas])
        
        return {
            'title': title,
            'description': description,
            'keywords': ', '.join(keywords),
            'author': author_profile.name
        }
    
    def _generate_tag_meta_tags(self, tag):
        """Generate meta tags for tag pages."""
        title = f"Posts tagged '{tag.name}' | {self.app.config.get('SEO_SITE_NAME')}"
        description = f"All posts tagged with '{tag.name}' on {self.app.config.get('SEO_SITE_NAME')}"
        
        return {
            'title': title,
            'description': description,
            'keywords': f"{tag.name}, blog posts, {self.app.config.get('SEO_SITE_NAME').lower()}",
            'robots': 'index, follow'
        }
    
    def _generate_search_meta_tags(self, query):
        """Generate meta tags for search results pages."""
        if query:
            title = f"Search results for '{query}' | {self.app.config.get('SEO_SITE_NAME')}"
            description = f"Search results for '{query}' on {self.app.config.get('SEO_SITE_NAME')}"
        else:
            title = f"Search | {self.app.config.get('SEO_SITE_NAME')}"
            description = f"Search for content on {self.app.config.get('SEO_SITE_NAME')}"
        
        return {
            'title': title,
            'description': description,
            'keywords': f"search, {query}, blog" if query else "search, blog",
            'robots': 'noindex, follow'  # Don't index search results
        }
    
    def generate_open_graph_tags(self, page_type='website', content=None, **kwargs):
        """
        Generate Open Graph tags for social media sharing.
        
        Args:
            page_type: Type of page ('website', 'article', 'profile')
            content: Content object if applicable
            **kwargs: Additional OG tag data
        
        Returns:
            dict: Open Graph tag data
        """
        site_name = self.app.config.get('SEO_SITE_NAME')
        site_url = self.app.config.get('SEO_SITE_URL')
        default_image = self.app.config.get('SEO_DEFAULT_IMAGE')
        
        og_tags = {
            'og:site_name': site_name,
            'og:url': self._get_canonical_url(),
            'og:type': page_type,
            'og:locale': 'en_US',
            'og:image': urljoin(site_url, default_image) if default_image else None,
            'og:image:alt': f"{site_name} logo"
        }
        
        # Add Twitter Card tags
        twitter_handle = self.app.config.get('SEO_TWITTER_HANDLE')
        og_tags.update({
            'twitter:card': 'summary_large_image',
            'twitter:site': twitter_handle,
            'twitter:creator': twitter_handle
        })
        
        # Add Facebook App ID if configured
        fb_app_id = self.app.config.get('SEO_FACEBOOK_APP_ID')
        if fb_app_id:
            og_tags['fb:app_id'] = fb_app_id
        
        if page_type == 'article' and content:
            og_tags.update(self._generate_post_og_tags(content))
        elif page_type == 'profile' and content:
            og_tags.update(self._generate_profile_og_tags(content))
        
        # Override with any provided kwargs
        og_tags.update(kwargs)
        
        return og_tags
    
    def _generate_post_og_tags(self, post):
        """Generate Open Graph tags specific to blog posts."""
        site_url = self.app.config.get('SEO_SITE_URL')
        
        og_tags = {
            'og:title': post.title,
            'og:description': post.summary or self._generate_excerpt(post.content, 200),
            'og:type': 'article',
            'article:published_time': post.published_at.isoformat() if post.published_at else None,
            'article:modified_time': post.created_at.isoformat(),
            'article:section': post.category,
            'twitter:card': 'summary_large_image'
        }
        
        # Add article tags
        tags = []
        if hasattr(post, 'tag_relationships') and post.tag_relationships:
            tags.extend([tag.name for tag in post.tag_relationships])
        if post.tags:
            legacy_tags = [tag.strip() for tag in post.tags.split(',') if tag.strip()]
            tags.extend(legacy_tags)
        
        if tags:
            og_tags['article:tag'] = tags
        
        # Try to find an image in the post content
        post_image = self._extract_first_image_from_content(post.content)
        if post_image:
            og_tags['og:image'] = urljoin(site_url, post_image)
            og_tags['og:image:alt'] = f"Image from {post.title}"
        
        return og_tags
    
    def _generate_profile_og_tags(self, author_profile):
        """Generate Open Graph tags for author profile."""
        site_url = self.app.config.get('SEO_SITE_URL')
        
        og_tags = {
            'og:title': f"About {author_profile.name}",
            'og:description': author_profile.mission_statement or author_profile.bio,
            'og:type': 'profile',
            'profile:first_name': author_profile.name.split()[0] if author_profile.name else '',
            'profile:last_name': ' '.join(author_profile.name.split()[1:]) if len(author_profile.name.split()) > 1 else ''
        }
        
        # Add profile image if available
        if author_profile.profile_image:
            og_tags['og:image'] = urljoin(site_url, f"/static/uploads/{author_profile.profile_image}")
            og_tags['og:image:alt'] = f"Profile photo of {author_profile.name}"
        
        return og_tags
    
    def generate_structured_data(self, page_type='WebSite', content=None, **kwargs):
        """
        Generate JSON-LD structured data markup.
        
        Args:
            page_type: Schema.org type ('WebSite', 'BlogPosting', 'Person', 'Organization')
            content: Content object if applicable
            **kwargs: Additional structured data
        
        Returns:
            dict: JSON-LD structured data
        """
        site_name = self.app.config.get('SEO_SITE_NAME')
        site_url = self.app.config.get('SEO_SITE_URL')
        site_description = self.app.config.get('SEO_SITE_DESCRIPTION')
        
        base_data = {
            "@context": "https://schema.org",
            "@type": page_type,
            "url": self._get_canonical_url()
        }
        
        if page_type == 'WebSite':
            base_data.update({
                "name": site_name,
                "description": site_description,
                "url": site_url,
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": {
                        "@type": "EntryPoint",
                        "urlTemplate": f"{site_url}/search?q={{search_term_string}}"
                    },
                    "query-input": "required name=search_term_string"
                }
            })
        elif page_type == 'BlogPosting' and content:
            base_data.update(self._generate_post_structured_data(content))
        elif page_type == 'Person' and content:
            base_data.update(self._generate_person_structured_data(content))
        elif page_type == 'Organization':
            base_data.update(self._generate_organization_structured_data())
        
        # Override with any provided kwargs
        base_data.update(kwargs)
        
        return base_data
    
    def _generate_post_structured_data(self, post):
        """Generate structured data for blog posts."""
        site_name = self.app.config.get('SEO_SITE_NAME')
        site_url = self.app.config.get('SEO_SITE_URL')
        
        # Get author profile
        author_profile = AuthorProfile.query.first()
        
        structured_data = {
            "headline": post.title,
            "description": post.summary or self._generate_excerpt(post.content, 200),
            "datePublished": post.published_at.isoformat() if post.published_at else post.created_at.isoformat(),
            "dateModified": post.created_at.isoformat(),
            "author": {
                "@type": "Person",
                "name": author_profile.name if author_profile else site_name,
                "url": urljoin(site_url, "/about") if author_profile else site_url
            },
            "publisher": {
                "@type": "Organization",
                "name": site_name,
                "url": site_url
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": self._get_canonical_url()
            }
        }
        
        # Add article section (category)
        if post.category:
            structured_data["articleSection"] = post.category
        
        # Add keywords from tags
        keywords = []
        if hasattr(post, 'tag_relationships') and post.tag_relationships:
            keywords.extend([tag.name for tag in post.tag_relationships])
        if post.tags:
            legacy_tags = [tag.strip() for tag in post.tags.split(',') if tag.strip()]
            keywords.extend(legacy_tags)
        
        if keywords:
            structured_data["keywords"] = list(set(keywords))
        
        # Add image if found in content
        post_image = self._extract_first_image_from_content(post.content)
        if post_image:
            structured_data["image"] = {
                "@type": "ImageObject",
                "url": urljoin(site_url, post_image),
                "caption": f"Image from {post.title}"
            }
        
        return structured_data
    
    def _generate_person_structured_data(self, author_profile):
        """Generate structured data for author profile."""
        site_url = self.app.config.get('SEO_SITE_URL')
        
        structured_data = {
            "name": author_profile.name,
            "description": author_profile.bio,
            "email": author_profile.email,
            "url": urljoin(site_url, "/about")
        }
        
        # Add social media profiles
        same_as = []
        if author_profile.twitter_handle:
            same_as.append(f"https://twitter.com/{author_profile.twitter_handle.lstrip('@')}")
        if author_profile.linkedin_url:
            same_as.append(author_profile.linkedin_url)
        if author_profile.github_url:
            same_as.append(author_profile.github_url)
        if author_profile.website_url:
            same_as.append(author_profile.website_url)
        
        if same_as:
            structured_data["sameAs"] = same_as
        
        # Add profile image
        if author_profile.profile_image:
            structured_data["image"] = {
                "@type": "ImageObject",
                "url": urljoin(site_url, f"/static/uploads/{author_profile.profile_image}"),
                "caption": f"Profile photo of {author_profile.name}"
            }
        
        # Add expertise areas as knows about
        expertise_areas = author_profile.get_expertise_areas()
        if expertise_areas:
            structured_data["knowsAbout"] = expertise_areas
        
        return structured_data
    
    def _generate_organization_structured_data(self):
        """Generate structured data for the organization/website."""
        site_name = self.app.config.get('SEO_SITE_NAME')
        site_url = self.app.config.get('SEO_SITE_URL')
        site_description = self.app.config.get('SEO_SITE_DESCRIPTION')
        
        return {
            "name": site_name,
            "description": site_description,
            "url": site_url,
            "@type": "Organization"
        }
    
    def generate_sitemap(self):
        """
        Generate XML sitemap for all public content.
        
        Returns:
            str: XML sitemap content
        """
        site_url = self.app.config.get('SEO_SITE_URL')
        
        # Start XML sitemap
        sitemap_xml = ['<?xml version="1.0" encoding="UTF-8"?>']
        sitemap_xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        
        # Add homepage
        sitemap_xml.append(self._generate_sitemap_url(
            loc=site_url,
            lastmod=datetime.now(timezone.utc),
            changefreq='daily',
            priority='1.0'
        ))
        
        # Add about page
        sitemap_xml.append(self._generate_sitemap_url(
            loc=urljoin(site_url, '/about'),
            lastmod=datetime.now(timezone.utc),
            changefreq='monthly',
            priority='0.8'
        ))
        
        # Add explore page
        sitemap_xml.append(self._generate_sitemap_url(
            loc=urljoin(site_url, '/explore'),
            lastmod=datetime.now(timezone.utc),
            changefreq='daily',
            priority='0.7'
        ))
        
        # Add tags page
        sitemap_xml.append(self._generate_sitemap_url(
            loc=urljoin(site_url, '/tags'),
            lastmod=datetime.now(timezone.utc),
            changefreq='weekly',
            priority='0.6'
        ))
        
        # Add all published posts
        published_posts = Post.query.filter_by(status='published').order_by(Post.published_at.desc()).all()
        for post in published_posts:
            post_url = urljoin(site_url, f'/post/{post.id}')
            sitemap_xml.append(self._generate_sitemap_url(
                loc=post_url,
                lastmod=post.published_at or post.created_at,
                changefreq='monthly',
                priority='0.9'
            ))
        
        # Add all tag pages
        tags = Tag.query.all()
        for tag in tags:
            tag_url = urljoin(site_url, f'/tag/{tag.slug}')
            sitemap_xml.append(self._generate_sitemap_url(
                loc=tag_url,
                lastmod=datetime.now(timezone.utc),
                changefreq='weekly',
                priority='0.5'
            ))
        
        sitemap_xml.append('</urlset>')
        
        return '\n'.join(sitemap_xml)
    
    def _generate_sitemap_url(self, loc, lastmod, changefreq='monthly', priority='0.5'):
        """Generate a single URL entry for the sitemap."""
        lastmod_str = lastmod.strftime('%Y-%m-%d') if lastmod else ''
        
        return f"""  <url>
    <loc>{loc}</loc>
    <lastmod>{lastmod_str}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>"""
    
    def get_canonical_url(self, endpoint=None, **values):
        """
        Generate canonical URLs for pages.
        
        Args:
            endpoint: Flask endpoint name
            **values: URL parameters
        
        Returns:
            str: Canonical URL
        """
        site_url = self.app.config.get('SEO_SITE_URL')
        
        if endpoint:
            try:
                relative_url = url_for(endpoint, **values)
                return urljoin(site_url, relative_url)
            except Exception:
                return site_url
        else:
            return self._get_canonical_url()
    
    def _get_canonical_url(self):
        """Get canonical URL for current request."""
        site_url = self.app.config.get('SEO_SITE_URL')
        
        if request:
            return urljoin(site_url, request.path)
        else:
            return site_url
    
    def _generate_excerpt(self, content, max_length=160):
        """Generate excerpt from content."""
        if not content:
            return ""
        
        # Remove HTML tags for excerpt
        import re
        clean_content = re.sub(r'<[^>]+>', ' ', content)
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()
        
        if len(clean_content) <= max_length:
            return clean_content
        
        # Find last complete word within limit
        excerpt = clean_content[:max_length]
        last_space = excerpt.rfind(' ')
        
        if last_space > max_length * 0.8:  # If we can find a space reasonably close to the limit
            excerpt = excerpt[:last_space]
        
        return excerpt + '...'
    
    def _extract_first_image_from_content(self, content):
        """Extract the first image URL from post content."""
        if not content:
            return None
        
        import re
        # Look for img tags with src attributes
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        match = re.search(img_pattern, content, re.IGNORECASE)
        
        if match:
            return match.group(1)
        
        return None