# Railway Deployment Fix - Database Connection

## Problem Solved
The app was trying to use SQLite and failing with "unable to open database file" because:
1. Railway provides PostgreSQL with `postgres://` URL prefix
2. SQLAlchemy 1.4+ requires `postgresql://` prefix
3. The app wasn't converting the URL format

## Solution Applied

### 1. Fixed Database URL Handling in `app.py`
Added automatic conversion from Railway's `postgres://` to SQLAlchemy's `postgresql://`:

```python
# Get database URL and fix Railway's postgres:// to postgresql://
database_url = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.abspath("instance/site.db")}')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
```

### 2. Updated Dockerfile
- Switched from Nixpacks to Dockerfile for reliable builds
- Added directory creation for instance and uploads
- Proper Python + Node.js setup

### 3. Created Environment Setup Guide
See `RAILWAY_ENV_SETUP.md` for complete environment variable configuration.

## Files Modified

1. **app.py** - Added DATABASE_URL format conversion
2. **Dockerfile** - Complete build configuration
3. **railway.json** - Switched to Dockerfile builder
4. **.dockerignore** - Optimized build context

## Next Steps

### 1. Ensure PostgreSQL is Added
In Railway dashboard:
- Click "New" → "Database" → "Add PostgreSQL"
- Wait for provisioning
- Railway automatically sets `DATABASE_URL`

### 2. Set Required Environment Variables
In your Railway service → Variables tab:

```env
SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_hex(32))">
ADMIN_USER=admin
ADMIN_PASSWORD=<your-secure-password>
FLASK_ENV=production
```

**DO NOT manually set DATABASE_URL** - Railway sets it automatically when you add PostgreSQL.

### 3. Deploy
```bash
git add app.py Dockerfile railway.json .dockerignore
git commit -m "Fix: Handle Railway PostgreSQL URL format and switch to Dockerfile"
git push
```

Railway will automatically:
- Build using Dockerfile
- Connect to PostgreSQL (with URL conversion)
- Run migrations
- Start the application

### 4. Verify Deployment
Check Railway logs for:
```
✓ Building Dockerfile
✓ Installing dependencies
✓ Running migrations
✓ Starting application
✓ Server listening on port 8080
```

## Expected Behavior

### Before Fix
```
sqlite3.OperationalError: unable to open database file
```

### After Fix
```
INFO: Connected to PostgreSQL database
INFO: Running migrations...
INFO: Database tables created successfully
INFO: Starting production server on port 8080
```

## Troubleshooting

### Still seeing SQLite errors?
1. Verify PostgreSQL database is added in Railway
2. Check that `DATABASE_URL` variable exists (Railway sets this)
3. Ensure latest code with fix is deployed
4. Check Railway logs for the URL conversion message

### Migrations failing?
1. Check PostgreSQL is accessible
2. Verify `DATABASE_URL` format in logs
3. Try manual migration: `railway run python -m flask db upgrade`

### Can't connect to database?
1. Don't manually set `DATABASE_URL`
2. Use Railway's automatic `${{Postgres.DATABASE_URL}}`
3. Restart the service after adding PostgreSQL

## Why This Fix Works

Railway's PostgreSQL provides URLs like:
```
postgres://user:pass@host:port/db
```

But SQLAlchemy 1.4+ requires:
```
postgresql://user:pass@host:port/db
```

The fix automatically converts the format, so your app works with Railway's PostgreSQL without manual configuration.

## Additional Resources

- `RAILWAY_ENV_SETUP.md` - Complete environment variable guide
- `RAILWAY_DEPLOYMENT_STEPS.md` - Step-by-step deployment
- `RAILWAY_TROUBLESHOOTING.md` - Common issues and solutions
