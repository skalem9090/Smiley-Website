"""
Property-Based Tests for Content Block Creation and Styling

**Feature: advanced-editor-system, Property 2: Block Creation and Styling**

For any block type (paragraph, heading, blockquote, table, list, callout, columns, divider),
creating a block should result in a properly structured block with the correct default styling
and formatting options available.

**Validates: Requirements 1.3, 1.4, 1.5, 6.1, 6.2, 6.3**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


# Callout styles
CALLOUT_STYLES = ['info', 'warning', 'success', 'error', 'note']

# Divider styles
DIVIDER_STYLES = ['solid', 'dashed', 'dotted', 'double']


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
    """Create a test page with content blocks"""
    # Read the necessary JavaScript files
    import os
    
    block_system_path = os.path.join('static', 'js', 'advanced-editor', 'block-system.js')
    content_blocks_path = os.path.join('static', 'js', 'advanced-editor', 'content-blocks.js')
    
    with open(block_system_path, 'r', encoding='utf-8') as f:
        block_system_js = f.read()
    
    with open(content_blocks_path, 'r', encoding='utf-8') as f:
        content_blocks_js = f.read()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Content Blocks Test</title>
        <style>
            body {{ margin: 20px; font-family: Arial, sans-serif; }}
            #test-container {{ margin: 20px 0; }}
            
            /* Callout styles */
            .block-callout {{
                padding: 16px;
                border-radius: 4px;
                margin: 16px 0;
                border-left: 4px solid;
            }}
            .callout-info {{ background: #e3f2fd; border-color: #2196F3; }}
            .callout-warning {{ background: #fff3e0; border-color: #ff9800; }}
            .callout-success {{ background: #e8f5e9; border-color: #4caf50; }}
            .callout-error {{ background: #ffebee; border-color: #f44336; }}
            .callout-note {{ background: #f5f5f5; border-color: #9e9e9e; }}
            
            /* Column styles */
            .block-columns {{
                display: grid;
                gap: 16px;
                margin: 16px 0;
            }}
            
            /* Table styles */
            .block-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 16px 0;
            }}
            .block-table th, .block-table td {{
                border: 1px solid #e0e0e0;
                padding: 8px 12px;
                text-align: left;
            }}
            .block-table th {{
                background: #f5f5f5;
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div id="test-container"></div>
        
        <script>
        {block_system_js}
        </script>
        <script>
        {content_blocks_js}
        </script>
        
        <script>
            window.testReady = true;
        </script>
    </body>
    </html>
    """
    
    # Save to temporary file and load
    import tempfile
    
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


