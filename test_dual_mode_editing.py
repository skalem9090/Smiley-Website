"""
Property-based tests for dual-mode editing functionality.

Tests the WYSIWYG/Markdown mode switching and content preservation.
"""

import pytest
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from hypothesis import given, strategies as st, settings, HealthCheck


class TestDualModeEditing:
    """Test dual-mode editing functionality with property-based testing."""

    @pytest.fixture(scope="class")
    def test_page(self):
        """Set up a test page with the advanced editor."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        
        # Create a test HTML page with the editor
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Dual Mode Editor Test</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .test-container { width: 800px; height: 600px; }
            </style>
        </head>
        <body>
            <div id="test-container" class="test-container"></div>
            <script>
                // Mock CSS variables for testing
                document.documentElement.style.setProperty('--card', '#ffffff');
                document.documentElement.style.setProperty('--paper-border', '#e5e7eb');
                document.documentElement.style.setProperty('--bg', '#f9fafb');
                document.documentElement.style.setProperty('--text', '#111827');
                document.documentElement.style.setProperty('--accent', '#d97706');
                document.documentElement.style.setProperty('--muted', '#6b7280');
                document.documentElement.style.setProperty('--hover-bg', '#f3f4f6');
                document.documentElement.style.setProperty('--font-body', 'Arial, sans-serif');
                document.documentElement.style.setProperty('--font-heading', 'Arial, sans-serif');
            </script>
        </body>
        </html>
        """
        
        driver.get("data:text/html;charset=utf-8," + test_html)
        
        # Load the advanced editor script
        with open('static/js/advanced-editor/simple-editor.js', 'r', encoding='utf-8') as f:
            editor_script = f.read()
        
        driver.execute_script(editor_script)
        
        yield driver
        driver.quit()

    @given(
        initial_content=st.text(min_size=10, max_size=500),
        markdown_content=st.text(min_size=10, max_size=300)
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_dual_mode_content_preservation(self, test_page, initial_content, markdown_content):
        """
        Feature: advanced-editor-system, Property 3: Dual-Mode Round-Trip Preservation

        Round-trip conversion (WYSIWYG → Markdown → WYSIWYG) should preserve 
        essential content structure and formatting.
        """
        browser = test_page

        # Initialize editor
        browser.execute_script("""
            window.testEditor = new window.AdvancedEditor({
                container: '#test-container',
                content: arguments[0],
                showToolbar: true,
                showSidebar: true
            });
            return window.testEditor.initialize();
        """, f"<p>{initial_content}</p>")

        # Wait for initialization
        WebDriverWait(browser, 10).until(
            lambda driver: driver.execute_script("return window.testEditor && window.testEditor.isReady()")
        )

        # Get initial content
        initial_state = browser.execute_script("""
            return {
                mode: window.testEditor.getCurrentMode(),
                content: window.testEditor.getContent()
            };
        """)

        assert initial_state['mode'] == 'visual', "Editor should start in visual mode"

        # Switch to markdown mode
        browser.execute_script("window.testEditor.toggleMarkdownMode();")

        # Verify mode switch
        markdown_state = browser.execute_script("""
            return {
                mode: window.testEditor.getCurrentMode(),
                content: window.testEditor.getContent()
            };
        """)

        assert markdown_state['mode'] == 'markdown', "Editor should be in markdown mode"
        assert 'markdown' in markdown_state['content'], "Content should include markdown"

        # Modify content in markdown mode
        browser.execute_script(f"""
            const editor = window.testEditor.editor;
            editor.textContent = {json.dumps(f"# Test Header\\n\\n{markdown_content}\\n\\n**Bold text**")};
            window.testEditor.handleInput();
        """)

        # Switch back to visual mode
        browser.execute_script("window.testEditor.switchToVisualMode();")

        # Verify round-trip preservation
        final_state = browser.execute_script("""
            return {
                mode: window.testEditor.getCurrentMode(),
                content: window.testEditor.getContent()
            };
        """)

        assert final_state['mode'] == 'visual', "Editor should be back in visual mode"
        
        # Check that content structure is preserved
        final_html = final_state['content']['html']
        assert '<h1>' in final_html, "Header should be preserved as HTML"
        assert '<strong>' in final_html or '<b>' in final_html, "Bold formatting should be preserved"

    @given(
        test_markdown=st.sampled_from([
            "# Heading 1\n\nParagraph text",
            "## Heading 2\n\n**Bold** and *italic* text",
            "### Heading 3\n\n- List item 1\n- List item 2",
            "> Blockquote text\n\nNormal paragraph",
            "`inline code` and ```\ncode block\n```",
            "[Link text](https://example.com)",
            "![Alt text](https://example.com/image.jpg)"
        ])
    )
    @settings(max_examples=7, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_markdown_to_html_conversion(self, test_page, test_markdown):
        """
        Feature: advanced-editor-system, Property 3: Dual-Mode Round-Trip Preservation

        Markdown to HTML conversion should produce valid HTML with correct formatting.
        """
        browser = test_page

        # Initialize editor in markdown mode
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

        # Switch to markdown mode and set content
        browser.execute_script(f"""
            window.testEditor.switchToMarkdownMode();
            window.testEditor.editor.textContent = {json.dumps(test_markdown)};
            window.testEditor.handleInput();
        """)

        # Switch to visual mode to trigger conversion
        browser.execute_script("window.testEditor.switchToVisualMode();")

        # Get converted content
        result = browser.execute_script("""
            return {
                html: window.testEditor.getContent().html,
                mode: window.testEditor.getCurrentMode()
            };
        """)

        assert result['mode'] == 'visual', "Should be in visual mode"
        
        html_content = result['html']
        
        # Verify conversion based on markdown content
        if test_markdown.startswith('# '):
            assert '<h1>' in html_content, "H1 should be converted"
        elif test_markdown.startswith('## '):
            assert '<h2>' in html_content, "H2 should be converted"
        elif test_markdown.startswith('### '):
            assert '<h3>' in html_content, "H3 should be converted"
        
        if '**' in test_markdown:
            assert '<strong>' in html_content or '<b>' in html_content, "Bold should be converted"
        
        if '*' in test_markdown and '**' not in test_markdown:
            assert '<em>' in html_content or '<i>' in html_content, "Italic should be converted"
        
        if test_markdown.startswith('> '):
            assert '<blockquote>' in html_content, "Blockquote should be converted"
        
        if '- ' in test_markdown:
            assert '<li>' in html_content, "List items should be converted"
        
        if '`' in test_markdown:
            assert '<code>' in html_content, "Code should be converted"
        
        if '[' in test_markdown and '](' in test_markdown and not test_markdown.startswith('!['):
            assert '<a href=' in html_content, "Links should be converted"
        
        if '![' in test_markdown:
            assert '<img' in html_content, "Images should be converted"

    def test_mode_switching_keyboard_shortcut(self, test_page):
        """
        Feature: advanced-editor-system, Property 3: Dual-Mode Round-Trip Preservation

        Keyboard shortcut (Alt+M) should toggle between visual and markdown modes.
        """
        browser = test_page

        # Initialize editor
        browser.execute_script("""
            window.testEditor = new window.AdvancedEditor({
                container: '#test-container',
                content: '<p>Test content</p>',
                showToolbar: true,
                showSidebar: true
            });
            return window.testEditor.initialize();
        """)

        # Wait for initialization
        WebDriverWait(browser, 10).until(
            lambda driver: driver.execute_script("return window.testEditor && window.testEditor.isReady()")
        )

        # Verify initial mode
        initial_mode = browser.execute_script("return window.testEditor.getCurrentMode();")
        assert initial_mode == 'visual', "Should start in visual mode"

        # Simulate Alt+M keyboard shortcut
        browser.execute_script("""
            const editor = window.testEditor.editor;
            const event = new KeyboardEvent('keydown', {
                key: 'm',
                altKey: true,
                bubbles: true
            });
            editor.dispatchEvent(event);
        """)

        # Verify mode switched
        new_mode = browser.execute_script("return window.testEditor.getCurrentMode();")
        assert new_mode == 'markdown', "Should switch to markdown mode with Alt+M"

        # Switch back
        browser.execute_script("""
            const editor = window.testEditor.editor;
            const event = new KeyboardEvent('keydown', {
                key: 'm',
                altKey: true,
                bubbles: true
            });
            editor.dispatchEvent(event);
        """)

        # Verify mode switched back
        final_mode = browser.execute_script("return window.testEditor.getCurrentMode();")
        assert final_mode == 'visual', "Should switch back to visual mode"

    def test_toolbar_state_updates_with_mode(self, test_page):
        """
        Feature: advanced-editor-system, Property 3: Dual-Mode Round-Trip Preservation

        Toolbar buttons should be appropriately enabled/disabled based on current mode.
        """
        browser = test_page

        # Initialize editor
        browser.execute_script("""
            window.testEditor = new window.AdvancedEditor({
                container: '#test-container',
                content: '<p>Test content</p>',
                showToolbar: true,
                showSidebar: true
            });
            return window.testEditor.initialize();
        """)

        # Wait for initialization
        WebDriverWait(browser, 10).until(
            lambda driver: driver.execute_script("return window.testEditor && window.testEditor.isReady()")
        )

        # Check initial toolbar state (visual mode)
        visual_toolbar_state = browser.execute_script("""
            const toolbar = window.testEditor.toolbar;
            const boldBtn = toolbar.querySelector('[data-command="bold"]');
            const markdownBtn = toolbar.querySelector('[data-command="toggleMarkdown"]');
            
            return {
                boldDisabled: boldBtn ? boldBtn.disabled : null,
                markdownActive: markdownBtn ? markdownBtn.classList.contains('active') : null
            };
        """)

        assert not visual_toolbar_state['boldDisabled'], "Bold button should be enabled in visual mode"
        assert not visual_toolbar_state['markdownActive'], "Markdown button should not be active in visual mode"

        # Switch to markdown mode
        browser.execute_script("window.testEditor.toggleMarkdownMode();")

        # Check toolbar state in markdown mode
        markdown_toolbar_state = browser.execute_script("""
            const toolbar = window.testEditor.toolbar;
            const boldBtn = toolbar.querySelector('[data-command="bold"]');
            const markdownBtn = toolbar.querySelector('[data-command="toggleMarkdown"]');
            
            return {
                boldDisabled: boldBtn ? boldBtn.disabled : null,
                markdownActive: markdownBtn ? markdownBtn.classList.contains('active') : null
            };
        """)

        assert markdown_toolbar_state['boldDisabled'], "Bold button should be disabled in markdown mode"
        assert markdown_toolbar_state['markdownActive'], "Markdown button should be active in markdown mode"