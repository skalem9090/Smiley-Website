# Deployment Configuration

## Environment Variables

The application supports the following environment variables for configuration:

- `SECRET_KEY`: Flask secret key for session security (required in production)
- `DATABASE_URL`: Database connection string (defaults to SQLite in instance/site.db)
- `ADMIN_USER`: Initial admin username (optional, for first-time setup)
- `ADMIN_PASSWORD`: Initial admin password (optional, for first-time setup)

## File Upload Configuration

- **Upload Directory**: `static/uploads/`
- **Supported Formats**: JPEG, PNG, GIF
- **Max File Size**: Configured in ImageHandler (default: 5MB)
- **Security**: Files are validated and renamed with UUIDs

## Background Tasks

The application uses APScheduler for background task processing:

- **Scheduled Post Publication**: Checks every minute for posts ready to publish
- **Automatic Startup**: Scheduler starts automatically with the Flask application
- **Error Handling**: Failed publications are retried with exponential backoff

## Database

- **Engine**: SQLite (development) or PostgreSQL (production via DATABASE_URL)
- **Migrations**: Managed with Flask-Migrate
- **Schema**: Enhanced with tags, images, and scheduling support

## Production Deployment

1. Set environment variables:
   ```bash
   export SECRET_KEY="your-secret-key-here"
   export DATABASE_URL="postgresql://user:pass@host:port/dbname"
   ```

2. Initialize database:
   ```bash
   flask db upgrade
   ```

3. Create admin user (if not using environment variables):
   ```bash
   python scripts/create_admin.py
   ```

4. Ensure upload directory permissions:
   ```bash
   mkdir -p static/uploads
   chmod 755 static/uploads
   ```

5. Start the application:
   ```bash
   python app.py
   ```

## Security Considerations

- CSRF protection enabled for all forms
- File upload validation and sanitization
- Content sanitization with bleach
- Admin-only access to management features
- Secure filename generation for uploads

## Monitoring

- Check scheduler status in application logs
- Monitor upload directory disk usage
- Verify database connectivity
- Test scheduled post publication functionality