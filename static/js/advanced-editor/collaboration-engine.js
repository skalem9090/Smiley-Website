/**
 * Advanced Editor System - Collaboration Engine
 * 
 * Manages real-time collaboration features:
 * - User presence tracking and cursor positions
 * - Comments attached to content sections
 * - Suggestions with accept/reject functionality
 * - Version history and restoration
 * - Collaborative editing session management
 * 
 * Validates Property 12: Collaboration Feature Integrity
 * Validates Property 13: Real-Time Collaboration Consistency
 */

(function(window) {
    'use strict';

    /**
     * Collaboration Engine
     * Manages collaborative editing features
     */
    class CollaborationEngine {
        constructor(websocketManager, config = {}) {
            this.ws = websocketManager;
            this.config = {
                presenceUpdateInterval: config.presenceUpdateInterval || 5000,
                cursorUpdateThrottle: config.cursorUpdateThrottle || 100,
                ...config
            };

            this.sessionId = null;
            this.documentId = null;
            this.currentUser = null;
            this.activeUsers = new Map();
            this.comments = new Map();
            this.suggestions = new Map();
            this.versions = [];
            
            this.presenceTimer = null;
            this.cursorThrottle = null;

            // Event listeners
            this.eventListeners = {
                'userJoined': [],
                'userLeft': [],
                'presenceUpdated': [],
                'commentAdded': [],
                'commentResolved': [],
                'suggestionAdded': [],
                'suggestionStatusChanged': [],
                'versionCreated': [],
                'contentChanged': []
            };

            this.setupMessageHandlers();
        }

        /**
         * Setup WebSocket message handlers
         */
        setupMessageHandlers() {
            // User presence
            this.ws.on('user:joined', (data) => this.handleUserJoined(data));
            this.ws.on('user:left', (data) => this.handleUserLeft(data));
            this.ws.on('presence:updated', (data) => this.handlePresenceUpdated(data));

            // Comments
            this.ws.on('comment:added', (data) => this.handleCommentAdded(data));
            this.ws.on('comment:resolved', (data) => this.handleCommentResolved(data));

            // Suggestions
            this.ws.on('suggestion:added', (data) => this.handleSuggestionAdded(data));
            this.ws.on('suggestion:status', (data) => this.handleSuggestionStatus(data));

            // Versions
            this.ws.on('version:created', (data) => this.handleVersionCreated(data));

            // Content changes
            this.ws.on('content:changed', (data) => this.handleContentChanged(data));
        }

        /**
         * Start collaboration session
         * @param {string} documentId - Document ID
         * @param {Object} user - Current user
         * @returns {Promise<Object>} Session data
         */
        async startSession(documentId, user) {
            this.documentId = documentId;
            this.currentUser = user;

            try {
                const response = await this.ws.send('session:start', {
                    documentId: documentId,
                    user: user
                }, true);

                this.sessionId = response.sessionId;
                this.activeUsers = new Map(response.activeUsers.map(u => [u.id, u]));

                // Start presence updates
                this.startPresenceUpdates();

                return response;
            } catch (error) {
                console.error('Failed to start collaboration session:', error);
                throw error;
            }
        }

        /**
         * End collaboration session
         * @returns {Promise<void>}
         */
        async endSession() {
            if (!this.sessionId) {
                return;
            }

            this.stopPresenceUpdates();

            try {
                await this.ws.send('session:end', {
                    sessionId: this.sessionId
                });

                this.sessionId = null;
                this.documentId = null;
                this.activeUsers.clear();
            } catch (error) {
                console.error('Failed to end collaboration session:', error);
            }
        }

        /**
         * Update user presence
         * @param {Object} presence - Presence data
         */
        updatePresence(presence) {
            if (!this.sessionId) {
                return;
            }

            const presenceData = {
                sessionId: this.sessionId,
                userId: this.currentUser.id,
                cursor: presence.cursor || null,
                selection: presence.selection || null,
                isActive: presence.isActive !== undefined ? presence.isActive : true,
                timestamp: Date.now()
            };

            this.ws.send('presence:update', presenceData);
        }

        /**
         * Update cursor position (throttled)
         * @param {Object} cursor - Cursor position
         */
        updateCursor(cursor) {
            if (this.cursorThrottle) {
                clearTimeout(this.cursorThrottle);
            }

            this.cursorThrottle = setTimeout(() => {
                this.updatePresence({ cursor });
            }, this.config.cursorUpdateThrottle);
        }

        /**
         * Get active users
         * @returns {Array} Active users
         */
        getActiveUsers() {
            return Array.from(this.activeUsers.values());
        }

        /**
         * Add comment to content
         * @param {string} blockId - Block ID
         * @param {string} content - Comment content
         * @param {Object} options - Additional options
         * @returns {Promise<Object>} Created comment
         */
        async addComment(blockId, content, options = {}) {
            if (!this.sessionId) {
                throw new Error('No active collaboration session');
            }

            try {
                const response = await this.ws.send('comment:add', {
                    sessionId: this.sessionId,
                    blockId: blockId,
                    content: content,
                    author: this.currentUser,
                    parentId: options.parentId || null,
                    timestamp: Date.now()
                }, true);

                const comment = response.comment;
                this.comments.set(comment.id, comment);

                return comment;
            } catch (error) {
                console.error('Failed to add comment:', error);
                throw error;
            }
        }

        /**
         * Resolve comment
         * @param {string} commentId - Comment ID
         * @returns {Promise<void>}
         */
        async resolveComment(commentId) {
            if (!this.sessionId) {
                throw new Error('No active collaboration session');
            }

            try {
                await this.ws.send('comment:resolve', {
                    sessionId: this.sessionId,
                    commentId: commentId,
                    resolvedBy: this.currentUser.id,
                    timestamp: Date.now()
                }, true);

                const comment = this.comments.get(commentId);
                if (comment) {
                    comment.resolved = true;
                    comment.resolvedBy = this.currentUser.id;
                    comment.resolvedAt = Date.now();
                }
            } catch (error) {
                console.error('Failed to resolve comment:', error);
                throw error;
            }
        }

        /**
         * Get comments for block
         * @param {string} blockId - Block ID
         * @returns {Array} Comments
         */
        getCommentsForBlock(blockId) {
            return Array.from(this.comments.values())
                .filter(comment => comment.blockId === blockId && !comment.resolved);
        }

        /**
         * Add suggestion
         * @param {string} blockId - Block ID
         * @param {string} type - Suggestion type (insert, delete, modify)
         * @param {*} originalContent - Original content
         * @param {*} suggestedContent - Suggested content
         * @returns {Promise<Object>} Created suggestion
         */
        async addSuggestion(blockId, type, originalContent, suggestedContent) {
            if (!this.sessionId) {
                throw new Error('No active collaboration session');
            }

            try {
                const response = await this.ws.send('suggestion:add', {
                    sessionId: this.sessionId,
                    blockId: blockId,
                    type: type,
                    originalContent: originalContent,
                    suggestedContent: suggestedContent,
                    author: this.currentUser,
                    status: 'pending',
                    timestamp: Date.now()
                }, true);

                const suggestion = response.suggestion;
                this.suggestions.set(suggestion.id, suggestion);

                return suggestion;
            } catch (error) {
                console.error('Failed to add suggestion:', error);
                throw error;
            }
        }

        /**
         * Accept suggestion
         * @param {string} suggestionId - Suggestion ID
         * @returns {Promise<void>}
         */
        async acceptSuggestion(suggestionId) {
            return this.updateSuggestionStatus(suggestionId, 'accepted');
        }

        /**
         * Reject suggestion
         * @param {string} suggestionId - Suggestion ID
         * @returns {Promise<void>}
         */
        async rejectSuggestion(suggestionId) {
            return this.updateSuggestionStatus(suggestionId, 'rejected');
        }

        /**
         * Update suggestion status
         * @param {string} suggestionId - Suggestion ID
         * @param {string} status - New status
         * @returns {Promise<void>}
         */
        async updateSuggestionStatus(suggestionId, status) {
            if (!this.sessionId) {
                throw new Error('No active collaboration session');
            }

            try {
                await this.ws.send('suggestion:status', {
                    sessionId: this.sessionId,
                    suggestionId: suggestionId,
                    status: status,
                    updatedBy: this.currentUser.id,
                    timestamp: Date.now()
                }, true);

                const suggestion = this.suggestions.get(suggestionId);
                if (suggestion) {
                    suggestion.status = status;
                    suggestion.updatedBy = this.currentUser.id;
                    suggestion.updatedAt = Date.now();
                }
            } catch (error) {
                console.error('Failed to update suggestion status:', error);
                throw error;
            }
        }

        /**
         * Get suggestions for block
         * @param {string} blockId - Block ID
         * @returns {Array} Suggestions
         */
        getSuggestionsForBlock(blockId) {
            return Array.from(this.suggestions.values())
                .filter(suggestion => suggestion.blockId === blockId && suggestion.status === 'pending');
        }

        /**
         * Create version
         * @param {string} description - Version description
         * @param {Array} blocks - Document blocks
         * @returns {Promise<Object>} Created version
         */
        async createVersion(description, blocks) {
            if (!this.sessionId) {
                throw new Error('No active collaboration session');
            }

            try {
                const response = await this.ws.send('version:create', {
                    sessionId: this.sessionId,
                    documentId: this.documentId,
                    description: description,
                    blocks: blocks,
                    author: this.currentUser,
                    timestamp: Date.now()
                }, true);

                const version = response.version;
                this.versions.push(version);

                return version;
            } catch (error) {
                console.error('Failed to create version:', error);
                throw error;
            }
        }

        /**
         * Restore version
         * @param {string} versionId - Version ID
         * @returns {Promise<Object>} Restored blocks
         */
        async restoreVersion(versionId) {
            if (!this.sessionId) {
                throw new Error('No active collaboration session');
            }

            try {
                const response = await this.ws.send('version:restore', {
                    sessionId: this.sessionId,
                    versionId: versionId,
                    restoredBy: this.currentUser.id,
                    timestamp: Date.now()
                }, true);

                return response.blocks;
            } catch (error) {
                console.error('Failed to restore version:', error);
                throw error;
            }
        }

        /**
         * Get version history
         * @returns {Promise<Array>} Version history
         */
        async getVersionHistory() {
            if (!this.sessionId) {
                throw new Error('No active collaboration session');
            }

            try {
                const response = await this.ws.send('version:history', {
                    sessionId: this.sessionId,
                    documentId: this.documentId
                }, true);

                this.versions = response.versions;
                return this.versions;
            } catch (error) {
                console.error('Failed to get version history:', error);
                throw error;
            }
        }

        /**
         * Broadcast content change
         * @param {Object} change - Content change
         */
        broadcastChange(change) {
            if (!this.sessionId) {
                return;
            }

            this.ws.send('content:change', {
                sessionId: this.sessionId,
                change: change,
                author: this.currentUser.id,
                timestamp: Date.now()
            });
        }

        /**
         * Start presence updates
         */
        startPresenceUpdates() {
            this.stopPresenceUpdates();

            this.presenceTimer = setInterval(() => {
                this.updatePresence({ isActive: true });
            }, this.config.presenceUpdateInterval);
        }

        /**
         * Stop presence updates
         */
        stopPresenceUpdates() {
            if (this.presenceTimer) {
                clearInterval(this.presenceTimer);
                this.presenceTimer = null;
            }
        }

        /**
         * Handle user joined event
         * @param {Object} data - User data
         */
        handleUserJoined(data) {
            this.activeUsers.set(data.user.id, data.user);
            this.emit('userJoined', data.user);
        }

        /**
         * Handle user left event
         * @param {Object} data - User data
         */
        handleUserLeft(data) {
            this.activeUsers.delete(data.userId);
            this.emit('userLeft', data.userId);
        }

        /**
         * Handle presence updated event
         * @param {Object} data - Presence data
         */
        handlePresenceUpdated(data) {
            const user = this.activeUsers.get(data.userId);
            if (user) {
                user.presence = {
                    cursor: data.cursor,
                    selection: data.selection,
                    isActive: data.isActive,
                    timestamp: data.timestamp
                };
                this.emit('presenceUpdated', { userId: data.userId, presence: user.presence });
            }
        }

        /**
         * Handle comment added event
         * @param {Object} data - Comment data
         */
        handleCommentAdded(data) {
            this.comments.set(data.comment.id, data.comment);
            this.emit('commentAdded', data.comment);
        }

        /**
         * Handle comment resolved event
         * @param {Object} data - Comment data
         */
        handleCommentResolved(data) {
            const comment = this.comments.get(data.commentId);
            if (comment) {
                comment.resolved = true;
                comment.resolvedBy = data.resolvedBy;
                comment.resolvedAt = data.timestamp;
                this.emit('commentResolved', comment);
            }
        }

        /**
         * Handle suggestion added event
         * @param {Object} data - Suggestion data
         */
        handleSuggestionAdded(data) {
            this.suggestions.set(data.suggestion.id, data.suggestion);
            this.emit('suggestionAdded', data.suggestion);
        }

        /**
         * Handle suggestion status event
         * @param {Object} data - Suggestion status data
         */
        handleSuggestionStatus(data) {
            const suggestion = this.suggestions.get(data.suggestionId);
            if (suggestion) {
                suggestion.status = data.status;
                suggestion.updatedBy = data.updatedBy;
                suggestion.updatedAt = data.timestamp;
                this.emit('suggestionStatusChanged', suggestion);
            }
        }

        /**
         * Handle version created event
         * @param {Object} data - Version data
         */
        handleVersionCreated(data) {
            this.versions.push(data.version);
            this.emit('versionCreated', data.version);
        }

        /**
         * Handle content changed event
         * @param {Object} data - Content change data
         */
        handleContentChanged(data) {
            // Don't process our own changes
            if (data.author === this.currentUser.id) {
                return;
            }

            this.emit('contentChanged', data.change);
        }

        /**
         * Add event listener
         * @param {string} event - Event name
         * @param {Function} callback - Callback function
         */
        addEventListener(event, callback) {
            if (this.eventListeners[event]) {
                this.eventListeners[event].push(callback);
            }
        }

        /**
         * Remove event listener
         * @param {string} event - Event name
         * @param {Function} callback - Callback function
         */
        removeEventListener(event, callback) {
            if (this.eventListeners[event]) {
                const index = this.eventListeners[event].indexOf(callback);
                if (index !== -1) {
                    this.eventListeners[event].splice(index, 1);
                }
            }
        }

        /**
         * Emit event
         * @param {string} event - Event name
         * @param {*} data - Event data
         */
        emit(event, data) {
            if (this.eventListeners[event]) {
                this.eventListeners[event].forEach(callback => {
                    try {
                        callback(data);
                    } catch (error) {
                        console.error('Event listener error:', error);
                    }
                });
            }
        }
    }

    // Export to global scope
    window.CollaborationEngine = CollaborationEngine;

    console.log('Collaboration Engine module loaded');

})(window);
