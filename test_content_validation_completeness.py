"""
Property-Based Tests for Content Validator
Feature: advanced-editor-system
Property 19: Content Migration Preservation
Property 20: Content Validation Completeness

Tests that content migration preserves all content, metadata, and formatting,
and that content validation checks all required elements with specific error messages.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume


# Test data generators
@st.composite
def html_paragraph(draw):
    """Generate HTML paragraph"""
    text = draw(st.text(
        alphabet=st.characters(min_codepoint=65, max_codepoint=122),  # A-Z, a-z
        min_size=1,
        max_size=100
    ))
    return f'<p>{text}</p>'


@st.composite
def html_heading(draw):
    """Generate HTML heading"""
    level = draw(st.integers(min_value=1, max_value=6))
    text = draw(st.text(
        alphabet=st.characters(min_codepoint=65, max_codepoint=122),  # A-Z, a-z
        min_size=1,
        max_size=100
    ))
    return f'<h{level}>{text}</h{level}>'


@st.composite
def html_list(draw):
    """Generate HTML list"""
    ordered = draw(st.booleans())
    tag = 'ol' if ordered else 'ul'
    items = draw(st.lists(
        st.text(
            alphabet=st.characters(min_codepoint=65, max_codepoint=122),  # A-Z, a-z
            min_size=1,
            max_size=50
        ),
        min_size=1,
        max_size=5
    ))
    html = f'<{tag}>'
    for item in items:
        html += f'<li>{item}</li>'
    html += f'</{tag}>'
    return html


@st.composite
def html_image(draw):
    """Generate HTML image"""
    has_alt = draw(st.booleans())
    alt = draw(st.text(
        alphabet=st.characters(min_codepoint=65, max_codepoint=122),  # A-Z, a-z
        min_size=1,
        max_size=50
    )) if has_alt else ''
    
    if has_alt:
        return f'<img src="https://example.com/image.jpg" alt="{alt}" />'
    else:
        return '<img src="https://example.com/image.jpg" />'


@st.composite
def html_document(draw):
    """Generate HTML document"""
    elements = draw(st.lists(
        st.one_of(
            html_paragraph(),
            html_heading(),
            html_list(),
            html_image()
        ),
        min_size=1,
        max_size=10
    ))
    return '\n'.join(elements)


@st.composite
def content_block(draw):
    """Generate content block"""
    block_type = draw(st.sampled_from(['paragraph', 'heading', 'image']))
    
    if block_type == 'paragraph':
        return {
            'type': 'paragraph',
            'content': {
                'text': draw(st.text(
                    alphabet=st.characters(min_codepoint=32, max_codepoint=126),
                    min_size=1,
                    max_size=100
                ))
            }
        }
    elif block_type == 'heading':
        return {
            'type': 'heading',
            'content': {
                'text': draw(st.text(
                    alphabet=st.characters(min_codepoint=32, max_codepoint=126),
                    min_size=1,
                    max_size=100
                )),
                'data': {'level': draw(st.integers(min_value=1, max_value=6))}
            }
        }
    else:  # image
        has_alt = draw(st.booleans())
        return {
            'type': 'image',
            'content': {
                'data': {
                    'url': 'https://example.com/image.jpg',
                    'altText': draw(st.text(
                        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
                        min_size=1,
                        max_size=50
                    )) if has_alt else ''
                }
            }
        }


@st.composite
def content_document(draw):
    """Generate content document"""
    blocks = draw(st.lists(content_block(), min_size=1, max_size=10))
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


class TestContentMigrationPreservation:
    """
    **Feature: advanced-editor-system, Property 19: Content Migration Preservation**
    
    Content migration should preserve all content, metadata, and formatting.
    """
    
    @given(html=html_document())
    @settings(max_examples=50, deadline=None)
    def test_html_to_blocks_preserves_content(self, html):
        """
        Property: HTML to blocks migration preserves all text content
        """
        from content_validator_helper import validate_html_migration
        
        result = validate_html_migration(html)
        
        # Migration should succeed
        assert result['success'], \
            f"HTML migration failed: {result['errors']}"
        
        # All text content should be preserved
        assert result['content_preserved'], \
            f"Text content not preserved: {result['missing_content']}"
    
    @given(html=html_document())
    @settings(max_examples=50, deadline=None)
    def test_html_to_blocks_preserves_structure(self, html):
        """
        Property: HTML to blocks migration preserves document structure
        """
        from content_validator_helper import validate_structure_preservation
        
        result = validate_structure_preservation(html)
        
        # Block types should match HTML elements
        assert result['structure_preserved'], \
            f"Structure not preserved: {result['mismatches']}"
    
    @given(html=html_document())
    @settings(max_examples=50, deadline=None)
    def test_html_migration_error_reporting(self, html):
        """
        Property: Migration errors are clearly reported
        """
        from content_validator_helper import validate_error_reporting
        
        result = validate_error_reporting(html)
        
        # Errors should be reported if any
        if not result['success']:
            assert result['has_error_messages'], \
                "Migration failures should include error messages"


class TestContentValidationCompleteness:
    """
    **Feature: advanced-editor-system, Property 20: Content Validation Completeness**
    
    Content validation should check all required elements and provide
    specific error messages.
    """
    
    @given(content=content_document())
    @settings(max_examples=50, deadline=None)
    def test_image_alt_text_validation(self, content):
        """
        Property: Images without alt text are flagged as errors
        """
        from content_validator_helper import validate_image_alt_text
        
        result = validate_image_alt_text(content)
        
        # Check if validation catches missing alt text
        images_without_alt = [
            i for i, block in enumerate(content['blocks'])
            if block['type'] == 'image' and not block['content']['data'].get('altText')
        ]
        
        if images_without_alt:
            assert not result['valid'], \
                "Validation should fail for images without alt text"
            assert result['has_alt_text_errors'], \
                "Validation should report alt text errors"
        else:
            # If all images have alt text, validation should pass
            assert not result['has_alt_text_errors'], \
                "Validation should not report alt text errors when all images have alt text"
    
    @given(content=content_document())
    @settings(max_examples=50, deadline=None)
    def test_heading_structure_validation(self, content):
        """
        Property: Documents without H1 heading are flagged as warnings
        """
        from content_validator_helper import validate_heading_structure
        
        result = validate_heading_structure(content)
        
        # Check if document has H1
        has_h1 = any(
            block['type'] == 'heading' and block['content']['data'].get('level') == 1
            for block in content['blocks']
        )
        
        if not has_h1:
            assert result['has_h1_warning'], \
                "Validation should warn about missing H1 heading"
    
    @given(content=content_document())
    @settings(max_examples=50, deadline=None)
    def test_validation_error_specificity(self, content):
        """
        Property: Validation errors include specific details
        """
        from content_validator_helper import validate_error_specificity
        
        result = validate_error_specificity(content)
        
        # All errors should have specific messages
        if result['has_errors']:
            assert result['errors_have_messages'], \
                "All validation errors should have specific messages"
            assert result['errors_have_locations'], \
                "All validation errors should include block locations"
    
    @given(content=content_document())
    @settings(max_examples=50, deadline=None)
    def test_validation_rule_customization(self, content):
        """
        Property: Custom validation rules can be added and applied
        """
        from content_validator_helper import validate_custom_rules
        
        result = validate_custom_rules(content)
        
        # Custom rules should be applied
        assert result['custom_rule_applied'], \
            "Custom validation rules should be applied"
    
    @given(content=content_document())
    @settings(max_examples=50, deadline=None)
    def test_pre_publication_check_completeness(self, content):
        """
        Property: Pre-publication check validates all aspects
        """
        from content_validator_helper import validate_pre_publication_check
        
        result = validate_pre_publication_check(content)
        
        # Check should include all aspects
        assert result['has_validation'], \
            "Pre-publication check should include content validation"
        assert result['has_seo_check'], \
            "Pre-publication check should include SEO validation"
        assert result['has_accessibility_check'], \
            "Pre-publication check should include accessibility validation"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
