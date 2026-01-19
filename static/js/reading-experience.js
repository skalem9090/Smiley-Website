/**
 * Reading Experience Enhancements
 * - Reading time estimation
 * - Reading progress bar
 * - Table of contents generation
 * - Reader mode toggle
 */

class ReadingExperience {
    constructor() {
        this.progressBar = null;
        this.tocContainer = null;
        this.readerModeActive = false;
        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    setup() {
        const postContent = document.querySelector('.post-content');
        if (!postContent) return;

        // Calculate and display reading time
        this.addReadingTime(postContent);

        // Add reading progress bar
        this.addProgressBar();

        // Generate table of contents
        this.generateTableOfContents(postContent);

        // Add reader mode toggle
        this.addReaderModeToggle();

        // Load saved reader mode preference
        this.loadReaderModePreference();
    }

    /**
     * Calculate reading time based on word count
     * Average reading speed: 200-250 words per minute
     */
    addReadingTime(content) {
        const text = content.textContent || content.innerText;
        const wordCount = text.trim().split(/\s+/).length;
        const readingTime = Math.ceil(wordCount / 225); // 225 words per minute

        // Find the meta section to add reading time
        const metaSection = document.querySelector('.post-article .meta');
        if (metaSection) {
            const readingTimeSpan = document.createElement('span');
            readingTimeSpan.className = 'reading-time';
            readingTimeSpan.innerHTML = ` · <span style="color: var(--accent); font-weight: 500;">📖 ${readingTime} min read</span>`;
            metaSection.appendChild(readingTimeSpan);
        }
    }

    /**
     * Add reading progress bar at the top of the page
     */
    addProgressBar() {
        // Create progress bar element
        this.progressBar = document.createElement('div');
        this.progressBar.className = 'reading-progress-bar';
        this.progressBar.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 0%;
            height: 3px;
            background: linear-gradient(90deg, var(--accent), var(--accent-muted));
            z-index: 9999;
            transition: width 0.1s ease-out;
        `;
        document.body.appendChild(this.progressBar);

        // Update progress on scroll
        window.addEventListener('scroll', () => this.updateProgress(), { passive: true });
        this.updateProgress(); // Initial update
    }

    updateProgress() {
        const windowHeight = window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight - windowHeight;
        const scrolled = window.scrollY;
        const progress = (scrolled / documentHeight) * 100;
        
        if (this.progressBar) {
            this.progressBar.style.width = Math.min(progress, 100) + '%';
        }
    }

    /**
     * Generate table of contents from headings
     */
    generateTableOfContents(content) {
        const headings = content.querySelectorAll('h1, h2, h3, h4');
        
        // Only generate TOC if there are 3 or more headings
        if (headings.length < 3) return;

        // Create TOC container
        const tocWrapper = document.createElement('div');
        tocWrapper.className = 'table-of-contents-wrapper';
        tocWrapper.style.cssText = `
            margin: 2rem 0;
            padding: 1.5rem;
            background: var(--hover-bg);
            border-radius: var(--radius);
            border: 1px solid var(--paper-border);
        `;

        const tocHeader = document.createElement('div');
        tocHeader.style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            cursor: pointer;
        `;
        tocHeader.innerHTML = `
            <h3 style="margin: 0; font-size: 1.1rem; color: var(--paper-text);">
                📑 Table of Contents
            </h3>
            <span class="toc-toggle" style="color: var(--muted); font-size: 0.9rem;">
                ▼ Collapse
            </span>
        `;

        this.tocContainer = document.createElement('nav');
        this.tocContainer.className = 'table-of-contents';
        this.tocContainer.style.cssText = `
            display: block;
        `;

        const tocList = document.createElement('ul');
        tocList.style.cssText = `
            list-style: none;
            padding: 0;
            margin: 0;
        `;

        // Generate TOC items
        headings.forEach((heading, index) => {
            // Add ID to heading if it doesn't have one
            if (!heading.id) {
                heading.id = `heading-${index}`;
            }

            const level = parseInt(heading.tagName.substring(1));
            const listItem = document.createElement('li');
            listItem.style.cssText = `
                margin: 0.5rem 0;
                padding-left: ${(level - 1) * 1}rem;
            `;

            const link = document.createElement('a');
            link.href = `#${heading.id}`;
            link.textContent = heading.textContent;
            link.style.cssText = `
                color: var(--paper-text);
                text-decoration: none;
                font-size: ${level === 1 ? '1rem' : level === 2 ? '0.95rem' : '0.9rem'};
                font-weight: ${level <= 2 ? '500' : '400'};
                transition: color 0.2s;
                display: block;
                padding: 0.25rem 0;
            `;

            link.addEventListener('mouseenter', () => {
                link.style.color = 'var(--accent)';
            });

            link.addEventListener('mouseleave', () => {
                link.style.color = 'var(--paper-text)';
            });

            // Smooth scroll to heading
            link.addEventListener('click', (e) => {
                e.preventDefault();
                heading.scrollIntoView({ behavior: 'smooth', block: 'start' });
                history.pushState(null, null, `#${heading.id}`);
            });

            listItem.appendChild(link);
            tocList.appendChild(listItem);
        });

        this.tocContainer.appendChild(tocList);
        tocWrapper.appendChild(tocHeader);
        tocWrapper.appendChild(this.tocContainer);

        // Toggle TOC visibility
        let tocExpanded = true;
        tocHeader.addEventListener('click', () => {
            tocExpanded = !tocExpanded;
            this.tocContainer.style.display = tocExpanded ? 'block' : 'none';
            tocHeader.querySelector('.toc-toggle').textContent = tocExpanded ? '▼ Collapse' : '▶ Expand';
        });

        // Insert TOC after the post header
        const postHeader = document.querySelector('.post-article header');
        if (postHeader && postHeader.nextSibling) {
            postHeader.parentNode.insertBefore(tocWrapper, postHeader.nextSibling);
        }
    }

    /**
     * Add reader mode toggle button (only on post pages)
     */
    addReaderModeToggle() {
        const postArticle = document.querySelector('.post-article');
        const postContent = document.querySelector('.post-content');
        
        // Only add reader mode button if we're on an actual post page
        // (has both post-article and post-content)
        if (!postArticle || !postContent) return;

        // Create floating action button
        const readerModeBtn = document.createElement('button');
        readerModeBtn.className = 'reader-mode-toggle';
        readerModeBtn.innerHTML = '📖';
        readerModeBtn.title = 'Toggle Reader Mode';
        readerModeBtn.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: var(--ink-accent);
            color: white;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transition: all 0.3s ease;
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        readerModeBtn.addEventListener('mouseenter', () => {
            readerModeBtn.style.transform = 'scale(1.1)';
            readerModeBtn.style.boxShadow = '0 6px 16px rgba(0, 0, 0, 0.2)';
        });

        readerModeBtn.addEventListener('mouseleave', () => {
            readerModeBtn.style.transform = 'scale(1)';
            readerModeBtn.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
        });

        readerModeBtn.addEventListener('click', () => {
            this.toggleReaderMode();
        });

        document.body.appendChild(readerModeBtn);
    }

    /**
     * Toggle reader mode (hide distractions)
     */
    toggleReaderMode() {
        this.readerModeActive = !this.readerModeActive;

        const elementsToHide = [
            '.main-nav',
            '.site-footer',
            '.author-bio-section',
            '.comments-section',
            'footer',
            '.table-of-contents-wrapper'
        ];

        elementsToHide.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(el => {
                if (this.readerModeActive) {
                    el.style.display = 'none';
                } else {
                    el.style.display = '';
                }
            });
        });

