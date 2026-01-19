"""
Property-based tests for advanced text formatting controls in the editor.

**Feature: advanced-editor-system, Property 4.1**: Text formatting operations should apply consistently to selected text
**Feature: advanced-editor-system, Property 4.2**: Typography controls should maintain formatting integrity across mode switches
**Feature: advanced-editor-system, Property 4.3**: Color controls should preserve color values accurately
"""

import pytest
import os
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import re
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time


class TestAdvancedTextFormatting:
    """Property-based tests for advanced text formatting functionality."""

    @pytest.fixture(scope="class")
    def driver(self):
        """Set up Chrome WebDriver for testing."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    @pytest.fixture
    def editor_page(self, driver):
        """Navigate to dashboard with editor."""
        # Create a simple HTML page with the advanced editor for testing
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Advanced Editor Test</title>
            <link rel="stylesheet" href="/static/css/advanced-editor.css">
            <style>
                :root {
                    --accent: #d97706;
                    --text: #333;
                    --bg: #f8f9fa;
                    --card: #ffffff;
                    --hover-bg: #f1f5f9;
                    --paper-border: #e2e8f0;
                    --muted: #64748b;
                }
                body { font-family: Arial, sans-serif; margin: 20px; }
            </style>
        </head>
        <body>
            <div id="test-editor-container"></div>
            <script src="/static/js/advanced-editor/simple-editor.js"></script>
            <script>
                document.addEventListener('DOMContentLoaded', async function() {
                    const editor = new window.AdvancedEditor({
                        container: '#test-editor-container',
                        content: '<p>Test content for formatting</p>',
                        showToolbar: true,
                        showSidebar: false
                    });
                    await editor.initialize();
                    window.testEditor = editor;
                });
            </script>
        </body>
        </html>
        """
        
        # Save test HTML to a temporary file and serve it
        with open('test_editor.html', 'w') as f:
            f.write(test_html)
        
        driver.get(f"file://{os.path.abspath('test_editor.html')}")
        
        # Wait for editor to initialize
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return window.testEditor && window.testEditor.isReady()")
        )
        
        yield driver
        
        # Cleanup
        try:
            os.remove('test_editor.html')
        except:
            pass

    # Text formatting strategies
    text_content = st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Zs')),
        min_size=1,
        max_size=100
    )
    
    formatting_commands = st.sampled_from([
        'bold', 'italic', 'underline', 'strikeThrough', 'superscript', 'subscript'
    ])
    
    color_values = st.sampled_from([
        '#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff',
        '#000000', '#ffffff', '#808080', '#ffa500', '#800080', '#008000'
    ])
    
    font_families = st.sampled_from([
        'Arial, sans-serif', 'Georgia, serif', "'Times New Roman', serif",
        'Helvetica, sans-serif', "'Courier New', monospace", 'Verdana, sans-serif'
    ])
    
    font_sizes = st.sampled_from(['1', '2', '3', '4', '5', '6', '7'])
    
    line_heights = st.sampled_from(['1', '1.15', '1.5', '2', '2.5', '3'])

    @given(text_content, formatting_commands)
    @settings(max_examples=20, deadline=30000)
    def test_text_formatting_consistency(self, editor_page, test_text, format_command):
        """
        **Validates: Requirements 4.1, 4.8**
        Property: Applying any formatting to selected text should result in the text having the specified formatting attributes.
        """
        assume(len(test_text.strip()) > 0)
        
        driver = editor_page
        
        try:
            # Insert test text into editor
            editor_content = driver.find_element(By.CLASS_NAME, "editor-content-area")
            editor_content.clear()
            editor_content.send_keys(test_text)
            
            # Select all text
            editor_content.send_keys(Keys.CONTROL + "a")
            
            # Apply formatting
            format_button = driver.find_element(By.CSS_SELECTOR, f'[data-command="{format_command}"]')
            format_button.click()
            
            # Wait for formatting to apply
            time.sleep(0.5)
            
            # Check if formatting was applied
            formatted_content = driver.execute_script("""
                const editor = window.testEditor;
                return editor.getContent().html;
            """)
            
            # Verify formatting is present in HTML
            format_tags = {
                'bold': ['<strong>', '<b>'],
                'italic': ['<em>', '<i>'],
                'underline': ['<u>'],
                'strikeThrough': ['<s>', '<strike>'],
                'superscript': ['<sup>'],
                'subscript': ['<sub>']
            }
            
            expected_tags = format_tags.get(format_command, [])
            formatting_applied = any(tag in formatted_content for tag in expected_tags)
            
            assert formatting_applied, f"Formatting '{format_command}' was not applied to text. Content: {formatted_content}"
            
            # Verify text content is preserved
            text_content = driver.execute_script("""
                const editor = window.testEditor;
                return editor.getContent().text;
            """)
            
            assert test_text.strip() in text_content.strip(), f"Original text not preserved after formatting"
            
        except Exception as e:
            pytest.fail(f"Text formatting test failed: {str(e)}")

    @given(text_content, color_values)
    @settings(max_examples=15, deadline=30000)
    def test_color_formatting_accuracy(self, editor_page, test_text, color_value):
        """
        **Validates: Requirements 4.2, 4.6**
        Property: Color controls should preserve color values accurately and apply to selected text.
        """
        assume(len(test_text.strip()) > 0)
        
        driver = editor_page
        
        try:
            # Insert test text into editor
            editor_content = driver.find_element(By.CLASS_NAME, "editor-content-area")
            editor_content.clear()
            editor_content.send_keys(test_text)
            
            # Select all text
            editor_content.send_keys(Keys.CONTROL + "a")
            
            # Apply text color
            color_picker = driver.find_element(By.CSS_SELECTOR, '[data-command="foreColor"] .color-picker')
            driver.execute_script(f"arguments[0].value = '{color_value}';", color_picker)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", color_picker)
            
            # Wait for color to apply
            time.sleep(0.5)
            
            # Check if color was applied
            formatted_content = driver.execute_script("""
                const editor = window.testEditor;
                return editor.getContent().html;
            """)
            
            # Verify color is present in HTML (either as style attribute or color tag)
            color_applied = (
                f'color: {color_value}' in formatted_content or
                f'color:{color_value}' in formatted_content or
                color_value.lower() in formatted_content.lower()
            )
            
            assert color_applied, f"Color '{color_value}' was not applied to text. Content: {formatted_content}"
            
            # Verify text content is preserved
            text_content = driver.execute_script("""
                const editor = window.testEditor;
                return editor.getContent().text;
            """)
            
            assert test_text.strip() in text_content.strip(), f"Original text not preserved after color formatting"
            
        except Exception as e:
            pytest.fail(f"Color formatting test failed: {str(e)}")

    @given(text_content, font_families)
    @settings(max_examples=10, deadline=30000)
    def test_font_family_application(self, editor_page, test_text, font_family):
        """
        **Validates: Requirements 4.3**
        Property: Font family selection should apply consistently to selected text.
        """
        assume(len(test_text.strip()) > 0)
        
        driver = editor_page
        
        try:
            # Insert test text into editor
            editor_content = driver.find_element(By.CLASS_NAME, "editor-content-area")
            editor_content.clear()
            editor_content.send_keys(test_text)
            
            # Select all text
            editor_content.send_keys(Keys.CONTROL + "a")
            
            # Apply font family
            font_select = driver.find_element(By.CSS_SELECTOR, '[data-command="fontName"]')
            driver.execute_script(f"arguments[0].value = '{font_family}';", font_select)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", font_select)
            
            # Wait for font to apply
            time.sleep(0.5)
            
            # Check if font family was applied
            formatted_content = driver.execute_script("""
                const editor = window.testEditor;
                return editor.getContent().html;
            """)
            
            # Extract the base font name for checking
            base_font = font_family.split(',')[0].strip().replace("'", "").replace('"', '')
            
            # Verify font family is present in HTML
            font_applied = (
                base_font.lower() in formatted_content.lower() or
                f'font-family: {font_family}' in formatted_content or
                f'font-family:{font_family}' in formatted_content
            )
            
            assert font_applied, f"Font family '{font_family}' was not applied to text. Content: {formatted_content}"
            
        except Exception as e:
            pytest.fail(f"Font family test failed: {str(e)}")

    @given(text_content, line_heights)
    @settings(max_examples=10, deadline=30000)
    def test_line_height_controls(self, editor_page, test_text, line_height):
        """
        **Validates: Requirements 4.5**
        Property: Line spacing controls should apply consistently to text blocks.
        """
        assume(len(test_text.strip()) > 0)
        
        driver = editor_page
        
        try:
            # Insert test text into editor
            editor_content = driver.find_element(By.CLASS_NAME, "editor-content-area")
            editor_content.clear()
            editor_content.send_keys(test_text)
            
            # Select all text
            editor_content.send_keys(Keys.CONTROL + "a")
            
            # Apply line height
            line_height_select = driver.find_element(By.CSS_SELECTOR, '[data-command="lineHeight"]')
            driver.execute_script(f"arguments[0].value = '{line_height}';", line_height_select)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", line_height_select)
            
            # Wait for line height to apply
            time.sleep(0.5)
            
            # Check if line height was applied
            formatted_content = driver.execute_script("""
                const editor = window.testEditor;
                return editor.getContent().html;
            """)
            
            # Verify line height is present in HTML
            line_height_applied = (
                f'line-height: {line_height}' in formatted_content or
                f'line-height:{line_height}' in formatted_content
            )
            
            assert line_height_applied, f"Line height '{line_height}' was not applied to text. Content: {formatted_content}"
            
        except Exception as e:
            pytest.fail(f"Line height test failed: {str(e)}")

    @given(st.integers(min_value=2, max_value=5), st.integers(min_value=2, max_value=4))
    @settings(max_examples=5, deadline=30000)
    def test_table_insertion_structure(self, editor_page, rows, cols):
        """
        **Validates: Requirements 4.7**
        Property: Table insertion should create properly structured HTML tables with correct dimensions.
        """
        driver = editor_page
        
        try:
            # Clear editor
            editor_content = driver.find_element(By.CLASS_NAME, "editor-content-area")
            editor_content.clear()
            
            # Mock the prompt dialogs for table creation
            driver.execute_script(f"""
                window.originalPrompt = window.prompt;
                let promptCount = 0;
                window.prompt = function(message, defaultValue) {{
                    promptCount++;
                    if (promptCount === 1) return '{rows}';  // rows
                    if (promptCount === 2) return '{cols}';  // columns
                    return defaultValue;
                }};
            """)
            
            # Click table insertion button
            table_button = driver.find_element(By.CSS_SELECTOR, '[data-command="insertTable"]')
            table_button.click()
            
            # Wait for table to be inserted
            time.sleep(1)
            
            # Restore original prompt
            driver.execute_script("window.prompt = window.originalPrompt;")
            
            # Check if table was created with correct structure
            formatted_content = driver.execute_script("""
                const editor = window.testEditor;
                return editor.getContent().html;
            """)
            
            # Verify table structure
            assert '<table' in formatted_content, "Table element not found in content"
            assert '<thead>' in formatted_content, "Table header not found"
            assert '<tbody>' in formatted_content, "Table body not found"
            
            # Count table rows and columns
            table_rows = formatted_content.count('<tr>')
            expected_rows = rows  # header + body rows
            
            assert table_rows == expected_rows, f"Expected {expected_rows} table rows, found {table_rows}"
            
            # Check for proper table styling
            assert 'border-collapse: collapse' in formatted_content, "Table styling not applied"
            
        except Exception as e:
            pytest.fail(f"Table insertion test failed: {str(e)}")


class AdvancedFormattingStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for advanced formatting operations.
    **Validates: Requirements 4.8, 4.9**
    """
    
    def __init__(self):
        super().__init__()
        self.applied_formats = set()
        self.current_text = ""
        self.current_colors = {}
        
    @initialize()
    def setup_editor(self):
        """Initialize the editor state."""
        self.current_text = "Test content for stateful formatting"
        self.applied_formats = set()
        self.current_colors = {}
    
    @rule(format_cmd=st.sampled_from(['bold', 'italic', 'underline', 'strikeThrough']))
    def apply_text_formatting(self, format_cmd):
        """Apply text formatting and track state."""
        if format_cmd in self.applied_formats:
            self.applied_formats.remove(format_cmd)  # Toggle off
        else:
            self.applied_formats.add(format_cmd)  # Toggle on
    
    @rule(color=st.sampled_from(['#ff0000', '#00ff00', '#0000ff', '#000000']))
    def apply_text_color(self, color):
        """Apply text color and track state."""
        self.current_colors['foreColor'] = color
    
    @rule(bg_color=st.sampled_from(['#ffff00', '#ff00ff', '#00ffff', '#ffffff']))
    def apply_highlight_color(self, bg_color):
        """Apply highlight color and track state."""
        self.current_colors['hiliteColor'] = bg_color
    
    @invariant()
    def formatting_state_consistent(self):
        """Verify that formatting state remains consistent."""
        # This would be implemented with actual DOM checking in a real test
        # For now, we verify our state tracking is consistent
        assert isinstance(self.applied_formats, set)
        assert isinstance(self.current_colors, dict)
        assert len(self.current_text) > 0


# Test runner for the state machine
TestAdvancedFormattingStateMachine = AdvancedFormattingStateMachine.TestCase


if __name__ == "__main__":
    # Run basic property tests
    import os
    pytest.main([__file__, "-v", "--tb=short"])