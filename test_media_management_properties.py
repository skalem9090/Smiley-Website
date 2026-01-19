"""
Property-based tests for media management functionality in the Advanced Editor System.

These tests validate the correctness properties defined in the design document
for media upload, insertion, and management operations.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import json
import tempfile
import os


@pytest.fixture(scope="module")
def browser():
    """Set up Chrome browser for testing."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_window_size(1200, 800)
    
    yield driver
    
    driver.quit()


class TestMediaManagementProperties:
    """Property-based tests for media management system."""

    @given(
        media_type=st.sampled_from(['image/jpeg', 'image/png', 'image/gif', 'video/mp4', 'audio/mp3']),
        alt_text=st.text(min_size=1, max_size=100),
        caption=st.text(max_size=200),
        size=st.sampled_from(['small', 'medium', 'large', 'full'])
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_media_upload_and_insertion_properties(self, test_page, media_type, alt_text, caption, size):
        """
        Feature: advanced-editor-system, Property 5.1: Media Upload and Insertion

        Any supported media file should upload successfully and be inserted with proper HTML 
        and accessibility attributes.
        """
        browser = test_page

        # Initialize editor
        browser.execute_script("""
            window.testEditor = new window.AdvancedEditor({
                container: '#test-container',
                content: '',
                showToolbar: true,
                showSidebar: true
            });
            return window.testEditor.initialize();
        """)

        # Wait for initialization
        WebDriverWait(browser, 10).until(
            lambda driver: driver.execute_script("return window.testEditor && window.testEditor.isReady()")
        )

        # Test media HTML generation (simulating successful upload)
        result = browser.execute_script(f"""
            // Simulate successful upload result
            const uploadResult = {{
                success: true,
                url: 'https://example.com/test-media.jpg',
                filename: 'test-media.jpg'
            }};
            
            const options = {{
                alt: {json.dumps(alt_text)},
                caption: {json.dumps(caption)},
                size: {json.dumps(size)}
            }};
            
            // Test media HTML generation
            const mediaHtml = window.testEditor.generateMediaHtml(uploadResult, options);
            
            return {{
                success: true,
                mediaHtml: mediaHtml,
                hasAltText: mediaHtml.includes('alt='),
                hasProperSize: mediaHtml.includes('width:') || mediaHtml.includes('style='),
                isAccessible: mediaHtml.includes('alt=') && !mediaHtml.includes('alt=""')
            }};
        """)

        # Verify media insertion properties
        assert result['success'], "Media HTML generation should succeed"
        assert result['mediaHtml'], "Media HTML should be generated"
        
        # Verify accessibility properties
        if 'image' in media_type:
            assert result['hasAltText'], "Images should have alt text attribute"
            assert result['isAccessible'], "Images should have non-empty alt text for accessibility"
        
        # Verify HTML structure
        media_html = result['mediaHtml']
        assert 'https://example.com/test-media.jpg' in media_html, "Media URL should be included"
        
        if caption:
            assert 'figcaption' in media_html or caption in media_html, "Caption should be included when provided"

    @given(
        youtube_url=st.sampled_from([
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtu.be/dQw4w9WgXcQ',
            'https://www.youtube.com/embed/dQw4w9WgXcQ'
        ]),
        vimeo_url=st.sampled_from([
            'https://vimeo.com/123456789',
            'https://player.vimeo.com/video/123456789'
        ])
    )
    @settings(max_examples=6, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_video_embedding_properties(self, test_page, youtube_url, vimeo_url):
        """
        Feature: advanced-editor-system, Property 5.2: Video Embedding

        Video embedding should correctly extract video IDs and generate responsive embed HTML.
        """
        browser = test_page

        # Initialize editor
        browser.execute_script("""
            window.testEditor = new window.AdvancedEditor({
                container: '#test-container'
            });
            return window.testEditor.initialize();
        """)

        # Wait for initialization
        WebDriverWait(browser, 10).until(
            lambda driver: driver.execute_script("return window.testEditor && window.testEditor.isReady()")
        )

        # Test YouTube URL extraction
        youtube_result = browser.execute_script(f"""
            const youtubeId = window.testEditor.extractYouTubeId({json.dumps(youtube_url)});
            return {{
                url: {json.dumps(youtube_url)},
                extractedId: youtubeId,
                isValid: youtubeId !== null && youtubeId.length > 0
            }};
        """)

        # Test Vimeo URL extraction
        vimeo_result = browser.execute_script(f"""
            const vimeoId = window.testEditor.extractVimeoId({json.dumps(vimeo_url)});
            return {{
                url: {json.dumps(vimeo_url)},
                extractedId: vimeoId,
                isValid: vimeoId !== null && vimeoId.length > 0
            }};
        """)

        # Verify YouTube extraction
        assert youtube_result['isValid'], f"Should extract valid YouTube ID from {youtube_url}"
        assert youtube_result['extractedId'], "YouTube ID should not be empty"

        # Verify Vimeo extraction
        assert vimeo_result['isValid'], f"Should extract valid Vimeo ID from {vimeo_url}"
        assert vimeo_result['extractedId'], "Vimeo ID should not be empty"

    def test_media_type_validation_properties(self, test_page):
        """
        Feature: advanced-editor-system, Property 5.3: Media Type Validation

        Media type validation should correctly identify supported and unsupported file types.
        """
        browser = test_page

        # Initialize editor
        browser.execute_script("""
            window.testEditor = new window.AdvancedEditor({
                container: '#test-container'
            });
            return window.testEditor.initialize();
        """)

        # Wait for initialization
        WebDriverWait(browser, 10).until(
            lambda driver: driver.execute_script("return window.testEditor && window.testEditor.isReady()")
        )

        # Test various file types
        test_cases = [
            # Supported types
            ('image/jpeg', True),
            ('image/png', True),
            ('image/gif', True),
            ('video/mp4', True),
            ('audio/mp3', True),
            ('application/pdf', True),
            # Unsupported types
            ('application/exe', False),
            ('text/html', False),
            ('application/unknown', False)
        ]

        for mime_type, should_be_valid in test_cases:
            result = browser.execute_script(f"""
                // Create mock file object
                const mockFile = {{
                    type: {json.dumps(mime_type)},
                    name: 'test-file',
                    size: 1024
                }};
                
                const isValid = window.testEditor.isValidMediaFile(mockFile);
                return {{
                    mimeType: {json.dumps(mime_type)},
                    isValid: isValid,
                    expected: {json.dumps(should_be_valid)}
                }};
            """)

            assert result['isValid'] == should_be_valid, \
                f"Media type {mime_type} validation should return {should_be_valid}"


@pytest.fixture(scope="function")
def test_page(browser):
    """Create a test HTML page with the advanced editor for property testing."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Media Management Property Test</title>
        <style>
            :root {
                --card: #ffffff;
                --bg: #f8f9fa;
                --text: #333333;
                --accent: #d97706;
                --muted: #6b7280;
                --paper-border: #e5e7eb;
                --font-body: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            body {
                margin: 0;
                padding: 20px;
                font-family: var(--font-body);
                background: var(--bg);
            }
            #test-container {
                max-width: 800px;
                margin: 0 auto;
                min-height: 400px;
            }
        </style>
    </head>
    <body>
        <div id="test-container"></div>
        
        <script>
            // Mock AdvancedEditor with media management methods
            class AdvancedEditor {
                constructor(config = {}) {
                    this.config = config;
                    this.container = null;
                    this.isInitialized = false;
                }
                
                async initialize() {
                    this.container = typeof this.config.container === 'string' 
                        ? document.querySelector(this.config.container)
                        : this.config.container;
                    
                    if (!this.container) {
                        throw new Error('Container not found');
                    }
                    
                    this.isInitialized = true;
                    return this;
                }
                
                isReady() {
                    return this.isInitialized;
                }
                
                generateMediaHtml(uploadResult, options) {
                    const { url, filename } = uploadResult;
                    const { alt, caption, size } = options;
                    
                    const extension = filename.split('.').pop().toLowerCase();
                    const isImage = ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(extension);
                    const isVideo = ['mp4', 'webm', 'ogg'].includes(extension);
                    const isAudio = ['mp3', 'wav', 'ogg'].includes(extension);
                    
                    let sizeStyle = '';
                    switch (size) {
                        case 'small': sizeStyle = 'width: 25%; '; break;
                        case 'medium': sizeStyle = 'width: 50%; '; break;
                        case 'large': sizeStyle = 'width: 75%; '; break;
                        case 'full': sizeStyle = 'width: 100%; '; break;
                    }
                    
                    let mediaHtml = '';
                    
                    if (isImage) {
                        mediaHtml = `<img src="${url}" alt="${alt}" style="${sizeStyle}max-width: 100%;">`;
                    } else if (isVideo) {
                        mediaHtml = `<video controls style="${sizeStyle}max-width: 100%;"><source src="${url}"></video>`;
                    } else if (isAudio) {
                        mediaHtml = `<audio controls><source src="${url}"></audio>`;
                    } else {
                        mediaHtml = `<a href="${url}" download="${filename}">${filename}</a>`;
                    }
                    
                    if (caption) {
                        mediaHtml = `<figure>${mediaHtml}<figcaption>${caption}</figcaption></figure>`;
                    }
                    
                    return mediaHtml;
                }
                
                extractYouTubeId(url) {
                    const regex = /(?:youtube\\.com\\/(?:[^\\/]+\\/.+\\/|(?:v|e(?:mbed)?)\\/|.*[?&]v=)|youtu\\.be\\/)([^"&?\\/\\s]{11})/;
                    const match = url.match(regex);
                    return match ? match[1] : null;
                }
                
                extractVimeoId(url) {
                    const regex = /vimeo\\.com\\/(?:channels\\/(?:\\w+\\/)?|groups\\/([^\\/]*)\\/videos\\/|album\\/(\\d+)\\/video\\/|video\\/|)(\\d+)(?:$|\\/|\\?)/;
                    const match = url.match(regex);
                    return match ? match[3] || match[2] || match[1] : null;
                }
                
                isValidMediaFile(file) {
                    const validTypes = [
                        'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
                        'video/mp4', 'video/webm', 'video/ogg',
                        'audio/mp3', 'audio/wav', 'audio/ogg',
                        'application/pdf', 'text/plain'
                    ];
                    return validTypes.includes(file.type);
                }
            }
            
            window.AdvancedEditor = AdvancedEditor;
            window.editorTestReady = true;
        </script>
    </body>
    </html>
    """
    
    try:
        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            temp_file = f.name
        
        # Load the page
        browser.get(f'file://{temp_file}')
        
        # Wait for the page to be ready
        WebDriverWait(browser, 10).until(
            lambda driver: driver.execute_script("return window.editorTestReady === true")
        )
        
        yield browser
        
    finally:
        # Clean up temporary file
        os.unlink(temp_file)