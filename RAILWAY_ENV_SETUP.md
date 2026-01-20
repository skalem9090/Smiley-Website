# Railway Environment Variables Setup

## Critical Fix Applied

### Database URL Handling
Railway provides PostgreSQL with `postgres://` prefix, but SQLAlchemy 1.4+ requires `postgresql://`.

**Fixed in `app.py`:**
```python
# Get database URL and fix Railway's postgres:// to postgresql://
database_url = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.abspath("instance/site.db")}')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
```

## Required Environment Variables in Railway

### 1. Add PostgreSQL Database
1. In Railway project, click "New" → "Database" → "Add PostgreSQL"
2. Wait for provisioning (30 seconds)
3. Railway automatically creates `DATABASE_URL` variable

### 2. Set Application Variables

Go to your service → Variables tab and add:

```env
# Security (REQUIRED)
SECRET_KEY=<generate-with-command-below>

# Admin Account (REQUIRED for first deployment)
ADMIN_USER=admin
ADMIN_PASSWORD=<your-secure-password>

# Flask Environment (REQUIRED)
FLASK_ENV=production

# Database (Automatically set by Railway when you add PostgreSQL)
# DATABASE_URL=${{Postgres.DATABASE_URL}}
# ⚠️ Railway sets this automatically - DO NOT manually set unless needed

# Email (Optional - for newsletter features)
SENDGRID_API_KEY=<your-sendgrid-key>
SENDGRID_FROM_EMAIL=noreply@yourdomain.com

# Upload Settings (Optional - has defaults)
UPLOAD_FOLDER=static/uploads
MAX_CONTENT_LENGTH=16777216
```

### Generate SECRET_KEY

Run this command locally:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste it as the `SECRET_KEY` value in Railway.

## Verification Steps

### 1. Check Database Connection
After deployment, check logs for:
```
✓ Connected to PostgreSQL database
✓ Running migrations...
✓ Database tables created
```

### 2. Check Environment Variables
In Railway dashboard:
- Variables tab should show all required variables
- `DATABASE_URL` should start with `postgresql://` (Railway shows `postgres://` but app converts it)

### 3. Test Database
After first deployment:
```bash
# In Railway CLI or dashboard logs
railway logs

# Look for:
# - "Database initialized"
# - "Admin user created"
# - No SQLite errors
```

## Common Issues

### Issue: "unable to open database file"
**Cause:** App is trying to use SQLite instead of PostgreSQL

**Solutions:**
1. Ensure PostgreSQL database is added in Railway
2. Check `DATABASE_URL` variable exists
3. Verify the fix in `app.py` is deployed (check git commit)
4. Redeploy the service

### Issue: "relation does not exist"
**Cause:** Database migrations haven't run

**Solution:**
```bash
# Migrations run automatically in Dockerfile CMD
# If they fail, check logs for specific error
# May need to run manually:
railway run python -m flask db upgrade
```

### Issue: "password authentication failed"
**Cause:** Database credentials issue

**Solution:**
1. Don't manually set `DATABASE_URL`
2. Let Railway set it automatically via `${{Postgres.DATABASE_URL}}`
3. Restart the service

## Deployment Checklist

Before deploying:
- [ ] PostgreSQL database added to Railway project
- [ ] `SECRET_KEY` generated and set
- [ ] `ADMIN_USER` and `ADMIN_PASSWORD` set
- [ ] `FLASK_ENV=production` set
- [ ] Latest code with database URL fix is committed
- [ ] `Dockerfile` and `railway.json` are in repository

After deploying:
- [ ] Check logs for successful database connection
- [ ] Verify migrations ran successfully
- [ ] Test accessing the application URL
- [ ] Try logging in with admin credentials
- [ ] Check that posts can be created

## Quick Deploy Commands

```bash
# 1. Commit the fixes
git add app.py Dockerfile railway.json
git commit -m "Fix: Handle Railway PostgreSQL URL format"
git push

# 2. Railway will auto-deploy

# 3. Monitor deployment
railway logs --follow

# 4. Test the deployment
curl https://your-app.railway.app/
```

## Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Auto-set | SQLite | PostgreSQL connection (Railway sets this) |
| `SECRET_KEY` | Yes | None | Flask session encryption key |
| `ADMIN_USER` | First run | None | Initial admin username |
| `ADMIN_PASSWORD` | First run | None | Initial admin password |
| `FLASK_ENV` | Yes | development | Set to `production` |
| `UPLOAD_FOLDER` | No | static/uploads | File upload directory |
| `SENDGRID_API_KEY` | No | None | Email service API key |
| `SENDGRID_FROM_EMAIL` | No | None | Email sender address |

## Next Steps

1. Commit the database URL fix
2. Push to trigger Railway deployment
3. Monitor logs for successful PostgreSQL connection
4. Access your app and create first post!
