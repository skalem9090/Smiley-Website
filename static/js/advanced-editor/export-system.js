/**
 * Advanced Editor System - Export System
 * 
 * Exports content to multiple formats:
 * - HTML with clean, semantic markup
 * - Markdown with standard compliance
 * - JSON for API integration
 * - Preserves metadata in all formats
 * 
 * Validates Property 17: Export Format Integrity
 */

(function(window) {
    'use strict';

    /**
     * Export System
     * Handles content export to various formats
     */
    class ExportSystem {
        constructor(config = {}) {
            this.config = {
                htmlIndent: config.htmlIndent || 2,
                markdownLineWidth: config.markdownLineWidth || 80,
                includeMetadata: config.includeMetadata !== false,
                ...config
            };
        }

        /**
         * Export content to specified format
         * @param {Object} content - Content to export
         * @param {string} format - Export format (html, markdown, json)
         * @param {Object} options - Export options
         * @returns {string} Exported content
         */
        export(content, format, options = {}) {
            const mergedOptions = { ...this.config, ...options };
            
            switch (format.toLowerCase()) {
                case 'html':
                    return this.exportToHTML(content, mergedOptions);
                case 'markdown':
                case 'md':
                    return this.exportToMarkdown(content, mergedOptions);
                case 'json':
                    return this.exportToJSON(content, mergedOptions);
                default:
                    throw new Error(`Unsupported export format: ${format}`);
            }
        }

        /**
         * Export to HTML
         * @param {Object} content - Content to export
         * @param {Object} options - Export options
         * @returns {string} HTML content
         */
        exportToHTML(content, options = {}) {
            const blocks = content.blocks || [];
            const metadata = content.metadata || {};
            
            let html = '';
            
            // Add metadata as HTML comments if enabled
            if (options.includeMetadata && Object.keys(metadata).length > 0) {
                html += '<!-- Document Metadata\n';
                html += JSON.stringify(metadata, null, 2);
                html += '\n-->\n\n';
            }
            
            // Convert blocks to HTML
            blocks.forEach(block => {
                html += this.blockToHTML(block, options) + '\n';
            });
            
            return html.trim();
        }

        /**
         * Convert block to HTML
         * @param {Object} block - Block to convert
         * @param {Object} options - Conversion options
         * @returns {string} HTML string
         */
        blockToHTML(block, options = {}) {
            const indent = ' '.repeat(options.htmlIndent || 2);
            
            switch (block.type) {
                case 'paragraph':
                    return `<p>${this.escapeHTML(block.content.text || '')}</p>`;
                
                case 'heading':
                    const level = block.content.data?.level || 1;
                    return `<h${level}>${this.escapeHTML(block.content.text || '')}</h${level}>`;
                
                case 'quote':
                    return `<blockquote>\n${indent}<p>${this.escapeHTML(block.content.text || '')}</p>\n</blockquote>`;
                
                case 'listItem':
                    const tag = block.content.data?.ordered ? 'ol' : 'ul';
                    return `<${tag}>\n${indent}<li>${this.escapeHTML(block.content.text || '')}</li>\n</${tag}>`;
                
                case 'codeBlock':
                    const language = block.content.data?.language || '';
                    const code = this.escapeHTML(block.content.text || '');
                    return `<pre><code class="language-${language}">${code}</code></pre>`;
                
                case 'image':
                    const src = block.content.data?.url || '';
                    const alt = block.content.data?.altText || '';
                    const caption = block.content.data?.caption || '';
                    let imgHTML = `<figure>\n${indent}<img src="${this.escapeHTML(src)}" alt="${this.escapeHTML(alt)}" />`;
                    if (caption) {
                        imgHTML += `\n${indent}<figcaption>${this.escapeHTML(caption)}</figcaption>`;
                    }
                    imgHTML += '\n</figure>';
                    return imgHTML;
                
                case 'divider':
                    return '<hr />';
                
                case 'table':
                    return this.tableToHTML(block, options);
                
                case 'callout':
                    const style = block.content.data?.style || 'info';
                    return `<div class="callout callout-${style}">\n${indent}<p>${this.escapeHTML(block.content.text || '')}</p>\n</div>`;
                
                default:
                    return `<div>${this.escapeHTML(block.content.text || '')}</div>`;
            }
        }

        /**
         * Convert table block to HTML
         */
        tableToHTML(block, options = {}) {
            const indent = ' '.repeat(options.htmlIndent || 2);
            const cells = block.content.data?.cells || [];
            const headers = block.content.data?.headers || false;
            
            let html = '<table>\n';
            
            cells.forEach((row, rowIndex) => {
                html += `${indent}<tr>\n`;
                row.forEach(cell => {
                    const tag = (rowIndex === 0 && headers) ? 'th' : 'td';
                    html += `${indent}${indent}<${tag}>${this.escapeHTML(cell)}</${tag}>\n`;
                });
                html += `${indent}</tr>\n`;
            });
            
            html += '</table>';
            return html;
        }

        /**
         * Export to Markdown
         * @param {Object} content - Content to export
         * @param {Object} options - Export options
         * @returns {string} Markdown content
         */
        exportToMarkdown(content, options = {}) {
            const blocks = content.blocks || [];
            const metadata = content.metadata || {};
            
            let markdown = '';
            
            // Add frontmatter if metadata exists
            if (options.includeMetadata && Object.keys(metadata).length > 0) {
                markdown += '---\n';
                Object.entries(metadata).forEach(([key, value]) => {
                    markdown += `${key}: ${JSON.stringify(value)}\n`;
                });
                markdown += '---\n\n';
            }
            
            // Convert blocks to Markdown
            blocks.forEach(block => {
                markdown += this.blockToMarkdown(block, options) + '\n\n';
            });
            
            return markdown.trim();
        }

        /**
         * Convert block to Markdown
         * @param {Object} block - Block to convert
         * @param {Object} options - Conversion options
         * @returns {string} Markdown string
         */
        blockToMarkdown(block, options = {}) {
            switch (block.type) {
                case 'paragraph':
                    return block.content.text || '';
                
                case 'heading':
                    const level = block.content.data?.level || 1;
                    return '#'.repeat(level) + ' ' + (block.content.text || '');
                
                case 'quote':
                    return '> ' + (block.content.text || '');
                
                case 'listItem':
                    const ordered = block.content.data?.ordered || false;
                    const indent = block.properties?.indentation || 0;
                    const prefix = ordered ? '1. ' : '- ';
                    return '  '.repeat(indent) + prefix + (block.content.text || '');
                
                case 'codeBlock':
                    const language = block.content.data?.language || '';
                    const code = block.content.text || '';
                    return '```' + language + '\n' + code + '\n```';
                
                case 'image':
                    const alt = block.content.data?.altText || '';
                    const url = block.content.data?.url || '';
                    return `![${alt}](${url})`;
                
                case 'divider':
                    return '---';
                
                case 'table':
                    return this.tableToMarkdown(block);
                
                case 'callout':
                    return '> **' + (block.content.data?.style || 'Note').toUpperCase() + '**: ' + (block.content.text || '');
                
                default:
                    return block.content.text || '';
            }
        }

        /**
         * Convert table block to Markdown
         */
        tableToMarkdown(block) {
            const cells = block.content.data?.cells || [];
            const headers = block.content.data?.headers || false;
            
            if (cells.length === 0) return '';
            
            let markdown = '';
            
            cells.forEach((row, rowIndex) => {
                markdown += '| ' + row.join(' | ') + ' |\n';
                
                // Add separator after first row if headers enabled
                if (rowIndex === 0 && headers) {
                    markdown += '| ' + row.map(() => '---').join(' | ') + ' |\n';
                }
            });
            
            return markdown.trim();
        }

        /**
         * Export to JSON
         * @param {Object} content - Content to export
         * @param {Object} options - Export options
         * @returns {string} JSON content
         */
        exportToJSON(content, options = {}) {
            const exportData = {
                version: '1.0',
                exportedAt: new Date().toISOString(),
                blocks: content.blocks || [],
                metadata: options.includeMetadata ? (content.metadata || {}) : undefined
            };
            
            return JSON.stringify(exportData, null, 2);
        }

        /**
         * Escape HTML special characters
         */
        escapeHTML(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        /**
         * Batch export multiple documents
         * @param {Array} documents - Array of documents to export
         * @param {string} format - Export format
         * @param {Object} options - Export options
         * @returns {Array} Array of exported content
         */
        batchExport(documents, format, options = {}) {
            return documents.map(doc => ({
                id: doc.id,
                title: doc.title,
                content: this.export(doc, format, options)
            }));
        }

        /**
         * Download exported content as file
         * @param {string} content - Content to download
         * @param {string} filename - Filename
         * @param {string} mimeType - MIME type
         */
        downloadAsFile(content, filename, mimeType = 'text/plain') {
            const blob = new Blob([content], { type: mimeType });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }
    }

    // Export to global scope
    window.ExportSystem = ExportSystem;

    console.log('Export System module loaded');

})(window);
