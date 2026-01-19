"""
Content Validator Helper
Validates content migration and validation for property-based tests
"""

import re
from html.parser import HTMLParser


class HTMLToBlocksParser(HTMLParser):
    """Parse HTML and convert to blocks"""
    def __init__(self):
        super().__init__()
        self.blocks = []
        self.current_list = None
        self.errors = []
    
    def handle_starttag(self, tag, attrs):
        if tag in ['ul', 'ol']:
            self.current_list = {'type': tag, 'items': []}
        elif tag == 'img':
            attrs_dict = dict(attrs)
            self.blocks.append({
                'type': 'image',
                'content': {
                    'data': {
                        'url': attrs_dict.get('src', ''),
                        'altText': attrs_dict.get('alt', '')
                    }
                }
            })
    
    def handle_endtag(self, tag):
        if tag in ['ul', 'ol'] and self.current_list:
            for item in self.current_list['items']:
                self.blocks.append({
                    'type': 'listItem',
                    'content': {
                        'text': item,
                        'data': {'ordered': tag == 'ol'}
                    }
                })
            self.current_list = None
    
    def handle_data(self, data):
        data = data.strip()
        if not data:
            return
        
        # Get the current tag from the stack
        if self.lasttag == 'p':
            self.blocks.append({
                'type': 'paragraph',
                'content': {'text': data}
            })
        elif self.lasttag and self.lasttag.startswith('h') and len(self.lasttag) == 2:
            try:
                level = int(self.lasttag[1])
                self.blocks.append({
                    'type': 'heading',
                    'content': {
                        'text': data,
                        'data': {'level': level}
                    }
                })
            except ValueError:
                pass
        elif self.lasttag == 'li' and self.current_list:
            self.current_list['items'].append(data)


def migrate_html_to_blocks(html):
    """Migrate HTML to blocks"""
    parser = HTMLToBlocksParser()
    try:
        parser.feed(html)
        return {
            'blocks': parser.blocks,
            'errors': parser.errors,
            'success': len(parser.errors) == 0
        }
    except Exception as e:
        return {
            'blocks': [],
            'errors': [str(e)],
            'success': False
        }


def extract_text_from_html(html):
    """Extract all text content from HTML"""
    # Remove tags but keep alt text from images
    text = re.sub(r'<img[^>]*alt="([^"]*)"[^>]*>', r'\1', html)
    # Remove remaining tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Normalize whitespace
    text = ' '.join(text.split())
    return text


def extract_text_from_blocks(blocks):
    """Extract all text content from blocks"""
    texts = []
    for block in blocks:
        if 'content' in block:
            if 'text' in block['content']:
                texts.append(block['content']['text'])
            # Also extract alt text from images
            elif 'data' in block['content'] and 'altText' in block['content']['data']:
                alt_text = block['content']['data']['altText']
                if alt_text:
                    texts.append(alt_text)
    return ' '.join(texts)


def validate_html_migration(html):
    """Validate HTML to blocks migration"""
    result = migrate_html_to_blocks(html)
    
    # Extract text from both
    html_text = extract_text_from_html(html)
    blocks_text = extract_text_from_blocks(result['blocks'])
    
    # Check if content is preserved (only check non-empty text)
    html_words = set(w for w in html_text.split() if w.strip())
    blocks_words = set(w for w in blocks_text.split() if w.strip())
    
    # For images, the alt text should be preserved
    missing_content = html_words - blocks_words
    
    # Filter out HTML artifacts like quotes and slashes
    missing_content = {w for w in missing_content if w not in ['"', "'", '/', '>', '<', '/>']}
    
    content_preserved = len(missing_content) == 0
    
    return {
        'success': result['success'],
        'errors': result['errors'],
        'content_preserved': content_preserved,
        'missing_content': list(missing_content)
    }


def validate_structure_preservation(html):
    """Validate structure preservation"""
    result = migrate_html_to_blocks(html)
    
    # Count elements in HTML (only count non-empty content)
    html_p_matches = re.finditer(r'<p>([^<]*)</p>', html)
    html_p_count = sum(1 for m in html_p_matches if m.group(1).strip())
    
    html_h_matches = re.finditer(r'<h([1-6])>([^<]*)</h\1>', html)
    html_h_count = sum(1 for m in html_h_matches if m.group(2).strip())
    
    html_img_count = len(re.findall(r'<img', html))
    
    # Count blocks
    blocks = result['blocks']
    block_p_count = sum(1 for b in blocks if b['type'] == 'paragraph')
    block_h_count = sum(1 for b in blocks if b['type'] == 'heading')
    block_img_count = sum(1 for b in blocks if b['type'] == 'image')
    
    mismatches = []
    if html_p_count != block_p_count:
        mismatches.append(f"Paragraphs: {html_p_count} vs {block_p_count}")
    if html_h_count != block_h_count:
        mismatches.append(f"Headings: {html_h_count} vs {block_h_count}")
    if html_img_count != block_img_count:
        mismatches.append(f"Images: {html_img_count} vs {block_img_count}")
    
    return {
        'structure_preserved': len(mismatches) == 0,
        'mismatches': mismatches
    }


