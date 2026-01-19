/**
 * Advanced Editor System - Block Rendering System
 * 
 * This module implements the block rendering system for displaying
 * blocks in the editor. Uses vanilla JavaScript instead of React
 * for compatibility with the existing Flask application.
 */

(function(window) {
    'use strict';

    /**
     * BlockRenderer - Renders blocks to DOM elements
     */
    class BlockRenderer {
        constructor(editorController) {
            this.editorController = editorController;
            this.renderers = new Map();
            this.registerDefaultRenderers();
        }

        /**
         * Register default renderers for all block types
         */
        registerDefaultRenderers() {
            // Text blocks
            this.registerRenderer(window.BlockType.PARAGRAPH, this.renderParagraph.bind(this));
            this.registerRenderer(window.BlockType.HEADING, this.renderHeading.bind(this));
            this.registerRenderer(window.BlockType.QUOTE, this.renderQuote.bind(this));
            this.registerRenderer(window.BlockType.LIST_ITEM, this.renderListItem.bind(this));
            
            // Media blocks
            this.registerRenderer(window.BlockType.IMAGE, this.renderImage.bind(this));
            this.registerRenderer(window.BlockType.VIDEO, this.renderVideo.bind(this));
            this.registerRenderer(window.BlockType.AUDIO, this.renderAudio.bind(this));
            this.registerRenderer(window.BlockType.FILE, this.renderFile.bind(this));
            
            // Code blocks
            this.registerRenderer(window.BlockType.CODE_BLOCK, this.renderCodeBlock.bind(this));
            this.registerRenderer(window.BlockType.INLINE_CODE, this.renderInlineCode.bind(this));
            
            // Layout blocks
            this.registerRenderer(window.BlockType.COLUMNS, this.renderColumns.bind(this));
            this.registerRenderer(window.BlockType.DIVIDER, this.renderDivider.bind(this));
            this.registerRenderer(window.BlockType.SPACER, this.renderSpacer.bind(this));
            
            // Interactive blocks
            this.registerRenderer(window.BlockType.CALLOUT, this.renderCallout.bind(this));
            this.registerRenderer(window.BlockType.TABLE, this.renderTable.bind(this));
            this.registerRenderer(window.BlockType.EMBED, this.renderEmbed.bind(this));
        }

        /**
         * Register a custom renderer for a block type
         * @param {string} blockType - Block type
         * @param {Function} renderer - Renderer function
         */
        registerRenderer(blockType, renderer) {
            this.renderers.set(blockType, renderer);
        }

        /**
         * Render a block to a DOM element
         * @param {Block} block - Block to render
         * @returns {HTMLElement} Rendered DOM element
         */
        renderBlock(block) {
            const renderer = this.renderers.get(block.type);
            if (!renderer) {
                console.warn(`No renderer found for block type: ${block.type}`);
                return this.renderFallback(block);
            }

            try {
                const element = renderer(block);
                this.applyBlockProperties(element, block);
                element.setAttribute('data-block-id', block.id);
                element.setAttribute('data-block-type', block.type);
                element.classList.add('editor-block');
                
                return element;
            } catch (error) {
                console.error(`Error rendering block ${block.id}:`, error);
                return this.renderError(block, error);
            }
        }

        /**
         * Apply block properties to element
         * @param {HTMLElement} element - DOM element
         * @param {Block} block - Block with properties
         */
        applyBlockProperties(element, block) {
            const props = block.properties;
            
            if (props.alignment) {
                element.style.textAlign = props.alignment;
            }
            
            if (props.color) {
                element.style.color = props.color;
            }
            
            if (props.backgroundColor) {
                element.style.backgroundColor = props.backgroundColor;
            }
            
            if (props.fontSize) {
                element.style.fontSize = `${props.fontSize}px`;
            }
            
            if (props.fontFamily) {
                element.style.fontFamily = props.fontFamily;
            }
            
            if (props.indentation) {
                element.style.marginLeft = `${props.indentation * 20}px`;
            }
            
            if (props.padding) {
                element.style.padding = props.padding;
            }
            
            if (props.margin) {
                element.style.margin = props.margin;
            }
            
            if (props.borderColor) {
                element.style.borderColor = props.borderColor;
            }
            
            if (props.borderWidth) {
                element.style.borderWidth = props.borderWidth;
            }
            
            if (props.borderRadius) {
                element.style.borderRadius = props.borderRadius;
            }
        }

        /**
         * Render paragraph block
         */
        renderParagraph(block) {
            const p = document.createElement('p');
            p.className = 'block-paragraph';
            
            if (block.content.html) {
                p.innerHTML = block.content.html;
            } else {
                p.textContent = block.content.text || '';
            }
            
            return p;
        }

        /**
         * Render heading block
         */
        renderHeading(block) {
            const level = block.content.data.level || 1;
            const h = document.createElement(`h${level}`);
            h.className = 'block-heading';
            
            if (block.content.html) {
                h.innerHTML = block.content.html;
            } else {
                h.textContent = block.content.text || '';
            }
            
            return h;
        }

        /**
         * Render quote block
         */
        renderQuote(block) {
            const blockquote = document.createElement('blockquote');
            blockquote.className = 'block-quote';
            
            if (block.content.html) {
                blockquote.innerHTML = block.content.html;
            } else {
                blockquote.textContent = block.content.text || '';
            }
            
            if (block.content.data.author) {
                const cite = document.createElement('cite');
                cite.textContent = block.content.data.author;
                blockquote.appendChild(cite);
            }
            
            return blockquote;
        }

        /**
         * Render list item block
         */
        renderListItem(block) {
            const li = document.createElement('li');
            li.className = 'block-list-item';
            
            if (block.content.data.checked !== undefined) {
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.checked = block.content.data.checked;
                li.appendChild(checkbox);
            }
            
            const span = document.createElement('span');
            if (block.content.html) {
                span.innerHTML = block.content.html;
            } else {
                span.textContent = block.content.text || '';
            }
            li.appendChild(span);
            
            return li;
        }

        /**
         * Render image block
         */
        renderImage(block) {
            const figure = document.createElement('figure');
            figure.className = 'block-image';
            
            const img = document.createElement('img');
            img.src = block.content.data.url || '';
            img.alt = block.content.data.alt || '';
            
            if (block.content.data.width) {
                img.width = block.content.data.width;
            }
            if (block.content.data.height) {
                img.height = block.content.data.height;
            }
            
            figure.appendChild(img);
            
            if (block.content.data.caption) {
                const figcaption = document.createElement('figcaption');
                figcaption.textContent = block.content.data.caption;
                figure.appendChild(figcaption);
            }
            
            return figure;
        }

        /**
         * Render video block
         */
        renderVideo(block) {
            const container = document.createElement('div');
            container.className = 'block-video';
            
            const url = block.content.data.url || '';
            const provider = block.content.data.provider || 'direct';
            
            if (provider === 'youtube') {
                const iframe = document.createElement('iframe');
                iframe.src = url;
                iframe.setAttribute('allowfullscreen', '');
                container.appendChild(iframe);
            } else if (provider === 'vimeo') {
                const iframe = document.createElement('iframe');
                iframe.src = url;
                iframe.setAttribute('allowfullscreen', '');
                container.appendChild(iframe);
            } else {
                const video = document.createElement('video');
                video.src = url;
                video.controls = true;
                container.appendChild(video);
            }
            
            return container;
        }

        /**
         * Render audio block
         */
        renderAudio(block) {
            const container = document.createElement('div');
            container.className = 'block-audio';
            
            const audio = document.createElement('audio');
            audio.src = block.content.data.url || '';
            audio.controls = true;
            
            container.appendChild(audio);
            
            if (block.content.data.title) {
                const title = document.createElement('div');
                title.className = 'audio-title';
                title.textContent = block.content.data.title;
                container.insertBefore(title, audio);
            }
            
            return container;
        }

        /**
         * Render file block
         */
        renderFile(block) {
            const container = document.createElement('div');
            container.className = 'block-file';
            
            const link = document.createElement('a');
            link.href = block.content.data.url || '#';
            link.download = block.content.data.filename || 'download';
            link.textContent = block.content.data.filename || 'Download File';
            
            container.appendChild(link);
            
            if (block.content.data.size) {
                const size = document.createElement('span');
                size.className = 'file-size';
                size.textContent = ` (${this.formatFileSize(block.content.data.size)})`;
                container.appendChild(size);
            }
            
            return container;
        }

        /**
         * Render code block
         */
        renderCodeBlock(block) {
            // Use CodeEditor if available
            if (window.codeEditor) {
                const code = block.content.text || '';
                const language = block.content.data.language || 'plaintext';
                const lineNumbers = block.content.data.lineNumbers !== false; // Default true
                
                return window.codeEditor.createCodeBlock(code, language, {
                    lineNumbers: lineNumbers,
                    copyButton: true
                });
            }
            
            // Fallback to basic rendering
            const pre = document.createElement('pre');
            pre.className = 'block-code';
            
            const code = document.createElement('code');
            const language = block.content.data.language || 'plaintext';
            code.className = `language-${language}`;
            code.textContent = block.content.text || '';
            
            pre.appendChild(code);
            
            if (block.content.data.lineNumbers) {
                pre.classList.add('line-numbers');
            }
            
            return pre;
        }

        /**
         * Render inline code
         */
        renderInlineCode(block) {
            // Use CodeEditor if available
            if (window.codeEditor) {
                return window.codeEditor.createInlineCode(block.content.text || '');
            }
            
            // Fallback to basic rendering
            const code = document.createElement('code');
            code.className = 'block-inline-code inline-code';
            code.textContent = block.content.text || '';
            
            return code;
        }

        /**
         * Render columns block
         */
        renderColumns(block) {
            const container = document.createElement('div');
            container.className = 'block-columns';
            
            const columnCount = block.content.data.columnCount || 2;
            container.style.gridTemplateColumns = `repeat(${columnCount}, 1fr)`;
            
            if (block.children && block.children.length > 0) {
                block.children.forEach(child => {
                    const column = document.createElement('div');
                    column.className = 'column';
                    column.appendChild(this.renderBlock(child));
                    container.appendChild(column);
                });
            }
            
            return container;
        }

        /**
         * Render divider block
         */
        renderDivider(block) {
            const hr = document.createElement('hr');
            hr.className = 'block-divider';
            
            if (block.content.data.style) {
                hr.classList.add(`divider-${block.content.data.style}`);
            }
            
            return hr;
        }

        /**
         * Render spacer block
         */
        renderSpacer(block) {
            const div = document.createElement('div');
            div.className = 'block-spacer';
            
            const height = block.content.data.height || 20;
            div.style.height = `${height}px`;
            
            return div;
        }

        /**
         * Render callout block
         */
        renderCallout(block) {
            const div = document.createElement('div');
            div.className = 'block-callout';
            
            const style = block.content.data.style || 'info';
            div.classList.add(`callout-${style}`);
            
            if (block.content.data.title) {
                const title = document.createElement('div');
                title.className = 'callout-title';
                title.textContent = block.content.data.title;
                div.appendChild(title);
            }
            
            const content = document.createElement('div');
            content.className = 'callout-content';
            if (block.content.html) {
                content.innerHTML = block.content.html;
            } else {
                content.textContent = block.content.text || '';
            }
            div.appendChild(content);
            
            return div;
        }

        /**
         * Render table block
         */
        renderTable(block) {
            const table = document.createElement('table');
            table.className = 'block-table';
            
            const rows = block.content.data.rows || 3;
            const cols = block.content.data.cols || 3;
            const hasHeaders = block.content.data.headers !== false;
            
            if (hasHeaders) {
                const thead = document.createElement('thead');
                const headerRow = document.createElement('tr');
                for (let i = 0; i < cols; i++) {
                    const th = document.createElement('th');
                    th.textContent = `Header ${i + 1}`;
                    headerRow.appendChild(th);
                }
                thead.appendChild(headerRow);
                table.appendChild(thead);
            }
            
            const tbody = document.createElement('tbody');
            for (let i = 0; i < rows; i++) {
                const tr = document.createElement('tr');
                for (let j = 0; j < cols; j++) {
                    const td = document.createElement('td');
                    td.textContent = '';
                    tr.appendChild(td);
                }
                tbody.appendChild(tr);
            }
            table.appendChild(tbody);
            
            return table;
        }

        /**
         * Render embed block
         */
        renderEmbed(block) {
            const container = document.createElement('div');
            container.className = 'block-embed';
            
            const iframe = document.createElement('iframe');
            iframe.src = block.content.data.url || '';
            
            if (block.content.data.width) {
                iframe.width = block.content.data.width;
            }
            if (block.content.data.height) {
                iframe.height = block.content.data.height;
            }
            
            container.appendChild(iframe);
            
            return container;
        }

        /**
         * Render fallback for unknown block types
         */
        renderFallback(block) {
            const div = document.createElement('div');
            div.className = 'block-fallback';
            div.textContent = `Unknown block type: ${block.type}`;
            
            return div;
        }

        /**
         * Render error block
         */
        renderError(block, error) {
            const div = document.createElement('div');
            div.className = 'block-error';
            div.textContent = `Error rendering block: ${error.message}`;
            
            return div;
        }

        /**
         * Format file size for display
         */
        formatFileSize(bytes) {
            if (bytes < 1024) return `${bytes} B`;
            if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
            if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
            return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
        }

        /**
         * Render multiple blocks to a container
         * @param {Block[]} blocks - Array of blocks
         * @param {HTMLElement} container - Container element
         */
        renderBlocks(blocks, container) {
            container.innerHTML = '';
            
            blocks.forEach(block => {
                const element = this.renderBlock(block);
                container.appendChild(element);
            });
        }

        /**
         * Update a rendered block
         * @param {Block} block - Updated block
         * @param {HTMLElement} container - Container element
         */
        updateBlock(block, container) {
            const existingElement = container.querySelector(`[data-block-id="${block.id}"]`);
            if (!existingElement) {
                console.warn(`Block element not found: ${block.id}`);
                return;
            }
            
            const newElement = this.renderBlock(block);
            existingElement.replaceWith(newElement);
        }

        /**
         * Remove a rendered block
         * @param {string} blockId - Block ID
         * @param {HTMLElement} container - Container element
         */
        removeBlock(blockId, container) {
            const element = container.querySelector(`[data-block-id="${blockId}"]`);
            if (element) {
                element.remove();
            }
        }
    }

    // Export to global scope
    window.BlockRenderer = BlockRenderer;

})(window);
