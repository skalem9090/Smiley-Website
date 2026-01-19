#!/usr/bin/env python3
"""
Production startup script for Smileys Blog Site
This script starts the Flask application using the appropriate WSGI server for the platform
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def main():
    """Start the production server with the appropriate WSGI server"""
    
    # Ensure we're in the correct directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Virtual environment not detected!")
        print("   Consider activating your virtual environment first:")
        print("   venv\\Scripts\\activate  # Windows")
        print("   source venv/bin/activate  # Linux/Mac")
        print()
    
    # Check if .env file exists
    if not Path('.env').exists():
        print("❌ Error: .env file not found!")
        print("   Please create a .env file with your configuration.")
        print("   You can copy from .env.example if available.")
        return 1
    
    # Check if instance directory exists
    instance_dir = Path('instance')
    if not instance_dir.exists():
        print("📁 Creating instance directory...")
        instance_dir.mkdir(exist_ok=True)
    
    # Determine which WSGI server to use based on platform
    is_windows = platform.system() == 'Windows'
    server_name = "Waitress" if is_windows else "Gunicorn"
    
    print(f"🚀 Starting Smileys Blog Site with {server_name}...")
    print("📍 Server will be available at: http://localhost:5000")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        if is_windows:
            # Use Waitress for Windows
            cmd = [
                "waitress-serve",
                "--host=0.0.0.0",
                "--port=5000",
                "--threads=4",
                "--connection-limit=1000",
                "--cleanup-interval=30",
                "--channel-timeout=120",
                "wsgi:app"
            ]
        else:
            # Use Gunicorn for Unix-like systems
            cmd = [
                "gunicorn",
                "--config", "gunicorn_config.py",
                "wsgi:app"
            ]
        
        # Run the command
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting server: {e}")
        return 1
    except FileNotFoundError:
        server_cmd = "waitress-serve" if is_windows else "gunicorn"
        package_name = "waitress" if is_windows else "gunicorn"
        print(f"❌ Error: {server_cmd} not found!")
        print(f"   Please install it with: pip install {package_name}")
        return 1

if __name__ == "__main__":
    sys.exit(main())