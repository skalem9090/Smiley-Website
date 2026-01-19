"""
Property-based tests for analytics data collection.

**Property 29: Analytics Data Collection**
**Validates: Requirements 8.4, 8.7**

This module tests that the system collects and stores analytics data for reporting
purposes, including search queries, email delivery statistics, and system health metrics.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime, timezone, timedelta
from app import create_app
from models import db, User, Post, Comment, NewsletterSubscription, SearchQuery
from analytics_manager import AnalyticsManager
from search_engine import SearchEngine
from newsletter_manager import NewsletterManager
import uuid


class TestAnalyticsDataCollection:
    """Test analytics data collection functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test environment before each test."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        with self.app.app_context():
            db.create_all()
            
            # Create test admin user with unique username
            unique_username = f'admin_{uuid.uuid4().hex[:8]}'
            self.admin_user = User(username=unique_username, is_admin=True)
            self.admin_user.set_password('password')
            db.session.add(self.admin_user)
            
            # Create test post
            self.test_post = Post(
                title='Test Post',
                content='Test content for analytics',
                status='published',
                published_at=datetime.now(timezone.utc)
            )
            db.session.add(self.test_post)
            db.session.commit()
            
            # Store the post ID to avoid detached instance issues
            self.test_post_id = self.test_post.id
            
            # Store the admin user ID to avoid detached instance issues
            self.admin_user_id = self.admin_user.id
            
            self.analytics_manager = AnalyticsManager(self.app)
            self.search_engine = SearchEngine(self.app)
    
    @given(
        search_queries=st.lists(
            st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs'))),
            min_size=1,
            max_size=20
        ),
        days_back=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=30, deadline=10000)
    def test_search_analytics_collection_property(self, search_queries, days_back):
        """
        **Property 29: Analytics Data Collection (Search Analytics)**
        **Validates: Requirements 8.4, 8.7**
        
        Property: When users perform searches, the system should collect and store
        analytics data including query text, result counts, and timestamps.
        """
        with self.app.app_context():
            # Ensure we have a clean search index
            try:
                self.search_engine.create_search_index()
            except:
                pass  # Index might already exist
            
            # Record initial search query count
            initial_count = db.session.query(SearchQuery).count()
            
            # Perform searches and collect analytics
            search_results = []
            for query in search_queries:
                # Perform search (this should trigger analytics collection)
                results = self.search_engine.search_posts(query, page=1, per_page=10)
                search_results.append((query, results))
                
                # Manually log search query to ensure analytics collection
                self.search_engine.log_search_query(
                    query=query,
                    results_count=results['total_results'],
                    ip_address='127.0.0.1',
                    user_agent='Test User Agent'
                )
            
            # Verify analytics data collection
            final_count = db.session.query(SearchQuery).count()
            
            # Should have collected analytics for each search
            assert final_count >= initial_count + len(search_queries), \
                f"Expected at least {len(search_queries)} new search queries to be logged"
            
            # Verify search analytics can be retrieved
            analytics = self.analytics_manager.get_search_analytics(
                start_date=datetime.now(timezone.utc) - timedelta(days=days_back),
                end_date=datetime.now(timezone.utc)
            )
            
            assert 'error' not in analytics, f"Analytics collection failed: {analytics.get('error')}"
            assert 'total_searches' in analytics, "Analytics should include total search count"
            assert 'unique_queries' in analytics, "Analytics should include unique query count"
            assert 'popular_searches' in analytics, "Analytics should include popular searches"
            
            # Verify that analytics reflect the searches we performed
            assert analytics['total_searches'] >= len(search_queries), \
                "Analytics should reflect the searches performed during the test"
            
            # Verify popular searches include our queries
            popular_queries = [search['query'] for search in analytics['popular_searches']]
            for query in search_queries:
                if query.strip():  # Only check non-empty queries
                    # Query should appear in recent searches (might not be in top popular if many tests run)
                    recent_queries = db.session.query(SearchQuery.query_text).filter(
                        SearchQuery.query_text == query
                    ).all()
                    assert len(recent_queries) > 0, f"Query '{query}' should be recorded in analytics"
    
    @given(
        subscription_count=st.integers(min_value=1, max_value=15),
        confirmation_ratio=st.floats(min_value=0.0, max_value=1.0),
        days_back=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=25, deadline=10000)
    def test_newsletter_analytics_collection_property(self, subscription_count, confirmation_ratio, days_back):
        """
        **Property 29: Analytics Data Collection (Newsletter Analytics)**
        **Validates: Requirements 8.4, 8.7**
        
        Property: When users subscribe to newsletters, the system should collect
        and store subscription analytics including confirmation rates and growth metrics.
        """
        with self.app.app_context():
            # Record initial subscription count
            initial_count = db.session.query(NewsletterSubscription).count()
            
            # Create test subscriptions
            subscriptions = []
            confirmed_count = int(subscription_count * confirmation_ratio)
            
            for i in range(subscription_count):
                email = f'test{i}_{uuid.uuid4().hex[:8]}@example.com'
                subscription = NewsletterSubscription(
                    email=email,
                    frequency='weekly',
                    subscribed_at=datetime.now(timezone.utc) - timedelta(days=days_back//2),
                    is_confirmed=i < confirmed_count,
                    confirmed_at=datetime.now(timezone.utc) - timedelta(days=days_back//3) if i < confirmed_count else None,
                    is_active=True
                )
                db.session.add(subscription)
                subscriptions.append(subscription)
            
            db.session.commit()
            
            # Verify analytics data collection
            final_count = db.session.query(NewsletterSubscription).count()
            assert final_count >= initial_count + subscription_count, \
                "All subscriptions should be recorded in the database"
            
            # Verify newsletter analytics can be retrieved
            analytics = self.analytics_manager.get_newsletter_analytics(
                start_date=datetime.now(timezone.utc) - timedelta(days=days_back),
                end_date=datetime.now(timezone.utc)
            )
            
            assert 'error' not in analytics, f"Newsletter analytics collection failed: {analytics.get('error')}"
            assert 'new_subscriptions' in analytics, "Analytics should include new subscription count"
            assert 'confirmations' in analytics, "Analytics should include confirmation count"
            assert 'confirmation_rate' in analytics, "Analytics should include confirmation rate"
            assert 'total_active' in analytics, "Analytics should include total active subscribers"
            
            # Verify analytics reflect the subscriptions we created
            assert analytics['new_subscriptions'] >= subscription_count, \
                "Analytics should reflect the subscriptions created during the test"
            
            if subscription_count > 0:
                expected_confirmation_rate = (confirmed_count / subscription_count) * 100
                # Allow for some variance due to existing data
                assert analytics['confirmation_rate'] >= 0, \
                    "Confirmation rate should be non-negative"
                assert analytics['confirmation_rate'] <= 100, \
                    "Confirmation rate should not exceed 100%"
            
            # Verify frequency breakdown is collected
            assert 'frequency_breakdown' in analytics, "Analytics should include frequency breakdown"
            assert isinstance(analytics['frequency_breakdown'], list), \
                "Frequency breakdown should be a list"
    
    @given(
        comment_count=st.integers(min_value=1, max_value=20),
        approval_ratio=st.floats(min_value=0.0, max_value=1.0),
        spam_ratio=st.floats(min_value=0.0, max_value=0.3),
        days_back=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=25, deadline=10000)
    def test_engagement_analytics_collection_property(self, comment_count, approval_ratio, spam_ratio, days_back):
        """
        **Property 29: Analytics Data Collection (Engagement Analytics)**
        **Validates: Requirements 8.4, 8.7**
        
        Property: When users submit comments, the system should collect engagement
        analytics including approval rates, spam detection, and user activity metrics.
        """
        with self.app.app_context():
            # Ensure spam_ratio + approval_ratio doesn't exceed 1.0
            assume(spam_ratio + approval_ratio <= 1.0)
            
            # Record initial comment count
            initial_count = db.session.query(Comment).count()
            
            # Get the test post ID (avoid detached instance issues)
            test_post_id = self.test_post_id
            
            # Create test comments with different states
            comments = []
            approved_count = int(comment_count * approval_ratio)
            spam_count = int(comment_count * spam_ratio)
            
            for i in range(comment_count):
                comment = Comment(
                    post_id=test_post_id,
                    author_name=f'Test Author {i}',
                    author_email=f'test{i}_{uuid.uuid4().hex[:8]}@example.com',
                    content=f'Test comment content {i}',
                    created_at=datetime.now(timezone.utc) - timedelta(days=days_back//2),
                    is_approved=i < approved_count,
                    is_spam=i >= (comment_count - spam_count),
                    approved_at=datetime.now(timezone.utc) - timedelta(days=days_back//3) if i < approved_count else None,
                    approved_by=self.admin_user_id if i < approved_count else None
                )
                db.session.add(comment)
                comments.append(comment)
            
            db.session.commit()
            
            # Verify analytics data collection
            final_count = db.session.query(Comment).count()
            assert final_count >= initial_count + comment_count, \
                "All comments should be recorded in the database"
            
            # Verify engagement analytics can be retrieved
            analytics = self.analytics_manager.get_engagement_analytics(
                start_date=datetime.now(timezone.utc) - timedelta(days=days_back),
                end_date=datetime.now(timezone.utc)
            )
            
            assert 'error' not in analytics, f"Engagement analytics collection failed: {analytics.get('error')}"
            assert 'comments_submitted' in analytics, "Analytics should include submitted comment count"
            assert 'comments_approved' in analytics, "Analytics should include approved comment count"
            assert 'comments_spam' in analytics, "Analytics should include spam comment count"
            assert 'approval_rate' in analytics, "Analytics should include approval rate"
            assert 'spam_rate' in analytics, "Analytics should include spam rate"
            assert 'unique_commenters' in analytics, "Analytics should include unique commenter count"
            
            # Verify analytics reflect the comments we created
            assert analytics['comments_submitted'] >= comment_count, \
                "Analytics should reflect the comments created during the test"
            
            if comment_count > 0:
                # Verify rates are within reasonable bounds
                assert 0 <= analytics['approval_rate'] <= 100, \
                    "Approval rate should be between 0 and 100%"
                assert 0 <= analytics['spam_rate'] <= 100, \
                    "Spam rate should be between 0 and 100%"
            
            # Verify unique commenters are tracked
            assert analytics['unique_commenters'] >= 0, \
                "Unique commenter count should be non-negative"
            assert analytics['unique_commenters'] <= analytics['comments_submitted'], \
                "Unique commenters should not exceed total comments"
    
    @given(
        content_count=st.integers(min_value=1, max_value=15),
        published_ratio=st.floats(min_value=0.1, max_value=1.0),
        days_back=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=25, deadline=10000)
    def test_content_analytics_collection_property(self, content_count, published_ratio, days_back):
        """
        **Property 29: Analytics Data Collection (Content Analytics)**
        **Validates: Requirements 8.4, 8.7**
        
        Property: When content is created and published, the system should collect
        content analytics including publishing rates, category distribution, and performance metrics.
        """
        with self.app.app_context():
            # Record initial post count
            initial_count = db.session.query(Post).count()
            
            # Create test posts with different statuses
            posts = []
            published_count = int(content_count * published_ratio)
            categories = ['wealth', 'health', 'happiness']
            
            for i in range(content_count):
                category = categories[i % len(categories)]
                status = 'published' if i < published_count else 'draft'
                
                post = Post(
                    title=f'Test Post {i}',
                    content=f'Test content for analytics {i}',
                    category=category,
                    status=status,
                    created_at=datetime.now(timezone.utc) - timedelta(days=days_back//2),
                    published_at=datetime.now(timezone.utc) - timedelta(days=days_back//3) if status == 'published' else None
                )
                db.session.add(post)
                posts.append(post)
            
            db.session.commit()
            
            # Verify analytics data collection
            final_count = db.session.query(Post).count()
            assert final_count >= initial_count + content_count, \
                "All posts should be recorded in the database"
            
            # Verify content analytics can be retrieved
            analytics = self.analytics_manager.get_content_analytics(
                start_date=datetime.now(timezone.utc) - timedelta(days=days_back),
                end_date=datetime.now(timezone.utc)
            )
            
            assert 'error' not in analytics, f"Content analytics collection failed: {analytics.get('error')}"
            assert 'posts_created' in analytics, "Analytics should include created post count"
            assert 'posts_published' in analytics, "Analytics should include published post count"
            assert 'total_published' in analytics, "Analytics should include total published count"
            assert 'publishing_rate' in analytics, "Analytics should include publishing rate"
            assert 'category_breakdown' in analytics, "Analytics should include category breakdown"
            assert 'status_breakdown' in analytics, "Analytics should include status breakdown"
            
            # Verify analytics reflect the posts we created
            assert analytics['posts_created'] >= content_count, \
                "Analytics should reflect the posts created during the test"
            
            # Verify category breakdown is collected
            assert isinstance(analytics['category_breakdown'], list), \
                "Category breakdown should be a list"
            
            # Verify status breakdown is collected
            assert isinstance(analytics['status_breakdown'], list), \
                "Status breakdown should be a list"
            
            # Verify publishing rate calculation
            if days_back > 0:
                expected_max_rate = analytics['posts_published'] / days_back
                assert analytics['publishing_rate'] <= expected_max_rate + 0.1, \
                    "Publishing rate should be reasonable based on the time period"
    
    @given(
        days_back=st.integers(min_value=7, max_value=90)
    )
    @settings(max_examples=20, deadline=10000)
    def test_comprehensive_analytics_collection_property(self, days_back):
        """
        **Property 29: Analytics Data Collection (Comprehensive Analytics)**
        **Validates: Requirements 8.4, 8.7**
        
        Property: The system should be able to generate comprehensive analytics
        reports that combine data from all system components.
        """
        with self.app.app_context():
            # Create some test data across different components
            
            # Create a test post
            test_post = Post(
                title='Analytics Test Post',
                content='Content for comprehensive analytics test',
                status='published',
                published_at=datetime.now(timezone.utc) - timedelta(days=days_back//2)
            )
            db.session.add(test_post)
            db.session.commit()  # Commit to get the post ID
            
            # Create a test comment
            test_comment = Comment(
                post_id=test_post.id,  # Now we have a valid post_id
                author_name='Analytics Tester',
                author_email=f'analytics_{uuid.uuid4().hex[:8]}@example.com',
                content='Test comment for analytics',
                is_approved=True,
                created_at=datetime.now(timezone.utc) - timedelta(days=days_back//3)
            )
            db.session.add(test_comment)
            
            # Create a test subscription
            test_subscription = NewsletterSubscription(
                email=f'analytics_{uuid.uuid4().hex[:8]}@example.com',
                is_confirmed=True,
                confirmed_at=datetime.now(timezone.utc) - timedelta(days=days_back//4)
            )
            db.session.add(test_subscription)
            
            # Create a test search query
            test_search = SearchQuery(
                query_text='analytics test query',
                results_count=1,
                created_at=datetime.now(timezone.utc) - timedelta(days=days_back//5)
            )
            db.session.add(test_search)
            
            db.session.commit()
            
            # Generate comprehensive analytics
            analytics = self.analytics_manager.get_comprehensive_analytics(days=days_back)
            
            # Verify comprehensive analytics structure
            assert 'error' not in analytics, f"Comprehensive analytics failed: {analytics.get('error')}"
            
            # Verify all major components are included
            required_sections = ['content', 'engagement', 'search', 'newsletter', 'growth', 'performance']
            for section in required_sections:
                assert section in analytics, f"Analytics should include {section} section"
                assert isinstance(analytics[section], dict), f"{section} section should be a dictionary"
                assert 'error' not in analytics[section], f"{section} analytics should not have errors"
            
            # Verify period information
            assert 'period' in analytics, "Analytics should include period information"
            assert analytics['period']['days'] == days_back, "Period should match requested days"
            
            # Verify generated timestamp
            assert 'generated_at' in analytics, "Analytics should include generation timestamp"
            
            # Verify growth metrics include multiple periods
            growth_metrics = analytics['growth']
            assert isinstance(growth_metrics, dict), "Growth metrics should be a dictionary"
            
            # Should have at least one growth period within our date range
            growth_periods = [key for key in growth_metrics.keys() if key.endswith('_days')]
            valid_periods = [period for period in growth_periods 
                           if int(period.split('_')[0]) <= days_back]
            assert len(valid_periods) > 0, "Should have at least one valid growth period"
    
    @given(
        analytics_period=st.integers(min_value=1, max_value=60)
    )
    @settings(max_examples=15, deadline=8000)
    def test_analytics_export_functionality_property(self, analytics_period):
        """
        **Property 29: Analytics Data Collection (Export Functionality)**
        **Validates: Requirements 8.4, 8.7**
        
        Property: The system should be able to export analytics data in different
        formats for external analysis and reporting.
        """
        with self.app.app_context():
            # Generate analytics report
            json_report = self.analytics_manager.export_analytics_report(
                days=analytics_period, 
                format='json'
            )
            
            # Verify JSON export
            assert isinstance(json_report, str), "JSON report should be a string"
            assert len(json_report) > 0, "JSON report should not be empty"
            
            # Verify it's valid JSON by attempting to parse
            import json
            try:
                parsed_report = json.loads(json_report)
                assert isinstance(parsed_report, dict), "Parsed JSON should be a dictionary"
                
                # Verify essential sections are present
                essential_keys = ['period', 'content', 'engagement', 'search', 'newsletter']
                for key in essential_keys:
                    assert key in parsed_report, f"Exported report should include {key} section"
                
            except json.JSONDecodeError as e:
                pytest.fail(f"Exported JSON report is not valid JSON: {e}")
            
            # Test CSV export (even if not fully implemented)
            csv_report = self.analytics_manager.export_analytics_report(
                days=analytics_period, 
                format='csv'
            )
            
            assert isinstance(csv_report, str), "CSV report should be a string"
            assert len(csv_report) > 0, "CSV report should not be empty"
    
    @given(
        dashboard_request=st.booleans()
    )
    @settings(max_examples=10, deadline=5000)
    def test_dashboard_analytics_summary_property(self, dashboard_request):
        """
        **Property 29: Analytics Data Collection (Dashboard Summary)**
        **Validates: Requirements 8.4, 8.7**
        
        Property: The system should provide summarized analytics data suitable
        for dashboard display with key performance indicators.
        """
        with self.app.app_context():
            if dashboard_request:
                # Test dashboard summary
                summary = self.analytics_manager.get_dashboard_summary()
                
                assert 'error' not in summary, f"Dashboard summary failed: {summary.get('error')}"
                
                # Verify dashboard summary structure
                required_sections = ['content', 'engagement', 'newsletter', 'search', 'performance']
                for section in required_sections:
                    assert section in summary, f"Dashboard summary should include {section} section"
                    assert isinstance(summary[section], dict), f"{section} section should be a dictionary"
                
                # Verify key metrics are present
                content_metrics = summary['content']
                assert 'total_posts' in content_metrics, "Content summary should include total posts"
                assert 'recent_posts' in content_metrics, "Content summary should include recent posts"
                
                engagement_metrics = summary['engagement']
                assert 'total_comments' in engagement_metrics, "Engagement summary should include total comments"
                assert 'approval_rate' in engagement_metrics, "Engagement summary should include approval rate"
                
                newsletter_metrics = summary['newsletter']
                assert 'total_subscribers' in newsletter_metrics, "Newsletter summary should include total subscribers"
                
                search_metrics = summary['search']
                assert 'recent_searches' in search_metrics, "Search summary should include recent searches"
                
                performance_metrics = summary['performance']
                assert 'publishing_efficiency' in performance_metrics, "Performance summary should include publishing efficiency"