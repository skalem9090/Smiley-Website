/**
 * Advanced Editor System - Block Selection and Focus Management
 * 
 * This module handles block selection, focus states, and keyboard navigation
 * for the block-based editor system.
 */

(function(window) {
    'use strict';

    /**
     * BlockSelectionManager - Manages block selection and focus
     */
    class BlockSelectionManager {
        constructor(editorController, containerElement) {
            this.editorController = editorController;
            this.container = containerElement;
            this.selectedBlocks = new Set();
            this.focusedBlock = null;
            this.lastSelectedBlock = null;
            this.selectionMode = 'single'; // 'single' or 'multiple'
            
            this.setupEventListeners();
        }

        /**
         * Set up event listeners for selection and focus
         */
        setupEventListeners() {
            // Click events for selection
            this.container.addEventListener('click', this.handleClick.bind(this));
            
            // Keyboard events for navigation
            document.addEventListener('keydown', this.handleKeyDown.bind(this));
            
            // Focus events
            this.container.addEventListener('focusin', this.handleFocusIn.bind(this));
            this.container.addEventListener('focusout', this.handleFocusOut.bind(this));
        }

        /**
         * Handle click events on blocks
         */
        handleClick(event) {
            const blockElement = event.target.closest('.editor-block');
            if (!blockElement) {
                this.clearSelection();
                return;
            }

            const blockId = blockElement.getAttribute('data-block-id');
            if (!blockId) return;

            // Check for modifier keys
            if (event.ctrlKey || event.metaKey) {
                // Toggle selection
                this.toggleBlockSelection(blockId, blockElement);
            } else if (event.shiftKey && this.lastSelectedBlock) {
                // Range selection
                this.selectBlockRange(this.lastSelectedBlock, blockId);
            } else {
                // Single selection
                this.selectBlock(blockId, blockElement);
            }
        }

        /**
         * Handle keyboard navigation
         */
        handleKeyDown(event) {
            if (!this.focusedBlock) return;

            switch (event.key) {
                case 'ArrowUp':
                    event.preventDefault();
                    this.selectPreviousBlock();
                    break;
                case 'ArrowDown':
                    event.preventDefault();
                    this.selectNextBlock();
                    break;
                case 'Escape':
                    event.preventDefault();
                    this.clearSelection();
                    break;
                case 'a':
                    if (event.ctrlKey || event.metaKey) {
                        event.preventDefault();
                        this.selectAllBlocks();
                    }
                    break;
                case 'Delete':
                case 'Backspace':
                    if (this.selectedBlocks.size > 0 && !this.isEditingBlock()) {
                        event.preventDefault();
                        this.deleteSelectedBlocks();
                    }
                    break;
            }
        }

        /**
         * Handle focus in events
         */
        handleFocusIn(event) {
            const blockElement = event.target.closest('.editor-block');
            if (blockElement) {
                const blockId = blockElement.getAttribute('data-block-id');
                this.setFocusedBlock(blockId, blockElement);
            }
        }

        /**
         * Handle focus out events
         */
        handleFocusOut(event) {
            // Only clear focus if not moving to another block
            const relatedTarget = event.relatedTarget;
            if (!relatedTarget || !relatedTarget.closest('.editor-block')) {
                this.clearFocus();
            }
        }

        /**
         * Select a single block
         */
        selectBlock(blockId, blockElement) {
            this.clearSelection();
            this.selectedBlocks.add(blockId);
            this.lastSelectedBlock = blockId;
            
            if (blockElement) {
                blockElement.classList.add('block-selected');
            }
            
            this.emitSelectionChange();
        }

        /**
         * Toggle block selection
         */
        toggleBlockSelection(blockId, blockElement) {
            if (this.selectedBlocks.has(blockId)) {
                this.selectedBlocks.delete(blockId);
                if (blockElement) {
                    blockElement.classList.remove('block-selected');
                }
            } else {
                this.selectedBlocks.add(blockId);
                this.lastSelectedBlock = blockId;
                if (blockElement) {
                    blockElement.classList.add('block-selected');
                }
            }
            
            this.emitSelectionChange();
        }

        /**
         * Select a range of blocks
         */
        selectBlockRange(startBlockId, endBlockId) {
            const allBlocks = Array.from(this.container.querySelectorAll('.editor-block'));
            const startIndex = allBlocks.findIndex(el => el.getAttribute('data-block-id') === startBlockId);
            const endIndex = allBlocks.findIndex(el => el.getAttribute('data-block-id') === endBlockId);
            
            if (startIndex === -1 || endIndex === -1) return;
            
            const start = Math.min(startIndex, endIndex);
            const end = Math.max(startIndex, endIndex);
            
            this.clearSelection();
            
            for (let i = start; i <= end; i++) {
                const blockElement = allBlocks[i];
                const blockId = blockElement.getAttribute('data-block-id');
                this.selectedBlocks.add(blockId);
                blockElement.classList.add('block-selected');
            }
            
            this.lastSelectedBlock = endBlockId;
            this.emitSelectionChange();
        }

        /**
         * Select all blocks
         */
        selectAllBlocks() {
            this.clearSelection();
            
            const allBlocks = this.container.querySelectorAll('.editor-block');
            allBlocks.forEach(blockElement => {
                const blockId = blockElement.getAttribute('data-block-id');
                this.selectedBlocks.add(blockId);
                blockElement.classList.add('block-selected');
            });
            
            this.emitSelectionChange();
        }

        /**
         * Clear all selections
         */
        clearSelection() {
            this.selectedBlocks.forEach(blockId => {
                const blockElement = this.container.querySelector(`[data-block-id="${blockId}"]`);
                if (blockElement) {
                    blockElement.classList.remove('block-selected');
                }
            });
            
            this.selectedBlocks.clear();
            this.emitSelectionChange();
        }

        /**
         * Set focused block
         */
        setFocusedBlock(blockId, blockElement) {
            // Clear previous focus
            if (this.focusedBlock) {
                const prevElement = this.container.querySelector(`[data-block-id="${this.focusedBlock}"]`);
                if (prevElement) {
                    prevElement.classList.remove('block-focused');
                }
            }
            
            this.focusedBlock = blockId;
            
            if (blockElement) {
                blockElement.classList.add('block-focused');
            }
            
            this.emitFocusChange();
        }

        /**
         * Clear focus
         */
        clearFocus() {
            if (this.focusedBlock) {
                const blockElement = this.container.querySelector(`[data-block-id="${this.focusedBlock}"]`);
                if (blockElement) {
                    blockElement.classList.remove('block-focused');
                }
            }
            
            this.focusedBlock = null;
            this.emitFocusChange();
        }

        /**
         * Select previous block
         */
        selectPreviousBlock() {
            if (!this.focusedBlock) return;
            
            const allBlocks = Array.from(this.container.querySelectorAll('.editor-block'));
            const currentIndex = allBlocks.findIndex(el => el.getAttribute('data-block-id') === this.focusedBlock);
            
            if (currentIndex > 0) {
                const prevBlock = allBlocks[currentIndex - 1];
                const prevBlockId = prevBlock.getAttribute('data-block-id');
                this.selectBlock(prevBlockId, prevBlock);
                this.setFocusedBlock(prevBlockId, prevBlock);
                prevBlock.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }

        /**
         * Select next block
         */
        selectNextBlock() {
            if (!this.focusedBlock) return;
            
            const allBlocks = Array.from(this.container.querySelectorAll('.editor-block'));
            const currentIndex = allBlocks.findIndex(el => el.getAttribute('data-block-id') === this.focusedBlock);
            
            if (currentIndex < allBlocks.length - 1) {
                const nextBlock = allBlocks[currentIndex + 1];
                const nextBlockId = nextBlock.getAttribute('data-block-id');
                this.selectBlock(nextBlockId, nextBlock);
                this.setFocusedBlock(nextBlockId, nextBlock);
                nextBlock.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }

        /**
         * Delete selected blocks
         */
        deleteSelectedBlocks() {
            if (this.selectedBlocks.size === 0) return;
            
            const blockIds = Array.from(this.selectedBlocks);
            const blockManager = this.editorController.blockManager;
            
            blockIds.forEach(blockId => {
                blockManager.deleteBlock(blockId);
            });
            
            this.clearSelection();
            this.clearFocus();
        }

        /**
         * Check if currently editing a block
         */
        isEditingBlock() {
            const activeElement = document.activeElement;
            return activeElement && (
                activeElement.isContentEditable ||
                activeElement.tagName === 'INPUT' ||
                activeElement.tagName === 'TEXTAREA'
            );
        }

        /**
         * Get selected block IDs
         */
        getSelectedBlocks() {
            return Array.from(this.selectedBlocks);
        }

        /**
         * Get focused block ID
         */
        getFocusedBlock() {
            return this.focusedBlock;
        }

        /**
         * Check if a block is selected
         */
        isBlockSelected(blockId) {
            return this.selectedBlocks.has(blockId);
        }

        /**
         * Check if a block is focused
         */
        isBlockFocused(blockId) {
            return this.focusedBlock === blockId;
        }

        /**
         * Emit selection change event
         */
        emitSelectionChange() {
            if (this.editorController) {
                this.editorController.emit('selectionChanged', {
                    selectedBlocks: this.getSelectedBlocks(),
                    count: this.selectedBlocks.size
                });
            }
        }

        /**
         * Emit focus change event
         */
        emitFocusChange() {
            if (this.editorController) {
                this.editorController.emit('focusChanged', {
                    focusedBlock: this.focusedBlock
                });
            }
        }

        /**
         * Destroy the selection manager
         */
        destroy() {
            this.clearSelection();
            this.clearFocus();
            
            // Remove event listeners
            this.container.removeEventListener('click', this.handleClick);
            document.removeEventListener('keydown', this.handleKeyDown);
            this.container.removeEventListener('focusin', this.handleFocusIn);
            this.container.removeEventListener('focusout', this.handleFocusOut);
            
            this.editorController = null;
            this.container = null;
        }
    }

    // Export to global scope
    window.BlockSelectionManager = BlockSelectionManager;

})(window);
