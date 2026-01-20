# Authentication & Authorization Overview

## Summary

Your blog application uses **Flask-Login** for session-based authentication with a **single-user admin model**. The system is designed for a personal blog where only the admin (developer) can create and manage content, while the public can view published content and submit comments.

---

## Authentication System

### Technology Stack
- **Flask-Login**: Session management and user authentication
- **Werkzeug Security**: Password hashing (PBKDF2 with SHA-256)
- **Flask-WTF**: CSRF protection for all forms
- **SQLite**: User credential storage

### User Model (`models.py`)

```python
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
```

**Key Features:**
- Passwords are **never stored in plain text**
- Uses `generate_password_hash()` with default PBKDF2-SHA256
- `UserMixin` provides Flask-Login integration (is_authenticated, is_active, etc.)
- `is_admin` flag for authorization checks

### Login Flow (`app.py`)

```python
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_admin:
                flash('Unauthorized: developer access only', 'danger')
            else:
                login_user(user)
                return redirect(request.args.get('next') or url_for('index'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html', form=form)
```

**Security Features:**
1. **CSRF Protection**: All forms protected by Flask-WTF
2. **Admin-Only Access**: Non-admin users are rejected even with valid credentials
3. **Password Validation**: Minimum 6 characters (enforced in `LoginForm`)
4. **Secure Hashing**: Werkzeug's password hashing with salt
5. **Session Management**: Flask-Login handles secure session cookies

### Initial Admin Setup

On first run, the app automatically creates an admin user if none exists:

```python
with app.app_context():
    db.create_all()
    if User.query.count() == 0:
        admin_user = os.environ.get('ADMIN_USER')
        admin_pass = os.environ.get('ADMIN_PASSWORD')
        if admin_user and admin_pass:
            u = User(username=admin_user, is_admin=True)
            u.set_password(admin_pass)
            db.session.add(u)
            db.session.commit()
```

**Configuration** (`.env` file):
```
ADMIN_USER=your_username
ADMIN_PASSWORD=your_secure_password
```

---

## Authorization System

### Access Control Model

The application uses a **simple role-based access control (RBAC)** with two roles:

1. **Admin** (`is_admin=True`): Full access to all features
2. **Public** (unauthenticated): Read-only access to published content

### Protected Routes

All admin routes use the `@login_required` decorator:

```python
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    # Only accessible to logged-in users
    ...

@app.route('/dashboard/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    if not current_user.is_admin:
        abort(403)  # Additional admin check
    ...
```

### Authorization Checks

**Two-Level Protection:**

1. **Route Level**: `@login_required` decorator
   - Redirects to login page if not authenticated
   - Configured via `login_manager.login_view = 'login'`

2. **Function Level**: `current_user.is_admin` checks
   - Additional verification inside route handlers
   - Returns 403 Forbidden for non-admin users

### Protected Features

| Feature | Authentication | Authorization |
|---------|---------------|---------------|
| View published posts | ❌ None | Public |
| View draft posts | ✅ Required | Admin only |
| Create/edit posts | ✅ Required | Admin only |
| Delete posts | ✅ Required | Admin only |
| Upload images | ✅ Required | Admin only |
| Manage comments | ✅ Required | Admin only |
| Author profile | ✅ Required | Admin only |
| Newsletter management | ✅ Required | Admin only |
| Media library | ✅ Required | Admin only |
| System health | ✅ Required | Admin only |
| Submit comments | ❌ None | Public |
| Subscribe to newsletter | ❌ None | Public |

---

## Security Measures

### 1. CSRF Protection

```python
csrf = CSRFProtect(app)
```

- **All forms** are protected against Cross-Site Request Forgery
- CSRF tokens automatically added to forms via `{{ form.hidden_tag() }}`
- API endpoints require CSRF token in headers: `X-CSRFToken`

### 2. Password Security

- **Hashing Algorithm**: PBKDF2-HMAC-SHA256 (Werkzeug default)
- **Salt**: Automatically generated per password
- **Minimum Length**: 6 characters (enforced in form validation)
- **No Plain Text**: Passwords never stored or logged

### 3. Content Sanitization

```python
def sanitize_content(content):
    """Sanitize HTML content for safe storage."""
    ALLOWED_TAGS = ['a', 'abbr', 'b', 'blockquote', 'br', 'code', 'em', 
                    'i', 'li', 'ol', 'p', 'strong', 'ul', 'h1', 'h2', 
                    'h3', 'h4', 'img']
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title', 'rel', 'target'],
        'img': ['src', 'alt', 'title', 'width', 'height', 'style', 'class']
    }
    return bleach.clean(content, tags=ALLOWED_TAGS, 
                       attributes=ALLOWED_ATTRIBUTES, strip=True)
```

- **XSS Prevention**: All user-submitted content is sanitized
- **Whitelist Approach**: Only allowed HTML tags and attributes
- Applied to: Post content, comments, author bio

### 4. Session Security

```python
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
```

- **Secret Key**: Used for signing session cookies
- **Should be set** in production via environment variable
- **Session Cookies**: HTTPOnly by default (Flask-Login)

### 5. File Upload Security

```python
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
```

- **Size Limit**: 16MB maximum file size
- **Type Validation**: Only image files allowed (JPEG, PNG, GIF, WebP)
- **Filename Sanitization**: Secure filenames generated
- **Admin-Only**: Only authenticated admins can upload

