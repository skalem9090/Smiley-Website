# Railway Deployment Troubleshooting

## 🔍 Current Status

You have a Railway project deployed at:
- Project ID: `a2bff6f6-5c17-4319-b7cc-9e962b6a81de`
- Service ID: `df2dd634-c372-46fa-9940-da6979f11ee6`

## 🐛 Common Railway Issues & Fixes

### Issue 1: Build Failing

**Symptoms:**
- Build logs show errors
- Deployment never completes
- Red "Failed" status

**Common Causes & Solutions:**

#### A. Missing Dependencies

**Check:** Look for `ModuleNotFoundError` in logs

**Fix:**
```bash
# Ensure all dependencies are in requirements.txt
pip freeze > requirements.txt

# Commit and push
git add requirements.txt
git commit -m "Update dependencies"
git push
```

#### B. Python Version Mismatch

**Check:** Railway might be using wrong Python version

**Fix:** Create `runtime.txt` in project root:
```
python-3.11.0
```

Then commit and push:
```bash
git add runtime.txt
git commit -m "Specify Python version"
git push
```

#### C. Build Command Issues

**Check:** Railway.json or Procfile configuration

**Fix:** Ensure `railway.json` exists with correct config:
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

### Issue 2: Database Connection Error

**Symptoms:**
- App builds but crashes on start
- Logs show "could not connect to database"
- `psycopg2` errors

**Solutions:**

#### A. PostgreSQL Not Added

1. In Railway dashboard, click "New"
2. Select "Database" → "Add PostgreSQL"
3. Wait for database to provision
4. Railway automatically sets `DATABASE_URL`

#### B. Missing psycopg2

Add to `requirements.txt`:
```
psycopg2-binary==2.9.9
```

Then:
```bash
git add requirements.txt
git commit -m "Add PostgreSQL driver"
git push
```

#### C. Database Migrations Not Run

Railway should run migrations automatically, but if not:

1. Go to your service in Railway
2. Click "Settings" → "Deploy"
3. Ensure start command includes: `flask db upgrade &&`

### Issue 3: Environment Variables Not Set

**Symptoms:**
- App crashes with "KeyError" or "None" errors
- Missing SECRET_KEY errors
- Configuration errors

**Solution:**

1. **Generate Secure Keys:**
```bash
python setup_production.py --generate-keys
```

2. **Set in Railway:**
   - Go to your service
   - Click "Variables" tab
   - Add these variables:

```env
SECRET_KEY=<generated-64-char-key>
DATABASE_URL=${{Postgres.DATABASE_URL}}
ADMIN_USER=admin
ADMIN_PASSWORD=<generated-strong-password>
SITE_URL=https://your-app.up.railway.app
APP_NAME=Your Blog Name
FORCE_HTTPS=true
ENABLE_HSTS=true
HSTS_MAX_AGE=31536000
```

3. **Redeploy:**
   - Railway auto-redeploys when variables change
   - Or click "Deploy" → "Redeploy"

### Issue 4: Port Binding Error

**Symptoms:**
- "Address already in use"
- "Failed to bind to port"

**Solution:**

Railway automatically sets the `PORT` environment variable. Ensure your `start_production.py` uses it:

```python
# In start_production.py
port = int(os.environ.get('PORT', 5000))
```

This should already be correct in your code.

### Issue 5: Static Files Not Loading

**Symptoms:**
- Site loads but no CSS/JS
- 404 errors for static files

**Solution:**

Ensure your `app.py` has correct static folder configuration:
```python
app = Flask(__name__, static_folder='static', static_url_path='/static')
```

