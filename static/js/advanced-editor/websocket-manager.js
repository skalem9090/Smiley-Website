/**
 * Advanced Editor System - WebSocket Manager
 * 
 * Manages WebSocket connections for real-time collaboration features:
 * - Connection lifecycle management
 * - Message routing and handling
 * - Reconnection logic with exponential backoff
 * - Heartbeat/ping-pong for connection health
 * - Event-based message distribution
 * 
 * Validates Property 12: Collaboration Feature Integrity
 * Validates Property 13: Real-Time Collaboration Consistency
 */

(function(window) {
    'use strict';

    /**
     * WebSocket Manager
     * Handles WebSocket connections for real-time collaboration
     */
    class WebSocketManager {
        constructor(config = {}) {
            this.config = {
                url: config.url || this.getWebSocketUrl(),
                reconnectInterval: config.reconnectInterval || 1000,
                maxReconnectInterval: config.maxReconnectInterval || 30000,
                reconnectDecay: config.reconnectDecay || 1.5,
                heartbeatInterval: config.heartbeatInterval || 30000,
                messageTimeout: config.messageTimeout || 5000,
                ...config
            };

            this.socket = null;
            this.isConnected = false;
            this.reconnectAttempts = 0;
            this.reconnectTimer = null;
            this.heartbeatTimer = null;
            this.messageHandlers = new Map();
            this.pendingMessages = [];
            this.messageCallbacks = new Map();
            this.messageId = 0;

            // Event listeners
            this.eventListeners = {
                'connected': [],
                'disconnected': [],
                'error': [],
                'message': [],
                'reconnecting': []
            };
        }

        /**
         * Get WebSocket URL based on current location
         * @returns {string} WebSocket URL
         */
        getWebSocketUrl() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            return `${protocol}//${host}/ws/collaboration`;
        }

        /**
         * Connect to WebSocket server
         * @param {Object} auth - Authentication data
         * @returns {Promise<void>}
         */
        connect(auth = {}) {
            return new Promise((resolve, reject) => {
                if (this.socket && this.isConnected) {
                    resolve();
                    return;
                }

                try {
                    const url = new URL(this.config.url);
                    if (auth.token) {
                        url.searchParams.set('token', auth.token);
                    }

                    this.socket = new WebSocket(url.toString());

                    this.socket.onopen = () => {
                        this.handleOpen();
                        resolve();
                    };

                    this.socket.onclose = (event) => {
                        this.handleClose(event);
                    };

                    this.socket.onerror = (error) => {
                        this.handleError(error);
                        reject(error);
                    };

                    this.socket.onmessage = (event) => {
                        this.handleMessage(event);
                    };

                } catch (error) {
                    console.error('WebSocket connection error:', error);
                    reject(error);
                }
            });
        }

        /**
         * Disconnect from WebSocket server
         */
        disconnect() {
            if (this.socket) {
                this.socket.close(1000, 'Client disconnect');
                this.socket = null;
            }

            this.stopHeartbeat();
            this.stopReconnect();
            this.isConnected = false;
        }

        /**
         * Handle WebSocket open event
         */
        handleOpen() {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.reconnectAttempts = 0;

            // Send pending messages
            this.flushPendingMessages();

            // Start heartbeat
            this.startHeartbeat();

            // Emit connected event
            this.emit('connected');
        }

        /**
         * Handle WebSocket close event
         * @param {CloseEvent} event - Close event
         */
        handleClose(event) {
            console.log('WebSocket closed:', event.code, event.reason);
            this.isConnected = false;
            this.stopHeartbeat();

            // Emit disconnected event
            this.emit('disconnected', { code: event.code, reason: event.reason });

            // Attempt reconnection if not a normal closure
            if (event.code !== 1000 && event.code !== 1001) {
                this.scheduleReconnect();
            }
        }

        /**
         * Handle WebSocket error event
         * @param {Event} error - Error event
         */
        handleError(error) {
            console.error('WebSocket error:', error);
            this.emit('error', error);
        }

        /**
         * Handle incoming WebSocket message
         * @param {MessageEvent} event - Message event
         */
        handleMessage(event) {
            try {
                const message = JSON.parse(event.data);
                
                // Handle heartbeat response
                if (message.type === 'pong') {
                    return;
                }

                // Handle message response (for request/response pattern)
                if (message.id && this.messageCallbacks.has(message.id)) {
                    const callback = this.messageCallbacks.get(message.id);
                    this.messageCallbacks.delete(message.id);
                    callback(null, message);
                    return;
                }

                // Route message to registered handlers
                if (this.messageHandlers.has(message.type)) {
                    const handlers = this.messageHandlers.get(message.type);
                    handlers.forEach(handler => {
                        try {
                            handler(message.data, message);
                        } catch (error) {
                            console.error('Message handler error:', error);
                        }
                    });
                }

                // Emit generic message event
                this.emit('message', message);

            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        }

        /**
         * Send message through WebSocket
         * @param {string} type - Message type
         * @param {*} data - Message data
         * @param {boolean} expectResponse - Whether to expect a response
         * @returns {Promise<*>} Response data if expectResponse is true
         */
        send(type, data, expectResponse = false) {
            const message = {
                type: type,
                data: data,
                timestamp: Date.now()
            };

            if (expectResponse) {
                message.id = ++this.messageId;
                
                return new Promise((resolve, reject) => {
                    // Set timeout for response
                    const timeout = setTimeout(() => {
                        this.messageCallbacks.delete(message.id);
                        reject(new Error('Message timeout'));
                    }, this.config.messageTimeout);

                    // Store callback
                    this.messageCallbacks.set(message.id, (error, response) => {
                        clearTimeout(timeout);
                        if (error) {
                            reject(error);
                        } else {
                            resolve(response.data);
                        }
                    });

                    // Send message
                    this.sendMessage(message);
                });
            } else {
                this.sendMessage(message);
                return Promise.resolve();
            }
        }

        /**
         * Send message (internal)
         * @param {Object} message - Message object
         */
        sendMessage(message) {
            if (this.isConnected && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(JSON.stringify(message));
            } else {
                // Queue message for later
                this.pendingMessages.push(message);
            }
        }

        /**
         * Flush pending messages
         */
        flushPendingMessages() {
            while (this.pendingMessages.length > 0) {
                const message = this.pendingMessages.shift();
                this.sendMessage(message);
            }
        }

        /**
         * Register message handler
         * @param {string} type - Message type
         * @param {Function} handler - Handler function
         */
        on(type, handler) {
            if (!this.messageHandlers.has(type)) {
                this.messageHandlers.set(type, []);
            }
            this.messageHandlers.get(type).push(handler);
        }

        /**
         * Unregister message handler
         * @param {string} type - Message type
         * @param {Function} handler - Handler function
         */
        off(type, handler) {
            if (this.messageHandlers.has(type)) {
                const handlers = this.messageHandlers.get(type);
                const index = handlers.indexOf(handler);
                if (index !== -1) {
                    handlers.splice(index, 1);
                }
            }
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

        /**
         * Schedule reconnection attempt
         */
        scheduleReconnect() {
            if (this.reconnectTimer) {
                return;
            }

            const interval = Math.min(
                this.config.reconnectInterval * Math.pow(this.config.reconnectDecay, this.reconnectAttempts),
                this.config.maxReconnectInterval
            );

            console.log(`Reconnecting in ${interval}ms (attempt ${this.reconnectAttempts + 1})`);
            this.emit('reconnecting', { attempt: this.reconnectAttempts + 1, interval });

            this.reconnectTimer = setTimeout(() => {
                this.reconnectTimer = null;
                this.reconnectAttempts++;
                this.connect().catch(error => {
                    console.error('Reconnection failed:', error);
                });
            }, interval);
        }

        /**
         * Stop reconnection attempts
         */
        stopReconnect() {
            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }
        }

        /**
         * Start heartbeat
         */
        startHeartbeat() {
            this.stopHeartbeat();
            
            this.heartbeatTimer = setInterval(() => {
                if (this.isConnected) {
                    this.send('ping', { timestamp: Date.now() });
                }
            }, this.config.heartbeatInterval);
        }

        /**
         * Stop heartbeat
         */
        stopHeartbeat() {
            if (this.heartbeatTimer) {
                clearInterval(this.heartbeatTimer);
                this.heartbeatTimer = null;
            }
        }

        /**
         * Get connection status
         * @returns {Object} Connection status
         */
        getStatus() {
            return {
                connected: this.isConnected,
                readyState: this.socket ? this.socket.readyState : WebSocket.CLOSED,
                reconnectAttempts: this.reconnectAttempts,
                pendingMessages: this.pendingMessages.length
            };
        }
    }

    // Export to global scope
    window.WebSocketManager = WebSocketManager;

    console.log('WebSocket Manager module loaded');

})(window);
