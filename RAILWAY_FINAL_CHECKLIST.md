# Railway Deployment - Final Checklist

## 🚨 CRITICAL ISSUE IDENTIFIED

Your app is failing because **PostgreSQL database is not added in Railway**.

The error `sqlite3.OperationalError: unable to open database file` confirms that `DATABASE_URL` environment variable is NOT set.

---

## ✅ Complete Setup Steps

### 1. Add PostgreSQL Database (REQUIRED - Do This First!)

**In Railway Dashboard:**
1. Open your Railway project
2. Click **"New"** button (top right)
3. Select **"Database"**
4. Choose **"Add PostgreSQL"**
5. Wait 30-60 seconds for provisioning
6. Verify status shows **"Active"**

**Result:** Railway automatically creates `DATABASE_URL` variable

### 2. Verify DATABASE_URL is Available

**Check in your service (not database):**
1. Click on your **app service** (not the Postgres card)
2. Go to **"Variables"** tab
3. Look for `DATABASE_URL`
4. Value should be: `${{Postgres.DATABASE_URL}}`

**If DATABASE_URL is missing:**
- Click "New Variable"
- Key: `DATABASE_URL`
- Value: `${{Postgres.DATABASE_URL}}`
- Click "Add"

### 3. Set Other Environment Variables

**In your service → Variables tab, add:**

```env
SECRET_KEY=<generate-with-command-below>
ADMIN_USER=admin
ADMIN_PASSWORD=<your-secure-password>
FLASK_ENV=production
```

**Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Deploy Latest Code

```bash
# Commit all fixes
git add app.py check_railway_env.py CRITICAL_DATABASE_URL_MISSING.md COMMIT_AND_DEPLOY.md
git commit -m "Add Railway PostgreSQL debugging and fix"
git push
```

Railway will automatically deploy after push.

### 5. Monitor Deployment Logs

**Watch for these key lines:**
```
[DATABASE] Raw DATABASE_URL from environment: postgres://...
[DATABASE] Converted postgres:// to postgresql://
[DATABASE] Final connection string: postgresql://...
✓ Running migrations...
✓ Database tables created
✓ Starting application
```

**If you see this instead:**
```
[DATABASE] Raw DATABASE_URL from environment: sqlite:///...
```
**STOP!** Go back to Step 1 - PostgreSQL is not configured.

### 6. Test Your Application

1. Click **"Open App"** in Railway dashboard
2. Navigate to `/login`
3. Log in with your admin credentials
4. Create a test post
5. Verify images upload
6. Check that data persists

---

## 📋 Pre-Deployment Checklist

Before you can successfully deploy, verify:

### Database
- [ ] PostgreSQL database added in Railway project
- [ ] Database status is "Active" (not "Deploying")
- [ ] DATABASE_URL appears in service variables
- [ ] DATABASE_URL value is `${{Postgres.DATABASE_URL}}`

### Environment Variables (in service, not database)
- [ ] `SECRET_KEY` is set (64 characters)
- [ ] `ADMIN_USER` is set
- [ ] `ADMIN_PASSWORD` is set
- [ ] `FLASK_ENV=production` is set

### Code
- [ ] Latest code with database fix is committed
- [ ] `app.py` has DATABASE_URL conversion code
- [ ] `Dockerfile` exists in repository
- [ ] `railway.json` uses Dockerfile builder
- [ ] All files are pushed to GitHub

### Railway Configuration
- [ ] GitHub repository is connected
- [ ] Service is linked to correct repository
- [ ] Auto-deploy is enabled (optional but recommended)

---

## 🔍 Diagnostic Tools

### Run Environment Check
```bash
# Install Railway CLI if not already installed
npm install -g @railway/cli

# Login and link to your project
railway login
railway link

# Run diagnostic script
railway run python check_railway_env.py
```

**This will show:**
- ✅ Which environment variables are set
- ✅ DATABASE_URL format and details
- ✅ Database connection test results
- ❌ What's missing or misconfigured

