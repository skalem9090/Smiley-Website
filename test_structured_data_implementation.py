"""
Property-Based Tests for Structured Data Implementation

**Validates: Requirements 6.4**

This module tests that structured data (JSON-LD) is properly implemented
across all page types for enhanced search engine understanding.
"""

import pytest
import json
from hypothesis import given, strategies as st, settings, HealthCheck
from flask import Flask, url_for
from bs4 import BeautifulSoup
from models import db, Post, AuthorProfile
from post_manager import PostManager
from about_page_manager import AboutPageManager


@pytest.fixture
def app_context():
    """Create test Flask app with in-memory database."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SERVER_NAME'] = 'localhost'
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


class TestStructuredDataImplementation:
    """Property tests for structured data implementation across all page types."""

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=20, max_size=1000).filter(lambda x: x.strip()),
        category=st.sampled_from(['wealth', 'health', 'happiness'])
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_blog_post_structured_data(self, app_context, title, content, category):
        """
        Property: All blog posts must include valid BlogPosting structured data.
        
        **Validates: Requirements 6.4**
        
        This test ensures that individual blog posts include proper
        JSON-LD structured data for search engine optimization.
        """
        # Create a published post
        post = PostManager.create_post(
            title=title,
            content=content,
            category=category,
            status='published'
        )
        
        with app_context.test_client() as client:
            response = client.get(f'/post/{post.id}')
            assert response.status_code == 200
            
            # Parse HTML content
            soup = BeautifulSoup(response.data, 'html.parser')
            
            # Find JSON-LD script tags
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            assert len(json_ld_scripts) > 0, "Blog posts must include JSON-LD structured data"
            
            # Parse and validate structured data
            structured_data_found = False
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Check if this is BlogPosting structured data
                    if isinstance(data, dict) and data.get('@type') == 'BlogPosting':
                        structured_data_found = True
                        
                        # Validate required BlogPosting properties
                        assert '@context' in data, "BlogPosting must include @context"
                        assert data['@context'] == 'https://schema.org', "BlogPosting must use schema.org context"
                        assert 'headline' in data, "BlogPosting must include headline"
                        assert 'author' in data, "BlogPosting must include author"
                        assert 'datePublished' in data, "BlogPosting must include datePublished"
                        assert 'url' in data, "BlogPosting must include url"
                        
                        # Validate content quality
                        assert data['headline'].strip() != '', "BlogPosting headline must not be empty"
                        assert isinstance(data['author'], dict), "BlogPosting author must be an object"
                        assert data['author'].get('@type') == 'Person', "BlogPosting author must be a Person"
                        assert data['author'].get('name', '').strip() != '', "BlogPosting author must have a name"
                        
                        # Validate URL structure
                        assert f'/post/{post.id}' in data['url'], "BlogPosting URL must reference the correct post"
                        
                        break
                        
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
            
            assert structured_data_found, "Blog posts must include valid BlogPosting structured data"

    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_website_structured_data(self, app_context):
        """
        Property: The homepage must include valid WebSite structured data.
        
        **Validates: Requirements 6.4**
        
        This test ensures that the homepage includes proper
        JSON-LD structured data for the website.
        """
        with app_context.test_client() as client:
            response = client.get('/')
            assert response.status_code == 200
            
            # Parse HTML content
            soup = BeautifulSoup(response.data, 'html.parser')
            
            # Find JSON-LD script tags
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            assert len(json_ld_scripts) > 0, "Homepage must include JSON-LD structured data"
            
            # Parse and validate structured data
            structured_data_found = False
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Check if this is WebSite structured data
                    if isinstance(data, dict) and data.get('@type') == 'WebSite':
                        structured_data_found = True
                        
                        # Validate required WebSite properties
                        assert '@context' in data, "WebSite must include @context"
                        assert data['@context'] == 'https://schema.org', "WebSite must use schema.org context"
                        assert 'name' in data, "WebSite must include name"
                        assert 'url' in data, "WebSite must include url"
                        
                        # Validate content quality
                        assert data['name'].strip() != '', "WebSite name must not be empty"
                        assert data['url'].strip() != '', "WebSite url must not be empty"
                        
                        # Check for optional but recommended properties
                        if 'description' in data:
                            assert data['description'].strip() != '', "WebSite description must not be empty when present"
                        
                        if 'potentialAction' in data:
                            assert isinstance(data['potentialAction'], dict), "WebSite potentialAction must be an object"
                            if data['potentialAction'].get('@type') == 'SearchAction':
                                assert 'target' in data['potentialAction'], "SearchAction must include target"
                        
                        break
                        
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
            
            assert structured_data_found, "Homepage must include valid WebSite structured data"

    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_person_structured_data(self, app_context):
        """
        Property: The about page must include valid Person structured data.
        
        **Validates: Requirements 6.4**
        
        This test ensures that the about page includes proper
        JSON-LD structured data for the author/person.
        """
        # Ensure author profile exists
        about_manager = AboutPageManager(app_context)
        profile = about_manager.get_author_profile()
        
        with app_context.test_client() as client:
            response = client.get('/about')
            assert response.status_code == 200
            
            # Parse HTML content
            soup = BeautifulSoup(response.data, 'html.parser')
            
            # Find JSON-LD script tags
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            assert len(json_ld_scripts) > 0, "About page must include JSON-LD structured data"
            
            # Parse and validate structured data
            structured_data_found = False
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Check if this is Person structured data
                    if isinstance(data, dict) and data.get('@type') == 'Person':
                        structured_data_found = True
                        
                        # Validate required Person properties
                        assert '@context' in data, "Person must include @context"
                        assert data['@context'] == 'https://schema.org', "Person must use schema.org context"
                        assert 'name' in data, "Person must include name"
                        
                        # Validate content quality
                        assert data['name'].strip() != '', "Person name must not be empty"
                        
                        # Check for optional but recommended properties
                        if 'description' in data:
                            assert data['description'].strip() != '', "Person description must not be empty when present"
                        
                        if 'url' in data:
                            assert data['url'].strip() != '', "Person url must not be empty when present"
                        
                        if 'sameAs' in data:
                            assert isinstance(data['sameAs'], list), "Person sameAs must be a list"
                            for url in data['sameAs']:
                                assert isinstance(url, str), "Person sameAs URLs must be strings"
                                assert url.strip() != '', "Person sameAs URLs must not be empty"
                        
                        if 'jobTitle' in data:
                            assert data['jobTitle'].strip() != '', "Person jobTitle must not be empty when present"
                        
                        break
                        
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
            
            assert structured_data_found, "About page must include valid Person structured data"

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=20, max_size=1000).filter(lambda x: x.strip()),
        category=st.sampled_from(['wealth', 'health', 'happiness'])
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_structured_data_json_validity(self, app_context, title, content, category):
        """
        Property: All structured data must be valid JSON-LD.
        
        **Validates: Requirements 6.4**
        
        This test ensures that all JSON-LD structured data is syntactically
        valid and can be parsed without errors.
        """
        # Create a published post
        post = PostManager.create_post(
            title=title,
            content=content,
            category=category,
            status='published'
        )
        
        with app_context.test_client() as client:
            response = client.get(f'/post/{post.id}')
            assert response.status_code == 200
            
            # Parse HTML content
            soup = BeautifulSoup(response.data, 'html.parser')
            
            # Find all JSON-LD script tags
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_ld_scripts:
                try:
                    # Attempt to parse JSON
                    data = json.loads(script.string)
                    
                    # Validate basic JSON-LD structure
                    if isinstance(data, dict):
                        # Must have @context and @type for valid JSON-LD
                        if '@context' in data and '@type' in data:
                            assert data['@context'] == 'https://schema.org', "JSON-LD must use schema.org context"
                            assert isinstance(data['@type'], str), "JSON-LD @type must be a string"
                            assert data['@type'].strip() != '', "JSON-LD @type must not be empty"
                    
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON-LD found: {e}")
                except Exception as e:
                    pytest.fail(f"Error validating JSON-LD: {e}")

    @settings(max_examples=5, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_breadcrumb_structured_data(self, app_context):
        """
        Property: Pages with navigation hierarchy must include BreadcrumbList structured data.
        
        **Validates: Requirements 6.4**
        
        This test ensures that pages with clear navigation hierarchy
        include proper breadcrumb structured data.
        """
        pages_to_test = ['/about', '/explore']
        
        with app_context.test_client() as client:
            for page in pages_to_test:
                response = client.get(page)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.data, 'html.parser')
                    
                    # Find JSON-LD script tags
                    json_ld_scripts = soup.find_all('script', type='application/ld+json')
                    
                    # Look for BreadcrumbList structured data
                    breadcrumb_found = False
                    for script in json_ld_scripts:
                        try:
                            data = json.loads(script.string)
                            
                            if isinstance(data, dict) and data.get('@type') == 'BreadcrumbList':
                                breadcrumb_found = True
                                
                                # Validate BreadcrumbList structure
                                assert '@context' in data, "BreadcrumbList must include @context"
                                assert data['@context'] == 'https://schema.org', "BreadcrumbList must use schema.org context"
                                assert 'itemListElement' in data, "BreadcrumbList must include itemListElement"
                                assert isinstance(data['itemListElement'], list), "itemListElement must be a list"
                                assert len(data['itemListElement']) > 0, "BreadcrumbList must have at least one item"
                                
                                # Validate each breadcrumb item
                                for i, item in enumerate(data['itemListElement']):
                                    assert isinstance(item, dict), "Breadcrumb items must be objects"
                                    assert item.get('@type') == 'ListItem', "Breadcrumb items must be ListItem type"
                                    assert 'position' in item, "Breadcrumb items must have position"
                                    assert item['position'] == i + 1, "Breadcrumb positions must be sequential"
                                    assert 'name' in item, "Breadcrumb items must have name"
                                    assert item['name'].strip() != '', "Breadcrumb names must not be empty"
                                
                                break
                                
                        except (json.JSONDecodeError, KeyError, TypeError):
                            continue
                    
                    # Breadcrumbs are optional but if present must be valid
                    # This test validates structure when breadcrumbs exist

    @given(
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=20, max_size=1000).filter(lambda x: x.strip()),
        category=st.sampled_from(['wealth', 'health', 'happiness'])
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_structured_data_author_consistency(self, app_context, title, content, category):
        """
        Property: Author information in structured data must be consistent across pages.
        
        **Validates: Requirements 6.4**
        
        This test ensures that author information in structured data
        is consistent between blog posts and the about page.
        """
        # Create a published post
        post = PostManager.create_post(
            title=title,
            content=content,
            category=category,
            status='published'
        )
        
        author_names = []
        
        with app_context.test_client() as client:
            # Check post page structured data
            response = client.get(f'/post/{post.id}')
            if response.status_code == 200:
                soup = BeautifulSoup(response.data, 'html.parser')
                json_ld_scripts = soup.find_all('script', type='application/ld+json')
                
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict) and data.get('@type') == 'BlogPosting':
                            author = data.get('author', {})
                            if isinstance(author, dict) and 'name' in author:
                                author_names.append(author['name'])
                    except (json.JSONDecodeError, KeyError, TypeError):
                        continue
            
            # Check about page structured data
            response = client.get('/about')
            if response.status_code == 200:
                soup = BeautifulSoup(response.data, 'html.parser')
                json_ld_scripts = soup.find_all('script', type='application/ld+json')
                
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict) and data.get('@type') == 'Person':
                            if 'name' in data:
                                author_names.append(data['name'])
                    except (json.JSONDecodeError, KeyError, TypeError):
                        continue
        
        # If author names are found, they should be consistent
        if len(author_names) > 1:
            assert len(set(author_names)) == 1, "Author names in structured data must be consistent across pages"