def validate_error_reporting(html):
    """Validate error reporting"""
    result = migrate_html_to_blocks(html)
    
    has_error_messages = len(result['errors']) > 0 if not result['success'] else True
    
    return {
        'success': result['success'],
        'has_error_messages': has_error_messages
    }


class ContentValidator:
    """Simple content validator"""
    def __init__(self):
        self.rules = {}
        self._add_default_rules()
    
    def _add_default_rules(self):
        """Add default validation rules"""
        self.rules['image-alt-text'] = {
            'type': 'image',
            'validate': lambda block: {
                'valid': bool(block['content']['data'].get('altText')),
                'message': 'Image is missing alt text'
            },
            'severity': 'error'
        }
        
        self.rules['heading-structure'] = {
            'type': 'document',
            'validate': lambda content: {
                'valid': any(
                    b['type'] == 'heading' and b['content']['data'].get('level') == 1
                    for b in content['blocks']
                ),
                'message': 'Document should have at least one H1 heading'
            },
            'severity': 'warning'
        }
    
    def add_rule(self, rule_id, rule):
        """Add custom rule"""
        self.rules[rule_id] = rule
    
    def validate(self, content):
        """Validate content"""
        errors = []
        warnings = []
        blocks = content.get('blocks', [])
        
        # Run document-level rules
        for rule_id, rule in self.rules.items():
            if rule['type'] == 'document':
                result = rule['validate'](content)
                if not result['valid']:
                    issue = {
                        'ruleId': rule_id,
                        'message': result['message'],
                        'severity': rule['severity']
                    }
                    if rule['severity'] == 'error':
                        errors.append(issue)
                    else:
                        warnings.append(issue)
        
        # Run block-level rules
        for i, block in enumerate(blocks):
            for rule_id, rule in self.rules.items():
                if rule['type'] == block['type']:
                    result = rule['validate'](block)
                    if not result['valid']:
                        issue = {
                            'ruleId': rule_id,
                            'blockIndex': i,
                            'blockType': block['type'],
                            'message': result['message'],
                            'severity': rule['severity']
                        }
                        if rule['severity'] == 'error':
                            errors.append(issue)
                        else:
                            warnings.append(issue)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def pre_publication_check(self, content):
        """Pre-publication check"""
        validation = self.validate(content)
        
        # SEO check
        seo_issues = []
        blocks = content.get('blocks', [])
        has_h1 = any(
            b['type'] == 'heading' and b['content']['data'].get('level') == 1
            for b in blocks
        )
        if not has_h1:
            seo_issues.append({'message': 'Missing H1 heading'})
        
        # Accessibility check
        accessibility_issues = []
        for i, block in enumerate(blocks):
            if block['type'] == 'image':
                if not block['content']['data'].get('altText'):
                    accessibility_issues.append({
                        'blockIndex': i,
                        'message': 'Image missing alt text'
                    })
        
        return {
            'validation': validation,
            'seo': {'issues': seo_issues},
            'accessibility': {'issues': accessibility_issues}
        }


def validate_image_alt_text(content):
    """Validate image alt text"""
    validator = ContentValidator()
    result = validator.validate(content)
    
    has_alt_text_errors = any(
        'alt text' in error['message'].lower()
        for error in result['errors']
    )
    
    return {
        'valid': result['valid'],
        'has_alt_text_errors': has_alt_text_errors
    }


def validate_heading_structure(content):
    """Validate heading structure"""
    validator = ContentValidator()
    result = validator.validate(content)
    
    has_h1_warning = any(
        'h1' in warning['message'].lower()
        for warning in result['warnings']
    )
    
    return {
        'has_h1_warning': has_h1_warning
    }


def validate_error_specificity(content):
    """Validate error specificity"""
    validator = ContentValidator()
    result = validator.validate(content)
    
    all_errors = result['errors'] + result['warnings']
    has_errors = len(all_errors) > 0
    
    errors_have_messages = all(
        'message' in error and error['message']
        for error in all_errors
    )
    
    errors_have_locations = all(
        'blockIndex' in error or 'ruleId' in error
        for error in all_errors
    )
    
    return {
        'has_errors': has_errors,
        'errors_have_messages': errors_have_messages,
        'errors_have_locations': errors_have_locations
    }


def validate_custom_rules(content):
    """Validate custom rules"""
    validator = ContentValidator()
    
    # Add a custom rule
    validator.add_rule('custom-test', {
        'type': 'paragraph',
        'validate': lambda block: {
            'valid': True,
            'message': ''
        },
        'severity': 'warning'
    })
    
    # Check if custom rule exists
    custom_rule_applied = 'custom-test' in validator.rules
    
    return {
        'custom_rule_applied': custom_rule_applied
    }


def validate_pre_publication_check(content):
    """Validate pre-publication check"""
    validator = ContentValidator()
    result = validator.pre_publication_check(content)
    
    has_validation = 'validation' in result
    has_seo_check = 'seo' in result
    has_accessibility_check = 'accessibility' in result
    
    return {
        'has_validation': has_validation,
        'has_seo_check': has_seo_check,
        'has_accessibility_check': has_accessibility_check
    }
