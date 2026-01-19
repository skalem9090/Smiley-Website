/**
 * Advanced Editor System - Mode Converter
 * 
 * This module handles conversion between WYSIWYG and Markdown modes,
 * managing the bidirectional transformation of content.
 */

(function(window) {
    'use strict';

    /**
     * ModeConverter - Handles conversion between editing modes
     */
    class ModeConverter {
        constructor(editorController) {
            this.editorController = editorController;
            this.markdownParser = new window.MarkdownParser();
            this.markdownSerializer = new window.MarkdownSerializer();
            this.currentMode = 'wysiwyg';
            this.wysiwygContent = null;
            this.markdownContent = '';
        }

        /**
         * Convert from WYSIWYG to Markdown
         * @returns {string} Markdown text
         */
        convertToMarkdown() {
            const blockManager = this.editorController.blockManager;
            if (!blockManager) {
                throw new Error('BlockManager not available');
            }

            const blocks = blockManager.getAllBlocks();
            const markdown = this.markdownSerializer.serialize(blocks);
            
            this.markdownContent = markdown;
            this.currentMode = 'markdown';
            
            return markdown;
        }

        /**
         * Convert from Markdown to WYSIWYG
         * @param {string} markdown - Markdown text
         * @returns {Block[]} Array of blocks
         */
        convertToWYSIWYG(markdown) {
            const blocks = this.markdownParser.parse(markdown);
            
            const blockManager = this.editorController.blockManager;
            if (!blockManager) {
                throw new Error('BlockManager not available');
            }

            // Clear existing blocks
            blockManager.clearAllBlocks();
            
            // Add parsed blocks
            blocks.forEach(block => {
                blockManager.blockCollection.add(block);
            });
            
            this.wysiwygContent = blocks;
            this.currentMode = 'wysiwyg';
            
            return blocks;
        }

        /**
         * Switch mode
         * @param {string} targetMode - Target mode ('wysiwyg' or 'markdown')
         */
        switchMode(targetMode) {
            if (targetMode === this.currentMode) {
                return;
            }

            if (targetMode === 'markdown') {
                return this.convertToMarkdown();
            } else if (targetMode === 'wysiwyg') {
                return this.convertToWYSIWYG(this.markdownContent);
            } else {
                throw new Error(`Invalid mode: ${targetMode}`);
            }
        }

        /**
         * Get current mode
         * @returns {string} Current mode
         */
        getCurrentMode() {
            return this.currentMode;
        }

        /**
         * Validate round-trip conversion
         * @param {Block[]} originalBlocks - Original blocks
         * @returns {Object} Validation result
         */
        validateRoundTrip(originalBlocks) {
            // Convert to Markdown
            const markdown = this.markdownSerializer.serialize(originalBlocks);
            
            // Convert back to blocks
            const convertedBlocks = this.markdownParser.parse(markdown);
            
            // Compare
            const errors = [];
            
            if (originalBlocks.length !== convertedBlocks.length) {
                errors.push(`Block count mismatch: ${originalBlocks.length} vs ${convertedBlocks.length}`);
            }
            
            for (let i = 0; i < Math.min(originalBlocks.length, convertedBlocks.length); i++) {
                const original = originalBlocks[i];
                const converted = convertedBlocks[i];
                
                if (original.type !== converted.type) {
                    errors.push(`Block ${i} type mismatch: ${original.type} vs ${converted.type}`);
                }
                
                if (original.content.text !== converted.content.text) {
                    errors.push(`Block ${i} text mismatch`);
                }
            }
            
            return {
                isValid: errors.length === 0,
                errors: errors,
                markdown: markdown,
                convertedBlocks: convertedBlocks
            };
        }

        /**
         * Sync content between modes
         * @param {string} sourceMode - Source mode
         * @param {*} content - Content to sync
         */
        syncContent(sourceMode, content) {
            if (sourceMode === 'wysiwyg') {
                // Update Markdown from WYSIWYG
                this.markdownContent = this.markdownSerializer.serialize(content);
            } else if (sourceMode === 'markdown') {
                // Update WYSIWYG from Markdown
                this.wysiwygContent = this.markdownParser.parse(content);
            }
        }

        /**
         * Get content in specified mode
         * @param {string} mode - Mode to get content for
         * @returns {*} Content in specified mode
         */
        getContent(mode) {
            if (mode === 'markdown') {
                if (this.currentMode === 'wysiwyg') {
                    return this.convertToMarkdown();
                }
                return this.markdownContent;
            } else if (mode === 'wysiwyg') {
                if (this.currentMode === 'markdown') {
                    return this.convertToWYSIWYG(this.markdownContent);
                }
                return this.wysiwygContent;
            }
        }
    }

    // Export to global scope
    window.ModeConverter = ModeConverter;

})(window);
