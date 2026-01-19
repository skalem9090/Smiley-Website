"""
Export System Validator
Validates export functionality for property-based tests
"""

import json
import re
from html.parser import HTMLParser


class HTMLValidator(HTMLParser):
    """Simple HTML validator"""
    def __init__(self):
        super().__init__()
        self.errors = []
        self.tags = []
    
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
    
    def handle_endtag(self, tag):
        if not self.tags or self.tags[-1] != tag:
            if tag not in ['img', 'hr', 'br']:  # Self-closing tags
                self.errors.append(f"Mismatched tag: {tag}")
        else:
            self.tags.pop()
    
    def error(self, message):
        self.errors.append(message)


def export_to_html(content):
    """Simulate HTML export"""
    blocks = content.get('blocks', [])
    metadata = content.get('metadata', {})
    
    html = ''
    
    # Add metadata as comment
    if metadata:
        html += '<!-- Document Metadata\n'
        html += json.dumps(metadata, indent=2)
        html += '\n-->\n\n'
    
    # Convert blocks
    for block in blocks:
        block_type = block.get('type', '')
        content_data = block.get('content', {})
        text = content_data.get('text', '')
        data = content_data.get('data', {})
        
        if block_type == 'paragraph':
            html += f'<p>{escape_html(text)}</p>\n'
        elif block_type == 'heading':
            level = data.get('level', 1)
            html += f'<h{level}>{escape_html(text)}</h{level}>\n'
        elif block_type == 'quote':
            html += f'<blockquote>\n  <p>{escape_html(text)}</p>\n</blockquote>\n'
        elif block_type == 'listItem':
            tag = 'ol' if data.get('ordered') else 'ul'
            html += f'<{tag}>\n  <li>{escape_html(text)}</li>\n</{tag}>\n'
        elif block_type == 'codeBlock':
            language = data.get('language', '')
            html += f'<pre><code class="language-{language}">{escape_html(text)}</code></pre>\n'
        elif block_type == 'image':
            url = data.get('url', '')
            alt = data.get('altText', '')
            caption = data.get('caption', '')
            html += '<figure>\n'
            html += f'  <img src="{escape_html(url)}" alt="{escape_html(alt)}" />\n'
            if caption:
                html += f'  <figcaption>{escape_html(caption)}</figcaption>\n'
            html += '</figure>\n'
        elif block_type == 'divider':
            html += '<hr />\n'
    
    return html.strip()


def export_to_markdown(content):
    """Simulate Markdown export"""
    blocks = content.get('blocks', [])
    metadata = content.get('metadata', {})
    
    markdown = ''
    
    # Add frontmatter
    if metadata:
        markdown += '---\n'
        for key, value in metadata.items():
            markdown += f'{key}: {json.dumps(value)}\n'
        markdown += '---\n\n'
    
    # Convert blocks
    for block in blocks:
        block_type = block.get('type', '')
        content_data = block.get('content', {})
        text = content_data.get('text', '')
        data = content_data.get('data', {})
        
        if block_type == 'paragraph':
            markdown += f'{text}\n\n'
        elif block_type == 'heading':
            level = data.get('level', 1)
            markdown += f'{"#" * level} {text}\n\n'
        elif block_type == 'quote':
            markdown += f'> {text}\n\n'
        elif block_type == 'listItem':
            prefix = '1. ' if data.get('ordered') else '- '
            markdown += f'{prefix}{text}\n\n'
        elif block_type == 'codeBlock':
            language = data.get('language', '')
            markdown += f'```{language}\n{text}\n```\n\n'
        elif block_type == 'image':
            url = data.get('url', '')
            alt = data.get('altText', '')
            markdown += f'![{alt}]({url})\n\n'
        elif block_type == 'divider':
            markdown += '---\n\n'
    
    return markdown.strip()


def export_to_json(content):
    """Simulate JSON export"""
    export_data = {
        'version': '1.0',
        'blocks': content.get('blocks', []),
        'metadata': content.get('metadata', {})
    }
    return json.dumps(export_data, indent=2)


def escape_html(text):
    """Escape HTML special characters"""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))


def validate_html_export(content):
    """Validate HTML export"""
    html = export_to_html(content)
    
    # Check if all blocks are represented
    blocks = content.get('blocks', [])
    missing_blocks = []
    
    for i, block in enumerate(blocks):
        block_type = block.get('type', '')
        text = block.get('content', {}).get('text', '')
        
        # Check if block content appears in HTML (for text blocks)
        if text and text not in html:
            # Check if escaped version appears
            escaped_text = escape_html(text)
            if escaped_text not in html:
                missing_blocks.append(f"Block {i} ({block_type})")
    
    # Validate HTML structure
    validator = HTMLValidator()
    try:
        validator.feed(html)
        html_errors = validator.errors
        valid_html = len(html_errors) == 0
    except Exception as e:
        html_errors = [str(e)]
        valid_html = False
    
    return {
        'blocks_preserved': len(missing_blocks) == 0,
        'missing_blocks': missing_blocks,
        'valid_html': valid_html,
        'html_errors': html_errors
    }


