#!/usr/bin/env python3
"""
Create admin user for Railway deployment.
This script creates a user with username and password from environment variables.
"""

from app import create_app, db
from models import User

def create_admin():
    app = create_app()
    
    with app.app_context():
        # Create admin user with credentials: TheOnlyUser / TheOnlyPassword123!
        username = 'TheOnlyUser'
        password = 'TheOnlyPassword123!'
        
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        
        if existing_user:
            print(f"User '{username}' already exists. Updating password...")
            existing_user.set_password(password)
            existing_user.is_admin = True
            db.session.commit()
            print(f"✅ Password updated for user: {username}")
        else:
            print(f"Creating new admin user: {username}")
            admin = User(username=username, is_admin=True)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            print(f"✅ Admin user created: {username}")
        
        print(f"\nLogin credentials:")
        print(f"Username: {username}")
        print(f"Password: {password}")

if __name__ == '__main__':
    create_admin()
