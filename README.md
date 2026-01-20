# Smileys Blog - Comprehensive Flask Blog Platform

A feature-rich blog platform built with Flask, focusing on wealth, health, and happiness content. This project implements a complete content management system with advanced features including RSS/Atom feeds, author profiles, tag management, post scheduling, and comprehensive testing.

## 🚀 Features

### Core Blog Functionality
- **Content Management**: Create, edit, and organize blog posts with rich HTML content
- **Post Scheduling**: Schedule posts for future publication with automatic publishing
- **Tag System**: Comprehensive tagging with slug-based URLs and tag management
- **Image Management**: Upload, organize, and manage images with automatic processing
- **Post Status Organization**: Draft, published, and scheduled post management

### Author & Profile System
- **Author Profiles**: Complete author information with bio, mission statement, and expertise areas
- **About Page**: Dedicated author page with social media integration
- **Profile Image Management**: Upload and manage author profile images

### RSS/Atom Feeds
- **RSS 2.0 & Atom 1.0**: Standards-compliant feed generation
- **Feed Discovery**: Automatic feed discovery links in HTML
- **Content Filtering**: Only published posts appear in feeds
- **Metadata Integration**: Author and post metadata in feeds

### Advanced Features
- **Property-Based Testing**: Comprehensive test suite with property-based testing using Hypothesis
- **Database Migrations**: Alembic-based database schema management
- **Background Scheduling**: APScheduler for automated post publishing
- **Image Processing**: PIL-based image optimization and resizing

### Security Features
- **Rate Limiting**: Configurable rate limits on login, admin, and password reset endpoints
- **Account Lockout**: Automatic account lockout after failed login attempts with configurable duration
- **Two-Factor Authentication (2FA)**: TOTP-based 2FA with QR code setup and backup codes
- **Session Management**: Configurable session timeouts with automatic expiration
- **Password Validation**: Enforced password complexity requirements
- **Security Headers**: Comprehensive security headers including CSP, HSTS, X-Frame-Options
- **HTTPS Enforcement**: Automatic HTTPS redirect in production environments
- **Audit Logging**: Complete audit trail of admin actions and security events
- **Security Dashboard**: Admin interface for viewing audit logs and login attempts

## 📋 Requirements

- Python 3.8+
- Flask 2.3+
- SQLAlchemy 2.0+
- See `requirements.txt` for complete dependencies

## 🛠️ Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd smileys-blog
```

2. **Create and activate a virtual environment:**
```powershell
# Windows
python -m venv venv
venv\Scripts\Activate.ps1

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

3. **Install dependencies:**
```powershell
pip install -r requirements.txt
```

4. **Set up the database:**
```powershell
# Initialize database migrations (if needed)
flask db init

# Run migrations
flask db upgrade
```

5. **Create an admin user:**
```powershell
python scripts/create_admin.py
```

6. **Run the application:**
```powershell
python app.py
```

Open http://127.0.0.1:5000/ in your browser.

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///instance/site.db
ADMIN_USER=admin
ADMIN_PASSWORD=your-admin-password
SITE_URL=http://localhost:5000
```

### Configuration Options

- `SECRET_KEY`: Flask secret key for sessions and CSRF protection
- `DATABASE_URL`: Database connection string
- `UPLOAD_FOLDER`: Directory for uploaded files (default: static/uploads)
- `MAX_CONTENT_LENGTH`: Maximum file upload size
- `SITE_URL`: Base URL for RSS feeds and absolute links

### Security Configuration

Configure security features via environment variables in your `.env` file:

#### Rate Limiting
```env
# Maximum login attempts per minute (default: 5)
RATE_LIMIT_LOGIN=5

# Maximum admin requests per minute (default: 30)
RATE_LIMIT_ADMIN=30

# Maximum password reset requests per hour (default: 3)
RATE_LIMIT_PASSWORD_RESET=3
```

#### Account Lockout
```env
# Failed login attempts before lockout (default: 5)
ACCOUNT_LOCKOUT_THRESHOLD=5

# Lockout duration in minutes (default: 30)
ACCOUNT_LOCKOUT_DURATION=30
```

#### Session Management
```env
# Session timeout in minutes (default: 30)
SESSION_TIMEOUT_MINUTES=30
```

#### Password Requirements
```env
# Minimum password length (default: 12)
PASSWORD_MIN_LENGTH=12

# Require uppercase letters (default: true)
PASSWORD_REQUIRE_UPPERCASE=true

# Require lowercase letters (default: true)
PASSWORD_REQUIRE_LOWERCASE=true

# Require digits (default: true)
PASSWORD_REQUIRE_DIGIT=true

# Require special characters (default: true)
PASSWORD_REQUIRE_SPECIAL=true
```

#### HTTPS and Security Headers
```env
# Enforce HTTPS in production (default: false)
FORCE_HTTPS=true

# Enable strict transport security (default: false)
ENABLE_HSTS=true

