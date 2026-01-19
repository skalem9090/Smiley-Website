/**
 * Advanced Rich Text Editor
 * A modern, feature-rich editor with block-based content system
 */

(function(window) {
    'use strict';

    /**
     * AdvancedEditor - A sophisticated rich text editor with modern features
     */
    class AdvancedEditor {
        constructor(config = {}) {
            this.config = {
                container: null,
                content: '',
                showToolbar: true,
                showSidebar: true,
                autosave: true,
                autosaveInterval: 30000,
                placeholder: 'Start writing your post...',
                theme: 'papery',
                ...config
            };
            
            this.container = null;
            this.editor = null;
            this.toolbar = null;
            this.sidebar = null;
            this.autosaveTimer = null;
            this.isInitialized = false;
            this.eventListeners = new Map();
            this.blocks = [];
            this.currentBlock = null;
            this.history = [];
            this.historyIndex = -1;
            this.currentMode = 'visual'; // 'visual' or 'markdown'
            this.markdownContent = '';
            this.visualContent = '';
            
            // Bind methods
            this.handleInput = this.handleInput.bind(this);
            this.handleKeyDown = this.handleKeyDown.bind(this);
            this.handlePaste = this.handlePaste.bind(this);
            this.updateStats = this.updateStats.bind(this);
            this.handleSelection = this.handleSelection.bind(this);
        }

        /**
         * Initialize the editor
         */
        async initialize() {
            try {
                // Validate configuration
                if (!this.config.container) {
                    throw new Error('Container element is required');
                }
                
                // Handle different container types with better validation
                if (typeof this.config.container === 'string') {
                    // Validate CSS selector - allow numeric IDs but ensure proper format
                    if (!this.config.container.trim()) {
                        throw new Error('Container selector cannot be empty');
                    }
                    
                    // Try to query the selector, let browser handle validation
                    try {
                        this.container = document.querySelector(this.config.container);
                    } catch (error) {
                        throw new Error(`Invalid container selector format: ${this.config.container}`);
                    }
                } else if (this.config.container instanceof HTMLElement) {
                    this.container = this.config.container;
                } else if (typeof this.config.container === 'number') {
                    throw new Error('Container must be a valid CSS selector string or HTMLElement, not a number');
                } else if (Array.isArray(this.config.container)) {
                    throw new Error('Container must be a valid CSS selector string or HTMLElement, not an array');
                } else if (typeof this.config.container === 'object' && this.config.container !== null) {
                    throw new Error('Container must be a valid CSS selector string or HTMLElement, not an object');
                } else {
                    throw new Error('Container must be a valid CSS selector string or HTMLElement');
                }
                    
                if (!this.container) {
                    throw new Error('Container element not found');
                }

                // Create editor structure
                this.createEditorStructure();
                
                // Initialize components
                this.initializeEditor();
                if (this.config.showToolbar) this.initializeToolbar();
                if (this.config.showSidebar) this.initializeSidebar();
                
                // Set up autosave
                if (this.config.autosave) {
                    this.startAutosave();
                }
                
                this.isInitialized = true;
                this.emit('initialized', { editor: this });
                
                return this;
            } catch (error) {
                console.error('Failed to initialize Advanced Editor:', error);
                throw error;
            }
        }

        /**
         * Create the main editor structure
         */
        createEditorStructure() {
            // Ensure container is a valid DOM element
            if (!this.container || typeof this.container.className === 'undefined') {
                throw new Error('Container must be a valid DOM element');
            }
            
            this.container.className = 'advanced-editor-container';
            this.container.innerHTML = `
                ${this.config.showToolbar ? '<div class="toolbar-container"></div>' : ''}
                <div class="advanced-editor-wrapper">
                    <div class="editor-main">
                        <div class="editor-pane">
                            <div class="editor-content-area" 
                                 contenteditable="true" 
                                 data-placeholder="${this.config.placeholder}"
                                 spellcheck="true"
                                 role="textbox"
                                 aria-multiline="true"
                                 aria-label="Rich text editor">
                            </div>
                            <div class="editor-block-menu" style="display: none;">
                                <button type="button" class="block-btn" data-block="paragraph">¶ Paragraph</button>
                                <button type="button" class="block-btn" data-block="heading1">H1 Heading 1</button>
                                <button type="button" class="block-btn" data-block="heading2">H2 Heading 2</button>
                                <button type="button" class="block-btn" data-block="heading3">H3 Heading 3</button>
                                <button type="button" class="block-btn" data-block="quote">❝ Quote</button>
                                <button type="button" class="block-btn" data-block="code">⌨ Code Block</button>
                                <button type="button" class="block-btn" data-block="list">• Bullet List</button>
                                <button type="button" class="block-btn" data-block="numbered">1. Numbered List</button>
                                <button type="button" class="block-btn" data-block="divider">— Divider</button>
                            </div>
                        </div>
                    </div>
                    ${this.config.showSidebar ? '<div class="sidebar-container"></div>' : ''}
                </div>
            `;
        }

        /**
         * Initialize the main editor
         */
        initializeEditor() {
            this.editor = this.container.querySelector('.editor-content-area');
            this.blockMenu = this.container.querySelector('.editor-block-menu');
            
            // Set initial content
            if (this.config.content) {
                this.editor.innerHTML = this.config.content;
            } else {
                this.editor.innerHTML = '<p><br></p>';
            }
            
            // Add event listeners
            this.editor.addEventListener('input', this.handleInput);
            this.editor.addEventListener('keydown', this.handleKeyDown);
            this.editor.addEventListener('paste', this.handlePaste);
            this.editor.addEventListener('mouseup', this.handleSelection);
            this.editor.addEventListener('keyup', this.handleSelection);
            
            // Handle focus/blur
            this.editor.addEventListener('focus', () => {
                this.container.classList.add('editor-focused');
                this.emit('focus', { editor: this });
            });
            
            this.editor.addEventListener('blur', () => {
                this.container.classList.remove('editor-focused');
                this.hideBlockMenu();
                this.emit('blur', { editor: this });
            });

            // Block menu event listeners
            if (this.blockMenu) {
                this.blockMenu.addEventListener('click', (event) => {
                    const blockBtn = event.target.closest('.block-btn');
                    if (blockBtn) {
                        const blockType = blockBtn.dataset.block;
                        this.insertBlock(blockType);
                        this.hideBlockMenu();
                        this.editor.focus();
                    }
                });
            }

            // Initialize with proper paragraph structure
            this.normalizeContent();
        }

        /**
         * Initialize the toolbar
         */
        initializeToolbar() {
            const toolbarContainer = this.container.querySelector('.toolbar-container');
            if (!toolbarContainer) return;
            
            toolbarContainer.innerHTML = `
                <div class="editor-toolbar">
                    <div class="toolbar-section toolbar-formatting">
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="bold" title="Bold (Ctrl+B)">
                            <span class="btn-icon"><strong>B</strong></span>
                            <span class="btn-label">Bold</span>
                        </button>
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="italic" title="Italic (Ctrl+I)">
                            <span class="btn-icon"><em>I</em></span>
                            <span class="btn-label">Italic</span>
                        </button>
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="underline" title="Underline (Ctrl+U)">
                            <span class="btn-icon"><u>U</u></span>
                            <span class="btn-label">Underline</span>
                        </button>
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="strikeThrough" title="Strikethrough">
                            <span class="btn-icon"><s>S</s></span>
                            <span class="btn-label">Strike</span>
                        </button>
                    </div>
                    
                    <div class="toolbar-section toolbar-alignment">
                        <div class="toolbar-separator"></div>
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="justifyLeft" title="Align Left">
                            <span class="btn-icon">⬅</span>
                            <span class="btn-label">Left</span>
                        </button>
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="justifyCenter" title="Align Center">
                            <span class="btn-icon">↔</span>
                            <span class="btn-label">Center</span>
                        </button>
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="justifyRight" title="Align Right">
                            <span class="btn-icon">➡</span>
                            <span class="btn-label">Right</span>
                        </button>
                    </div>
                    
                    <div class="toolbar-section toolbar-blocks">
                        <div class="toolbar-separator"></div>
                        <select class="toolbar-select toolbar-select-large" data-command="formatBlock" title="Block Type">
                            <option value="">📝 Block Type</option>
                            <option value="p">¶ Paragraph</option>
                            <option value="h1">H1 Heading 1</option>
                            <option value="h2">H2 Heading 2</option>
                            <option value="h3">H3 Heading 3</option>
                            <option value="blockquote">❝ Quote</option>
                            <option value="pre">⌨ Code Block</option>
                        </select>
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="insertUnorderedList" title="Bullet List">
                            <span class="btn-icon">•</span>
                            <span class="btn-label">List</span>
                        </button>
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="insertOrderedList" title="Numbered List">
                            <span class="btn-icon">1.</span>
                            <span class="btn-label">Numbers</span>
                        </button>
                    </div>
                    
                    <div class="toolbar-section toolbar-insert">
                        <div class="toolbar-separator"></div>
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="createLink" title="Insert Link (Ctrl+K)">
                            <span class="btn-icon">🔗</span>
                            <span class="btn-label">Link</span>
                        </button>
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="insertImage" title="Insert Image">
                            <span class="btn-icon">🖼️</span>
                            <span class="btn-label">Image</span>
                        </button>
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="insertHorizontalRule" title="Insert Divider">
                            <span class="btn-icon">➖</span>
                            <span class="btn-label">Divider</span>
                        </button>
                    </div>
                    
                    <div class="toolbar-section toolbar-actions">
                        <div class="toolbar-separator"></div>
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="undo" title="Undo (Ctrl+Z)">
                            <span class="btn-icon">↶</span>
                            <span class="btn-label">Undo</span>
                        </button>
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="redo" title="Redo (Ctrl+Y)">
                            <span class="btn-icon">↷</span>
                            <span class="btn-label">Redo</span>
                        </button>
                        <div class="toolbar-separator"></div>
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="removeFormat" title="Clear Formatting">
                            <span class="btn-icon">🧹</span>
                            <span class="btn-label">Clear</span>
                        </button>
                        <button type="button" class="toolbar-btn toolbar-btn-large" data-command="toggleMarkdown" title="Toggle Markdown Mode (Alt+M)">
                            <span class="btn-icon">📝</span>
                            <span class="btn-label">Markdown</span>
                        </button>
                        <!-- Settings Dropdown -->
                        <div class="toolbar-dropdown">
                            <button type="button" class="toolbar-btn toolbar-btn-large dropdown-toggle" id="settings-dropdown-btn" title="Settings">
                                <span class="btn-icon">⚙️</span>
                                <span class="btn-label">Settings</span>
                            </button>
                            <div class="dropdown-menu" id="settings-dropdown-menu" style="display: none;">
                                <div class="dropdown-item">
                                    <label style="display: flex; align-items: center; justify-content: space-between; width: 100%; cursor: pointer;">
                                        <span>📊 Show Sidebar</span>
                                        <input type="checkbox" id="sidebar-toggle-checkbox" style="cursor: pointer; width: 18px; height: 18px;">
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            this.toolbar = toolbarContainer.querySelector('.editor-toolbar');
            
            // Add event listeners
            this.toolbar.addEventListener('click', (event) => {
                const button = event.target.closest('.toolbar-btn');
                if (button && !button.classList.contains('dropdown-toggle')) {
                    event.preventDefault();
                    const command = button.dataset.command;
                    
                    if (command) {
                        this.executeCommand(command);
                    }
                }
            });
            
            // Settings dropdown toggle
            const settingsDropdownBtn = this.toolbar.querySelector('#settings-dropdown-btn');
            const settingsDropdownMenu = this.toolbar.querySelector('#settings-dropdown-menu');
            if (settingsDropdownBtn && settingsDropdownMenu) {
                settingsDropdownBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const isVisible = settingsDropdownMenu.style.display !== 'none';
                    settingsDropdownMenu.style.display = isVisible ? 'none' : 'block';
                });
                
                // Close dropdown when clicking outside
                document.addEventListener('click', (e) => {
                    if (!settingsDropdownBtn.contains(e.target) && !settingsDropdownMenu.contains(e.target)) {
                        settingsDropdownMenu.style.display = 'none';
                    }
                });
            }
            
            // Sidebar toggle checkbox in settings
            const sidebarToggleCheckbox = this.toolbar.querySelector('#sidebar-toggle-checkbox');
            if (sidebarToggleCheckbox) {
                // Load saved sidebar state (default to false/hidden)
                const savedSidebarState = localStorage.getItem('editor-sidebar-visible');
                const sidebarVisible = savedSidebarState === 'true'; // Default to false (hidden)
                sidebarToggleCheckbox.checked = sidebarVisible;
                this.toggleSidebarVisibility(sidebarVisible);
                
                sidebarToggleCheckbox.addEventListener('change', (e) => {
                    const isVisible = e.target.checked;
                    this.toggleSidebarVisibility(isVisible);
                    localStorage.setItem('editor-sidebar-visible', isVisible);
                });
            }
            
            this.toolbar.addEventListener('change', (event) => {
                if (event.target.classList.contains('toolbar-select')) {
                    const command = event.target.dataset.command;
                    const value = event.target.value;
                    if (value) {
                        this.executeCommand(command, value);
                        event.target.value = ''; // Reset select
                    }
                }
            });
        }
        
        /**
         * Toggle document details panel
         */
        toggleDocumentDetails() {
            if (!this.sidebar) return;
            
            const docInfoPanel = this.sidebar.querySelector('.sidebar-panel:nth-child(2)'); // Document Info panel
            if (docInfoPanel) {
                const isHidden = docInfoPanel.style.display === 'none';
                docInfoPanel.style.display = isHidden ? 'block' : 'none';
                
                // Update button state
                const btn = this.sidebar.querySelector('#toggle-doc-details');
                if (btn) {
                    if (isHidden) {
                        btn.classList.add('active');
                    } else {
                        btn.classList.remove('active');
                    }
                }
            }
        }
        
        /**
         * Toggle sidebar visibility
         */
        toggleSidebarVisibility(isVisible) {
            const sidebarContainer = this.container.querySelector('.sidebar-container');
            if (sidebarContainer) {
                sidebarContainer.style.display = isVisible ? 'block' : 'none';
            }
        }

        /**
         * Initialize the sidebar
         */
        initializeSidebar() {
            const sidebarContainer = this.container.querySelector('.sidebar-container');
            if (!sidebarContainer) return;
            
            sidebarContainer.innerHTML = `
                <div class="editor-sidebar">
                    <div class="sidebar-header">
                        <h3>Editor Tools</h3>
                        <button type="button" class="sidebar-toggle" id="toggle-doc-details" title="Toggle Document Details">
                            📊
                        </button>
                    </div>
                    
                    <div class="sidebar-content">
                        <div class="sidebar-panel">
                            <h4>Editor Mode</h4>
                            <div class="mode-info">
                                <div class="mode-indicator">
                                    <span class="mode-label">Current Mode:</span>
                                    <span class="mode-value" id="current-mode">Visual</span>
                                </div>
                                <div class="mode-description" id="mode-description">
                                    Rich text editing with visual formatting
                                </div>
                            </div>
                        </div>
                        
                        <div class="sidebar-panel">
                            <h4>📊 Document Info</h4>
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
                    </div>
                </div>
            `;
            
            this.sidebar = sidebarContainer.querySelector('.editor-sidebar');
            
            // Document details toggle button
            const docDetailsBtn = this.sidebar.querySelector('#toggle-doc-details');
            if (docDetailsBtn) {
                docDetailsBtn.addEventListener('click', () => {
                    this.toggleDocumentDetails();
                });
            }
            
            // Initial stats update
            this.updateStats();
        }
        
        /**
         * Apply theme to editor
         */
        applyTheme(theme) {
            if (theme === 'dark') {
                this.container.classList.add('dark-theme');
                this.container.classList.remove('light-theme');
            } else {
                this.container.classList.add('light-theme');
                this.container.classList.remove('dark-theme');
            }
        }

        /**
         * Handle input events
         */
        handleInput(event) {
            const content = this.getContent();
            this.emit('update', { content, editor: this });
            this.updateStats();
            
            // Reset autosave timer
            if (this.config.autosave) {
                this.resetAutosaveTimer();
            }
        }

        /**
         * Handle keyboard shortcuts
         */
        handleKeyDown(event) {
            // Handle keyboard shortcuts
            if (event.ctrlKey || event.metaKey) {
                switch (event.key.toLowerCase()) {
                    case 'b':
                        event.preventDefault();
                        this.executeCommand('bold');
                        break;
                    case 'i':
                        event.preventDefault();
                        this.executeCommand('italic');
                        break;
                    case 'u':
                        event.preventDefault();
                        this.executeCommand('underline');
                        break;
                    case 'k':
                        event.preventDefault();
                        this.executeCommand('createLink');
                        break;
                    case 's':
                        event.preventDefault();
                        this.save();
                        break;
                    case 'z':
                        if (event.shiftKey) {
                            event.preventDefault();
                            this.executeCommand('redo');
                        } else {
                            event.preventDefault();
                            this.executeCommand('undo');
                        }
                        break;
                    case 'y':
                        event.preventDefault();
                        this.executeCommand('redo');
                        break;
                }
            }

            // Handle special keys
            switch (event.key) {
                case 'Enter':
                    if (event.shiftKey) {
                        // Shift+Enter = line break
                        event.preventDefault();
                        this.insertLineBreak();
                    } else {
                        // Enter = new paragraph/block
                        this.handleEnterKey(event);
                    }
                    break;
                case 'Backspace':
                    this.handleBackspace(event);
                    break;
                case '/':
                    if (this.isAtBlockStart()) {
                        event.preventDefault();
                        this.showBlockMenu();
                    }
                    break;
                case 'Tab':
                    event.preventDefault();
                    if (event.shiftKey) {
                        this.executeCommand('outdent');
                    } else {
                        this.executeCommand('indent');
                    }
                    break;
                case 'm':
                case 'M':
                    if (event.altKey) {
                        event.preventDefault();
                        this.toggleMarkdownMode();
                    }
                    break;
            }
        }

        /**
         * Handle paste events
         */
        handlePaste(event) {
            // Let the default paste happen, then clean up
            setTimeout(() => {
                this.handleInput(event);
            }, 10);
        }

        /**
         * Execute editor command
         */
        executeCommand(command, value = null) {
            try {
                this.editor.focus();
                
                switch (command) {
                    case 'createLink':
                        this.insertLink();
                        break;
                    case 'insertImage':
                        this.insertImage();
                        break;
                    case 'insertTable':
                        this.insertTable();
                        break;
                    case 'insertHorizontalRule':
                        document.execCommand('insertHorizontalRule', false, null);
                        break;
                    case 'showSource':
                        this.toggleSourceView();
                        break;
                    case 'toggleMarkdown':
                        this.toggleMarkdownMode();
                        break;
                    case 'lineHeight':
                        this.setLineHeight(value);
                        break;
                    case 'foreColor':
                    case 'hiliteColor':
                    case 'backColor':
                        if (value) {
                            // Use backColor for highlighting (more reliable than hiliteColor)
                            const cmd = command === 'hiliteColor' ? 'backColor' : command;
                            document.execCommand(cmd, false, value);
                        }
                        break;
                    case 'fontName':
                        if (value) {
                            document.execCommand('fontName', false, value);
                        }
                        break;
                    default:
                        if (this.currentMode === 'visual') {
                            document.execCommand(command, false, value);
                        }
                        break;
                }
                
                this.handleInput();
                this.updateToolbarState();
            } catch (error) {
                console.error('Command execution failed:', command, error);
            }
        }

        /**
         * Insert a link
         */
        insertLink() {
            const selection = window.getSelection();
            const selectedText = selection.toString();
            const url = prompt('Enter URL:', 'https://');
            
            if (url && url !== 'https://') {
                if (selectedText) {
                    document.execCommand('createLink', false, url);
                } else {
                    const linkText = prompt('Enter link text:', url);
                    if (linkText) {
                        const link = `<a href="${url}" target="_blank">${linkText}</a>`;
                        document.execCommand('insertHTML', false, link);
                    }
                }
            }
        }

        /**
         * Insert an image with enhanced options
         */
        insertImage() {
            this.showMediaManager('image');
        }

        /**
         * Show comprehensive media manager
         */
        showMediaManager(mediaType = 'all') {
            const modal = this.createMediaManagerModal(mediaType);
            document.body.appendChild(modal);
        }

        /**
         * Create media manager modal
         */
        createMediaManagerModal(mediaType) {
            const modal = document.createElement('div');
            modal.className = 'media-manager-modal';
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 2rem;
            `;

            const modalContent = document.createElement('div');
            modalContent.className = 'media-manager-content';
            modalContent.style.cssText = `
                background: var(--card);
                border-radius: 12px;
                padding: 0;
                max-width: 900px;
                max-height: 80vh;
                width: 100%;
                overflow: hidden;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            `;

            modalContent.innerHTML = `
                <div class="media-manager-header" style="
                    padding: 1.5rem;
                    border-bottom: 1px solid var(--paper-border);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    background: var(--bg);
                ">
                    <h3 style="margin: 0; color: var(--accent); font-size: 1.2rem;">Media Manager</h3>
                    <button class="close-modal" style="
                        background: none;
                        border: none;
                        font-size: 1.5rem;
                        cursor: pointer;
                        color: var(--muted);
                        padding: 0.25rem;
                        border-radius: 4px;
                        transition: all 0.15s ease;
                    ">×</button>
                </div>
                
                <div class="media-manager-tabs" style="
                    display: flex;
                    background: var(--bg);
                    border-bottom: 1px solid var(--paper-border);
                ">
                    <button class="media-tab active" data-tab="upload" style="
                        flex: 1;
                        padding: 1rem;
                        border: none;
                        background: transparent;
                        cursor: pointer;
                        border-bottom: 2px solid transparent;
                        transition: all 0.15s ease;
                    ">📤 Upload</button>
                    <button class="media-tab" data-tab="library" style="
                        flex: 1;
                        padding: 1rem;
                        border: none;
                        background: transparent;
                        cursor: pointer;
                        border-bottom: 2px solid transparent;
                        transition: all 0.15s ease;
                    ">📁 Library</button>
                    <button class="media-tab" data-tab="url" style="
                        flex: 1;
                        padding: 1rem;
                        border: none;
                        background: transparent;
                        cursor: pointer;
                        border-bottom: 2px solid transparent;
                        transition: all 0.15s ease;
                    ">🔗 URL</button>
                    <button class="media-tab" data-tab="embed" style="
                        flex: 1;
                        padding: 1rem;
                        border: none;
                        background: transparent;
                        cursor: pointer;
                        border-bottom: 2px solid transparent;
                        transition: all 0.15s ease;
                    ">📺 Embed</button>
                </div>
                
                <div class="media-manager-body" style="
                    padding: 1.5rem;
                    max-height: 60vh;
                    overflow-y: auto;
                ">
                    ${this.createUploadTab()}
                    ${this.createLibraryTab()}
                    ${this.createUrlTab()}
                    ${this.createEmbedTab()}
                </div>
            `;

            modal.appendChild(modalContent);

            // Add event listeners
            this.setupMediaManagerEvents(modal);

            return modal;
        }

        /**
         * Create upload tab content
         */
        createUploadTab() {
            return `
                <div class="media-tab-content" data-tab-content="upload">
                    <div class="upload-area" style="
                        border: 2px dashed var(--paper-border);
                        border-radius: 8px;
                        padding: 3rem;
                        text-align: center;
                        background: var(--bg);
                        transition: all 0.15s ease;
                        cursor: pointer;
                    ">
                        <div class="upload-icon" style="font-size: 3rem; margin-bottom: 1rem;">📁</div>
                        <h4 style="margin: 0 0 0.5rem 0; color: var(--text);">Drop files here or click to browse</h4>
                        <p style="margin: 0; color: var(--muted); font-size: 0.9rem;">
                            Supports: Images (JPG, PNG, GIF, WebP), Videos (MP4, WebM), Audio (MP3, WAV, OGG)
                        </p>
                        <input type="file" class="file-input" multiple accept="image/*,video/*,audio/*" style="display: none;">
                    </div>
                    
                    <div class="upload-options" style="margin-top: 1.5rem;">
                        <div class="form-group" style="margin-bottom: 1rem;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 500;">Alt Text (for images)</label>
                            <input type="text" class="alt-text-input" placeholder="Describe the image for accessibility" style="
                                width: 100%;
                                padding: 0.5rem;
                                border: 1px solid var(--paper-border);
                                border-radius: 4px;
                                font-size: 0.9rem;
                            ">
                        </div>
                        
                        <div class="form-group" style="margin-bottom: 1rem;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 500;">Caption (optional)</label>
                            <input type="text" class="caption-input" placeholder="Add a caption" style="
                                width: 100%;
                                padding: 0.5rem;
                                border: 1px solid var(--paper-border);
                                border-radius: 4px;
                                font-size: 0.9rem;
                            ">
                        </div>
                        
                        <div class="form-group">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 500;">Size</label>
                            <select class="size-select" style="
                                width: 100%;
                                padding: 0.5rem;
                                border: 1px solid var(--paper-border);
                                border-radius: 4px;
                                font-size: 0.9rem;
                            ">
                                <option value="full">Full Size</option>
                                <option value="large">Large (75%)</option>
                                <option value="medium" selected>Medium (50%)</option>
                                <option value="small">Small (25%)</option>
                                <option value="custom">Custom Size</option>
                            </select>
                        </div>
                    </div>
                </div>
            `;
        }

        /**
         * Create library tab content
         */
        createLibraryTab() {
            return `
                <div class="media-tab-content" data-tab-content="library" style="display: none;">
                    <div class="library-filters" style="
                        display: flex;
                        gap: 1rem;
                        margin-bottom: 1.5rem;
                        align-items: center;
                    ">
                        <select class="media-type-filter" style="
                            padding: 0.5rem;
                            border: 1px solid var(--paper-border);
                            border-radius: 4px;
                            font-size: 0.9rem;
                        ">
                            <option value="all">All Media</option>
                            <option value="image">Images</option>
                            <option value="video">Videos</option>
                            <option value="audio">Audio</option>
                            <option value="document">Documents</option>
                        </select>
                        
                        <input type="search" class="media-search" placeholder="Search media..." style="
                            flex: 1;
                            padding: 0.5rem;
                            border: 1px solid var(--paper-border);
                            border-radius: 4px;
                            font-size: 0.9rem;
                        ">
                    </div>
                    
                    <div class="media-grid" style="
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
                        gap: 1rem;
                        max-height: 400px;
                        overflow-y: auto;
                    ">
                        <div class="loading-media" style="
                            grid-column: 1 / -1;
                            text-align: center;
                            padding: 2rem;
                            color: var(--muted);
                        ">Loading media library...</div>
                    </div>
                </div>
            `;
        }

        /**
         * Create URL tab content
         */
        createUrlTab() {
            return `
                <div class="media-tab-content" data-tab-content="url" style="display: none;">
                    <div class="url-input-section">
                        <div class="form-group" style="margin-bottom: 1rem;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 500;">Media URL</label>
                            <input type="url" class="media-url-input" placeholder="https://example.com/image.jpg" style="
                                width: 100%;
                                padding: 0.5rem;
                                border: 1px solid var(--paper-border);
                                border-radius: 4px;
                                font-size: 0.9rem;
                            ">
                        </div>
                        
                        <div class="form-group" style="margin-bottom: 1rem;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 500;">Alt Text</label>
                            <input type="text" class="url-alt-text" placeholder="Describe the media" style="
                                width: 100%;
                                padding: 0.5rem;
                                border: 1px solid var(--paper-border);
                                border-radius: 4px;
                                font-size: 0.9rem;
                            ">
                        </div>
                        
                        <div class="url-preview" style="
                            margin-top: 1rem;
                            padding: 1rem;
                            border: 1px solid var(--paper-border);
                            border-radius: 4px;
                            background: var(--bg);
                            display: none;
                        ">
                            <div class="preview-content"></div>
                        </div>
                        
                        <button class="preview-url-btn" style="
                            background: var(--accent);
                            color: white;
                            border: none;
                            padding: 0.5rem 1rem;
                            border-radius: 4px;
                            cursor: pointer;
                            font-size: 0.9rem;
                            margin-top: 1rem;
                        ">Preview URL</button>
                    </div>
                </div>
            `;
        }

        /**
         * Create embed tab content
         */
        createEmbedTab() {
            return `
                <div class="media-tab-content" data-tab-content="embed" style="display: none;">
                    <div class="embed-options" style="
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 1rem;
                        margin-bottom: 1.5rem;
                    ">
                        <button class="embed-type-btn" data-embed="youtube" style="
                            padding: 1rem;
                            border: 1px solid var(--paper-border);
                            border-radius: 8px;
                            background: var(--card);
                            cursor: pointer;
                            text-align: center;
                            transition: all 0.15s ease;
                        ">
                            <div style="font-size: 2rem; margin-bottom: 0.5rem;">📺</div>
                            <div style="font-weight: 500;">YouTube</div>
                        </button>
                        
                        <button class="embed-type-btn" data-embed="vimeo" style="
                            padding: 1rem;
                            border: 1px solid var(--paper-border);
                            border-radius: 8px;
                            background: var(--card);
                            cursor: pointer;
                            text-align: center;
                            transition: all 0.15s ease;
                        ">
                            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎬</div>
                            <div style="font-weight: 500;">Vimeo</div>
                        </button>
                        
                        <button class="embed-type-btn" data-embed="soundcloud" style="
                            padding: 1rem;
                            border: 1px solid var(--paper-border);
                            border-radius: 8px;
                            background: var(--card);
                            cursor: pointer;
                            text-align: center;
                            transition: all 0.15s ease;
                        ">
                            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎵</div>
                            <div style="font-weight: 500;">SoundCloud</div>
                        </button>
                        
                        <button class="embed-type-btn" data-embed="custom" style="
                            padding: 1rem;
                            border: 1px solid var(--paper-border);
                            border-radius: 8px;
                            background: var(--card);
                            cursor: pointer;
                            text-align: center;
                            transition: all 0.15s ease;
                        ">
                            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔗</div>
                            <div style="font-weight: 500;">Custom Embed</div>
                        </button>
                    </div>
                    
                    <div class="embed-input-section" style="display: none;">
                        <div class="form-group" style="margin-bottom: 1rem;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 500;">URL or Embed Code</label>
                            <textarea class="embed-input" rows="4" placeholder="Paste YouTube URL, Vimeo URL, or embed code..." style="
                                width: 100%;
                                padding: 0.5rem;
                                border: 1px solid var(--paper-border);
                                border-radius: 4px;
                                font-size: 0.9rem;
                                resize: vertical;
                            "></textarea>
                        </div>
                        
                        <div class="embed-preview" style="
                            margin-top: 1rem;
                            padding: 1rem;
                            border: 1px solid var(--paper-border);
                            border-radius: 4px;
                            background: var(--bg);
                            display: none;
                        ">
                            <div class="preview-content"></div>
                        </div>
                    </div>
                </div>
            `;
        }

        /**
         * Set up media manager event listeners
         */
        setupMediaManagerEvents(modal) {
            const closeBtn = modal.querySelector('.close-modal');
            const tabs = modal.querySelectorAll('.media-tab');
            const tabContents = modal.querySelectorAll('.media-tab-content');
            const uploadArea = modal.querySelector('.upload-area');
            const fileInput = modal.querySelector('.file-input');

            // Close modal
            closeBtn.addEventListener('click', () => {
                modal.remove();
            });

            // Close on background click
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.remove();
                }
            });

            // Tab switching
            tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    const tabName = tab.dataset.tab;
                    
                    // Update active tab
                    tabs.forEach(t => {
                        t.classList.remove('active');
                        t.style.borderBottomColor = 'transparent';
                        t.style.color = 'var(--muted)';
                    });
                    tab.classList.add('active');
                    tab.style.borderBottomColor = 'var(--accent)';
                    tab.style.color = 'var(--accent)';
                    
                    // Show corresponding content
                    tabContents.forEach(content => {
                        content.style.display = 'none';
                    });
                    const activeContent = modal.querySelector(`[data-tab-content="${tabName}"]`);
                    if (activeContent) {
                        activeContent.style.display = 'block';
                    }

                    // Load library content when library tab is clicked
                    if (tabName === 'library') {
                        this.loadMediaLibrary(modal);
                    }
                });
            });

            // File upload handling
            uploadArea.addEventListener('click', () => {
                fileInput.click();
            });

            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.style.borderColor = 'var(--accent)';
                uploadArea.style.backgroundColor = 'rgba(217, 119, 6, 0.1)';
            });

            uploadArea.addEventListener('dragleave', (e) => {
                e.preventDefault();
                uploadArea.style.borderColor = 'var(--paper-border)';
                uploadArea.style.backgroundColor = 'var(--bg)';
            });

            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.style.borderColor = 'var(--paper-border)';
                uploadArea.style.backgroundColor = 'var(--bg)';
                
                const files = Array.from(e.dataTransfer.files);
                this.handleFileUpload(files, modal);
            });

            fileInput.addEventListener('change', (e) => {
                const files = Array.from(e.target.files);
                this.handleFileUpload(files, modal);
            });

            // URL preview
            const previewBtn = modal.querySelector('.preview-url-btn');
            if (previewBtn) {
                previewBtn.addEventListener('click', () => {
                    this.previewMediaUrl(modal);
                });
            }

            // Embed type selection
            const embedBtns = modal.querySelectorAll('.embed-type-btn');
            embedBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    const embedType = btn.dataset.embed;
                    this.showEmbedInput(modal, embedType);
                });
            });

            // Set initial active tab
            tabs[0].click();
        }

        /**
         * Handle file upload
         */
        async handleFileUpload(files, modal) {
            const altTextInput = modal.querySelector('.alt-text-input');
            const captionInput = modal.querySelector('.caption-input');
            const sizeSelect = modal.querySelector('.size-select');

            for (const file of files) {
                if (this.isValidMediaFile(file)) {
                    try {
                        const result = await this.uploadFile(file);
                        if (result.success) {
                            const mediaHtml = this.generateMediaHtml(result, {
                                alt: altTextInput.value || file.name,
                                caption: captionInput.value,
                                size: sizeSelect.value
                            });
                            
                            this.insertMediaIntoEditor(mediaHtml);
                            this.showNotification(`${file.name} uploaded successfully!`, 'success');
                        } else {
                            this.showNotification(`Failed to upload ${file.name}: ${result.error}`, 'error');
                        }
                    } catch (error) {
                        this.showNotification(`Error uploading ${file.name}: ${error.message}`, 'error');
                    }
                } else {
                    this.showNotification(`${file.name} is not a supported media type`, 'error');
                }
            }

            modal.remove();
        }

        /**
         * Check if file is valid media type
         */
        isValidMediaFile(file) {
            const validTypes = [
                // Images
                'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
                // Videos
                'video/mp4', 'video/webm', 'video/ogg', 'video/avi', 'video/mov',
                // Audio
                'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/m4a', 'audio/aac',
                // Documents
                'application/pdf', 'text/plain', 'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ];
            
            return validTypes.includes(file.type);
        }

        /**
         * Upload file to server
         */
        async uploadFile(file) {
            const formData = new FormData();
            formData.append('image', file); // Using 'image' for compatibility with existing endpoint
            
            try {
                const response = await fetch('/api/upload-editor-image', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': this.getCSRFToken()
                    }
                });
                
                return await response.json();
            } catch (error) {
                return { success: false, error: error.message };
            }
        }

        /**
         * Get CSRF token
         */
        getCSRFToken() {
            const token = document.querySelector('meta[name=csrf-token]');
            return token ? token.getAttribute('content') : '';
        }

        /**
         * Generate media HTML based on file type and options
         */
        generateMediaHtml(uploadResult, options) {
            const { url, filename } = uploadResult;
            const { alt, caption, size } = options;
            
            // Determine media type from URL/filename
            const extension = filename.split('.').pop().toLowerCase();
            const isImage = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(extension);
            const isVideo = ['mp4', 'webm', 'ogg', 'avi', 'mov'].includes(extension);
            const isAudio = ['mp3', 'wav', 'ogg', 'm4a', 'aac'].includes(extension);
            
            let sizeStyle = '';
            switch (size) {
                case 'small': sizeStyle = 'width: 25%; '; break;
                case 'medium': sizeStyle = 'width: 50%; '; break;
                case 'large': sizeStyle = 'width: 75%; '; break;
                case 'full': sizeStyle = 'width: 100%; '; break;
            }
            
            let mediaHtml = '';
            
            if (isImage) {
                mediaHtml = `<img src="${url}" alt="${alt}" style="${sizeStyle}max-width: 100%; height: auto; border-radius: 8px; margin: 1rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">`;
            } else if (isVideo) {
                mediaHtml = `<video controls style="${sizeStyle}max-width: 100%; height: auto; border-radius: 8px; margin: 1rem 0;">
                    <source src="${url}" type="video/${extension}">
                    Your browser does not support the video tag.
                </video>`;
            } else if (isAudio) {
                mediaHtml = `<audio controls style="width: 100%; margin: 1rem 0;">
                    <source src="${url}" type="audio/${extension}">
                    Your browser does not support the audio tag.
                </audio>`;
            } else {
                // File attachment
                mediaHtml = `<a href="${url}" download="${filename}" style="
                    display: inline-block;
                    padding: 0.5rem 1rem;
                    background: var(--bg);
                    border: 1px solid var(--paper-border);
                    border-radius: 4px;
                    text-decoration: none;
                    color: var(--text);
                    margin: 1rem 0;
                ">📎 ${filename}</a>`;
            }
            
            // Add caption if provided
            if (caption) {
                mediaHtml = `<figure style="margin: 1rem 0;">
                    ${mediaHtml}
                    <figcaption style="text-align: center; font-style: italic; color: var(--muted); margin-top: 0.5rem;">${caption}</figcaption>
                </figure>`;
            }
            
            return mediaHtml;
        }

        /**
         * Insert media HTML into editor
         */
        insertMediaIntoEditor(mediaHtml) {
            this.editor.focus();
            document.execCommand('insertHTML', false, mediaHtml);
            this.handleInput();
        }

        /**
         * Load media library
         */
        async loadMediaLibrary(modal) {
            const mediaGrid = modal.querySelector('.media-grid');
            
            try {
                const response = await fetch('/api/editor-images');
                const data = await response.json();
                
                if (data.success) {
                    this.displayMediaLibrary(data.images, mediaGrid);
                } else {
                    mediaGrid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: var(--muted);">Failed to load media library</div>';
                }
            } catch (error) {
                mediaGrid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: var(--muted);">Error loading media library</div>';
            }
        }

        /**
         * Display media library items
         */
        displayMediaLibrary(items, container) {
            if (items.length === 0) {
                container.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: var(--muted);">No media files found</div>';
                return;
            }
            
            container.innerHTML = items.map(item => `
                <div class="media-item" data-url="${item.url}" data-filename="${item.original_name}" style="
                    border: 1px solid var(--paper-border);
                    border-radius: 8px;
                    overflow: hidden;
                    cursor: pointer;
                    transition: all 0.15s ease;
                    background: var(--card);
                ">
                    <div class="media-preview" style="
                        width: 100%;
                        height: 80px;
                        background: var(--bg);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 2rem;
                    ">
                        ${this.getMediaIcon(item.mime_type)}
                    </div>
                    <div class="media-info" style="
                        padding: 0.5rem;
                        font-size: 0.8rem;
                        color: var(--text);
                    ">
                        <div style="font-weight: 500; margin-bottom: 0.25rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.original_name}</div>
                        <div style="color: var(--muted);">${(item.file_size / 1024).toFixed(1)} KB</div>
                    </div>
                </div>
            `).join('');
            
            // Add click handlers
            container.querySelectorAll('.media-item').forEach(item => {
                item.addEventListener('click', () => {
                    const url = item.dataset.url;
                    const filename = item.dataset.filename;
                    const mediaHtml = this.generateMediaHtml({ url, filename }, {
                        alt: filename,
                        caption: '',
                        size: 'medium'
                    });
                    
                    this.insertMediaIntoEditor(mediaHtml);
                    item.closest('.media-manager-modal').remove();
                });
                
                item.addEventListener('mouseenter', () => {
                    item.style.transform = 'translateY(-2px)';
                    item.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
                });
                
                item.addEventListener('mouseleave', () => {
                    item.style.transform = 'translateY(0)';
                    item.style.boxShadow = 'none';
                });
            });
        }

        /**
         * Get media icon based on MIME type
         */
        getMediaIcon(mimeType) {
            if (mimeType.startsWith('image/')) return '🖼️';
            if (mimeType.startsWith('video/')) return '🎬';
            if (mimeType.startsWith('audio/')) return '🎵';
            if (mimeType === 'application/pdf') return '📄';
            return '📎';
        }

        /**
         * Preview media URL
         */
        async previewMediaUrl(modal) {
            const urlInput = modal.querySelector('.media-url-input');
            const preview = modal.querySelector('.url-preview');
            const previewContent = preview.querySelector('.preview-content');
            
            const url = urlInput.value.trim();
            if (!url) return;
            
            preview.style.display = 'block';
            previewContent.innerHTML = '<div style="text-align: center; padding: 1rem;">Loading preview...</div>';
            
            try {
                // Simple preview based on URL
                const extension = url.split('.').pop().toLowerCase();
                const isImage = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(extension);
                const isVideo = ['mp4', 'webm', 'ogg'].includes(extension);
                
                if (isImage) {
                    previewContent.innerHTML = `<img src="${url}" style="max-width: 100%; height: auto; border-radius: 4px;" onerror="this.parentElement.innerHTML='<div style=\\'color: var(--muted);\\'>Could not load image preview</div>'">`;
                } else if (isVideo) {
                    previewContent.innerHTML = `<video controls style="max-width: 100%; height: auto; border-radius: 4px;">
                        <source src="${url}">
                        Your browser does not support the video tag.
                    </video>`;
                } else {
                    previewContent.innerHTML = `<div style="color: var(--muted);">Preview not available for this media type</div>`;
                }
                
                // Add insert button
                const insertBtn = document.createElement('button');
                insertBtn.textContent = 'Insert Media';
                insertBtn.style.cssText = `
                    background: var(--accent);
                    color: white;
                    border: none;
                    padding: 0.5rem 1rem;
                    border-radius: 4px;
                    cursor: pointer;
                    margin-top: 1rem;
                `;
                insertBtn.addEventListener('click', () => {
                    const altText = modal.querySelector('.url-alt-text').value || 'Media';
                    const mediaHtml = this.generateMediaHtml({ url, filename: url.split('/').pop() }, {
                        alt: altText,
                        caption: '',
                        size: 'medium'
                    });
                    
                    this.insertMediaIntoEditor(mediaHtml);
                    modal.remove();
                });
                
                previewContent.appendChild(insertBtn);
                
            } catch (error) {
                previewContent.innerHTML = '<div style="color: var(--muted);">Could not load preview</div>';
            }
        }

        /**
         * Show embed input for specific type
         */
        showEmbedInput(modal, embedType) {
            const embedSection = modal.querySelector('.embed-input-section');
            const embedInput = modal.querySelector('.embed-input');
            
            embedSection.style.display = 'block';
            
            let placeholder = '';
            switch (embedType) {
                case 'youtube':
                    placeholder = 'Paste YouTube URL (e.g., https://www.youtube.com/watch?v=...)';
                    break;
                case 'vimeo':
                    placeholder = 'Paste Vimeo URL (e.g., https://vimeo.com/...)';
                    break;
                case 'soundcloud':
                    placeholder = 'Paste SoundCloud URL';
                    break;
                case 'custom':
                    placeholder = 'Paste embed code or URL';
                    break;
            }
            
            embedInput.placeholder = placeholder;
            embedInput.focus();
            
            // Add process button if not exists
            if (!modal.querySelector('.process-embed-btn')) {
                const processBtn = document.createElement('button');
                processBtn.className = 'process-embed-btn';
                processBtn.textContent = 'Insert Embed';
                processBtn.style.cssText = `
                    background: var(--accent);
                    color: white;
                    border: none;
                    padding: 0.5rem 1rem;
                    border-radius: 4px;
                    cursor: pointer;
                    margin-top: 1rem;
                `;
                
                processBtn.addEventListener('click', () => {
                    this.processEmbed(modal, embedType);
                });
                
                embedSection.appendChild(processBtn);
            }
        }

        /**
         * Process embed code/URL
         */
        processEmbed(modal, embedType) {
            const embedInput = modal.querySelector('.embed-input');
            const input = embedInput.value.trim();
            
            if (!input) return;
            
            let embedHtml = '';
            
            try {
                if (embedType === 'youtube') {
                    const videoId = this.extractYouTubeId(input);
                    if (videoId) {
                        embedHtml = `<div style="position: relative; padding-bottom: 56.25%; height: 0; margin: 1rem 0;">
                            <iframe src="https://www.youtube.com/embed/${videoId}" 
                                    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; border-radius: 8px;"
                                    allowfullscreen>
                            </iframe>
                        </div>`;
                    }
                } else if (embedType === 'vimeo') {
                    const videoId = this.extractVimeoId(input);
                    if (videoId) {
                        embedHtml = `<div style="position: relative; padding-bottom: 56.25%; height: 0; margin: 1rem 0;">
                            <iframe src="https://player.vimeo.com/video/${videoId}" 
                                    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; border-radius: 8px;"
                                    allowfullscreen>
                            </iframe>
                        </div>`;
                    }
                } else {
                    // Custom embed - sanitize and use as-is
                    embedHtml = `<div style="margin: 1rem 0;">${input}</div>`;
                }
                
                if (embedHtml) {
                    this.insertMediaIntoEditor(embedHtml);
                    modal.remove();
                } else {
                    this.showNotification('Could not process embed. Please check the URL or code.', 'error');
                }
                
            } catch (error) {
                this.showNotification('Error processing embed: ' + error.message, 'error');
            }
        }

        /**
         * Extract YouTube video ID from URL
         */
        extractYouTubeId(url) {
            const regex = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
            const match = url.match(regex);
            return match ? match[1] : null;
        }

        /**
         * Extract Vimeo video ID from URL
         */
        extractVimeoId(url) {
            const regex = /vimeo\.com\/(?:channels\/(?:\w+\/)?|groups\/([^\/]*)\/videos\/|album\/(\d+)\/video\/|)(\d+)(?:$|\/|\?)/;
            const match = url.match(regex);
            return match ? match[3] : null;
        }

        /**
         * Show notification
         */
        showNotification(message, type = 'info') {
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 2rem;
                right: 2rem;
                padding: 1rem 1.5rem;
                border-radius: 8px;
                color: white;
                font-weight: 500;
                z-index: 10001;
                max-width: 300px;
                animation: slideInRight 0.3s ease-out;
            `;
            
            switch (type) {
                case 'success':
                    notification.style.background = '#28a745';
                    break;
                case 'error':
                    notification.style.background = '#dc3545';
                    break;
                case 'warning':
                    notification.style.background = '#ffc107';
                    notification.style.color = '#333';
                    break;
                default:
                    notification.style.background = '#17a2b8';
            }
            
            notification.textContent = message;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.animation = 'slideOutRight 0.3s ease-in';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }, 4000);
        }
        insertTable() {
            const rows = parseInt(prompt('Number of rows:', '3')) || 3;
            const cols = parseInt(prompt('Number of columns:', '3')) || 3;
            
            if (rows > 0 && cols > 0 && rows <= 20 && cols <= 10) {
                let tableHTML = '<table style="border-collapse: collapse; width: 100%; margin: 1rem 0; border: 1px solid #ddd;">';
                
                // Create header row
                tableHTML += '<thead><tr>';
                for (let c = 0; c < cols; c++) {
                    tableHTML += '<th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5; font-weight: bold;">Header ' + (c + 1) + '</th>';
                }
                tableHTML += '</tr></thead>';
                
                // Create body rows
                tableHTML += '<tbody>';
                for (let r = 0; r < rows - 1; r++) {
                    tableHTML += '<tr>';
                    for (let c = 0; c < cols; c++) {
                        tableHTML += '<td style="border: 1px solid #ddd; padding: 8px;">Cell ' + (r + 1) + ',' + (c + 1) + '</td>';
                    }
                    tableHTML += '</tr>';
                }
                tableHTML += '</tbody></table><p><br></p>';
                
                document.execCommand('insertHTML', false, tableHTML);
            } else {
                alert('Please enter valid table dimensions (max 20 rows, 10 columns)');
            }
        }

        /**
         * Set line height for selected text or current paragraph
         */
        setLineHeight(value) {
            if (!value) return;
            
            const selection = window.getSelection();
            if (selection.rangeCount === 0) return;
            
            // Get the current element or create a span
            let element;
            if (selection.toString().length > 0) {
                // Text is selected, wrap it in a span
                const range = selection.getRangeAt(0);
                const span = document.createElement('span');
                span.style.lineHeight = value;
                
                try {
                    range.surroundContents(span);
                } catch (e) {
                    // If we can't surround (e.g., selection spans multiple elements),
                    // apply to the parent block element
                    const parentBlock = this.getParentBlock(range.commonAncestorContainer);
                    if (parentBlock) {
                        parentBlock.style.lineHeight = value;
                    }
                }
            } else {
                // No text selected, apply to current paragraph/block
                const parentBlock = this.getParentBlock(selection.anchorNode);
                if (parentBlock) {
                    parentBlock.style.lineHeight = value;
                }
            }
        }

        /**
         * Get parent block element
         */
        getParentBlock(node) {
            const blockElements = ['P', 'DIV', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'BLOCKQUOTE', 'LI'];
            
            while (node && node !== this.editor) {
                if (node.nodeType === Node.ELEMENT_NODE && blockElements.includes(node.tagName)) {
                    return node;
                }
                node = node.parentNode;
            }
            
            return null;
        }

        /**
         * Toggle between visual and markdown modes
         */
        toggleMarkdownMode() {
            if (this.currentMode === 'visual') {
                this.switchToMarkdownMode();
            } else {
                this.switchToVisualMode();
            }
        }

        /**
         * Switch to markdown editing mode
         */
        switchToMarkdownMode() {
            if (this.currentMode === 'markdown') return;

            // Convert current HTML content to markdown
            const htmlContent = this.editor.innerHTML;
            const markdownContent = this.htmlToMarkdown(htmlContent);
            
            // Store visual content
            this.visualContent = htmlContent;
            this.markdownContent = markdownContent;
            
            // Switch editor to markdown mode
            this.editor.contentEditable = 'true';
            this.editor.style.fontFamily = 'Courier New, monospace';
            this.editor.style.fontSize = '0.9rem';
            this.editor.style.lineHeight = '1.5';
            this.editor.style.whiteSpace = 'pre-wrap';
            this.editor.textContent = markdownContent;
            
            this.currentMode = 'markdown';
            this.container.classList.add('markdown-mode');
            
            // Update toolbar state
            this.updateToolbarForMode();
            
            this.emit('modeChanged', { mode: 'markdown', content: markdownContent });
        }

        /**
         * Switch to visual editing mode
         */
        switchToVisualMode() {
            if (this.currentMode === 'visual') return;

            // Convert current markdown content to HTML
            const markdownContent = this.editor.textContent;
            const htmlContent = this.markdownToHtml(markdownContent);
            
            // Store markdown content
            this.markdownContent = markdownContent;
            this.visualContent = htmlContent;
            
            // Switch editor to visual mode
            this.editor.style.fontFamily = '';
            this.editor.style.fontSize = '';
            this.editor.style.lineHeight = '';
            this.editor.style.whiteSpace = '';
            this.editor.innerHTML = htmlContent;
            
            this.currentMode = 'visual';
            this.container.classList.remove('markdown-mode');
            
            // Update toolbar state
            this.updateToolbarForMode();
            
            this.emit('modeChanged', { mode: 'visual', content: htmlContent });
        }

        /**
         * Convert HTML to Markdown
         */
        htmlToMarkdown(html) {
            // Create a temporary div to parse HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            
            return this.processNodeToMarkdown(tempDiv);
        }

        /**
         * Process DOM node to markdown recursively
         */
        processNodeToMarkdown(node) {
            let markdown = '';
            
            for (const child of node.childNodes) {
                if (child.nodeType === Node.TEXT_NODE) {
                    markdown += child.textContent;
                } else if (child.nodeType === Node.ELEMENT_NODE) {
                    const tagName = child.tagName.toLowerCase();
                    const content = this.processNodeToMarkdown(child);
                    
                    switch (tagName) {
                        case 'h1':
                            markdown += `# ${content}\n\n`;
                            break;
                        case 'h2':
                            markdown += `## ${content}\n\n`;
                            break;
                        case 'h3':
                            markdown += `### ${content}\n\n`;
                            break;
                        case 'h4':
                            markdown += `#### ${content}\n\n`;
                            break;
                        case 'h5':
                            markdown += `##### ${content}\n\n`;
                            break;
                        case 'h6':
                            markdown += `###### ${content}\n\n`;
                            break;
                        case 'p':
                            markdown += `${content}\n\n`;
                            break;
                        case 'strong':
                        case 'b':
                            markdown += `**${content}**`;
                            break;
                        case 'em':
                        case 'i':
                            markdown += `*${content}*`;
                            break;
                        case 'u':
                            markdown += `<u>${content}</u>`;
                            break;
                        case 's':
                            markdown += `~~${content}~~`;
                            break;
                        case 'code':
                            markdown += `\`${content}\``;
                            break;
                        case 'pre':
                            markdown += `\`\`\`\n${content}\n\`\`\`\n\n`;
                            break;
                        case 'blockquote':
                            const lines = content.split('\n');
                            markdown += lines.map(line => `> ${line}`).join('\n') + '\n\n';
                            break;
                        case 'ul':
                            markdown += this.processListToMarkdown(child, '-') + '\n';
                            break;
                        case 'ol':
                            markdown += this.processListToMarkdown(child, '1.') + '\n';
                            break;
                        case 'a':
                            const href = child.getAttribute('href') || '';
                            markdown += `[${content}](${href})`;
                            break;
                        case 'img':
                            const src = child.getAttribute('src') || '';
                            const alt = child.getAttribute('alt') || '';
                            markdown += `![${alt}](${src})`;
                            break;
                        case 'hr':
                            markdown += '---\n\n';
                            break;
                        case 'br':
                            markdown += '\n';
                            break;
                        default:
                            markdown += content;
                    }
                }
            }
            
            return markdown;
        }

        /**
         * Process list elements to markdown
         */
        processListToMarkdown(listElement, marker) {
            let markdown = '';
            let counter = 1;
            
            for (const li of listElement.children) {
                if (li.tagName.toLowerCase() === 'li') {
                    const content = this.processNodeToMarkdown(li);
                    const currentMarker = marker === '1.' ? `${counter}.` : marker;
                    markdown += `${currentMarker} ${content}\n`;
                    counter++;
                }
            }
            
            return markdown;
        }

        /**
         * Convert Markdown to HTML
         */
        markdownToHtml(markdown) {
            if (!markdown || markdown.trim() === '') {
                return '';
            }
            
            let html = markdown;
            
            // Protect code blocks first (to prevent processing their content)
            const codeBlocks = [];
            html = html.replace(/```[\s\S]*?```/g, (match) => {
                codeBlocks.push(match);
                return `__CODEBLOCK_${codeBlocks.length - 1}__`;
            });
            
            // Headers (must be processed in order from longest to shortest)
            html = html.replace(/^######\s+(.+)$/gm, '<h6>$1</h6>');
            html = html.replace(/^#####\s+(.+)$/gm, '<h5>$1</h5>');
            html = html.replace(/^####\s+(.+)$/gm, '<h4>$1</h4>');
            html = html.replace(/^###\s+(.+)$/gm, '<h3>$1</h3>');
            html = html.replace(/^##\s+(.+)$/gm, '<h2>$1</h2>');
            html = html.replace(/^#\s+(.+)$/gm, '<h1>$1</h1>');
            
            // Horizontal rules (before lists to avoid conflicts)
            html = html.replace(/^---+$/gm, '<hr>');
            
            // Blockquotes
            html = html.replace(/^>\s+(.+)$/gm, '<blockquote>$1</blockquote>');
            
            // Lists
            html = html.replace(/^[-*+]\s+(.+)$/gm, '<li>$1</li>');
            html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');
            
            // Wrap consecutive <li> elements in <ul> or <ol>
            html = html.replace(/(<li>.*?<\/li>\n?)+/gs, (match) => {
                return `<ul>${match}</ul>`;
            });
            
            // Images (must come before links)
            html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1">');
            
            // Links
            html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
            
            // Inline formatting (bold, italic, code, strikethrough)
            // Protect inline code first
            const inlineCodes = [];
            html = html.replace(/`([^`]+)`/g, (match, code) => {
                inlineCodes.push(code);
                return `__INLINECODE_${inlineCodes.length - 1}__`;
            });
            
            // Bold (must be before italic)
            html = html.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
            html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');
            
            // Strikethrough
            html = html.replace(/~~([^~]+)~~/g, '<del>$1</del>');
            
            // Italic
            html = html.replace(/\*([^\*]+)\*/g, '<em>$1</em>');
            html = html.replace(/_([^_]+)_/g, '<em>$1</em>');
            
            // Restore inline code
            inlineCodes.forEach((code, index) => {
                html = html.replace(`__INLINECODE_${index}__`, `<code>${code}</code>`);
            });
            
            // Restore code blocks
            codeBlocks.forEach((block, index) => {
                // Extract language and code from the block
                const match = block.match(/```(\w+)?\n?([\s\S]*?)```/);
                if (match) {
                    const code = match[2] || '';
                    html = html.replace(`__CODEBLOCK_${index}__`, `<pre><code>${code}</code></pre>`);
                } else {
                    html = html.replace(`__CODEBLOCK_${index}__`, block);
                }
            });
            
            // Paragraphs (wrap non-tag lines)
            const lines = html.split('\n');
            const processedLines = [];
            
            for (let i = 0; i < lines.length; i++) {
                const trimmed = lines[i].trim();
                
                // Skip empty lines
                if (!trimmed) {
                    continue;
                }
                
                // If it's already an HTML tag, keep it as is
                if (trimmed.match(/^<[a-z]/i)) {
                    processedLines.push(trimmed);
                } else {
                    // Wrap in paragraph
                    processedLines.push(`<p>${trimmed}</p>`);
                }
            }
            
            // Join with actual HTML line breaks for proper rendering
            html = processedLines.join('');
            
            return html;
        }

        /**
         * Update toolbar for current mode
         */
        updateToolbarForMode() {
            if (!this.toolbar) return;
            
            const formatButtons = this.toolbar.querySelectorAll('[data-command="bold"], [data-command="italic"], [data-command="underline"], [data-command="strikeThrough"]');
            const blockButtons = this.toolbar.querySelectorAll('[data-command="formatBlock"], [data-command="insertUnorderedList"], [data-command="insertOrderedList"]');
            const alignButtons = this.toolbar.querySelectorAll('[data-command="justifyLeft"], [data-command="justifyCenter"], [data-command="justifyRight"]');
            
            if (this.currentMode === 'markdown') {
                // Disable visual formatting buttons in markdown mode
                [...formatButtons, ...blockButtons, ...alignButtons].forEach(btn => {
                    btn.disabled = true;
                    btn.style.opacity = '0.5';
                });
            } else {
                // Enable all buttons in visual mode
                [...formatButtons, ...blockButtons, ...alignButtons].forEach(btn => {
                    btn.disabled = false;
                    btn.style.opacity = '1';
                });
            }
            
            // Update mode indicator
            const markdownBtn = this.toolbar.querySelector('[data-command="toggleMarkdown"]');
            if (markdownBtn) {
                markdownBtn.classList.toggle('active', this.currentMode === 'markdown');
                markdownBtn.title = this.currentMode === 'markdown' ? 'Switch to Visual Mode' : 'Switch to Markdown Mode';
            }
        }

        /**
         * Format HTML for display
         */
        formatHTML(html) {
            return html
                .replace(/></g, '>\n<')
                .replace(/^\s+|\s+$/g, '')
                .split('\n')
                .map(line => line.trim())
                .filter(line => line)
                .join('\n');
        }

        /**
         * Handle Enter key press
         */
        handleEnterKey(event) {
            const selection = window.getSelection();
            const range = selection.getRangeAt(0);
            const currentElement = range.startContainer.nodeType === Node.TEXT_NODE 
                ? range.startContainer.parentElement 
                : range.startContainer;

            // Handle different block types
            if (currentElement.tagName === 'BLOCKQUOTE') {
                event.preventDefault();
                this.exitBlock('p');
            } else if (currentElement.tagName && currentElement.tagName.match(/^H[1-6]$/)) {
                event.preventDefault();
                this.exitBlock('p');
            }
        }

        /**
         * Handle backspace key
         */
        handleBackspace(event) {
            const selection = window.getSelection();
            if (selection.rangeCount === 0) return;

            const range = selection.getRangeAt(0);
            if (range.startOffset === 0) {
                const currentElement = range.startContainer.nodeType === Node.TEXT_NODE 
                    ? range.startContainer.parentElement 
                    : range.startContainer;

                if (currentElement.tagName && currentElement.tagName.match(/^H[1-6]$|BLOCKQUOTE/)) {
                    event.preventDefault();
                    this.convertBlock(currentElement, 'p');
                }
            }
        }

        /**
         * Insert line break
         */
        insertLineBreak() {
            document.execCommand('insertHTML', false, '<br>');
        }

        /**
         * Check if cursor is at block start
         */
        isAtBlockStart() {
            const selection = window.getSelection();
            if (selection.rangeCount === 0) return false;

            const range = selection.getRangeAt(0);
            return range.startOffset === 0;
        }

        /**
         * Show block menu
         */
        showBlockMenu() {
            if (this.blockMenu) {
                const selection = window.getSelection();
                const range = selection.getRangeAt(0);
                const rect = range.getBoundingClientRect();
                
                this.blockMenu.style.display = 'block';
                this.blockMenu.style.position = 'absolute';
                this.blockMenu.style.top = (rect.bottom + window.scrollY + 5) + 'px';
                this.blockMenu.style.left = rect.left + 'px';
                this.blockMenu.style.zIndex = '1000';
            }
        }

        /**
         * Hide block menu
         */
        hideBlockMenu() {
            if (this.blockMenu) {
                this.blockMenu.style.display = 'none';
            }
        }

        /**
         * Insert block
         */
        insertBlock(blockType) {
            const selection = window.getSelection();
            const range = selection.getRangeAt(0);
            
            // Remove the '/' character
            if (range.startOffset > 0) {
                range.setStart(range.startContainer, range.startOffset - 1);
                range.deleteContents();
            }

            let html = '';
            switch (blockType) {
                case 'heading1':
                    html = '<h1>Heading 1</h1>';
                    break;
                case 'heading2':
                    html = '<h2>Heading 2</h2>';
                    break;
                case 'heading3':
                    html = '<h3>Heading 3</h3>';
                    break;
                case 'quote':
                    html = '<blockquote>Quote text</blockquote>';
                    break;
                case 'code':
                    html = '<pre><code>Code block</code></pre>';
                    break;
                case 'list':
                    html = '<ul><li>List item</li></ul>';
                    break;
                case 'numbered':
                    html = '<ol><li>Numbered item</li></ol>';
                    break;
                case 'divider':
                    html = '<hr>';
                    break;
                default:
                    html = '<p>Paragraph</p>';
            }

            document.execCommand('insertHTML', false, html);
        }

        /**
         * Exit current block
         */
        exitBlock(newBlockType = 'p') {
            const html = `<${newBlockType}><br></${newBlockType}>`;
            document.execCommand('insertHTML', false, html);
        }

        /**
         * Convert block type
         */
        convertBlock(element, newType) {
            const content = element.innerHTML;
            const newElement = document.createElement(newType);
            newElement.innerHTML = content;
            element.parentNode.replaceChild(newElement, element);
        }

        /**
         * Handle selection changes
         */
        handleSelection() {
            this.updateToolbarState();
        }

        /**
         * Update toolbar button states
         */
        updateToolbarState() {
            if (!this.toolbar) return;

            const commands = ['bold', 'italic', 'underline', 'strikeThrough', 'superscript', 'subscript'];
            commands.forEach(command => {
                const button = this.toolbar.querySelector(`[data-command="${command}"]`);
                if (button) {
                    const isActive = document.queryCommandState(command);
                    button.classList.toggle('active', isActive);
                }
            });

            // Update alignment buttons
            const alignCommands = ['justifyLeft', 'justifyCenter', 'justifyRight', 'justifyFull'];
            alignCommands.forEach(command => {
                const button = this.toolbar.querySelector(`[data-command="${command}"]`);
                if (button) {
                    const isActive = document.queryCommandState(command);
                    button.classList.toggle('active', isActive);
                }
            });

            // Update font family and size selects
            try {
                const fontNameSelect = this.toolbar.querySelector('[data-command="fontName"]');
                if (fontNameSelect) {
                    const currentFont = document.queryCommandValue('fontName');
                    if (currentFont) {
                        // Try to match the current font with one of our options
                        const options = Array.from(fontNameSelect.options);
                        const matchingOption = options.find(option => 
                            currentFont.toLowerCase().includes(option.value.toLowerCase().split(',')[0])
                        );
                        if (matchingOption) {
                            fontNameSelect.value = matchingOption.value;
                        }
                    }
                }

                const fontSizeSelect = this.toolbar.querySelector('[data-command="fontSize"]');
                if (fontSizeSelect) {
                    const currentSize = document.queryCommandValue('fontSize');
                    if (currentSize) {
                        fontSizeSelect.value = currentSize;
                    }
                }
            } catch (error) {
                // Ignore errors from queryCommandValue
            }

            // Update color indicators
            try {
                const foreColorBtn = this.toolbar.querySelector('[data-command="foreColor"]');
                if (foreColorBtn) {
                    const currentColor = document.queryCommandValue('foreColor');
                    if (currentColor) {
                        const colorIcon = foreColorBtn.querySelector('.color-icon');
                        const colorPicker = foreColorBtn.querySelector('.color-picker');
                        if (colorIcon && colorPicker) {
                            // Convert RGB to hex if needed
                            const hexColor = this.rgbToHex(currentColor);
                            colorIcon.style.color = hexColor;
                            colorPicker.value = hexColor;
                        }
                    }
                }

                const hiliteColorBtn = this.toolbar.querySelector('[data-command="hiliteColor"]');
                if (hiliteColorBtn) {
                    const currentBgColor = document.queryCommandValue('hiliteColor');
                    if (currentBgColor) {
                        const highlightIcon = hiliteColorBtn.querySelector('.highlight-icon');
                        const colorPicker = hiliteColorBtn.querySelector('.color-picker');
                        if (highlightIcon && colorPicker) {
                            const hexColor = this.rgbToHex(currentBgColor);
                            highlightIcon.style.background = hexColor;
                            colorPicker.value = hexColor;
                        }
                    }
                }
            } catch (error) {
                // Ignore errors from queryCommandValue
            }
        }

        /**
         * Convert RGB color to hex
         */
        rgbToHex(rgb) {
            if (!rgb) return '#000000';
            
            // If it's already hex, return it
            if (rgb.startsWith('#')) return rgb;
            
            // Handle rgb() format
            const rgbMatch = rgb.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
            if (rgbMatch) {
                const r = parseInt(rgbMatch[1]);
                const g = parseInt(rgbMatch[2]);
                const b = parseInt(rgbMatch[3]);
                return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
            }
            
            // Handle named colors (basic ones)
            const namedColors = {
                'black': '#000000',
                'white': '#ffffff',
                'red': '#ff0000',
                'green': '#008000',
                'blue': '#0000ff',
                'yellow': '#ffff00',
                'cyan': '#00ffff',
                'magenta': '#ff00ff'
            };
            
            return namedColors[rgb.toLowerCase()] || '#000000';
        }

        /**
         * Normalize content structure
         */
        normalizeContent() {
            // Ensure content is wrapped in proper block elements
            const content = this.editor.innerHTML.trim();
            if (!content || content === '<br>') {
                this.editor.innerHTML = '<p><br></p>';
            }
        }

        /**
         * Update document statistics
         */
        updateStats() {
            if (!this.sidebar) return;
            
            const text = this.currentMode === 'markdown' ? this.editor.textContent : (this.editor.textContent || '');
            const html = this.currentMode === 'visual' ? this.editor.innerHTML : '';
            
            // Count words
            const words = text.split(/\s+/).filter(word => word.length > 0);
            const wordCount = words.length;
            
            // Count characters (excluding whitespace)
            const charCount = text.replace(/\s/g, '').length;
            
            // Count paragraphs
            let paragraphCount = 1;
            if (this.currentMode === 'markdown') {
                paragraphCount = text.split(/\n\s*\n/).filter(p => p.trim().length > 0).length;
            } else {
                const paragraphs = html.split(/<\/p>|<br\s*\/?>/i).filter(p => p.trim().length > 0);
                paragraphCount = Math.max(1, paragraphs.length);
            }
            
            // Update display
            const wordCountEl = this.sidebar.querySelector('#word-count');
            const charCountEl = this.sidebar.querySelector('#char-count');
            const paragraphCountEl = this.sidebar.querySelector('#paragraph-count');
            
            if (wordCountEl) wordCountEl.textContent = wordCount;
            if (charCountEl) charCountEl.textContent = charCount;
            if (paragraphCountEl) paragraphCountEl.textContent = paragraphCount;
            
            // Update mode indicator
            const modeValueEl = this.sidebar.querySelector('#current-mode');
            const modeDescEl = this.sidebar.querySelector('#mode-description');
            
            if (modeValueEl) {
                modeValueEl.textContent = this.getCurrentMode();
            }
            
            if (modeDescEl) {
                const descriptions = {
                    'visual': 'Rich text editing with visual formatting',
                    'markdown': 'Plain text editing with markdown syntax',
                    'source': 'Raw HTML source code editing'
                };
                modeDescEl.textContent = descriptions[this.getCurrentMode()] || '';
            }
        }

        /**
         * Start autosave functionality
         */
        startAutosave() {
            this.autosaveTimer = setInterval(() => {
                if (this.isInitialized) {
                    const content = this.getContent();
                    this.emit('autosave', { content, editor: this });
                }
            }, this.config.autosaveInterval);
        }

        /**
         * Stop autosave functionality
         */
        stopAutosave() {
            if (this.autosaveTimer) {
                clearInterval(this.autosaveTimer);
                this.autosaveTimer = null;
            }
        }

        /**
         * Reset autosave timer
         */
        resetAutosaveTimer() {
            this.stopAutosave();
            this.startAutosave();
        }

        /**
         * Get current editor content
         */
        getContent() {
            if (!this.editor) return { html: '', text: '', markdown: '' };
            
            let html = '';
            let text = '';
            let markdown = '';
            
            if (this.currentMode === 'markdown') {
                markdown = this.editor.textContent || '';
                html = this.markdownToHtml(markdown);
                text = this.editor.textContent || '';
            } else if (this.getCurrentMode() === 'source') {
                html = this.editor.textContent || '';
                text = this.editor.textContent || '';
                markdown = this.htmlToMarkdown(html);
            } else {
                html = this.editor.innerHTML || '';
                text = this.editor.textContent || this.editor.innerText || '';
                markdown = this.htmlToMarkdown(html);
            }
            
            return {
                html: html,
                text: text,
                markdown: markdown,
                mode: this.getCurrentMode()
            };
        }

        /**
         * Set editor content
         */
        setContent(content) {
            if (!this.editor) {
                throw new Error('Editor not initialized');
            }
            
            if (typeof content === 'string') {
                if (this.currentMode === 'markdown') {
                    this.editor.textContent = content;
                    this.markdownContent = content;
                } else {
                    this.editor.innerHTML = content;
                    this.visualContent = content;
                }
            } else if (content && typeof content === 'object') {
                if (this.currentMode === 'markdown' && content.markdown) {
                    this.editor.textContent = content.markdown;
                    this.markdownContent = content.markdown;
                } else if (content.html) {
                    this.editor.innerHTML = content.html;
                    this.visualContent = content.html;
                }
            }
            
            this.updateStats();
        }

        /**
         * Save content (triggers save event)
         */
        save() {
            const content = this.getContent();
            this.emit('save', { content, editor: this });
            return content;
        }

        /**
         * Focus the editor
         */
        focus() {
            if (this.editor) {
                this.editor.focus();
            }
        }

        /**
         * Check if editor is ready
         */
        isReady() {
            return this.isInitialized && this.editor;
        }

        /**
         * Toggle source view
         */
        toggleSourceView() {
            if (this.editor.contentEditable === 'true') {
                // Switch to source view
                const html = this.editor.innerHTML;
                this.editor.contentEditable = 'false';
                this.editor.style.fontFamily = 'monospace';
                this.editor.style.whiteSpace = 'pre-wrap';
                this.editor.textContent = this.formatHTML(html);
                this.container.classList.add('source-view');
            } else {
                // Switch back to visual view
                const html = this.editor.textContent;
                this.editor.contentEditable = 'true';
                this.editor.style.fontFamily = '';
                this.editor.style.whiteSpace = '';
                this.editor.innerHTML = html;
                this.container.classList.remove('source-view');
            }
        }

        /**
         * Get current mode (visual, markdown, or source)
         */
        getCurrentMode() {
            if (this.container && this.container.classList.contains('source-view')) {
                return 'source';
            }
            return this.currentMode;
        }

        /**
         * Get editor state
         */
        getState() {
            return {
                initialized: this.isInitialized,
                mode: this.getCurrentMode(),
                hasContent: this.editor ? this.editor.innerHTML.trim().length > 0 : false,
                wordCount: this.getWordCount(),
                characterCount: this.getCharacterCount()
            };
        }

        /**
         * Get word count
         */
        getWordCount() {
            if (!this.editor) return 0;
            const text = this.editor.textContent || '';
            const words = text.split(/\s+/).filter(word => word.length > 0);
            return words.length;
        }

        /**
         * Get character count
         */
        getCharacterCount() {
            if (!this.editor) return 0;
            const text = this.editor.textContent || '';
            return text.replace(/\s/g, '').length;
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
         * Check if editor is ready
         */
        isReady() {
            return this.isInitialized && this.container && this.editor;
        }

        /**
         * Get current editing mode
         */
        getCurrentMode() {
            return this.currentMode;
        }

        /**
         * Get editor state
         */
        getState() {
            return {
                mode: this.currentMode,
                content: this.getContent(),
                isInitialized: this.isInitialized,
                hasUnsavedChanges: this.hasUnsavedChanges || false
            };
        }

        /**
         * Switch editing mode
         */
        switchMode(mode) {
            if (mode === 'markdown' || mode === 'wysiwyg' || mode === 'visual') {
                if (mode === 'markdown') {
                    this.switchToMarkdownMode();
                } else if (mode === 'wysiwyg' || mode === 'visual') {
                    this.switchToVisualMode();
                }
            }
        }

        /**
         * Get content from editor
         */
        getContent() {
            if (!this.editor) return '';
            
            if (this.currentMode === 'markdown') {
                return {
                    html: this.markdownToHtml(this.editor.textContent || ''),
                    markdown: this.editor.textContent || '',
                    text: this.editor.textContent || ''
                };
            } else {
                return {
                    html: this.editor.innerHTML || '',
                    markdown: this.htmlToMarkdown(this.editor.innerHTML || ''),
                    text: this.editor.textContent || ''
                };
            }
        }

        /**
         * Set content in editor
         */
        setContent(content) {
            if (!this.editor) return;
            
            if (typeof content === 'string') {
                if (this.currentMode === 'markdown') {
                    this.editor.textContent = content;
                } else {
                    this.editor.innerHTML = content;
                }
            } else if (content && typeof content === 'object') {
                if (this.currentMode === 'markdown' && content.markdown) {
                    this.editor.textContent = content.markdown;
                } else if (content.html) {
                    this.editor.innerHTML = content.html;
                }
            }
            
            this.handleInput();
        }

        /**
         * Destroy the editor
         */
        destroy() {
            try {
                this.stopAutosave();
                
                if (this.editor) {
                    this.editor.removeEventListener('input', this.handleInput);
                    this.editor.removeEventListener('keydown', this.handleKeyDown);
                    this.editor.removeEventListener('paste', this.handlePaste);
                }
                
                if (this.container) {
                    this.container.innerHTML = '';
                    this.container.className = '';
                }
                
                this.eventListeners.clear();
                this.isInitialized = false;
                
                this.emit('destroyed', { editor: this });
            } catch (error) {
                console.error('Error destroying editor:', error);
            }
        }
    }

    // Factory function for easy initialization
    function createAdvancedEditor(config) {
        const editor = new AdvancedEditor(config);
        return editor;
    }

    // Export for global use
    window.AdvancedEditor = AdvancedEditor;
    window.SimpleEditor = AdvancedEditor; // Backward compatibility
    window.createAdvancedEditor = createAdvancedEditor;
    window.createSimpleEditor = createAdvancedEditor;

})(window);