### Quick Checks
```bash
# Check if DATABASE_URL exists
railway run python -c "import os; print('DATABASE_URL:', 'SET' if os.environ.get('DATABASE_URL') else 'NOT SET')"

# Check DATABASE_URL format
railway run python -c "import os; url = os.environ.get('DATABASE_URL', 'NOT SET'); print('Format:', url[:30])"

# List all environment variables
railway run env
```

---

## 🎯 Success Criteria

Your deployment is successful when you see:

### In Railway Logs:
```
✅ Building Dockerfile
✅ Installing dependencies
✅ [DATABASE] Raw DATABASE_URL from environment: postgres://
✅ [DATABASE] Converted postgres:// to postgresql://
✅ Running migrations
✅ Database tables created
✅ Starting production server
✅ Listening on port 8080
```

### In Your Browser:
- ✅ Application loads without errors
- ✅ Can log in with admin credentials
- ✅ Can create and publish posts
- ✅ Images upload successfully
- ✅ Data persists between page refreshes

---

## ❌ Common Issues & Solutions

### Issue 1: "unable to open database file"
**Symptom:** SQLite error in logs
**Cause:** DATABASE_URL not set (PostgreSQL not added)
**Solution:** 
1. Add PostgreSQL in Railway dashboard
2. Verify DATABASE_URL appears in variables
3. Redeploy

### Issue 2: "relation does not exist"
**Symptom:** Database table errors
**Cause:** Migrations didn't run
**Solution:**
```bash
railway run python -m flask db upgrade
```

### Issue 3: "Connection refused"
**Symptom:** Can't connect to database
**Cause:** Database not fully provisioned
**Solution:** Wait 1-2 minutes, then redeploy

### Issue 4: Still seeing SQLite in logs
**Symptom:** `[DATABASE] Raw DATABASE_URL from environment: sqlite:///`
**Cause:** Latest code not deployed or DATABASE_URL still not set
**Solution:**
1. Verify PostgreSQL is added
2. Check DATABASE_URL in variables
3. Force redeploy: Railway dashboard → Deploy → Redeploy

---

## 📚 Documentation Reference

| Document | Purpose |
|----------|---------|
| `CRITICAL_DATABASE_URL_MISSING.md` | Explains DATABASE_URL requirement |
| `COMMIT_AND_DEPLOY.md` | Quick deployment commands |
| `RAILWAY_ENV_SETUP.md` | Environment variable guide |
| `RAILWAY_DEPLOYMENT_COMPLETE.md` | Complete deployment guide |
| `RAILWAY_TROUBLESHOOTING.md` | Common issues and fixes |
| `check_railway_env.py` | Diagnostic script |

---

## 🚀 Quick Start (TL;DR)

If you just want to get it working:

1. **Add PostgreSQL:** Railway dashboard → New → Database → PostgreSQL
2. **Set variables:** SECRET_KEY, ADMIN_USER, ADMIN_PASSWORD, FLASK_ENV
3. **Deploy code:** `git push`
4. **Check logs:** Look for `[DATABASE] Raw DATABASE_URL from environment: postgres://`
5. **Test app:** Open app URL and log in

If step 4 shows `sqlite://` instead of `postgres://`, go back to step 1.

---

## 💡 Why This Happens

Railway doesn't automatically add a database. You must:
1. Explicitly add PostgreSQL
2. Railway then sets DATABASE_URL
3. Your app detects and uses it

Without step 1, DATABASE_URL doesn't exist, so your app defaults to SQLite (which fails in Docker).

---

## 🆘 Still Stuck?

1. **Run diagnostics:** `railway run python check_railway_env.py`
2. **Check Railway dashboard:** Verify PostgreSQL card exists
3. **View logs:** Look for DATABASE_URL debug messages
4. **Read docs:** `CRITICAL_DATABASE_URL_MISSING.md`
5. **Ask for help:** Railway Discord or support

---

**Next Action:** Add PostgreSQL database in Railway dashboard NOW! 🎯
