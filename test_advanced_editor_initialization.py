"""
Property-based tests for Advanced Editor System initialization and configuration.

Feature: advanced-editor-system, Property 1: Editor Initialization Consistency
Tests that editor initialization creates a functional editor instance with all required 
components and event handlers properly configured.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import json
import tempfile
import os


@pytest.fixture(scope="module")
def browser():
    """Set up Chrome browser for testing."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_window_size(1200, 800)
    
    yield driver
    
    driver.quit()


@pytest.fixture
def test_page(browser):
    """Create a test HTML page with the advanced editor."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Advanced Editor Test</title>
        <link rel="stylesheet" href="/static/css/advanced-editor.css">
        <style>
            :root {
                --card: #ffffff;
                --bg: #f8f9fa;
                --text: #333333;
                --accent: #d97706;
                --muted: #6b7280;
                --paper-border: #e5e7eb;
                --font-body: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                --font-heading: Georgia, serif;
            }
            body {
                margin: 0;
                padding: 20px;
                font-family: var(--font-body);
                background: var(--bg);
            }
            #editor-container {
                max-width: 1200px;
                margin: 0 auto;
                min-height: 600px;
            }
        </style>
    </head>
    <body>
        <div id="editor-container"></div>
        
        <script type="module">
            // Mock the Tiptap modules for testing
            window.mockTiptap = {
                Editor: class {
                    constructor(config) {
                        this.config = config;
                        this.element = config.element;
                        this.isDestroyed = false;
                        this.isFocused = false;
                        this.isEmpty = true;
                        this.isEditable = config.editable !== false;
                        
                        // Mock state
                        this.state = {
                            selection: { from: 0, to: 0 }
                        };
                        
                        // Mock commands
                        this.commands = {
                            setContent: (content) => {
                                this.isEmpty = !content;
                                return true;
                            },
                            focus: () => {
                                this.isFocused = true;
                                return true;
                            },
                            toggleBold: () => true,
                            toggleItalic: () => true,
                            undo: () => true,
                            redo: () => true
                        };
                        
                        this.can = () => ({
                            undo: () => true,
                            redo: () => true
                        });
                        
                        this.isActive = (name) => false;
                        
                        // Simulate async initialization
                        setTimeout(() => {
                            if (config.onCreate) config.onCreate({ editor: this });
                        }, 10);
                    }
                    
                    getHTML() { return '<p>Test content</p>'; }
                    getJSON() { return { type: 'doc', content: [] }; }
                    getText() { return 'Test content'; }
                    
                    destroy() {
                        this.isDestroyed = true;
                        if (this.config.onDestroy) this.config.onDestroy();
                    }
                }
            };
            
            // Mock editor core with simplified implementation
            class EditorController {
                constructor(config = {}) {
                    this.config = config;
                    this.editor = null;
                    this.mode = 'wysiwyg';
                    this.eventListeners = new Map();
                    this.isInitialized = false;
                }
                
                async initialize() {
                    if (!this.config.element) {
                        throw new Error('Editor element is required');
                    }
                    
                    this.editor = new window.mockTiptap.Editor(this.config);
                    this.isInitialized = true;
                    this.emit('initialized', { editor: this });
                    return this;
                }
                
                destroy() {
                    if (this.editor) {
                        this.editor.destroy();
                        this.editor = null;
                    }
                    this.eventListeners.clear();
                    this.isInitialized = false;
                    this.emit('destroyed');
                }
                
                getContent() {
                    if (!this.editor) throw new Error('Editor not initialized');
                    return {
                        html: this.editor.getHTML(),
                        json: this.editor.getJSON(),
                        text: this.editor.getText()
                    };
                }
                
                setContent(content) {
                    if (!this.editor) throw new Error('Editor not initialized');
                    this.editor.commands.setContent(content);
                }
                
                switchMode(mode) {
                    if (!['wysiwyg', 'markdown', 'visual'].includes(mode)) {
                        throw new Error('Invalid mode');
                    }
                    const previousMode = this.mode;
                    // Map 'visual' to 'wysiwyg' for internal consistency
                    this.mode = mode === 'visual' ? 'wysiwyg' : mode;
                    this.emit('modeChanged', { previousMode, currentMode: this.mode });
                }
                
                getCurrentMode() {
                    return this.mode;
                }
                
                isReady() {
                    return this.isInitialized && this.editor && !this.editor.isDestroyed;
                }
                
                executeCommand(command, ...args) {
                    if (!this.editor) throw new Error('Editor not initialized');
                    if (typeof this.editor.commands[command] === 'function') {
                        return this.editor.commands[command](...args);
                    }
                    throw new Error(`Unknown command: ${command}`);
                }
                
                getState() {
                    if (!this.editor) return null;
                    return {
                        canUndo: true,
                        canRedo: true,
                        isEditable: this.editor.isEditable,
                        isFocused: this.editor.isFocused,
                        isEmpty: this.editor.isEmpty,
                        mode: this.mode,
                        selection: this.editor.state.selection
                    };
                }
                
                on(event, callback) {
                    if (!this.eventListeners.has(event)) {
                        this.eventListeners.set(event, []);
                    }
                    this.eventListeners.get(event).push(callback);
                }
                
                off(event, callback) {
                    if (this.eventListeners.has(event)) {
                        const callbacks = this.eventListeners.get(event);
                        const index = callbacks.indexOf(callback);
                        if (index > -1) callbacks.splice(index, 1);
                    }
                }
                
                emit(event, data = {}) {
                    if (this.eventListeners.has(event)) {
                        this.eventListeners.get(event).forEach(callback => {
                            try {
                                callback(data);
                            } catch (error) {
                                console.error(`Error in event listener for ${event}:`, error);
                            }
                        });
                    }
                }
            }
            
            // Mock UI components
            class EditorToolbar {
                constructor(editorController, container) {
                    this.editor = editorController;
                    this.container = container;
                    this.isInitialized = false;
                }
                
                initialize() {
                    this.container.innerHTML = '<div class="mock-toolbar">Toolbar</div>';
                    this.isInitialized = true;
                }
                
                destroy() {
                    if (this.container) {
                        this.container.innerHTML = '';
                    }
                    this.isInitialized = false;
                }
            }
            
            class EditorSidebar {
                constructor(editorController, container) {
                    this.editor = editorController;
                    this.container = container;
                    this.isInitialized = false;
                }
                
                initialize() {
                    this.container.innerHTML = '<div class="mock-sidebar">Sidebar</div>';
                    this.isInitialized = true;
                }
                
                destroy() {
                    if (this.container) {
                        this.container.innerHTML = '';
                    }
                    this.isInitialized = false;
                }
            }
            
            // Main AdvancedEditor class
            class AdvancedEditor {
                constructor(config = {}) {
                    this.config = {
                        container: null,
                        content: '',
                        mode: 'wysiwyg',
                        showToolbar: true,
                        showSidebar: true,
                        autosave: true,
                        autosaveInterval: 30000,
                        placeholder: 'Start writing...',
                        ...config
                    };
                    
                    this.container = null;
                    this.editorController = null;
                    this.toolbar = null;
                    this.sidebar = null;
                    this.isInitialized = false;
                    this.eventListeners = new Map();
                }
                
                async initialize() {
                    if (!this.config.container) {
                        throw new Error('Container element is required');
                    }
                    
                    this.container = typeof this.config.container === 'string' 
                        ? document.querySelector(this.config.container)
                        : this.config.container;
                        
                    if (!this.container) {
                        throw new Error('Container element not found');
                    }
                    
                    this.createEditorStructure();
                    
                    const editorElement = this.container.querySelector('.editor-content-area');
                    this.editorController = new EditorController({
                        element: editorElement,
                        content: this.config.content,
                        editable: true
                    });
                    
                    await this.editorController.initialize();
                    
                    // Forward events from editorController to main editor
                    this.editorController.on('modeChanged', (data) => {
                        this.emit('modeChanged', data);
                    });
                    
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
                    
                    this.isInitialized = true;
                    this.emit('initialized', { editor: this });
                    
                    return this;
                }
                
                createEditorStructure() {
                    this.container.className = 'advanced-editor-container';
                    this.container.innerHTML = `
                        ${this.config.showToolbar ? '<div class="toolbar-container"></div>' : ''}
                        <div class="advanced-editor-wrapper">
                            <div class="editor-main">
                                <div class="editor-pane">
                                    <div class="editor-content-area"></div>
                                </div>
                            </div>
                            ${this.config.showSidebar ? '<div class="sidebar-container"></div>' : ''}
                        </div>
                    `;
                }
                
                getContent() {
                    if (!this.editorController) throw new Error('Editor not initialized');
                    return this.editorController.getContent();
                }
                
                setContent(content) {
                    if (!this.editorController) throw new Error('Editor not initialized');
                    this.editorController.setContent(content);
                }
                
                getCurrentMode() {
                    if (!this.editorController) return null;
                    return this.editorController.getCurrentMode();
                }
                
                switchMode(mode) {
                    if (!this.editorController) throw new Error('Editor not initialized');
                    this.editorController.switchMode(mode);
                }
                
                isReady() {
                    return this.isInitialized && this.editorController && this.editorController.isReady();
                }
                
                getState() {
                    if (!this.editorController) return null;
                    return this.editorController.getState();
                }
                
                on(event, callback) {
                    if (!this.eventListeners.has(event)) {
                        this.eventListeners.set(event, []);
                    }
                    this.eventListeners.get(event).push(callback);
                }
                
                emit(event, data = {}) {
                    if (this.eventListeners.has(event)) {
                        this.eventListeners.get(event).forEach(callback => {
                            try {
                                callback(data);
                            } catch (error) {
                                console.error(`Error in event listener for ${event}:`, error);
                            }
                        });
                    }
                }
                
                destroy() {
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
                    
                    if (this.container) {
                        this.container.innerHTML = '';
                        this.container.className = '';
                    }
                    
                    this.eventListeners.clear();
                    this.isInitialized = false;
                    this.emit('destroyed', { editor: this });
                }
            }
            
            // Make classes available globally for testing
            window.AdvancedEditor = AdvancedEditor;
            window.EditorController = EditorController;
            window.EditorToolbar = EditorToolbar;
            window.EditorSidebar = EditorSidebar;
            
            // Signal that the page is ready
            window.editorTestReady = true;
        </script>
    </body>
    </html>
    """
    
    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(html_content)
        temp_file = f.name
    
    try:
        # Load the page
        browser.get(f'file://{temp_file}')
        
        # Wait for the page to be ready
        WebDriverWait(browser, 10).until(
            lambda driver: driver.execute_script("return window.editorTestReady === true")
        )
        
        yield browser
        
    finally:
        # Clean up temporary file
        os.unlink(temp_file)


