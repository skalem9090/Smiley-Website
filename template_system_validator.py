"""
Template System Validator
Validates template functionality for property-based tests
"""

import json
import re


class TemplateSystem:
    """Simple template system for validation"""
    def __init__(self):
        self.templates = {}
    
    def create_template(self, template):
        """Create a template"""
        template_id = template.get('id', f"template-{len(self.templates)}")
        self.templates[template_id] = {
            'id': template_id,
            'name': template.get('name', ''),
            'description': template.get('description', ''),
            'category': template.get('category', 'general'),
            'blocks': template.get('blocks', []),
            'variables': template.get('variables', [])
        }
        return template_id
    
    def get_template(self, template_id):
        """Get a template by ID"""
        return self.templates.get(template_id)
    
    def get_templates_by_category(self, category):
        """Get templates by category"""
        return [t for t in self.templates.values() if t['category'] == category]
    
    def search_templates(self, query):
        """Search templates"""
        query_lower = query.lower()
        results = []
        
        for template in self.templates.values():
            if (query_lower in template['name'].lower() or
                query_lower in template['description'].lower()):
                results.append(template)
        
        return results
    
    def apply_template(self, template_id, values):
        """Apply template with values"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Check required variables
        required_vars = [v['name'] for v in template['variables'] if v['required']]
        missing = [v for v in required_vars if v not in values]
        
        if missing:
            raise ValueError(f"Missing required variables: {', '.join(missing)}")
        
        # Clone blocks and populate variables
        blocks = json.loads(json.dumps(template['blocks']))
        
        for block in blocks:
            if 'content' in block and 'text' in block['content']:
                text = block['content']['text']
                # Replace {{variable}} with values
                for var_name, var_value in values.items():
                    text = text.replace(f'{{{{{var_name}}}}}', str(var_value))
                block['content']['text'] = text
        
        return {
            'blocks': blocks,
            'metadata': {
                'templateId': template_id,
                'templateName': template['name']
            }
        }
    
    def export_template(self, template_id):
        """Export template as JSON"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        return json.dumps(template, indent=2)
    
    def import_template(self, json_str):
        """Import template from JSON"""
        template = json.loads(json_str)
        return self.create_template(template)


def validate_template_creation(template):
    """Validate template creation"""
    system = TemplateSystem()
    
    try:
        template_id = system.create_template(template)
        created = True
        error = None
    except Exception as e:
        created = False
        error = str(e)
        template_id = None
    
    # Check if retrievable
    retrievable = False
    data_matches = False
    differences = []
    
    if created:
        retrieved = system.get_template(template_id)
        retrievable = retrieved is not None
        
        if retrievable:
            # Check data matches
            for key in ['name', 'description', 'category']:
                if template.get(key) != retrieved.get(key):
                    differences.append(f"{key}: {template.get(key)} != {retrieved.get(key)}")
            
            data_matches = len(differences) == 0
    
    return {
        'created': created,
        'error': error,
        'retrievable': retrievable,
        'data_matches': data_matches,
        'differences': differences
    }


def validate_variable_population(template, values):
    """Validate variable population"""
    system = TemplateSystem()
    template_id = system.create_template(template)
    
    # Add all required variables to values if not present
    all_values = dict(values)
    for var in template['variables']:
        if var['required'] and var['name'] not in all_values:
            all_values[var['name']] = f"required_{var['name']}_value"
    
    try:
        result = system.apply_template(template_id, all_values)
        blocks = result['blocks']
        
        # Check if variables that were originally provided are populated
        unpopulated = []
        for var_name in values.keys():  # Only check originally provided values
            # Check if placeholder still exists
            for block in blocks:
                text = block.get('content', {}).get('text', '')
                if f'{{{{{var_name}}}}}' in text:
                    unpopulated.append(var_name)
                    break
        
        # Check if originally provided values are present
        missing_values = []
        for var_name, var_value in values.items():  # Only check originally provided values
            found = False
            for block in blocks:
                text = block.get('content', {}).get('text', '')
                if str(var_value) in text:
                    found = True
                    break
            if not found:
                missing_values.append(var_name)
        
        return {
            'all_populated': len(unpopulated) == 0,
            'unpopulated': unpopulated,
            'values_present': len(missing_values) == 0,
            'missing_values': missing_values
        }
    except Exception as e:
        return {
            'all_populated': False,
            'unpopulated': list(values.keys()),
            'values_present': False,
            'missing_values': list(values.keys())
        }


def validate_required_variables(template, values):
    """Validate required variable checking"""
    system = TemplateSystem()
    template_id = system.create_template(template)
    
    try:
        system.apply_template(template_id, values)
        valid = True
        error = None
    except Exception as e:
        valid = False
        error = str(e)
    
    # Check if error mentions missing variables
    mentions_missing = False
    if error:
        required_vars = [v['name'] for v in template['variables'] if v['required']]
        mentions_missing = any(var in error for var in required_vars) or 'required' in error.lower()
    
    return {
        'valid': valid,
        'error': error,
        'mentions_missing': mentions_missing
    }


def validate_template_categories(template):
    """Validate template categorization"""
    system = TemplateSystem()
    template_id = system.create_template(template)
    
    retrieved = system.get_template(template_id)
    has_category = 'category' in retrieved and retrieved['category']
    
    # Check if findable by category
    category_templates = system.get_templates_by_category(template['category'])
    findable_by_category = any(t['id'] == template_id for t in category_templates)
    
    return {
        'has_category': has_category,
        'findable_by_category': findable_by_category
    }


def validate_template_search(template):
    """Validate template search"""
    system = TemplateSystem()
    template_id = system.create_template(template)
    
    # Search by name
    findable_by_name = False
    if template['name']:
        # Search with part of the name
        search_term = template['name'][:min(5, len(template['name']))]
        results = system.search_templates(search_term)
        findable_by_name = any(t['id'] == template_id for t in results)
    
    # Search by description
    findable_by_description = False
    if template['description']:
        # Search with part of the description
        words = template['description'].split()
        if words:
            search_term = words[0]
            results = system.search_templates(search_term)
            findable_by_description = any(t['id'] == template_id for t in results)
    
    return {
        'findable_by_name': findable_by_name,
        'findable_by_description': findable_by_description
    }


def validate_template_export_import(template):
    """Validate template export/import"""
    system = TemplateSystem()
    template_id = system.create_template(template)
    
    # Export
    try:
        exported = system.export_template(template_id)
        export_success = True
        export_error = None
    except Exception as e:
        export_success = False
        export_error = str(e)
        exported = None
    
    # Import
    import_success = False
    import_error = None
    imported_id = None
    
    if export_success:
        try:
            imported_id = system.import_template(exported)
            import_success = True
        except Exception as e:
            import_error = str(e)
    
    # Check data preservation
    data_preserved = False
    differences = []
    
    if import_success:
        original = system.get_template(template_id)
        imported = system.get_template(imported_id)
        
        for key in ['name', 'description', 'category']:
            if original.get(key) != imported.get(key):
                differences.append(f"{key}: {original.get(key)} != {imported.get(key)}")
        
        data_preserved = len(differences) == 0
    
    return {
        'export_success': export_success,
        'export_error': export_error,
        'import_success': import_success,
        'import_error': import_error,
        'data_preserved': data_preserved,
        'differences': differences
    }
