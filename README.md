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
- **Security**: CSRF protection, content sanitization, and secure file uploads

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

## 📖 Usage

### Admin Dashboard

Access the admin dashboard at `/dashboard` (requires login):
- Create and manage blog posts
- Upload and organize images
- Manage author profile information
- View post statistics and organization

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

### Production Considerations

1. **Environment Variables**: Set production values for all environment variables
2. **Database**: Use PostgreSQL or MySQL for production
3. **Web Server**: Use Gunicorn or uWSGI with Nginx
4. **Static Files**: Configure proper static file serving
5. **Security**: Enable HTTPS and set secure headers

### Example Production Setup

```bash
# Install production dependencies
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

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
