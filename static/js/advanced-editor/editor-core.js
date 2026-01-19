/**
 * Advanced Editor System - Core Editor Implementation
 * 
 * This module provides the foundation for the advanced blog post editor,
 * built on top of Tiptap/ProseMirror with modern editing capabilities.
 */

(function(window) {
    'use strict';

    // Check if Tiptap is available
    if (typeof window.Tiptap === 'undefined') {
        console.error('Tiptap is not loaded. Please include Tiptap scripts before this file.');
        return;
    }

    const { Editor } = window.Tiptap;
    const { StarterKit } = window.TiptapStarterKit;

    /**
     * EditorController - Main controller for the advanced editor system
     */
    class EditorController {
        constructor(config = {}) {
            this.config = {
                element: null,
                content: '',
                editable: true,
                autofocus: false,
                extensions: [],
                onUpdate: () => {},
                onCreate: () => {},
                onDestroy: () => {},
                ...config
            };
            
            this.editor = null;
            this.mode = 'wysiwyg'; // 'wysiwyg' or 'markdown'
            this.eventListeners = new Map();
            this.blockManager = null;
            this.contentProcessor = null;
            this.isInitialized = false;
        }

        /**
         * Initialize the editor with all extensions and configurations
         */
        async initialize() {
            try {
                if (!this.config.element) {
                    throw new Error('Editor element is required');
                }

                // Create default extensions - just use StarterKit for now
                const extensions = [
                    StarterKit
                ];

                // Add custom extensions
                extensions.push(...this.config.extensions);

                // Create editor instance
                this.editor = new Editor({
                    element: this.config.element,
                    extensions: extensions,
                    content: this.config.content,
                    editable: this.config.editable,
                    autofocus: this.config.autofocus,
                    onUpdate: ({ editor }) => {
                        this.handleUpdate(editor);
                    },
                    onCreate: ({ editor }) => {
                        this.handleCreate(editor);
                    },
                    onDestroy: () => {
                        this.handleDestroy();
                    },
                });

                // Initialize managers
                this.blockManager = new BlockManager(this);
                this.contentProcessor = new ContentProcessor(this);

                this.isInitialized = true;
                this.emit('initialized', { editor: this });

                return this;
            } catch (error) {
                console.error('Failed to initialize EditorController:', error);
                throw error;
            }
        }

        /**
         * Handle editor update events
         */
        handleUpdate(editor) {
            const content = {
                html: editor.getHTML(),
                json: editor.getJSON(),
                text: editor.getText()
            };
            
            this.config.onUpdate({ content, editor: this });
            this.emit('update', { content, editor: this });
        }

        /**
         * Handle editor create events
         */
        handleCreate(editor) {
            this.config.onCreate({ editor: this });
            this.emit('create', { editor: this });
        }

        /**
         * Handle editor destroy events
         */
        handleDestroy() {
            this.config.onDestroy({ editor: this });
            this.emit('destroy', { editor: this });
        }

        /**
         * Get current editor content
         */
        getContent() {
            if (!this.editor) return { html: '', json: null, text: '' };
            
            return {
                html: this.editor.getHTML(),
                json: this.editor.getJSON(),
                text: this.editor.getText()
            };
        }

        /**
         * Set editor content
         */
        setContent(content) {
            if (!this.editor) {
                throw new Error('Editor not initialized');
            }
            
            this.editor.commands.setContent(content);
        }

        /**
         * Get current editing mode
         */
        getCurrentMode() {
            return this.mode;
        }

        /**
         * Switch editing mode
         */
        switchMode(mode) {
            if (mode === this.mode) return;
            
            const previousMode = this.mode;
            this.mode = mode;
            
            this.emit('modeChanged', { 
                currentMode: mode, 
                previousMode: previousMode, 
                editor: this 
            });
        }

        /**
         * Execute editor command
         */
        executeCommand(command, ...args) {
            if (!this.editor) {
                throw new Error('Editor not initialized');
            }
            
            return this.editor.commands[command](...args);
        }

        /**
         * Get editor state
         */
        getState() {
            if (!this.editor) return null;
            
            return {
                canUndo: this.editor.can().undo(),
                canRedo: this.editor.can().redo(),
                isEmpty: this.editor.isEmpty,
                isFocused: this.editor.isFocused,
                isEditable: this.editor.isEditable,
                mode: this.mode
            };
        }

        /**
         * Check if editor is ready
         */
        isReady() {
            return this.isInitialized && this.editor && !this.editor.isDestroyed;
        }

        /**
         * Focus the editor
         */
        focus() {
            if (this.editor) {
                this.editor.commands.focus();
            }
        }

        /**
         * Event handling
         */
        on(event, callback) {
            if (!this.eventListeners.has(event)) {
                this.eventListeners.set(event, []);
            }
            this.eventListeners.get(event).push(callback);
        }

        off(event, callback) {
            if (!this.eventListeners.has(event)) return;
            
            const callbacks = this.eventListeners.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }

        emit(event, data = {}) {
            if (!this.eventListeners.has(event)) return;
            
            this.eventListeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in event listener for ${event}:`, error);
                }
            });
        }

        /**
         * Destroy the editor
         */
        destroy() {
            if (this.editor) {
                this.editor.destroy();
                this.editor = null;
            }
            
            if (this.blockManager) {
                this.blockManager.destroy();
                this.blockManager = null;
            }
            
            if (this.contentProcessor) {
                this.contentProcessor.destroy();
                this.contentProcessor = null;
            }
            
            this.eventListeners.clear();
            this.isInitialized = false;
        }
    }

    /**
     * BlockManager - Manages block-based content operations
     * Enhanced to use the comprehensive block system
     */
    class BlockManager {
        constructor(editorController) {
            this.editorController = editorController;
            this.blockCollection = new window.BlockCollection();
            this.eventListeners = new Map();
        }

        /**
         * Create a new block
         * @param {string} type - Block type from BlockType enum
         * @param {Object} options - Block creation options
         * @returns {Block} Created block
         */
        createBlock(type, options = {}) {
            if (!window.BlockType || !Object.values(window.BlockType).includes(type)) {
                throw new Error(`Invalid block type: ${type}`);
            }

            const block = window.BlockFactory.createBlock(type, options);
            
            // Validate block
            const validation = window.BlockFactory.validateBlock(block);
            if (!validation.isValid) {
                throw new Error(`Block validation failed: ${validation.errors.join(', ')}`);
            }

            // Validate against schema
            const schemaValidation = window.BlockSchema.validateAgainstSchema(block);
            if (!schemaValidation.isValid) {
                console.warn('Block schema validation warnings:', schemaValidation.errors);
            }

            // Add to collection
            this.blockCollection.add(block, options.position);

            // Emit event
            this.emit('blockCreated', { block, manager: this });

            return block;
        }

        /**
         * Update an existing block
         * @param {string} blockId - Block ID
         * @param {Object} updates - Updates to apply
         * @returns {Block} Updated block
         */
        updateBlock(blockId, updates) {
            const block = this.blockCollection.get(blockId);
            if (!block) {
                throw new Error(`Block ${blockId} not found`);
            }

            const updatedBlock = this.blockCollection.update(blockId, updates);
            
            // Validate updated block
            const validation = window.BlockFactory.validateBlock(updatedBlock);
            if (!validation.isValid) {
                throw new Error(`Updated block validation failed: ${validation.errors.join(', ')}`);
            }

            // Emit event
            this.emit('blockUpdated', { block: updatedBlock, manager: this });

            return updatedBlock;
        }

        /**
         * Delete a block
         * @param {string} blockId - Block ID
         * @returns {boolean} True if deleted
         */
        deleteBlock(blockId) {
            const block = this.blockCollection.get(blockId);
            if (!block) {
                return false;
            }

            const removed = this.blockCollection.remove(blockId);
            
            if (removed) {
                this.emit('blockDeleted', { blockId, block, manager: this });
            }

            return removed;
        }

        /**
         * Move a block to a new position
         * @param {string} blockId - Block ID
         * @param {number} newPosition - New position
         * @returns {boolean} True if moved
         */
        moveBlock(blockId, newPosition) {
            const moved = this.blockCollection.move(blockId, newPosition);
            
            if (moved) {
                const block = this.blockCollection.get(blockId);
                this.emit('blockMoved', { block, newPosition, manager: this });
            }

            return moved;
        }

        /**
         * Duplicate a block
         * @param {string} blockId - Block ID to duplicate
         * @returns {Block} Duplicated block
         */
        duplicateBlock(blockId) {
            const block = this.blockCollection.get(blockId);
            if (!block) {
                throw new Error(`Block ${blockId} not found`);
            }

            const clonedBlock = window.BlockFactory.cloneBlock(block);
            const position = this.blockCollection.getPosition(blockId);
            
            this.blockCollection.add(clonedBlock, position + 1);

            this.emit('blockDuplicated', { original: block, duplicate: clonedBlock, manager: this });

            return clonedBlock;
        }

        /**
         * Get a block by ID
         * @param {string} blockId - Block ID
         * @returns {Block|null} Block or null
         */
        getBlock(blockId) {
            return this.blockCollection.get(blockId);
        }

        /**
         * Get all blocks in order
         * @returns {Block[]} Array of blocks
         */
        getAllBlocks() {
            return this.blockCollection.getAll();
        }

        /**
         * Get blocks by type
         * @param {string} type - Block type
         * @returns {Block[]} Array of blocks
         */
        getBlocksByType(type) {
            return this.blockCollection.getByType(type);
        }

        /**
         * Validate a block
         * @param {Block} block - Block to validate
         * @returns {ValidationResult} Validation result
         */
        validateBlock(block) {
            const basicValidation = window.BlockFactory.validateBlock(block);
            if (!basicValidation.isValid) {
                return basicValidation;
            }

            return window.BlockSchema.validateAgainstSchema(block);
        }

        /**
         * Check if a block type can be inserted at a position
         * @param {string} type - Block type
         * @param {number} position - Position to check
         * @returns {boolean} True if can insert
         */
        canInsertBlock(type, position) {
            // Basic validation
            if (!window.BlockType || !Object.values(window.BlockType).includes(type)) {
                return false;
            }

            if (position < 0 || position > this.blockCollection.count()) {
                return false;
            }

            // Check if position is within a parent block that doesn't allow this type
            // This is a simplified check - can be enhanced based on parent-child relationships
            return true;
        }

        /**
         * Get block count
         * @returns {number} Number of blocks
         */
        getBlockCount() {
            return this.blockCollection.count();
        }

        /**
         * Clear all blocks
         */
        clearAllBlocks() {
            this.blockCollection.clear();
            this.emit('blocksCleared', { manager: this });
        }

        /**
         * Export blocks to JSON
         * @returns {Object} JSON representation
         */
        exportToJSON() {
            return this.blockCollection.toJSON();
        }

        /**
         * Import blocks from JSON
         * @param {Object} data - JSON data
         */
        importFromJSON(data) {
            this.blockCollection.fromJSON(data);
            this.emit('blocksImported', { data, manager: this });
        }

        /**
         * Event handling
         */
        on(event, callback) {
            if (!this.eventListeners.has(event)) {
                this.eventListeners.set(event, []);
            }
            this.eventListeners.get(event).push(callback);
        }

        off(event, callback) {
            if (!this.eventListeners.has(event)) return;
            
            const callbacks = this.eventListeners.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }

        emit(event, data = {}) {
            if (!this.eventListeners.has(event)) return;
            
            this.eventListeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in BlockManager event listener for ${event}:`, error);
                }
            });
        }

        /**
         * Destroy the block manager
         */
        destroy() {
            this.blockCollection.clear();
            this.eventListeners.clear();
            this.editorController = null;
        }
    }

    /**
     * ContentProcessor - Handles content transformation and validation
     */
    class ContentProcessor {
        constructor(editorController) {
            this.editorController = editorController;
        }

        /**
         * Process content for different output formats
         */
        processContent(content, format = 'html') {
            switch (format) {
                case 'html':
                    return this.processHTML(content);
                case 'markdown':
                    return this.processMarkdown(content);
                case 'text':
                    return this.processText(content);
                default:
                    throw new Error(`Unsupported format: ${format}`);
            }
        }

        /**
         * Process HTML content
         */
        processHTML(content) {
            // Basic HTML processing - can be extended
            return content;
        }

        /**
         * Process Markdown content
         */
        processMarkdown(content) {
            // Basic Markdown processing - can be extended
            // This would need a proper HTML to Markdown converter
            return content;
        }

        /**
         * Process text content
         */
        processText(content) {
            // Strip HTML tags for plain text
            const div = document.createElement('div');
            div.innerHTML = content;
            return div.textContent || div.innerText || '';
        }

        /**
         * Validate content
         */
        validateContent(content) {
            const errors = [];
            
            // Basic validation - can be extended
            if (!content || content.trim().length === 0) {
                errors.push('Content cannot be empty');
            }
            
            return {
                isValid: errors.length === 0,
                errors: errors
            };
        }

        /**
         * Destroy the content processor
         */
        destroy() {
            this.editorController = null;
        }
    }

    // Export classes to global scope
    window.EditorController = EditorController;
    window.BlockManager = BlockManager;
    window.ContentProcessor = ContentProcessor;

})(window);