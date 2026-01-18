import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from models import User

app = create_app()
with app.app_context():
    print('USER_COUNT=', User.query.count())
    for u in User.query.all():
        print('USER:', u.username, 'is_admin=', u.is_admin)