class TestContentBlockCreation:
    """
    Property-Based Tests for Content Block Creation and Styling
    
    **Feature: advanced-editor-system, Property 2: Block Creation and Styling**
    """
    
    @settings(max_examples=100, deadline=5000)
    @given(
        style=st.sampled_from(CALLOUT_STYLES),
        content=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?',
            min_size=5,
            max_size=200
        )
    )
    def test_callout_block_creation(self, test_page, style, content):
        """
        Property: Creating a callout block with any style should result in a properly
        structured block with correct styling.
        
        **Validates: Requirements 6.1**
        """
        driver = test_page
        
        script = f"""
        const callout = window.contentBlocks.createCallout(
            {repr(style)},
            {repr(content)}
        );
        
        return {{
            hasBlock: !!callout,
            type: callout.type,
            style: callout.content.data.style,
            content: callout.content.text,
            hasIcon: !!callout.content.data.icon,
            hasBackgroundColor: !!callout.properties.backgroundColor,
            hasBorderColor: !!callout.properties.borderColor,
            backgroundColor: callout.properties.backgroundColor,
            borderColor: callout.properties.borderColor
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasBlock'], "Callout block should be created"
        assert result['type'] == 'callout', "Block type should be 'callout'"
        assert result['style'] == style, f"Callout style should be '{style}'"
        assert result['content'] == content, "Content should be preserved"
        assert result['hasIcon'], "Callout should have an icon"
        assert result['hasBackgroundColor'], "Callout should have background color"
        assert result['hasBorderColor'], "Callout should have border color"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        column_count=st.integers(min_value=2, max_value=4)
    )
    def test_column_layout_creation(self, test_page, column_count):
        """
        Property: Creating a column layout with any valid column count should result
        in a properly structured block.
        
        **Validates: Requirement 6.2**
        """
        driver = test_page
        
        script = f"""
        const columns = window.contentBlocks.createColumns({column_count});
        
        return {{
            hasBlock: !!columns,
            type: columns.type,
            columnCount: columns.content.data.columnCount,
            childrenCount: columns.children.length,
            hasGap: !!columns.content.data.gap
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasBlock'], "Column layout block should be created"
        assert result['type'] == 'columns', "Block type should be 'columns'"
        assert result['columnCount'] == column_count, \
            f"Column count should be {column_count}"
        assert result['childrenCount'] == column_count, \
            f"Should have {column_count} child blocks"
        assert result['hasGap'], "Column layout should have gap property"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        style=st.sampled_from(DIVIDER_STYLES)
    )
    def test_divider_block_creation(self, test_page, style):
        """
        Property: Creating a divider block with any style should result in a properly
        structured block.
        
        **Validates: Requirement 6.3**
        """
        driver = test_page
        
        script = f"""
        const divider = window.contentBlocks.createDivider({repr(style)});
        
        return {{
            hasBlock: !!divider,
            type: divider.type,
            style: divider.content.data.style,
            hasThickness: !!divider.content.data.thickness,
            hasBorderColor: !!divider.properties.borderColor,
            hasMargin: !!divider.properties.margin
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasBlock'], "Divider block should be created"
        assert result['type'] == 'divider', "Block type should be 'divider'"
        assert result['style'] == style, f"Divider style should be '{style}'"
        assert result['hasThickness'], "Divider should have thickness property"
        assert result['hasBorderColor'], "Divider should have border color"
        assert result['hasMargin'], "Divider should have margin"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        rows=st.integers(min_value=1, max_value=10),
        cols=st.integers(min_value=1, max_value=10),
        headers=st.booleans()
    )
    def test_table_block_creation(self, test_page, rows, cols, headers):
        """
        Property: Creating a table block with any valid dimensions should result
        in a properly structured block with initialized cells.
        
        **Validates: Requirement 1.4**
        """
        driver = test_page
        
        script = f"""
        const table = window.contentBlocks.createTable({rows}, {cols}, {{
            headers: {str(headers).lower()}
        }});
        
        return {{
            hasBlock: !!table,
            type: table.type,
            rows: table.content.data.rows,
            cols: table.content.data.cols,
            headers: table.content.data.headers,
            hasCells: !!table.content.data.cells,
            cellsLength: table.content.data.cells.length,
            firstRowLength: table.content.data.cells[0].length,
            hasBorderColor: !!table.properties.borderColor,
            hasBorderWidth: !!table.properties.borderWidth
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasBlock'], "Table block should be created"
        assert result['type'] == 'table', "Block type should be 'table'"
        assert result['rows'] == rows, f"Table should have {rows} rows"
        assert result['cols'] == cols, f"Table should have {cols} columns"
        assert result['headers'] == headers, f"Table headers should be {headers}"
        assert result['hasCells'], "Table should have cells array"
        assert result['cellsLength'] == rows, "Cells array should match row count"
        assert result['firstRowLength'] == cols, "First row should match column count"
        assert result['hasBorderColor'], "Table should have border color"
        assert result['hasBorderWidth'], "Table should have border width"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        text=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ',
            min_size=1,
            max_size=100
        ),
        ordered=st.booleans(),
        indentation=st.integers(min_value=0, max_value=5)
    )
    def test_list_item_creation(self, test_page, text, ordered, indentation):
        """
        Property: Creating a list item with any text and indentation should result
        in a properly structured block.
        
        **Validates: Requirements 1.5, 6.5**
        """
        driver = test_page
        
        script = f"""
        const listItem = window.contentBlocks.createListItem({repr(text)}, {{
            ordered: {str(ordered).lower()},
            indentation: {indentation}
        }});
        
        return {{
            hasBlock: !!listItem,
            type: listItem.type,
            text: listItem.content.text,
            ordered: listItem.content.data.ordered,
            indentation: listItem.properties.indentation
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasBlock'], "List item block should be created"
        assert result['type'] == 'listItem', "Block type should be 'listItem'"
        assert result['text'] == text, "Text should be preserved"
        assert result['ordered'] == ordered, f"Ordered property should be {ordered}"
        assert result['indentation'] == indentation, \
            f"Indentation should be {indentation}"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        height=st.integers(min_value=10, max_value=200)
    )
    def test_spacer_block_creation(self, test_page, height):
        """
        Property: Creating a spacer block with any height should result in a properly
        structured block.
        
        **Validates: Requirement 6.3**
        """
        driver = test_page
        
        script = f"""
        const spacer = window.contentBlocks.createSpacer({height});
        
        return {{
            hasBlock: !!spacer,
            type: spacer.type,
            height: spacer.content.data.height
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasBlock'], "Spacer block should be created"
        assert result['type'] == 'spacer', "Block type should be 'spacer'"
        assert result['height'] == height, f"Spacer height should be {height}"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        query=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz ',
            min_size=1,
            max_size=20
        )
    )
    def test_block_search_functionality(self, test_page, query):
        """
        Property: Searching for blocks should return relevant results.
        
        **Validates: Requirement 6.7**
        """
        driver = test_page
        
        script = f"""
        const results = window.contentBlocks.searchBlocks({repr(query)});
        
        return {{
            hasResults: Array.isArray(results),
            resultsCount: results.length,
            allHaveType: results.every(r => r.type),
            allHaveLabel: results.every(r => r.label),
            allHaveDescription: results.every(r => r.description),
            allHaveCategory: results.every(r => r.category)
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasResults'], "Search should return an array"
        assert result['resultsCount'] >= 0, "Results count should be non-negative"
        if result['resultsCount'] > 0:
            assert result['allHaveType'], "All results should have type"
            assert result['allHaveLabel'], "All results should have label"
            assert result['allHaveDescription'], "All results should have description"
            assert result['allHaveCategory'], "All results should have category"


class TestContentBlockEdgeCases:
    """Edge case tests for content block creation"""
    
    def test_invalid_column_count(self, test_page):
        """Test column creation with invalid count"""
        driver = test_page
        
        script = """
        const columns = window.contentBlocks.createColumns(10); // Too many
        
        return {
            hasBlock: !!columns,
            columnCount: columns.content.data.columnCount
        };
        """
        
        result = driver.execute_script(script)
        
        assert result['hasBlock'], "Block should still be created"
        assert result['columnCount'] == 2, "Should default to 2 columns"
    
    def test_invalid_table_dimensions(self, test_page):
        """Test table creation with invalid dimensions"""
        driver = test_page
        
        script = """
        const table = window.contentBlocks.createTable(200, 50); // Too large
        
        return {
            hasBlock: !!table,
            rows: table.content.data.rows,
            cols: table.content.data.cols
        };
        """
        
        result = driver.execute_script(script)
        
        assert result['hasBlock'], "Block should still be created"
        assert result['rows'] == 3, "Should default to 3 rows"
        assert result['cols'] == 3, "Should default to 3 columns"
    
    def test_empty_search_query(self, test_page):
        """Test block search with empty query"""
        driver = test_page
        
        script = """
        const results = window.contentBlocks.searchBlocks('');
        
        return {
            hasResults: Array.isArray(results),
            resultsCount: results.length
        };
        """
        
        result = driver.execute_script(script)
        
        assert result['hasResults'], "Should return array"
        assert result['resultsCount'] > 0, "Should return all blocks for empty query"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
