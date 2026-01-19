/**
 * Advanced Editor System - Block Drag and Drop
 * 
 * This module implements drag-and-drop functionality for reordering blocks
 * in the editor.
 */

(function(window) {
    'use strict';

    /**
     * BlockDragDropManager - Manages drag and drop for blocks
     */
    class BlockDragDropManager {
        constructor(editorController, containerElement) {
            this.editorController = editorController;
            this.container = containerElement;
            this.draggedBlock = null;
            this.draggedElement = null;
            this.dropIndicator = null;
            this.dropPosition = null;
            
            this.createDropIndicator();
            this.setupEventListeners();
        }

        /**
         * Create drop indicator element
         */
        createDropIndicator() {
            this.dropIndicator = document.createElement('div');
            this.dropIndicator.className = 'block-drop-indicator';
            this.dropIndicator.style.display = 'none';
        }

        /**
         * Set up event listeners for drag and drop
         */
        setupEventListeners() {
            // Make blocks draggable
            this.container.addEventListener('mousedown', this.handleMouseDown.bind(this));
            
            // Drag events
            this.container.addEventListener('dragstart', this.handleDragStart.bind(this));
            this.container.addEventListener('dragend', this.handleDragEnd.bind(this));
            this.container.addEventListener('dragover', this.handleDragOver.bind(this));
            this.container.addEventListener('drop', this.handleDrop.bind(this));
            this.container.addEventListener('dragleave', this.handleDragLeave.bind(this));
        }

        /**
         * Handle mouse down to add drag handle
         */
        handleMouseDown(event) {
            const blockElement = event.target.closest('.editor-block');
            if (!blockElement) return;

            // Check if clicking on drag handle area (left side)
            const rect = blockElement.getBoundingClientRect();
            const clickX = event.clientX - rect.left;
            
            if (clickX < 30) {
                blockElement.setAttribute('draggable', 'true');
                blockElement.classList.add('draggable');
            } else {
                blockElement.setAttribute('draggable', 'false');
                blockElement.classList.remove('draggable');
            }
        }

        /**
         * Handle drag start
         */
        handleDragStart(event) {
            const blockElement = event.target.closest('.editor-block');
            if (!blockElement) return;

            this.draggedElement = blockElement;
            this.draggedBlock = blockElement.getAttribute('data-block-id');
            
            blockElement.classList.add('dragging');
            
            // Set drag data
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', this.draggedBlock);
            
            // Add drop indicator to container
            this.container.appendChild(this.dropIndicator);
            
            this.emitDragStart();
        }

        /**
         * Handle drag over
         */
        handleDragOver(event) {
            event.preventDefault();
            event.dataTransfer.dropEffect = 'move';
            
            const blockElement = event.target.closest('.editor-block');
            if (!blockElement || blockElement === this.draggedElement) {
                this.hideDropIndicator();
                return;
            }
            
            // Calculate drop position
            const rect = blockElement.getBoundingClientRect();
            const midpoint = rect.top + rect.height / 2;
            const dropBefore = event.clientY < midpoint;
            
            this.showDropIndicator(blockElement, dropBefore);
            this.dropPosition = {
                targetBlock: blockElement.getAttribute('data-block-id'),
                before: dropBefore
            };
        }

        /**
         * Handle drag leave
         */
        handleDragLeave(event) {
            const blockElement = event.target.closest('.editor-block');
            if (!blockElement) {
                this.hideDropIndicator();
            }
        }

        /**
         * Handle drop
         */
        handleDrop(event) {
            event.preventDefault();
            event.stopPropagation();
            
            if (!this.draggedBlock || !this.dropPosition) {
                this.cleanup();
                return;
            }
            
            const blockManager = this.editorController.blockManager;
            const allBlocks = blockManager.getAllBlocks();
            
            // Find current and target positions
            const currentIndex = allBlocks.findIndex(b => b.id === this.draggedBlock);
            const targetIndex = allBlocks.findIndex(b => b.id === this.dropPosition.targetBlock);
            
            if (currentIndex === -1 || targetIndex === -1) {
                this.cleanup();
                return;
            }
            
            // Calculate new position
            let newPosition = targetIndex;
            if (!this.dropPosition.before) {
                newPosition++;
            }
            if (currentIndex < targetIndex) {
                newPosition--;
            }
            
            // Move the block
            blockManager.moveBlock(this.draggedBlock, newPosition);
            
            // Re-render blocks
            this.reorderBlockElements();
            
            this.emitDrop();
            this.cleanup();
        }

        /**
         * Handle drag end
         */
        handleDragEnd(event) {
            this.cleanup();
        }

        /**
         * Show drop indicator
         */
        showDropIndicator(targetElement, before) {
            this.dropIndicator.style.display = 'block';
            
            if (before) {
                targetElement.parentNode.insertBefore(this.dropIndicator, targetElement);
            } else {
                targetElement.parentNode.insertBefore(this.dropIndicator, targetElement.nextSibling);
            }
        }

        /**
         * Hide drop indicator
         */
        hideDropIndicator() {
            this.dropIndicator.style.display = 'none';
        }

        /**
         * Reorder block elements in DOM
         */
        reorderBlockElements() {
            const blockManager = this.editorController.blockManager;
            const orderedBlocks = blockManager.getAllBlocks();
            
            // Get all block elements
            const blockElements = new Map();
            this.container.querySelectorAll('.editor-block').forEach(el => {
                const id = el.getAttribute('data-block-id');
                blockElements.set(id, el);
            });
            
            // Clear container
            const fragment = document.createDocumentFragment();
            
            // Add blocks in correct order
            orderedBlocks.forEach(block => {
                const element = blockElements.get(block.id);
                if (element) {
                    fragment.appendChild(element);
                }
            });
            
            this.container.innerHTML = '';
            this.container.appendChild(fragment);
        }

        /**
         * Cleanup after drag operation
         */
        cleanup() {
            if (this.draggedElement) {
                this.draggedElement.classList.remove('dragging');
                this.draggedElement.setAttribute('draggable', 'false');
            }
            
            this.hideDropIndicator();
            
            if (this.dropIndicator.parentNode) {
                this.dropIndicator.parentNode.removeChild(this.dropIndicator);
            }
            
            this.draggedBlock = null;
            this.draggedElement = null;
            this.dropPosition = null;
        }

        /**
         * Enable drag and drop
         */
        enable() {
            this.container.classList.add('drag-drop-enabled');
        }

        /**
         * Disable drag and drop
         */
        disable() {
            this.container.classList.remove('drag-drop-enabled');
            this.cleanup();
        }

        /**
         * Emit drag start event
         */
        emitDragStart() {
            if (this.editorController) {
                this.editorController.emit('blockDragStart', {
                    blockId: this.draggedBlock
                });
            }
        }

        /**
         * Emit drop event
         */
        emitDrop() {
            if (this.editorController) {
                this.editorController.emit('blockDropped', {
                    blockId: this.draggedBlock,
                    newPosition: this.dropPosition
                });
            }
        }

        /**
         * Destroy the drag-drop manager
         */
        destroy() {
            this.cleanup();
            
            // Remove event listeners
            this.container.removeEventListener('mousedown', this.handleMouseDown);
            this.container.removeEventListener('dragstart', this.handleDragStart);
            this.container.removeEventListener('dragend', this.handleDragEnd);
            this.container.removeEventListener('dragover', this.handleDragOver);
            this.container.removeEventListener('drop', this.handleDrop);
            this.container.removeEventListener('dragleave', this.handleDragLeave);
            
            if (this.dropIndicator && this.dropIndicator.parentNode) {
                this.dropIndicator.parentNode.removeChild(this.dropIndicator);
            }
            
            this.editorController = null;
            this.container = null;
        }
    }

    // Export to global scope
    window.BlockDragDropManager = BlockDragDropManager;

})(window);
