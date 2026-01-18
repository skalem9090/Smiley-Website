"""
Property-based test for image reference integration.

**Feature: enhanced-content-management, Property 8: Image Reference Integration**

**Validates: Requirements 3.5, 3.6**

This test validates that successfully uploaded images are properly integrated
into post content and served with appropriate caching headers.
"""

import pytest
import os
import io
import tempfile
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from PIL import Image as PILImage
from werkzeug.datastructures import FileStorage
from flask import url_for

from app import create_app
from models import db, Image as ImageModel, Post, User
from image_handler import ImageHandler


class TestImageReferenceIntegration:
    """Test image reference integration using property-based testing."""

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
            
            # Create test user
            user = User(username='testuser', is_admin=True)
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            yield app
            db.session.remove()
            db.drop_all()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def create_test_image(self, format='JPEG', size=(100, 100)):
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
        width=st.integers(min_value=10, max_value=500),
        height=st.integers(min_value=10, max_value=500),
        filename_base=st.text(
            alphabet=st.characters(min_codepoint=97, max_codepoint=122),  # lowercase letters only
            min_size=3, max_size=20
        )
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_successful_image_upload_creates_proper_references(self, app_context, format, width, height, filename_base):
        """
        **Property 8: Image Reference Integration (Upload Success)**
        
        For any successfully uploaded image, the system should create proper
        database records and generate accessible URLs.
        
        **Validates: Requirements 3.5, 3.6**
        """
        # Create valid test image
        img_io, extension, mime_type = self.create_test_image(format, (width, height))
        filename = f"{filename_base}.{extension}"
        
        # Ensure file is under size limit
        file_size = len(img_io.getvalue())
        assume(file_size <= ImageHandler.MAX_FILE_SIZE)
        
        file_storage = self.create_file_storage(filename, img_io, mime_type)
        
        handler = ImageHandler()
        success, message, image_record = handler.save_image(file_storage)
        
        # Upload should succeed
        assert success, f"Valid {format} image should upload successfully: {message}"
        assert image_record is not None, "Image record should be created"
        
        # Verify database record properties
        assert image_record.original_name == filename, "Original filename should be preserved"
        assert image_record.filename != filename, "Stored filename should be different from original"
        assert image_record.file_size == file_size, "File size should be recorded correctly"
        assert image_record.mime_type == mime_type, "MIME type should be recorded correctly"
        assert image_record.id is not None, "Image should have a database ID"
        
        # Verify URL generation
        image_url = handler.get_image_url(image_record.filename)
        assert image_url.startswith('/static/uploads/'), "Image URL should point to uploads directory"
        assert image_record.filename in image_url, "Image URL should contain the filename"
        
        # Verify file exists on disk
        file_path = os.path.join(handler.upload_folder, image_record.filename)
        assert os.path.exists(file_path), "Image file should exist on disk"
        
        # Verify file content matches
        with open(file_path, 'rb') as saved_file:
            saved_content = saved_file.read()
            assert len(saved_content) == file_size, "Saved file should have correct size"

    @given(
        post_title=st.text(
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            min_size=5, max_size=50
        ).filter(lambda x: x.strip()),
        post_content=st.text(
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            min_size=10, max_size=200
        ).filter(lambda x: x.strip()),
        format=st.sampled_from(['JPEG', 'PNG', 'GIF'])
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_image_post_association_integration(self, app_context, post_title, post_content, format):
        """
        **Property 8: Image Reference Integration (Post Association)**
        
        For any image uploaded with a post association, the system should
        properly link the image to the post in the database.
        
        **Validates: Requirements 3.5**
        """
        # Create a test post
        post = Post(
            title=post_title,
            content=post_content,
            category='test'
        )
        db.session.add(post)
        db.session.commit()
        
        # Create and upload image associated with the post
        img_io, extension, mime_type = self.create_test_image(format, (100, 100))
        filename = f"test_image.{extension}"
        file_storage = self.create_file_storage(filename, img_io, mime_type)
        
        handler = ImageHandler()
        success, message, image_record = handler.save_image(file_storage, post.id)
        
        # Upload should succeed
        assert success, f"Image upload should succeed: {message}"
        assert image_record is not None, "Image record should be created"
        
        # Verify post association
        assert image_record.post_id == post.id, "Image should be associated with the post"
        
        # Verify reverse relationship
        post_images = handler.get_images_by_post(post.id)
        assert len(post_images) == 1, "Post should have one associated image"
        assert post_images[0].id == image_record.id, "Associated image should match uploaded image"
        
        # Verify database relationship
        db.session.refresh(post)
        assert len(post.images) == 1, "Post should have one image in relationship"
        assert post.images[0].id == image_record.id, "Post image relationship should be correct"

    def test_image_serving_with_caching_headers(self, app_context, client):
        """
        **Property 8: Image Reference Integration (Caching Headers)**
        
        For any served image, the system should include appropriate caching headers.
        
        **Validates: Requirements 3.6**
        """
        # Create and upload a test image
        img_io, extension, mime_type = self.create_test_image('JPEG', (50, 50))
        filename = f"test_cache.{extension}"
        file_storage = self.create_file_storage(filename, img_io, mime_type)
        
        handler = ImageHandler()
        success, message, image_record = handler.save_image(file_storage)
        
        assert success, f"Image upload should succeed: {message}"
        
        # Test serving the image
        response = client.get(f'/images/{image_record.filename}')
        
        # Should return the image successfully
        assert response.status_code == 200, "Image should be served successfully"
        
        # Should have appropriate caching headers
        assert 'Cache-Control' in response.headers, "Response should include Cache-Control header"
        assert 'public' in response.headers['Cache-Control'], "Cache-Control should be public"
        assert 'max-age' in response.headers['Cache-Control'], "Cache-Control should include max-age"
        
        # Should have ETag header
        assert 'ETag' in response.headers, "Response should include ETag header"
        assert image_record.filename in response.headers['ETag'], "ETag should include filename"
        
        # Content should match uploaded image
        assert len(response.data) == image_record.file_size, "Served content should match file size"

    def test_nonexistent_image_returns_404(self, app_context, client):
        """Test that requesting a nonexistent image returns 404."""
        response = client.get('/images/nonexistent_image.jpg')
        assert response.status_code == 404, "Nonexistent image should return 404"

    @given(
        num_images=st.integers(min_value=1, max_value=5),
        format=st.sampled_from(['JPEG', 'PNG', 'GIF'])
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_multiple_image_upload_and_retrieval(self, app_context, num_images, format):
        """
        **Property 8: Image Reference Integration (Multiple Images)**
        
        For any number of images uploaded to a post, the system should
        properly track and retrieve all associated images.
        
        **Validates: Requirements 3.5**
        """
        # Create a test post
        post = Post(
            title="Test Post with Multiple Images",
            content="This post has multiple images",
            category='test'
        )
        db.session.add(post)
        db.session.commit()
        
        handler = ImageHandler()
        uploaded_images = []
        
        # Upload multiple images
        for i in range(num_images):
            img_io, extension, mime_type = self.create_test_image(format, (50 + i * 10, 50 + i * 10))
            filename = f"test_image_{i}.{extension}"
            file_storage = self.create_file_storage(filename, img_io, mime_type)
            
            success, message, image_record = handler.save_image(file_storage, post.id)
            assert success, f"Image {i} upload should succeed: {message}"
            uploaded_images.append(image_record)
        
        # Verify all images are associated with the post
        post_images = handler.get_images_by_post(post.id)
        assert len(post_images) == num_images, f"Post should have {num_images} associated images"
        
        # Verify all uploaded images are in the retrieved list
        uploaded_ids = {img.id for img in uploaded_images}
        retrieved_ids = {img.id for img in post_images}
        assert uploaded_ids == retrieved_ids, "All uploaded images should be retrievable"
        
        # Verify each image has unique filename
        filenames = {img.filename for img in post_images}
        assert len(filenames) == num_images, "All images should have unique filenames"

    def test_image_cleanup_functionality(self, app_context):
        """Test that orphaned image cleanup works correctly."""
        handler = ImageHandler()
        
        # Clean up any existing orphaned files first
        handler.cleanup_orphaned_images()
        
        # Create and upload a test image
        img_io, extension, mime_type = self.create_test_image('JPEG', (100, 100))
        filename = f"test_cleanup.{extension}"
        file_storage = self.create_file_storage(filename, img_io, mime_type)
        
        success, message, image_record = handler.save_image(file_storage)
        assert success, "Image upload should succeed"
        
        # Verify file exists
        file_path = os.path.join(handler.upload_folder, image_record.filename)
        assert os.path.exists(file_path), "Image file should exist"
        
        # Delete database record but leave file
        db.session.delete(image_record)
        db.session.commit()
        
        # Run cleanup
        files_deleted, records_deleted = handler.cleanup_orphaned_images()
        
        # Should have cleaned up at least the orphaned file we created
        assert files_deleted >= 1, "Should have deleted at least one orphaned file"
        assert records_deleted == 0, "Should not have deleted any records"
        assert not os.path.exists(file_path), "Our orphaned file should be deleted"

    @given(
        image_format=st.sampled_from(['JPEG', 'PNG', 'GIF'])
    )
    @settings(max_examples=5, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_image_deletion_removes_file_and_record(self, app_context, image_format):
        """
        **Property 8: Image Reference Integration (Deletion)**
        
        For any uploaded image that is deleted, both the file and database
        record should be removed.
        
        **Validates: Requirements 3.5**
        """
        # Create and upload a test image
        img_io, extension, mime_type = self.create_test_image(image_format, (100, 100))
        filename = f"test_delete.{extension}"
        file_storage = self.create_file_storage(filename, img_io, mime_type)
        
        handler = ImageHandler()
        success, message, image_record = handler.save_image(file_storage)
        assert success, "Image upload should succeed"
        
        # Verify file and record exist
        file_path = os.path.join(handler.upload_folder, image_record.filename)
        assert os.path.exists(file_path), "Image file should exist"
        assert db.session.get(ImageModel, image_record.id) is not None, "Database record should exist"
        
        # Delete the image
        delete_success, delete_message = handler.delete_image(image_record.id)
        assert delete_success, f"Image deletion should succeed: {delete_message}"
        
        # Verify file and record are removed
        assert not os.path.exists(file_path), "Image file should be deleted"
        assert db.session.get(ImageModel, image_record.id) is None, "Database record should be deleted"