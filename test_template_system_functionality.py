"""
Property-Based Tests for Template System
Feature: advanced-editor-system
Property 18: Template System Functionality

Tests that template operations handle templates correctly with proper
placeholder population and update propagation.
"""

import pytest
from hypothesis import given, strategies as st, settings
import json


# Test data generators
@st.composite
def template_variable(draw):
    """Generate template variable definition"""
    name = draw(st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),  # a-z
        min_size=3,
        max_size=20
    ))
    var_type = draw(st.sampled_from(['text', 'number', 'boolean']))
    required = draw(st.booleans())
    
    return {
        'name': name,
        'type': var_type,
        'required': required
    }


@st.composite
def template_block(draw, variables):
    """Generate template block with variable placeholders"""
    block_type = draw(st.sampled_from(['paragraph', 'heading', 'quote']))
    
    # Create text with variable placeholders
    if variables:
        var_name = draw(st.sampled_from([v['name'] for v in variables]))
        text = f'{{{{{var_name}}}}}'
    else:
        text = draw(st.text(
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            min_size=1,
            max_size=100
        ))
    
    block = {
        'type': block_type,
        'content': {'text': text}
    }
    
    if block_type == 'heading':
        block['content']['data'] = {'level': draw(st.integers(min_value=1, max_value=6))}
    
    return block


@st.composite
def template_definition(draw):
    """Generate template definition"""
    name = draw(st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=3,
        max_size=50
    ))
    description = draw(st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=0,
        max_size=200
    ))
    category = draw(st.sampled_from(['blog', 'educational', 'review', 'news', 'general']))
    
    # Generate variables first
    variables = draw(st.lists(template_variable(), min_size=1, max_size=5))
    
    # Generate blocks that use these variables
    blocks = draw(st.lists(
        template_block(variables),
        min_size=1,
        max_size=5
    ))
    
    return {
        'name': name,
        'description': description,
        'category': category,
        'blocks': blocks,
        'variables': variables
    }


@st.composite
def variable_values(draw, template):
    """Generate variable values for a template"""
    values = {}
    
    for var in template['variables']:
        if var['required'] or draw(st.booleans()):
            if var['type'] == 'text':
                values[var['name']] = draw(st.text(
                    alphabet=st.characters(min_codepoint=32, max_codepoint=126),
                    min_size=1,
                    max_size=100
                ))
            elif var['type'] == 'number':
                values[var['name']] = str(draw(st.integers(min_value=0, max_value=1000)))
            elif var['type'] == 'boolean':
                values[var['name']] = str(draw(st.booleans()))
    
    return values


class TestTemplateSystemFunctionality:
    """
    **Feature: advanced-editor-system, Property 18: Template System Functionality**
    
    Template operations should handle templates correctly with proper
    placeholder population and update propagation.
    """
    
    @given(template=template_definition())
    @settings(max_examples=50, deadline=None)
    def test_template_creation_and_storage(self, template):
        """
        Property: Templates can be created and stored correctly
        """
        from template_system_validator import validate_template_creation
        
        result = validate_template_creation(template)
        
        # Template should be created successfully
        assert result['created'], \
            f"Template creation failed: {result['error']}"
        
        # Template should be retrievable
        assert result['retrievable'], \
            "Created template cannot be retrieved"
        
        # Template data should match
        assert result['data_matches'], \
            f"Template data mismatch: {result['differences']}"
    
    @given(template=template_definition())
    @settings(max_examples=50, deadline=None)
    def test_template_variable_population(self, template):
        """
        Property: Template variables are correctly populated with values
        """
        from template_system_validator import validate_variable_population
        
        # Find which variables are actually used in blocks
        used_vars = set()
        for block in template['blocks']:
            text = block.get('content', {}).get('text', '')
            import re
            matches = re.findall(r'\{\{(\w+)\}\}', text)
            used_vars.update(matches)
        
        # Provide values for all used variables
        values = {}
        for var in template['variables']:
            if var['name'] in used_vars:
                values[var['name']] = f"test_{var['name']}_value"
        
        # If no variables are used, skip this test
        if not used_vars:
            return
        
        result = validate_variable_population(template, values)
        
        # All provided variables should be populated
        assert result['all_populated'], \
            f"Not all variables populated: {result['unpopulated']}"
        
        # Values should appear in content
        assert result['values_present'], \
            f"Variable values not present in content: {result['missing_values']}"
    
    @given(template=template_definition())
    @settings(max_examples=50, deadline=None)
    def test_required_variable_validation(self, template):
        """
        Property: Required variables must be provided
        """
        from template_system_validator import validate_required_variables
        
        # Try to apply template without required variables
        result = validate_required_variables(template, {})
        
        required_vars = [v['name'] for v in template['variables'] if v['required']]
        
        if required_vars:
            # Should fail if required variables are missing
            assert not result['valid'], \
                "Template application should fail without required variables"
            
            # Error should mention missing variables
            assert result['mentions_missing'], \
                "Error message should mention missing required variables"
        else:
            # Should succeed if no required variables
            assert result['valid'], \
                "Template application should succeed when no required variables"
    
    @given(template=template_definition())
    @settings(max_examples=50, deadline=None)
    def test_template_categories(self, template):
        """
        Property: Templates are correctly categorized
        """
        from template_system_validator import validate_template_categories
        
        result = validate_template_categories(template)
        
        # Template should have a category
        assert result['has_category'], \
            "Template should have a category"
        
        # Template should be findable by category
        assert result['findable_by_category'], \
            f"Template not findable by category: {template['category']}"
    
    @given(template=template_definition())
    @settings(max_examples=50, deadline=None)
    def test_template_search(self, template):
        """
        Property: Templates are searchable by name and description
        """
        from template_system_validator import validate_template_search
        
        result = validate_template_search(template)
        
        # Template should be findable by name
        if template['name'] and template['name'].strip():
            assert result['findable_by_name'], \
                "Template should be findable by name"
        
        # Template should be findable by description keywords
        if template['description'] and template['description'].strip():
            assert result['findable_by_description'], \
                "Template should be findable by description"
    
    @given(template=template_definition())
    @settings(max_examples=50, deadline=None)
    def test_template_export_import(self, template):
        """
        Property: Templates can be exported and imported without data loss
        """
        from template_system_validator import validate_template_export_import
        
        result = validate_template_export_import(template)
        
        # Export should succeed
        assert result['export_success'], \
            f"Template export failed: {result['export_error']}"
        
        # Import should succeed
        assert result['import_success'], \
            f"Template import failed: {result['import_error']}"
        
        # Data should be preserved
        assert result['data_preserved'], \
            f"Template data not preserved: {result['differences']}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
