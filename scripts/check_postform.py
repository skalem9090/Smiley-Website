#!/usr/bin/env python3
from app import create_app

app = create_app()
with app.app_context():
    from forms import PostForm
    print('PostForm category choices =', PostForm().category.choices)
