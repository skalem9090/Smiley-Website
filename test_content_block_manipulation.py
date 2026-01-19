"""
Property-Based Tests for Content Block Manipulation Operations

**Feature: advanced-editor-system, Property 11: Block Manipulation Operations**

For any content block and manipulation operation (drag-drop reordering, duplication, deletion),
the operation should complete successfully while maintaining document structure and block relationships.

**Validates: Requirements 6.4, 6.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


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
        <title>Block Manipulation Test</title>
        <style>
            body {{ margin: 20px; font-family: Arial, sans-serif; }}
            #test-container {{ margin: 20px 0; }}
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


class TestContentBlockManipulation:
    """
    Property-Based Tests for Content Block Manipulation Operations
    
    **Feature: advanced-editor-system, Property 11: Block Manipulation Operations**
    """
    
    @settings(max_examples=100, deadline=5000)
    @given(
        row=st.integers(min_value=0, max_value=5),
        col=st.integers(min_value=0, max_value=5),
        content=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ',
            min_size=1,
            max_size=50
        )
    )
    def test_table_cell_update(self, test_page, row, col, content):
        """
        Property: Updating any table cell should preserve table structure and update
        the cell content correctly.
        
        **Validates: Requirement 6.4**
        """
        driver = test_page
        
        script = f"""
        // Create a table
        const table = window.contentBlocks.createTable(6, 6);
        const originalRows = table.content.data.rows;
        const originalCols = table.content.data.cols;
        const originalVersion = table.metadata.version;
        
        // Update cell
        const updated = window.contentBlocks.updateTableCell(
            table,
            {row},
            {col},
            {repr(content)}
        );
        
        return {{
            hasTable: !!updated,
            rowsPreserved: updated.content.data.rows === originalRows,
            colsPreserved: updated.content.data.cols === originalCols,
            cellContent: updated.content.data.cells[{row}][{col}],
            versionIncremented: updated.metadata.version > originalVersion
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasTable'], "Table should be returned"
        assert result['rowsPreserved'], "Row count should be preserved"
        assert result['colsPreserved'], "Column count should be preserved"
        assert result['cellContent'] == content, "Cell content should be updated"
        assert result['versionIncremented'], "Version should be incremented"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        position=st.integers(min_value=0, max_value=5)
    )
    def test_table_row_addition(self, test_page, position):
        """
        Property: Adding a row to a table should increase row count and maintain
        column count.
        
        **Validates: Requirement 6.4**
        """
        driver = test_page
        
        script = f"""
        const table = window.contentBlocks.createTable(3, 4);
        const originalRows = table.content.data.rows;
        const originalCols = table.content.data.cols;
        
        const updated = window.contentBlocks.addTableRow(table, {position});
        
        return {{
            hasTable: !!updated,
            rowsIncreased: updated.content.data.rows === originalRows + 1,
            colsPreserved: updated.content.data.cols === originalCols,
            cellsLength: updated.content.data.cells.length,
            newRowLength: updated.content.data.cells[{min(position, 3)}].length
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasTable'], "Table should be returned"
        assert result['rowsIncreased'], "Row count should increase by 1"
        assert result['colsPreserved'], "Column count should be preserved"
        assert result['cellsLength'] == 4, "Cells array should have 4 rows"
        assert result['newRowLength'] == 4, "New row should have correct column count"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        position=st.integers(min_value=0, max_value=4)
    )
    def test_table_column_addition(self, test_page, position):
        """
        Property: Adding a column to a table should increase column count and maintain
        row count.
        
        **Validates: Requirement 6.4**
        """
        driver = test_page
        
        script = f"""
        const table = window.contentBlocks.createTable(3, 4);
        const originalRows = table.content.data.rows;
        const originalCols = table.content.data.cols;
        
        const updated = window.contentBlocks.addTableColumn(table, {position});
        
        return {{
            hasTable: !!updated,
            rowsPreserved: updated.content.data.rows === originalRows,
            colsIncreased: updated.content.data.cols === originalCols + 1,
            firstRowLength: updated.content.data.cells[0].length,
            allRowsUpdated: updated.content.data.cells.every(row => row.length === originalCols + 1)
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasTable'], "Table should be returned"
        assert result['rowsPreserved'], "Row count should be preserved"
        assert result['colsIncreased'], "Column count should increase by 1"
        assert result['firstRowLength'] == 5, "First row should have 5 columns"
        assert result['allRowsUpdated'], "All rows should have new column"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        row_to_delete=st.integers(min_value=0, max_value=4)
    )
    def test_table_row_deletion(self, test_page, row_to_delete):
        """
        Property: Deleting a row from a table should decrease row count and maintain
        column count.
        
        **Validates: Requirement 6.4**
        """
        driver = test_page
        
        script = f"""
        const table = window.contentBlocks.createTable(5, 3);
        const originalRows = table.content.data.rows;
        const originalCols = table.content.data.cols;
        
        const updated = window.contentBlocks.deleteTableRow(table, {row_to_delete});
        
        return {{
            hasTable: !!updated,
            rowsDecreased: updated.content.data.rows === originalRows - 1,
            colsPreserved: updated.content.data.cols === originalCols,
            cellsLength: updated.content.data.cells.length
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasTable'], "Table should be returned"
        assert result['rowsDecreased'], "Row count should decrease by 1"
        assert result['colsPreserved'], "Column count should be preserved"
        assert result['cellsLength'] == 4, "Cells array should have 4 rows"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        col_to_delete=st.integers(min_value=0, max_value=3)
    )
    def test_table_column_deletion(self, test_page, col_to_delete):
        """
        Property: Deleting a column from a table should decrease column count and
        maintain row count.
        
        **Validates: Requirement 6.4**
        """
        driver = test_page
        
        script = f"""
        const table = window.contentBlocks.createTable(3, 4);
        const originalRows = table.content.data.rows;
        const originalCols = table.content.data.cols;
        
        const updated = window.contentBlocks.deleteTableColumn(table, {col_to_delete});
        
        return {{
            hasTable: !!updated,
            rowsPreserved: updated.content.data.rows === originalRows,
            colsDecreased: updated.content.data.cols === originalCols - 1,
            firstRowLength: updated.content.data.cells[0].length,
            allRowsUpdated: updated.content.data.cells.every(row => row.length === originalCols - 1)
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasTable'], "Table should be returned"
        assert result['rowsPreserved'], "Row count should be preserved"
        assert result['colsDecreased'], "Column count should decrease by 1"
        assert result['firstRowLength'] == 3, "First row should have 3 columns"
        assert result['allRowsUpdated'], "All rows should have column removed"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        text=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ',
            min_size=1,
            max_size=100
        )
    )
    def test_list_item_indentation(self, test_page, text):
        """
        Property: Indenting a list item should increase indentation level without
        changing content.
        
        **Validates: Requirement 6.5**
        """
        driver = test_page
        
        script = f"""
        const listItem = window.contentBlocks.createListItem({repr(text)});
        const originalIndent = listItem.properties.indentation;
        const originalText = listItem.content.text;
        
        const indented = window.contentBlocks.indentListItem(listItem);
        
        return {{
            hasItem: !!indented,
            indentIncreased: indented.properties.indentation === originalIndent + 1,
            textPreserved: indented.content.text === originalText,
            versionIncremented: indented.metadata.version > 1
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasItem'], "List item should be returned"
        assert result['indentIncreased'], "Indentation should increase by 1"
        assert result['textPreserved'], "Text content should be preserved"
        assert result['versionIncremented'], "Version should be incremented"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        text=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ',
            min_size=1,
            max_size=100
        ),
        initial_indent=st.integers(min_value=1, max_value=5)
    )
    def test_list_item_outdentation(self, test_page, text, initial_indent):
        """
        Property: Outdenting a list item should decrease indentation level without
        changing content.
        
        **Validates: Requirement 6.5**
        """
        driver = test_page
        
        script = f"""
        const listItem = window.contentBlocks.createListItem({repr(text)}, {{
            indentation: {initial_indent}
        }});
        const originalIndent = listItem.properties.indentation;
        const originalText = listItem.content.text;
        
        const outdented = window.contentBlocks.outdentListItem(listItem);
        
        return {{
            hasItem: !!outdented,
            indentDecreased: outdented.properties.indentation === originalIndent - 1,
            textPreserved: outdented.content.text === originalText,
            versionIncremented: outdented.metadata.version > 1
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasItem'], "List item should be returned"
        assert result['indentDecreased'], "Indentation should decrease by 1"
        assert result['textPreserved'], "Text content should be preserved"
        assert result['versionIncremented'], "Version should be incremented"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        items=st.lists(
            st.fixed_dictionaries({
                'text': st.text(
                    alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ',
                    min_size=1,
                    max_size=50
                ),
                'indentation': st.integers(min_value=0, max_value=3)
            }),
            min_size=1,
            max_size=5
        )
    )
    def test_nested_list_creation(self, test_page, items):
        """
        Property: Creating a nested list should preserve all items and their
        indentation levels.
        
        **Validates: Requirement 6.5**
        """
        driver = test_page
        
        script = f"""
        const items = {repr(items)};
        const listItems = window.contentBlocks.createNestedList(items, false);
        
        return {{
            hasItems: Array.isArray(listItems),
            itemCount: listItems.length,
            allHaveType: listItems.every(item => item.type === 'listItem'),
            textsMatch: listItems.every((item, i) => item.content.text === items[i].text)
        }};
        """
        
        result = driver.execute_script(script)
        
        assert result['hasItems'], "Should return array of list items"
        assert result['itemCount'] == len(items), f"Should have {len(items)} items"
        assert result['allHaveType'], "All items should be list items"
        assert result['textsMatch'], "All texts should be preserved"


class TestBlockManipulationEdgeCases:
    """Edge case tests for block manipulation"""
    
    def test_table_cannot_delete_last_row(self, test_page):
        """Test that deleting the last row is prevented"""
        driver = test_page
        
        script = """
        const table = window.contentBlocks.createTable(1, 3);
        const originalRows = table.content.data.rows;
        
        const updated = window.contentBlocks.deleteTableRow(table, 0);
        
        return {
            rowsPreserved: updated.content.data.rows === originalRows
        };
        """
        
        result = driver.execute_script(script)
        
        assert result['rowsPreserved'], "Should not delete last row"
    
    def test_table_cannot_delete_last_column(self, test_page):
        """Test that deleting the last column is prevented"""
        driver = test_page
        
        script = """
        const table = window.contentBlocks.createTable(3, 1);
        const originalCols = table.content.data.cols;
        
        const updated = window.contentBlocks.deleteTableColumn(table, 0);
        
        return {
            colsPreserved: updated.content.data.cols === originalCols
        };
        """
        
        result = driver.execute_script(script)
        
        assert result['colsPreserved'], "Should not delete last column"
    
    def test_list_item_max_indentation(self, test_page):
        """Test that indentation is capped at maximum level"""
        driver = test_page
        
        script = """
        let listItem = window.contentBlocks.createListItem('Test');
        
        // Indent 10 times
        for (let i = 0; i < 10; i++) {
            listItem = window.contentBlocks.indentListItem(listItem);
        }
        
        return {
            indentation: listItem.properties.indentation,
            cappedAt5: listItem.properties.indentation <= 5
        };
        """
        
        result = driver.execute_script(script)
        
        assert result['cappedAt5'], "Indentation should be capped at 5"
    
    def test_list_item_min_indentation(self, test_page):
        """Test that outdentation is capped at minimum level"""
        driver = test_page
        
        script = """
        let listItem = window.contentBlocks.createListItem('Test');
        
        // Outdent 5 times (should stay at 0)
        for (let i = 0; i < 5; i++) {
            listItem = window.contentBlocks.outdentListItem(listItem);
        }
        
        return {
            indentation: listItem.properties.indentation,
            staysAt0: listItem.properties.indentation === 0
        };
        """
        
        result = driver.execute_script(script)
        
        assert result['staysAt0'], "Indentation should not go below 0"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
