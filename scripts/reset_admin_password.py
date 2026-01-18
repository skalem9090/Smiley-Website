#!/usr/bin/env python3
import argparse
import sys
import os

# Ensure project root is on sys.path when running this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User


def main():
    parser = argparse.ArgumentParser(description='Reset a user password')
    parser.add_argument('username', help='username to update')
    parser.add_argument('password', help='new password')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=args.username).first()
        if not user:
            print('User not found:', args.username)
            sys.exit(1)
        user.set_password(args.password)
        db.session.commit()
        print('Updated password for', args.username)


if __name__ == '__main__':
    main()
