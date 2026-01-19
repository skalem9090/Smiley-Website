/**
 * Advanced Editor System - Block System Implementation
 * 
 * This module implements the block-based content system with comprehensive
 * data structures, interfaces, and type definitions for the advanced editor.
 * 
 * Based on the design document specifications for block architecture.
 */

(function(window) {
    'use strict';

    /**
     * Block Types Enumeration
     * Defines all supported block types in the editor system
     */
    const BlockType = Object.freeze({
        // Text blocks
        PARAGRAPH: 'paragraph',
        HEADING: 'heading',
        QUOTE: 'quote',
        LIST_ITEM: 'listItem',
        
        // Media blocks
        IMAGE: 'image',
        VIDEO: 'video',
        AUDIO: 'audio',
        FILE: 'file',
        
        // Code blocks
        CODE_BLOCK: 'codeBlock',
        INLINE_CODE: 'inlineCode',
        
        // Layout blocks
        COLUMNS: 'columns',
        DIVIDER: 'divider',
        SPACER: 'spacer',
        
        // Interactive blocks
        CALLOUT: 'callout',
        TABLE: 'table',
        EMBED: 'embed',
        
        // Template blocks
        TEMPLATE: 'template'
    });

    /**
     * Block Alignment Options
     */
    const BlockAlignment = Object.freeze({
        LEFT: 'left',
        CENTER: 'center',
        RIGHT: 'right',
        JUSTIFY: 'justify'
    });

    /**
     * Callout Block Styles
     */
    const CalloutStyle = Object.freeze({
        INFO: 'info',
        WARNING: 'warning',
        SUCCESS: 'success',
        ERROR: 'error',
        NOTE: 'note'
    });

    /**
     * Block Status
     */
    const BlockStatus = Object.freeze({
        ACTIVE: 'active',
        DELETED: 'deleted',
        ARCHIVED: 'archived'
    });

    /**
     * Block Factory - Creates properly structured block instances
     */
    class BlockFactory {
        /**
         * Create a new block with default structure
         * @param {string} type - Block type from BlockType enum
         * @param {Object} options - Block creation options
         * @returns {Block} Newly created block
         */
        static createBlock(type, options = {}) {
            const blockId = BlockFactory.generateBlockId();
            const now = new Date();

            const block = {
                id: blockId,
                type: type,
                content: BlockFactory.createDefaultContent(type, options.content),
                properties: BlockFactory.createDefaultProperties(type, options.properties),
                children: options.children || [],
                metadata: {
                    createdAt: now,
                    updatedAt: now,
                    author: options.author || null,
                    version: 1,
                    status: BlockStatus.ACTIVE
                }
            };

            return Object.seal(block);
        }

        /**
         * Create default content structure for a block type
         * @param {string} type - Block type
         * @param {Object} customContent - Custom content to merge
         * @returns {BlockContent} Content object
         */
        static createDefaultContent(type, customContent = {}) {
            const defaultContent = {
                text: '',
                html: '',
                data: {}
            };

            // Type-specific default content
            switch (type) {
                case BlockType.HEADING:
                    defaultContent.data.level = 1;
                    break;
                case BlockType.CODE_BLOCK:
                    defaultContent.data.language = 'javascript';
                    defaultContent.data.lineNumbers = true;
                    break;
                case BlockType.IMAGE:
                    defaultContent.data.url = '';
                    defaultContent.data.alt = '';
                    defaultContent.data.caption = '';
                    break;
                case BlockType.VIDEO:
                    defaultContent.data.url = '';
                    defaultContent.data.provider = 'direct';
                    break;
                case BlockType.AUDIO:
                    defaultContent.data.url = '';
                    defaultContent.data.title = '';
                    break;
                case BlockType.FILE:
                    defaultContent.data.url = '';
                    defaultContent.data.filename = '';
                    defaultContent.data.size = 0;
                    break;
                case BlockType.CALLOUT:
                    defaultContent.data.style = CalloutStyle.INFO;
                    break;
                case BlockType.COLUMNS:
                    defaultContent.data.columnCount = 2;
                    break;
                case BlockType.TABLE:
                    defaultContent.data.rows = 3;
                    defaultContent.data.cols = 3;
                    defaultContent.data.headers = true;
                    break;
                case BlockType.EMBED:
                    defaultContent.data.url = '';
                    defaultContent.data.embedType = 'iframe';
                    break;
            }

            return { ...defaultContent, ...customContent };
        }

        /**
         * Create default properties for a block type
         * @param {string} type - Block type
         * @param {Object} customProperties - Custom properties to merge
         * @returns {BlockProperties} Properties object
         */
        static createDefaultProperties(type, customProperties = {}) {
            const defaultProperties = {
                alignment: BlockAlignment.LEFT,
                color: null,
                backgroundColor: null,
                fontSize: null,
                fontFamily: null,
                indentation: 0,
                padding: null,
                margin: null,
                borderColor: null,
                borderWidth: null,
                borderRadius: null
            };

            return { ...defaultProperties, ...customProperties };
        }

        /**
         * Generate unique block ID
         * @returns {string} Unique block identifier
         */
        static generateBlockId() {
            const timestamp = Date.now();
            const random = Math.random().toString(36).substring(2, 11);
            return `block_${timestamp}_${random}`;
        }

        /**
         * Validate block structure
         * @param {Object} block - Block to validate
         * @returns {ValidationResult} Validation result
         */
        static validateBlock(block) {
            const errors = [];

            // Required fields validation
            if (!block.id || typeof block.id !== 'string') {
                errors.push('Block must have a valid string ID');
            }

            if (!block.type || !Object.values(BlockType).includes(block.type)) {
                errors.push('Block must have a valid type');
            }

            if (!block.content || typeof block.content !== 'object') {
                errors.push('Block must have a content object');
            }

            if (!block.properties || typeof block.properties !== 'object') {
                errors.push('Block must have a properties object');
            }

            if (!block.metadata || typeof block.metadata !== 'object') {
                errors.push('Block must have a metadata object');
            }

            // Metadata validation
            if (block.metadata) {
                if (!(block.metadata.createdAt instanceof Date)) {
                    errors.push('Block metadata must have a valid createdAt date');
                }
                if (!(block.metadata.updatedAt instanceof Date)) {
                    errors.push('Block metadata must have a valid updatedAt date');
                }
                if (typeof block.metadata.version !== 'number') {
                    errors.push('Block metadata must have a numeric version');
                }
            }

            // Children validation
            if (block.children && !Array.isArray(block.children)) {
                errors.push('Block children must be an array');
            }

            return {
                isValid: errors.length === 0,
                errors: errors
            };
        }

        /**
         * Clone a block with a new ID
         * @param {Block} block - Block to clone
         * @returns {Block} Cloned block
         */
        static cloneBlock(block) {
            const clonedBlock = {
                id: BlockFactory.generateBlockId(),
                type: block.type,
                content: JSON.parse(JSON.stringify(block.content)),
                properties: JSON.parse(JSON.stringify(block.properties)),
                children: block.children.map(child => BlockFactory.cloneBlock(child)),
                metadata: {
                    createdAt: new Date(),
                    updatedAt: new Date(),
                    author: block.metadata.author,
                    version: 1,
                    status: BlockStatus.ACTIVE
                }
            };

            return Object.seal(clonedBlock);
        }
    }

    /**
     * Block Schema Definitions
     * Defines the structure and validation rules for each block type
     */
    class BlockSchema {
        /**
         * Get schema for a specific block type
         * @param {string} type - Block type
         * @returns {Object} Schema definition
         */
        static getSchema(type) {
            const schemas = {
                [BlockType.PARAGRAPH]: {
                    type: BlockType.PARAGRAPH,
                    allowedChildren: [],
                    requiredFields: ['text'],
                    optionalFields: ['html'],
                    properties: ['alignment', 'color', 'backgroundColor', 'fontSize', 'fontFamily', 'indentation']
                },
                [BlockType.HEADING]: {
                    type: BlockType.HEADING,
                    allowedChildren: [],
                    requiredFields: ['text', 'data.level'],
                    optionalFields: ['html'],
                    properties: ['alignment', 'color'],
                    validation: {
                        'data.level': (value) => value >= 1 && value <= 6
                    }
                },
                [BlockType.QUOTE]: {
                    type: BlockType.QUOTE,
                    allowedChildren: [],
                    requiredFields: ['text'],
                    optionalFields: ['html', 'data.author', 'data.source'],
                    properties: ['alignment', 'color', 'backgroundColor', 'borderColor']
                },
                [BlockType.LIST_ITEM]: {
                    type: BlockType.LIST_ITEM,
                    allowedChildren: [BlockType.LIST_ITEM],
                    requiredFields: ['text'],
                    optionalFields: ['data.ordered', 'data.checked'],
                    properties: ['indentation']
                },
                [BlockType.IMAGE]: {
                    type: BlockType.IMAGE,
                    allowedChildren: [],
                    requiredFields: ['data.url', 'data.alt'],
                    optionalFields: ['data.caption', 'data.width', 'data.height'],
                    properties: ['alignment']
                },
                [BlockType.VIDEO]: {
                    type: BlockType.VIDEO,
                    allowedChildren: [],
                    requiredFields: ['data.url'],
                    optionalFields: ['data.provider', 'data.caption', 'data.autoplay'],
                    properties: ['alignment']
                },
                [BlockType.AUDIO]: {
                    type: BlockType.AUDIO,
                    allowedChildren: [],
                    requiredFields: ['data.url'],
                    optionalFields: ['data.title', 'data.autoplay'],
                    properties: []
                },
                [BlockType.FILE]: {
                    type: BlockType.FILE,
                    allowedChildren: [],
                    requiredFields: ['data.url', 'data.filename'],
                    optionalFields: ['data.size', 'data.mimeType'],
                    properties: []
                },
                [BlockType.CODE_BLOCK]: {
                    type: BlockType.CODE_BLOCK,
                    allowedChildren: [],
                    requiredFields: ['text'],
                    optionalFields: ['data.language', 'data.lineNumbers', 'data.theme'],
                    properties: []
                },
                [BlockType.INLINE_CODE]: {
                    type: BlockType.INLINE_CODE,
                    allowedChildren: [],
                    requiredFields: ['text'],
                    optionalFields: [],
                    properties: ['color', 'backgroundColor']
                },
                [BlockType.COLUMNS]: {
                    type: BlockType.COLUMNS,
                    allowedChildren: Object.values(BlockType),
                    requiredFields: ['data.columnCount'],
                    optionalFields: ['data.gap'],
                    properties: [],
                    validation: {
                        'data.columnCount': (value) => value >= 2 && value <= 4
                    }
                },
                [BlockType.DIVIDER]: {
                    type: BlockType.DIVIDER,
                    allowedChildren: [],
                    requiredFields: [],
                    optionalFields: ['data.style', 'data.thickness'],
                    properties: ['color', 'margin']
                },
                [BlockType.SPACER]: {
                    type: BlockType.SPACER,
                    allowedChildren: [],
                    requiredFields: ['data.height'],
                    optionalFields: [],
                    properties: []
                },
                [BlockType.CALLOUT]: {
                    type: BlockType.CALLOUT,
                    allowedChildren: [],
                    requiredFields: ['text', 'data.style'],
                    optionalFields: ['data.icon', 'data.title'],
                    properties: ['backgroundColor', 'borderColor'],
                    validation: {
                        'data.style': (value) => Object.values(CalloutStyle).includes(value)
                    }
                },
                [BlockType.TABLE]: {
                    type: BlockType.TABLE,
                    allowedChildren: [],
                    requiredFields: ['data.rows', 'data.cols'],
                    optionalFields: ['data.headers', 'data.cells'],
                    properties: ['borderColor', 'borderWidth'],
                    validation: {
                        'data.rows': (value) => value >= 1 && value <= 100,
                        'data.cols': (value) => value >= 1 && value <= 20
                    }
                },
                [BlockType.EMBED]: {
                    type: BlockType.EMBED,
                    allowedChildren: [],
                    requiredFields: ['data.url'],
                    optionalFields: ['data.embedType', 'data.width', 'data.height'],
                    properties: ['alignment']
                },
                [BlockType.TEMPLATE]: {
                    type: BlockType.TEMPLATE,
                    allowedChildren: Object.values(BlockType),
                    requiredFields: ['data.templateId'],
                    optionalFields: ['data.variables'],
                    properties: []
                }
            };

            return schemas[type] || null;
        }

        /**
         * Validate block against its schema
         * @param {Block} block - Block to validate
         * @returns {ValidationResult} Validation result
         */
        static validateAgainstSchema(block) {
            const errors = [];
            const schema = BlockSchema.getSchema(block.type);

            if (!schema) {
                errors.push(`No schema found for block type: ${block.type}`);
                return { isValid: false, errors };
            }

            // Validate required fields
            schema.requiredFields.forEach(field => {
                const value = BlockSchema.getNestedValue(block.content, field);
                if (value === undefined || value === null || value === '') {
                    errors.push(`Required field missing: ${field}`);
                }
            });

            // Validate field values
            if (schema.validation) {
                Object.keys(schema.validation).forEach(field => {
                    const value = BlockSchema.getNestedValue(block.content, field);
                    const validator = schema.validation[field];
                    if (value !== undefined && !validator(value)) {
                        errors.push(`Invalid value for field: ${field}`);
                    }
                });
            }

            // Validate children
            if (block.children && block.children.length > 0) {
                block.children.forEach((child, index) => {
                    if (!schema.allowedChildren.includes(child.type)) {
                        errors.push(`Child type ${child.type} not allowed at index ${index}`);
                    }
                });
            }

            return {
                isValid: errors.length === 0,
                errors: errors
            };
        }

        /**
         * Get nested value from object using dot notation
         * @param {Object} obj - Object to search
         * @param {string} path - Dot-notation path
         * @returns {*} Value at path
         */
        static getNestedValue(obj, path) {
            return path.split('.').reduce((current, key) => current?.[key], obj);
        }
    }

    /**
     * Block Collection - Manages a collection of blocks
     */
    class BlockCollection {
        constructor() {
            this.blocks = new Map();
            this.order = [];
        }

        /**
         * Add a block to the collection
         * @param {Block} block - Block to add
         * @param {number} position - Position to insert (optional)
         */
        add(block, position = null) {
            this.blocks.set(block.id, block);
            
            if (position !== null && position >= 0 && position <= this.order.length) {
                this.order.splice(position, 0, block.id);
            } else {
                this.order.push(block.id);
            }
        }

        /**
         * Remove a block from the collection
         * @param {string} blockId - Block ID to remove
         * @returns {boolean} True if removed
         */
        remove(blockId) {
            const removed = this.blocks.delete(blockId);
            if (removed) {
                const index = this.order.indexOf(blockId);
                if (index > -1) {
                    this.order.splice(index, 1);
                }
            }
            return removed;
        }

        /**
         * Get a block by ID
         * @param {string} blockId - Block ID
         * @returns {Block|null} Block or null
         */
        get(blockId) {
            return this.blocks.get(blockId) || null;
        }

        /**
         * Update a block
         * @param {string} blockId - Block ID
         * @param {Object} updates - Updates to apply
         * @returns {Block|null} Updated block or null
         */
        update(blockId, updates) {
            const block = this.blocks.get(blockId);
            if (!block) return null;

            // Deep merge updates
            Object.keys(updates).forEach(key => {
                if (key === 'content' || key === 'properties') {
                    block[key] = { ...block[key], ...updates[key] };
                } else if (key !== 'id' && key !== 'metadata') {
                    block[key] = updates[key];
                }
            });

            // Update metadata
            block.metadata.updatedAt = new Date();
            block.metadata.version += 1;

            this.blocks.set(blockId, block);
            return block;
        }

        /**
         * Move a block to a new position
         * @param {string} blockId - Block ID
         * @param {number} newPosition - New position
         * @returns {boolean} True if moved
         */
        move(blockId, newPosition) {
            const currentIndex = this.order.indexOf(blockId);
            if (currentIndex === -1) return false;

            // Remove from current position
            this.order.splice(currentIndex, 1);

            // Insert at new position
            const insertIndex = Math.max(0, Math.min(newPosition, this.order.length));
            this.order.splice(insertIndex, 0, blockId);

            return true;
        }

        /**
         * Get all blocks in order
         * @returns {Block[]} Array of blocks
         */
        getAll() {
            return this.order.map(id => this.blocks.get(id)).filter(Boolean);
        }

        /**
         * Get blocks by type
         * @param {string} type - Block type
         * @returns {Block[]} Array of blocks
         */
        getByType(type) {
            return Array.from(this.blocks.values()).filter(block => block.type === type);
        }

        /**
         * Get block position
         * @param {string} blockId - Block ID
         * @returns {number} Position or -1
         */
        getPosition(blockId) {
            return this.order.indexOf(blockId);
        }

        /**
         * Get total count
         * @returns {number} Number of blocks
         */
        count() {
            return this.blocks.size;
        }

        /**
         * Clear all blocks
         */
        clear() {
            this.blocks.clear();
            this.order = [];
        }

        /**
         * Export to JSON
         * @returns {Object} JSON representation
         */
        toJSON() {
            return {
                blocks: this.getAll(),
                order: this.order,
                count: this.count()
            };
        }

        /**
         * Import from JSON
         * @param {Object} data - JSON data
         */
        fromJSON(data) {
            this.clear();
            if (data.blocks && Array.isArray(data.blocks)) {
                data.blocks.forEach(block => {
                    // Restore Date objects
                    if (block.metadata) {
                        block.metadata.createdAt = new Date(block.metadata.createdAt);
                        block.metadata.updatedAt = new Date(block.metadata.updatedAt);
                    }
                    this.blocks.set(block.id, block);
                });
            }
            if (data.order && Array.isArray(data.order)) {
                this.order = [...data.order];
            }
        }
    }

    // Export to global scope
    window.BlockType = BlockType;
    window.BlockAlignment = BlockAlignment;
    window.CalloutStyle = CalloutStyle;
    window.BlockStatus = BlockStatus;
    window.BlockFactory = BlockFactory;
    window.BlockSchema = BlockSchema;
    window.BlockCollection = BlockCollection;

})(window);
