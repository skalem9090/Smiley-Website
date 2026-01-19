# 🚀 Deployment Guide - Smiley's Blog

## Quick Start Options

### 1. **Railway** (Recommended - $5/month)

**Why Railway?**
- Simple one-click deployment
- Automatic HTTPS
- Built-in PostgreSQL database
- Easy environment variable management
- Great for small to medium blogs

**Steps:**
1. Push your code to GitHub
2. Go to [railway.app](https://railway.app)
3. Click "Deploy from GitHub repo"
4. Select your repository
5. Add environment variables:
   - `SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_hex(32))"`
   - `FLASK_ENV`: `production`
6. Railway will automatically detect and deploy your Flask app!

### 2. **Heroku** (Free tier discontinued, paid plans available)

**Steps:**
1. Install [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
2. Login: `heroku login`
3. Create app: `heroku create your-blog-name`
4. Add PostgreSQL: `heroku addons:create heroku-postgresql:mini`
5. Set environment variables:
   ```bash
   heroku config:set SECRET_KEY="your-secret-key"
   heroku config:set FLASK_ENV="production"
   ```
6. Deploy: `git push heroku main`

### 3. **DigitalOcean App Platform** (~$5/month)

**Steps:**
1. Push code to GitHub
2. Go to [DigitalOcean Apps](https://cloud.digitalocean.com/apps)
3. Create new app from GitHub
4. Use the `.do/app.yaml` configuration
5. Add environment variables in the dashboard

### 4. **VPS Deployment** (Most control, requires more setup)

**For Ubuntu/Debian servers:**

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Python and dependencies
sudo apt install python3 python3-pip python3-venv nginx supervisor postgresql postgresql-contrib -y

# 3. Create user and directory
sudo useradd -m -s /bin/bash bloguser
sudo mkdir -p /var/www/smiley-blog
sudo chown bloguser:bloguser /var/www/smiley-blog

# 4. Clone and setup application
cd /var/www/smiley-blog
git clone https://github.com/yourusername/your-repo.git .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-prod.txt

# 5. Setup database
sudo -u postgres createdb smiley_blog
sudo -u postgres createuser bloguser
sudo -u postgres psql -c "ALTER USER bloguser CREATEDB;"

# 6. Configure environment
echo "SECRET_KEY=your-secret-key-here" > .env
echo "DATABASE_URL=postgresql://bloguser@localhost/smiley_blog" >> .env
echo "FLASK_ENV=production" >> .env

# 7. Initialize database
flask db upgrade

# 8. Create admin user
python scripts/create_admin.py
```

## Pre-Deployment Checklist

### 1. **Security Setup**
- [ ] Generate strong SECRET_KEY
- [ ] Set FLASK_ENV=production
- [ ] Review admin credentials
- [ ] Check file upload permissions

### 2. **Database Migration**
```bash
# Test migrations locally first
flask db upgrade
```

### 3. **Environment Variables**
```bash
# Required
SECRET_KEY=your-32-character-secret-key
DATABASE_URL=postgresql://user:pass@host:port/dbname
FLASK_ENV=production

# Optional
UPLOAD_FOLDER=static/uploads
ADMIN_USER=your-admin-username
ADMIN_PASSWORD=your-admin-password
```

### 4. **Test Locally in Production Mode**
```bash
export FLASK_ENV=production
export SECRET_KEY="test-key"
python app.py
```

## Post-Deployment Steps

### 1. **Create Admin User**
If you didn't set ADMIN_USER/ADMIN_PASSWORD environment variables:
```bash
python scripts/create_admin.py
```

### 2. **Test Core Features**
- [ ] Homepage loads
- [ ] Admin login works
- [ ] Create/edit posts
- [ ] Image uploads
- [ ] RSS feeds work
- [ ] Comments system
- [ ] Newsletter signup

### 3. **Setup Domain (Optional)**
- Purchase domain from registrar
- Point DNS to your deployment platform
- Most platforms handle SSL automatically

### 4. **Monitoring Setup**
- Check application logs regularly
- Monitor database size
- Watch upload folder disk usage
- Set up uptime monitoring (UptimeRobot, etc.)

## Troubleshooting

### Common Issues:

**Database Connection Errors:**
- Verify DATABASE_URL format
- Check database credentials
- Ensure database exists

**File Upload Issues:**
- Check upload folder permissions
- Verify MAX_CONTENT_LENGTH setting
- Ensure sufficient disk space

**Static Files Not Loading:**
- Check static folder permissions
- Verify Flask static_folder configuration

**Scheduled Posts Not Publishing:**
- Check APScheduler logs
- Verify timezone settings
- Ensure background process is running

## Cost Estimates

| Platform | Monthly Cost | Pros | Cons |
|----------|-------------|------|------|
| Railway | $5 | Simple, automatic scaling | Limited free tier |
| Heroku | $7+ | Mature platform, add-ons | More expensive |
| DigitalOcean | $5+ | Good performance, simple | Less automation |
| VPS | $5-20+ | Full control, customizable | Requires server management |

## Performance Tips

1. **Enable caching headers** (already implemented)
2. **Optimize images** before upload
3. **Use CDN** for static assets (optional)
4. **Monitor database queries** for optimization
5. **Set up database backups**

## Need Help?

- Check platform-specific documentation
- Review application logs for errors
- Test locally before deploying
- Start with Railway or Heroku for simplicity

Your blog is ready for production! 🎉