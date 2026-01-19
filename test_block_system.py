"""
Property-Based Tests for Block System Implementation

Tests the Block interface and data structures according to the design document.
Uses Hypothesis for property-based testing to validate correctness properties.

Feature: advanced-editor-system, Property 2: Block Creation and Styling
Feature: advanced-editor-system, Property 11: Block Manipulation Operations
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, JavascriptException
import json
import time


# Block type constants matching JavaScript implementation
BLOCK_TYPES = [
    'paragraph', 'heading', 'quote', 'listItem',
    'image', 'video', 'audio', 'file',
    'codeBlock', 'inlineCode',
    'columns', 'divider', 'spacer',
    'callout', 'table', 'embed', 'template'
]

BLOCK_ALIGNMENTS = ['left', 'center', 'right', 'justify']
CALLOUT_STYLES = ['info', 'warning', 'success', 'error', 'note']


# Hypothesis strategies for generating test data
@st.composite
def block_type_strategy(draw):
    """Generate a valid block type"""
    return draw(st.sampled_from(BLOCK_TYPES))


@st.composite
def block_content_strategy(draw, block_type):
    """Generate valid content for a block type"""
    content = {
        'text': draw(st.text(min_size=0, max_size=1000)),
        'html': draw(st.text(min_size=0, max_size=1000)),
        'data': {}
    }
    
    # Add type-specific data
    if block_type == 'heading':
        content['data']['level'] = draw(st.integers(min_value=1, max_value=6))
    elif block_type == 'codeBlock':
        content['data']['language'] = draw(st.sampled_from(['javascript', 'python', 'html', 'css']))
        content['data']['lineNumbers'] = draw(st.booleans())
    elif block_type == 'image':
        content['data']['url'] = draw(st.text(min_size=1, max_size=200))
        content['data']['alt'] = draw(st.text(min_size=1, max_size=200))
        content['data']['caption'] = draw(st.text(min_size=0, max_size=200))
    elif block_type == 'callout':
        content['data']['style'] = draw(st.sampled_from(CALLOUT_STYLES))
    elif block_type == 'columns':
        content['data']['columnCount'] = draw(st.integers(min_value=2, max_value=4))
    elif block_type == 'table':
        content['data']['rows'] = draw(st.integers(min_value=1, max_value=20))
        content['data']['cols'] = draw(st.integers(min_value=1, max_value=10))
        content['data']['headers'] = draw(st.booleans())
    
    return content


@st.composite
def block_properties_strategy(draw):
    """Generate valid block properties"""
    return {
        'alignment': draw(st.sampled_from(BLOCK_ALIGNMENTS)),
        'color': draw(st.one_of(st.none(), st.text(min_size=3, max_size=20))),
        'backgroundColor': draw(st.one_of(st.none(), st.text(min_size=3, max_size=20))),
        'fontSize': draw(st.one_of(st.none(), st.integers(min_value=8, max_value=72))),
        'fontFamily': draw(st.one_of(st.none(), st.sampled_from(['Arial', 'Times New Roman', 'Courier']))),
        'indentation': draw(st.integers(min_value=0, max_value=10))
    }


@st.composite
def block_options_strategy(draw, block_type):
    """Generate valid block creation options"""
    return {
        'content': draw(block_content_strategy(block_type)),
        'properties': draw(block_properties_strategy()),
        'author': draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        'children': []  # Simplified for now
    }


class TestBlockSystem:
    """Test suite for block system implementation"""
    
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
        """Set up test page with block system loaded"""
        import os
        import tempfile
        
        # Read the block-system.js file
        block_system_path = os.path.join('static', 'js', 'advanced-editor', 'block-system.js')
        with open(block_system_path, 'r', encoding='utf-8') as f:
            block_system_js = f.read()
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Block System Test</title>
        </head>
        <body>
            <div id="test-container"></div>
            <script>
                {block_system_js}
                
                // Make block system available globally for testing
                window.testBlockSystem = {{
                    BlockType: window.BlockType,
                    BlockFactory: window.BlockFactory,
                    BlockSchema: window.BlockSchema,
                    BlockCollection: window.BlockCollection,
                    BlockAlignment: window.BlockAlignment,
                    CalloutStyle: window.CalloutStyle,
                    BlockStatus: window.BlockStatus
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
                lambda d: d.execute_script('return typeof window.testBlockSystem !== "undefined"')
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
    
    @given(
        block_type=block_type_strategy(),
        options=st.data()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_block_creation_structure(self, setup_page, block_type, options):
        """
        Property Test: Block Creation and Styling
        
        **Feature: advanced-editor-system, Property 2: Block Creation and Styling**
        
        For any block type, creating a block should result in a properly 
        structured block with the correct default styling and formatting 
        options available.
        
        **Validates: Requirements 1.3, 1.4, 1.5, 6.1, 6.2, 6.3**
        """
        driver = setup_page
        
        # Generate options for this block type
        block_options = options.draw(block_options_strategy(block_type))
        
        # Create block via JavaScript
        script = f"""
        const options = {json.dumps(block_options)};
        const block = window.testBlockSystem.BlockFactory.createBlock('{block_type}', options);
        return block;
        """
        
        block = self.execute_js(driver, script)
        
        # Verify block structure
        assert block is not None, "Block should be created"
        assert 'id' in block, "Block must have an ID"
        assert isinstance(block['id'], str), "Block ID must be a string"
        assert block['id'].startswith('block_'), "Block ID should have correct prefix"
        
        assert 'type' in block, "Block must have a type"
        assert block['type'] == block_type, f"Block type should be {block_type}"
        
        assert 'content' in block, "Block must have content"
        assert isinstance(block['content'], dict), "Block content must be an object"
        
        assert 'properties' in block, "Block must have properties"
        assert isinstance(block['properties'], dict), "Block properties must be an object"
        
        assert 'metadata' in block, "Block must have metadata"
        assert isinstance(block['metadata'], dict), "Block metadata must be an object"
        
        # Verify metadata structure
        metadata = block['metadata']
        assert 'createdAt' in metadata, "Metadata must have createdAt"
        assert 'updatedAt' in metadata, "Metadata must have updatedAt"
        assert 'version' in metadata, "Metadata must have version"
        assert metadata['version'] == 1, "Initial version should be 1"
        assert 'status' in metadata, "Metadata must have status"
        
        # Verify children array exists
        assert 'children' in block, "Block must have children array"
        assert isinstance(block['children'], list), "Block children must be an array"
    
    @given(
        block_type=block_type_strategy(),
        options=st.data()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_block_validation(self, setup_page, block_type, options):
        """
        Property Test: Block structure validation
        
        For any created block, validation should pass and confirm all 
        required fields are present and correctly typed.
        """
        driver = setup_page
        
        block_options = options.draw(block_options_strategy(block_type))
        
        # Create and validate block
        script = f"""
        const options = {json.dumps(block_options)};
        const block = window.testBlockSystem.BlockFactory.createBlock('{block_type}', options);
        const validation = window.testBlockSystem.BlockFactory.validateBlock(block);
        return validation;
        """
        
        validation = self.execute_js(driver, script)
        
        assert validation is not None, "Validation result should be returned"
        assert 'isValid' in validation, "Validation must have isValid field"
        assert validation['isValid'] is True, f"Block should be valid. Errors: {validation.get('errors', [])}"
        assert 'errors' in validation, "Validation must have errors field"
        assert len(validation['errors']) == 0, "Valid block should have no errors"
    
    @given(
        block_type=block_type_strategy(),
        options=st.data()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_block_manipulation_operations(self, setup_page, block_type, options):
        """
        Property Test: Block Manipulation Operations
        
        **Feature: advanced-editor-system, Property 11: Block Manipulation Operations**
        
        For any content block and manipulation operation (create, update, delete, 
        move, duplicate), the operation should complete successfully while 
        maintaining document structure and block relationships.
        
        **Validates: Requirements 6.4, 6.5**
        """
        driver = setup_page
        
        block_options = options.draw(block_options_strategy(block_type))
        
        # Test create, update, delete, duplicate operations
        options_json = json.dumps(block_options)
        script = """
        const options = """ + options_json + """;
        const collection = new window.testBlockSystem.BlockCollection();
        
        // Create block
        const block1 = window.testBlockSystem.BlockFactory.createBlock('""" + block_type + """', options);
        collection.add(block1);
        
        const initialCount = collection.count();
        const block1Retrieved = collection.get(block1.id);
        
        // Update block
        const updates = {
            content: { text: 'Updated text' },
            properties: { alignment: 'center' }
        };
        const updatedBlock = collection.update(block1.id, updates);
        
        // Duplicate block
        const block2 = window.testBlockSystem.BlockFactory.cloneBlock(block1);
        collection.add(block2);
        
        const afterDuplicateCount = collection.count();
        
        // Move block
        const moved = collection.move(block2.id, 0);
        const newPosition = collection.getPosition(block2.id);
        
        // Delete block
        const deleted = collection.remove(block2.id);
        const finalCount = collection.count();
        
        return {
            initialCount: initialCount,
            block1Retrieved: block1Retrieved !== null,
            updatedBlock: updatedBlock !== null,
            updatedVersion: updatedBlock ? updatedBlock.metadata.version : 0,
            afterDuplicateCount: afterDuplicateCount,
            moved: moved,
            newPosition: newPosition,
            deleted: deleted,
            finalCount: finalCount,
            block1StillExists: collection.get(block1.id) !== null,
            block2Removed: collection.get(block2.id) === null
        };
        """
        
        result = self.execute_js(driver, script)
        
        # Verify create operation
        assert result['initialCount'] == 1, "Collection should have 1 block after creation"
        assert result['block1Retrieved'] is True, "Created block should be retrievable"
        
        # Verify update operation
        assert result['updatedBlock'] is True, "Block should be updated"
        assert result['updatedVersion'] == 2, "Version should increment after update"
        
        # Verify duplicate operation
        assert result['afterDuplicateCount'] == 2, "Collection should have 2 blocks after duplication"
        
        # Verify move operation
        assert result['moved'] is True, "Block should be moved"
        assert result['newPosition'] == 0, "Block should be at position 0"
        
        # Verify delete operation
        assert result['deleted'] is True, "Block should be deleted"
        assert result['finalCount'] == 1, "Collection should have 1 block after deletion"
        assert result['block1StillExists'] is True, "Original block should still exist"
        assert result['block2Removed'] is True, "Duplicated block should be removed"
    
    @given(
        block_type=block_type_strategy(),
        options=st.data(),
        new_position=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_block_ordering_preservation(self, setup_page, block_type, options, new_position):
        """
        Property Test: Block ordering is preserved during operations
        
        For any sequence of block operations, the order of blocks should 
        be maintained correctly and retrievable.
        """
        driver = setup_page
        
        block_options = options.draw(block_options_strategy(block_type))
        
        # Create multiple blocks and test ordering
        script = f"""
        const options = {json.dumps(block_options)};
        const collection = new window.testBlockSystem.BlockCollection();
        
        // Create 5 blocks
        const blocks = [];
        for (let i = 0; i < 5; i++) {{
            const block = window.testBlockSystem.BlockFactory.createBlock('{block_type}', options);
            collection.add(block);
            blocks.push(block.id);
        }}
        
        // Get initial order
        const initialOrder = collection.getAll().map(b => b.id);
        
        // Move first block to new position
        const targetPosition = Math.min({new_position}, 4);
        const moved = collection.move(blocks[0], targetPosition);
        
        // Get final order
        const finalOrder = collection.getAll().map(b => b.id);
        
        return {{
            initialOrder: initialOrder,
            finalOrder: finalOrder,
            moved: moved,
            allBlocksPresent: finalOrder.length === 5,
            firstBlockPosition: collection.getPosition(blocks[0])
        }};
        """
        
        result = self.execute_js(driver, script)
        
        assert result['moved'] is True, "Block should be moved successfully"
        assert result['allBlocksPresent'] is True, "All blocks should still be present"
        assert len(result['initialOrder']) == 5, "Should have 5 blocks initially"
        assert len(result['finalOrder']) == 5, "Should have 5 blocks after move"
        
        # Verify all blocks are still present (just reordered)
        assert set(result['initialOrder']) == set(result['finalOrder']), "Same blocks should be present"
    
    @given(block_type=block_type_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_block_schema_validation(self, setup_page, block_type):
        """
        Property Test: Block schema validation
        
        For any block type, the schema should define required fields and 
        validation should enforce them.
        """
        driver = setup_page
        
        script = f"""
        const schema = window.testBlockSystem.BlockSchema.getSchema('{block_type}');
        
        if (!schema) {{
            return {{ hasSchema: false }};
        }}
        
        return {{
            hasSchema: true,
            type: schema.type,
            hasRequiredFields: Array.isArray(schema.requiredFields),
            hasOptionalFields: Array.isArray(schema.optionalFields),
            hasProperties: Array.isArray(schema.properties),
            hasAllowedChildren: Array.isArray(schema.allowedChildren)
        }};
        """
        
        result = self.execute_js(driver, script)
        
        assert result['hasSchema'] is True, f"Schema should exist for block type {block_type}"
        assert result['type'] == block_type, "Schema type should match block type"
        assert result['hasRequiredFields'] is True, "Schema should define required fields"
        assert result['hasOptionalFields'] is True, "Schema should define optional fields"
        assert result['hasProperties'] is True, "Schema should define properties"
        assert result['hasAllowedChildren'] is True, "Schema should define allowed children"
    
    def test_block_collection_json_serialization(self, setup_page):
        """
        Unit Test: Block collection JSON serialization
        
        Block collections should be serializable to JSON and deserializable 
        back to the same structure.
        """
        driver = setup_page
        
        script = """
        const collection = new window.testBlockSystem.BlockCollection();
        
        // Create some blocks
        const block1 = window.testBlockSystem.BlockFactory.createBlock('paragraph', {
            content: { text: 'Test paragraph' }
        });
        const block2 = window.testBlockSystem.BlockFactory.createBlock('heading', {
            content: { text: 'Test heading', data: { level: 2 } }
        });
        
        collection.add(block1);
        collection.add(block2);
        
        // Export to JSON
        const exported = collection.toJSON();
        
        // Create new collection and import
        const newCollection = new window.testBlockSystem.BlockCollection();
        newCollection.fromJSON(exported);
        
        return {
            originalCount: collection.count(),
            importedCount: newCollection.count(),
            originalBlocks: collection.getAll().map(b => ({ id: b.id, type: b.type })),
            importedBlocks: newCollection.getAll().map(b => ({ id: b.id, type: b.type }))
        };
        """
        
        result = self.execute_js(driver, script)
        
        assert result['originalCount'] == result['importedCount'], "Counts should match"
        assert result['originalCount'] == 2, "Should have 2 blocks"
        
        # Verify blocks match
        for i in range(len(result['originalBlocks'])):
            assert result['originalBlocks'][i]['id'] == result['importedBlocks'][i]['id'], "Block IDs should match"
            assert result['originalBlocks'][i]['type'] == result['importedBlocks'][i]['type'], "Block types should match"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
