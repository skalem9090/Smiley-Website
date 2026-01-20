# Security Configuration Guide

This guide provides comprehensive documentation for configuring and managing the security features of Smileys Blog.

## Table of Contents

1. [Overview](#overview)
2. [Environment Variables](#environment-variables)
3. [Rate Limiting](#rate-limiting)
4. [Account Lockout](#account-lockout)
5. [Two-Factor Authentication](#two-factor-authentication)
6. [Session Management](#session-management)
7. [Password Validation](#password-validation)
8. [Security Headers](#security-headers)
9. [HTTPS Enforcement](#https-enforcement)
10. [Audit Logging](#audit-logging)
11. [Production Deployment](#production-deployment)
12. [Troubleshooting](#troubleshooting)

## Overview

Smileys Blog implements comprehensive security features to protect against common web application vulnerabilities and attacks. All security features are configurable via environment variables, allowing you to tailor the security posture to your specific requirements.

### Security Architecture

The security system consists of several independent but complementary components:

- **Rate Limiter**: Prevents brute force attacks by limiting request rates
- **Account Lockout Manager**: Temporarily locks accounts after failed login attempts
- **Two-Factor Auth Manager**: Provides TOTP-based second factor authentication
- **Session Manager**: Manages session lifecycle and automatic timeouts
- **Password Validator**: Enforces password complexity requirements
- **Security Headers**: Adds protective HTTP headers to all responses
- **Audit Logger**: Records all security events and admin actions

## Environment Variables

All security configuration is managed through environment variables in your `.env` file. Copy `.env.example` to `.env` and customize the values for your deployment.

### Quick Reference

```env
# Rate Limiting
RATE_LIMIT_LOGIN=5
RATE_LIMIT_ADMIN=30
RATE_LIMIT_PASSWORD_RESET=3

# Account Lockout
ACCOUNT_LOCKOUT_THRESHOLD=5
ACCOUNT_LOCKOUT_DURATION=30

# Session Management
SESSION_TIMEOUT_MINUTES=30

# Password Requirements
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SPECIAL=true

# HTTPS and Security Headers
FORCE_HTTPS=false
ENABLE_HSTS=false
HSTS_MAX_AGE=31536000

# Two-Factor Authentication
APP_NAME=Smileys Blog
```

## Rate Limiting

Rate limiting prevents brute force attacks and abuse by limiting the number of requests from a single IP address within a time window.

### Configuration

```env
# Maximum login attempts per minute
RATE_LIMIT_LOGIN=5

# Maximum admin dashboard requests per minute
RATE_LIMIT_ADMIN=30

# Maximum password reset requests per hour
RATE_LIMIT_PASSWORD_RESET=3
```

### How It Works

- Each endpoint has its own rate limit
- Limits are enforced per IP address
- When exceeded, returns HTTP 429 (Too Many Requests)
- Includes `Retry-After` header indicating when to retry
- Automatically resets after the time window expires

### Protected Endpoints

- `/login` - Login attempts
- `/dashboard/*` - All admin dashboard routes
- `/reset-password` - Password reset requests
- `/verify-2fa` - 2FA verification attempts

### Recommendations

**Development:**
```env
RATE_LIMIT_LOGIN=10
RATE_LIMIT_ADMIN=60
RATE_LIMIT_PASSWORD_RESET=5
```

**Production (Low Traffic):**
```env
RATE_LIMIT_LOGIN=5
RATE_LIMIT_ADMIN=30
RATE_LIMIT_PASSWORD_RESET=3
```

**Production (High Traffic):**
```env
RATE_LIMIT_LOGIN=10
RATE_LIMIT_ADMIN=100
RATE_LIMIT_PASSWORD_RESET=5
```

### Advanced: Redis Backend

For distributed deployments, configure Redis as the rate limiting backend:

```python
# In app.py or security_config.py
RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'memory://')
```

```env
REDIS_URL=redis://localhost:6379/0
```

## Account Lockout

Account lockout temporarily disables login for accounts that exceed failed login attempts, protecting against credential stuffing and brute force attacks.

### Configuration

```env
# Number of failed attempts before lockout
ACCOUNT_LOCKOUT_THRESHOLD=5

# Lockout duration in minutes
ACCOUNT_LOCKOUT_DURATION=30
```

### How It Works

1. Failed login attempts are tracked per user account
2. After reaching the threshold, the account is locked
3. During lockout, all login attempts are rejected
4. Lockout automatically expires after the configured duration
5. Successful login resets the failed attempt counter
6. All lockout events are logged to the audit log

### Lockout Behavior

- Locked accounts receive HTTP 403 (Forbidden) response
- Error message includes unlock time
- Admin users can manually unlock accounts via database
- Lockout applies even with correct credentials

### Recommendations

**Development:**
```env
ACCOUNT_LOCKOUT_THRESHOLD=10
ACCOUNT_LOCKOUT_DURATION=5
```

**Production (Standard):**
```env
ACCOUNT_LOCKOUT_THRESHOLD=5
ACCOUNT_LOCKOUT_DURATION=30
```

**Production (High Security):**
```env
ACCOUNT_LOCKOUT_THRESHOLD=3
ACCOUNT_LOCKOUT_DURATION=60
```

### Manual Unlock

To manually unlock an account:

```python
from app import app, db
from models import User
from datetime import datetime

with app.app_context():
    user = User.query.filter_by(username='username').first()
    user.failed_login_attempts = 0
    user.locked_until = None
    db.session.commit()
```

## Two-Factor Authentication

TOTP-based two-factor authentication adds an additional security layer beyond passwords.

### Configuration

```env
# Application name shown in authenticator apps
APP_NAME=Smileys Blog
```

### User Setup Process

1. User navigates to `/setup-2fa`
2. System generates a unique TOTP secret
3. QR code is displayed for scanning
4. User scans with authenticator app (Google Authenticator, Authy, etc.)
5. User enters verification code
6. System generates 10 backup codes
7. 2FA is enabled upon successful verification

### Login Flow with 2FA

1. User enters username and password
2. If credentials are valid and 2FA is enabled:
   - User is redirected to `/verify-2fa`
   - User enters 6-digit TOTP code or backup code
   - Session is created upon successful verification
3. If 2FA is not enabled, login proceeds normally

### Backup Codes

- 10 backup codes are generated during 2FA setup
- Each code can be used once
- Codes are hashed before storage
- Users can regenerate codes at `/regenerate-backup-codes`
- Regeneration invalidates all previous codes

### Disabling 2FA

Users can disable 2FA at `/disable-2fa`:
1. Enter current password
2. Enter valid TOTP code
3. Confirm action
4. 2FA is disabled and backup codes are deleted

### Security Considerations

- TOTP secrets are stored encrypted in the database
- Backup codes are hashed using bcrypt
- Failed 2FA attempts count toward account lockout
- 2FA changes are logged to audit log
- Time drift tolerance: ±1 time step (30 seconds)

### Supported Authenticator Apps

- Google Authenticator
- Authy
- Microsoft Authenticator
- 1Password
- LastPass Authenticator
- Any TOTP-compatible app

## Session Management

Session management controls how long users remain logged in and automatically logs out inactive sessions.

### Configuration

```env
# Session timeout in minutes
SESSION_TIMEOUT_MINUTES=30
```

### How It Works

1. Session is created upon successful login
2. `last_activity` timestamp is stored in session
3. On each request, timestamp is checked
4. If inactive for longer than timeout, session is invalidated
5. User is redirected to login page
6. Activity timestamp is updated on each request

### Session Lifecycle

```
Login → Session Created → Activity Updates → Timeout → Logout
```

### Recommendations

**Development:**
```env
SESSION_TIMEOUT_MINUTES=120  # 2 hours
```

**Production (Standard):**
```env
SESSION_TIMEOUT_MINUTES=30  # 30 minutes
```

**Production (High Security):**
```env
SESSION_TIMEOUT_MINUTES=15  # 15 minutes
```

**Production (Low Security/Convenience):**
```env
SESSION_TIMEOUT_MINUTES=480  # 8 hours
```

### Session Security

- Sessions use Flask's secure session cookies
- `SECRET_KEY` must be strong and random
- Sessions are invalidated on logout
- Expired sessions are automatically cleaned up
- Session cookies are HTTP-only and secure (in HTTPS mode)

## Password Validation

Password validation enforces complexity requirements to ensure strong passwords.

### Configuration

```env
# Minimum password length
PASSWORD_MIN_LENGTH=12

# Require at least one uppercase letter
PASSWORD_REQUIRE_UPPERCASE=true

# Require at least one lowercase letter
PASSWORD_REQUIRE_LOWERCASE=true

# Require at least one digit
PASSWORD_REQUIRE_DIGIT=true

# Require at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
PASSWORD_REQUIRE_SPECIAL=true
```

### Validation Rules

Passwords are validated on:
- User registration
- Password changes
- Password resets

### Error Messages

The validator provides specific error messages for each failed requirement:
- "Password must be at least X characters long"
- "Password must contain at least one uppercase letter"
- "Password must contain at least one lowercase letter"
- "Password must contain at least one digit"
- "Password must contain at least one special character"

### Recommendations

**Development:**
```env
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SPECIAL=false
```

**Production (Standard):**
```env
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SPECIAL=true
```

**Production (High Security):**
```env
PASSWORD_MIN_LENGTH=16
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SPECIAL=true
```

### Special Characters

Accepted special characters:
```
! @ # $ % ^ & * ( ) _ + - = [ ] { } | ; : , . < > ?
```

## Security Headers

Security headers protect against common web vulnerabilities like XSS, clickjacking, and MIME sniffing.

### Configuration

Headers are automatically applied to all responses. Configuration is minimal:

```env
# Enable HSTS (only in HTTPS mode)
ENABLE_HSTS=false

# HSTS max age in seconds (1 year = 31536000)
HSTS_MAX_AGE=31536000
```

### Applied Headers

**Content-Security-Policy:**
```
default-src 'self'; 
script-src 'self' 'unsafe-inline' 'unsafe-eval'; 
style-src 'self' 'unsafe-inline'; 
img-src 'self' data:; 
font-src 'self' data:;
```

**X-Frame-Options:**
```
SAMEORIGIN
```

**X-Content-Type-Options:**
```
nosniff
```

**Referrer-Policy:**
```
strict-origin-when-cross-origin
```

**Strict-Transport-Security (HTTPS only):**
```
max-age=31536000; includeSubDomains
```

### Customizing CSP

To customize the Content-Security-Policy, modify `security_headers.py`:

```python
csp = {
    'default-src': "'self'",
    'script-src': ["'self'", "'unsafe-inline'"],
    'style-src': ["'self'", "'unsafe-inline'"],
    # Add your custom directives
}
```

### Testing Headers

Verify headers are applied:

```bash
curl -I https://yourdomain.com
```

Or use online tools:
- [Security Headers](https://securityheaders.com/)
- [Mozilla Observatory](https://observatory.mozilla.org/)

## HTTPS Enforcement

HTTPS enforcement ensures all traffic uses encrypted connections in production.

### Configuration

```env
# Force HTTPS redirect
FORCE_HTTPS=false

# Enable HSTS
ENABLE_HSTS=false
```

### How It Works

When `FORCE_HTTPS=true`:
1. All HTTP requests are redirected to HTTPS
2. HTTP status 301 (Permanent Redirect) is used
3. Original path and query string are preserved

When `ENABLE_HSTS=true`:
1. `Strict-Transport-Security` header is added
2. Browsers will automatically use HTTPS for future requests
3. Applies to all subdomains

### Recommendations

**Development:**
```env
FORCE_HTTPS=false
ENABLE_HSTS=false
```

**Production:**
```env
FORCE_HTTPS=true
ENABLE_HSTS=true
HSTS_MAX_AGE=31536000
```

### SSL/TLS Setup

Before enabling HTTPS enforcement, ensure you have:

1. Valid SSL/TLS certificate
2. Certificate installed on web server
3. HTTPS working correctly
4. No mixed content warnings

### Certificate Options

- **Let's Encrypt**: Free, automated certificates
- **Commercial CA**: Paid certificates with extended validation
- **Self-Signed**: For development only

### Nginx HTTPS Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

## Audit Logging

Audit logging provides a complete trail of security events and admin actions.

### Logged Events

**Login Attempts:**
- Successful logins
- Failed logins (with reason)
- Account lockouts
- 2FA verifications

**Admin Actions:**
- Post creation, updates, deletion
- Media uploads and deletion
- Settings changes
- User management actions

**Security Events:**
- 2FA enable/disable
- Password changes
- Account lockouts
- Session expirations

### Log Fields

Each audit log entry includes:
- Timestamp (UTC)
- User ID and username
- Action type
- Action details (JSON)
- IP address
- User agent (optional)

### Accessing Logs

**Web Interface:**
- Audit Logs: `/security/audit-logs`
- Login Attempts: `/security/login-attempts`

**Database Query:**
```python
from models import AuditLog, LoginAttempt

# Recent audit logs
logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()

# Failed login attempts
failed = LoginAttempt.query.filter_by(success=False).all()
```

### Filtering and Export

The security dashboard supports:
- Date range filtering
- User filtering
- Action type filtering
- CSV export of filtered results

### Log Retention

Consider implementing log retention policies:

```python
from datetime import datetime, timedelta
from models import AuditLog, LoginAttempt

# Delete logs older than 90 days
cutoff = datetime.utcnow() - timedelta(days=90)
AuditLog.query.filter(AuditLog.timestamp < cutoff).delete()
LoginAttempt.query.filter(LoginAttempt.timestamp < cutoff).delete()
db.session.commit()
```

### Monitoring and Alerts

Set up monitoring for security events:

```python
# Example: Alert on multiple failed logins
from models import LoginAttempt
from datetime import datetime, timedelta

recent_failures = LoginAttempt.query.filter(
    LoginAttempt.success == False,
    LoginAttempt.timestamp > datetime.utcnow() - timedelta(minutes=5)
).count()

if recent_failures > 10:
    # Send alert
    pass
```

## Production Deployment

### Pre-Deployment Checklist

- [ ] Set strong, random `SECRET_KEY`
- [ ] Configure production database (PostgreSQL/MySQL)
- [ ] Set up SSL/TLS certificates
- [ ] Enable `FORCE_HTTPS=true`
- [ ] Enable `ENABLE_HSTS=true`
- [ ] Configure appropriate rate limits
- [ ] Set account lockout thresholds
- [ ] Configure session timeout
- [ ] Review password requirements
- [ ] Enable 2FA for all admin accounts
- [ ] Set up Redis for rate limiting (recommended)
- [ ] Configure log retention policies
- [ ] Set up security monitoring
- [ ] Test all security features
- [ ] Review audit logs regularly

### Environment-Specific Configuration

**Development:**
```env
FORCE_HTTPS=false
ENABLE_HSTS=false
RATE_LIMIT_LOGIN=10
ACCOUNT_LOCKOUT_THRESHOLD=10
SESSION_TIMEOUT_MINUTES=120
PASSWORD_MIN_LENGTH=8
```

**Staging:**
```env
FORCE_HTTPS=true
ENABLE_HSTS=false
RATE_LIMIT_LOGIN=5
ACCOUNT_LOCKOUT_THRESHOLD=5
SESSION_TIMEOUT_MINUTES=30
PASSWORD_MIN_LENGTH=12
```

**Production:**
```env
FORCE_HTTPS=true
ENABLE_HSTS=true
RATE_LIMIT_LOGIN=5
ACCOUNT_LOCKOUT_THRESHOLD=5
SESSION_TIMEOUT_MINUTES=30
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SPECIAL=true
```

### Security Monitoring

Implement monitoring for:
- Failed login attempts
- Account lockouts
- Rate limit violations
- 2FA changes
- Password changes
- Unusual admin activity

### Backup and Recovery

Regularly backup:
- Database (including security tables)
- Environment configuration
- SSL/TLS certificates
- Application code

### Incident Response

In case of security incident:
1. Review audit logs for suspicious activity
2. Check login attempts for brute force attacks
3. Verify 2FA is enabled for affected accounts
4. Reset passwords if compromised
5. Review and update security configuration
6. Document incident and response

## Troubleshooting

### Common Issues

**Issue: Rate limit too restrictive**
- Symptom: Legitimate users getting blocked
- Solution: Increase rate limits or implement IP whitelisting

**Issue: Account lockout too aggressive**
- Symptom: Users frequently locked out
- Solution: Increase lockout threshold or decrease duration

**Issue: Session timeout too short**
- Symptom: Users complaining about frequent logouts
- Solution: Increase session timeout duration

**Issue: 2FA QR code not scanning**
- Symptom: Authenticator app can't read QR code
- Solution: Ensure `APP_NAME` doesn't contain special characters

**Issue: HTTPS redirect loop**
- Symptom: Browser shows "too many redirects"
- Solution: Check reverse proxy configuration, ensure `X-Forwarded-Proto` header is set

**Issue: Security headers breaking functionality**
- Symptom: Scripts or styles not loading
- Solution: Review and adjust Content-Security-Policy

### Debug Mode

Enable debug logging for security components:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing Security Features

```bash
# Test rate limiting
for i in {1..10}; do curl -X POST http://localhost:5000/login; done

# Test account lockout
# (Attempt login with wrong password 6 times)

# Test session timeout
# (Wait for SESSION_TIMEOUT_MINUTES + 1 minute, then access protected route)

# Test 2FA
# (Enable 2FA, logout, login again)
```

### Getting Help

If you encounter issues:
1. Check application logs
2. Review audit logs for security events
3. Verify environment configuration
4. Test with default configuration
5. Check database for locked accounts
6. Review security headers in browser dev tools

---

**Last Updated:** January 2026
**Version:** 1.0