def validate_markdown_export(content):
    """Validate Markdown export"""
    markdown = export_to_markdown(content)
    
    # Check if all text content is preserved
    blocks = content.get('blocks', [])
    missing_content = []
    
    for i, block in enumerate(blocks):
        text = block.get('content', {}).get('text', '')
        if text and text not in markdown:
            missing_content.append(f"Block {i} text: {text[:50]}")
    
    # Basic Markdown validation
    markdown_errors = []
    
    # Check for balanced code blocks
    code_blocks = re.findall(r'```', markdown)
    if len(code_blocks) % 2 != 0:
        markdown_errors.append("Unbalanced code blocks")
    
    return {
        'content_preserved': len(missing_content) == 0,
        'missing_content': missing_content,
        'valid_markdown': len(markdown_errors) == 0,
        'markdown_errors': markdown_errors
    }


def validate_json_export(content):
    """Validate JSON export"""
    json_str = export_to_json(content)
    
    # Try to parse JSON
    try:
        parsed = json.loads(json_str)
        valid_json = True
        json_error = None
    except Exception as e:
        valid_json = False
        json_error = str(e)
        parsed = {}
    
    # Check data preservation
    differences = []
    
    if valid_json:
        # Check blocks
        original_blocks = content.get('blocks', [])
        exported_blocks = parsed.get('blocks', [])
        
        if len(original_blocks) != len(exported_blocks):
            differences.append(f"Block count mismatch: {len(original_blocks)} vs {len(exported_blocks)}")
        
        # Check metadata
        original_metadata = content.get('metadata', {})
        exported_metadata = parsed.get('metadata', {})
        
        for key in original_metadata:
            if key not in exported_metadata:
                differences.append(f"Missing metadata key: {key}")
    
    return {
        'valid_json': valid_json,
        'json_error': json_error,
        'data_preserved': len(differences) == 0,
        'differences': differences
    }


def validate_metadata_preservation(content):
    """Validate metadata preservation across formats"""
    metadata = content.get('metadata', {})
    
    html = export_to_html(content)
    markdown = export_to_markdown(content)
    json_str = export_to_json(content)
    
    # Check HTML (metadata in comments)
    html_has_metadata = False
    if metadata:
        for key in metadata:
            if key in html:
                html_has_metadata = True
                break
    else:
        html_has_metadata = True  # No metadata to preserve
    
    # Check Markdown (metadata in frontmatter)
    markdown_has_metadata = False
    if metadata:
        for key in metadata:
            if key in markdown:
                markdown_has_metadata = True
                break
    else:
        markdown_has_metadata = True
    
    # Check JSON
    json_has_metadata = False
    try:
        parsed = json.loads(json_str)
        json_has_metadata = 'metadata' in parsed
    except:
        pass
    
    return {
        'html_has_metadata': html_has_metadata,
        'markdown_has_metadata': markdown_has_metadata,
        'json_has_metadata': json_has_metadata
    }


def validate_format_compliance(content, format_type):
    """Validate format standards compliance"""
    violations = []
    
    if format_type == 'html':
        html = export_to_html(content)
        validator = HTMLValidator()
        try:
            validator.feed(html)
            violations = validator.errors
        except Exception as e:
            violations = [str(e)]
    
    elif format_type == 'markdown':
        markdown = export_to_markdown(content)
        # Check for balanced code blocks
        code_blocks = re.findall(r'```', markdown)
        if len(code_blocks) % 2 != 0:
            violations.append("Unbalanced code blocks")
    
    elif format_type == 'json':
        json_str = export_to_json(content)
        try:
            json.loads(json_str)
        except Exception as e:
            violations.append(f"Invalid JSON: {str(e)}")
    
    return {
        'compliant': len(violations) == 0,
        'violations': violations
    }


def validate_special_characters(content):
    """Validate special character handling"""
    html = export_to_html(content)
    markdown = export_to_markdown(content)
    
    html_issues = []
    markdown_issues = []
    
    # Check HTML escaping
    blocks = content.get('blocks', [])
    for block in blocks:
        text = block.get('content', {}).get('text', '')
        if '<' in text or '>' in text or '&' in text:
            # These should be escaped in HTML
            if '<' in text and '<' in html and '&lt;' not in html:
                html_issues.append("Unescaped < character")
            if '>' in text and '>' in html and '&gt;' not in html:
                html_issues.append("Unescaped > character")
    
    return {
        'html_escaped': len(html_issues) == 0,
        'html_issues': html_issues,
        'markdown_escaped': len(markdown_issues) == 0,
        'markdown_issues': markdown_issues
    }
