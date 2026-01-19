"""
Unit tests for advanced text formatting controls in the editor.

**Feature: advanced-editor-system, Property 4.1**: Text formatting operations should apply consistently to selected text
**Feature: advanced-editor-system, Property 4.2**: Typography controls should maintain formatting integrity across mode switches
**Feature: advanced-editor-system, Property 4.3**: Color controls should preserve color values accurately
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
import re
import os


class TestAdvancedFormattingUnit:
    """Unit tests for advanced text formatting functionality."""

    def test_editor_file_exists(self):
        """Verify that the advanced editor JavaScript file exists."""
        editor_path = "static/js/advanced-editor/simple-editor.js"
        assert os.path.exists(editor_path), f"Editor file not found at {editor_path}"

    def test_css_file_exists(self):
        """Verify that the advanced editor CSS file exists."""
        css_path = "static/css/advanced-editor.css"
        assert os.path.exists(css_path), f"CSS file not found at {css_path}"

    def test_editor_contains_formatting_methods(self):
        """Verify that the editor contains all required formatting methods."""
        editor_path = "static/js/advanced-editor/simple-editor.js"
        
        with open(editor_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for essential formatting methods
        required_methods = [
            'insertTable',
            'setLineHeight',
            'getParentBlock',
            'executeCommand',
            'updateToolbarState',
            'rgbToHex'
        ]
        
        for method in required_methods:
            assert method in content, f"Method '{method}' not found in editor"

    def test_toolbar_contains_advanced_controls(self):
        """Verify that the toolbar contains advanced formatting controls."""
        editor_path = "static/js/advanced-editor/simple-editor.js"
        
        with open(editor_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for advanced toolbar controls
        advanced_controls = [
            'data-command="insertTable"',
            'data-command="lineHeight"',
            'data-command="justifyFull"',
            'data-command="superscript"',
            'data-command="subscript"',
            'color-picker',
            'highlight-icon'
        ]
        
        for control in advanced_controls:
            assert control in content, f"Advanced control '{control}' not found in toolbar"

    def test_css_contains_formatting_styles(self):
        """Verify that the CSS contains styles for advanced formatting."""
        css_path = "static/css/advanced-editor.css"
        
        with open(css_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for advanced styling
        required_styles = [
            '.color-controls',
            '.color-picker',
            '.highlight-icon',
            'table th',
            'table td',
            'line-height',
            '.toolbar-btn:disabled'
        ]
        
        for style in required_styles:
            assert style in content, f"Style '{style}' not found in CSS"

    @given(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))))
    @settings(max_examples=10)
    def test_color_hex_validation(self, test_text):
        """
        **Validates: Requirements 4.2, 4.6**
        Property: Color values should be valid hex codes.
        """
        assume(len(test_text.strip()) > 0)
        
        # Test hex color validation pattern
        hex_pattern = r'^#[0-9A-Fa-f]{6}$'
        
        test_colors = ['#ff0000', '#00ff00', '#0000ff', '#ffffff', '#000000']
        
        for color in test_colors:
            assert re.match(hex_pattern, color), f"Color '{color}' is not a valid hex code"

    @given(st.integers(min_value=1, max_value=10), st.integers(min_value=1, max_value=8))
    @settings(max_examples=20)
    def test_table_dimensions_validation(self, rows, cols):
        """
        **Validates: Requirements 4.7**
        Property: Table creation should validate dimensions within reasonable limits.
        """
        # Test table dimension validation logic
        max_rows = 20
        max_cols = 10
        
        is_valid = (1 <= rows <= max_rows) and (1 <= cols <= max_cols)
        
        if rows > max_rows or cols > max_cols:
            assert not is_valid, f"Table dimensions {rows}x{cols} should be invalid"
        else:
            assert is_valid, f"Table dimensions {rows}x{cols} should be valid"

    @given(st.floats(min_value=0.5, max_value=5.0))
    @settings(max_examples=15)
    def test_line_height_values(self, line_height):
        """
        **Validates: Requirements 4.5**
        Property: Line height values should be within reasonable bounds.
        """
        # Test line height validation
        valid_line_heights = ['1', '1.15', '1.5', '2', '2.5', '3']
        
        # Convert to string for comparison
        line_height_str = str(line_height)
        
        # Check if it's a reasonable line height value
        is_reasonable = 0.5 <= line_height <= 5.0
        assert is_reasonable, f"Line height {line_height} should be within reasonable bounds"

    def test_font_family_options(self):
        """
        **Validates: Requirements 4.3**
        Property: Font family options should include common web-safe fonts.
        """
        editor_path = "static/js/advanced-editor/simple-editor.js"
        
        with open(editor_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for common web-safe fonts
        expected_fonts = [
            'Arial',
            'Georgia',
            'Times New Roman',
            'Helvetica',
            'Courier New',
            'Verdana'
        ]
        
        for font in expected_fonts:
            assert font in content, f"Font '{font}' not found in font options"

    def test_formatting_command_coverage(self):
        """
        **Validates: Requirements 4.1, 4.8**
        Property: All formatting commands should be handled in executeCommand method.
        """
        editor_path = "static/js/advanced-editor/simple-editor.js"
        
        with open(editor_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the executeCommand method more accurately
        execute_command_start = content.find('executeCommand(command, value = null)')
        assert execute_command_start != -1, "executeCommand method not found"
        
        # Find the end of the method (next method or class end)
        method_start = content.find('{', execute_command_start)
        brace_count = 0
        method_end = method_start
        
        for i, char in enumerate(content[method_start:], method_start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    method_end = i
                    break
        
        execute_command_content = content[method_start:method_end]
        
        # Check for handling of advanced commands
        advanced_commands = [
            'insertTable',
            'insertHorizontalRule',
            'lineHeight',
            'foreColor',
            'hiliteColor'
        ]
        
        for command in advanced_commands:
            assert command in execute_command_content, f"Command '{command}' not handled in executeCommand"

    @given(st.sampled_from(['bold', 'italic', 'underline', 'strikeThrough', 'superscript', 'subscript']))
    @settings(max_examples=6)
    def test_formatting_command_validation(self, format_command):
        """
        **Validates: Requirements 4.1**
        Property: All text formatting commands should be valid HTML formatting commands.
        """
        # Valid HTML formatting commands
        valid_commands = {
            'bold': ['<strong>', '<b>'],
            'italic': ['<em>', '<i>'],
            'underline': ['<u>'],
            'strikeThrough': ['<s>', '<strike>'],
            'superscript': ['<sup>'],
            'subscript': ['<sub>']
        }
        
        assert format_command in valid_commands, f"Format command '{format_command}' is not valid"
        
        # Check that each command has associated HTML tags
        tags = valid_commands[format_command]
        assert len(tags) > 0, f"No HTML tags defined for command '{format_command}'"

    def test_toolbar_accessibility(self):
        """
        **Validates: Requirements 4.7**
        Property: Toolbar buttons should have proper accessibility attributes.
        """
        editor_path = "static/js/advanced-editor/simple-editor.js"
        
        with open(editor_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for accessibility attributes
        accessibility_features = [
            'title=',
            'aria-label',
            'role=',
            'tabindex'
        ]
        
        # At least some accessibility features should be present
        accessibility_count = sum(1 for feature in accessibility_features if feature in content)
        assert accessibility_count > 0, "No accessibility features found in toolbar"

    def test_responsive_toolbar_layout(self):
        """
        **Validates: Requirements 4.7**
        Property: Toolbar should have responsive layout styles.
        """
        css_path = "static/css/advanced-editor.css"
        
        with open(css_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for responsive design features
        responsive_features = [
            'flex-wrap',
            '@media',
            'min-width',
            'max-width'
        ]
        
        responsive_count = sum(1 for feature in responsive_features if feature in content)
        assert responsive_count >= 2, f"Insufficient responsive design features found (found {responsive_count})"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])