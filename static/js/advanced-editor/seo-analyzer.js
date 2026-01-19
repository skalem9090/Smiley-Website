/**
 * Advanced Editor System - SEO Analyzer
 * 
 * Provides real-time SEO analysis and optimization tools:
 * - Readability scoring (Flesch Reading Ease, Flesch-Kincaid Grade)
 * - Meta description character counter and preview
 * - Heading structure analysis and validation
 * - Keyword optimization suggestions
 * - Alt text validation for images
 * - Content length and structure recommendations
 * 
 * Validates Property 14: SEO Analysis Accuracy
 */

(function(window) {
    'use strict';

    /**
     * SEO Analyzer
     * Analyzes content for SEO optimization
     */
    class SEOAnalyzer {
        constructor(config = {}) {
            this.config = {
                minReadabilityScore: config.minReadabilityScore || 60,
                maxReadabilityScore: config.maxReadabilityScore || 70,
                minMetaDescriptionLength: config.minMetaDescriptionLength || 120,
                maxMetaDescriptionLength: config.maxMetaDescriptionLength || 160,
                minContentLength: config.minContentLength || 300,
                recommendedContentLength: config.recommendedContentLength || 1000,
                maxKeywordDensity: config.maxKeywordDensity || 2.5,
                ...config
            };

            this.analysisCache = new Map();
            this.lastAnalysis = null;
        }

        /**
         * Analyze content for SEO
         * @param {Object} content - Content to analyze
         * @returns {Object} SEO analysis results
         */
        analyze(content) {
            const text = this.extractText(content);
            const blocks = content.blocks || [];
            
            const analysis = {
                readability: this.analyzeReadability(text),
                metaDescription: this.analyzeMetaDescription(content.metaDescription || ''),
                headings: this.analyzeHeadings(blocks),
                keywords: this.analyzeKeywords(text, content.focusKeyword),
                images: this.analyzeImages(blocks),
                contentLength: this.analyzeContentLength(text),
                structure: this.analyzeStructure(blocks),
                overallScore: 0,
                recommendations: []
            };

            // Calculate overall score
            analysis.overallScore = this.calculateOverallScore(analysis);
            
            // Generate recommendations
            analysis.recommendations = this.generateRecommendations(analysis);
            
            this.lastAnalysis = analysis;
            return analysis;
        }

        /**
         * Extract text from content
         * @param {Object} content - Content object
         * @returns {string} Extracted text
         */
        extractText(content) {
            if (typeof content === 'string') {
                return content;
            }

            if (content.text) {
                return content.text;
            }

            if (content.blocks) {
                return content.blocks
                    .filter(block => block.content && block.content.text)
                    .map(block => block.content.text)
                    .join(' ');
            }

            return '';
        }

        /**
         * Analyze readability
         * @param {string} text - Text to analyze
         * @returns {Object} Readability analysis
         */
        analyzeReadability(text) {
            const sentences = this.countSentences(text);
            const words = this.countWords(text);
            const syllables = this.countSyllables(text);

            // Flesch Reading Ease Score
            const fleschScore = this.calculateFleschScore(sentences, words, syllables);
            
            // Flesch-Kincaid Grade Level
            const gradeLevel = this.calculateGradeLevel(sentences, words, syllables);

            return {
                fleschScore: Math.round(fleschScore * 10) / 10,
                gradeLevel: Math.round(gradeLevel * 10) / 10,
                sentences: sentences,
                words: words,
                syllables: syllables,
                averageWordsPerSentence: sentences > 0 ? Math.round((words / sentences) * 10) / 10 : 0,
                averageSyllablesPerWord: words > 0 ? Math.round((syllables / words) * 10) / 10 : 0,
                difficulty: this.getReadabilityDifficulty(fleschScore),
                score: this.scoreReadability(fleschScore)
            };
        }

        /**
         * Calculate Flesch Reading Ease Score
         * Formula: 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
         */
        calculateFleschScore(sentences, words, syllables) {
            if (sentences === 0 || words === 0) return 0;
            
            const avgWordsPerSentence = words / sentences;
            const avgSyllablesPerWord = syllables / words;
            
            return 206.835 - (1.015 * avgWordsPerSentence) - (84.6 * avgSyllablesPerWord);
        }

        /**
         * Calculate Flesch-Kincaid Grade Level
         * Formula: 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
         */
        calculateGradeLevel(sentences, words, syllables) {
            if (sentences === 0 || words === 0) return 0;
            
            const avgWordsPerSentence = words / sentences;
            const avgSyllablesPerWord = syllables / words;
            
            return (0.39 * avgWordsPerSentence) + (11.8 * avgSyllablesPerWord) - 15.59;
        }

        /**
         * Count sentences in text
         */
        countSentences(text) {
            if (!text) return 0;
            const sentences = text.match(/[.!?]+/g);
            return sentences ? sentences.length : 0;
        }

        /**
         * Count words in text
         */
        countWords(text) {
            if (!text) return 0;
            const words = text.match(/\b\w+\b/g);
            return words ? words.length : 0;
        }

        /**
         * Count syllables in text (approximation)
         */
        countSyllables(text) {
            if (!text) return 0;
            
            const words = text.toLowerCase().match(/\b\w+\b/g) || [];
            let syllableCount = 0;
            
            words.forEach(word => {
                syllableCount += this.countSyllablesInWord(word);
            });
            
            return syllableCount;
        }

        /**
         * Count syllables in a single word
         */
        countSyllablesInWord(word) {
            word = word.toLowerCase();
            if (word.length <= 3) return 1;
            
            // Remove silent e
            word = word.replace(/(?:[^laeiouy]es|ed|[^laeiouy]e)$/, '');
            word = word.replace(/^y/, '');
            
            // Count vowel groups
            const matches = word.match(/[aeiouy]{1,2}/g);
            return matches ? matches.length : 1;
        }

        /**
         * Get readability difficulty level
         */
        getReadabilityDifficulty(score) {
            if (score >= 90) return 'Very Easy';
            if (score >= 80) return 'Easy';
            if (score >= 70) return 'Fairly Easy';
            if (score >= 60) return 'Standard';
            if (score >= 50) return 'Fairly Difficult';
            if (score >= 30) return 'Difficult';
            return 'Very Difficult';
        }

        /**
         * Score readability (0-100)
         */
        scoreReadability(fleschScore) {
            const min = this.config.minReadabilityScore;
            const max = this.config.maxReadabilityScore;
            
            if (fleschScore >= min && fleschScore <= max) {
                return 100;
            } else if (fleschScore < min) {
                return Math.max(0, 100 - (min - fleschScore) * 2);
            } else {
                return Math.max(0, 100 - (fleschScore - max) * 2);
            }
        }

        /**
         * Analyze meta description
         * @param {string} description - Meta description
         * @returns {Object} Meta description analysis
         */
        analyzeMetaDescription(description) {
            const length = description.length;
            const min = this.config.minMetaDescriptionLength;
            const max = this.config.maxMetaDescriptionLength;
            
            let score = 0;
            if (length >= min && length <= max) {
                score = 100;
            } else if (length < min) {
                score = Math.max(0, (length / min) * 100);
            } else {
                score = Math.max(0, 100 - ((length - max) / max) * 100);
            }

            return {
                length: length,
                minLength: min,
                maxLength: max,
                isOptimal: length >= min && length <= max,
                isTooShort: length < min,
                isTooLong: length > max,
                score: Math.round(score),
                preview: length > 0 ? (description.substring(0, max) + (length > max ? '...' : '')) : ''
            };
        }

        /**
         * Analyze heading structure
         * @param {Array} blocks - Content blocks
         * @returns {Object} Heading analysis
         */
        analyzeHeadings(blocks) {
            const headings = blocks.filter(block => block.type === 'heading');
            const structure = [];
            let hasH1 = false;
            let h1Count = 0;
            let previousLevel = 0;
            let skippedLevels = false;

            headings.forEach(heading => {
                const level = heading.content.data?.level || 1;
                const text = heading.content.text || '';
                
                structure.push({ level, text, length: text.length });
                
                if (level === 1) {
                    hasH1 = true;
                    h1Count++;
                }
                
                // Check for skipped levels
                if (previousLevel > 0 && level > previousLevel + 1) {
                    skippedLevels = true;
                }
                
                previousLevel = level;
            });

            let score = 100;
            if (!hasH1) score -= 30;
            if (h1Count > 1) score -= 20;
            if (skippedLevels) score -= 15;
            if (headings.length === 0) score -= 25;

            return {
                count: headings.length,
                hasH1: hasH1,
                h1Count: h1Count,
                structure: structure,
                skippedLevels: skippedLevels,
                score: Math.max(0, score)
            };
        }

        /**
         * Analyze keywords
         * @param {string} text - Text to analyze
         * @param {string} focusKeyword - Focus keyword
         * @returns {Object} Keyword analysis
         */
        analyzeKeywords(text, focusKeyword = '') {
            const words = text.toLowerCase().match(/\b\w+\b/g) || [];
            const totalWords = words.length;
            
            // Count keyword occurrences
            const keywordCount = focusKeyword ? 
                this.countKeywordOccurrences(text, focusKeyword) : 0;
            
            // Calculate keyword density
            const density = totalWords > 0 ? (keywordCount / totalWords) * 100 : 0;
            
            // Find most common words (excluding stop words)
            const wordFrequency = this.calculateWordFrequency(words);
            const topKeywords = this.getTopKeywords(wordFrequency, 10);

            let score = 0;
            if (focusKeyword) {
                if (keywordCount >= 3 && density <= this.config.maxKeywordDensity) {
                    score = 100;
                } else if (keywordCount < 3) {
                    score = (keywordCount / 3) * 100;
                } else {
                    score = Math.max(0, 100 - (density - this.config.maxKeywordDensity) * 20);
                }
            }

            return {
                focusKeyword: focusKeyword,
                keywordCount: keywordCount,
                density: Math.round(density * 100) / 100,
                isOptimal: density > 0.5 && density <= this.config.maxKeywordDensity,
                topKeywords: topKeywords,
                score: Math.round(score)
            };
        }

        /**
         * Count keyword occurrences
         */
        countKeywordOccurrences(text, keyword) {
            const regex = new RegExp('\\b' + keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'gi');
            const matches = text.match(regex);
            return matches ? matches.length : 0;
        }

        /**
         * Calculate word frequency
         */
        calculateWordFrequency(words) {
            const stopWords = new Set([
                'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
                'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
                'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
                'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their'
            ]);

            const frequency = new Map();
            
            words.forEach(word => {
                if (word.length > 3 && !stopWords.has(word)) {
                    frequency.set(word, (frequency.get(word) || 0) + 1);
                }
            });
            
            return frequency;
        }

        /**
         * Get top keywords by frequency
         */
        getTopKeywords(frequency, limit = 10) {
            return Array.from(frequency.entries())
                .sort((a, b) => b[1] - a[1])
                .slice(0, limit)
                .map(([word, count]) => ({ word, count }));
        }

        /**
         * Analyze images
         * @param {Array} blocks - Content blocks
         * @returns {Object} Image analysis
         */
        analyzeImages(blocks) {
            const images = blocks.filter(block => block.type === 'image');
            const totalImages = images.length;
            const imagesWithAlt = images.filter(img => 
                img.content.data?.altText && img.content.data.altText.length > 0
            ).length;
            
            const missingAlt = totalImages - imagesWithAlt;
            const score = totalImages > 0 ? (imagesWithAlt / totalImages) * 100 : 100;

            return {
                totalImages: totalImages,
                imagesWithAlt: imagesWithAlt,
                missingAlt: missingAlt,
                altTextCoverage: Math.round(score),
                score: Math.round(score)
            };
        }

        /**
         * Analyze content length
         * @param {string} text - Text to analyze
         * @returns {Object} Content length analysis
         */
        analyzeContentLength(text) {
            const wordCount = this.countWords(text);
            const min = this.config.minContentLength;
            const recommended = this.config.recommendedContentLength;
            
            let score = 0;
            if (wordCount >= recommended) {
                score = 100;
            } else if (wordCount >= min) {
                score = 50 + ((wordCount - min) / (recommended - min)) * 50;
            } else {
                score = (wordCount / min) * 50;
            }

            return {
                wordCount: wordCount,
                minLength: min,
                recommendedLength: recommended,
                isTooShort: wordCount < min,
                isOptimal: wordCount >= recommended,
                score: Math.round(score)
            };
        }

        /**
         * Analyze content structure
         * @param {Array} blocks - Content blocks
         * @returns {Object} Structure analysis
         */
        analyzeStructure(blocks) {
            const paragraphs = blocks.filter(b => b.type === 'paragraph').length;
            const headings = blocks.filter(b => b.type === 'heading').length;
            const lists = blocks.filter(b => b.type === 'listItem').length;
            const images = blocks.filter(b => b.type === 'image').length;
            const links = this.countLinks(blocks);

            const hasVariety = paragraphs > 0 && headings > 0 && (lists > 0 || images > 0);
            const score = hasVariety ? 100 : 50;

            return {
                paragraphs: paragraphs,
                headings: headings,
                lists: lists,
                images: images,
                links: links,
                hasVariety: hasVariety,
                score: score
            };
        }

        /**
         * Count links in blocks
         */
        countLinks(blocks) {
            let linkCount = 0;
            blocks.forEach(block => {
                if (block.content && block.content.html) {
                    const matches = block.content.html.match(/<a\s+/g);
                    linkCount += matches ? matches.length : 0;
                }
            });
            return linkCount;
        }

        /**
         * Calculate overall SEO score
         * @param {Object} analysis - Analysis results
         * @returns {number} Overall score (0-100)
         */
        calculateOverallScore(analysis) {
            const weights = {
                readability: 0.20,
                metaDescription: 0.15,
                headings: 0.15,
                keywords: 0.15,
                images: 0.10,
                contentLength: 0.15,
                structure: 0.10
            };

            let totalScore = 0;
            totalScore += analysis.readability.score * weights.readability;
            totalScore += analysis.metaDescription.score * weights.metaDescription;
            totalScore += analysis.headings.score * weights.headings;
            totalScore += analysis.keywords.score * weights.keywords;
            totalScore += analysis.images.score * weights.images;
            totalScore += analysis.contentLength.score * weights.contentLength;
            totalScore += analysis.structure.score * weights.structure;

            return Math.round(totalScore);
        }

        /**
         * Generate recommendations
         * @param {Object} analysis - Analysis results
         * @returns {Array} Recommendations
         */
        generateRecommendations(analysis) {
            const recommendations = [];

            // Readability
            if (analysis.readability.score < 70) {
                recommendations.push({
                    category: 'readability',
                    priority: 'high',
                    message: `Improve readability (current score: ${analysis.readability.fleschScore}). Try shorter sentences and simpler words.`
                });
            }

            // Meta description
            if (analysis.metaDescription.isTooShort) {
                recommendations.push({
                    category: 'meta',
                    priority: 'high',
                    message: `Meta description is too short (${analysis.metaDescription.length} characters). Aim for ${analysis.metaDescription.minLength}-${analysis.metaDescription.maxLength} characters.`
                });
            } else if (analysis.metaDescription.isTooLong) {
                recommendations.push({
                    category: 'meta',
                    priority: 'medium',
                    message: `Meta description is too long (${analysis.metaDescription.length} characters). It will be truncated in search results.`
                });
            }

            // Headings
            if (!analysis.headings.hasH1) {
                recommendations.push({
                    category: 'headings',
                    priority: 'high',
                    message: 'Add an H1 heading to your content.'
                });
            }
            if (analysis.headings.h1Count > 1) {
                recommendations.push({
                    category: 'headings',
                    priority: 'medium',
                    message: 'Use only one H1 heading per page.'
                });
            }
            if (analysis.headings.skippedLevels) {
                recommendations.push({
                    category: 'headings',
                    priority: 'low',
                    message: 'Avoid skipping heading levels (e.g., H2 to H4).'
                });
            }

            // Keywords
            if (analysis.keywords.focusKeyword && analysis.keywords.keywordCount < 3) {
                recommendations.push({
                    category: 'keywords',
                    priority: 'medium',
                    message: `Use your focus keyword "${analysis.keywords.focusKeyword}" more frequently (currently ${analysis.keywords.keywordCount} times).`
                });
            }
            if (analysis.keywords.density > this.config.maxKeywordDensity) {
                recommendations.push({
                    category: 'keywords',
                    priority: 'medium',
                    message: `Keyword density is too high (${analysis.keywords.density}%). Reduce keyword usage to avoid over-optimization.`
                });
            }

            // Images
            if (analysis.images.missingAlt > 0) {
                recommendations.push({
                    category: 'images',
                    priority: 'high',
                    message: `Add alt text to ${analysis.images.missingAlt} image(s) for better accessibility and SEO.`
                });
            }

            // Content length
            if (analysis.contentLength.isTooShort) {
                recommendations.push({
                    category: 'content',
                    priority: 'high',
                    message: `Content is too short (${analysis.contentLength.wordCount} words). Aim for at least ${analysis.contentLength.recommendedLength} words.`
                });
            }

            // Structure
            if (!analysis.structure.hasVariety) {
                recommendations.push({
                    category: 'structure',
                    priority: 'low',
                    message: 'Add more variety to your content structure (headings, lists, images).'
                });
            }

            return recommendations;
        }

        /**
         * Get last analysis
         * @returns {Object} Last analysis results
         */
        getLastAnalysis() {
            return this.lastAnalysis;
        }
    }

    // Export to global scope
    window.SEOAnalyzer = SEOAnalyzer;

    console.log('SEO Analyzer module loaded');

})(window);
