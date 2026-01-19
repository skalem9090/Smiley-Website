/**
 * Advanced Editor System - Content Validator
 * 
 * Validates and migrates content:
 * - HTML to blocks conversion
 * - Legacy content compatibility
 * - Content validation for links and images
 * - Custom validation rules
 * - Pre-publication content checks
 * 
 * Validates Property 19: Content Migration Preservation
 * Validates Property 20: Content Validation Completeness
 */

(function(window) {
    'use strict';

    /**
     * Content Validator
     * Validates and migrates content
     */
    class ContentValidator {
        constructor(config = {}) {
            this.config = {
                validateLinks: config.validateLinks !== false,
                validateImages: config.validateImages !== false,
                requireAltText: config.requireAltText !== false,
                minContentLength: config.minContentLength || 100,
                ...config
            };

            this.validationRules = new Map();
            this.initializeDefaultRules();
        }

        /**
         * Initialize default validation rules
         */
        initializeDefaultRules() {
            // Required alt text for images
            this.addRule('image-alt-text', {
                type: 'image',
                validate: (block) => {
                    if (!this.config.requireAltText) return { valid: true };
                    
                    const altText = block.content.data?.altText || '';
                    return {
                        valid: altText.length > 0,
                        message: 'Image is missing alt text for accessibility'
                    };
                },
                severity: 'error'
            });

            // Valid image URLs
            this.addRule('image-url', {
                type: 'image',
                validate: (block) => {
                    const url = block.content.data?.url || '';
                    return {
                        valid: url.length > 0 && this.isValidURL(url),
                        message: 'Image has invalid or missing URL'
                    };
                },
                severity: 'error'
            });

            // Minimum content length
            this.addRule('content-length', {
                type: 'document',
                validate: (content) => {
                    const text = this.extractText(content);
                    const wordCount = this.countWords(text);
                    return {
                        valid: wordCount >= this.config.minContentLength,
                        message: `Content is too short (${wordCount} words, minimum ${this.config.minContentLength})`
                    };
                },
                severity: 'warning'
            });

            // Heading structure
            this.addRule('heading-structure', {
                type: 'document',
                validate: (content) => {
                    const headings = content.blocks.filter(b => b.type === 'heading');
                    const hasH1 = headings.some(h => h.content.data?.level === 1);
                    return {
                        valid: hasH1,
                        message: 'Document should have at least one H1 heading'
                    };
                },
                severity: 'warning'
            });
        }

        /**
         * Add validation rule
         * @param {string} id - Rule ID
         * @param {Object} rule - Rule definition
         */
        addRule(id, rule) {
            this.validationRules.set(id, rule);
        }

        /**
         * Remove validation rule
         * @param {string} id - Rule ID
         */
        removeRule(id) {
            this.validationRules.delete(id);
        }

        /**
         * Validate content
         * @param {Object} content - Content to validate
         * @returns {Object} Validation results
         */
        validate(content) {
            const errors = [];
            const warnings = [];
            const blocks = content.blocks || [];

            // Run document-level rules
            this.validationRules.forEach((rule, id) => {
                if (rule.type === 'document') {
                    const result = rule.validate(content);
                    if (!result.valid) {
                        const issue = {
                            ruleId: id,
                            message: result.message,
                            severity: rule.severity
                        };
                        
                        if (rule.severity === 'error') {
                            errors.push(issue);
                        } else {
                            warnings.push(issue);
                        }
                    }
                }
            });

            // Run block-level rules
            blocks.forEach((block, index) => {
                this.validationRules.forEach((rule, id) => {
                    if (rule.type === block.type) {
                        const result = rule.validate(block);
                        if (!result.valid) {
                            const issue = {
                                ruleId: id,
                                blockIndex: index,
                                blockType: block.type,
                                message: result.message,
                                severity: rule.severity
                            };
                            
                            if (rule.severity === 'error') {
                                errors.push(issue);
                            } else {
                                warnings.push(issue);
                            }
                        }
                    }
                });
            });

            return {
                valid: errors.length === 0,
                errors: errors,
                warnings: warnings,
                summary: {
                    totalIssues: errors.length + warnings.length,
                    errorCount: errors.length,
                    warningCount: warnings.length
                }
            };
        }

        /**
         * Migrate HTML to blocks
         * @param {string} html - HTML content
         * @returns {Object} Migrated content
         */
        migrateFromHTML(html) {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const blocks = [];
            const errors = [];

            try {
                this.processHTMLNode(doc.body, blocks, errors);
            } catch (error) {
                errors.push({
                    type: 'migration',
                    message: 'Failed to parse HTML: ' + error.message
                });
            }

            return {
                blocks: blocks,
                errors: errors,
                success: errors.length === 0
            };
        }

        /**
         * Process HTML node
         * @param {Node} node - HTML node
         * @param {Array} blocks - Blocks array
         * @param {Array} errors - Errors array
         */
        processHTMLNode(node, blocks, errors) {
            if (node.nodeType === Node.TEXT_NODE) {
                const text = node.textContent.trim();
                if (text) {
                    blocks.push({
                        type: 'paragraph',
                        content: { text: text }
                    });
                }
                return;
            }

            if (node.nodeType !== Node.ELEMENT_NODE) return;

            const tagName = node.tagName.toLowerCase();

            switch (tagName) {
                case 'h1':
                case 'h2':
                case 'h3':
                case 'h4':
                case 'h5':
                case 'h6':
                    blocks.push({
                        type: 'heading',
                        content: {
                            text: node.textContent,
                            data: { level: parseInt(tagName[1]) }
                        }
                    });
                    break;

                case 'p':
                    blocks.push({
                        type: 'paragraph',
                        content: { text: node.textContent }
                    });
                    break;

                case 'blockquote':
                    blocks.push({
                        type: 'quote',
                        content: { text: node.textContent }
                    });
                    break;

                case 'ul':
                case 'ol':
                    const items = node.querySelectorAll('li');
                    items.forEach(item => {
                        blocks.push({
                            type: 'listItem',
                            content: {
                                text: item.textContent,
                                data: { ordered: tagName === 'ol' }
                            }
                        });
                    });
                    break;

                case 'pre':
                    const code = node.querySelector('code');
                    const codeText = code ? code.textContent : node.textContent;
                    const language = code ? this.extractLanguage(code.className) : '';
                    blocks.push({
                        type: 'codeBlock',
                        content: {
                            text: codeText,
                            data: { language: language }
                        }
                    });
                    break;

                case 'img':
                    blocks.push({
                        type: 'image',
                        content: {
                            data: {
                                url: node.getAttribute('src') || '',
                                altText: node.getAttribute('alt') || '',
                                caption: node.getAttribute('title') || ''
                            }
                        }
                    });
                    break;

                case 'hr':
                    blocks.push({
                        type: 'divider',
                        content: { data: { style: 'solid' } }
                    });
                    break;

                case 'table':
                    blocks.push(this.parseTable(node));
                    break;

                default:
                    // Process children for unknown tags
                    Array.from(node.childNodes).forEach(child => {
                        this.processHTMLNode(child, blocks, errors);
                    });
            }
        }

        /**
         * Parse HTML table
         * @param {Element} table - Table element
         * @returns {Object} Table block
         */
        parseTable(table) {
            const rows = table.querySelectorAll('tr');
            const cells = [];
            let hasHeaders = false;

            rows.forEach((row, rowIndex) => {
                const rowCells = [];
                const cellElements = row.querySelectorAll('td, th');
                
                cellElements.forEach(cell => {
                    rowCells.push(cell.textContent);
                    if (cell.tagName.toLowerCase() === 'th') {
                        hasHeaders = true;
                    }
                });
                
                cells.push(rowCells);
            });

            return {
                type: 'table',
                content: {
                    data: {
                        rows: cells.length,
                        cols: cells[0]?.length || 0,
                        headers: hasHeaders,
                        cells: cells
                    }
                }
            };
        }

        /**
         * Extract language from code class
         * @param {string} className - Class name
         * @returns {string} Language
         */
        extractLanguage(className) {
            const match = className.match(/language-(\w+)/);
            return match ? match[1] : '';
        }

        /**
         * Validate URL
         * @param {string} url - URL to validate
         * @returns {boolean} Is valid
         */
        isValidURL(url) {
            try {
                new URL(url);
                return true;
            } catch {
                return false;
            }
        }

        /**
         * Extract text from content
         * @param {Object} content - Content object
         * @returns {string} Extracted text
         */
        extractText(content) {
            const blocks = content.blocks || [];
            return blocks
                .filter(block => block.content && block.content.text)
                .map(block => block.content.text)
                .join(' ');
        }

        /**
         * Count words in text
         * @param {string} text - Text to count
         * @returns {number} Word count
         */
        countWords(text) {
            const words = text.match(/\b\w+\b/g);
            return words ? words.length : 0;
        }

        /**
         * Pre-publication check
         * @param {Object} content - Content to check
         * @returns {Object} Check results
         */
        prePublicationCheck(content) {
            const validation = this.validate(content);
            const seoIssues = this.checkSEO(content);
            const accessibilityIssues = this.checkAccessibility(content);

            return {
                canPublish: validation.valid && seoIssues.length === 0,
                validation: validation,
                seo: {
                    issues: seoIssues,
                    passed: seoIssues.length === 0
                },
                accessibility: {
                    issues: accessibilityIssues,
                    passed: accessibilityIssues.length === 0
                }
            };
        }

        /**
         * Check SEO issues
         * @param {Object} content - Content to check
         * @returns {Array} SEO issues
         */
        checkSEO(content) {
            const issues = [];
            const blocks = content.blocks || [];

            // Check for H1
            const hasH1 = blocks.some(b => b.type === 'heading' && b.content.data?.level === 1);
            if (!hasH1) {
                issues.push({
                    type: 'seo',
                    message: 'Missing H1 heading',
                    severity: 'warning'
                });
            }

            // Check content length
            const text = this.extractText(content);
            const wordCount = this.countWords(text);
            if (wordCount < 300) {
                issues.push({
                    type: 'seo',
                    message: `Content is short (${wordCount} words). Consider adding more content.`,
                    severity: 'warning'
                });
            }

            return issues;
        }

        /**
         * Check accessibility issues
         * @param {Object} content - Content to check
         * @returns {Array} Accessibility issues
         */
        checkAccessibility(content) {
            const issues = [];
            const blocks = content.blocks || [];

            // Check images for alt text
            blocks.forEach((block, index) => {
                if (block.type === 'image') {
                    const altText = block.content.data?.altText || '';
                    if (!altText) {
                        issues.push({
                            type: 'accessibility',
                            blockIndex: index,
                            message: 'Image missing alt text',
                            severity: 'error'
                        });
                    }
                }
            });

            return issues;
        }
    }

    // Export to global scope
    window.ContentValidator = ContentValidator;

    console.log('Content Validator module loaded');

})(window);
