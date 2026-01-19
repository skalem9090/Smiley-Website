/**
 * Theme Manager - Site-wide Dark/Light Mode
 * Manages theme preferences and applies them across the entire site
 */

class ThemeManager {
    constructor() {
        this.currentTheme = 'light';
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
        // Load saved theme preference or detect system preference
        this.loadThemePreference();
        
        // Add theme toggle button to navigation
        this.addThemeToggle();
        
        // Apply the theme
        this.applyTheme(this.currentTheme);
    }

    /**
     * Load theme preference from localStorage or system
     */
    loadThemePreference() {
        const savedTheme = localStorage.getItem('siteTheme');
        
        if (savedTheme) {
            this.currentTheme = savedTheme;
        } else {
            // Check system preference
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                this.currentTheme = 'dark';
            }
        }
    }

    /**
     * Add theme toggle button to navigation
     */
    addThemeToggle() {
        const navRight = document.querySelector('.nav-right');
        if (!navRight) return;

        // Create theme toggle button
        const themeToggle = document.createElement('button');
        themeToggle.className = 'theme-toggle-btn';
        themeToggle.setAttribute('aria-label', 'Toggle dark mode');
        themeToggle.title = 'Toggle dark/light mode';
        
        // Set initial icon
        this.updateToggleIcon(themeToggle);
        
        // Style the button
        themeToggle.style.cssText = `
            background: var(--paper-cream);
            border: 2px solid var(--paper-shadow);
            padding: 0.5rem 0.75rem;
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-size: 1.2rem;
            transition: var(--transition);
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 44px;
            height: 44px;
            box-shadow: 0 2px 4px rgba(139, 69, 19, 0.1);
        `;

        themeToggle.addEventListener('click', () => {
            this.toggleTheme();
            this.updateToggleIcon(themeToggle);
        });

        themeToggle.addEventListener('mouseenter', () => {
            themeToggle.style.transform = 'scale(1.1) rotate(15deg)';
            themeToggle.style.boxShadow = '0 4px 8px rgba(139, 69, 19, 0.2)';
        });

        themeToggle.addEventListener('mouseleave', () => {
            themeToggle.style.transform = 'scale(1) rotate(0deg)';
            themeToggle.style.boxShadow = '0 2px 4px rgba(139, 69, 19, 0.1)';
        });

        // Insert before the dropdown menu
        const dropdown = navRight.querySelector('.dropdown');
        if (dropdown) {
            navRight.insertBefore(themeToggle, dropdown);
        } else {
            navRight.appendChild(themeToggle);
        }
    }

    /**
     * Update toggle button icon based on current theme
     */
    updateToggleIcon(button) {
        button.innerHTML = this.currentTheme === 'dark' ? '☀️' : '🌙';
        button.title = this.currentTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
    }

    /**
     * Toggle between light and dark themes
     */
    toggleTheme() {
        this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(this.currentTheme);
        localStorage.setItem('siteTheme', this.currentTheme);
        
        // Show notification
        this.showNotification(
            this.currentTheme === 'dark' ? 'Dark Mode Enabled' : 'Light Mode Enabled'
        );
    }

    /**
     * Apply theme to the document
     */
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        
        // Also update editor theme if present
        const editorContainer = document.querySelector('.advanced-editor-container');
        if (editorContainer) {
            if (theme === 'dark') {
                editorContainer.classList.add('dark-theme');
            } else {
                editorContainer.classList.remove('dark-theme');
            }
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
                if (notification.parentNode) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, 2000);
    }
}

// Listen for system theme changes
if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        const themeManager = new ThemeManager();
        const newTheme = e.matches ? 'dark' : 'light';
        
        // Only auto-switch if user hasn't manually set a preference
        if (!localStorage.getItem('siteTheme')) {
            themeManager.currentTheme = newTheme;
            themeManager.applyTheme(newTheme);
        }
    });
}

// Initialize theme manager
new ThemeManager();