        // Adjust post article styling
        const postArticle = document.querySelector('.post-article');
        if (postArticle) {
            if (this.readerModeActive) {
                postArticle.style.maxWidth = '700px';
                postArticle.style.margin = '2rem auto';
                postArticle.style.fontSize = '1.1rem';
                postArticle.style.lineHeight = '1.8';
            } else {
                postArticle.style.maxWidth = '';
                postArticle.style.margin = '';
                postArticle.style.fontSize = '';
                postArticle.style.lineHeight = '';
            }
        }

        // Save preference
        localStorage.setItem('readerMode', this.readerModeActive ? 'true' : 'false');

        // Show notification
        this.showNotification(
            this.readerModeActive ? 'Reader Mode Enabled' : 'Reader Mode Disabled'
        );
    }

    /**
     * Load saved reader mode preference
     */
    loadReaderModePreference() {
        const savedPreference = localStorage.getItem('readerMode');
        if (savedPreference === 'true') {
            this.toggleReaderMode();
        }
    }

    /**
     * Show temporary notification
     */
    showNotification(message) {
        const notification = document.createElement('div');
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 5rem;
            right: 2rem;
            background: var(--paper-bg);
            color: var(--paper-text);
            padding: 1rem 1.5rem;
            border-radius: var(--radius);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
            border: 1px solid var(--paper-border);
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 2000);
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }

    /* Responsive adjustments */
    @media (max-width: 768px) {
        .reader-mode-toggle {
            bottom: 1rem !important;
            right: 1rem !important;
            width: 45px !important;
            height: 45px !important;
            font-size: 1.3rem !important;
        }

        .table-of-contents-wrapper {
            margin: 1rem 0 !important;
            padding: 1rem !important;
        }
    }
`;
document.head.appendChild(style);

// Initialize reading experience
new ReadingExperience();
