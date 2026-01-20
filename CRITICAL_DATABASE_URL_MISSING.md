# 🚨 CRITICAL: DATABASE_URL Not Set in Railway

## The Problem

Your app is still trying to use SQLite because **`DATABASE_URL` environment variable is NOT set** in Railway.

The error `sqlite3.OperationalError: unable to open database file` means Railway doesn't have a PostgreSQL database configured.

## ✅ Solution: Add PostgreSQL Database

### Step 1: Add PostgreSQL in Railway Dashboard

1. **Open your Railway project**
2. **Click "New"** (top right)
3. **Select "Database"**
4. **Choose "Add PostgreSQL"**
5. **Wait 30-60 seconds** for provisioning

Railway will automatically:
- Create a PostgreSQL database
- Set the `DATABASE_URL` environment variable
- Link it to your service

### Step 2: Verify DATABASE_URL is Set

1. Go to your **service** (not the database)
2. Click **"Variables"** tab
3. Look for `DATABASE_URL`
4. It should show: `${{Postgres.DATABASE_URL}}`

If you don't see it:
- Click **"New Variable"**
- **Key:** `DATABASE_URL`
- **Value:** `${{Postgres.DATABASE_URL}}`
- Click **"Add"**

### Step 3: Redeploy

After adding PostgreSQL:
1. Railway should automatically redeploy
2. If not, click **"Deploy"** → **"Redeploy"**
3. Watch the logs

### Step 4: Verify Connection

Check the deployment logs for:
```
[DATABASE] Raw DATABASE_URL from environment: postgres://...
[DATABASE] Converted postgres:// to postgresql://
[DATABASE] Final connection string: postgresql://...
✓ Running migrations...
✓ Database tables created
```

## 🔍 Diagnostic Commands

### Check Environment Variables
```bash
# If you have Railway CLI installed
railway run python check_railway_env.py
```

This will show:
- Which environment variables are set
- DATABASE_URL format and details
- Database connection test results

### Manual Check
In Railway dashboard → Service → Variables tab, you should see:

```
DATABASE_URL = ${{Postgres.DATABASE_URL}}
SECRET_KEY = <your-secret-key>
ADMIN_USER = admin
ADMIN_PASSWORD = <your-password>
FLASK_ENV = production
```

## ❌ Common Mistakes

### Mistake 1: No PostgreSQL Database Added
**Symptom:** DATABASE_URL doesn't exist in variables
**Fix:** Add PostgreSQL database (see Step 1 above)

### Mistake 2: Manually Set Wrong DATABASE_URL
**Symptom:** DATABASE_URL is set but still fails
**Fix:** Delete the manual value, use `${{Postgres.DATABASE_URL}}`

### Mistake 3: Database Not Linked
**Symptom:** PostgreSQL exists but DATABASE_URL not available
**Fix:** 
1. Go to PostgreSQL database settings
2. Check "Connected Services"
3. Ensure your app service is listed
4. If not, reconnect them

## 📋 Complete Setup Checklist

Before your app will work:

### Database Setup
- [ ] PostgreSQL database added to Railway project
- [ ] Database is provisioned (status: "Active")
- [ ] DATABASE_URL variable appears in service variables
- [ ] DATABASE_URL value is `${{Postgres.DATABASE_URL}}`

### Environment Variables
- [ ] SECRET_KEY is set (64+ character random string)
- [ ] ADMIN_USER is set (e.g., "admin")
- [ ] ADMIN_PASSWORD is set (strong password)
- [ ] FLASK_ENV is set to "production"

### Code Deployment
- [ ] Latest code with database URL fix is committed
- [ ] Code is pushed to GitHub
- [ ] Railway has deployed the latest commit
- [ ] Dockerfile and railway.json are in repository

## 🎯 Quick Fix Commands

```bash
# 1. Ensure latest code is deployed
git add app.py check_railway_env.py
git commit -m "Add database URL debugging and fix"
git push

# 2. Check environment (if Railway CLI installed)
railway run python check_railway_env.py

# 3. View logs
railway logs --follow

# 4. If DATABASE_URL is still not set, add PostgreSQL:
#    Go to Railway dashboard → New → Database → PostgreSQL
```

## 🔄 What Happens After Adding PostgreSQL

1. **Railway provisions database** (30-60 seconds)
2. **DATABASE_URL is automatically set** to `${{Postgres.DATABASE_URL}}`
3. **Service redeploys automatically**
4. **App detects PostgreSQL URL** (starts with `postgres://`)
5. **App converts to SQLAlchemy format** (`postgresql://`)
6. **Migrations run** and create tables
7. **App starts successfully** ✅

## 📊 Expected Log Output After Fix

### Before (Current - WRONG):
```
[DATABASE] Raw DATABASE_URL from environment: sqlite:///...
[DATABASE] Final connection string: sqlite:///...
sqlite3.OperationalError: unable to open database file
```

### After (Correct):
```
[DATABASE] Raw DATABASE_URL from environment: postgres://railway.app...
[DATABASE] Converted postgres:// to postgresql://
[DATABASE] Final connection string: postgresql://railway.app...
INFO: Running migrations...
INFO: Database tables created successfully
INFO: Starting production server on port 8080
```

## 🆘 Still Not Working?

### Check These:

1. **Is PostgreSQL actually added?**
   - Railway dashboard → Your project → Should see both "Service" and "Postgres" cards

2. **Is DATABASE_URL visible in service variables?**
   - Service → Variables tab → Should see DATABASE_URL

3. **Is the latest code deployed?**
   - Service → Deployments → Check commit hash matches your latest

4. **Are there other errors in logs?**
   - Service → Deployments → View Logs → Look for other issues

### Get Help:

```bash
# Run diagnostic script
railway run python check_railway_env.py

# Check all environment variables
railway run env

# Test database connection manually
railway run python -c "import os; print('DATABASE_URL:', os.environ.get('DATABASE_URL', 'NOT SET'))"
```

## 💡 Why This Happens

Railway doesn't automatically add a database when you deploy. You must:
1. Explicitly add PostgreSQL
2. Railway then sets DATABASE_URL
3. Your app uses that URL

Without step 1, DATABASE_URL doesn't exist, so your app falls back to SQLite (which fails in Docker because the instance directory isn't writable).

---

**Next Step:** Add PostgreSQL database in Railway dashboard NOW, then redeploy.
