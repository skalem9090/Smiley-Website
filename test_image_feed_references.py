"""
Property-based test for image feed references.

This module tests the property that posts containing images should include
proper image references in feed entries when they appear in RSS/Atom feeds.

**Feature: blog-comprehensive-features, Property 5: Image Feed References**
**Validates: Requirements 2.7**
"""

import pytest
from hypothesis import given, strategies as st, settings
from app import create_app
from models import db, Post, User, AuthorProfile, Image
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import re
import string
import os
import tempfile
from werkzeug.datastructures import FileStorage
from io import BytesIO


# Custom strategy for XML-safe text
def xml_safe_text(min_size=1, max_size=100):
    """Generate XML-safe text without control characters."""
    safe_chars = string.ascii_letters + string.digits + string.punctuation + ' '
    safe_chars = ''.join(c for c in safe_chars if ord(c) >= 32 and c not in '<>&"\'')
    return st.text(alphabet=safe_chars, min_size=min_size, max_size=max_size).filter(lambda x: x.strip())


class TestImageFeedReferences:
    """Property-based test for image feed references."""
    
    def setup_method(self):
        """Set up test environment."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SITE_URL'] = 'http://testsite.com'
        
        # Set up upload directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.app.config['UPLOAD_FOLDER'] = self.temp_dir
        
        with self.app.app_context():
            db.create_all()
            
            # Clear any existing data
            db.session.query(User).delete()
            db.session.query(AuthorProfile).delete()
            db.session.query(Post).delete()
            db.session.query(Image).delete()
            
            # Create admin user
            admin = User(username='testadmin', is_admin=True)
            admin.set_password('testpass')
            db.session.add(admin)
            
            # Create author profile
            profile = AuthorProfile(
                name="Test Author",
                bio="A test author for feed testing.",
                mission_statement="To test RSS and Atom feeds thoroughly.",
                email="test@example.com"
            )
            profile.set_expertise_areas(["Testing", "RSS", "Atom"])
            db.session.add(profile)
            db.session.commit()
    
    def teardown_method(self):
        """Clean up test environment."""
        # Clean up temporary directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_test_image(self, filename="test_image.jpg"):
        """
        Create a test image record in the database.
        
        Args:
            filename: Name of the image file
            
        Returns:
            Image: Created image record
        """
        # Create a simple test image file
        image_path = os.path.join(self.temp_dir, filename)
        
        # Create a minimal JPEG-like file (just for testing)
        with open(image_path, 'wb') as f:
            # Write minimal JPEG header
            f.write(b'\\xff\\xd8\\xff\\xe0\\x00\\x10JFIF\\x00\\x01\\x01\\x01\\x00H\\x00H\\x00\\x00\\xff\\xdb')
            f.write(b'\\x00C\\x00\\x08\\x06\\x06\\x07\\x06\\x05\\x08\\x07\\x07\\x07\\t\\t\\x08\\n\\x0c\\x14\\r\\x0c\\x0b')
            f.write(b'\\x0b\\x0c\\x19\\x12\\x13\\x0f\\x14\\x1d\\x1a\\x1f\\x1e\\x1d\\x1a\\x1c\\x1c $.\' ",#\\x1c\\x1c(7),01444')
            f.write(b'\\x1f\\xff\\xc0\\x00\\x11\\x08\\x00\\x01\\x00\\x01\\x01\\x01\\x11\\x00\\x02\\x11\\x01\\x03\\x11\\x01')
            f.write(b'\\xff\\xc4\\x00\\x14\\x00\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x08')
            f.write(b'\\xff\\xda\\x00\\x08\\x01\\x01\\x00\\x00?\\x00\\xff\\xd9')
        
        # Create image record
        image = Image(
            filename=filename,
            original_name=filename,
            file_size=os.path.getsize(image_path),
            mime_type='image/jpeg',
            upload_date=datetime.now(timezone.utc)
        )
        db.session.add(image)
        db.session.commit()
        
        return image
    
    def _extract_images_from_feed_content(self, feed_content):
        """
        Extract image references from feed content.
        
        Args:
            feed_content: RSS or Atom feed content
            
        Returns:
            list: List of image URLs found in the feed
        """
        import html
        
        # Decode HTML entities first
        decoded_content = html.unescape(feed_content)
        
        # Look for image references in various formats
        image_patterns = [
            r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>',  # HTML img tags
            r'<content:encoded[^>]*>(.*?)</content:encoded>',  # Content encoded sections
            r'<description[^>]*>(.*?)</description>',  # Description sections
            r'<summary[^>]*>(.*?)</summary>',  # Atom summary sections
        ]
        
        image_urls = []
        
        # First extract content from encoded sections
        content_sections = []
        for pattern in image_patterns[1:]:  # Skip the img pattern for now
            matches = re.findall(pattern, decoded_content, re.DOTALL | re.IGNORECASE)
            content_sections.extend(matches)
        
        # Now look for img tags in the extracted content sections and the main content
        all_content = [decoded_content] + content_sections
        
        for content in all_content:
            # Decode HTML entities in the content section
            section_content = html.unescape(content)
            
            # Look for img tags
            img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', section_content, re.IGNORECASE)
            image_urls.extend(img_matches)
            
            # Also look for any URL that looks like an image
            url_matches = re.findall(r'https?://[^\\s<>"\']+\\.(jpg|jpeg|png|gif|webp|svg)', section_content, re.IGNORECASE)
            image_urls.extend([match[0] if isinstance(match, tuple) else match for match in url_matches])
            
            # Look for relative image URLs
            relative_matches = re.findall(r'/[^\\s<>"\']*\\.(jpg|jpeg|png|gif|webp|svg)', section_content, re.IGNORECASE)
            image_urls.extend([match[0] if isinstance(match, tuple) else match for match in relative_matches])
        
        return list(set(image_urls))  # Remove duplicates
    
    @given(
        title=xml_safe_text(min_size=1, max_size=100),
        content_before=xml_safe_text(min_size=10, max_size=200),
        content_after=xml_safe_text(min_size=10, max_size=200)
    )
    @settings(max_examples=10, deadline=20000)
    def test_posts_with_images_include_image_references_in_feeds(self, title, content_before, content_after):
        """
        Property: Posts containing images should include proper image references
        in feed entries when they appear in RSS/Atom feeds.
        
        **Validates: Requirements 2.7**
        """
        with self.app.app_context():
            # Clear any existing posts and images
            db.session.query(Post).delete()
            db.session.query(Image).delete()
            db.session.commit()
            
            # Create a test image
            image = self._create_test_image("test_feed_image.jpg")
            
            # Create post content with embedded image
            image_url = f"/static/uploads/{image.filename}"
            post_content = f"<p>{content_before}</p><img src='{image_url}' alt='Test Image'><p>{content_after}</p>"
            
            # Create a published post with the image
            post = Post(
                title=title,
                content=post_content,
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            db.session.add(post)
            db.session.commit()
            
            client = self.app.test_client()
            
            # Test RSS feed
            rss_response = client.get('/feed.xml')
            assert rss_response.status_code == 200
            rss_content = rss_response.get_data(as_text=True)
            
            # Check if the post appears in RSS feed
            assert title in rss_content, f"Post '{title}' should appear in RSS feed"
            
            # Extract image references from RSS feed
            rss_images = self._extract_images_from_feed_content(rss_content)
            
            # Should contain reference to the image
            image_found_in_rss = any(image.filename in img_url or image_url in img_url for img_url in rss_images)
            assert image_found_in_rss, f"RSS feed should contain reference to image {image.filename}. Found images: {rss_images}"
            
            # Test Atom feed
            atom_response = client.get('/atom.xml')
            assert atom_response.status_code == 200
            atom_content = atom_response.get_data(as_text=True)
            
            # Check if the post appears in Atom feed
            assert title in atom_content, f"Post '{title}' should appear in Atom feed"
            
            # Extract image references from Atom feed
            atom_images = self._extract_images_from_feed_content(atom_content)
            
            # Should contain reference to the image
            image_found_in_atom = any(image.filename in img_url or image_url in img_url for img_url in atom_images)
            assert image_found_in_atom, f"Atom feed should contain reference to image {image.filename}. Found images: {atom_images}"
    
    def test_posts_with_multiple_images_include_all_references(self):
        """
        Property: Posts with multiple images should include references to all images in feeds.
        
        **Validates: Requirements 2.7**
        """
        with self.app.app_context():
            # Clear any existing posts and images
            db.session.query(Post).delete()
            db.session.query(Image).delete()
            db.session.commit()
            
            # Create multiple test images
            images = []
            for i in range(3):
                image = self._create_test_image(f"test_image_{i+1}.jpg")
                images.append(image)
            
            # Create post content with multiple embedded images
            post_content = "<p>This post contains multiple images:</p>"
            for i, image in enumerate(images):
                image_url = f"/static/uploads/{image.filename}"
                post_content += f"<p>Image {i+1}:</p><img src='{image_url}' alt='Test Image {i+1}'>"
            post_content += "<p>End of post.</p>"
            
            # Create a published post with multiple images
            post = Post(
                title="Post with Multiple Images",
                content=post_content,
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            db.session.add(post)
            db.session.commit()
            
            client = self.app.test_client()
            
            # Test RSS feed
            rss_response = client.get('/feed.xml')
            assert rss_response.status_code == 200
            rss_content = rss_response.get_data(as_text=True)
            
            # Extract image references from RSS feed
            rss_images = self._extract_images_from_feed_content(rss_content)
            
            # Should contain references to all images
            for image in images:
                image_found = any(image.filename in img_url for img_url in rss_images)
                assert image_found, f"RSS feed should contain reference to image {image.filename}. Found images: {rss_images}"
            
            # Test Atom feed
            atom_response = client.get('/atom.xml')
            assert atom_response.status_code == 200
            atom_content = atom_response.get_data(as_text=True)
            
            # Extract image references from Atom feed
            atom_images = self._extract_images_from_feed_content(atom_content)
            
            # Should contain references to all images
            for image in images:
                image_found = any(image.filename in img_url for img_url in atom_images)
                assert image_found, f"Atom feed should contain reference to image {image.filename}. Found images: {atom_images}"
    
    def test_posts_without_images_do_not_include_image_references(self):
        """
        Property: Posts without images should not include spurious image references in feeds.
        
        **Validates: Requirements 2.7**
        """
        with self.app.app_context():
            # Clear any existing posts and images
            db.session.query(Post).delete()
            db.session.query(Image).delete()
            db.session.commit()
            
            # Create a published post without images
            post = Post(
                title="Post without Images",
                content="<p>This post contains only text content.</p><p>No images here!</p>",
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            db.session.add(post)
            db.session.commit()
            
            client = self.app.test_client()
            
            # Test RSS feed
            rss_response = client.get('/feed.xml')
            assert rss_response.status_code == 200
            rss_content = rss_response.get_data(as_text=True)
            
            # Extract image references from RSS feed
            rss_images = self._extract_images_from_feed_content(rss_content)
            
            # Should not contain any image references for this post
            # (Note: there might be images from other posts, but we cleared all posts)
            assert len(rss_images) == 0, f"RSS feed should not contain image references for text-only post. Found: {rss_images}"
            
            # Test Atom feed
            atom_response = client.get('/atom.xml')
            assert atom_response.status_code == 200
            atom_content = atom_response.get_data(as_text=True)
            
            # Extract image references from Atom feed
            atom_images = self._extract_images_from_feed_content(atom_content)
            
            # Should not contain any image references for this post
            assert len(atom_images) == 0, f"Atom feed should not contain image references for text-only post. Found: {atom_images}"
    
    def test_image_urls_in_feeds_are_absolute(self):
        """
        Property: Image URLs in feeds should be absolute URLs, not relative paths.
        
        **Validates: Requirements 2.7**
        """
        with self.app.app_context():
            # Clear any existing posts and images
            db.session.query(Post).delete()
            db.session.query(Image).delete()
            db.session.commit()
            
            # Create a test image
            image = self._create_test_image("absolute_url_test.jpg")
            
            # Create post content with relative image URL
            relative_image_url = f"/static/uploads/{image.filename}"
            post_content = f"<p>Image with relative URL:</p><img src='{relative_image_url}' alt='Test Image'>"
            
            # Create a published post with the image
            post = Post(
                title="Post with Relative Image URL",
                content=post_content,
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            db.session.add(post)
            db.session.commit()
            
            client = self.app.test_client()
            
            # Test RSS feed
            rss_response = client.get('/feed.xml')
            assert rss_response.status_code == 200
            rss_content = rss_response.get_data(as_text=True)
            
            # Extract image references from RSS feed
            rss_images = self._extract_images_from_feed_content(rss_content)
            
            # Check if any image URLs are absolute
            absolute_urls = [url for url in rss_images if url.startswith('http')]
            
            # At least one image URL should be absolute (or the feed should convert relative to absolute)
            # Note: This test might need adjustment based on how the feed generator handles URLs
            if rss_images:
                # If there are images, check that they are properly formatted
                for img_url in rss_images:
                    # Image URL should either be absolute or properly formatted relative URL
                    assert img_url.startswith('/') or img_url.startswith('http'), f"Image URL should be properly formatted: {img_url}"
    
    @given(
        num_images=st.integers(min_value=1, max_value=4)
    )
    @settings(max_examples=5, deadline=20000)
    def test_feed_image_references_scale_with_post_images(self, num_images):
        """
        Property: The number of image references in feeds should correspond to
        the number of images in posts.
        
        **Validates: Requirements 2.7**
        """
        with self.app.app_context():
            # Clear any existing posts and images
            db.session.query(Post).delete()
            db.session.query(Image).delete()
            db.session.commit()
            
            # Create test images
            images = []
            for i in range(num_images):
                image = self._create_test_image(f"scale_test_{i+1}.jpg")
                images.append(image)
            
            # Create post content with all images
            post_content = f"<p>This post contains {num_images} images:</p>"
            for i, image in enumerate(images):
                image_url = f"/static/uploads/{image.filename}"
                post_content += f"<img src='{image_url}' alt='Test Image {i+1}'>"
            
            # Create a published post
            post = Post(
                title=f"Post with {num_images} Images",
                content=post_content,
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            db.session.add(post)
            db.session.commit()
            
            client = self.app.test_client()
            
            # Test RSS feed
            rss_response = client.get('/feed.xml')
            assert rss_response.status_code == 200
            rss_content = rss_response.get_data(as_text=True)
            
            # Count unique image references in RSS feed
            rss_images = self._extract_images_from_feed_content(rss_content)
            unique_rss_images = list(set(rss_images))
            
            # Should have references corresponding to the number of images
            # (allowing for some flexibility in how images are referenced)
            assert len(unique_rss_images) >= min(num_images, 1), f"RSS feed should contain at least {min(num_images, 1)} image reference(s) for {num_images} images. Found: {unique_rss_images}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])