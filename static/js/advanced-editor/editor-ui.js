/**
 * Advanced Editor System - UI Components
 * 
 * This module provides the user interface components for the advanced editor,
 * including toolbar, sidebar, and other interactive elements.
 */

(function(window) {
    'use strict';

    /**
     * EditorToolbar - Provides formatting controls and tools
     */
    class EditorToolbar {
        constructor(editorController, container) {
            this.editorController = editorController;
            this.container = container;
            this.isInitialized = false;
            this.buttons = new Map();
        }

        /**
         * Initialize the toolbar
         */
        initialize() {
            if (!this.container) {
                throw new Error('Toolbar container is required');
            }

            this.createToolbarStructure();
            this.setupEventListeners();
            this.isInitialized = true;
        }

        /**
         * Create the toolbar HTML structure
         */
        createToolbarStructure() {
            this.container.className = 'editor-toolbar';
            this.container.innerHTML = `
                <div class="toolbar-section toolbar-formatting">
                    <button type="button" class="toolbar-btn" data-command="toggleBold" title="Bold (Ctrl+B)">
                        <strong>B</strong>
                    </button>
                    <button type="button" class="toolbar-btn" data-command="toggleItalic" title="Italic (Ctrl+I)">
                        <em>I</em>
                    </button>
                    <button type="button" class="toolbar-btn" data-command="toggleStrike" title="Strikethrough">
                        <s>S</s>
                    </button>
                    <div class="toolbar-separator"></div>
                    <button type="button" class="toolbar-btn" data-command="toggleCode" title="Inline Code">
                        &lt;/&gt;
                    </button>
                </div>
                
                <div class="toolbar-section toolbar-structure">
                    <div class="toolbar-separator"></div>
                    <select class="toolbar-select" data-command="setHeading" title="Heading Level">
                        <option value="paragraph">Paragraph</option>
                        <option value="1">Heading 1</option>
                        <option value="2">Heading 2</option>
                        <option value="3">Heading 3</option>
                        <option value="4">Heading 4</option>
                        <option value="5">Heading 5</option>
                        <option value="6">Heading 6</option>
                    </select>
                    <div class="toolbar-separator"></div>
                    <button type="button" class="toolbar-btn" data-command="toggleBulletList" title="Bullet List">
                        • List
                    </button>
                    <button type="button" class="toolbar-btn" data-command="toggleOrderedList" title="Numbered List">
                        1. List
                    </button>
                    <button type="button" class="toolbar-btn" data-command="toggleBlockquote" title="Quote">
                        " Quote
                    </button>
                </div>
                
                <div class="toolbar-section toolbar-media">
                    <div class="toolbar-separator"></div>
                    <button type="button" class="toolbar-btn" data-command="addCodeBlock" title="Code Block">
                        📝 Code
                    </button>
                </div>
                
                <div class="toolbar-section toolbar-actions">
                    <div class="toolbar-separator"></div>
                    <button type="button" class="toolbar-btn" data-command="undo" title="Undo (Ctrl+Z)">
                        ↶ Undo
                    </button>
                    <button type="button" class="toolbar-btn" data-command="redo" title="Redo (Ctrl+Y)">
                        ↷ Redo
                    </button>
                    <div class="toolbar-separator"></div>
                    <button type="button" class="toolbar-btn toolbar-mode-toggle" data-command="toggleMode" title="Toggle Mode">
                        📝 Mode
                    </button>
                </div>
            `;
        }

        /**
         * Set up event listeners for toolbar interactions
         */
        setupEventListeners() {
            // Handle button clicks
            this.container.addEventListener('click', (event) => {
                const button = event.target.closest('.toolbar-btn');
                if (button) {
                    event.preventDefault();
                    const command = button.dataset.command;
                    this.executeCommand(command, button);
                }
            });

            // Handle select changes
            this.container.addEventListener('change', (event) => {
                if (event.target.classList.contains('toolbar-select')) {
                    const command = event.target.dataset.command;
                    const value = event.target.value;
                    this.executeCommand(command, event.target, value);
                }
            });

            // Update toolbar state when editor selection changes
            if (this.editorController.editor) {
                this.editorController.editor.on('selectionUpdate', () => {
                    this.updateToolbarState();
                });
            }
        }

        /**
         * Execute a toolbar command
         */
        executeCommand(command, element, value = null) {
            if (!this.editorController.isReady()) return;

            const editor = this.editorController.editor;

            switch (command) {
                case 'toggleBold':
                    editor.chain().focus().toggleBold().run();
                    break;
                case 'toggleItalic':
                    editor.chain().focus().toggleItalic().run();
                    break;
                case 'toggleStrike':
                    editor.chain().focus().toggleStrike().run();
                    break;
                case 'toggleCode':
                    editor.chain().focus().toggleCode().run();
                    break;
                case 'setHeading':
                    if (value === 'paragraph') {
                        editor.chain().focus().setParagraph().run();
                    } else {
                        editor.chain().focus().toggleHeading({ level: parseInt(value) }).run();
                    }
                    break;
                case 'toggleBulletList':
                    editor.chain().focus().toggleBulletList().run();
                    break;
                case 'toggleOrderedList':
                    editor.chain().focus().toggleOrderedList().run();
                    break;
                case 'toggleBlockquote':
                    editor.chain().focus().toggleBlockquote().run();
                    break;
                case 'addCodeBlock':
                    editor.chain().focus().toggleCodeBlock().run();
                    break;
                case 'undo':
                    editor.chain().focus().undo().run();
                    break;
                case 'redo':
                    editor.chain().focus().redo().run();
                    break;
                case 'toggleMode':
                    this.toggleEditingMode();
                    break;
                default:
                    console.warn(`Unknown toolbar command: ${command}`);
            }

            this.updateToolbarState();
        }

        /**
         * Update toolbar button states based on current selection
         */
        updateToolbarState() {
            if (!this.editorController.isReady()) return;

            const editor = this.editorController.editor;

            // Update button active states
            this.updateButtonState('toggleBold', editor.isActive('bold'));
            this.updateButtonState('toggleItalic', editor.isActive('italic'));
            this.updateButtonState('toggleStrike', editor.isActive('strike'));
            this.updateButtonState('toggleCode', editor.isActive('code'));
            this.updateButtonState('toggleBulletList', editor.isActive('bulletList'));
            this.updateButtonState('toggleOrderedList', editor.isActive('orderedList'));
            this.updateButtonState('toggleBlockquote', editor.isActive('blockquote'));

            // Update heading select
            const headingSelect = this.container.querySelector('[data-command="setHeading"]');
            if (headingSelect) {
                let selectedValue = 'paragraph';
                for (let level = 1; level <= 6; level++) {
                    if (editor.isActive('heading', { level })) {
                        selectedValue = level.toString();
                        break;
                    }
                }
                headingSelect.value = selectedValue;
            }

            // Update undo/redo buttons
            this.updateButtonState('undo', editor.can().undo());
            this.updateButtonState('redo', editor.can().redo());
        }

        /**
         * Update individual button state
         */
        updateButtonState(command, isActive) {
            const button = this.container.querySelector(`[data-command="${command}"]`);
            if (button) {
                button.classList.toggle('active', isActive);
                if (command === 'undo' || command === 'redo') {
                    button.disabled = !isActive;
                }
            }
        }

        /**
         * Show image insertion dialog
         */
        showImageDialog() {
            const url = prompt('Enter image URL:');
            if (url) {
                this.editorController.editor.chain().focus().setImage({ src: url }).run();
            }
        }

        /**
         * Show link insertion dialog
         */
        showLinkDialog() {
            const url = prompt('Enter link URL:');
            if (url) {
                this.editorController.editor.chain().focus().setLink({ href: url }).run();
            }
        }

        /**
         * Toggle editing mode
         */
        toggleEditingMode() {
            const currentMode = this.editorController.getCurrentMode();
            const newMode = currentMode === 'wysiwyg' ? 'markdown' : 'wysiwyg';
            this.editorController.switchMode(newMode);
        }

        /**
         * Destroy the toolbar
         */
        destroy() {
            if (this.container) {
                this.container.innerHTML = '';
                this.container.className = '';
            }
            this.buttons.clear();
            this.editorController = null;
            this.isInitialized = false;
        }
    }

    /**
     * EditorSidebar - Provides additional tools and information
     */
    class EditorSidebar {
        constructor(editorController, container) {
            this.editorController = editorController;
            this.container = container;
            this.isInitialized = false;
            this.panels = new Map();
        }

        /**
         * Initialize the sidebar
         */
        initialize() {
            if (!this.container) {
                throw new Error('Sidebar container is required');
            }

            this.createSidebarStructure();
            this.setupEventListeners();
            this.isInitialized = true;
        }

        /**
         * Create the sidebar HTML structure
         */
        createSidebarStructure() {
            this.container.className = 'editor-sidebar';
            this.container.innerHTML = `
                <div class="sidebar-header">
                    <h3>Editor Tools</h3>
                    <button type="button" class="sidebar-toggle" title="Toggle Sidebar">×</button>
                </div>
                
                <div class="sidebar-content">
                    <div class="sidebar-panel" data-panel="document">
                        <h4>Document Info</h4>
                        <div class="document-stats">
                            <div class="stat-item">
                                <span class="stat-label">Words:</span>
                                <span class="stat-value" id="word-count">0</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Characters:</span>
                                <span class="stat-value" id="char-count">0</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Paragraphs:</span>
                                <span class="stat-value" id="paragraph-count">0</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="sidebar-panel" data-panel="outline">
                        <h4>Document Outline</h4>
                        <div class="outline-content" id="document-outline">
                            <p class="muted">No headings found</p>
                        </div>
                    </div>
                    
                    <div class="sidebar-panel" data-panel="help">
                        <h4>Keyboard Shortcuts</h4>
                        <div class="shortcuts-list">
                            <div class="shortcut-item">
                                <kbd>Ctrl+B</kbd> Bold
                            </div>
                            <div class="shortcut-item">
                                <kbd>Ctrl+I</kbd> Italic
                            </div>
                            <div class="shortcut-item">
                                <kbd>Ctrl+U</kbd> Underline
                            </div>
                            <div class="shortcut-item">
                                <kbd>Ctrl+Z</kbd> Undo
                            </div>
                            <div class="shortcut-item">
                                <kbd>Ctrl+Y</kbd> Redo
                            </div>
                            <div class="shortcut-item">
                                <kbd>Ctrl+Shift+M</kbd> Toggle Mode
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        /**
         * Set up event listeners for sidebar interactions
         */
        setupEventListeners() {
            // Handle sidebar toggle
            const toggleButton = this.container.querySelector('.sidebar-toggle');
            if (toggleButton) {
                toggleButton.addEventListener('click', () => {
                    this.container.classList.toggle('collapsed');
                });
            }

            // Update sidebar content when editor content changes
            if (this.editorController.editor) {
                this.editorController.editor.on('update', () => {
                    this.updateDocumentStats();
                    this.updateDocumentOutline();
                });
            }

            // Initial update
            this.updateDocumentStats();
            this.updateDocumentOutline();
        }

        /**
         * Update document statistics
         */
        updateDocumentStats() {
            if (!this.editorController.isReady()) return;

            const content = this.editorController.getContent();
            const text = content.text;

            // Count words (split by whitespace and filter empty strings)
            const words = text.split(/\s+/).filter(word => word.length > 0);
            const wordCount = words.length;

            // Count characters (excluding whitespace)
            const charCount = text.replace(/\s/g, '').length;

            // Count paragraphs (split by double newlines or paragraph tags)
            const paragraphs = content.html.split(/<\/p>|<br\s*\/?>/i).filter(p => p.trim().length > 0);
            const paragraphCount = paragraphs.length;

            // Update display
            const wordCountEl = this.container.querySelector('#word-count');
            const charCountEl = this.container.querySelector('#char-count');
            const paragraphCountEl = this.container.querySelector('#paragraph-count');

            if (wordCountEl) wordCountEl.textContent = wordCount;
            if (charCountEl) charCountEl.textContent = charCount;
            if (paragraphCountEl) paragraphCountEl.textContent = paragraphCount;
        }

        /**
         * Update document outline based on headings
         */
        updateDocumentOutline() {
            if (!this.editorController.isReady()) return;

            const content = this.editorController.getContent();
            const outlineContainer = this.container.querySelector('#document-outline');
            
            if (!outlineContainer) return;

            // Extract headings from HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = content.html;
            const headings = tempDiv.querySelectorAll('h1, h2, h3, h4, h5, h6');

            if (headings.length === 0) {
                outlineContainer.innerHTML = '<p class="muted">No headings found</p>';
                return;
            }

            // Build outline HTML
            let outlineHTML = '<ul class="outline-list">';
            headings.forEach((heading, index) => {
                const level = parseInt(heading.tagName.charAt(1));
                const text = heading.textContent.trim();
                const id = `heading-${index}`;
                
                outlineHTML += `
                    <li class="outline-item outline-level-${level}">
                        <a href="#${id}" class="outline-link">${text}</a>
                    </li>
                `;
            });
            outlineHTML += '</ul>';

            outlineContainer.innerHTML = outlineHTML;

            // Add click handlers for outline navigation
            outlineContainer.querySelectorAll('.outline-link').forEach((link, index) => {
                link.addEventListener('click', (event) => {
                    event.preventDefault();
                    // Focus on the corresponding heading in the editor
                    // This would need more sophisticated implementation
                    this.editorController.focus();
                });
            });
        }

        /**
         * Destroy the sidebar
         */
        destroy() {
            if (this.container) {
                this.container.innerHTML = '';
                this.container.className = '';
            }
            this.panels.clear();
            this.editorController = null;
            this.isInitialized = false;
        }
    }

    // Export classes to global scope
    window.EditorToolbar = EditorToolbar;
    window.EditorSidebar = EditorSidebar;

})(window);