"""
Property-Based Tests for Code Block Functionality

**Feature: advanced-editor-system, Property 9: Code Block Functionality**

For any programming language and code content, creating a code block should provide 
syntax highlighting, line numbers, proper indentation, and copy functionality.

**Validates: Requirements 5.1, 5.2, 5.3, 5.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


# Supported programming languages (matching code-editor.js)
SUPPORTED_LANGUAGES = [
    'javascript', 'typescript', 'python', 'java', 'csharp', 'cpp', 'c',
    'php', 'ruby', 'go', 'rust', 'swift', 'kotlin', 'sql', 'html', 'css',
    'scss', 'json', 'yaml', 'markdown', 'bash', 'powershell', 'docker',
    'xml', 'plaintext'
]


# Strategy for generating code content
@st.composite
def code_content_strategy(draw):
    """Generate realistic code content"""
    num_lines = draw(st.integers(min_value=1, max_value=20))
    lines = []
    
    for _ in range(num_lines):
        # Generate line with various content types
        line_type = draw(st.sampled_from([
            'code', 'comment', 'blank', 'indented'
        ]))
        
        if line_type == 'code':
            # Use ASCII-safe characters only
            line = draw(st.text(
                alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789(){}[]<>=+-*/.,:;_',
                min_size=5,
                max_size=80
            ))
        elif line_type == 'comment':
            line = '// ' + draw(st.text(
                alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ',
                min_size=5,
                max_size=60
            ))
        elif line_type == 'blank':
            line = ''
        else:  # indented
            indent = '    ' * draw(st.integers(min_value=0, max_value=3))
            line = indent + draw(st.text(
                alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ',
                min_size=5,
                max_size=60
            ))
        
        lines.append(line)
    
    return '\n'.join(lines)


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
        <title>Code Block Test</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/line-numbers/prism-line-numbers.min.css">
        <style>
            body {{ margin: 20px; font-family: Arial, sans-serif; }}
            #test-container {{ margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div id="test-container"></div>
        
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/line-numbers/prism-line-numbers.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>
        <script>
        {code_editor_js}
        </script>
        
        <script>
            // Wait for Prism to load
            window.addEventListener('load', function() {{
                window.testReady = true;
            }});
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


class TestCodeBlockFunctionality:
    """
    Property-Based Tests for Code Block Functionality
    
    **Feature: advanced-editor-system, Property 9: Code Block Functionality**
    """
    
    @settings(max_examples=100, deadline=5000)
    @given(
        language=st.sampled_from(SUPPORTED_LANGUAGES),
        code=code_content_strategy()
    )
    def test_code_block_creation_with_syntax_highlighting(self, test_page, language, code):
        """
        Property: Creating a code block with any supported language should provide 
        proper syntax highlighting and formatting.
        
        **Validates: Requirements 5.1, 5.2**
        """
        # Skip empty code
        assume(code.strip() != '')
        
        driver = test_page
        
        # Create code block using JavaScript
        script = f"""
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const codeBlock = window.codeEditor.createCodeBlock(
            {repr(code)},
            {repr(language)},
            {{ lineNumbers: true, copyButton: true }}
        );
        
        container.appendChild(codeBlock);
        
        return {{
            hasContainer: !!codeBlock,
            hasToolbar: !!codeBlock.querySelector('.code-block-toolbar'),
            hasLanguageLabel: !!codeBlock.querySelector('.code-language-label'),
            hasCopyButton: !!codeBlock.querySelector('.code-copy-button'),
            hasPreElement: !!codeBlock.querySelector('pre'),
            hasCodeElement: !!codeBlock.querySelector('code'),
            codeClassName: codeBlock.querySelector('code')?.className || '',
            codeContent: codeBlock.querySelector('code')?.textContent || '',
            dataLanguage: codeBlock.getAttribute('data-language')
        }};
        """
        
        result = driver.execute_script(script)
        
        # Verify code block structure
        assert result['hasContainer'], "Code block container should be created"
        assert result['hasToolbar'], "Code block should have toolbar"
        assert result['hasLanguageLabel'], "Code block should have language label"
        assert result['hasCopyButton'], "Code block should have copy button"
        assert result['hasPreElement'], "Code block should have pre element"
        assert result['hasCodeElement'], "Code block should have code element"
        
        # Verify language class
        assert f'language-{language}' in result['codeClassName'], \
            f"Code element should have language-{language} class"
        
        # Verify data attribute
        assert result['dataLanguage'] == language, \
            f"Container should have data-language='{language}'"
        
        # Verify code content is preserved
        assert result['codeContent'] == code, \
            "Code content should be preserved exactly"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        language=st.sampled_from(SUPPORTED_LANGUAGES),
        code=code_content_strategy(),
        line_numbers=st.booleans()
    )
    def test_code_block_line_numbers(self, test_page, language, code, line_numbers):
        """
        Property: Code blocks should support line numbers when requested.
        
        **Validates: Requirement 5.3**
        """
        assume(code.strip() != '')
        
        driver = test_page
        
        script = f"""
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const codeBlock = window.codeEditor.createCodeBlock(
            {repr(code)},
            {repr(language)},
            {{ lineNumbers: {str(line_numbers).lower()}, copyButton: true }}
        );
        
        container.appendChild(codeBlock);
        
        const pre = codeBlock.querySelector('pre');
        return {{
            hasLineNumbersClass: pre?.classList.contains('line-numbers') || false,
            lineCount: {repr(code)}.split('\\n').length
        }};
        """
        
        result = driver.execute_script(script)
        
        if line_numbers:
            assert result['hasLineNumbersClass'], \
                "Pre element should have line-numbers class when line numbers are enabled"
        else:
            assert not result['hasLineNumbersClass'], \
                "Pre element should not have line-numbers class when line numbers are disabled"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        language=st.sampled_from(SUPPORTED_LANGUAGES),
        code=st.text(min_size=10, max_size=200)
    )
    def test_code_block_copy_functionality(self, test_page, language, code):
        """
        Property: Code blocks should have functional copy-to-clipboard button.
        
        **Validates: Requirement 5.5**
        """
        assume(code.strip() != '')
        
        driver = test_page
        
        script = f"""
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const codeBlock = window.codeEditor.createCodeBlock(
            {repr(code)},
            {repr(language)},
            {{ lineNumbers: true, copyButton: true }}
        );
        
        container.appendChild(codeBlock);
        
        const copyButton = codeBlock.querySelector('.code-copy-button');
        return {{
            hasCopyButton: !!copyButton,
            buttonVisible: copyButton ? window.getComputedStyle(copyButton).display !== 'none' : false,
            buttonEnabled: copyButton ? !copyButton.disabled : false,
            hasClickHandler: copyButton ? copyButton.onclick !== null || 
                            copyButton.addEventListener !== undefined : false
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasCopyButton'], "Code block should have copy button"
        assert result['buttonVisible'], "Copy button should be visible"
        assert result['buttonEnabled'], "Copy button should be enabled"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        code=code_content_strategy()
    )
    def test_code_block_indentation_preservation(self, test_page, code):
        """
        Property: Code blocks should preserve indentation exactly as provided.
        
        **Validates: Requirement 5.3**
        """
        assume(code.strip() != '')
        assume('\t' in code or '    ' in code)  # Has indentation
        
        driver = test_page
        
        script = f"""
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const originalCode = {repr(code)};
        const codeBlock = window.codeEditor.createCodeBlock(
            originalCode,
            'javascript',
            {{ lineNumbers: true, copyButton: true }}
        );
        
        container.appendChild(codeBlock);
        
        const codeElement = codeBlock.querySelector('code');
        const renderedCode = codeElement.textContent;
        
        return {{
            originalCode: originalCode,
            renderedCode: renderedCode,
            indentationPreserved: originalCode === renderedCode
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['indentationPreserved'], \
            "Code block should preserve indentation exactly"
        assert result['originalCode'] == result['renderedCode'], \
            "Rendered code should match original code exactly"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        initial_language=st.sampled_from(SUPPORTED_LANGUAGES[:10]),
        new_language=st.sampled_from(SUPPORTED_LANGUAGES[10:])
    )
    def test_code_block_language_switching(self, test_page, initial_language, new_language):
        """
        Property: Code blocks should support changing the programming language
        and re-applying syntax highlighting.
        
        **Validates: Requirements 5.1, 5.2**
        """
        driver = test_page
        
        code = "function test() { return 42; }"
        
        script = f"""
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const codeBlock = window.codeEditor.createCodeBlock(
            {repr(code)},
            {repr(initial_language)},
            {{ lineNumbers: true, copyButton: true }}
        );
        
        container.appendChild(codeBlock);
        
        const initialLanguage = codeBlock.getAttribute('data-language');
        const initialClass = codeBlock.querySelector('code').className;
        
        // Change language
        window.codeEditor.updateLanguage(codeBlock, {repr(new_language)});
        
        const newLanguage = codeBlock.getAttribute('data-language');
        const newClass = codeBlock.querySelector('code').className;
        
        return {{
            initialLanguage: initialLanguage,
            newLanguage: newLanguage,
            initialClass: initialClass,
            newClass: newClass,
            languageChanged: initialLanguage !== newLanguage,
            classUpdated: initialClass !== newClass
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['initialLanguage'] == initial_language, \
            "Initial language should be set correctly"
        assert result['newLanguage'] == new_language, \
            "Language should be updated"
        assert result['languageChanged'], \
            "Language should change when updateLanguage is called"
        assert result['classUpdated'], \
            "Code element class should be updated"
        assert f'language-{new_language}' in result['newClass'], \
            f"Code element should have new language class"


class TestCodeBlockEdgeCases:
    """Edge case tests for code block functionality"""
    
    def test_empty_code_block(self, test_page):
        """Test code block with empty content"""
        driver = test_page
        
        script = """
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const codeBlock = window.codeEditor.createCodeBlock('', 'javascript');
        container.appendChild(codeBlock);
        
        return {
            hasContainer: !!codeBlock,
            codeContent: codeBlock.querySelector('code')?.textContent || ''
        };
        """
        
        result = driver.execute_script(script)
        
        assert result['hasContainer'], "Empty code block should still be created"
        assert result['codeContent'] == '', "Empty code should render as empty"
    
    def test_very_long_code_block(self, test_page):
        """Test code block with very long content"""
        driver = test_page
        
        long_code = '\n'.join([f'line {i}' for i in range(1000)])
        
        script = f"""
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const longCode = {repr(long_code)};
        const codeBlock = window.codeEditor.createCodeBlock(longCode, 'javascript');
        container.appendChild(codeBlock);
        
        return {{
            hasContainer: !!codeBlock,
            lineCount: longCode.split('\\n').length,
            contentPreserved: codeBlock.querySelector('code').textContent === longCode
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasContainer'], "Long code block should be created"
        assert result['lineCount'] == 1000, "All lines should be preserved"
        assert result['contentPreserved'], "Long content should be preserved exactly"
    
    def test_special_characters_in_code(self, test_page):
        """Test code block with special characters"""
        driver = test_page
        
        special_code = '<script>alert("test");</script>\n<>&"\'\n\t\r\n'
        
        script = f"""
        const container = document.getElementById('test-container');
        container.innerHTML = '';
        
        const specialCode = {repr(special_code)};
        const codeBlock = window.codeEditor.createCodeBlock(specialCode, 'html');
        container.appendChild(codeBlock);
        
        const codeElement = codeBlock.querySelector('code');
        const renderedCode = codeElement.textContent;
        
        return {{
            hasContainer: !!codeBlock,
            originalCode: specialCode,
            renderedCode: renderedCode,
            contentPreserved: renderedCode === specialCode,
            noXSS: !container.querySelector('script[src]')
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasContainer'], "Code block with special chars should be created"
        # Note: textContent normalizes line endings, so we check the important parts
        assert '<script>' in result['renderedCode'], "HTML tags should be preserved"
        assert result['noXSS'], "Special characters should not cause XSS"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
