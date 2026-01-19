"""
Property-Based Tests for Export System
Feature: advanced-editor-system
Property 17: Export Format Integrity

Tests that exported content maintains all formatting, structure, and metadata
while conforming to target format standards.
"""

import pytest
from hypothesis import given, strategies as st, settings
import json
import re


# Test data generators
@st.composite
def block_content(draw):
    """Generate block content"""
    text = draw(st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=0,
        max_size=200
    ))
    return {'text': text}


@st.composite
def paragraph_block(draw):
    """Generate paragraph block"""
    return {
        'type': 'paragraph',
        'content': draw(block_content())
    }


@st.composite
def heading_block(draw):
    """Generate heading block"""
    level = draw(st.integers(min_value=1, max_value=6))
    text = draw(st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=1,
        max_size=100
    ))
    return {
        'type': 'heading',
        'content': {
            'text': text,
            'data': {'level': level}
        }
    }


@st.composite
def quote_block(draw):
    """Generate quote block"""
    text = draw(st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=1,
        max_size=200
    ))
    return {
        'type': 'quote',
        'content': {'text': text}
    }


@st.composite
def list_item_block(draw):
    """Generate list item block"""
    text = draw(st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=1,
        max_size=100
    ))
    ordered = draw(st.booleans())
    return {
        'type': 'listItem',
        'content': {
            'text': text,
            'data': {'ordered': ordered}
        }
    }


@st.composite
def code_block(draw):
    """Generate code block"""
    code = draw(st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=1,
        max_size=200
    ))
    language = draw(st.sampled_from(['python', 'javascript', 'html', 'css', '']))
    return {
        'type': 'codeBlock',
        'content': {
            'text': code,
            'data': {'language': language}
        }
    }


@st.composite
def image_block(draw):
    """Generate image block"""
    url = 'https://example.com/image.jpg'
    alt_text = draw(st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=1,
        max_size=100
    ))
    caption = draw(st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=0,
        max_size=100
    ))
    return {
        'type': 'image',
        'content': {
            'data': {
                'url': url,
                'altText': alt_text,
                'caption': caption
            }
        }
    }


@st.composite
def divider_block(draw):
    """Generate divider block"""
    return {
        'type': 'divider',
        'content': {'data': {'style': 'solid'}}
    }


@st.composite
def content_document(draw):
    """Generate a content document with blocks"""
    blocks = draw(st.lists(
        st.one_of(
            paragraph_block(),
            heading_block(),
            quote_block(),
            list_item_block(),
            code_block(),
            image_block(),
            divider_block()
        ),
        min_size=1,
        max_size=10
    ))
    
    metadata = {
        'title': draw(st.text(
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            min_size=1,
            max_size=100
        )),
        'author': draw(st.text(
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            min_size=1,
            max_size=50
        ))
    }
    
    return {
        'blocks': blocks,
        'metadata': metadata
    }


class TestExportFormatIntegrity:
    """
    **Feature: advanced-editor-system, Property 17: Export Format Integrity**
    
    Exported content should maintain all formatting, structure, and metadata
    while conforming to target format standards.
    """
    
    @given(content=content_document())
    @settings(max_examples=50, deadline=None)
    def test_html_export_preserves_structure(self, content):
        """
        Property: HTML export preserves all block types and structure
        """
        from export_system_validator import validate_html_export
        
        result = validate_html_export(content)
        
        # All blocks should be represented in HTML
        assert result['blocks_preserved'], \
            f"Not all blocks preserved in HTML export: {result['missing_blocks']}"
        
        # HTML should be valid
        assert result['valid_html'], \
            f"Generated HTML is not valid: {result['html_errors']}"
    
    @given(content=content_document())
    @settings(max_examples=50, deadline=None)
    def test_markdown_export_preserves_content(self, content):
        """
        Property: Markdown export preserves all text content
        """
        from export_system_validator import validate_markdown_export
        
        result = validate_markdown_export(content)
        
        # All text content should be present
        assert result['content_preserved'], \
            f"Text content not preserved in Markdown: {result['missing_content']}"
        
        # Markdown should be valid
        assert result['valid_markdown'], \
            f"Generated Markdown is not valid: {result['markdown_errors']}"
    
    @given(content=content_document())
    @settings(max_examples=50, deadline=None)
    def test_json_export_preserves_everything(self, content):
        """
        Property: JSON export preserves complete document structure
        """
        from export_system_validator import validate_json_export
        
        result = validate_json_export(content)
        
        # JSON should be parseable
        assert result['valid_json'], \
            f"Generated JSON is not valid: {result['json_error']}"
        
        # All data should be preserved
        assert result['data_preserved'], \
            f"Data not fully preserved in JSON: {result['differences']}"
    
    @given(content=content_document())
    @settings(max_examples=50, deadline=None)
    def test_metadata_preservation(self, content):
        """
        Property: Metadata is preserved in all export formats
        """
        from export_system_validator import validate_metadata_preservation
        
        result = validate_metadata_preservation(content)
        
        # Metadata should be present in all formats
        assert result['html_has_metadata'], \
            "Metadata not preserved in HTML export"
        assert result['markdown_has_metadata'], \
            "Metadata not preserved in Markdown export"
        assert result['json_has_metadata'], \
            "Metadata not preserved in JSON export"
    
    @given(
        content=content_document(),
        format_type=st.sampled_from(['html', 'markdown', 'json'])
    )
    @settings(max_examples=50, deadline=None)
    def test_export_format_standards_compliance(self, content, format_type):
        """
        Property: Exported content conforms to format standards
        """
        from export_system_validator import validate_format_compliance
        
        result = validate_format_compliance(content, format_type)
        
        # Format should comply with standards
        assert result['compliant'], \
            f"{format_type.upper()} export does not comply with standards: {result['violations']}"
    
    @given(content=content_document())
    @settings(max_examples=50, deadline=None)
    def test_special_characters_handling(self, content):
        """
        Property: Special characters are properly escaped in all formats
        """
        from export_system_validator import validate_special_characters
        
        result = validate_special_characters(content)
        
        # Special characters should be properly handled
        assert result['html_escaped'], \
            f"HTML special characters not properly escaped: {result['html_issues']}"
        assert result['markdown_escaped'], \
            f"Markdown special characters not properly escaped: {result['markdown_issues']}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
