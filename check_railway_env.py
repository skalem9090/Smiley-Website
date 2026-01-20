#!/usr/bin/env python3
"""
Check Railway environment variables and database connectivity.
Run this in Railway to diagnose deployment issues.
"""

import os
import sys

def check_environment():
    """Check all required environment variables."""
    print("=" * 60)
    print("RAILWAY ENVIRONMENT CHECK")
    print("=" * 60)
    
    required_vars = {
        'DATABASE_URL': 'Database connection string',
        'SECRET_KEY': 'Flask secret key',
        'FLASK_ENV': 'Flask environment',
    }
    
    optional_vars = {
        'ADMIN_USER': 'Initial admin username',
        'ADMIN_PASSWORD': 'Initial admin password',
        'SENDGRID_API_KEY': 'Email service API key',
        'UPLOAD_FOLDER': 'File upload directory',
    }
    
    print("\n📋 REQUIRED VARIABLES:")
    all_required_set = True
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            if var in ['SECRET_KEY', 'DATABASE_URL', 'ADMIN_PASSWORD']:
                display_value = f"{value[:10]}...{value[-10:]}" if len(value) > 20 else "***"
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
            print(f"     ({description})")
        else:
            print(f"  ❌ {var}: NOT SET")
            print(f"     ({description})")
            all_required_set = False
    
    print("\n📋 OPTIONAL VARIABLES:")
    for var, description in optional_vars.items():
        value = os.environ.get(var)
        if value:
            if var in ['ADMIN_PASSWORD', 'SENDGRID_API_KEY']:
                display_value = "***"
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ⚠️  {var}: Not set ({description})")
    
    print("\n" + "=" * 60)
    
    # Check DATABASE_URL specifically
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        print("\n🔍 DATABASE_URL ANALYSIS:")
        print(f"  Length: {len(database_url)} characters")
        
        if database_url.startswith('postgres://'):
            print(f"  ⚠️  Format: postgres:// (needs conversion to postgresql://)")
        elif database_url.startswith('postgresql://'):
            print(f"  ✅ Format: postgresql:// (correct)")
        elif database_url.startswith('sqlite://'):
            print(f"  ⚠️  Format: sqlite:// (should be PostgreSQL in production)")
        else:
            print(f"  ❓ Format: Unknown ({database_url[:20]}...)")
        
        # Try to parse the URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(database_url)
            print(f"  Scheme: {parsed.scheme}")
            print(f"  Host: {parsed.hostname}")
            print(f"  Port: {parsed.port}")
            print(f"  Database: {parsed.path.lstrip('/')}")
            print(f"  Username: {parsed.username}")
        except Exception as e:
            print(f"  ❌ Error parsing URL: {e}")
    else:
        print("\n❌ DATABASE_URL is NOT SET!")
        print("   This is why the app is trying to use SQLite.")
        print("\n   TO FIX:")
        print("   1. In Railway dashboard, add PostgreSQL database")
        print("   2. Railway will automatically set DATABASE_URL")
        print("   3. Redeploy your service")
    
    print("\n" + "=" * 60)
    
    # Test database connection
    if database_url:
        print("\n🔌 TESTING DATABASE CONNECTION:")
        try:
            # Convert postgres:// to postgresql:// if needed
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
                print("  ℹ️  Converted postgres:// to postgresql://")
            
            from sqlalchemy import create_engine
            engine = create_engine(database_url)
            
            with engine.connect() as conn:
                result = conn.execute("SELECT version();")
                version = result.fetchone()[0]
                print(f"  ✅ Connected successfully!")
                print(f"  Database version: {version[:50]}...")
                
        except Exception as e:
            print(f"  ❌ Connection failed: {e}")
            print(f"\n  Common causes:")
            print(f"  - Database not provisioned yet")
            print(f"  - Wrong credentials")
            print(f"  - Network issues")
    
    print("\n" + "=" * 60)
    print("\n📊 SUMMARY:")
    if all_required_set:
        print("  ✅ All required variables are set")
    else:
        print("  ❌ Some required variables are missing")
        print("  👉 Set them in Railway dashboard → Variables tab")
    
    if not database_url:
        print("\n  🚨 CRITICAL: DATABASE_URL is not set!")
        print("  👉 Add PostgreSQL in Railway dashboard:")
        print("     1. Click 'New' → 'Database' → 'Add PostgreSQL'")
        print("     2. Wait 30 seconds for provisioning")
        print("     3. Railway automatically sets DATABASE_URL")
        print("     4. Redeploy your service")
    
    print("\n" + "=" * 60)
    
    return all_required_set and database_url is not None

if __name__ == '__main__':
    success = check_environment()
    sys.exit(0 if success else 1)
