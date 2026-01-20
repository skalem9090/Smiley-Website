# Railway Deployment - Action Steps

## 🚀 Your Railway Project is Live!

Project URL: https://railway.com/project/a2bff6f6-5c17-4319-b7cc-9e962b6a81de

## ✅ Files Just Updated

I've fixed your Railway configuration:

1. **`railway.json`** - Now runs database migrations before starting
2. **`requirements.txt`** - Added `psycopg2-binary` for PostgreSQL support

## 📋 Next Steps to Complete Deployment

### Step 1: Commit and Push Changes (2 minutes)

```bash
# Add the updated files
git add railway.json requirements.txt

# Commit
git commit -m "Fix Railway deployment configuration"

# Push to trigger redeploy
git push
```

Railway will automatically detect the push and redeploy your app.

### Step 2: Add PostgreSQL Database (if not already added)

1. Go to your Railway project dashboard
2. Click "New" button
3. Select "Database" → "Add PostgreSQL"
4. Wait 30 seconds for provisioning
5. Railway automatically sets `DATABASE_URL` variable

### Step 3: Set Environment Variables

Go to your service → "Variables" tab and add:

```env
# Generate these first:
# Run: python setup_production.py --generate-keys

SECRET_KEY=<paste-64-char-key-here>
ADMIN_USER=admin
ADMIN_PASSWORD=<paste-strong-password-here>

# Site configuration
SITE_URL=https://your-app-name.up.railway.app
APP_NAME=Smileys Blog

# Database (Railway sets this automatically when you add PostgreSQL)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Security
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

### Step 4: Generate Secure Keys Locally

```bash
# Run the setup script
python setup_production.py --generate-keys

# Copy the output:
# SECRET_KEY=... (64 characters)
# ADMIN_PASSWORD=... (20 characters)

# Paste these into Railway Variables
```

### Step 5: Get Your Site URL

1. In Railway, click on your service
2. Look for "Domains" section
3. You'll see something like: `your-app-name.up.railway.app`
4. Copy this URL
5. Update `SITE_URL` variable with this URL

### Step 6: Watch the Deployment

1. Go to "Deployments" tab
2. Click on the latest deployment
3. Watch the logs:
   - ✅ Build should complete (installing dependencies)
   - ✅ Deploy should run migrations
   - ✅ Server should start

**Look for these success messages:**
```
Running migrations...
Operations to perform:
  Apply all migrations: ...
Applying ...
  OK
Starting production server...
Listening on 0.0.0.0:XXXX
```

### Step 7: Test Your Site

Once deployment completes:

1. **Visit your Railway URL** (from Step 5)
2. **Test homepage** - Should load with "Smileys Blog"
3. **Test login** - Go to `/login`
4. **Login with admin credentials** (from Step 4)
5. **Access dashboard** - Should redirect to `/dashboard`

### Step 8: Enable 2FA (Security)

1. After logging in, go to `/setup-2fa`
2. Scan QR code with authenticator app (Google Authenticator, Authy, etc.)
3. Enter the 6-digit code
4. **Save backup codes** in a secure location!

### Step 9: Create Your First Post

1. In dashboard, click "Create New Post"
2. Write a test post
3. Upload an image
4. Publish it
5. View it on the homepage

## 🐛 If Something Goes Wrong

### Build Fails

**Check logs for:**
- Missing dependencies → Already fixed in requirements.txt
- Python version issues → Railway uses Python 3.11 by default

**Solution:**
```bash
# If needed, create runtime.txt
echo "python-3.11.0" > runtime.txt
git add runtime.txt
git commit -m "Specify Python version"
git push
```

### Database Connection Error

**Symptoms:** "could not connect to database"

**Solution:**
1. Ensure PostgreSQL is added (Step 2)
2. Check `DATABASE_URL` variable is set to `${{Postgres.DATABASE_URL}}`
3. Redeploy

### App Crashes on Start

**Check logs for specific error**

Common fixes:
```bash
# Missing SECRET_KEY
# → Set in Variables (Step 3)

# Migration errors
# → Railway CLI: railway run flask db upgrade

# Port binding issues
# → Already handled in start_production.py
```

### Can't Login

**Possible causes:**
1. Admin user not created
2. Wrong password
3. Database not migrated

**Solution:**
```bash
# Use Railway CLI to create admin
railway run python scripts/create_admin.py

# Or reset password
railway run python scripts/reset_admin_password.py
```

## 📧 Optional: Set Up Email (Later)

For newsletter functionality, you'll need to configure email:

1. **Sign up for SendGrid** (free tier: 100 emails/day)
2. **Create API key** in SendGrid dashboard
3. **Add to Railway Variables:**
```env
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=apikey
MAIL_PASSWORD=<sendgrid-api-key>
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

See `DEPLOYMENT_GUIDE.md` for detailed email setup.

## 🎯 Success Checklist

- [ ] Code pushed to GitHub
- [ ] Railway redeployed automatically
- [ ] PostgreSQL database added
- [ ] Environment variables set
- [ ] Build completed successfully
- [ ] Migrations ran successfully
- [ ] Site loads at Railway URL
- [ ] Can login with admin credentials
- [ ] Dashboard accessible
- [ ] Can create test post
- [ ] 2FA enabled for admin account

## 🎉 You're Live!

Once all steps are complete, your blog is live at:
`https://your-app-name.up.railway.app`

### Next Steps:
1. Create 5-10 blog posts
2. Set up author profile
3. Configure about page
4. Add custom domain (optional)
5. Set up email service (optional)
6. Share your blog!

## 📞 Need Help?

- **Railway Logs:** Check deployment logs for errors
- **Troubleshooting:** See `RAILWAY_TROUBLESHOOTING.md`
- **Full Guide:** See `DEPLOYMENT_GUIDE.md`
- **Railway Docs:** [docs.railway.app](https://docs.railway.app)

---

**Current Status:** Ready to push changes and redeploy!

**Next Command:** `git add . && git commit -m "Fix Railway config" && git push`
