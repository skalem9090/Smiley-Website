# Railway Deployment Fix - Pip Command Not Found

## Problem
The build was failing with `pip: command not found` because:
1. Nixpacks detected `package.json` and treated this as a Node.js project
2. Python/pip wasn't properly configured in the build environment
3. Version mismatch between `nixpacks.toml` (python311) and `runtime.txt` (python-3.13.1)

## Solution Applied

### 1. Updated `nixpacks.toml`
- Added explicit Python provider declaration
- Included both Python and Node.js packages (since you have npm dependencies)
- Proper install sequence: npm first, then pip

### 2. Updated `runtime.txt`
- Changed from `python-3.13.1` to `python-3.11` to match nixpacks configuration

## Files Modified
- `nixpacks.toml` - Added providers section and proper package setup
- `runtime.txt` - Aligned Python version with nixpacks

## Next Steps
1. Commit these changes:
   ```bash
   git add nixpacks.toml runtime.txt
   git commit -m "Fix: Configure Nixpacks for Python+Node.js hybrid project"
   git push
   ```

2. Railway will automatically trigger a new deployment

3. Monitor the build logs - you should see:
   - npm install running successfully
   - pip install running successfully
   - Flask migrations running
   - Application starting

## If Build Still Fails
Try these alternatives:

### Option 1: Use Dockerfile instead
Create a `Dockerfile` in the root:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Node.js
RUN apt-get update && apt-get install -y nodejs npm

# Copy package files
COPY package*.json ./
COPY requirements.txt ./

# Install dependencies
RUN npm install
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run migrations and start
CMD python -m flask db upgrade && python start_production.py
```

Then update `railway.json`:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Option 2: Simplify Nixpacks
Remove `package.json` dependencies if not critical, or install them differently.

## Environment Variables
Make sure these are set in Railway:
- `DATABASE_URL` (automatically provided by Railway Postgres)
- `SECRET_KEY`
- `FLASK_ENV=production`
- Any other app-specific variables from `.env.example`
