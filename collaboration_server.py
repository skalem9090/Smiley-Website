"""
Advanced Editor System - Collaboration Server

WebSocket server for real-time collaboration features:
- Session management
- User presence tracking
- Comments and suggestions
- Version history
- Content synchronization

Validates Property 12: Collaboration Feature Integrity
Validates Property 13: Real-Time Collaboration Consistency
"""

from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from datetime import datetime
import uuid
import json

# Global storage (in production, use Redis or database)
sessions = {}
active_users = {}
comments = {}
suggestions = {}
versions = {}


def init_collaboration(app):
    """
    Initialize collaboration server with Flask app
    
    Args:
        app: Flask application instance
        
    Returns:
        SocketIO instance
    """
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        print(f'Client connected: {request.sid}')
        emit('connected', {'status': 'success'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print(f'Client disconnected: {request.sid}')
        
        # Remove user from all sessions
        for session_id, session in list(sessions.items()):
            if request.sid in session.get('clients', []):
                session['clients'].remove(request.sid)
                
                # Find user
                user = None
                for u in session.get('users', []):
                    if u.get('sid') == request.sid:
                        user = u
                        break
                
                if user:
                    session['users'].remove(user)
                    # Notify other users
                    emit('user:left', {
                        'userId': user['id'],
                        'timestamp': datetime.now().isoformat()
                    }, room=session_id, skip_sid=request.sid)
    
    @socketio.on('ping')
    def handle_ping(data):
        """Handle heartbeat ping"""
        emit('pong', {'timestamp': datetime.now().isoformat()})
    
    @socketio.on('session:start')
    def handle_session_start(data):
        """Start collaboration session"""
        document_id = data.get('documentId')
        user = data.get('user')
        
        if not document_id or not user:
            emit('error', {'message': 'Missing documentId or user'})
            return
        
        # Create or join session
        session_id = f'doc:{document_id}'
        
        if session_id not in sessions:
            sessions[session_id] = {
                'id': session_id,
                'documentId': document_id,
                'users': [],
                'clients': [],
                'createdAt': datetime.now().isoformat()
            }
        
        session = sessions[session_id]
        
        # Add user to session
        user['sid'] = request.sid
        user['joinedAt'] = datetime.now().isoformat()
        user['presence'] = {
            'cursor': None,
            'selection': None,
            'isActive': True,
            'color': generate_user_color(len(session['users']))
        }
        
        session['users'].append(user)
        session['clients'].append(request.sid)
        
        # Join room
        join_room(session_id)
        
        # Notify other users
        emit('user:joined', {
            'user': user,
            'timestamp': datetime.now().isoformat()
        }, room=session_id, skip_sid=request.sid)
        
        # Send response
        emit('response', {
            'id': data.get('id'),
            'data': {
                'sessionId': session_id,
                'activeUsers': [u for u in session['users'] if u['sid'] != request.sid]
            }
        })
    
    @socketio.on('session:end')
    def handle_session_end(data):
        """End collaboration session"""
        session_id = data.get('sessionId')
        
        if session_id in sessions:
            session = sessions[session_id]
            
            # Remove user
            user = None
            for u in session['users']:
                if u['sid'] == request.sid:
                    user = u
                    break
            
            if user:
                session['users'].remove(user)
                session['clients'].remove(request.sid)
                
                # Notify other users
                emit('user:left', {
                    'userId': user['id'],
                    'timestamp': datetime.now().isoformat()
                }, room=session_id, skip_sid=request.sid)
            
            # Leave room
            leave_room(session_id)
            
            # Clean up empty sessions
            if len(session['users']) == 0:
                del sessions[session_id]
    
    @socketio.on('presence:update')
    def handle_presence_update(data):
        """Update user presence"""
        session_id = data.get('sessionId')
        user_id = data.get('userId')
        
        if session_id in sessions:
            session = sessions[session_id]
            
            # Update user presence
            for user in session['users']:
                if user['id'] == user_id:
                    user['presence'].update({
                        'cursor': data.get('cursor'),
                        'selection': data.get('selection'),
                        'isActive': data.get('isActive', True),
                        'timestamp': data.get('timestamp')
                    })
                    break
            
            # Broadcast to other users
            emit('presence:updated', {
                'userId': user_id,
                'cursor': data.get('cursor'),
                'selection': data.get('selection'),
                'isActive': data.get('isActive', True),
                'timestamp': data.get('timestamp')
            }, room=session_id, skip_sid=request.sid)
    
    @socketio.on('comment:add')
    def handle_comment_add(data):
        """Add comment"""
        session_id = data.get('sessionId')
        block_id = data.get('blockId')
        content = data.get('content')
        author = data.get('author')
        parent_id = data.get('parentId')
        
        comment_id = str(uuid.uuid4())
        comment = {
            'id': comment_id,
            'blockId': block_id,
            'content': content,
            'author': author,
            'parentId': parent_id,
            'resolved': False,
            'createdAt': datetime.now().isoformat(),
            'replies': []
        }
        
        comments[comment_id] = comment
        
        # Broadcast to all users in session
        emit('comment:added', {
            'comment': comment,
            'timestamp': datetime.now().isoformat()
        }, room=session_id)
        
        # Send response
        emit('response', {
            'id': data.get('id'),
            'data': {'comment': comment}
        })
    
    @socketio.on('comment:resolve')
    def handle_comment_resolve(data):
        """Resolve comment"""
        session_id = data.get('sessionId')
        comment_id = data.get('commentId')
        resolved_by = data.get('resolvedBy')
        
        if comment_id in comments:
            comments[comment_id]['resolved'] = True
            comments[comment_id]['resolvedBy'] = resolved_by
            comments[comment_id]['resolvedAt'] = datetime.now().isoformat()
            
            # Broadcast to all users in session
            emit('comment:resolved', {
                'commentId': comment_id,
                'resolvedBy': resolved_by,
                'timestamp': datetime.now().isoformat()
            }, room=session_id)
            
            # Send response
            emit('response', {
                'id': data.get('id'),
                'data': {'success': True}
            })
    
    @socketio.on('suggestion:add')
    def handle_suggestion_add(data):
        """Add suggestion"""
        session_id = data.get('sessionId')
        block_id = data.get('blockId')
        suggestion_type = data.get('type')
        original_content = data.get('originalContent')
        suggested_content = data.get('suggestedContent')
        author = data.get('author')
        
        suggestion_id = str(uuid.uuid4())
        suggestion = {
            'id': suggestion_id,
            'blockId': block_id,
            'type': suggestion_type,
            'originalContent': original_content,
            'suggestedContent': suggested_content,
            'author': author,
            'status': 'pending',
            'createdAt': datetime.now().isoformat()
        }
        
        suggestions[suggestion_id] = suggestion
        
        # Broadcast to all users in session
        emit('suggestion:added', {
            'suggestion': suggestion,
            'timestamp': datetime.now().isoformat()
        }, room=session_id)
        
        # Send response
        emit('response', {
            'id': data.get('id'),
            'data': {'suggestion': suggestion}
        })
    
    @socketio.on('suggestion:status')
    def handle_suggestion_status(data):
        """Update suggestion status"""
        session_id = data.get('sessionId')
        suggestion_id = data.get('suggestionId')
        status = data.get('status')
        updated_by = data.get('updatedBy')
        
        if suggestion_id in suggestions:
            suggestions[suggestion_id]['status'] = status
            suggestions[suggestion_id]['updatedBy'] = updated_by
            suggestions[suggestion_id]['updatedAt'] = datetime.now().isoformat()
            
            # Broadcast to all users in session
            emit('suggestion:status', {
                'suggestionId': suggestion_id,
                'status': status,
                'updatedBy': updated_by,
                'timestamp': datetime.now().isoformat()
            }, room=session_id)
            
            # Send response
            emit('response', {
                'id': data.get('id'),
                'data': {'success': True}
            })
    
    @socketio.on('version:create')
    def handle_version_create(data):
        """Create version"""
        session_id = data.get('sessionId')
        document_id = data.get('documentId')
        description = data.get('description')
        blocks = data.get('blocks')
        author = data.get('author')
        
        version_id = str(uuid.uuid4())
        version = {
            'id': version_id,
            'documentId': document_id,
            'description': description,
            'blocks': blocks,
            'author': author,
            'createdAt': datetime.now().isoformat()
        }
        
        if document_id not in versions:
            versions[document_id] = []
        
        versions[document_id].append(version)
        
        # Broadcast to all users in session
        emit('version:created', {
            'version': version,
            'timestamp': datetime.now().isoformat()
        }, room=session_id)
        
        # Send response
        emit('response', {
            'id': data.get('id'),
            'data': {'version': version}
        })
    
    @socketio.on('version:restore')
    def handle_version_restore(data):
        """Restore version"""
        session_id = data.get('sessionId')
        version_id = data.get('versionId')
        
        # Find version
        version = None
        for doc_versions in versions.values():
            for v in doc_versions:
                if v['id'] == version_id:
                    version = v
                    break
            if version:
                break
        
        if version:
            # Send response
            emit('response', {
                'id': data.get('id'),
                'data': {'blocks': version['blocks']}
            })
    
    @socketio.on('version:history')
    def handle_version_history(data):
        """Get version history"""
        document_id = data.get('documentId')
        
        doc_versions = versions.get(document_id, [])
        
        # Send response
        emit('response', {
            'id': data.get('id'),
            'data': {'versions': doc_versions}
        })
    
    @socketio.on('content:change')
    def handle_content_change(data):
        """Broadcast content change"""
        session_id = data.get('sessionId')
        change = data.get('change')
        author = data.get('author')
        
        # Broadcast to all users except sender
        emit('content:changed', {
            'change': change,
            'author': author,
            'timestamp': datetime.now().isoformat()
        }, room=session_id, skip_sid=request.sid)
    
    return socketio


def generate_user_color(index):
    """
    Generate a color for user cursor/presence
    
    Args:
        index: User index
        
    Returns:
        Color hex string
    """
    colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A',
        '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2',
        '#F8B739', '#52B788', '#E76F51', '#2A9D8F'
    ]
    return colors[index % len(colors)]
