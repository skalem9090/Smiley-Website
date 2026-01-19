/**
 * Advanced Editor System - Code Editor with Syntax Highlighting
 * 
 * This module implements advanced code editing features including:
 * - Syntax highlighting for 20+ programming languages using Prism.js
 * - Line numbers and proper indentation
 * - Language selection dropdown
 * - Inline code formatting
 * - Copy-to-clipboard functionality
 * - Code block themes and styling
 * 
 * Validates Property 9: Code Block Functionality
 * Validates Property 10: Inline Code Formatting
 */

(function(window) {
    'use strict';

    /**
     * Supported programming languages for syntax highlighting
     */
    const SUPPORTED_LANGUAGES = [
        { value: 'javascript', label: 'JavaScript', aliases: ['js'] },
        { value: 'typescript', label: 'TypeScript', aliases: ['ts'] },
        { value: 'python', label: 'Python', aliases: ['py'] },
        { value: 'java', label: 'Java', aliases: [] },
        { value: 'csharp', label: 'C#', aliases: ['cs'] },
        { value: 'cpp', label: 'C++', aliases: ['c++'] },
        { value: 'c', label: 'C', aliases: [] },
        { value: 'php', label: 'PHP', aliases: [] },
        { value: 'ruby', label: 'Ruby', aliases: ['rb'] },
        { value: 'go', label: 'Go', aliases: ['golang'] },
        { value: 'rust', label: 'Rust', aliases: ['rs'] },
        { value: 'swift', label: 'Swift', aliases: [] },
        { value: 'kotlin', label: 'Kotlin', aliases: ['kt'] },
        { value: 'sql', label: 'SQL', aliases: [] },
        { value: 'html', label: 'HTML', aliases: ['markup'] },
        { value: 'css', label: 'CSS', aliases: [] },
        { value: 'scss', label: 'SCSS', aliases: ['sass'] },
        { value: 'json', label: 'JSON', aliases: [] },
        { value: 'yaml', label: 'YAML', aliases: ['yml'] },
        { value: 'markdown', label: 'Markdown', aliases: ['md'] },
        { value: 'bash', label: 'Bash', aliases: ['shell', 'sh'] },
        { value: 'powershell', label: 'PowerShell', aliases: ['ps1'] },
        { value: 'docker', label: 'Dockerfile', aliases: ['dockerfile'] },
        { value: 'xml', label: 'XML', aliases: [] },
        { value: 'plaintext', label: 'Plain Text', aliases: ['text', 'txt'] }
    ];

    /**
     * Code Editor Manager
     * Handles code block creation, editing, and syntax highlighting
     */
    class CodeEditor {
        constructor() {
            this.prismLoaded = false;
            this.initializePrism();
        }

        /**
         * Initialize Prism.js and configure autoloader
         */
        initializePrism() {
            if (typeof Prism !== 'undefined') {
                this.prismLoaded = true;
                
                // Configure Prism autoloader for additional languages
                if (Prism.plugins && Prism.plugins.autoloader) {
                    Prism.plugins.autoloader.languages_path = 
                        'https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/';
                }
                
                console.log('Prism.js initialized successfully');
            } else {
                console.warn('Prism.js not loaded');
            }
        }

        /**
         * Create a code block element with syntax highlighting
         * @param {string} code - Code content
         * @param {string} language - Programming language
         * @param {Object} options - Additional options
         * @returns {HTMLElement} Code block element
         */
        createCodeBlock(code, language = 'plaintext', options = {}) {
            const {
                lineNumbers = true,
                copyButton = true,
                theme = 'tomorrow'
            } = options;

            // Create container
            const container = document.createElement('div');
            container.className = 'code-block-container';
            container.setAttribute('data-language', language);

            // Create toolbar
            if (copyButton) {
                const toolbar = this.createToolbar(language, code);
                container.appendChild(toolbar);
            }

            // Create pre element
            const pre = document.createElement('pre');
            if (lineNumbers) {
                pre.className = 'line-numbers';
            }

            // Create code element
            const codeElement = document.createElement('code');
            codeElement.className = `language-${language}`;
            codeElement.textContent = code;

            pre.appendChild(codeElement);
            container.appendChild(pre);

            // Apply syntax highlighting
            if (this.prismLoaded) {
                Prism.highlightElement(codeElement);
            }

            return container;
        }

        /**
         * Create toolbar for code block
         * @param {string} language - Programming language
         * @param {string} code - Code content
         * @returns {HTMLElement} Toolbar element
         */
        createToolbar(language, code) {
            const toolbar = document.createElement('div');
            toolbar.className = 'code-block-toolbar';

            // Language label
            const languageLabel = document.createElement('span');
            languageLabel.className = 'code-language-label';
            const langInfo = this.getLanguageInfo(language);
            languageLabel.textContent = langInfo.label;
            toolbar.appendChild(languageLabel);

            // Copy button
            const copyButton = document.createElement('button');
            copyButton.className = 'code-copy-button';
            copyButton.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M4 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" 
                          stroke="currentColor" stroke-width="1.5" fill="none"/>
                    <path d="M6 6h4M6 9h4" stroke="currentColor" stroke-width="1.5"/>
                </svg>
                <span>Copy</span>
            `;
            copyButton.setAttribute('aria-label', 'Copy code to clipboard');
            copyButton.addEventListener('click', () => this.copyToClipboard(code, copyButton));
            toolbar.appendChild(copyButton);

            return toolbar;
        }

        /**
         * Create language selection dropdown
         * @param {string} currentLanguage - Currently selected language
         * @param {Function} onChange - Callback when language changes
         * @returns {HTMLElement} Dropdown element
         */
        createLanguageSelector(currentLanguage, onChange) {
            const container = document.createElement('div');
            container.className = 'code-language-selector';

            const select = document.createElement('select');
            select.className = 'code-language-select';
            select.setAttribute('aria-label', 'Select programming language');

            SUPPORTED_LANGUAGES.forEach(lang => {
                const option = document.createElement('option');
                option.value = lang.value;
                option.textContent = lang.label;
                if (lang.value === currentLanguage) {
                    option.selected = true;
                }
                select.appendChild(option);
            });

            select.addEventListener('change', (e) => {
                if (onChange) {
                    onChange(e.target.value);
                }
            });

            container.appendChild(select);
            return container;
        }

        /**
         * Create inline code element
         * @param {string} code - Code content
         * @returns {HTMLElement} Inline code element
         */
        createInlineCode(code) {
            const codeElement = document.createElement('code');
            codeElement.className = 'inline-code';
            codeElement.textContent = code;
            return codeElement;
        }

        /**
         * Copy code to clipboard
         * @param {string} code - Code to copy
         * @param {HTMLElement} button - Copy button element
         */
        async copyToClipboard(code, button) {
            try {
                await navigator.clipboard.writeText(code);
                
                // Update button state
                const originalHTML = button.innerHTML;
                button.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <path d="M3 8l3 3 7-7" stroke="currentColor" stroke-width="2" fill="none"/>
                    </svg>
                    <span>Copied!</span>
                `;
                button.classList.add('copied');

                // Reset after 2 seconds
                setTimeout(() => {
                    button.innerHTML = originalHTML;
                    button.classList.remove('copied');
                }, 2000);
            } catch (error) {
                console.error('Failed to copy code:', error);
                
                // Fallback for older browsers
                this.fallbackCopyToClipboard(code, button);
            }
        }

        /**
         * Fallback copy method for older browsers
         * @param {string} code - Code to copy
         * @param {HTMLElement} button - Copy button element
         */
        fallbackCopyToClipboard(code, button) {
            const textarea = document.createElement('textarea');
            textarea.value = code;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            
            try {
                document.execCommand('copy');
                button.textContent = 'Copied!';
                setTimeout(() => {
                    button.textContent = 'Copy';
                }, 2000);
            } catch (error) {
                console.error('Fallback copy failed:', error);
            }
            
            document.body.removeChild(textarea);
        }

        /**
         * Get language information
         * @param {string} language - Language value or alias
         * @returns {Object} Language info
         */
        getLanguageInfo(language) {
            const lang = SUPPORTED_LANGUAGES.find(l => 
                l.value === language || l.aliases.includes(language)
            );
            return lang || SUPPORTED_LANGUAGES.find(l => l.value === 'plaintext');
        }

        /**
         * Normalize language name
         * @param {string} language - Language value or alias
         * @returns {string} Normalized language value
         */
        normalizeLanguage(language) {
            const langInfo = this.getLanguageInfo(language);
            return langInfo.value;
        }

        /**
         * Get all supported languages
         * @returns {Array} Array of supported languages
         */
        getSupportedLanguages() {
            return SUPPORTED_LANGUAGES;
        }

        /**
         * Highlight code element
         * @param {HTMLElement} element - Code element to highlight
         */
        highlightElement(element) {
            if (this.prismLoaded && element) {
                Prism.highlightElement(element);
            }
        }

        /**
         * Highlight all code blocks in container
         * @param {HTMLElement} container - Container element
         */
        highlightAll(container = document) {
            if (this.prismLoaded) {
                const codeBlocks = container.querySelectorAll('pre code');
                codeBlocks.forEach(block => {
                    Prism.highlightElement(block);
                });
            }
        }

        /**
         * Add line numbers to code block
         * @param {HTMLElement} pre - Pre element
         */
        addLineNumbers(pre) {
            if (!pre.classList.contains('line-numbers')) {
                pre.classList.add('line-numbers');
                
                // Re-highlight if Prism is loaded
                if (this.prismLoaded) {
                    const code = pre.querySelector('code');
                    if (code) {
                        Prism.highlightElement(code);
                    }
                }
            }
        }

        /**
         * Remove line numbers from code block
         * @param {HTMLElement} pre - Pre element
         */
        removeLineNumbers(pre) {
            if (pre.classList.contains('line-numbers')) {
                pre.classList.remove('line-numbers');
                
                // Remove line numbers span if exists
                const lineNumbers = pre.querySelector('.line-numbers-rows');
                if (lineNumbers) {
                    lineNumbers.remove();
                }
            }
        }

        /**
         * Update code block language
         * @param {HTMLElement} container - Code block container
         * @param {string} newLanguage - New language
         */
        updateLanguage(container, newLanguage) {
            const code = container.querySelector('code');
            if (!code) return;

            // Remove old language class
            const oldClass = Array.from(code.classList).find(c => c.startsWith('language-'));
            if (oldClass) {
                code.classList.remove(oldClass);
            }

            // Add new language class
            const normalizedLang = this.normalizeLanguage(newLanguage);
            code.classList.add(`language-${normalizedLang}`);
            container.setAttribute('data-language', normalizedLang);

            // Update language label
            const label = container.querySelector('.code-language-label');
            if (label) {
                const langInfo = this.getLanguageInfo(normalizedLang);
                label.textContent = langInfo.label;
            }

            // Re-highlight
            this.highlightElement(code);
        }

        /**
         * Format code with proper indentation
         * @param {string} code - Code to format
         * @param {string} language - Programming language
         * @returns {string} Formatted code
         */
        formatCode(code, language) {
            // Basic formatting - normalize line endings and trim
            let formatted = code.replace(/\r\n/g, '\n').trim();
            
            // Language-specific formatting could be added here
            // For now, just ensure consistent indentation
            const lines = formatted.split('\n');
            const minIndent = Math.min(
                ...lines
                    .filter(line => line.trim().length > 0)
                    .map(line => line.match(/^\s*/)[0].length)
            );
            
            if (minIndent > 0) {
                formatted = lines
                    .map(line => line.substring(minIndent))
                    .join('\n');
            }
            
            return formatted;
        }
    }

    // Export to global scope
    window.CodeEditor = CodeEditor;

    // Create global instance
    window.codeEditor = new CodeEditor();

    console.log('Code Editor module loaded');

})(window);