### 6. Comment Spam Protection

```python
# Tracks IP address and user agent for spam detection
ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', 
                                 request.environ.get('REMOTE_ADDR'))
user_agent = request.headers.get('User-Agent')
```

- **Moderation Required**: Comments require admin approval
- **Spam Flagging**: Comments can be marked as spam
- **IP Tracking**: For abuse prevention
- **Email Validation**: Required for comment submission

---

## Security Gaps & Recommendations

### Current Limitations

1. **No Rate Limiting**
   - Login attempts are not rate-limited
   - Could be vulnerable to brute force attacks
   - **Recommendation**: Add Flask-Limiter

2. **No Account Lockout**
   - Failed login attempts don't lock accounts
   - **Recommendation**: Implement temporary lockout after N failed attempts

3. **No Two-Factor Authentication (2FA)**
   - Single-factor authentication only
   - **Recommendation**: Add TOTP-based 2FA for admin account

4. **Session Timeout**
   - No explicit session timeout configured
   - **Recommendation**: Set `PERMANENT_SESSION_LIFETIME`

5. **No Password Complexity Requirements**
   - Only minimum length enforced (6 chars)
   - **Recommendation**: Require uppercase, lowercase, numbers, symbols

6. **No HTTPS Enforcement**
   - Application doesn't force HTTPS
   - **Recommendation**: Use Flask-Talisman or reverse proxy (nginx)

7. **No Security Headers**
   - Missing headers like CSP, X-Frame-Options, etc.
   - **Recommendation**: Add Flask-Talisman for security headers

8. **Single Admin Account**
   - No multi-user support
   - No audit logging of admin actions
   - **Recommendation**: Add action logging for compliance

### Recommended Improvements

```python
# Example: Add rate limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Max 5 login attempts per minute
def login():
    ...

# Example: Add security headers
from flask_talisman import Talisman

Talisman(app, 
    force_https=True,
    strict_transport_security=True,
    content_security_policy={
        'default-src': "'self'",
        'img-src': ['*', 'data:'],
        'script-src': ["'self'", "'unsafe-inline'"],
        'style-src': ["'self'", "'unsafe-inline'", 'fonts.googleapis.com']
    }
)

# Example: Add session timeout
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# Example: Add password complexity
from wtforms.validators import Regexp

class LoginForm(FlaskForm):
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=12, max=128),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])',
               message='Password must contain uppercase, lowercase, number, and special character')
    ])
```

---

## Password Reset

**Currently NOT Implemented**

The application does not have a password reset mechanism. To reset the admin password:

1. **Use the reset script**: `scripts/reset_admin_password.py`
2. **Or manually via Python shell**:
   ```python
   from app import create_app
   from models import db, User
   
   app = create_app()
   with app.app_context():
       user = User.query.filter_by(username='admin').first()
       user.set_password('new_password')
       db.session.commit()
   ```

**Recommendation**: Implement email-based password reset with:
- Secure token generation
- Time-limited reset links
- Email verification

---

## API Security

### API Endpoints

The application has several API endpoints for AJAX functionality:

```python
@app.route('/api/upload-editor-image', methods=['POST'])
@login_required
def upload_editor_image():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    ...

@app.route('/api/editor-images')
@login_required
def get_editor_images():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    ...
```

**Security Features:**
- All API endpoints require authentication
- Admin-only access enforced
- CSRF token required for POST requests
- JSON error responses

---

## Environment Variables

**Required for Production:**

```bash
# .env file
SECRET_KEY=your-very-long-random-secret-key-here
ADMIN_USER=your_admin_username
ADMIN_PASSWORD=your_secure_password
DATABASE_URL=sqlite:///path/to/database.db
SENDGRID_API_KEY=your_sendgrid_key  # For email features
```

**Security Notes:**
- Never commit `.env` file to version control
- Use strong, random SECRET_KEY (32+ characters)
- Use strong admin password (12+ characters, mixed case, numbers, symbols)
- Rotate SECRET_KEY if compromised (invalidates all sessions)

---

## Deployment Security Checklist

- [ ] Set strong `SECRET_KEY` in production
- [ ] Use HTTPS (SSL/TLS certificate)
- [ ] Set secure session cookie flags
- [ ] Enable security headers (CSP, HSTS, etc.)
- [ ] Implement rate limiting
- [ ] Add session timeout
- [ ] Use strong admin password
- [ ] Keep dependencies updated
- [ ] Enable database backups
- [ ] Monitor failed login attempts
- [ ] Set up logging and monitoring
- [ ] Use environment variables for secrets
- [ ] Disable debug mode in production
- [ ] Use a production WSGI server (Gunicorn, uWSGI)
- [ ] Set up firewall rules
- [ ] Regular security audits

---

## Conclusion

Your blog application has a **solid foundation** for authentication and authorization:

✅ **Strengths:**
- Secure password hashing
- CSRF protection
- Content sanitization
- Admin-only access control
- Session management

⚠️ **Areas for Improvement:**
- Rate limiting
- Account lockout
- 2FA support
- Security headers
- Password complexity
- Session timeout
- Audit logging

For a **personal blog**, the current security is adequate. For **production use** or **multi-user scenarios**, implement the recommended improvements above.
