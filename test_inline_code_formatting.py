"""
Property-Based Tests for Inline Code Formatting

**Feature: advanced-editor-system, Property 10: Inline Code Formatting**

For any text marked as inline code, it should display with monospace font and 
background highlighting while maintaining readability.

**Validates: Requirement 5.4**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


# Strategy for generating inline code content
@st.composite
def inline_code_strategy(draw):
    """Generate realistic inline code snippets"""
    code_type = draw(st.sampled_from([
        'variable', 'function', 'class', 'keyword', 'operator', 'mixed'
    ]))
    
    if code_type == 'variable':
        # Use ASCII-safe characters only
        return draw(st.text(
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_',
            min_size=1,
            max_size=30
        ))
    elif code_type == 'function':
        name = draw(st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz_',
            min_size=3,
            max_size=20
        ))
        return f"{name}()"
    elif code_type == 'class':
        name = draw(st.text(
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_',
            min_size=3,
            max_size=20
        ))
        return name
    elif code_type == 'keyword':
        return draw(st.sampled_from([
            'const', 'let', 'var', 'function', 'class', 'return', 'if', 'else',
            'for', 'while', 'import', 'export', 'async', 'await', 'try', 'catch'
        ]))
    elif code_type == 'operator':
        return draw(st.sampled_from([
            '===', '!==', '==', '!=', '<=', '>=', '<', '>', '&&', '||', '??'
        ]))
    else:  # mixed
        return draw(st.text(
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789(){}[]<>=+-*/.,:;_',
            min_size=1,
            max_size=50
        ))


@pytest.fixture(scope='module')
def driver():
    """Create a Selenium WebDriver instance"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_window_size(1920, 1080)
    
    yield driver
    
    driver.quit()


