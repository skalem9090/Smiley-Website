/**
 * Advanced Editor System - Mode Switcher UI
 * 
 * This module provides the UI controls for switching between
 * WYSIWYG and Markdown editing modes.
 */

(function(window) {
    'use strict';

    /**
     * ModeSwitcher - UI for mode switching
     */
    class ModeSwitcher {
        constructor(editorController, containerElement) {
            this.editorController = editorController;
            this.container = containerElement;
            this.modeConverter = new window.ModeConverter(editorController);
            this.currentMode = 'wysiwyg';
            this.wysiwygEditor = null;
            this.markdownEditor = null;
            
            this.createUI();
            this.setupEventListeners();
        }

        /**
         * Create mode switcher UI
         */
        createUI() {
            // Create mode switcher container
            const switcherContainer = document.createElement('div');
            switcherContainer.className = 'mode-switcher-container';
            
            // Create mode buttons
            const wysiwygButton = document.createElement('button');
            wysiwygButton.className = 'mode-button mode-button-active';
            wysiwygButton.setAttribute('data-mode', 'wysiwyg');
            wysiwygButton.innerHTML = `
                <span class="mode-icon">👁</span>
                <span class="mode-label">Visual</span>
            `;
            
            const markdownButton = document.createElement('button');
            markdownButton.className = 'mode-button';
            markdownButton.setAttribute('data-mode', 'markdown');
            markdownButton.innerHTML = `
                <span class="mode-icon">⌨</span>
                <span class="mode-label">Markdown</span>
            `;
            
            switcherContainer.appendChild(wysiwygButton);
            switcherContainer.appendChild(markdownButton);
            
            // Create editor containers
            const editorsContainer = document.createElement('div');
            editorsContainer.className = 'editors-container';
            
            // WYSIWYG editor container
            const wysiwygContainer = document.createElement('div');
            wysiwygContainer.className = 'wysiwyg-editor-container editor-active';
            wysiwygContainer.id = 'wysiwyg-editor';
            
            // Markdown editor container
            const markdownContainer = document.createElement('div');
            markdownContainer.className = 'markdown-editor-container';
            markdownContainer.id = 'markdown-editor';
            
            const markdownTextarea = document.createElement('textarea');
            markdownTextarea.className = 'markdown-textarea';
            markdownTextarea.placeholder = 'Write your content in Markdown...';
            markdownContainer.appendChild(markdownTextarea);
            
            editorsContainer.appendChild(wysiwygContainer);
            editorsContainer.appendChild(markdownContainer);
            
            // Add to container
            this.container.appendChild(switcherContainer);
            this.container.appendChild(editorsContainer);
            
            // Store references
            this.wysiwygEditor = wysiwygContainer;
            this.markdownEditor = markdownTextarea;
            this.switcherButtons = { wysiwygButton, markdownButton };
        }

        /**
         * Set up event listeners
         */
        setupEventListeners() {
            // Mode button clicks
            this.switcherButtons.wysiwygButton.addEventListener('click', () => {
                this.switchToMode('wysiwyg');
            });
            
            this.switcherButtons.markdownButton.addEventListener('click', () => {
                this.switchToMode('markdown');
            });
            
            // Markdown editor input
            this.markdownEditor.addEventListener('input', () => {
                if (this.currentMode === 'markdown') {
                    this.handleMarkdownInput();
                }
            });
            
            // Keyboard shortcut: Ctrl/Cmd + Shift + M
            document.addEventListener('keydown', (event) => {
                if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'M') {
                    event.preventDefault();
                    this.toggleMode();
                }
            });
        }

        /**
         * Switch to specified mode
         * @param {string} mode - Target mode ('wysiwyg' or 'markdown')
         */
        switchToMode(mode) {
            if (mode === this.currentMode) return;
            
            try {
                if (mode === 'markdown') {
                    // Convert WYSIWYG to Markdown
                    const markdown = this.modeConverter.convertToMarkdown();
                    this.markdownEditor.value = markdown;
                    
                    // Update UI
                    this.wysiwygEditor.parentElement.classList.remove('editor-active');
                    this.markdownEditor.parentElement.classList.add('editor-active');
                    this.switcherButtons.wysiwygButton.classList.remove('mode-button-active');
                    this.switcherButtons.markdownButton.classList.add('mode-button-active');
                    
                } else if (mode === 'wysiwyg') {
                    // Convert Markdown to WYSIWYG
                    const markdown = this.markdownEditor.value;
                    this.modeConverter.convertToWYSIWYG(markdown);
                    
                    // Re-render blocks
                    this.renderWYSIWYGBlocks();
                    
                    // Update UI
                    this.markdownEditor.parentElement.classList.remove('editor-active');
                    this.wysiwygEditor.parentElement.classList.add('editor-active');
                    this.switcherButtons.markdownButton.classList.remove('mode-button-active');
                    this.switcherButtons.wysiwygButton.classList.add('mode-button-active');
                }
                
                this.currentMode = mode;
                this.emitModeChange(mode);
                
            } catch (error) {
                console.error('Error switching modes:', error);
                alert('Failed to switch modes. Please check your content for errors.');
            }
        }

        /**
         * Toggle between modes
         */
        toggleMode() {
            const newMode = this.currentMode === 'wysiwyg' ? 'markdown' : 'wysiwyg';
            this.switchToMode(newMode);
        }

        /**
         * Handle Markdown editor input
         */
        handleMarkdownInput() {
            // Debounce input handling
            clearTimeout(this.inputTimeout);
            this.inputTimeout = setTimeout(() => {
                this.validateMarkdown();
                this.syncToWYSIWYG();
            }, 500);
        }

        /**
         * Sync Markdown changes to WYSIWYG (background sync)
         */
        syncToWYSIWYG() {
            if (this.currentMode !== 'markdown') return;
            
            try {
                const markdown = this.markdownEditor.value;
                const blocks = this.modeConverter.markdownParser.parse(markdown);
                
                // Update block manager silently
                const blockManager = this.editorController.blockManager;
                blockManager.clearAllBlocks();
                blocks.forEach(block => {
                    blockManager.blockCollection.add(block);
                });
                
                this.emitContentSync('markdown', 'wysiwyg');
            } catch (error) {
                console.warn('Sync to WYSIWYG failed:', error);
            }
        }

        /**
         * Sync WYSIWYG changes to Markdown (background sync)
         */
        syncToMarkdown() {
            if (this.currentMode !== 'wysiwyg') return;
            
            try {
                const markdown = this.modeConverter.convertToMarkdown();
                // Don't update the textarea if we're not in markdown mode
                // Just keep it in sync in the background
                this.modeConverter.markdownContent = markdown;
                
                this.emitContentSync('wysiwyg', 'markdown');
            } catch (error) {
                console.warn('Sync to Markdown failed:', error);
            }
        }

        /**
         * Validate Markdown syntax
         */
        validateMarkdown() {
            const markdown = this.markdownEditor.value;
            
            try {
                // Try to parse
                const blocks = this.modeConverter.markdownParser.parse(markdown);
                
                // Clear error state
                this.markdownEditor.classList.remove('markdown-error');
                this.clearErrorMessage();
                
            } catch (error) {
                // Show error state
                this.markdownEditor.classList.add('markdown-error');
                this.showErrorMessage(error.message);
            }
        }

        /**
         * Show error message
         */
        showErrorMessage(message) {
            let errorDiv = this.markdownEditor.parentElement.querySelector('.markdown-error-message');
            
            if (!errorDiv) {
                errorDiv = document.createElement('div');
                errorDiv.className = 'markdown-error-message';
                this.markdownEditor.parentElement.appendChild(errorDiv);
            }
            
            errorDiv.textContent = `Markdown Error: ${message}`;
            errorDiv.style.display = 'block';
        }

        /**
         * Clear error message
         */
        clearErrorMessage() {
            const errorDiv = this.markdownEditor.parentElement.querySelector('.markdown-error-message');
            if (errorDiv) {
                errorDiv.style.display = 'none';
            }
        }

        /**
         * Render WYSIWYG blocks
         */
        renderWYSIWYGBlocks() {
            const blockManager = this.editorController.blockManager;
            const blockRenderer = new window.BlockRenderer(this.editorController);
            
            const blocks = blockManager.getAllBlocks();
            blockRenderer.renderBlocks(blocks, this.wysiwygEditor);
        }

        /**
         * Get current mode
         * @returns {string} Current mode
         */
        getCurrentMode() {
            return this.currentMode;
        }

        /**
         * Get content in current mode
         * @returns {*} Content
         */
        getContent() {
            if (this.currentMode === 'markdown') {
                return this.markdownEditor.value;
            } else {
                return this.editorController.blockManager.getAllBlocks();
            }
        }

        /**
         * Set content
         * @param {*} content - Content to set
         * @param {string} mode - Mode of the content
         */
        setContent(content, mode) {
            if (mode === 'markdown') {
                this.markdownEditor.value = content;
                if (this.currentMode === 'wysiwyg') {
                    this.switchToMode('markdown');
                }
            } else {
                // Assume blocks
                const blockManager = this.editorController.blockManager;
                blockManager.clearAllBlocks();
                content.forEach(block => {
                    blockManager.blockCollection.add(block);
                });
                this.renderWYSIWYGBlocks();
                if (this.currentMode === 'markdown') {
                    this.switchToMode('wysiwyg');
                }
            }
        }

        /**
         * Emit mode change event
         */
        emitModeChange(mode) {
            if (this.editorController) {
                this.editorController.emit('modeChanged', {
                    mode: mode,
                    previousMode: this.currentMode === 'wysiwyg' ? 'markdown' : 'wysiwyg'
                });
            }
        }

        /**
         * Emit content sync event
         */
        emitContentSync(sourceMode, targetMode) {
            if (this.editorController) {
                this.editorController.emit('contentSynced', {
                    sourceMode: sourceMode,
                    targetMode: targetMode,
                    timestamp: new Date()
                });
            }
        }

        /**
         * Destroy the mode switcher
         */
        destroy() {
            clearTimeout(this.inputTimeout);
            
            // Remove event listeners
            this.switcherButtons.wysiwygButton.removeEventListener('click', this.switchToMode);
            this.switcherButtons.markdownButton.removeEventListener('click', this.switchToMode);
            this.markdownEditor.removeEventListener('input', this.handleMarkdownInput);
            
            this.editorController = null;
            this.container = null;
        }
    }

    // Export to global scope
    window.ModeSwitcher = ModeSwitcher;

})(window);