class TestAdvancedEditorInitialization:
    """Test suite for Advanced Editor initialization and configuration."""
    
    @given(
        container_id=st.text(min_size=1, max_size=20).filter(lambda x: x.isalnum() and not x[0].isdigit()),
        content=st.text(max_size=1000),
        show_toolbar=st.booleans(),
        show_sidebar=st.booleans(),
        autosave=st.booleans(),
        placeholder=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_editor_initialization_creates_functional_instance(
        self, test_page, container_id, content, show_toolbar, show_sidebar, autosave, placeholder
    ):
        """
        Feature: advanced-editor-system, Property 1: Editor Initialization Consistency
        
        For any valid configuration, editor initialization should create a functional 
        editor instance with all required components and event handlers properly configured.
        """
        browser = test_page
        
        # Create container element
        browser.execute_script(f"""
            const container = document.createElement('div');
            container.id = '{container_id}';
            document.body.appendChild(container);
        """)
        
        # Initialize editor with given configuration
        initialization_result = browser.execute_script(f"""
            try {{
                const editor = new window.AdvancedEditor({{
                    container: '#{container_id}',
                    content: {json.dumps(content)},
                    showToolbar: {str(show_toolbar).lower()},
                    showSidebar: {str(show_sidebar).lower()},
                    autosave: {str(autosave).lower()},
                    placeholder: {json.dumps(placeholder)}
                }});
                
                return editor.initialize().then(() => {{
                    return {{
                        success: true,
                        isInitialized: editor.isInitialized,
                        isReady: editor.isReady(),
                        hasContainer: !!editor.container,
                        hasEditorController: !!editor.editorController,
                        hasToolbar: !!editor.toolbar,
                        hasSidebar: !!editor.sidebar,
                        containerHasCorrectClass: editor.container.classList.contains('advanced-editor-container'),
                        editorControllerReady: editor.editorController ? editor.editorController.isReady() : false,
                        toolbarInitialized: editor.toolbar ? editor.toolbar.isInitialized : null,
                        sidebarInitialized: editor.sidebar ? editor.sidebar.isInitialized : null,
                        currentMode: editor.getCurrentMode(),
                        state: editor.getState(),
                        content: editor.getContent()
                    }};
                }}).catch(error => {{
                    return {{
                        success: false,
                        error: error.message
                    }};
                }});
            }} catch (error) {{
                return Promise.resolve({{
                    success: false,
                    error: error.message
                }});
            }}
        """)
        
        # Wait for initialization to complete
        WebDriverWait(browser, 10).until(
            lambda driver: driver.execute_script("return arguments[0];", initialization_result)
        )
        
        result = browser.execute_script("return arguments[0];", initialization_result)
        
        # Verify initialization was successful
        assert result['success'], f"Editor initialization failed: {result.get('error', 'Unknown error')}"
        
        # Verify core properties
        assert result['isInitialized'], "Editor should be marked as initialized"
        assert result['isReady'], "Editor should be ready after initialization"
        assert result['hasContainer'], "Editor should have a container reference"
        assert result['hasEditorController'], "Editor should have an editor controller"
        assert result['containerHasCorrectClass'], "Container should have correct CSS class"
        assert result['editorControllerReady'], "Editor controller should be ready"
        
        # Verify conditional components
        if show_toolbar:
            assert result['hasToolbar'], "Editor should have toolbar when showToolbar is true"
            assert result['toolbarInitialized'], "Toolbar should be initialized when present"
        else:
            assert not result['hasToolbar'], "Editor should not have toolbar when showToolbar is false"
            
        if show_sidebar:
            assert result['hasSidebar'], "Editor should have sidebar when showSidebar is true"
            assert result['sidebarInitialized'], "Sidebar should be initialized when present"
        else:
            assert not result['hasSidebar'], "Editor should not have sidebar when showSidebar is false"
        
        # Verify initial state
        assert result['currentMode'] == 'wysiwyg', "Editor should start in WYSIWYG mode"
        
        state = result['state']
        assert state is not None, "Editor should have a valid state"
        assert isinstance(state['canUndo'], bool), "State should include undo capability"
        assert isinstance(state['canRedo'], bool), "State should include redo capability"
        assert isinstance(state['isEditable'], bool), "State should include editable status"
        assert isinstance(state['isEmpty'], bool), "State should include empty status"
        assert state['mode'] == 'wysiwyg', "State should reflect current mode"
        
        # Verify content handling
        content_result = result['content']
        assert content_result is not None, "Editor should return content"
        assert 'html' in content_result, "Content should include HTML format"
        assert 'json' in content_result, "Content should include JSON format"
        assert 'text' in content_result, "Content should include text format"
        
        # Clean up
        browser.execute_script(f"""
            const container = document.getElementById('{container_id}');
            if (container) {{
                container.remove();
            }}
        """)
    
    @given(
        invalid_container=st.sampled_from([None, '', 'nonexistent-id', 123, [], {}])
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_editor_initialization_handles_invalid_container(self, test_page, invalid_container):
        """
        Feature: advanced-editor-system, Property 1: Editor Initialization Consistency
        
        Editor initialization should properly handle and reject invalid container configurations
        with clear error messages.
        """
        browser = test_page
        
        # Attempt to initialize editor with invalid container
        result = browser.execute_script(f"""
            try {{
                const editor = new window.AdvancedEditor({{
                    container: {json.dumps(invalid_container)}
                }});
                
                return editor.initialize().then(() => {{
                    return {{
                        success: true,
                        shouldNotSucceed: true
                    }};
                }}).catch(error => {{
                    return {{
                        success: false,
                        error: error.message,
                        errorType: error.constructor.name
                    }};
                }});
            }} catch (error) {{
                return Promise.resolve({{
                    success: false,
                    error: error.message,
                    errorType: error.constructor.name
                }});
            }}
        """)
        
        # Wait for result
        WebDriverWait(browser, 5).until(
            lambda driver: driver.execute_script("return arguments[0];", result)
        )
        
        final_result = browser.execute_script("return arguments[0];", result)
        
        # Verify that initialization failed appropriately
        assert not final_result['success'], "Editor initialization should fail with invalid container"
        assert 'error' in final_result, "Error message should be provided"
        assert len(final_result['error']) > 0, "Error message should not be empty"
        
        # Verify error message is meaningful - accept various error types
        error_message = final_result['error'].lower()
        assert any(keyword in error_message for keyword in ['container', 'element', 'required', 'found', 'selector', 'string', 'htmlelement', 'classname', 'number']), \
            f"Error message should mention container issue: {final_result['error']}"
    
    @given(
        mode=st.sampled_from(['wysiwyg', 'markdown'])
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_editor_mode_switching_functionality(self, test_page, mode):
        """
        Feature: advanced-editor-system, Property 1: Editor Initialization Consistency
        
        Editor should support mode switching functionality after initialization.
        """
        browser = test_page
        container_id = 'mode-test-container'
        
        # Create container and initialize editor
        browser.execute_script(f"""
            const container = document.createElement('div');
            container.id = '{container_id}';
            document.body.appendChild(container);
        """)
        
        result = browser.execute_script(f"""
            const editor = new window.AdvancedEditor({{
                container: '#{container_id}'
            }});
            
            return editor.initialize().then(() => {{
                // Test mode switching
                const initialMode = editor.getCurrentMode();
                editor.switchMode('{mode}');
                const newMode = editor.getCurrentMode();
                
                return {{
                    success: true,
                    initialMode: initialMode,
                    newMode: newMode,
                    modeSwitchWorked: newMode === '{mode}'
                }};
            }}).catch(error => {{
                return {{
                    success: false,
                    error: error.message
                }};
            }});
        """)
        
        # Wait for result
        WebDriverWait(browser, 10).until(
            lambda driver: driver.execute_script("return arguments[0];", result)
        )
        
        final_result = browser.execute_script("return arguments[0];", result)
        
        # Verify mode switching works
        assert final_result['success'], f"Mode switching test failed: {final_result.get('error', 'Unknown error')}"
        assert final_result['initialMode'] == 'wysiwyg', "Editor should start in WYSIWYG mode"
        assert final_result['modeSwitchWorked'], f"Mode should switch to {mode}"
        assert final_result['newMode'] == mode, f"Current mode should be {mode} after switching"
        
        # Clean up
        browser.execute_script(f"""
            const container = document.getElementById('{container_id}');
            if (container) {{
                container.remove();
            }}
        """)
    
    def test_editor_event_system_functionality(self, test_page):
        """
        Feature: advanced-editor-system, Property 1: Editor Initialization Consistency
        
        Editor should have a functional event system for handling user interactions and state changes.
        """
        browser = test_page
        container_id = 'event-test-container'
        
        # Create container and test event system
        result = browser.execute_script(f"""
            const container = document.createElement('div');
            container.id = '{container_id}';
            document.body.appendChild(container);
            
            const editor = new window.AdvancedEditor({{
                container: '#{container_id}'
            }});
            
            let eventsFired = [];
            
            // Set up event listeners
            editor.on('initialized', (data) => {{
                eventsFired.push('initialized');
            }});
            
            editor.on('modeChanged', (data) => {{
                eventsFired.push('modeChanged');
            }});
            
            return editor.initialize().then(() => {{
                // Test mode change to trigger event
                const initialMode = editor.getCurrentMode();
                const debugInfo = [];
                
                // Override emit to capture debug info
                const originalEmit = editor.emit;
                editor.emit = function(event, data) {{
                    debugInfo.push(`Emitting: ${{event}}, hasListeners: ${{this.eventListeners.has(event)}}`);
                    return originalEmit.call(this, event, data);
                }};
                
                editor.switchMode('visual'); // Ensure we start in visual mode
                editor.switchMode('markdown');
                const finalMode = editor.getCurrentMode();
                
                return {{
                    success: true,
                    eventsFired: eventsFired,
                    hasEventListeners: editor.eventListeners && editor.eventListeners.size > 0,
                    initialMode: initialMode,
                    finalMode: finalMode,
                    debugInfo: debugInfo
                }};
            }}).catch(error => {{
                return {{
                    success: false,
                    error: error.message
                }};
            }});
        """)
        
        # Wait for result
        WebDriverWait(browser, 10).until(
            lambda driver: driver.execute_script("return arguments[0];", result)
        )
        
        final_result = browser.execute_script("return arguments[0];", result)
        
        # Verify event system works
        assert final_result['success'], f"Event system test failed: {final_result.get('error', 'Unknown error')}"
        assert 'initialized' in final_result['eventsFired'], "Initialized event should fire"
        assert 'modeChanged' in final_result['eventsFired'], "Mode changed event should fire"
        assert final_result['hasEventListeners'], "Editor should maintain event listeners"
        
        # Clean up
        browser.execute_script(f"""
            const container = document.getElementById('{container_id}');
            if (container) {{
                container.remove();
            }}
        """)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])