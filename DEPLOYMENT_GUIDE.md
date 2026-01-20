# Complete Production Deployment Guide

This guide walks you through deploying your blog to production with PostgreSQL, email service, custom domain, and SSL certificate.

## 🎯 Deployment Options

### Option 1: Railway (Recommended - Easiest)
- ✅ Free PostgreSQL database included
- ✅ Automatic SSL certificates
- ✅ Easy domain configuration
- ✅ Git-based deployments
- ✅ Environment variable management
- 💰 $5/month after free tier

### Option 2: Heroku
- ✅ Well-documented
- ✅ Add-ons for PostgreSQL and email
- ✅ Automatic SSL
- 💰 $7/month for basic dyno

### Option 3: DigitalOcean App Platform
- ✅ Full control
- ✅ Managed databases
- ✅ Automatic SSL
- 💰 $12/month

---

## 🚂 Railway Deployment (Step-by-Step)

### Step 1: Prepare Your Code

1. **Ensure all files are committed to Git:**
```bash
git add .
git commit -m "Prepare for production deployment"
```

2. **Push to GitHub (if not already):**
```bash
# Create a new repository on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

### Step 2: Create Railway Account

1. Go to [railway.app](https://railway.app)
2. Click "Start a New Project"
3. Sign up with GitHub
4. Authorize Railway to access your repositories

### Step 3: Deploy Your Application

1. **Create New Project:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your blog repository

2. **Add PostgreSQL Database:**
   - Click "New" → "Database" → "Add PostgreSQL"
   - Railway will automatically create a database
   - Database URL will be available as `DATABASE_URL`

3. **Configure Environment Variables:**
   - Click on your service
   - Go to "Variables" tab
   - Add these variables:

```env
# Required Variables
SECRET_KEY=<generate-a-strong-random-key>
DATABASE_URL=${{Postgres.DATABASE_URL}}
ADMIN_USER=admin
ADMIN_PASSWORD=<your-secure-password>

# Site Configuration
SITE_URL=https://your-app.up.railway.app
APP_NAME=Your Blog Name

# Security Settings
FORCE_HTTPS=true
ENABLE_HSTS=true
HSTS_MAX_AGE=31536000

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
```

4. **Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 4: Configure Custom Domain (Optional)

1. **In Railway:**
   - Go to your service settings
   - Click "Settings" → "Domains"
   - Click "Generate Domain" (free Railway subdomain)
   - Or click "Custom Domain" to add your own

2. **For Custom Domain:**
   - Add your domain (e.g., `yourblog.com`)
   - Railway will provide DNS records
   - Add these records to your domain registrar:
     - Type: `CNAME`
     - Name: `@` or `www`
     - Value: `your-app.up.railway.app`

3. **SSL Certificate:**
   - Railway automatically provisions SSL certificates
   - Wait 5-10 minutes for certificate to be issued
   - Your site will be available at `https://yourdomain.com`

### Step 5: Set Up Email Service

#### Option A: SendGrid (Recommended - Free Tier)