# HSTS max age in seconds (default: 31536000 = 1 year)
HSTS_MAX_AGE=31536000
```

#### Two-Factor Authentication
```env
# Application name for 2FA (appears in authenticator apps)
APP_NAME=Smileys Blog
```

See `.env.example` for a complete list of configuration options with detailed comments.

## 📖 Usage

### Admin Dashboard

Access the admin dashboard at `/dashboard` (requires login):
- Create and manage blog posts
- Upload and organize images
- Manage author profile information
- View post statistics and organization
- Access security dashboard (audit logs and login attempts)
- **Settings page** - Centralized security and account management:
  - Account information and status
  - Two-factor authentication management
  - Password change and requirements
  - Active session management
  - Security audit logs preview
  - Quick access to all security features

### Security Features

#### Two-Factor Authentication (2FA)

Enable 2FA for enhanced account security:

1. Log in to your account
2. Navigate to `/setup-2fa`
3. Scan the QR code with an authenticator app (Google Authenticator, Authy, etc.)
4. Enter the 6-digit code to verify
5. Save your backup codes in a secure location

To disable 2FA:
1. Navigate to `/disable-2fa`
2. Enter your current password
3. Enter a valid 2FA code
4. Confirm the action

#### Security Dashboard

Admin users can access security monitoring at:
- **Audit Logs**: `/security/audit-logs` - View all admin actions and security events
- **Login Attempts**: `/security/login-attempts` - Monitor login attempts and failures

Features:
- Filter by date range, user, and action type
- Pagination for large datasets
- Export logs as CSV
- Real-time monitoring of security events

#### Password Management

Password requirements are enforced on account creation and password changes:
- Minimum 12 characters (configurable)
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character

Change your password at `/change-password` (requires current password).

### Content Management

1. **Creating Posts**: Use the dashboard to create new posts with rich HTML content
2. **Scheduling**: Set future publication dates for automatic publishing
3. **Tags**: Add comma-separated tags for better organization
4. **Images**: Upload images directly through the post editor

### RSS/Atom Feeds

- RSS Feed: `/feed.xml` or `/rss.xml`
- Atom Feed: `/atom.xml`
- Feed discovery links are automatically included in all pages

## 🧪 Testing

The project includes comprehensive testing with both unit tests and property-based tests:

```powershell
# Run all tests
python -m pytest

# Run specific test files
python -m pytest test_author_information_consistency.py
python -m pytest test_rss_atom_feeds.py

# Run integration tests
python integration_test.py
```

### Property-Based Testing

The project uses Hypothesis for property-based testing to ensure correctness across a wide range of inputs:

- Author information consistency
- RSS/Atom feed generation
- Tag management and filtering
- Post scheduling and publication

## 📁 Project Structure

```
smileys-blog/
├── .kiro/                          # Kiro specs and configuration
│   └── specs/                      # Feature specifications
├── static/                         # Static assets
│   ├── css/                        # Stylesheets
│   └── uploads/                    # Uploaded images
├── templates/                      # Jinja2 templates
├── migrations/                     # Database migrations
├── scripts/                        # Utility scripts
├── app.py                          # Main Flask application
├── models.py                       # Database models
├── forms.py                        # WTForms definitions
├── feed_generator.py               # RSS/Atom feed generation
├── about_page_manager.py           # Author profile management
├── post_manager.py                 # Post management logic
├── tag_manager.py                  # Tag management system
├── image_handler.py                # Image upload and processing
├── schedule_manager.py             # Background task scheduling
└── test_*.py                       # Test files
```

## 🔄 Database Migrations

The project uses Alembic for database migrations:

```powershell
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Downgrade migrations
flask db downgrade
```

## 🚀 Deployment

### Quick Deploy (30 Minutes)

Your application is **production-ready** with complete deployment guides!

```bash
# 1. Generate secure configuration
python setup_production.py

# 2. Deploy to Railway (recommended)
# See QUICK_DEPLOY.md for 4-command deployment

# 3. Configure email service (SendGrid free tier)
# 4. Set up custom domain (optional)
# 5. Enable 2FA and create content
```

### Deployment Resources

- **Quick Start**: `QUICK_DEPLOY.md` - Deploy in 4 commands
- **Complete Guide**: `DEPLOYMENT_GUIDE.md` - Step-by-step with Railway/Heroku
- **Setup Helper**: `python setup_production.py` - Interactive configuration
- **Production Summary**: `PRODUCTION_READY_SUMMARY.md` - Everything you need

### What's Included

✅ **PostgreSQL Setup** - Production database configuration  
✅ **Email Service** - SendGrid/Mailgun integration with Flask-Mail  
✅ **SSL Certificates** - Automatic HTTPS with Railway/Heroku  
✅ **Environment Config** - Secure key generation and validation  
✅ **Domain Setup** - Custom domain configuration guide  
✅ **Security Hardening** - All security features pre-configured  
✅ **Monitoring** - Sentry and uptime monitoring setup  

### Deployment Options

1. **Railway** (Recommended)
   - Free PostgreSQL included
   - Automatic SSL certificates
   - Git-based deployments
   - $5/month after free tier

2. **Heroku**
   - Well-documented platform
   - Add-ons for PostgreSQL and email
   - $7/month for basic dyno

3. **DigitalOcean App Platform**
   - Full control
   - Managed databases
   - $12/month

### Security Hardening Checklist

Your app includes enterprise-grade security features:

✅ Two-Factor Authentication (TOTP)  
✅ Account lockout after failed attempts  
✅ Session management with timeouts  
✅ Password complexity requirements  
✅ Security headers (CSP, HSTS, X-Frame-Options)  
✅ Audit logging for all admin actions  
✅ Rate limiting on sensitive endpoints  
✅ HTTPS enforcement  
✅ CSRF protection  

**Before deploying:**
- [ ] Run `python setup_production.py` to generate secure keys
- [ ] Configure email service (SendGrid recommended)
- [ ] Set environment variables in hosting platform
- [ ] Enable 2FA after first login
- [ ] Create initial content

See `DEPLOYMENT_GUIDE.md` for complete security setup instructions.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write tests for new features
- Update documentation as needed
- Use property-based testing for complex logic

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Flask framework and ecosystem
- Hypothesis for property-based testing
- feedgen for RSS/Atom feed generation
- All contributors and testers

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation in the `.kiro/specs/` directory
- Review the test files for usage examples
