#!/usr/bin/env python3
"""
Production startup script for Smiley's Blog
"""

import os
import sys
from pathlib import Path

def main():
    """Start the application in production mode"""
    
    # Set production environment
    os.environ['FLASK_ENV'] = 'production'
    
    # Check if .env file exists
    if not Path('.env').exists():
        print("❌ No .env file found!")
        print("Please run: python setup_env.py")
        sys.exit(1)
    
    # Import and run the app (dotenv will be loaded automatically)
    from app import create_app
    
    try:
        app = create_app()
        port = int(os.environ.get('PORT', 5000))
        
        print("🚀 Starting Smiley's Blog in production mode...")
        print(f"   Port: {port}")
        print(f"   Environment: {os.environ.get('FLASK_ENV', 'development')}")
        
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
        
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        print("Try running: python app.py")
        sys.exit(1)

if __name__ == '__main__':
    main()