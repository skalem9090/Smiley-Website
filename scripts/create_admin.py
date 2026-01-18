#!/usr/bin/env python3
import argparse
import getpass
import sys
import os

# Ensure project root is on sys.path when running this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User


def main():
    parser = argparse.ArgumentParser(description='Create an admin user')
    parser.add_argument('username', nargs='?', help='username for the admin')
    parser.add_argument('password', nargs='?', help='password for the admin (optional)')
    args = parser.parse_args()

    username = args.username
    password = args.password

    if not username:
        username = input('Username: ').strip()
        if not username:
            print('Username is required')
            sys.exit(1)

    if not password:
        password = getpass.getpass('Password: ')
        if not password:
            print('Password is required')
            sys.exit(1)

    app = create_app()
    with app.app_context():
        # Only allow creating the single initial admin if no users exist.
        if User.query.count() > 0:
            print('An account already exists. This application supports a single developer account.')
            print('Use the reset_admin_password.py script to update the existing developer password.')
            sys.exit(1)
        if User.query.filter_by(username=username).first():
            print('User already exists:', username)
            sys.exit(1)
        u = User(username=username, is_admin=True)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        print('Created admin', username)


if __name__ == '__main__':
    main()
