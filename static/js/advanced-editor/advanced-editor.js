/**
 * Advanced Editor System - Main Integration
 * 
 * This module integrates all components of the advanced editor system
 * and provides a simple API for initializing and using the editor.
 */

(function(window) {
    'use strict';

    // Check if required dependencies are available
    if (typeof window.EditorController === 'undefined' || 
        typeof window.EditorToolbar === 'undefined' || 
        typeof window.EditorSidebar === 'undefined') {
        console.error('Advanced Editor dependencies not loaded. Please include editor-core.js and editor-ui.js first.');
        return;
    }

    const { EditorController, BlockManager, ContentProcessor } = window;
    const { EditorToolbar, EditorSidebar } = window;

    /**
     * AdvancedEditor - Main class that orchestrates the entire editor system
     */
    class AdvancedEditor {
        constructor(config = {}) {
            this.config = {
                container: null,
                content: '',
                mode: 'wysiwyg',
                showToolbar: true,
                showSidebar: true,
                autosave: true,
                autosaveInterval: 30000, // 30 seconds
                placeholder: 'Start writing your post...',
                ...config
            };
            
            this.container = null;
            this.editorController = null;
            this.toolbar = null;
            this.sidebar = null;
            this.autosaveTimer = null;
            this.isInitialized = false;
            
            // Bind methods
            this.handleAutosave = this.handleAutosave.bind(this);
            this.handleResize = this.handleResize.bind(this);
        }

        /**
         * Initialize the complete editor system
         */
        async initialize() {
            try {
                // Validate configuration
                if (!this.config.container) {
                    throw new Error('Container element is required');
                }
                
                this.container = typeof this.config.container === 'string' 
                    ? document.querySelector(this.config.container)
                    : this.config.container;
                    
                if (!this.container) {
                    throw new Error('Container element not found');
                }

                // Create editor structure
                this.createEditorStructure();
                
                // Initialize editor controller
                const editorElement = this.container.querySelector('.editor-content-area');
                this.editorController = new EditorController({
                    element: editorElement,
                    content: this.config.content,
                    editable: true,
                    autofocus: this.config.autofocus,
                    onUpdate: this.handleEditorUpdate.bind(this),
                    onCreate: this.handleEditorCreate.bind(this),
                    onDestroy: this.handleEditorDestroy.bind(this)
                });
                
                await this.editorController.initialize();
                
                // Initialize UI components
                if (this.config.showToolbar) {
                    const toolbarContainer = this.container.querySelector('.toolbar-container');
                    this.toolbar = new EditorToolbar(this.editorController, toolbarContainer);
                    this.toolbar.initialize();
                }
                
                if (this.config.showSidebar) {
                    const sidebarContainer = this.container.querySelector('.sidebar-container');
                    this.sidebar = new EditorSidebar(this.editorController, sidebarContainer);
                    this.sidebar.initialize();
                }
                
                // Set up autosave
                if (this.config.autosave) {
                    this.startAutosave();
                }
                
                // Set up event listeners
                this.setupEventListeners();
                
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
            this.container.className = 'advanced-editor-container';
            this.container.innerHTML = `
                ${this.config.showToolbar ? '<div class="toolbar-container"></div>' : ''}
                <div class="advanced-editor-wrapper">
                    <div class="editor-main">
                        <div class="editor-pane">
                            <div class="editor-content-area" data-placeholder="${this.config.placeholder}"></div>
                        </div>
                    </div>
                    ${this.config.showSidebar ? '<div class="sidebar-container"></div>' : ''}
                </div>
            `;
        }

        /**
         * Set up global event listeners
         */
        setupEventListeners() {
            // Handle window resize
            window.addEventListener('resize', this.handleResize);
            
            // Handle keyboard shortcuts
            document.addEventListener('keydown', this.handleKeyboardShortcuts.bind(this));
            
            // Handle editor focus/blur
            this.editorController.on('focus', this.handleEditorFocus.bind(this));
            this.editorController.on('blur', this.handleEditorBlur.bind(this));
            
            // Handle mode changes
            this.editorController.on('modeChanged', this.handleModeChange.bind(this));
        }

        /**
         * Handle keyboard shortcuts
         */
        handleKeyboardShortcuts(event) {
            if (!this.isInitialized || !this.editorController.isReady()) return;
            
            // Ctrl/Cmd + S for save
            if ((event.ctrlKey || event.metaKey) && event.key === 's') {
                event.preventDefault();
                this.save();
            }
            
            // Ctrl/Cmd + Shift + M for mode toggle
            if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'M') {
                event.preventDefault();
                this.toggleMode();
            }
        }

        /**
         * Handle editor update events
         */
        handleEditorUpdate({ content }) {
            this.emit('update', { content, editor: this });
            
            // Reset autosave timer
            if (this.config.autosave) {
                this.resetAutosaveTimer();
            }
        }

        /**
         * Handle editor create events
         */
        handleEditorCreate() {
            this.emit('create', { editor: this });
        }

        /**
         * Handle editor destroy events
         */
        handleEditorDestroy() {
            this.emit('destroy', { editor: this });
        }

        /**
         * Handle editor focus events
         */
        handleEditorFocus() {
            this.container.classList.add('editor-focused');
            this.emit('focus', { editor: this });
        }

        /**
         * Handle editor blur events
         */
        handleEditorBlur() {
            this.container.classList.remove('editor-focused');
            this.emit('blur', { editor: this });
        }

        /**
         * Handle mode change events
         */
        handleModeChange({ currentMode, previousMode }) {
            this.container.classList.remove(`mode-${previousMode}`);
            this.container.classList.add(`mode-${currentMode}`);
            this.emit('modeChanged', { currentMode, previousMode, editor: this });
        }

        /**
         * Handle window resize
         */
        handleResize() {
            // Update editor layout if needed
            this.emit('resize', { editor: this });
        }

        /**
         * Start autosave functionality
         */
        startAutosave() {
            this.autosaveTimer = setInterval(this.handleAutosave, this.config.autosaveInterval);
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
         * Handle autosave
         */
        handleAutosave() {
            if (!this.isInitialized || !this.editorController.isReady()) return;
            
            try {
                const content = this.getContent();
                
                // Save to localStorage as backup
                this.saveToLocalStorage(content);
                
                // Emit autosave event for custom handling
                this.emit('autosave', { content, editor: this });
                
            } catch (error) {
                console.error('Autosave failed:', error);
            }
        }

        /**
         * Save content to localStorage
         */
        saveToLocalStorage(content) {
            try {
                const key = `advanced-editor-backup-${Date.now()}`;
                const data = {
                    content,
                    timestamp: new Date().toISOString(),
                    mode: this.getCurrentMode()
                };
                
                localStorage.setItem(key, JSON.stringify(data));
                
                // Keep only the last 5 backups
                const keys = Object.keys(localStorage).filter(k => k.startsWith('advanced-editor-backup-'));
                if (keys.length > 5) {
                    keys.sort().slice(0, -5).forEach(k => localStorage.removeItem(k));
                }
                
            } catch (error) {
                console.warn('Failed to save to localStorage:', error);
            }
        }

        /**
         * Get current editor content
         */
        getContent() {
            if (!this.editorController) {
                throw new Error('Editor not initialized');
            }
            return this.editorController.getContent();
        }

        /**
         * Set editor content
         */
        setContent(content) {
            if (!this.editorController) {
                throw new Error('Editor not initialized');
            }
            this.editorController.setContent(content);
        }

        /**
         * Get current editing mode
         */
        getCurrentMode() {
            if (!this.editorController) return null;
            return this.editorController.getCurrentMode();
        }

        /**
         * Switch editing mode
         */
        switchMode(mode) {
            if (!this.editorController) {
                throw new Error('Editor not initialized');
            }
            this.editorController.switchMode(mode);
        }

        /**
         * Toggle between WYSIWYG and Markdown modes
         */
        toggleMode() {
            const currentMode = this.getCurrentMode();
            const newMode = currentMode === 'wysiwyg' ? 'markdown' : 'wysiwyg';
            this.switchMode(newMode);
        }

        /**
         * Execute editor command
         */
        executeCommand(command, ...args) {
            if (!this.editorController) {
                throw new Error('Editor not initialized');
            }
            return this.editorController.executeCommand(command, ...args);
        }

        /**
         * Get editor state
         */
        getState() {
            if (!this.editorController) return null;
            return this.editorController.getState();
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
            if (this.editorController && this.editorController.editor) {
                this.editorController.editor.commands.focus();
            }
        }

        /**
         * Check if editor is ready
         */
        isReady() {
            return this.isInitialized && this.editorController && this.editorController.isReady();
        }

        /**
         * Event handling
         */
        on(event, callback) {
            if (!this.eventListeners) {
                this.eventListeners = new Map();
            }
            
            if (!this.eventListeners.has(event)) {
                this.eventListeners.set(event, []);
            }
            this.eventListeners.get(event).push(callback);
        }

        off(event, callback) {
            if (!this.eventListeners || !this.eventListeners.has(event)) return;
            
            const callbacks = this.eventListeners.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }

        emit(event, data = {}) {
            if (!this.eventListeners || !this.eventListeners.has(event)) return;
            
            this.eventListeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in event listener for ${event}:`, error);
                }
            });
        }

        /**
         * Destroy the editor and clean up resources
         */
        destroy() {
            try {
                // Stop autosave
                this.stopAutosave();
                
                // Remove event listeners
                window.removeEventListener('resize', this.handleResize);
                document.removeEventListener('keydown', this.handleKeyboardShortcuts);
                
                // Destroy components
                if (this.toolbar) {
                    this.toolbar.destroy();
                    this.toolbar = null;
                }
                
                if (this.sidebar) {
                    this.sidebar.destroy();
                    this.sidebar = null;
                }
                
                if (this.editorController) {
                    this.editorController.destroy();
                    this.editorController = null;
                }
                
                // Clear container
                if (this.container) {
                    this.container.innerHTML = '';
                    this.container.className = '';
                }
                
                // Clear event listeners
                if (this.eventListeners) {
                    this.eventListeners.clear();
                }
                
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
    window.createAdvancedEditor = createAdvancedEditor;

})(window);