1. **Create SendGrid Account:**
   - Go to [sendgrid.com](https://sendgrid.com)
   - Sign up for free account (100 emails/day)
   - Verify your email address

2. **Create API Key:**
   - Go to Settings → API Keys
   - Click "Create API Key"
   - Name it "Blog Newsletter"
   - Select "Full Access"
   - Copy the API key (you won't see it again!)

3. **Add to Railway Environment Variables:**
```env
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=apikey
MAIL_PASSWORD=<your-sendgrid-api-key>
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

4. **Verify Sender Email:**
   - In SendGrid, go to Settings → Sender Authentication
   - Verify your sender email address
   - Or set up domain authentication for better deliverability

#### Option B: Mailgun

1. **Create Mailgun Account:**
   - Go to [mailgun.com](https://mailgun.com)
   - Sign up (5,000 emails/month free)

2. **Get SMTP Credentials:**
   - Go to Sending → Domain Settings
   - Copy SMTP credentials

3. **Add to Railway:**
```env
MAIL_SERVER=smtp.mailgun.org
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=<your-mailgun-username>
MAIL_PASSWORD=<your-mailgun-password>
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

#### Option C: Gmail (Development Only)

⚠️ **Not recommended for production** (daily sending limits)

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=<app-specific-password>
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

### Step 6: Update Application Code for Email

Add email configuration to `app.py`:

```python
# Add after other imports
from flask_mail import Mail, Message

# Add in create_app() function after app initialization
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'localhost')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 25))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'false').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@example.com')

mail = Mail(app)
```

### Step 7: Run Database Migrations

Railway will automatically run migrations if you have a `Procfile` or `railway.json`. Verify your `railway.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "flask db upgrade && python start_production.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Step 8: Verify Deployment

1. **Check Deployment Logs:**
   - In Railway, click on your service
   - Go to "Deployments" tab
   - Click on latest deployment
   - Check logs for errors

2. **Test Your Site:**
   - Visit your Railway URL or custom domain
   - Try logging in with admin credentials
   - Create a test post
   - Test image upload
   - Verify email sending (newsletter signup)

3. **Enable 2FA:**
   - Log in as admin
   - Go to `/setup-2fa`
   - Scan QR code with authenticator app
   - Save backup codes securely

### Step 9: Post-Deployment Checklist

```bash
✅ Site loads at custom domain
✅ HTTPS is working (green padlock)
✅ Admin login works
✅ Can create/edit posts
✅ Images upload successfully
✅ Newsletter signup works
✅ Email sending works
✅ 2FA is enabled for admin
✅ Security headers are present
✅ RSS/Atom feeds work
✅ Search functionality works
```

---

## 🔧 Heroku Deployment (Alternative)

### Step 1: Install Heroku CLI

```bash
# Windows (with Chocolatey)
choco install heroku-cli

# macOS
brew tap heroku/brew && brew install heroku

# Or download from heroku.com/cli
```

### Step 2: Login and Create App

```bash
heroku login
heroku create your-blog-name
```

### Step 3: Add PostgreSQL

```bash
heroku addons:create heroku-postgresql:mini
```

### Step 4: Set Environment Variables

```bash
# Generate secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Set variables
heroku config:set SECRET_KEY=<your-secret-key>
heroku config:set ADMIN_USER=admin
heroku config:set ADMIN_PASSWORD=<your-password>
heroku config:set FORCE_HTTPS=true
heroku config:set ENABLE_HSTS=true
heroku config:set APP_NAME="Your Blog Name"

# Email configuration (example with SendGrid)
heroku config:set MAIL_SERVER=smtp.sendgrid.net
heroku config:set MAIL_PORT=587
heroku config:set MAIL_USE_TLS=true
heroku config:set MAIL_USERNAME=apikey
heroku config:set MAIL_PASSWORD=<sendgrid-api-key>
heroku config:set MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

### Step 5: Deploy

```bash
git push heroku main
heroku run flask db upgrade
heroku open
```

### Step 6: Add Custom Domain

```bash
heroku domains:add yourdomain.com
heroku domains:add www.yourdomain.com
```

Heroku will provide DNS targets. Add these to your domain registrar.

---

## 📧 Email Service Setup Details

### Newsletter Manager Integration

Your `newsletter_manager.py` needs to be updated to use Flask-Mail:

```python
from flask_mail import Message
from app import mail  # Import mail instance

class NewsletterManager:
    def send_newsletter(self, subscribers, subject, content):
        """Send newsletter to subscribers"""
        for subscriber in subscribers:
            msg = Message(
                subject=subject,
                recipients=[subscriber.email],
                html=content,
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            try:
                mail.send(msg)
                subscriber.last_email_sent = datetime.now(timezone.utc)
            except Exception as e:
                current_app.logger.error(f"Failed to send to {subscriber.email}: {e}")
        
        db.session.commit()
```

### Test Email Sending

Create a test script `test_email.py`:

```python
from app import create_app, mail
from flask_mail import Message

app = create_app()

with app.app_context():
    msg = Message(
        subject="Test Email",
        recipients=["your-email@example.com"],
        body="This is a test email from your blog!",
        sender=app.config['MAIL_DEFAULT_SENDER']
    )
    
    try:
        mail.send(msg)
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Error sending email: {e}")
```

Run it:
```bash
python test_email.py
```

---

## 🔒 Security Hardening for Production

### 1. Generate Strong Secrets

```bash
# SECRET_KEY (64 characters)
python -c "import secrets; print(secrets.token_hex(32))"

# Admin password (use a password manager)
python -c "import secrets; import string; chars = string.ascii_letters + string.digits + string.punctuation; print(''.join(secrets.choice(chars) for _ in range(20)))"
```

### 2. Configure Security Headers

Already configured in your app! Verify they're working:

```bash
curl -I https://yourdomain.com
```

Should see:
- `Strict-Transport-Security`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Content-Security-Policy`

### 3. Set Up Monitoring

#### Option A: Sentry (Error Tracking)

1. Create account at [sentry.io](https://sentry.io)
2. Create new project (Python/Flask)
3. Install Sentry SDK:

```bash
pip install sentry-sdk[flask]
```

4. Add to `app.py`:

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0
)
```

5. Add to environment variables:
```env
SENTRY_DSN=<your-sentry-dsn>
```

#### Option B: UptimeRobot (Uptime Monitoring)

1. Go to [uptimerobot.com](https://uptimerobot.com)
2. Create free account
3. Add new monitor:
   - Type: HTTPS
   - URL: `https://yourdomain.com`
   - Interval: 5 minutes
4. Add alert contacts (email, SMS)

---

## 📊 Post-Deployment Tasks

### 1. Create Initial Content

```bash
# Log in to your site
# Go to /dashboard
# Create 5-10 blog posts
# Upload images
# Set up author profile
# Configure about page
```

### 2. SEO Setup

1. **Google Search Console:**
   - Go to [search.google.com/search-console](https://search.google.com/search-console)
   - Add your property
   - Verify ownership (DNS or HTML file)
   - Submit sitemap: `https://yourdomain.com/sitemap.xml`

2. **Google Analytics (Optional):**
   - Create account at [analytics.google.com](https://analytics.google.com)
   - Get tracking ID
   - Add to `base.html` template

3. **robots.txt:**
   - Already configured at `/robots.txt`
   - Verify it's accessible

### 3. Social Media Setup

1. Create social media accounts
2. Add links to author profile
3. Share your first posts
4. Set up Open Graph images

### 4. Backup Strategy

#### Automated Database Backups (Railway)

Railway automatically backs up PostgreSQL databases. To download:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# Download backup
railway run pg_dump $DATABASE_URL > backup.sql
```

#### Manual Backup Script

Create `backup_database.py`:

```python
import os
import subprocess
from datetime import datetime

# Get database URL from environment
db_url = os.environ.get('DATABASE_URL')

# Create backup filename
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_file = f'backups/backup_{timestamp}.sql'

# Create backups directory
os.makedirs('backups', exist_ok=True)

# Run pg_dump
subprocess.run(['pg_dump', db_url, '-f', backup_file])

print(f"✅ Backup created: {backup_file}")
```

---

## 🐛 Troubleshooting

### Issue: Site Not Loading

**Check:**
1. Deployment logs in Railway/Heroku
2. Environment variables are set correctly
3. Database migrations ran successfully
4. Port binding (Railway handles automatically)

**Solution:**
```bash
# Railway: Check logs
railway logs

# Heroku: Check logs
heroku logs --tail
```

### Issue: Database Connection Error

**Check:**
1. `DATABASE_URL` environment variable
2. PostgreSQL addon is provisioned
3. Database migrations completed

**Solution:**
```bash
# Railway: Check database status
railway status

# Heroku: Check database
heroku pg:info
```

### Issue: Email Not Sending

**Check:**
1. Email service credentials are correct
2. Sender email is verified
3. Flask-Mail is installed
4. SMTP settings are correct

**Solution:**
```bash
# Test email configuration
python test_email.py

# Check logs for email errors
railway logs | grep -i mail
```

### Issue: SSL Certificate Not Working

**Check:**
1. DNS records are correct
2. Wait 10-15 minutes for propagation
3. Domain is properly configured

**Solution:**
```bash
# Check DNS propagation
nslookup yourdomain.com

# Check SSL certificate
curl -vI https://yourdomain.com
```

---

## 📝 Maintenance Tasks

### Weekly
- [ ] Check error logs
- [ ] Review security audit logs
- [ ] Monitor uptime status
- [ ] Check email delivery rates

### Monthly
- [ ] Update dependencies
- [ ] Review and clean old audit logs
- [ ] Check database size
- [ ] Review backup integrity
- [ ] Update content

### Quarterly
- [ ] Security audit
- [ ] Performance review
- [ ] Update documentation
- [ ] Review and update SSL certificates (auto-renewed)

---

## 🎉 You're Live!

Your blog is now deployed with:
- ✅ PostgreSQL database
- ✅ Email service configured
- ✅ Custom domain (optional)
- ✅ SSL certificate
- ✅ Environment variables set
- ✅ Security hardening enabled
- ✅ Monitoring set up

**Next Steps:**
1. Create your first blog posts
2. Set up author profile
3. Enable 2FA for admin account
4. Share your blog with the world!

**Support:**
- Railway: [docs.railway.app](https://docs.railway.app)
- Heroku: [devcenter.heroku.com](https://devcenter.heroku.com)
- Email issues: Check your email service documentation

---

**Happy Blogging!** 🚀
