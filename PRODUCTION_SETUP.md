# Production Server Setup Guide

This guide explains how to run Smileys Blog Site using a production-ready WSGI server.

## 🚀 Quick Start

### Windows (Recommended)
```bash
# Option 1: Use the Python script
python start_production.py

# Option 2: Use the batch file
start_production.bat

# Option 3: Use PowerShell
.\start_production.ps1
```

### Linux/Mac
```bash
# The script will automatically use Gunicorn on Unix systems
python start_production.py
```

### Manual Start (Advanced)
```bash
# Windows - using Waitress
waitress-serve --host=0.0.0.0 --port=5000 --threads=4 wsgi:app

# Linux/Mac - using Gunicorn
gunicorn --config gunicorn_config.py wsgi:app
```

## 📋 Prerequisites

1. **Python Environment**: Ensure you have Python 3.8+ installed
2. **Dependencies**: Install required packages
   ```bash
   pip install -r requirements-clean.txt
   ```
3. **Environment File**: Create a `.env` file with your configuration
4. **Database**: Ensure the `instance/` directory exists

## 🔧 WSGI Servers

### Waitress (Windows)
- **Pros**: Cross-platform, pure Python, reliable
- **Cons**: Single-threaded per worker
- **Best for**: Windows development and small-scale production

### Gunicorn (Linux/Mac)
- **Pros**: Multi-worker, battle-tested, highly configurable
- **Cons**: Unix-only (doesn't work on Windows)
- **Best for**: Linux/Mac production deployments

## ⚙️ Configuration

### Waitress Configuration
The production script uses these Waitress settings:
- **Host**: `0.0.0.0` (all interfaces)
- **Port**: `5000`
- **Threads**: `4`
- **Connection Limit**: `1000`
- **Cleanup Interval**: `30` seconds
- **Channel Timeout**: `120` seconds

### Gunicorn Configuration
Settings are defined in `gunicorn_config.py`:
- **Workers**: `4`
- **Worker Class**: `sync`
- **Timeout**: `30` seconds
- **Max Requests**: `1000` (with jitter)
- **Logging**: Stdout/stderr

## 🌐 Accessing Your Site

Once started, your blog will be available at:
- **Local**: http://localhost:5000
- **Network**: http://YOUR_IP_ADDRESS:5000

## 🧪 Testing

Test if the server is working:
```bash
python test_server.py
```

## 📁 File Structure

```
├── wsgi.py                 # WSGI entry point
├── start_production.py     # Cross-platform startup script
├── start_production.bat    # Windows batch file
├── start_production.ps1    # PowerShell script
├── gunicorn_config.py      # Gunicorn configuration
├── test_server.py          # Server testing script
└── app.py                  # Main Flask application
```

## 🔒 Security Considerations

## 🔒 Security Considerations

### Security Hardening Checklist

Before deploying to production, complete this security checklist:

#### Essential Security Configuration

- [ ] **Secret Key**: Set a strong, random `SECRET_KEY` (minimum 32 characters)
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

- [ ] **HTTPS Setup**: Configure SSL/TLS certificates
  - Use Let's Encrypt for free certificates
  - Or obtain certificates from a commercial CA
  - Verify HTTPS is working correctly

- [ ] **HTTPS Enforcement**: Enable in `.env`
  ```env
  FORCE_HTTPS=true
  ENABLE_HSTS=true
  HSTS_MAX_AGE=31536000
  ```

- [ ] **Database**: Use PostgreSQL or MySQL instead of SQLite
  ```env
  DATABASE_URL=postgresql://user:password@localhost/dbname
  ```

#### Rate Limiting Configuration

- [ ] **Configure Rate Limits**: Adjust based on expected traffic
  ```env
  RATE_LIMIT_LOGIN=5          # Login attempts per minute
  RATE_LIMIT_ADMIN=30         # Admin requests per minute
  RATE_LIMIT_PASSWORD_RESET=3 # Password resets per hour
  ```

- [ ] **Redis Backend** (Recommended for production):
  ```env
  REDIS_URL=redis://localhost:6379/0
  ```
  Install Redis:
  ```bash
  # Ubuntu/Debian
  sudo apt-get install redis-server
  
  # Windows (via Chocolatey)
  choco install redis-64
  
  # macOS
  brew install redis
  ```

#### Account Security

- [ ] **Account Lockout**: Configure thresholds
  ```env
  ACCOUNT_LOCKOUT_THRESHOLD=5  # Failed attempts before lockout
  ACCOUNT_LOCKOUT_DURATION=30  # Lockout duration in minutes
  ```

- [ ] **Session Management**: Set appropriate timeout
  ```env
  SESSION_TIMEOUT_MINUTES=30   # Session timeout in minutes
  ```

- [ ] **Password Requirements**: Enforce strong passwords
  ```env
  PASSWORD_MIN_LENGTH=12
  PASSWORD_REQUIRE_UPPERCASE=true
  PASSWORD_REQUIRE_LOWERCASE=true
  PASSWORD_REQUIRE_DIGIT=true
  PASSWORD_REQUIRE_SPECIAL=true
  ```

#### Two-Factor Authentication

- [ ] **Enable 2FA**: Set application name
  ```env
  APP_NAME=Your Blog Name
  ```

- [ ] **Admin Accounts**: Enable 2FA for all admin users
  1. Log in as admin
  2. Navigate to `/setup-2fa`
  3. Scan QR code with authenticator app
  4. Save backup codes securely

#### Security Monitoring

- [ ] **Audit Logging**: Verify audit logs are working
  - Check `/security/audit-logs` (admin only)
  - Verify login attempts are logged
  - Test filtering and export functionality

- [ ] **Log Retention**: Set up automated log cleanup
  ```python
  # Example: Delete logs older than 90 days
  from datetime import datetime, timedelta
  from models import AuditLog, LoginAttempt
  
  cutoff = datetime.utcnow() - timedelta(days=90)
  AuditLog.query.filter(AuditLog.timestamp < cutoff).delete()
  LoginAttempt.query.filter(LoginAttempt.timestamp < cutoff).delete()
  db.session.commit()
  ```

- [ ] **Security Monitoring**: Set up alerts for:
  - Multiple failed login attempts
  - Account lockouts
  - Rate limit violations
  - 2FA changes
  - Unusual admin activity

#### Testing Security Features

- [ ] **Test Rate Limiting**: Verify limits are enforced
  ```bash
  # Should block after 5 attempts
  for i in {1..10}; do curl -X POST http://localhost:5000/login; done
  ```

- [ ] **Test Account Lockout**: Verify lockout after failed attempts
  - Attempt login with wrong password 6 times
  - Verify account is locked
  - Wait for lockout duration
  - Verify account is unlocked

- [ ] **Test 2FA Flow**: Complete 2FA setup and login
  - Enable 2FA for test account
  - Logout and login again
  - Verify 2FA code is required
  - Test backup code functionality

- [ ] **Test Session Timeout**: Verify automatic logout
  - Login to account
  - Wait for SESSION_TIMEOUT_MINUTES + 1 minute
  - Attempt to access protected route
  - Verify redirect to login

- [ ] **Test Security Headers**: Verify headers are present
  ```bash
  curl -I https://yourdomain.com
  ```
  Check for:
  - Content-Security-Policy
  - X-Frame-Options
  - X-Content-Type-Options
  - Strict-Transport-Security (HTTPS only)

### Additional Security Recommendations

#### Firewall Configuration

- [ ] Restrict access to necessary ports only:
  - Port 80 (HTTP) - for HTTPS redirect
  - Port 443 (HTTPS) - for application
  - Port 22 (SSH) - for administration (restrict to specific IPs)

#### Database Security

- [ ] Use strong database passwords
- [ ] Restrict database access to application server only
- [ ] Enable database encryption at rest
- [ ] Regular database backups
- [ ] Test backup restoration

#### Application Security

- [ ] Keep dependencies up to date
  ```bash
  pip list --outdated
  pip install --upgrade -r requirements.txt
  ```

- [ ] Regular security audits
  ```bash
  pip install safety
  safety check
  ```

- [ ] Monitor for security vulnerabilities
- [ ] Set up automated dependency updates

#### Backup Strategy

- [ ] Database backups (daily)
- [ ] Application code backups
- [ ] Environment configuration backups
- [ ] SSL/TLS certificate backups
- [ ] Test restoration procedures

### Security Resources

For detailed security configuration, see:
- `SECURITY_CONFIGURATION.md` - Comprehensive security guide
- `.env.example` - All configuration options with comments
- `/security/audit-logs` - Security event monitoring (admin only)
- `/security/login-attempts` - Login attempt monitoring (admin only)

### For Production Deployment:

1. **Environment Variables**: Never commit `.env` files
2. **Secret Key**: Use a strong, random secret key (see security checklist above)
3. **Database**: Use PostgreSQL or MySQL instead of SQLite
4. **HTTPS**: Configure SSL/TLS certificates (see security checklist above)
5. **Firewall**: Restrict access to necessary ports only
6. **Security**: Complete the security hardening checklist above
7. **Monitoring**: Set up security event monitoring and alerts
8. **Backups**: Implement automated backup strategy
6. **Reverse Proxy**: Use Nginx or Apache as a reverse proxy

### Example Nginx Configuration:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🐛 Troubleshooting

### Common Issues:

1. **Port Already in Use**
   ```bash
   # Find process using port 5000
   netstat -ano | findstr :5000  # Windows
   lsof -i :5000                 # Linux/Mac
   ```

2. **Module Not Found**
   - Ensure virtual environment is activated
   - Install dependencies: `pip install -r requirements-clean.txt`

3. **Database Errors**
   - Check if `instance/` directory exists
   - Verify database path in `.env` file

4. **Permission Errors**
   - Ensure write permissions for `instance/` directory
   - Check file ownership and permissions

### Logs and Debugging:

- **Waitress**: Logs to console by default
- **Gunicorn**: Configured to log to stdout/stderr
- **Flask**: Check application logs in the console output

## 📈 Performance Tuning

### For High Traffic:

1. **Increase Workers/Threads**:
   - Waitress: `--threads=8`
   - Gunicorn: Modify `workers` in `gunicorn_config.py`

2. **Database Connection Pooling**:
   - Configure SQLAlchemy pool settings
   - Consider using connection poolers like PgBouncer

3. **Caching**:
   - Implement Redis for session storage
   - Add caching headers for static content

4. **Load Balancing**:
   - Run multiple instances behind a load balancer
   - Use Docker containers for easy scaling

## 🔄 Process Management

For production, consider using process managers:

### Systemd (Linux)
```ini
[Unit]
Description=Smileys Blog Site
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/your/app
ExecStart=/path/to/venv/bin/python start_production.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### PM2 (Cross-platform)
```bash
pm2 start start_production.py --name "smileys-blog"
pm2 startup
pm2 save
```

## 📞 Support

If you encounter issues:
1. Check the console output for error messages
2. Verify your `.env` configuration
3. Test with `python test_server.py`
4. Check the troubleshooting section above

---

**Happy Blogging!** 🎉