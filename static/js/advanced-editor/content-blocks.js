/**
 * Advanced Editor System - Modular Content Blocks
 * 
 * This module implements reusable content blocks for structured content creation:
 * - Callout blocks with multiple styles (info, warning, success, error, note)
 * - Column layouts (2, 3, 4 columns)
 * - Divider blocks with various styles
 * - Table creation and editing
 * - Nested list support
 * 
 * Validates Property 2: Block Creation and Styling
 * Validates Property 11: Block Manipulation Operations
 */

(function(window) {
    'use strict';

    /**
     * Content Blocks Manager
     * Handles creation and management of modular content blocks
     */
    class ContentBlocks {
        constructor(blockFactory) {
            this.blockFactory = blockFactory || window.BlockFactory;
            
            if (!this.blockFactory) {
                console.error('BlockFactory not available');
            }
        }

        /**
         * Create a callout block
         * @param {string} style - Callout style (info, warning, success, error, note)
         * @param {string} content - Callout content
         * @param {Object} options - Additional options
         * @returns {Block} Callout block
         */
        createCallout(style = 'info', content = '', options = {}) {
            const {
                title = '',
                icon = this.getCalloutIcon(style)
            } = options;

            return this.blockFactory.createBlock(window.BlockType.CALLOUT, {
                content: {
                    text: content,
                    html: content,
                    data: {
                        style: style,
                        title: title,
                        icon: icon
                    }
                },
                properties: {
                    backgroundColor: this.getCalloutBackgroundColor(style),
                    borderColor: this.getCalloutBorderColor(style)
                }
            });
        }

        /**
         * Get default icon for callout style
         * @param {string} style - Callout style
         * @returns {string} Icon emoji or character
         */
        getCalloutIcon(style) {
            const icons = {
                info: 'ℹ️',
                warning: '⚠️',
                success: '✅',
                error: '❌',
                note: '📝'
            };
            return icons[style] || icons.info;
        }

        /**
         * Get background color for callout style
         * @param {string} style - Callout style
         * @returns {string} Background color
         */
        getCalloutBackgroundColor(style) {
            const colors = {
                info: '#e3f2fd',
                warning: '#fff3e0',
                success: '#e8f5e9',
                error: '#ffebee',
                note: '#f5f5f5'
            };
            return colors[style] || colors.info;
        }

        /**
         * Get border color for callout style
         * @param {string} style - Callout style
         * @returns {string} Border color
         */
        getCalloutBorderColor(style) {
            const colors = {
                info: '#2196F3',
                warning: '#ff9800',
                success: '#4caf50',
                error: '#f44336',
                note: '#9e9e9e'
            };
            return colors[style] || colors.info;
        }

        /**
         * Create a column layout block
         * @param {number} columnCount - Number of columns (2, 3, or 4)
         * @param {Array} children - Child blocks for each column
         * @param {Object} options - Additional options
         * @returns {Block} Column layout block
         */
        createColumns(columnCount = 2, children = [], options = {}) {
            const {
                gap = '16px'
            } = options;

            // Validate column count
            if (columnCount < 2 || columnCount > 4) {
                console.warn('Column count must be between 2 and 4, defaulting to 2');
                columnCount = 2;
            }

            // Ensure we have the right number of children
            while (children.length < columnCount) {
                children.push(this.blockFactory.createBlock(window.BlockType.PARAGRAPH, {
                    content: { text: '' }
                }));
            }

            return this.blockFactory.createBlock(window.BlockType.COLUMNS, {
                content: {
                    data: {
                        columnCount: columnCount,
                        gap: gap
                    }
                },
                children: children.slice(0, columnCount)
            });
        }

        /**
         * Create a divider block
         * @param {string} style - Divider style (solid, dashed, dotted, double)
         * @param {Object} options - Additional options
         * @returns {Block} Divider block
         */
        createDivider(style = 'solid', options = {}) {
            const {
                thickness = '1px',
                color = '#e0e0e0',
                margin = '24px 0'
            } = options;

            return this.blockFactory.createBlock(window.BlockType.DIVIDER, {
                content: {
                    data: {
                        style: style,
                        thickness: thickness
                    }
                },
                properties: {
                    borderColor: color,
                    margin: margin
                }
            });
        }

        /**
         * Create a table block
         * @param {number} rows - Number of rows
         * @param {number} cols - Number of columns
         * @param {Object} options - Additional options
         * @returns {Block} Table block
         */
        createTable(rows = 3, cols = 3, options = {}) {
            const {
                headers = true,
                cells = null
            } = options;

            // Validate dimensions
            if (rows < 1 || rows > 100) {
                console.warn('Row count must be between 1 and 100, defaulting to 3');
                rows = 3;
            }
            if (cols < 1 || cols > 20) {
                console.warn('Column count must be between 1 and 20, defaulting to 3');
                cols = 3;
            }

            // Initialize cells if not provided
            const tableCells = cells || this.initializeTableCells(rows, cols, headers);

            return this.blockFactory.createBlock(window.BlockType.TABLE, {
                content: {
                    data: {
                        rows: rows,
                        cols: cols,
                        headers: headers,
                        cells: tableCells
                    }
                },
                properties: {
                    borderColor: '#e0e0e0',
                    borderWidth: '1px'
                }
            });
        }

        /**
         * Initialize table cells with default content
         * @param {number} rows - Number of rows
         * @param {number} cols - Number of columns
         * @param {boolean} headers - Whether to include headers
         * @returns {Array} 2D array of cell content
         */
        initializeTableCells(rows, cols, headers) {
            const cells = [];
            
            for (let i = 0; i < rows; i++) {
                const row = [];
                for (let j = 0; j < cols; j++) {
                    if (i === 0 && headers) {
                        row.push(`Header ${j + 1}`);
                    } else {
                        row.push('');
                    }
                }
                cells.push(row);
            }
            
            return cells;
        }

        /**
         * Update table cell content
         * @param {Block} tableBlock - Table block
         * @param {number} row - Row index
         * @param {number} col - Column index
         * @param {string} content - New cell content
         * @returns {Block} Updated table block
         */
        updateTableCell(tableBlock, row, col, content) {
            if (!tableBlock || tableBlock.type !== window.BlockType.TABLE) {
                console.error('Invalid table block');
                return tableBlock;
            }

            const cells = tableBlock.content.data.cells;
            if (row >= 0 && row < cells.length && col >= 0 && col < cells[row].length) {
                cells[row][col] = content;
                tableBlock.metadata.updatedAt = new Date();
                tableBlock.metadata.version += 1;
            }

            return tableBlock;
        }

        /**
         * Add row to table
         * @param {Block} tableBlock - Table block
         * @param {number} position - Position to insert row (optional)
         * @returns {Block} Updated table block
         */
        addTableRow(tableBlock, position = null) {
            if (!tableBlock || tableBlock.type !== window.BlockType.TABLE) {
                console.error('Invalid table block');
                return tableBlock;
            }

            const cols = tableBlock.content.data.cols;
            const newRow = new Array(cols).fill('');
            
            if (position !== null && position >= 0 && position <= tableBlock.content.data.rows) {
                tableBlock.content.data.cells.splice(position, 0, newRow);
            } else {
                tableBlock.content.data.cells.push(newRow);
            }
            
            tableBlock.content.data.rows += 1;
            tableBlock.metadata.updatedAt = new Date();
            tableBlock.metadata.version += 1;

            return tableBlock;
        }

        /**
         * Add column to table
         * @param {Block} tableBlock - Table block
         * @param {number} position - Position to insert column (optional)
         * @returns {Block} Updated table block
         */
        addTableColumn(tableBlock, position = null) {
            if (!tableBlock || tableBlock.type !== window.BlockType.TABLE) {
                console.error('Invalid table block');
                return tableBlock;
            }

            const cells = tableBlock.content.data.cells;
            const insertPos = position !== null && position >= 0 && position <= tableBlock.content.data.cols
                ? position
                : tableBlock.content.data.cols;

            cells.forEach(row => {
                row.splice(insertPos, 0, '');
            });
            
            tableBlock.content.data.cols += 1;
            tableBlock.metadata.updatedAt = new Date();
            tableBlock.metadata.version += 1;

            return tableBlock;
        }

        /**
         * Delete row from table
         * @param {Block} tableBlock - Table block
         * @param {number} rowIndex - Row index to delete
         * @returns {Block} Updated table block
         */
        deleteTableRow(tableBlock, rowIndex) {
            if (!tableBlock || tableBlock.type !== window.BlockType.TABLE) {
                console.error('Invalid table block');
                return tableBlock;
            }

            if (tableBlock.content.data.rows <= 1) {
                console.warn('Cannot delete last row');
                return tableBlock;
            }

            if (rowIndex >= 0 && rowIndex < tableBlock.content.data.rows) {
                tableBlock.content.data.cells.splice(rowIndex, 1);
                tableBlock.content.data.rows -= 1;
                tableBlock.metadata.updatedAt = new Date();
                tableBlock.metadata.version += 1;
            }

            return tableBlock;
        }

        /**
         * Delete column from table
         * @param {Block} tableBlock - Table block
         * @param {number} colIndex - Column index to delete
         * @returns {Block} Updated table block
         */
        deleteTableColumn(tableBlock, colIndex) {
            if (!tableBlock || tableBlock.type !== window.BlockType.TABLE) {
                console.error('Invalid table block');
                return tableBlock;
            }

            if (tableBlock.content.data.cols <= 1) {
                console.warn('Cannot delete last column');
                return tableBlock;
            }

            if (colIndex >= 0 && colIndex < tableBlock.content.data.cols) {
                tableBlock.content.data.cells.forEach(row => {
                    row.splice(colIndex, 1);
                });
                tableBlock.content.data.cols -= 1;
                tableBlock.metadata.updatedAt = new Date();
                tableBlock.metadata.version += 1;
            }

            return tableBlock;
        }

        /**
         * Create a nested list item
         * @param {string} text - List item text
         * @param {Object} options - Additional options
         * @returns {Block} List item block
         */
        createListItem(text = '', options = {}) {
            const {
                ordered = false,
                checked = undefined,
                indentation = 0,
                children = []
            } = options;

            return this.blockFactory.createBlock(window.BlockType.LIST_ITEM, {
                content: {
                    text: text,
                    html: text,
                    data: {
                        ordered: ordered,
                        checked: checked
                    }
                },
                properties: {
                    indentation: indentation
                },
                children: children
            });
        }

        /**
         * Create a nested list structure
         * @param {Array} items - Array of list items with text and optional children
         * @param {boolean} ordered - Whether list is ordered
         * @returns {Array} Array of list item blocks
         */
        createNestedList(items, ordered = false) {
            return items.map(item => {
                const children = item.children
                    ? this.createNestedList(item.children, ordered)
                    : [];

                return this.createListItem(item.text, {
                    ordered: ordered,
                    checked: item.checked,
                    indentation: item.indentation || 0,
                    children: children
                });
            });
        }

        /**
         * Indent list item
         * @param {Block} listItem - List item block
         * @returns {Block} Updated list item
         */
        indentListItem(listItem) {
            if (!listItem || listItem.type !== window.BlockType.LIST_ITEM) {
                console.error('Invalid list item block');
                return listItem;
            }

            const currentIndent = listItem.properties.indentation || 0;
            if (currentIndent < 5) { // Max 5 levels
                listItem.properties.indentation = currentIndent + 1;
                listItem.metadata.updatedAt = new Date();
                listItem.metadata.version += 1;
            }

            return listItem;
        }

        /**
         * Outdent list item
         * @param {Block} listItem - List item block
         * @returns {Block} Updated list item
         */
        outdentListItem(listItem) {
            if (!listItem || listItem.type !== window.BlockType.LIST_ITEM) {
                console.error('Invalid list item block');
                return listItem;
            }

            const currentIndent = listItem.properties.indentation || 0;
            if (currentIndent > 0) {
                listItem.properties.indentation = currentIndent - 1;
                listItem.metadata.updatedAt = new Date();
                listItem.metadata.version += 1;
            }

            return listItem;
        }

        /**
         * Create a spacer block
         * @param {number} height - Height in pixels
         * @returns {Block} Spacer block
         */
        createSpacer(height = 20) {
            return this.blockFactory.createBlock(window.BlockType.SPACER, {
                content: {
                    data: {
                        height: height
                    }
                }
            });
        }

        /**
         * Get all available block types for insertion menu
         * @returns {Array} Array of block type definitions
         */
        getAvailableBlocks() {
            return [
                {
                    type: window.BlockType.PARAGRAPH,
                    label: 'Paragraph',
                    icon: '¶',
                    description: 'Basic text paragraph',
                    category: 'text'
                },
                {
                    type: window.BlockType.HEADING,
                    label: 'Heading',
                    icon: 'H',
                    description: 'Section heading',
                    category: 'text'
                },
                {
                    type: window.BlockType.QUOTE,
                    label: 'Quote',
                    icon: '"',
                    description: 'Blockquote',
                    category: 'text'
                },
                {
                    type: window.BlockType.LIST_ITEM,
                    label: 'List',
                    icon: '•',
                    description: 'Bulleted or numbered list',
                    category: 'text'
                },
                {
                    type: window.BlockType.CALLOUT,
                    label: 'Callout',
                    icon: 'ℹ️',
                    description: 'Highlighted callout box',
                    category: 'layout'
                },
                {
                    type: window.BlockType.COLUMNS,
                    label: 'Columns',
                    icon: '⫴',
                    description: 'Multi-column layout',
                    category: 'layout'
                },
                {
                    type: window.BlockType.DIVIDER,
                    label: 'Divider',
                    icon: '—',
                    description: 'Horizontal divider',
                    category: 'layout'
                },
                {
                    type: window.BlockType.SPACER,
                    label: 'Spacer',
                    icon: '⬍',
                    description: 'Vertical spacing',
                    category: 'layout'
                },
                {
                    type: window.BlockType.TABLE,
                    label: 'Table',
                    icon: '⊞',
                    description: 'Data table',
                    category: 'layout'
                },
                {
                    type: window.BlockType.CODE_BLOCK,
                    label: 'Code',
                    icon: '</>',
                    description: 'Code block with syntax highlighting',
                    category: 'code'
                },
                {
                    type: window.BlockType.IMAGE,
                    label: 'Image',
                    icon: '🖼️',
                    description: 'Image with caption',
                    category: 'media'
                },
                {
                    type: window.BlockType.VIDEO,
                    label: 'Video',
                    icon: '🎥',
                    description: 'Video embed',
                    category: 'media'
                },
                {
                    type: window.BlockType.AUDIO,
                    label: 'Audio',
                    icon: '🔊',
                    description: 'Audio player',
                    category: 'media'
                },
                {
                    type: window.BlockType.FILE,
                    label: 'File',
                    icon: '📎',
                    description: 'File attachment',
                    category: 'media'
                }
            ];
        }

        /**
         * Search available blocks by query
         * @param {string} query - Search query
         * @returns {Array} Filtered array of block types
         */
        searchBlocks(query) {
            if (!query || query.trim() === '') {
                return this.getAvailableBlocks();
            }

            const lowerQuery = query.toLowerCase();
            return this.getAvailableBlocks().filter(block => 
                block.label.toLowerCase().includes(lowerQuery) ||
                block.description.toLowerCase().includes(lowerQuery) ||
                block.category.toLowerCase().includes(lowerQuery)
            );
        }
    }

    // Export to global scope
    window.ContentBlocks = ContentBlocks;

    // Create global instance
    if (window.BlockFactory) {
        window.contentBlocks = new ContentBlocks(window.BlockFactory);
        console.log('Content Blocks module loaded');
    } else {
        console.warn('BlockFactory not available, ContentBlocks will be initialized later');
    }

})(window);
