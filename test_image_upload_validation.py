"""
Property-based test for image upload validation.

**Feature: enhanced-content-management, Property 7: Image Upload Validation**

**Validates: Requirements 3.2, 3.3, 3.4**

This test validates that the image upload system correctly validates file types,
rejects files exceeding size limits, and generates unique secure filenames for
accepted uploads.
"""

import pytest
import os
import tempfile
import io
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from PIL import Image as PILImage
from werkzeug.datastructures import FileStorage

from app import create_app
from models import db, Image as ImageModel
from image_handler import ImageHandler


class TestImageUploadValidation:
    """Test image upload validation using property-based testing."""

    @pytest.fixture
    def app(self):
        """Create test Flask application."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        return app

    @pytest.fixture
    def app_context(self, app):
        """Create application context for testing."""
        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()

    def create_test_image(self, format='JPEG', size=(100, 100), file_size_kb=None):
        """Create a test image file in memory."""
        img = PILImage.new('RGB', size, color='red')
        img_io = io.BytesIO()
        
        if format.upper() == 'JPEG':
            img.save(img_io, format='JPEG', quality=95)
            extension = 'jpg'
            mime_type = 'image/jpeg'
        elif format.upper() == 'PNG':
            img.save(img_io, format='PNG')
            extension = 'png'
            mime_type = 'image/png'
        elif format.upper() == 'GIF':
            img.save(img_io, format='GIF')
            extension = 'gif'
            mime_type = 'image/gif'
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        img_io.seek(0)
        
        # If specific file size is requested, pad or truncate
        if file_size_kb:
            current_size = len(img_io.getvalue())
            target_size = file_size_kb * 1024
            
            if current_size < target_size:
                # Pad with zeros to reach target size
                padding = b'\x00' * (target_size - current_size)
                img_io.write(padding)
            elif current_size > target_size:
                # Truncate to target size (this will make it invalid)
                img_io.truncate(target_size)
            
            img_io.seek(0)
        
        return img_io, extension, mime_type

    def create_file_storage(self, filename, content, content_type=None):
        """Create a FileStorage object for testing."""
        if isinstance(content, io.BytesIO):
            content.seek(0)
            content_bytes = content.read()
            content.seek(0)
        else:
            content_bytes = content
        
        return FileStorage(
            stream=io.BytesIO(content_bytes),
            filename=filename,
            content_type=content_type
        )

    @given(
        format=st.sampled_from(['JPEG', 'PNG', 'GIF']),
        width=st.integers(min_value=1, max_value=1000),
        height=st.integers(min_value=1, max_value=1000),
        filename_base=st.text(
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            min_size=1, max_size=50
        ).filter(lambda x: x.strip() and '.' not in x)
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_valid_image_upload_acceptance(self, app_context, format, width, height, filename_base):
        """
        **Property 7: Image Upload Validation (Valid Files)**
        
        For any valid image file (JPEG, PNG, GIF) under size limit,
        the system should accept the upload and generate a unique secure filename.
        
        **Validates: Requirements 3.2, 3.3, 3.4**
        """
        # Create valid test image
        img_io, extension, mime_type = self.create_test_image(format, (width, height))
        filename = f"{filename_base}.{extension}"
        
        # Ensure file is under size limit
        file_size = len(img_io.getvalue())
        assume(file_size <= ImageHandler.MAX_FILE_SIZE)
        
        file_storage = self.create_file_storage(filename, img_io, mime_type)
        
        handler = ImageHandler()
        is_valid, error_message = handler.validate_image(file_storage)
        
        # Valid images should be accepted
        assert is_valid, f"Valid {format} image should be accepted: {error_message}"
        assert error_message == "", f"Valid image should have no error message, got: {error_message}"
        
        # Test filename generation
        secure_filename = handler.generate_filename(filename)
        assert secure_filename != filename, "Generated filename should be different from original"
        assert secure_filename.endswith(f".{extension}"), f"Generated filename should preserve extension: {secure_filename}"
        assert len(secure_filename) > len(extension) + 1, "Generated filename should be longer than just extension"

    @given(
        invalid_extension=st.sampled_from(['txt', 'pdf', 'doc', 'exe', 'zip', 'mp4']),
        filename_base=st.text(
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            min_size=1, max_size=20
        ).filter(lambda x: x.strip())
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_file_type_rejection(self, app_context, invalid_extension, filename_base):
        """
        **Property 7: Image Upload Validation (Invalid Types)**
        
        For any file with unsupported extension, the system should reject the upload
        with appropriate error message.
        
        **Validates: Requirements 3.2**
        """
        filename = f"{filename_base}.{invalid_extension}"
        
        # Create dummy file content
        dummy_content = b"This is not an image file"
        file_storage = self.create_file_storage(filename, dummy_content)
        
        handler = ImageHandler()
        is_valid, error_message = handler.validate_image(file_storage)
        
        # Invalid file types should be rejected
        assert not is_valid, f"File with extension .{invalid_extension} should be rejected"
        assert "Invalid file type" in error_message or "Allowed types" in error_message, \
            f"Error message should mention invalid file type: {error_message}"

    @given(
        size_mb=st.floats(min_value=5.1, max_value=50.0),
        format=st.sampled_from(['JPEG', 'PNG', 'GIF'])
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_oversized_file_rejection(self, app_context, size_mb, format):
        """
        **Property 7: Image Upload Validation (Size Limits)**
        
        For any file exceeding the 5MB limit, the system should reject the upload
        with appropriate error message.
        
        **Validates: Requirements 3.4**
        """
        # Create oversized file
        size_kb = int(size_mb * 1024)
        img_io, extension, mime_type = self.create_test_image(format, file_size_kb=size_kb)
        filename = f"large_image.{extension}"
        
        file_storage = self.create_file_storage(filename, img_io, mime_type)
        
        handler = ImageHandler()
        is_valid, error_message = handler.validate_image(file_storage)
        
        # Oversized files should be rejected
        assert not is_valid, f"File of {size_mb}MB should be rejected (limit: 5MB)"
        assert "too large" in error_message.lower() or "maximum size" in error_message.lower(), \
            f"Error message should mention file size: {error_message}"

    @given(
        filename_base=st.text(
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            min_size=1, max_size=30
        ).filter(lambda x: x.strip())
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_empty_file_rejection(self, app_context, filename_base):
        """
        **Property 7: Image Upload Validation (Empty Files)**
        
        For any empty file, the system should reject the upload.
        
        **Validates: Requirements 3.2, 3.4**
        """
        filename = f"{filename_base}.jpg"
        
        # Create empty file
        empty_content = b""
        file_storage = self.create_file_storage(filename, empty_content, 'image/jpeg')
        
        handler = ImageHandler()
        is_valid, error_message = handler.validate_image(file_storage)
        
        # Empty files should be rejected
        assert not is_valid, "Empty file should be rejected"
        assert "empty" in error_message.lower(), f"Error message should mention empty file: {error_message}"

    @given(
        filename_base=st.text(
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            min_size=1, max_size=30
        ).filter(lambda x: x.strip())
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_corrupted_image_rejection(self, app_context, filename_base):
        """
        **Property 7: Image Upload Validation (Corrupted Files)**
        
        For any corrupted image file (valid extension but invalid content),
        the system should reject the upload.
        
        **Validates: Requirements 3.2, 3.4**
        """
        filename = f"{filename_base}.jpg"
        
        # Create corrupted image content (valid JPEG header but corrupted data)
        corrupted_content = b'\xff\xd8\xff\xe0' + b'corrupted data' * 100
        file_storage = self.create_file_storage(filename, corrupted_content, 'image/jpeg')
        
        handler = ImageHandler()
        is_valid, error_message = handler.validate_image(file_storage)
        
        # Corrupted files should be rejected
        assert not is_valid, "Corrupted image file should be rejected"
        assert "invalid" in error_message.lower() or "error" in error_message.lower(), \
            f"Error message should indicate invalid image: {error_message}"

    @given(
        original_filename=st.text(
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            min_size=1, max_size=50
        ).filter(lambda x: x.strip() and '.' in x)
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_filename_uniqueness_and_security(self, app_context, original_filename):
        """
        **Property 7: Image Upload Validation (Secure Filenames)**
        
        For any original filename, the system should generate unique, secure filenames
        that preserve the file extension but are different from the original.
        
        **Validates: Requirements 3.3, 3.4**
        """
        handler = ImageHandler()
        
        # Generate multiple filenames from the same original
        generated_filenames = set()
        for _ in range(5):
            secure_filename = handler.generate_filename(original_filename)
            generated_filenames.add(secure_filename)
        
        # All generated filenames should be unique
        assert len(generated_filenames) == 5, "Generated filenames should be unique"
        
        # Check each generated filename
        for secure_filename in generated_filenames:
            # Should preserve extension if original had a valid one
            if '.' in original_filename:
                original_ext = original_filename.rsplit('.', 1)[1].lower()
                # Remove dangerous characters from original extension for comparison
                import re
                sanitized_original_ext = re.sub(r'[^a-z0-9]', '', original_ext)
                
                if sanitized_original_ext and sanitized_original_ext in ['jpg', 'jpeg', 'png', 'gif']:
                    # Should preserve valid extension
                    assert secure_filename.endswith(f".{sanitized_original_ext}"), \
                        f"Generated filename should preserve valid extension: {secure_filename}"
                else:
                    # Should use default extension for invalid extensions
                    assert secure_filename.endswith(".jpg"), \
                        f"Generated filename should use default extension for invalid input: {secure_filename}"
            else:
                # Should use default extension when no extension in original
                assert secure_filename.endswith(".jpg"), \
                    f"Generated filename should use default extension: {secure_filename}"
            
            # Should be different from original
            assert secure_filename != original_filename, \
                "Generated filename should be different from original"
            
            # Should not contain potentially dangerous characters
            dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
            for char in dangerous_chars:
                assert char not in secure_filename, \
                    f"Generated filename should not contain '{char}': {secure_filename}"

    def test_no_file_rejection(self, app_context):
        """Test that missing file is properly rejected."""
        handler = ImageHandler()
        
        # Test with None
        is_valid, error_message = handler.validate_image(None)
        assert not is_valid, "None file should be rejected"
        assert "no file" in error_message.lower(), f"Error message should mention no file: {error_message}"
        
        # Test with file without filename
        mock_file = Mock()
        mock_file.filename = None
        is_valid, error_message = handler.validate_image(mock_file)
        assert not is_valid, "File without filename should be rejected"
        assert "no file" in error_message.lower(), f"Error message should mention no file: {error_message}"

    def test_image_save_and_database_integration(self, app_context):
        """Test that valid images are saved correctly with database records."""
        # Create valid test image
        img_io, extension, mime_type = self.create_test_image('JPEG', (200, 200))
        filename = f"test_image.{extension}"
        file_storage = self.create_file_storage(filename, img_io, mime_type)
        
        handler = ImageHandler()
        
        # Test saving
        success, message, image_record = handler.save_image(file_storage)
        
        assert success, f"Valid image should save successfully: {message}"
        assert image_record is not None, "Image record should be created"
        assert image_record.original_name == filename, "Original filename should be preserved"
        assert image_record.filename != filename, "Stored filename should be different from original"
        assert image_record.file_size > 0, "File size should be recorded"
        assert image_record.mime_type == mime_type, "MIME type should be recorded"
        
        # Verify database record exists
        db_record = ImageModel.query.filter_by(id=image_record.id).first()
        assert db_record is not None, "Image should exist in database"
        assert db_record.filename == image_record.filename, "Database record should match"