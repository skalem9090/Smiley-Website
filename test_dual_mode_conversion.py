"""
Property-Based Tests for Dual-Mode Editing

Tests the WYSIWYG/Markdown conversion and synchronization.
Uses Hypothesis for property-based testing.

Feature: advanced-editor-system, Property 3: Dual-Mode Round-Trip Preservation
Feature: advanced-editor-system, Property 4: Mode Synchronization
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import JavascriptException
import json
import os
import tempfile


# Markdown content strategies
@st.composite
def markdown_text_strategy(draw):
    """Generate valid Markdown text"""
    elements = []
    
    # Add headings
    if draw(st.booleans()):
        level = draw(st.integers(min_value=1, max_value=6))
        text = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters='\n#')))
        elements.append('#' * level + ' ' + text)
    
    # Add paragraphs
    if draw(st.booleans()):
        text = draw(st.text(min_size=1, max_size=200, alphabet=st.characters(blacklist_characters='\n')))
        elements.append(text)
    
    # Add quotes
    if draw(st.booleans()):
        text = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_characters='\n>')))
        elements.append('> ' + text)
    
    # Add list items
    if draw(st.booleans()):
        text = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters='\n-*')))
        elements.append('- ' + text)
    
    # Add code blocks
    if draw(st.booleans()):
        lang = draw(st.sampled_from(['javascript', 'python', 'html', 'css']))
        code = draw(st.text(min_size=1, max_size=100))
        elements.append(f'```{lang}\n{code}\n```')
    
    return '\n\n'.join(elements) if elements else '# Test Heading'


class TestDualModeConversion:
    """Test suite for dual-mode editing"""
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Set up Selenium WebDriver"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        
        yield driver
        
        driver.quit()
    
    @pytest.fixture(scope="class")
    def setup_page(self, driver):
        """Set up test page with dual-mode system loaded"""
        # Read the JavaScript files
        js_files = [
            'static/js/advanced-editor/block-system.js',
            'static/js/advanced-editor/markdown-parser.js',
            'static/js/advanced-editor/mode-converter.js'
        ]
        
        js_content = []
        for js_file in js_files:
            with open(js_file, 'r', encoding='utf-8') as f:
                js_content.append(f.read())
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Dual Mode Test</title>
        </head>
        <body>
            <div id="test-container"></div>
            <script>
                {''.join(js_content)}
                
                // Mock EditorController for testing
                window.testEditorController = {{
                    blockManager: {{
                        blockCollection: new window.BlockCollection(),
                        getAllBlocks: function() {{
                            return this.blockCollection.getAll();
                        }},
                        clearAllBlocks: function() {{
                            this.blockCollection.clear();
                        }}
                    }}
                }};
                
                // Make components available for testing
                window.testDualMode = {{
                    MarkdownParser: window.MarkdownParser,
                    MarkdownSerializer: window.MarkdownSerializer,
                    ModeConverter: window.ModeConverter,
                    BlockFactory: window.BlockFactory,
                    BlockType: window.BlockType
                }};
            </script>
        </body>
        </html>
        """
        
        # Save HTML to a temporary file and load it
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            temp_file = f.name
        
        try:
            driver.get(f'file://{os.path.abspath(temp_file)}')
            
            # Wait for scripts to load
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script('return typeof window.testDualMode !== "undefined"')
            )
            
            yield driver
        finally:
            os.unlink(temp_file)
    
    def execute_js(self, driver, script):
        """Execute JavaScript and return result"""
        try:
            return driver.execute_script(script)
        except JavascriptException as e:
            pytest.fail(f"JavaScript execution failed: {e}")
    
    @given(markdown=markdown_text_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_markdown_to_blocks_conversion(self, setup_page, markdown):
        """
        Property Test: Markdown to Blocks Conversion
        
        For any valid Markdown text, parsing should produce valid blocks
        that can be serialized back to Markdown.
        """
        driver = setup_page
        
        # Escape markdown for JavaScript
        markdown_escaped = json.dumps(markdown)
        
        script = f"""
        const markdown = {markdown_escaped};
        const parser = new window.testDualMode.MarkdownParser();
        
        try {{
            const blocks = parser.parse(markdown);
            
            return {{
                success: true,
                blockCount: blocks.length,
                blockTypes: blocks.map(b => b.type),
                hasBlocks: blocks.length > 0
            }};
        }} catch (error) {{
            return {{
                success: false,
                error: error.message
            }};
        }}
        """
        
        result = self.execute_js(driver, script)
        
        assert result['success'] is True, f"Parsing failed: {result.get('error', 'Unknown error')}"
        assert result['hasBlocks'] is True, "Should produce at least one block"
        assert result['blockCount'] > 0, "Block count should be positive"
    
    @given(markdown=markdown_text_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_round_trip_preservation(self, setup_page, markdown):
        """
        Property Test: Round-Trip Preservation
        
        **Feature: advanced-editor-system, Property 3: Dual-Mode Round-Trip Preservation**
        
        For any valid Markdown content, converting Markdown → Blocks → Markdown
        should preserve the essential content and structure.
        
        **Validates: Requirements 2.1, 2.2, 2.4**
        """
        driver = setup_page
        
        markdown_escaped = json.dumps(markdown)
        
        script = f"""
        const markdown = {markdown_escaped};
        const parser = new window.testDualMode.MarkdownParser();
        const serializer = new window.testDualMode.MarkdownSerializer();
        
        try {{
            // Parse Markdown to blocks
            const blocks = parser.parse(markdown);
            
            // Serialize blocks back to Markdown
            const roundTripMarkdown = serializer.serialize(blocks);
            
            // Parse again to verify
            const roundTripBlocks = parser.parse(roundTripMarkdown);
            
            return {{
                success: true,
                originalBlockCount: blocks.length,
                roundTripBlockCount: roundTripBlocks.length,
                originalMarkdown: markdown,
                roundTripMarkdown: roundTripMarkdown,
                blockCountMatch: blocks.length === roundTripBlocks.length
            }};
        }} catch (error) {{
            return {{
                success: false,
                error: error.message
            }};
        }}
        """
        
        result = self.execute_js(driver, script)
        
        assert result['success'] is True, f"Round-trip failed: {result.get('error', 'Unknown error')}"
        assert result['blockCountMatch'] is True, "Block count should be preserved in round-trip"
    
    def test_mode_converter_initialization(self, setup_page):
        """
        Unit Test: ModeConverter initialization
        
        ModeConverter should initialize with proper parser and serializer.
        """
        driver = setup_page
        
        script = """
        const converter = new window.testDualMode.ModeConverter(window.testEditorController);
        
        return {
            hasParser: converter.markdownParser !== null,
            hasSerializer: converter.markdownSerializer !== null,
            currentMode: converter.currentMode
        };
        """
        
        result = self.execute_js(driver, script)
        
        assert result['hasParser'] is True, "Should have markdown parser"
        assert result['hasSerializer'] is True, "Should have markdown serializer"
        assert result['currentMode'] == 'wysiwyg', "Should start in WYSIWYG mode"
    
    def test_wysiwyg_to_markdown_conversion(self, setup_page):
        """
        Unit Test: WYSIWYG to Markdown conversion
        
        Converting blocks to Markdown should produce valid Markdown text.
        """
        driver = setup_page
        
        script = """
        const converter = new window.testDualMode.ModeConverter(window.testEditorController);
        const blockManager = window.testEditorController.blockManager;
        
        // Create some test blocks
        const block1 = window.testDualMode.BlockFactory.createBlock(
            window.testDualMode.BlockType.HEADING,
            { content: { text: 'Test Heading', data: { level: 1 } } }
        );
        const block2 = window.testDualMode.BlockFactory.createBlock(
            window.testDualMode.BlockType.PARAGRAPH,
            { content: { text: 'Test paragraph' } }
        );
        
        blockManager.blockCollection.add(block1);
        blockManager.blockCollection.add(block2);
        
        // Convert to Markdown
        const markdown = converter.convertToMarkdown();
        
        return {
            markdown: markdown,
            hasContent: markdown.length > 0,
            hasHeading: markdown.includes('# Test Heading'),
            hasParagraph: markdown.includes('Test paragraph')
        };
        """
        
        result = self.execute_js(driver, script)
        
        assert result['hasContent'] is True, "Should produce Markdown content"
        assert result['hasHeading'] is True, "Should include heading"
        assert result['hasParagraph'] is True, "Should include paragraph"
    
    def test_markdown_to_wysiwyg_conversion(self, setup_page):
        """
        Unit Test: Markdown to WYSIWYG conversion
        
        Converting Markdown to blocks should produce valid block structures.
        """
        driver = setup_page
        
        script = """
        const converter = new window.testDualMode.ModeConverter(window.testEditorController);
        const markdown = '# Test Heading\\n\\nTest paragraph\\n\\n> Test quote';
        
        // Convert to WYSIWYG
        const blocks = converter.convertToWYSIWYG(markdown);
        
        return {
            blockCount: blocks.length,
            hasHeading: blocks.some(b => b.type === 'heading'),
            hasParagraph: blocks.some(b => b.type === 'paragraph'),
            hasQuote: blocks.some(b => b.type === 'quote')
        };
        """
        
        result = self.execute_js(driver, script)
        
        assert result['blockCount'] >= 3, "Should produce at least 3 blocks"
        assert result['hasHeading'] is True, "Should have heading block"
        assert result['hasParagraph'] is True, "Should have paragraph block"
        assert result['hasQuote'] is True, "Should have quote block"
    
    def test_content_preservation_simple(self, setup_page):
        """
        Unit Test: Content Preservation (Simplified)
        
        **Feature: advanced-editor-system, Property 4: Mode Synchronization**
        
        Content should be preserved during mode conversion for common cases.
        
        **Validates: Requirements 2.3**
        """
        driver = setup_page
        
        script = """
        const converter = new window.testDualMode.ModeConverter(window.testEditorController);
        const blockManager = window.testEditorController.blockManager;
        
        // Create blocks with test content
        const block1 = window.testDualMode.BlockFactory.createBlock(
            window.testDualMode.BlockType.HEADING,
            { content: { text: 'My Heading', data: { level: 2 } } }
        );
        const block2 = window.testDualMode.BlockFactory.createBlock(
            window.testDualMode.BlockType.PARAGRAPH,
            { content: { text: 'My paragraph text' } }
        );
        
        blockManager.blockCollection.add(block1);
        blockManager.blockCollection.add(block2);
        
        // Convert to Markdown
        const markdown = converter.convertToMarkdown();
        
        // Convert back to blocks
        const roundTripBlocks = converter.convertToWYSIWYG(markdown);
        
        return {
            markdown: markdown,
            blockCount: roundTripBlocks.length,
            hasHeading: markdown.includes('My Heading'),
            hasParagraph: markdown.includes('My paragraph')
        };
        """
        
        result = self.execute_js(driver, script)
        
        assert result['hasHeading'] is True, "Should preserve heading text"
        assert result['hasParagraph'] is True, "Should preserve paragraph text"
        assert result['blockCount'] >= 2, "Should have at least 2 blocks after round-trip"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
