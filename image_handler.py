"""
Image Upload and Management System for Enhanced Content Management

This module provides the ImageHandler class for handling image operations including:
- File validation for type, size, and security
- Secure filename generation and storage functionality
- Image serving with appropriate HTTP headers
"""

import os
import uuid
import hashlib
import mimetypes
from typing import Optional, Tuple, List
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from PIL import Image
from models import db, Image as ImageModel


class ImageHandler:
    """
    Manages image upload, validation, and storage operations for the blog system.
    Provides secure file handling with comprehensive validation and storage management.
    """
    
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
    ALLOWED_MIME_TYPES = {
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif'
    }
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    UPLOAD_FOLDER = 'static/uploads'
    
    def __init__(self, upload_folder: str = None):
        """
        Initialize ImageHandler with optional custom upload folder.
        
        Args:
            upload_folder: Custom upload directory path (optional)
        """
        self.upload_folder = upload_folder or self.UPLOAD_FOLDER
        self._ensure_upload_directory()
    
    def _ensure_upload_directory(self) -> None:
        """Ensure upload directory exists with proper permissions."""
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder, mode=0o755, exist_ok=True)
    
    def validate_image(self, file: FileStorage) -> Tuple[bool, str]:
        """
        Validate uploaded image file for type, size, and content.
        
        Args:
            file: Uploaded file object from Flask request
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
            
        Requirements: 3.2, 3.3, 3.4
        """
        if not file or not file.filename:
            return False, "No file selected"
        
        # Check file extension
        if not self._has_allowed_extension(file.filename):
            allowed = ', '.join(self.ALLOWED_EXTENSIONS)
            return False, f"Invalid file type. Allowed types: {allowed}"
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset file pointer
        
        if file_size > self.MAX_FILE_SIZE:
            max_size_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            return False, f"File too large. Maximum size: {max_size_mb}MB"
        
        if file_size == 0:
            return False, "File is empty"
        
        # Validate MIME type using mimetypes and PIL
        try:
            # Get MIME type from filename
            mime_type, _ = mimetypes.guess_type(file.filename)
            if mime_type not in self.ALLOWED_MIME_TYPES:
                return False, f"Invalid file type. Detected type: {mime_type}"
            
            # Additional validation using PIL to ensure it's a valid image
            file.seek(0)
            with Image.open(file) as img:
                img.verify()  # Verify it's a valid image
                # Get actual format from PIL
                file.seek(0)
                with Image.open(file) as img2:
                    actual_format = img2.format.lower()
                    if actual_format not in ['jpeg', 'png', 'gif']:
                        return False, f"Unsupported image format: {actual_format}"
            file.seek(0)  # Reset file pointer after verification
            
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"
        
        return True, ""
    
    def _has_allowed_extension(self, filename: str) -> bool:
        """Check if filename has an allowed extension."""
        return ('.' in filename and 
                filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS)
    
    def generate_filename(self, original_filename: str) -> str:
        """
        Generate secure, unique filename for uploaded image.
        
        Args:
            original_filename: Original filename from upload
            
        Returns:
            Secure unique filename with original extension
            
        Requirements: 3.3, 3.4
        """
        if not original_filename:
            raise ValueError("Original filename cannot be empty")
        
        # Extract and sanitize file extension
        if '.' in original_filename:
            extension = original_filename.rsplit('.', 1)[1].lower()
            # Remove any dangerous characters from extension
            import re
            extension = re.sub(r'[^a-z0-9]', '', extension)
            # Ensure extension is valid
            if not extension or extension not in ['jpg', 'jpeg', 'png', 'gif']:
                extension = 'jpg'  # Default extension
        else:
            extension = 'jpg'  # Default extension
        
        # Generate unique filename using UUID and timestamp
        unique_id = str(uuid.uuid4())
        timestamp = str(int(os.path.getmtime(__file__) if os.path.exists(__file__) else 0))
        
        # Create hash of original filename for additional uniqueness
        filename_hash = hashlib.md5(original_filename.encode('utf-8')).hexdigest()[:8]
        
        secure_name = f"{unique_id}_{timestamp}_{filename_hash}.{extension}"
        return secure_name
    
    def save_image(self, file: FileStorage, post_id: Optional[int] = None) -> Tuple[bool, str, Optional[ImageModel]]:
        """
        Securely save uploaded image with unique filename.
        
        Args:
            file: Uploaded file object
            post_id: Optional post ID to associate image with
            
        Returns:
            Tuple of (success: bool, message: str, image_model: ImageModel or None)
            
        Requirements: 3.3, 3.4
        """
        # Validate the image first
        is_valid, error_message = self.validate_image(file)
        if not is_valid:
            return False, error_message, None
        
        try:
            # Generate secure filename
            secure_name = self.generate_filename(file.filename)
            file_path = os.path.join(self.upload_folder, secure_name)
            
            # Get file info before saving
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            # Detect MIME type using mimetypes
            mime_type, _ = mimetypes.guess_type(file.filename)
            if not mime_type:
                # Fallback based on file extension
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                mime_type_map = {
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg', 
                    'png': 'image/png',
                    'gif': 'image/gif'
                }
                mime_type = mime_type_map.get(ext, 'image/jpeg')
            
            # Save file to disk
            file.save(file_path)
            
            # Create database record
            image_record = ImageModel(
                filename=secure_name,
                original_name=file.filename,
                file_size=file_size,
                mime_type=mime_type,
                post_id=post_id
            )
            
            db.session.add(image_record)
            db.session.commit()
            
            return True, f"Image uploaded successfully as {secure_name}", image_record
            
        except Exception as e:
            # Clean up file if database operation fails
            if 'file_path' in locals() and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            
            db.session.rollback()
            return False, f"Error saving image: {str(e)}", None
    
    def get_image_url(self, filename: str) -> str:
        """
        Generate URL for serving uploaded images.
        
        Args:
            filename: Filename of the uploaded image
            
        Returns:
            URL path for accessing the image
            
        Requirements: 3.6
        """
        if not filename:
            raise ValueError("Filename cannot be empty")
        
        # Return relative URL path for Flask static files
        return f"/static/uploads/{filename}"
    
    def delete_image(self, image_id: int) -> Tuple[bool, str]:
        """
        Delete image file and database record.
        
        Args:
            image_id: ID of the image to delete
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            image_record = db.session.get(ImageModel, image_id)
            if not image_record:
                return False, "Image not found"
            
            # Delete file from disk
            file_path = os.path.join(self.upload_folder, image_record.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Delete database record
            db.session.delete(image_record)
            db.session.commit()
            
            return True, "Image deleted successfully"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting image: {str(e)}"
    
    def get_image_info(self, image_id: int) -> Optional[ImageModel]:
        """
        Get image information from database.
        
        Args:
            image_id: ID of the image
            
        Returns:
            ImageModel object or None if not found
        """
        return db.session.get(ImageModel, image_id)
    
    def get_images_by_post(self, post_id: int) -> List[ImageModel]:
        """
        Get all images associated with a specific post.
        
        Args:
            post_id: ID of the post
            
        Returns:
            List of ImageModel objects
        """
        return ImageModel.query.filter_by(post_id=post_id).all()
    
    def cleanup_orphaned_images(self) -> Tuple[int, int]:
        """
        Clean up orphaned images (files without database records or vice versa).
        
        Returns:
            Tuple of (files_deleted: int, records_deleted: int)
        """
        files_deleted = 0
        records_deleted = 0
        
        try:
            # Find database records without corresponding files
            all_images = ImageModel.query.all()
            for image in all_images:
                file_path = os.path.join(self.upload_folder, image.filename)
                if not os.path.exists(file_path):
                    db.session.delete(image)
                    records_deleted += 1
            
            # Find files without database records
            if os.path.exists(self.upload_folder):
                for filename in os.listdir(self.upload_folder):
                    if not ImageModel.query.filter_by(filename=filename).first():
                        file_path = os.path.join(self.upload_folder, filename)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            files_deleted += 1
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise RuntimeError(f"Error during cleanup: {str(e)}")
        
        return files_deleted, records_deleted