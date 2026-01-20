# Quick Deploy Reference Card

## 🚀 Deploy in 4 Commands

```bash
# 1. Generate configuration
python setup_production.py

# 2. Push to GitHub
git add . && git commit -m "Ready for production" && git push

# 3. Deploy to Railway
# Go to railway.app → New Project → Deploy from GitHub

# 4. Set environment variables in Railway
# Copy from .env.production to Railway Variables tab
```

## 🔑 Essential Environment Variables

```env
SECRET_KEY=<run: python setup_production.py --generate-keys>
DATABASE_URL=${{Postgres.DATABASE_URL}}
ADMIN_USER=admin
ADMIN_PASSWORD=<from setup script>
SITE_URL=https://your-app.up.railway.app
FORCE_HTTPS=true
ENABLE_HSTS=true

# Email (SendGrid example)
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=apikey
MAIL_PASSWORD=<sendgrid-api-key>
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

## 📧 SendGrid Setup (2 minutes)

1. Sign up: [sendgrid.com](https://sendgrid.com)
2. Create API Key: Settings → API Keys → Create
3. Copy key to `MAIL_PASSWORD` variable
4. Verify sender email: Settings → Sender Authentication

## ✅ Post-Deploy Checklist

```bash
✅ Site loads at Railway URL
✅ Can login with admin credentials
✅ Enable 2FA at /setup-2fa
✅ Create first blog post
✅ Test image upload
✅ Test newsletter signup
✅ Check RSS feed at /feed.xml
```

## 🆘 Quick Fixes

**Site not loading?**
```bash
railway logs  # Check for errors
```

**Email not working?**
```bash
# Verify SendGrid API key is correct
# Check sender email is verified
```

**Database error?**
```bash
railway run flask db upgrade
```

## 📱 Important URLs

- **Dashboard**: `/dashboard`
- **Settings**: `/settings`
- **2FA Setup**: `/setup-2fa`
- **Author Profile**: `/dashboard/author-profile`
- **Media Library**: `/dashboard/media-library`
- **Security Logs**: `/security/audit-logs`

## 🔗 Resources

- Full Guide: `DEPLOYMENT_GUIDE.md`
- Setup Script: `python setup_production.py`
- Email Manager: `email_manager.py`
- Railway Docs: [docs.railway.app](https://docs.railway.app)

---

**Need help?** Read `DEPLOYMENT_GUIDE.md` for detailed instructions.
