/**
 * Advanced Editor System - Template System
 * 
 * Manages content templates and layouts:
 * - Template creation and storage
 * - Template library with common post types
 * - Template application with placeholder population
 * - Custom template creation and saving
 * - Template categories and search
 * 
 * Validates Property 18: Template System Functionality
 */

(function(window) {
    'use strict';

    /**
     * Template System
     * Manages content templates
     */
    class TemplateSystem {
        constructor(config = {}) {
            this.config = {
                storageKey: config.storageKey || 'editor_templates',
                ...config
            };

            this.templates = new Map();
            this.loadTemplates();
            this.initializeDefaultTemplates();
        }

        /**
         * Load templates from storage
         */
        loadTemplates() {
            try {
                const stored = localStorage.getItem(this.config.storageKey);
                if (stored) {
                    const templates = JSON.parse(stored);
                    templates.forEach(template => {
                        this.templates.set(template.id, template);
                    });
                }
            } catch (error) {
                console.error('Failed to load templates:', error);
            }
        }

        /**
         * Save templates to storage
         */
        saveTemplates() {
            try {
                const templates = Array.from(this.templates.values());
                localStorage.setItem(this.config.storageKey, JSON.stringify(templates));
            } catch (error) {
                console.error('Failed to save templates:', error);
            }
        }

        /**
         * Initialize default templates
         */
        initializeDefaultTemplates() {
            // Blog Post Template
            if (!this.templates.has('blog-post')) {
                this.createTemplate({
                    id: 'blog-post',
                    name: 'Blog Post',
                    description: 'Standard blog post with introduction, body, and conclusion',
                    category: 'blog',
                    blocks: [
                        {
                            type: 'heading',
                            content: { text: '{{title}}', data: { level: 1 } }
                        },
                        {
                            type: 'paragraph',
                            content: { text: '{{introduction}}' }
                        },
                        {
                            type: 'heading',
                            content: { text: 'Main Content', data: { level: 2 } }
                        },
                        {
                            type: 'paragraph',
                            content: { text: '{{body}}' }
                        },
                        {
                            type: 'heading',
                            content: { text: 'Conclusion', data: { level: 2 } }
                        },
                        {
                            type: 'paragraph',
                            content: { text: '{{conclusion}}' }
                        }
                    ],
                    variables: [
                        { name: 'title', type: 'text', required: true },
                        { name: 'introduction', type: 'text', required: true },
                        { name: 'body', type: 'text', required: true },
                        { name: 'conclusion', type: 'text', required: false }
                    ]
                });
            }

            // Tutorial Template
            if (!this.templates.has('tutorial')) {
                this.createTemplate({
                    id: 'tutorial',
                    name: 'Tutorial',
                    description: 'Step-by-step tutorial with prerequisites and examples',
                    category: 'educational',
                    blocks: [
                        {
                            type: 'heading',
                            content: { text: '{{title}}', data: { level: 1 } }
                        },
                        {
                            type: 'callout',
                            content: { text: '{{prerequisites}}', data: { style: 'info' } }
                        },
                        {
                            type: 'heading',
                            content: { text: 'Step 1: {{step1_title}}', data: { level: 2 } }
                        },
                        {
                            type: 'paragraph',
                            content: { text: '{{step1_content}}' }
                        },
                        {
                            type: 'heading',
                            content: { text: 'Step 2: {{step2_title}}', data: { level: 2 } }
                        },
                        {
                            type: 'paragraph',
                            content: { text: '{{step2_content}}' }
                        }
                    ],
                    variables: [
                        { name: 'title', type: 'text', required: true },
                        { name: 'prerequisites', type: 'text', required: false },
                        { name: 'step1_title', type: 'text', required: true },
                        { name: 'step1_content', type: 'text', required: true },
                        { name: 'step2_title', type: 'text', required: true },
                        { name: 'step2_content', type: 'text', required: true }
                    ]
                });
            }

            // Product Review Template
            if (!this.templates.has('product-review')) {
                this.createTemplate({
                    id: 'product-review',
                    name: 'Product Review',
                    description: 'Product review with pros, cons, and rating',
                    category: 'review',
                    blocks: [
                        {
                            type: 'heading',
                            content: { text: '{{product_name}} Review', data: { level: 1 } }
                        },
                        {
                            type: 'paragraph',
                            content: { text: '{{introduction}}' }
                        },
                        {
                            type: 'heading',
                            content: { text: 'Pros', data: { level: 2 } }
                        },
                        {
                            type: 'listItem',
                            content: { text: '{{pro1}}', data: { ordered: false } }
                        },
                        {
                            type: 'heading',
                            content: { text: 'Cons', data: { level: 2 } }
                        },
                        {
                            type: 'listItem',
                            content: { text: '{{con1}}', data: { ordered: false } }
                        },
                        {
                            type: 'heading',
                            content: { text: 'Verdict', data: { level: 2 } }
                        },
                        {
                            type: 'paragraph',
                            content: { text: '{{verdict}}' }
                        }
                    ],
                    variables: [
                        { name: 'product_name', type: 'text', required: true },
                        { name: 'introduction', type: 'text', required: true },
                        { name: 'pro1', type: 'text', required: true },
                        { name: 'con1', type: 'text', required: true },
                        { name: 'verdict', type: 'text', required: true }
                    ]
                });
            }

            // News Article Template
            if (!this.templates.has('news-article')) {
                this.createTemplate({
                    id: 'news-article',
                    name: 'News Article',
                    description: 'News article with headline, lead, and body',
                    category: 'news',
                    blocks: [
                        {
                            type: 'heading',
                            content: { text: '{{headline}}', data: { level: 1 } }
                        },
                        {
                            type: 'paragraph',
                            content: { text: '{{lead}}' }
                        },
                        {
                            type: 'paragraph',
                            content: { text: '{{body}}' }
                        },
                        {
                            type: 'callout',
                            content: { text: 'Source: {{source}}', data: { style: 'note' } }
                        }
                    ],
                    variables: [
                        { name: 'headline', type: 'text', required: true },
                        { name: 'lead', type: 'text', required: true },
                        { name: 'body', type: 'text', required: true },
                        { name: 'source', type: 'text', required: false }
                    ]
                });
            }
        }

        /**
         * Create template
         * @param {Object} template - Template data
         * @returns {Object} Created template
         */
        createTemplate(template) {
            const id = template.id || this.generateId();
            const newTemplate = {
                id: id,
                name: template.name,
                description: template.description || '',
                category: template.category || 'general',
                blocks: template.blocks || [],
                variables: template.variables || [],
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            };

            this.templates.set(id, newTemplate);
            this.saveTemplates();
            
            return newTemplate;
        }

        /**
         * Update template
         * @param {string} id - Template ID
         * @param {Object} updates - Template updates
         * @returns {Object} Updated template
         */
        updateTemplate(id, updates) {
            const template = this.templates.get(id);
            if (!template) {
                throw new Error(`Template not found: ${id}`);
            }

            Object.assign(template, updates, {
                updatedAt: new Date().toISOString()
            });

            this.templates.set(id, template);
            this.saveTemplates();
            
            return template;
        }

        /**
         * Delete template
         * @param {string} id - Template ID
         */
        deleteTemplate(id) {
            this.templates.delete(id);
            this.saveTemplates();
        }

        /**
         * Get template by ID
         * @param {string} id - Template ID
         * @returns {Object} Template
         */
        getTemplate(id) {
            return this.templates.get(id);
        }

        /**
         * Get all templates
         * @returns {Array} Array of templates
         */
        getAllTemplates() {
            return Array.from(this.templates.values());
        }

        /**
         * Get templates by category
         * @param {string} category - Category name
         * @returns {Array} Array of templates
         */
        getTemplatesByCategory(category) {
            return this.getAllTemplates().filter(t => t.category === category);
        }

        /**
         * Search templates
         * @param {string} query - Search query
         * @returns {Array} Array of matching templates
         */
        searchTemplates(query) {
            if (!query) return this.getAllTemplates();
            
            const lowerQuery = query.toLowerCase();
            return this.getAllTemplates().filter(template =>
                template.name.toLowerCase().includes(lowerQuery) ||
                template.description.toLowerCase().includes(lowerQuery) ||
                template.category.toLowerCase().includes(lowerQuery)
            );
        }

        /**
         * Apply template with variable values
         * @param {string} templateId - Template ID
         * @param {Object} values - Variable values
         * @returns {Object} Content with populated values
         */
        applyTemplate(templateId, values = {}) {
            const template = this.getTemplate(templateId);
            if (!template) {
                throw new Error(`Template not found: ${templateId}`);
            }

            // Validate required variables
            const missingRequired = template.variables
                .filter(v => v.required && !values[v.name])
                .map(v => v.name);
            
            if (missingRequired.length > 0) {
                throw new Error(`Missing required variables: ${missingRequired.join(', ')}`);
            }

            // Clone blocks and populate variables
            const blocks = JSON.parse(JSON.stringify(template.blocks));
            
            blocks.forEach(block => {
                if (block.content && block.content.text) {
                    block.content.text = this.populateVariables(block.content.text, values);
                }
            });

            return {
                blocks: blocks,
                metadata: {
                    templateId: templateId,
                    templateName: template.name,
                    appliedAt: new Date().toISOString()
                }
            };
        }

        /**
         * Populate variables in text
         * @param {string} text - Text with variables
         * @param {Object} values - Variable values
         * @returns {string} Text with populated values
         */
        populateVariables(text, values) {
            return text.replace(/\{\{(\w+)\}\}/g, (match, variable) => {
                return values[variable] !== undefined ? values[variable] : match;
            });
        }

        /**
         * Get template categories
         * @returns {Array} Array of unique categories
         */
        getCategories() {
            const categories = new Set();
            this.getAllTemplates().forEach(template => {
                categories.add(template.category);
            });
            return Array.from(categories).sort();
        }

        /**
         * Generate unique ID
         * @returns {string} Unique ID
         */
        generateId() {
            return 'template-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        }

        /**
         * Export template
         * @param {string} id - Template ID
         * @returns {string} JSON string
         */
        exportTemplate(id) {
            const template = this.getTemplate(id);
            if (!template) {
                throw new Error(`Template not found: ${id}`);
            }
            return JSON.stringify(template, null, 2);
        }

        /**
         * Import template
         * @param {string} json - Template JSON
         * @returns {Object} Imported template
         */
        importTemplate(json) {
            try {
                const template = JSON.parse(json);
                return this.createTemplate(template);
            } catch (error) {
                throw new Error('Invalid template JSON: ' + error.message);
            }
        }
    }

    // Export to global scope
    window.TemplateSystem = TemplateSystem;

    console.log('Template System module loaded');

})(window);