@pytest.fixture(scope='module')
def test_page(driver):
    """Create a test page with code editor"""
    # Read the code-editor.js file
    import os
    code_editor_path = os.path.join('static', 'js', 'advanced-editor', 'code-editor.js')
    
    with open(code_editor_path, 'r', encoding='utf-8') as f:
        code_editor_js = f.read()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Inline Code Test</title>
        <style>
            body {{ 
                margin: 20px; 
                font-family: Arial, sans-serif;
                font-size: 16px;
                line-height: 1.6;
            }}
            #test-container {{ 
                margin: 20px 0;
                padding: 20px;
                background: #f5f5f5;
            }}
            
            /* Inline code styles from advanced-editor.css */
            .inline-code {{
                padding: 0.125rem 0.375rem;
                border-radius: 3px;
                background: rgba(217, 119, 6, 0.1);
                color: #d97706;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 0.875em;
                font-weight: 500;
                white-space: nowrap;
            }}
        </style>
    </head>
    <body>
        <div id="test-container"></div>
        
        <script>
        {code_editor_js}
        </script>
        
        <script>
            window.testReady = true;
        </script>
    </body>
    </html>
    """
    
    # Save to temporary file and load
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html_content)
        temp_file = f.name
    
    try:
        driver.get(f'file://{os.path.abspath(temp_file)}')
        
        # Wait for page to be ready
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script('return window.testReady === true')
        )
        
        yield driver
    finally:
        os.unlink(temp_file)


class TestInlineCodeFormatting:
    """
    Property-Based Tests for Inline Code Formatting
    
    **Feature: advanced-editor-system, Property 10: Inline Code Formatting**
    """
    
    @settings(max_examples=100, deadline=5000)
    @given(code=inline_code_strategy())
    def test_inline_code_creation(self, test_page, code):
        """
        Property: Any text marked as inline code should be rendered with proper styling.
        
        **Validates: Requirement 5.4**
        """
        assume(code.strip() != '')
        
        driver = test_page
        
        script = f"""
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const inlineCode = window.codeEditor.createInlineCode({repr(code)});
        container.appendChild(inlineCode);
        
        return {{
            hasElement: !!inlineCode,
            tagName: inlineCode.tagName,
            className: inlineCode.className,
            textContent: inlineCode.textContent,
            hasInlineCodeClass: inlineCode.classList.contains('inline-code')
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasElement'], "Inline code element should be created"
        assert result['tagName'] == 'CODE', "Inline code should use <code> tag"
        assert result['hasInlineCodeClass'], "Inline code should have 'inline-code' class"
        assert result['textContent'] == code, "Inline code content should be preserved"
    
    @settings(max_examples=100, deadline=5000)
    @given(code=inline_code_strategy())
    def test_inline_code_monospace_font(self, test_page, code):
        """
        Property: Inline code should display with monospace font.
        
        **Validates: Requirement 5.4**
        """
        assume(code.strip() != '')
        
        driver = test_page
        
        script = f"""
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const inlineCode = window.codeEditor.createInlineCode({repr(code)});
        container.appendChild(inlineCode);
        
        const computedStyle = window.getComputedStyle(inlineCode);
        const fontFamily = computedStyle.fontFamily.toLowerCase();
        
        return {{
            fontFamily: fontFamily,
            hasMonospace: fontFamily.includes('consolas') || 
                         fontFamily.includes('monaco') || 
                         fontFamily.includes('courier') ||
                         fontFamily.includes('monospace')
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasMonospace'], \
            f"Inline code should use monospace font, got: {result['fontFamily']}"
    
    @settings(max_examples=100, deadline=5000)
    @given(code=inline_code_strategy())
    def test_inline_code_background_highlighting(self, test_page, code):
        """
        Property: Inline code should have background highlighting for visibility.
        
        **Validates: Requirement 5.4**
        """
        assume(code.strip() != '')
        
        driver = test_page
        
        script = f"""
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const inlineCode = window.codeEditor.createInlineCode({repr(code)});
        container.appendChild(inlineCode);
        
        const computedStyle = window.getComputedStyle(inlineCode);
        const backgroundColor = computedStyle.backgroundColor;
        const color = computedStyle.color;
        
        // Parse RGB values
        const bgMatch = backgroundColor.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
        const colorMatch = color.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
        
        return {{
            backgroundColor: backgroundColor,
            color: color,
            hasBackground: bgMatch && (
                parseInt(bgMatch[1]) > 0 || 
                parseInt(bgMatch[2]) > 0 || 
                parseInt(bgMatch[3]) > 0
            ),
            hasColor: colorMatch && (
                parseInt(colorMatch[1]) > 0 || 
                parseInt(colorMatch[2]) > 0 || 
                parseInt(colorMatch[3]) > 0
            )
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasBackground'], \
            f"Inline code should have background color, got: {result['backgroundColor']}"
        assert result['hasColor'], \
            f"Inline code should have text color, got: {result['color']}"
    
    @settings(max_examples=100, deadline=5000)
    @given(code=inline_code_strategy())
    def test_inline_code_readability(self, test_page, code):
        """
        Property: Inline code should maintain readability with proper sizing and spacing.
        
        **Validates: Requirement 5.4**
        """
        assume(code.strip() != '')
        
        driver = test_page
        
        script = f"""
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const inlineCode = window.codeEditor.createInlineCode({repr(code)});
        container.appendChild(inlineCode);
        
        const computedStyle = window.getComputedStyle(inlineCode);
        const fontSize = parseFloat(computedStyle.fontSize);
        const padding = computedStyle.padding;
        const borderRadius = computedStyle.borderRadius;
        
        return {{
            fontSize: fontSize,
            padding: padding,
            borderRadius: borderRadius,
            hasPadding: padding !== '0px',
            hasBorderRadius: borderRadius !== '0px'
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['fontSize'] > 0, "Inline code should have readable font size"
        assert result['hasPadding'], "Inline code should have padding for readability"
        assert result['hasBorderRadius'], "Inline code should have border radius for visual appeal"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        code=inline_code_strategy(),
        surrounding_text=st.text(min_size=10, max_size=100)
    )
    def test_inline_code_in_context(self, test_page, code, surrounding_text):
        """
        Property: Inline code should integrate well within surrounding text.
        
        **Validates: Requirement 5.4**
        """
        assume(code.strip() != '')
        assume(surrounding_text.strip() != '')
        
        driver = test_page
        
        script = f"""
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const paragraph = document.createElement('p');
        paragraph.textContent = {repr(surrounding_text)} + ' ';
        
        const inlineCode = window.codeEditor.createInlineCode({repr(code)});
        paragraph.appendChild(inlineCode);
        
        paragraph.appendChild(document.createTextNode(' ' + {repr(surrounding_text)}));
        
        container.appendChild(paragraph);
        
        const pStyle = window.getComputedStyle(paragraph);
        const codeStyle = window.getComputedStyle(inlineCode);
        
        const pLineHeight = parseFloat(pStyle.lineHeight);
        const codeHeight = inlineCode.offsetHeight;
        
        return {{
            paragraphLineHeight: pLineHeight,
            codeHeight: codeHeight,
            fitsInLine: codeHeight <= pLineHeight * 1.5,
            hasWhitespace: codeStyle.whiteSpace === 'nowrap'
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['fitsInLine'], \
            "Inline code should fit within line height of surrounding text"
        assert result['hasWhitespace'], \
            "Inline code should use nowrap to prevent breaking"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        codes=st.lists(inline_code_strategy(), min_size=2, max_size=5)
    )
    def test_multiple_inline_codes(self, test_page, codes):
        """
        Property: Multiple inline code elements should maintain consistent styling.
        
        **Validates: Requirement 5.4**
        """
        assume(all(code.strip() != '' for code in codes))
        
        driver = test_page
        
        script = f"""
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const codes = {repr(codes)};
        const elements = [];
        
        codes.forEach((code, index) => {{
            if (index > 0) {{
                container.appendChild(document.createTextNode(' and '));
            }}
            const inlineCode = window.codeEditor.createInlineCode(code);
            container.appendChild(inlineCode);
            elements.push(inlineCode);
        }});
        
        // Check consistency
        const styles = elements.map(el => {{
            const style = window.getComputedStyle(el);
            return {{
                fontFamily: style.fontFamily,
                fontSize: style.fontSize,
                backgroundColor: style.backgroundColor,
                color: style.color,
                padding: style.padding,
                borderRadius: style.borderRadius
            }};
        }});
        
        const firstStyle = styles[0];
        const allConsistent = styles.every(style => 
            style.fontFamily === firstStyle.fontFamily &&
            style.fontSize === firstStyle.fontSize &&
            style.backgroundColor === firstStyle.backgroundColor &&
            style.color === firstStyle.color &&
            style.padding === firstStyle.padding &&
            style.borderRadius === firstStyle.borderRadius
        );
        
        return {{
            elementCount: elements.length,
            allConsistent: allConsistent,
            styles: styles
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['elementCount'] == len(codes), \
            "All inline code elements should be created"
        assert result['allConsistent'], \
            "All inline code elements should have consistent styling"


class TestInlineCodeEdgeCases:
    """Edge case tests for inline code formatting"""
    
    def test_empty_inline_code(self, test_page):
        """Test inline code with empty content"""
        driver = test_page
        
        script = """
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const inlineCode = window.codeEditor.createInlineCode('');
        container.appendChild(inlineCode);
        
        return {
            hasElement: !!inlineCode,
            textContent: inlineCode.textContent,
            isEmpty: inlineCode.textContent === ''
        };
        """
        
        result = driver.execute_script(script)
        
        assert result['hasElement'], "Empty inline code should still be created"
        assert result['isEmpty'], "Empty inline code should render as empty"
    
    def test_inline_code_with_special_characters(self, test_page):
        """Test inline code with special HTML characters"""
        driver = test_page
        
        special_code = '<>&"\''
        
        script = f"""
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const specialCode = {repr(special_code)};
        const inlineCode = window.codeEditor.createInlineCode(specialCode);
        container.appendChild(inlineCode);
        
        return {{
            hasElement: !!inlineCode,
            textContent: inlineCode.textContent,
            contentPreserved: inlineCode.textContent === specialCode,
            noXSS: container.innerHTML.includes('&lt;') || 
                   inlineCode.textContent === specialCode
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasElement'], "Inline code with special chars should be created"
        assert result['contentPreserved'], "Special characters should be preserved"
        assert result['noXSS'], "Special characters should be properly escaped"
    
    def test_very_long_inline_code(self, test_page):
        """Test inline code with very long content"""
        driver = test_page
        
        long_code = 'a' * 200
        
        script = f"""
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const longCode = {repr(long_code)};
        const inlineCode = window.codeEditor.createInlineCode(longCode);
        container.appendChild(inlineCode);
        
        const computedStyle = window.getComputedStyle(inlineCode);
        
        return {{
            hasElement: !!inlineCode,
            length: inlineCode.textContent.length,
            contentPreserved: inlineCode.textContent === longCode,
            whiteSpace: computedStyle.whiteSpace
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasElement'], "Long inline code should be created"
        assert result['length'] == 200, "Long content should be preserved"
        assert result['contentPreserved'], "Long content should match exactly"
        assert result['whiteSpace'] == 'nowrap', "Long inline code should not wrap"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
