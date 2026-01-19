"""
Property tests for search infrastructure functionality.

This module contains property-based tests that validate the search system's
correctness properties across various scenarios and data inputs.
"""

import pytest
import hypothesis.strategies as st
from hypothesis import given, assume, settings, HealthCheck
from datetime import datetime, timezone, timedelta
import tempfile
import os
from flask import Flask
from models import db, Post, SearchQuery, User
from search_engine import SearchEngine
import string
import re


@pytest.fixture
def app():
    """Create test Flask app with in-memory database."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret'
    app.config['WTF_CSRF_ENABLED'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def search_engine(app):
    """Create SearchEngine instance for testing."""
    with app.app_context():
        engine = SearchEngine(app)
        engine.create_search_index()
        return engine


# Strategy for generating valid post content
post_content_strategy = st.text(
    alphabet=string.ascii_letters + string.digits + string.punctuation + ' \n\t',
    min_size=10,
    max_size=1000
)

# Strategy for generating post titles
post_title_strategy = st.text(
    alphabet=string.ascii_letters + string.digits + ' -_',
    min_size=5,
    max_size=100
).filter(lambda x: x.strip())

# Strategy for generating categories
category_strategy = st.sampled_from(['wealth', 'health', 'happiness', 'general'])

# Strategy for generating tags
tags_strategy = st.lists(
    st.text(alphabet=string.ascii_letters, min_size=2, max_size=20),
    min_size=0,
    max_size=5
).map(lambda tags: ', '.join(tags) if tags else '')


class TestFullTextSearchCoverage:
    """Property 6: Full-Text Search Coverage - Validates Requirements 3.1"""
    
    @given(
        title=post_title_strategy,
        content=post_content_strategy,
        category=category_strategy,
        tags=tags_strategy
    )
    @settings(max_examples=50, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_published_posts_are_searchable(self, app, search_engine, title, content, category, tags):
        """Property: All published posts must be findable through search."""
        with app.app_context():
            # Create a published post
            post = Post(
                title=title,
                content=content,
                category=category,
                tags=tags,
                status='published',
                created_at=datetime.now(timezone.utc),
                published_at=datetime.now(timezone.utc)
            )
            db.session.add(post)
            db.session.commit()
            
            # Index the post
            search_engine.index_post(post)
            db.session.commit()
            
            # Search for the post using its title
            title_words = title.split()
            if title_words:
                search_query = title_words[0]  # Use first word of title
                results = search_engine.search_posts(search_query)
                
                # The post should be found in search results
                post_ids = [result['post'].id for result in results['posts']]
                assert post.id in post_ids, f"Published post {post.id} not found when searching for '{search_query}'"
    
    @given(
        title=post_title_strategy,
        content=post_content_strategy,
        status=st.sampled_from(['draft', 'scheduled'])
    )
    @settings(max_examples=30, deadline=5000)
    def test_unpublished_posts_not_searchable(self, app, search_engine, title, content, status):
        """Property: Unpublished posts must not appear in search results."""
        with app.app_context():
            # Create an unpublished post
            post = Post(
                title=title,
                content=content,
                status=status,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(post)
            db.session.commit()
            
            # Try to index the post (should not be indexed)
            search_engine.index_post(post)
            db.session.commit()
            
            # Search for the post using its title
            title_words = title.split()
            if title_words:
                search_query = title_words[0]
                results = search_engine.search_posts(search_query)
                
                # The post should NOT be found in search results
                post_ids = [result['post'].id for result in results['posts']]
                assert post.id not in post_ids, f"Unpublished post {post.id} found in search results"
    
    @given(
        search_term=st.text(alphabet=string.ascii_letters + ' ', min_size=2, max_size=50)
    )
    @settings(max_examples=30, deadline=5000)
    def test_search_index_consistency(self, app, search_engine, search_term):
        """Property: Search index must be consistent with published posts."""
        with app.app_context():
            # Create multiple posts with the search term
            posts_with_term = []
            posts_without_term = []
            
            for i in range(3):
                # Post containing the search term
                post_with = Post(
                    title=f"Title with {search_term} content {i}",
                    content=f"This post contains the term {search_term} in its content.",
                    status='published',
                    created_at=datetime.now(timezone.utc),
                    published_at=datetime.now(timezone.utc)
                )
                posts_with_term.append(post_with)
                db.session.add(post_with)
                
                # Post not containing the search term
                post_without = Post(
                    title=f"Different title {i}",
                    content=f"This post does not contain the specific word we are looking for {i}.",
                    status='published',
                    created_at=datetime.now(timezone.utc),
                    published_at=datetime.now(timezone.utc)
                )
                posts_without_term.append(post_without)
                db.session.add(post_without)
            
            db.session.commit()
            
            # Index all posts
            for post in posts_with_term + posts_without_term:
                search_engine.index_post(post)
            db.session.commit()
            
            # Search for the term
            results = search_engine.search_posts(search_term)
            found_post_ids = [result['post'].id for result in results['posts']]
            
            # All posts with the term should be found
            for post in posts_with_term:
                assert post.id in found_post_ids, f"Post {post.id} with search term not found"
            
            # Posts without the term should not be found
            for post in posts_without_term:
                assert post.id not in found_post_ids, f"Post {post.id} without search term was found"


class TestSearchResultCompleteness:
    """Property 7: Search Result Completeness - Validates Requirements 3.2, 3.4, 3.7"""
    
    @given(
        query=st.text(alphabet=string.ascii_letters + ' ', min_size=3, max_size=30),
        num_posts=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=20, deadline=5000)
    def test_search_results_include_all_matches(self, app, search_engine, query, num_posts):
        """Property: Search results must include all posts that match the query."""
        with app.app_context():
            # Create posts that contain the query term
            matching_posts = []
            for i in range(num_posts):
                post = Post(
                    title=f"Post {i} about {query}",
                    content=f"This is content about {query} and related topics.",
                    status='published',
                    created_at=datetime.now(timezone.utc),
                    published_at=datetime.now(timezone.utc)
                )
                matching_posts.append(post)
                db.session.add(post)
            
            db.session.commit()
            
            # Index all posts
            for post in matching_posts:
                search_engine.index_post(post)
            db.session.commit()
            
            # Search with high per_page to get all results
            results = search_engine.search_posts(query, per_page=50)
            found_post_ids = [result['post'].id for result in results['posts']]
            
            # All matching posts should be found
            for post in matching_posts:
                assert post.id in found_post_ids, f"Matching post {post.id} not found in search results"
            
            # Total results count should match
            assert results['total_results'] >= len(matching_posts), "Total results count is less than expected matches"
    
    @given(
        query=st.text(alphabet=string.ascii_letters + ' ', min_size=3, max_size=20),
        page_size=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=15, deadline=5000)
    def test_search_pagination_completeness(self, app, search_engine, query, page_size):
        """Property: Paginated search results must cover all matches without duplication."""
        with app.app_context():
            # Create enough posts to test pagination
            num_posts = page_size * 2 + 1  # Ensure we have multiple pages
            matching_posts = []
            
            for i in range(num_posts):
                post = Post(
                    title=f"Post {i} containing {query}",
                    content=f"Content about {query} topic number {i}.",
                    status='published',
                    created_at=datetime.now(timezone.utc) - timedelta(minutes=i),  # Different timestamps
                    published_at=datetime.now(timezone.utc) - timedelta(minutes=i)
                )
                matching_posts.append(post)
                db.session.add(post)
            
            db.session.commit()
            
            # Index all posts
            for post in matching_posts:
                search_engine.index_post(post)
            db.session.commit()
            
            # Get all results through pagination
            all_found_ids = set()
            page = 1
            
            while True:
                results = search_engine.search_posts(query, page=page, per_page=page_size)
                
                if not results['posts']:
                    break
                
                page_post_ids = [result['post'].id for result in results['posts']]
                
                # Check for duplicates across pages
                for post_id in page_post_ids:
                    assert post_id not in all_found_ids, f"Post {post_id} found on multiple pages"
                    all_found_ids.add(post_id)
                
                page += 1
                
                # Safety check to prevent infinite loops
                if page > 10:
                    break
            
            # All matching posts should be found across all pages
            expected_ids = {post.id for post in matching_posts}
            assert all_found_ids == expected_ids, "Pagination did not return all expected posts"


class TestSearchAutocompleteFunction:
    """Property 8: Search Autocomplete Functionality - Validates Requirements 3.3"""
    
    @given(
        queries=st.lists(
            st.text(alphabet=string.ascii_letters + ' ', min_size=3, max_size=20),
            min_size=2,
            max_size=8
        )
    )
    @settings(max_examples=20, deadline=5000)
    def test_autocomplete_suggests_previous_queries(self, app, search_engine, queries):
        """Property: Autocomplete must suggest previously searched queries."""
        with app.app_context():
            # Log some search queries
            for query in queries:
                search_engine.log_search_query(
                    query=query,
                    results_count=5,
                    ip_address='127.0.0.1'
                )
            
            db.session.commit()
            
            # Test autocomplete for partial matches
            for query in queries:
                if len(query) >= 3:
                    partial = query[:3]  # Use first 3 characters
                    suggestions = search_engine.get_search_suggestions(partial)
                    
                    # The original query should be in suggestions if it starts with partial
                    matching_queries = [q for q in queries if q.startswith(partial)]
                    for matching_query in matching_queries:
                        assert matching_query in suggestions, f"Query '{matching_query}' not suggested for partial '{partial}'"
    
    @given(
        partial_query=st.text(alphabet=string.ascii_letters, min_size=1, max_size=3)
    )
    @settings(max_examples=15, deadline=5000)
    def test_autocomplete_respects_limits(self, app, search_engine, partial_query):
        """Property: Autocomplete must respect suggestion limits."""
        with app.app_context():
            # Create many queries that start with the partial
            for i in range(10):
                query = f"{partial_query}query{i}"
                search_engine.log_search_query(
                    query=query,
                    results_count=1,
                    ip_address='127.0.0.1'
                )
            
            db.session.commit()
            
            # Test different limits
            for limit in [1, 3, 5]:
                suggestions = search_engine.get_search_suggestions(partial_query, limit=limit)
                assert len(suggestions) <= limit, f"Autocomplete returned {len(suggestions)} suggestions, expected max {limit}"


class TestSearchFilteringAccuracy:
    """Property 9: Search Filtering Accuracy - Validates Requirements 3.5"""
    
    @given(
        query=st.text(alphabet=string.ascii_letters + ' ', min_size=3, max_size=20),
        target_category=category_strategy,
        other_categories=st.lists(category_strategy, min_size=1, max_size=3)
    )
    @settings(max_examples=15, deadline=5000)
    def test_category_filtering_accuracy(self, app, search_engine, query, target_category, other_categories):
        """Property: Category filtering must only return posts from the specified category."""
        assume(target_category not in other_categories)
        
        with app.app_context():
            # Create posts in target category
            target_posts = []
            for i in range(2):
                post = Post(
                    title=f"Post {i} about {query}",
                    content=f"Content about {query} in target category.",
                    category=target_category,
                    status='published',
                    created_at=datetime.now(timezone.utc),
                    published_at=datetime.now(timezone.utc)
                )
                target_posts.append(post)
                db.session.add(post)
            
            # Create posts in other categories
            other_posts = []
            for i, category in enumerate(other_categories):
                post = Post(
                    title=f"Other post {i} about {query}",
                    content=f"Content about {query} in other category.",
                    category=category,
                    status='published',
                    created_at=datetime.now(timezone.utc),
                    published_at=datetime.now(timezone.utc)
                )
                other_posts.append(post)
                db.session.add(post)
            
            db.session.commit()
            
            # Index all posts
            for post in target_posts + other_posts:
                search_engine.index_post(post)
            db.session.commit()
            
            # Search with category filter
            results = search_engine.search_posts(query, filters={'category': target_category})
            found_posts = [result['post'] for result in results['posts']]
            
            # All found posts should be from target category
            for post in found_posts:
                assert post.category == target_category, f"Post {post.id} has category '{post.category}', expected '{target_category}'"
            
            # All target posts should be found
            found_post_ids = [post.id for post in found_posts]
            for post in target_posts:
                assert post.id in found_post_ids, f"Target category post {post.id} not found"


class TestSearchPagination:
    """Property 10: Search Pagination - Validates Requirements 3.8"""
    
    @given(
        query=st.text(alphabet=string.ascii_letters + ' ', min_size=3, max_size=15),
        per_page=st.integers(min_value=1, max_value=5),
        total_posts=st.integers(min_value=3, max_value=15)
    )
    @settings(max_examples=10, deadline=5000)
    def test_pagination_consistency(self, app, search_engine, query, per_page, total_posts):
        """Property: Pagination must be mathematically consistent."""
        with app.app_context():
            # Create posts
            posts = []
            for i in range(total_posts):
                post = Post(
                    title=f"Post {i} about {query}",
                    content=f"Content {i} about {query}.",
                    status='published',
                    created_at=datetime.now(timezone.utc) - timedelta(minutes=i),
                    published_at=datetime.now(timezone.utc) - timedelta(minutes=i)
                )
                posts.append(post)
                db.session.add(post)
            
            db.session.commit()
            
            # Index all posts
            for post in posts:
                search_engine.index_post(post)
            db.session.commit()
            
            # Test first page
            results = search_engine.search_posts(query, page=1, per_page=per_page)
            
            # Verify pagination metadata
            expected_total_pages = (total_posts + per_page - 1) // per_page
            assert results['total_pages'] == expected_total_pages, f"Expected {expected_total_pages} pages, got {results['total_pages']}"
            assert results['page'] == 1, "Page number should be 1"
            assert results['per_page'] == per_page, f"Per page should be {per_page}"
            assert results['total_results'] == total_posts, f"Total results should be {total_posts}"
            
            # Verify has_prev and has_next
            assert not results['has_prev'], "First page should not have previous"
            assert results['has_next'] == (expected_total_pages > 1), "has_next should be True only if more than 1 page"
            
            # Verify page size
            expected_page_size = min(per_page, total_posts)
            assert len(results['posts']) == expected_page_size, f"Expected {expected_page_size} posts on first page"
    
    @given(
        query=st.text(alphabet=string.ascii_letters + ' ', min_size=3, max_size=15),
        per_page=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=10, deadline=5000)
    def test_pagination_boundary_conditions(self, app, search_engine, query, per_page):
        """Property: Pagination must handle boundary conditions correctly."""
        with app.app_context():
            # Create exactly enough posts for 2 full pages + 1 extra
            total_posts = per_page * 2 + 1
            posts = []
            
            for i in range(total_posts):
                post = Post(
                    title=f"Boundary post {i} about {query}",
                    content=f"Boundary content {i} about {query}.",
                    status='published',
                    created_at=datetime.now(timezone.utc) - timedelta(minutes=i),
                    published_at=datetime.now(timezone.utc) - timedelta(minutes=i)
                )
                posts.append(post)
                db.session.add(post)
            
            db.session.commit()
            
            # Index all posts
            for post in posts:
                search_engine.index_post(post)
            db.session.commit()
            
            # Test last page
            last_page = 3  # Should be page 3 with our setup
            results = search_engine.search_posts(query, page=last_page, per_page=per_page)
            
            # Last page should have exactly 1 post
            assert len(results['posts']) == 1, f"Last page should have 1 post, got {len(results['posts'])}"
            assert results['has_prev'], "Last page should have previous"
            assert not results['has_next'], "Last page should not have next"
            
            # Test page beyond last page
            beyond_last = last_page + 1
            results = search_engine.search_posts(query, page=beyond_last, per_page=per_page)
            assert len(results['posts']) == 0, "Page beyond last should have no posts"
            assert not results['has_next'], "Page beyond last should not have next"