And in templates, use:
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
```

## 📋 Step-by-Step Debugging

### Step 1: Check Build Logs

1. Go to Railway dashboard
2. Click on your service
3. Click "Deployments" tab
4. Click on latest deployment
5. Look for errors in build logs

**Common errors to look for:**
- `ModuleNotFoundError` → Missing dependency
- `SyntaxError` → Code error
- `No module named 'psycopg2'` → Missing PostgreSQL driver

### Step 2: Check Deploy Logs

After build succeeds, check deploy logs:

1. Same deployment view
2. Scroll to "Deploy" section
3. Look for:
   - Database migration output
   - Server startup messages
   - Any error messages

**Good signs:**
```
Running migrations...
Operations to perform: ...
Applying ...
Starting production server...
Listening on 0.0.0.0:XXXX
```

**Bad signs:**
```
Error: ...
Traceback ...
Failed to ...
```

### Step 3: Check Environment Variables

1. Click "Variables" tab
2. Verify all required variables are set:
   - ✅ SECRET_KEY (should be long random string)
   - ✅ DATABASE_URL (should reference Postgres)
   - ✅ ADMIN_USER
   - ✅ ADMIN_PASSWORD
   - ✅ SITE_URL

### Step 4: Check Database

1. Click on PostgreSQL service
2. Click "Data" tab
3. Verify tables exist:
   - `user`
   - `post`
   - `tag`
   - `login_attempts`
   - `audit_logs`
   - etc.

If tables don't exist, migrations didn't run.

### Step 5: Test the Site

1. Get your Railway URL:
   - Click on service
   - Look for "Domains" section
   - Copy the `.up.railway.app` URL

2. Visit the URL in browser

3. Test these pages:
   - `/` - Homepage
   - `/login` - Login page
   - `/dashboard` - Dashboard (after login)

## 🔧 Quick Fixes

### Fix 1: Force Redeploy

Sometimes Railway just needs a fresh deploy:

1. Go to service settings
2. Click "Deploy" → "Redeploy"
3. Wait for build to complete

### Fix 2: Clear Build Cache

If dependencies are causing issues:

1. Settings → "Build"
2. Enable "Clear build cache"
3. Redeploy

### Fix 3: Check Service Logs

Real-time logs can show what's happening:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to your project
railway link

# View logs
railway logs
```

### Fix 4: Manual Database Migration

If migrations aren't running automatically:

```bash
# Using Railway CLI
railway run flask db upgrade

# Or in Railway shell
# Go to service → Settings → "Open Shell"
flask db upgrade
```

## 🆘 Still Having Issues?

### Get Detailed Error Information

1. **Check Full Logs:**
   - Railway Dashboard → Service → Deployments → Latest
   - Scroll through entire log
   - Copy any error messages

2. **Check Database Connection:**
   ```bash
   railway run python -c "from app import create_app; app = create_app(); print('✅ App created successfully')"
   ```

3. **Test Database:**
   ```bash
   railway run python -c "from app import create_app, db; app = create_app(); app.app_context().push(); print('✅ Database connected')"
   ```

### Common Error Messages & Solutions

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'X'` | Add `X` to requirements.txt |
| `psycopg2.OperationalError` | Check DATABASE_URL is set |
| `KeyError: 'SECRET_KEY'` | Set SECRET_KEY in variables |
| `Address already in use` | Railway handles ports automatically, check start command |
| `No such file or directory: 'instance/site.db'` | Using SQLite instead of PostgreSQL, check DATABASE_URL |

## ✅ Verification Checklist

Once deployed, verify:

- [ ] Build completes successfully (green checkmark)
- [ ] Deploy completes successfully
- [ ] Site loads at Railway URL
- [ ] Can access homepage (/)
- [ ] Can access login page (/login)
- [ ] Can login with admin credentials
- [ ] Dashboard loads after login
- [ ] Can create a test post
- [ ] Images upload successfully
- [ ] No errors in Railway logs

## 📞 Need More Help?

If you're still stuck:

1. **Share the error message** from Railway logs
2. **Check these files exist:**
   - `requirements.txt`
   - `railway.json`
   - `start_production.py`
   - `wsgi.py`

3. **Verify your code is pushed:**
   ```bash
   git status  # Should show "nothing to commit"
   git log -1  # Should show your latest commit
   ```

4. **Check Railway status:**
   - [status.railway.app](https://status.railway.app)
   - Ensure no outages

---

**Pro Tip:** Railway automatically redeploys when you push to GitHub. Make sure your GitHub repo is connected and up to date!
