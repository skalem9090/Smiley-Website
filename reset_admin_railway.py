#!/usr/bin/env python3
"""
Reset admin password on Railway.
Run this with: railway run python reset_admin_railway.py
"""

import sys
import os

# Ensure we're using the app context
from app import create_app, db
from models import User

def reset_admin_password():
    """Reset the admin user password."""
    app = create_app()
    
    with app.app_context():
        # Find admin user
        admin = User.query.filter_by(username='admin').first()
        
        if not admin:
            print("❌ Admin user not found!")
            print("Creating new admin user...")
            admin = User(username='admin', is_admin=True)
            db.session.add(admin)
        
        # Get new password from environment or use default
        new_password = os.environ.get('NEW_ADMIN_PASSWORD', 'Admin123!')
        
        # Set the password
        admin.set_password(new_password)
        db.session.commit()
        
        print("✅ Admin password has been reset!")
        print(f"Username: admin")
        print(f"Password: {new_password}")
        print("\nYou can now log in with these credentials.")

if __name__ == '__main__':
    reset_admin_password()
