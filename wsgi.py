"""
WSGI entry point for Smileys Blog Site
This file provides the WSGI application object for production servers
"""

from app import create_app

# Create the Flask application instance
app = create_app()

if __name__ == "__main__":
    # This allows running the WSGI file directly for testing
    app.run(host='0.0.0.0', port=5000, debug=False)