"""
About Page Manager for handling author profile data and social links.

This module provides functionality for managing author profile information,
including profile image upload, social media links, and content management.
"""

import os
import uuid
from werkzeug.utils import secure_filename
from PIL import Image
from models import db, AuthorProfile
from image_handler import ImageHandler


class AboutPageManager:
    """Manager class for about page and author profile functionality."""
    
    def __init__(self, app=None):
        """Initialize AboutPageManager with optional Flask app."""
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app configuration."""
        self.app = app
        self.upload_folder = app.config.get('UPLOAD_FOLDER', 'static/uploads')
        self.allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        self.max_file_size = app.config.get('MAX_PROFILE_IMAGE_SIZE', 5 * 1024 * 1024)  # 5MB
    
    def get_author_profile(self):
        """
        Get current author profile or create default.
        
        Returns:
            AuthorProfile: The current author profile or a new default one
        """
        profile = db.session.query(AuthorProfile).first()
        if not profile:
            # Create default profile
            profile = AuthorProfile(
                name="Blog Author",
                bio="Welcome to my blog! I write about various topics that interest me.",
                mission_statement="To share knowledge and inspire others through thoughtful content.",
                email="author@example.com"
            )
            profile.set_expertise_areas(["Writing", "Technology"])
            db.session.add(profile)
            db.session.commit()
        
        return profile
    
    def update_author_profile(self, **kwargs):
        """
        Update author profile information.
        
        Args:
            **kwargs: Profile fields to update (name, bio, mission_statement, etc.)
            
        Returns:
            tuple: (success: bool, message: str, profile: AuthorProfile)
        """
        try:
            profile = self.get_author_profile()
            
            # Update basic fields
            if 'name' in kwargs and kwargs['name'].strip():
                profile.name = kwargs['name'].strip()
            
            if 'bio' in kwargs:
                profile.bio = kwargs['bio']
            
            if 'mission_statement' in kwargs:
                profile.mission_statement = kwargs['mission_statement']
            
            if 'email' in kwargs and kwargs['email'].strip():
                profile.email = kwargs['email'].strip()
            
            # Update social media fields
            profile.twitter_handle = kwargs.get('twitter_handle', '').strip() or None
            profile.linkedin_url = kwargs.get('linkedin_url', '').strip() or None
            profile.github_url = kwargs.get('github_url', '').strip() or None
            profile.website_url = kwargs.get('website_url', '').strip() or None
            
            # Update expertise areas
            if 'expertise_areas' in kwargs:
                if isinstance(kwargs['expertise_areas'], list):
                    profile.set_expertise_areas(kwargs['expertise_areas'])
                elif isinstance(kwargs['expertise_areas'], str):
                    # Parse comma-separated string
                    areas = [area.strip() for area in kwargs['expertise_areas'].split(',') if area.strip()]
                    profile.set_expertise_areas(areas)
            
            db.session.commit()
            return True, "Profile updated successfully", profile
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating profile: {str(e)}", None
    
    def get_social_links(self):
        """
        Get formatted social media links.
        
        Returns:
            dict: Dictionary of social media links with labels
        """
        profile = self.get_author_profile()
        links = {}
        
        if profile.twitter_handle:
            # Handle both @username and username formats
            handle = profile.twitter_handle.lstrip('@')
            links['Twitter'] = f"https://twitter.com/{handle}"
        
        if profile.linkedin_url:
            links['LinkedIn'] = profile.linkedin_url
        
        if profile.github_url:
            links['GitHub'] = profile.github_url
        
        if profile.website_url:
            links['Website'] = profile.website_url
        
        return links
    
    def upload_profile_image(self, image_file):
        """
        Handle profile image upload and processing.
        
        Args:
            image_file: FileStorage object from form upload
            
        Returns:
            tuple: (success: bool, message: str, filename: str or None)
        """
        if not image_file or not image_file.filename:
            return False, "No image file provided", None
        
        # Check file extension
        if not self._allowed_file(image_file.filename):
            return False, f"Invalid file type. Allowed: {', '.join(self.allowed_extensions)}", None
        
        # Check file size
        image_file.seek(0, os.SEEK_END)
        file_size = image_file.tell()
        image_file.seek(0)
        
        if file_size > self.max_file_size:
            return False, f"File too large. Maximum size: {self.max_file_size // (1024*1024)}MB", None
        
        try:
            # Generate secure filename
            filename = secure_filename(image_file.filename)
            name, ext = os.path.splitext(filename)
            unique_filename = f"profile_{uuid.uuid4().hex[:8]}{ext}"
            
            # Ensure upload directory exists
            os.makedirs(self.upload_folder, exist_ok=True)
            
            # Save and process image
            filepath = os.path.join(self.upload_folder, unique_filename)
            image_file.save(filepath)
            
            # Process image (resize, optimize)
            self._process_profile_image(filepath)
            
            # Update profile with new image
            profile = self.get_author_profile()
            old_image = profile.profile_image
            profile.profile_image = unique_filename
            db.session.commit()
            
            # Clean up old image
            if old_image and old_image != unique_filename:
                old_path = os.path.join(self.upload_folder, old_image)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            return True, "Profile image uploaded successfully", unique_filename
            
        except Exception as e:
            return False, f"Error uploading image: {str(e)}", None
    
    def get_profile_image_url(self):
        """
        Get URL for profile image.
        
        Returns:
            str: URL to profile image or None if no image
        """
        profile = self.get_author_profile()
        if profile.profile_image:
            return f"/images/{profile.profile_image}"
        return None
    
    def delete_profile_image(self):
        """
        Delete current profile image.
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            profile = self.get_author_profile()
            if not profile.profile_image:
                return False, "No profile image to delete"
            
            # Delete file
            filepath = os.path.join(self.upload_folder, profile.profile_image)
            if os.path.exists(filepath):
                os.remove(filepath)
            
            # Update profile
            profile.profile_image = None
            db.session.commit()
            
            return True, "Profile image deleted successfully"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting image: {str(e)}"
    
    def _allowed_file(self, filename):
        """Check if file extension is allowed."""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def _process_profile_image(self, filepath):
        """
        Process profile image (resize, optimize).
        
        Args:
            filepath: Path to the uploaded image file
        """
        try:
            with Image.open(filepath) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Resize to reasonable dimensions (max 400x400)
                max_size = (400, 400)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save optimized image
                img.save(filepath, 'JPEG', quality=85, optimize=True)
                
        except Exception as e:
            # If processing fails, keep original file
            print(f"Warning: Could not process profile image: {e}")
    
    def get_profile_stats(self):
        """
        Get profile statistics and metadata.
        
        Returns:
            dict: Profile statistics
        """
        profile = self.get_author_profile()
        
        # Count related content (will be expanded as features are added)
        stats = {
            'profile_created': profile.created_at,
            'profile_updated': profile.updated_at,
            'has_profile_image': bool(profile.profile_image),
            'expertise_count': len(profile.get_expertise_areas()),
            'social_links_count': len(self.get_social_links())
        }
        
        return stats