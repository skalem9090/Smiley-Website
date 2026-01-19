/**
 * Advanced Editor System - Block Actions
 * 
 * This module provides UI controls and actions for block operations
 * like duplication, deletion, and other block-level actions.
 */

(function(window) {
    'use strict';

    /**
     * BlockActionsManager - Manages block action UI and operations
     */
    class BlockActionsManager {
        constructor(editorController, containerElement) {
            this.editorController = editorController;
            this.container = containerElement;
            this.actionMenu = null;
            this.currentBlock = null;
            
            this.setupEventListeners();
        }

        /**
         * Set up event listeners
         */
        setupEventListeners() {
            // Show action menu on block hover
            this.container.addEventListener('mouseenter', this.handleBlockHover.bind(this), true);
            this.container.addEventListener('mouseleave', this.handleBlockLeave.bind(this), true);
            
            // Listen for keyboard shortcuts
            document.addEventListener('keydown', this.handleKeyboardShortcuts.bind(this));
        }

        /**
         * Handle block hover
         */
        handleBlockHover(event) {
            const blockElement = event.target.closest('.editor-block');
            if (!blockElement || blockElement === this.currentBlock) return;
            
            this.currentBlock = blockElement;
            this.showActionMenu(blockElement);
        }

        /**
         * Handle block leave
         */
        handleBlockLeave(event) {
            const blockElement = event.target.closest('.editor-block');
            if (!blockElement) return;
            
            // Check if mouse is still over the block or action menu
            const relatedTarget = event.relatedTarget;
            if (relatedTarget && (
                relatedTarget.closest('.editor-block') === blockElement ||
                relatedTarget.closest('.block-action-menu')
            )) {
                return;
            }
            
            this.hideActionMenu();
        }

        /**
         * Handle keyboard shortcuts
         */
        handleKeyboardShortcuts(event) {
            const selectionManager = this.editorController.selectionManager;
            if (!selectionManager) return;
            
            const selectedBlocks = selectionManager.getSelectedBlocks();
            if (selectedBlocks.length === 0) return;
            
            // Ctrl/Cmd + D for duplicate
            if ((event.ctrlKey || event.metaKey) && event.key === 'd') {
                event.preventDefault();
                this.duplicateSelectedBlocks();
            }
            
            // Ctrl/Cmd + Shift + D for delete
            if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'D') {
                event.preventDefault();
                this.deleteSelectedBlocks();
            }
        }

        /**
         * Show action menu for a block
         */
        showActionMenu(blockElement) {
            // Remove existing menu
            this.hideActionMenu();
            
            // Create action menu
            this.actionMenu = document.createElement('div');
            this.actionMenu.className = 'block-action-menu';
            
            // Add action buttons
            const actions = [
                { icon: '⊕', label: 'Add Block', action: 'add' },
                { icon: '⎘', label: 'Duplicate', action: 'duplicate' },
                { icon: '🗑', label: 'Delete', action: 'delete' },
                { icon: '↑', label: 'Move Up', action: 'moveUp' },
                { icon: '↓', label: 'Move Down', action: 'moveDown' }
            ];
            
            actions.forEach(actionDef => {
                const button = document.createElement('button');
                button.className = 'block-action-button';
                button.innerHTML = actionDef.icon;
                button.title = actionDef.label;
                button.setAttribute('data-action', actionDef.action);
                button.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.handleAction(actionDef.action, blockElement);
                });
                this.actionMenu.appendChild(button);
            });
            
            // Position menu
            blockElement.appendChild(this.actionMenu);
        }

        /**
         * Hide action menu
         */
        hideActionMenu() {
            if (this.actionMenu && this.actionMenu.parentNode) {
                this.actionMenu.parentNode.removeChild(this.actionMenu);
            }
            this.actionMenu = null;
            this.currentBlock = null;
        }

        /**
         * Handle action button click
         */
        handleAction(action, blockElement) {
            const blockId = blockElement.getAttribute('data-block-id');
            if (!blockId) return;
            
            switch (action) {
                case 'add':
                    this.addBlockAfter(blockId);
                    break;
                case 'duplicate':
                    this.duplicateBlock(blockId);
                    break;
                case 'delete':
                    this.deleteBlock(blockId);
                    break;
                case 'moveUp':
                    this.moveBlockUp(blockId);
                    break;
                case 'moveDown':
                    this.moveBlockDown(blockId);
                    break;
            }
            
            this.hideActionMenu();
        }

        /**
         * Add a new block after the specified block
         */
        addBlockAfter(blockId) {
            const blockManager = this.editorController.blockManager;
            const position = blockManager.blockCollection.getPosition(blockId);
            
            const newBlock = blockManager.createBlock(window.BlockType.PARAGRAPH, {
                position: position + 1,
                content: { text: '' }
            });
            
            this.emitBlockAdded(newBlock);
        }

        /**
         * Duplicate a block
         */
        duplicateBlock(blockId) {
            const blockManager = this.editorController.blockManager;
            
            try {
                const duplicatedBlock = blockManager.duplicateBlock(blockId);
                this.emitBlockDuplicated(blockId, duplicatedBlock);
            } catch (error) {
                console.error('Failed to duplicate block:', error);
            }
        }

        /**
         * Delete a block
         */
        deleteBlock(blockId) {
            const blockManager = this.editorController.blockManager;
            
            // Confirm deletion
            if (confirm('Are you sure you want to delete this block?')) {
                const deleted = blockManager.deleteBlock(blockId);
                if (deleted) {
                    this.emitBlockDeleted(blockId);
                }
            }
        }

        /**
         * Move block up
         */
        moveBlockUp(blockId) {
            const blockManager = this.editorController.blockManager;
            const currentPosition = blockManager.blockCollection.getPosition(blockId);
            
            if (currentPosition > 0) {
                blockManager.moveBlock(blockId, currentPosition - 1);
                this.emitBlockMoved(blockId, currentPosition - 1);
            }
        }

        /**
         * Move block down
         */
        moveBlockDown(blockId) {
            const blockManager = this.editorController.blockManager;
            const currentPosition = blockManager.blockCollection.getPosition(blockId);
            const totalBlocks = blockManager.getBlockCount();
            
            if (currentPosition < totalBlocks - 1) {
                blockManager.moveBlock(blockId, currentPosition + 1);
                this.emitBlockMoved(blockId, currentPosition + 1);
            }
        }

        /**
         * Duplicate selected blocks
         */
        duplicateSelectedBlocks() {
            const selectionManager = this.editorController.selectionManager;
            if (!selectionManager) return;
            
            const selectedBlocks = selectionManager.getSelectedBlocks();
            selectedBlocks.forEach(blockId => {
                this.duplicateBlock(blockId);
            });
        }

        /**
         * Delete selected blocks
         */
        deleteSelectedBlocks() {
            const selectionManager = this.editorController.selectionManager;
            if (!selectionManager) return;
            
            const selectedBlocks = selectionManager.getSelectedBlocks();
            
            if (confirm(`Are you sure you want to delete ${selectedBlocks.length} block(s)?`)) {
                selectedBlocks.forEach(blockId => {
                    this.deleteBlock(blockId);
                });
            }
        }

        /**
         * Emit block added event
         */
        emitBlockAdded(block) {
            if (this.editorController) {
                this.editorController.emit('blockAdded', { block });
            }
        }

        /**
         * Emit block duplicated event
         */
        emitBlockDuplicated(originalId, duplicatedBlock) {
            if (this.editorController) {
                this.editorController.emit('blockDuplicated', {
                    originalId,
                    duplicatedBlock
                });
            }
        }

        /**
         * Emit block deleted event
         */
        emitBlockDeleted(blockId) {
            if (this.editorController) {
                this.editorController.emit('blockDeleted', { blockId });
            }
        }

        /**
         * Emit block moved event
         */
        emitBlockMoved(blockId, newPosition) {
            if (this.editorController) {
                this.editorController.emit('blockMoved', {
                    blockId,
                    newPosition
                });
            }
        }

        /**
         * Destroy the actions manager
         */
        destroy() {
            this.hideActionMenu();
            
            // Remove event listeners
            this.container.removeEventListener('mouseenter', this.handleBlockHover, true);
            this.container.removeEventListener('mouseleave', this.handleBlockLeave, true);
            document.removeEventListener('keydown', this.handleKeyboardShortcuts);
            
            this.editorController = null;
            this.container = null;
        }
    }

    // Export to global scope
    window.BlockActionsManager = BlockActionsManager;

})(window);
