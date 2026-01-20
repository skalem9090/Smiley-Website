# Ready to Deploy - Quick Commands

## 🚨 CRITICAL: Add PostgreSQL Database First!

**Before deploying, you MUST add PostgreSQL in Railway:**

1. Open Railway dashboard
2. Click "New" → "Database" → "Add PostgreSQL"
3. Wait 30 seconds for provisioning
4. Verify `DATABASE_URL` appears in your service's Variables tab

**Without PostgreSQL, the app will fail with SQLite errors!**

---

## All Fixes Applied ✅

1. ✅ Database URL conversion (Railway postgres:// → postgresql://)
2. ✅ Dockerfile build system
3. ✅ Directory creation
4. ✅ Debug logging for DATABASE_URL
5. ✅ Environment diagnostic script

## Deploy Now

### Step 1: Add PostgreSQL (If Not Already Done)

**In Railway Dashboard:**
1. Go to your project
2. Click "New" (top right)
3. Select "Database"
4. Choose "Add PostgreSQL"
5. Wait for "Active" status

**Verify:**
- Go to your service → Variables tab
- You should see `DATABASE_URL = ${{Postgres.DATABASE_URL}}`

### Step 2: Commit Changes
```bash
git add app.py check_railway_env.py CRITICAL_DATABASE_URL_MISSING.md
git commit -m "Fix Railway deployment: Add PostgreSQL debugging and URL handling

- Add debug logging for DATABASE_URL detection
- Create environment diagnostic script
- Add critical setup documentation
- Fix postgres:// to postgresql:// conversion"
git push
```

### Step 3: Verify Railway Setup
Before the deployment completes, ensure in Railway dashboard:
- [ ] PostgreSQL database is added and Active
- [ ] Environment variables are set:
  - `DATABASE_URL` (auto-set by Railway when you add PostgreSQL)
  - `SECRET_KEY` (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)
  - `ADMIN_USER=admin`
  - `ADMIN_PASSWORD=<your-password>`
  - `FLASK_ENV=production`

### Step 4: Monitor Deployment
After pushing, watch Railway logs:
```bash
# If you have Railway CLI installed
railway logs --follow

# Or watch in Railway dashboard
# Click on your service → Deployments → View Logs
```

### Step 5: Check Database Connection
Look for these lines in the logs:
```
[DATABASE] Raw DATABASE_URL from environment: postgres://...
[DATABASE] Converted postgres:// to postgresql://
[DATABASE] Final connection string: postgresql://...
```

If you see:
```
[DATABASE] Raw DATABASE_URL from environment: sqlite:///...
```
**STOP!** PostgreSQL is not configured. Go back to Step 1.

### Step 6: Test Application
Once deployed:
1. Click "Open App" in Railway dashboard
2. Navigate to `/login`
3. Log in with admin credentials
4. Create a test post
5. Verify everything works

## Diagnostic Commands

### Check Environment Variables
```bash
# Run the diagnostic script
railway run python check_railway_env.py

# This will show:
# - Which variables are set
# - DATABASE_URL format
# - Database connection test
```

### Manual Checks
```bash
# Check if DATABASE_URL is set
railway run python -c "import os; print('DATABASE_URL:', 'SET' if os.environ.get('DATABASE_URL') else 'NOT SET')"

# Check DATABASE_URL format
railway run python -c "import os; url = os.environ.get('DATABASE_URL', ''); print('Format:', url[:20] if url else 'NOT SET')"

# Test database connection
railway run python -c "from app import create_app, db; app = create_app(); app.app_context().push(); print('Connected:', db.engine.url)"
```

## Expected Log Output

### ✅ Successful Deployment
```
Building Dockerfile...
Successfully built image
[DATABASE] Raw DATABASE_URL from environment: postgres://railway.app...
[DATABASE] Converted postgres:// to postgresql://
[DATABASE] Final connection string: postgresql://railway.app...
INFO: Running migrations...
INFO: Database tables created successfully
INFO: Starting production server on port 8080
✓ Server listening
```

### ❌ If You See Errors

**"unable to open database file"**
```
[DATABASE] Raw DATABASE_URL from environment: sqlite:///...
sqlite3.OperationalError: unable to open database file
```
**Cause:** PostgreSQL not added or DATABASE_URL not set
**Fix:** See `CRITICAL_DATABASE_URL_MISSING.md`

**"pip: command not found"**  
**Cause:** Old Nixpacks config still being used
**Fix:** Ensure Dockerfile and railway.json are committed

**"relation does not exist"**
**Cause:** Migrations didn't run
**Fix:** `railway run python -m flask db upgrade`

## Quick Reference

### Generate SECRET_KEY
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Check Local Build
```bash
docker build -t blog-test .
docker run -p 8080:8080 -e SECRET_KEY=test -e DATABASE_URL=sqlite:///test.db blog-test
```

### Railway CLI Commands
```bash
# Install
npm install -g @railway/cli

# Login and link
railway login
railway link

# View logs
railway logs

# Run diagnostic
railway run python check_railway_env.py

# Check environment
railway run env | grep DATABASE_URL
```

## Files Changed Summary

| File | Change | Why |
|------|--------|-----|
| `app.py` | Added URL conversion + debug logging | Fix Railway's postgres:// format and diagnose issues |
| `check_railway_env.py` | Created diagnostic script | Help troubleshoot environment setup |
| `CRITICAL_DATABASE_URL_MISSING.md` | Critical setup guide | Explain DATABASE_URL requirement |
| `Dockerfile` | Created | Reliable build process |
| `railway.json` | Updated builder | Use Dockerfile instead of Nixpacks |
| `.dockerignore` | Created | Optimize build |

## After Successful Deployment

1. **Change admin password** (use strong password)
2. **Set up 2FA** for admin account
3. **Configure email** (optional, for newsletters)
4. **Add custom domain** (optional)
5. **Create your first real post**
6. **Set up regular backups**

## Need Help?

### If DATABASE_URL is not set:
📖 Read `CRITICAL_DATABASE_URL_MISSING.md`

### For other deployment issues:
- 🔧 Check `RAILWAY_TROUBLESHOOTING.md`
- 📚 Read `RAILWAY_DEPLOYMENT_COMPLETE.md`
- 🌐 Visit Railway docs: https://docs.railway.app

### Run Diagnostics:
```bash
railway run python check_railway_env.py
```

---

**⚠️ IMPORTANT:** Make sure PostgreSQL is added BEFORE deploying! 🚀
