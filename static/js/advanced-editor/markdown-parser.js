/**
 * Advanced Editor System - Markdown Parser and Serializer
 * 
 * This module implements bidirectional conversion between Markdown and
 * the block-based editor format.
 */

(function(window) {
    'use strict';

    /**
     * MarkdownParser - Converts Markdown to blocks
     */
    class MarkdownParser {
        constructor() {
            this.blockParsers = this.initializeBlockParsers();
        }

        /**
         * Initialize block parsers for different Markdown elements
         */
        initializeBlockParsers() {
            return [
                { pattern: /^(#{1,6})\s+(.+)$/, parser: this.parseHeading.bind(this) },
                { pattern: /^>\s+(.+)$/, parser: this.parseQuote.bind(this) },
                { pattern: /^```(\w+)?$/, parser: this.parseCodeBlock.bind(this) },
                { pattern: /^[-*+]\s+(.+)$/, parser: this.parseListItem.bind(this) },
                { pattern: /^\d+\.\s+(.+)$/, parser: this.parseOrderedListItem.bind(this) },
                { pattern: /^!\[([^\]]*)\]\(([^)]+)\)$/, parser: this.parseImage.bind(this) },
                { pattern: /^\[([^\]]+)\]\(([^)]+)\)$/, parser: this.parseLink.bind(this) },
                { pattern: /^---+$/, parser: this.parseDivider.bind(this) },
                { pattern: /^(.+)$/, parser: this.parseParagraph.bind(this) }
            ];
        }

        /**
         * Parse Markdown text into blocks
         * @param {string} markdown - Markdown text
         * @returns {Block[]} Array of blocks
         */
        parse(markdown) {
            if (!markdown || markdown.trim() === '') {
                return [];
            }

            const lines = markdown.split('\n');
            const blocks = [];
            let i = 0;

            while (i < lines.length) {
                const line = lines[i];
                
                // Skip empty lines
                if (line.trim() === '') {
                    i++;
                    continue;
                }

                // Try to parse with each parser
                let parsed = false;
                for (const { pattern, parser } of this.blockParsers) {
                    const match = line.match(pattern);
                    if (match) {
                        const result = parser(match, lines, i);
                        if (result) {
                            blocks.push(result.block);
                            i += result.linesConsumed;
                            parsed = true;
                            break;
                        }
                    }
                }

                if (!parsed) {
                    i++;
                }
            }

            return blocks;
        }

        /**
         * Parse heading
         */
        parseHeading(match, lines, index) {
            const hashes = match[1];
            const level = hashes.length;
            const text = match[2].trim();

            const block = window.BlockFactory.createBlock(window.BlockType.HEADING, {
                content: {
                    text: text,
                    html: this.parseInlineMarkdown(text),
                    data: { level: level }
                }
            });

            return { block, linesConsumed: 1 };
        }

        /**
         * Parse quote
         */
        parseQuote(match, lines, index) {
            const text = match[1].trim();
            let fullText = text;
            let linesConsumed = 1;

            // Check for multi-line quotes
            for (let i = index + 1; i < lines.length; i++) {
                const nextLine = lines[i];
                if (nextLine.match(/^>\s+(.+)$/)) {
                    fullText += '\n' + nextLine.replace(/^>\s+/, '');
                    linesConsumed++;
                } else {
                    break;
                }
            }

            const block = window.BlockFactory.createBlock(window.BlockType.QUOTE, {
                content: {
                    text: fullText,
                    html: this.parseInlineMarkdown(fullText)
                }
            });

            return { block, linesConsumed };
        }

        /**
         * Parse code block
         */
        parseCodeBlock(match, lines, index) {
            const language = match[1] || 'plaintext';
            let code = '';
            let linesConsumed = 1;

            // Find the closing ```
            for (let i = index + 1; i < lines.length; i++) {
                if (lines[i].trim() === '```') {
                    linesConsumed = i - index + 1;
                    break;
                }
                code += (code ? '\n' : '') + lines[i];
            }

            const block = window.BlockFactory.createBlock(window.BlockType.CODE_BLOCK, {
                content: {
                    text: code,
                    data: {
                        language: language,
                        lineNumbers: true
                    }
                }
            });

            return { block, linesConsumed };
        }

        /**
         * Parse ordered list item
         */
        parseOrderedListItem(match, lines, index) {
            const text = match[1].trim();

            const block = window.BlockFactory.createBlock(window.BlockType.LIST_ITEM, {
                content: {
                    text: text,
                    html: this.parseInlineMarkdown(text),
                    data: {
                        ordered: true
                    }
                }
            });

            return { block, linesConsumed: 1 };
        }

        /**
         * Parse list item
         */
        parseListItem(match, lines, index) {
            const text = match[1].trim();
            const isOrdered = lines[index].match(/^\d+\.\s+/);

            const block = window.BlockFactory.createBlock(window.BlockType.LIST_ITEM, {
                content: {
                    text: text,
                    html: this.parseInlineMarkdown(text),
                    data: {
                        ordered: !!isOrdered
                    }
                }
            });

            return { block, linesConsumed: 1 };
        }

        /**
         * Parse image
         */
        parseImage(match, lines, index) {
            const alt = match[1];
            const url = match[2];

            const block = window.BlockFactory.createBlock(window.BlockType.IMAGE, {
                content: {
                    data: {
                        url: url,
                        alt: alt
                    }
                }
            });

            return { block, linesConsumed: 1 };
        }

        /**
         * Parse link (convert to paragraph with link)
         */
        parseLink(match, lines, index) {
            const text = match[1];
            const url = match[2];
            const html = `<a href="${url}">${text}</a>`;

            const block = window.BlockFactory.createBlock(window.BlockType.PARAGRAPH, {
                content: {
                    text: text,
                    html: html
                }
            });

            return { block, linesConsumed: 1 };
        }

        /**
         * Parse divider
         */
        parseDivider(match, lines, index) {
            const block = window.BlockFactory.createBlock(window.BlockType.DIVIDER, {
                content: { data: {} }
            });

            return { block, linesConsumed: 1 };
        }

        /**
         * Parse paragraph
         */
        parseParagraph(match, lines, index) {
            const text = match[1].trim();

            const block = window.BlockFactory.createBlock(window.BlockType.PARAGRAPH, {
                content: {
                    text: text,
                    html: this.parseInlineMarkdown(text)
                }
            });

            return { block, linesConsumed: 1 };
        }

        /**
         * Parse inline Markdown (bold, italic, code, etc.)
         */
        parseInlineMarkdown(text) {
            if (!text) return '';
            
            let html = text;

            // Inline code first (to protect it from other replacements)
            const codeBlocks = [];
            html = html.replace(/`([^`]+)`/g, (match, code) => {
                codeBlocks.push(code);
                return `__CODE_${codeBlocks.length - 1}__`;
            });

            // Bold: **text** or __text__ (must be done before italic)
            html = html.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
            html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');

            // Strikethrough: ~~text~~
            html = html.replace(/~~([^~]+)~~/g, '<del>$1</del>');

            // Italic: *text* or _text_ (single, not part of bold/code markers)
            html = html.replace(/\*([^\*]+)\*/g, '<em>$1</em>');
            html = html.replace(/_([^_]+)_/g, '<em>$1</em>');

            // Links: [text](url)
            html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');

            // Restore code blocks
            codeBlocks.forEach((code, index) => {
                html = html.replace(`__CODE_${index}__`, `<code>${code}</code>`);
            });

            return html;
        }
    }

    /**
     * MarkdownSerializer - Converts blocks to Markdown
     */
    class MarkdownSerializer {
        constructor() {
            this.serializers = this.initializeSerializers();
        }

        /**
         * Initialize serializers for different block types
         */
        initializeSerializers() {
            const serializers = new Map();
            
            serializers.set(window.BlockType.PARAGRAPH, this.serializeParagraph.bind(this));
            serializers.set(window.BlockType.HEADING, this.serializeHeading.bind(this));
            serializers.set(window.BlockType.QUOTE, this.serializeQuote.bind(this));
            serializers.set(window.BlockType.LIST_ITEM, this.serializeListItem.bind(this));
            serializers.set(window.BlockType.CODE_BLOCK, this.serializeCodeBlock.bind(this));
            serializers.set(window.BlockType.IMAGE, this.serializeImage.bind(this));
            serializers.set(window.BlockType.DIVIDER, this.serializeDivider.bind(this));
            serializers.set(window.BlockType.CALLOUT, this.serializeCallout.bind(this));
            
            return serializers;
        }

        /**
         * Serialize blocks to Markdown
         * @param {Block[]} blocks - Array of blocks
         * @returns {string} Markdown text
         */
        serialize(blocks) {
            if (!blocks || blocks.length === 0) {
                return '';
            }

            const markdown = blocks.map(block => {
                const serializer = this.serializers.get(block.type);
                if (serializer) {
                    return serializer(block);
                } else {
                    // Fallback for unsupported block types
                    return this.serializeFallback(block);
                }
            }).filter(Boolean).join('\n\n');

            return markdown;
        }

        /**
         * Serialize paragraph
         */
        serializeParagraph(block) {
            return this.serializeInlineMarkdown(block.content.text || '');
        }

        /**
         * Serialize heading
         */
        serializeHeading(block) {
            const level = block.content.data.level || 1;
            const hashes = '#'.repeat(level);
            const text = this.serializeInlineMarkdown(block.content.text || '');
            return `${hashes} ${text}`;
        }

        /**
         * Serialize quote
         */
        serializeQuote(block) {
            const text = this.serializeInlineMarkdown(block.content.text || '');
            const lines = text.split('\n');
            return lines.map(line => `> ${line}`).join('\n');
        }

        /**
         * Serialize list item
         */
        serializeListItem(block) {
            const text = this.serializeInlineMarkdown(block.content.text || '');
            const marker = block.content.data.ordered ? '1.' : '-';
            return `${marker} ${text}`;
        }

        /**
         * Serialize code block
         */
        serializeCodeBlock(block) {
            const language = block.content.data.language || '';
            const code = block.content.text || '';
            return `\`\`\`${language}\n${code}\n\`\`\``;
        }

        /**
         * Serialize image
         */
        serializeImage(block) {
            const alt = block.content.data.alt || '';
            const url = block.content.data.url || '';
            return `![${alt}](${url})`;
        }

        /**
         * Serialize divider
         */
        serializeDivider(block) {
            return '---';
        }

        /**
         * Serialize callout
         */
        serializeCallout(block) {
            const style = block.content.data.style || 'info';
            const text = this.serializeInlineMarkdown(block.content.text || '');
            return `> **${style.toUpperCase()}**: ${text}`;
        }

        /**
         * Serialize fallback for unsupported types
         */
        serializeFallback(block) {
            return block.content.text || '';
        }

        /**
         * Serialize inline Markdown from HTML
         */
        serializeInlineMarkdown(text) {
            // This is a simplified version - in production, you'd want to parse HTML properly
            let markdown = text;

            // Remove HTML tags and convert to Markdown
            markdown = markdown.replace(/<strong>(.+?)<\/strong>/g, '**$1**');
            markdown = markdown.replace(/<b>(.+?)<\/b>/g, '**$1**');
            markdown = markdown.replace(/<em>(.+?)<\/em>/g, '*$1*');
            markdown = markdown.replace(/<i>(.+?)<\/i>/g, '*$1*');
            markdown = markdown.replace(/<code>(.+?)<\/code>/g, '`$1`');
            markdown = markdown.replace(/<del>(.+?)<\/del>/g, '~~$1~~');
            markdown = markdown.replace(/<a href="([^"]+)">(.+?)<\/a>/g, '[$2]($1)');

            return markdown;
        }
    }

    // Export to global scope
    window.MarkdownParser = MarkdownParser;
    window.MarkdownSerializer = MarkdownSerializer;

})(window);
