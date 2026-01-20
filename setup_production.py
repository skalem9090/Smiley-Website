"""
Production Setup Helper Script

This script helps you prepare your application for production deployment.
It generates secure keys, validates configuration, and provides deployment guidance.
"""

import secrets
import string
import os
import sys
from pathlib import Path


def generate_secret_key(length=64):
    """Generate a secure random secret key"""
    return secrets.token_hex(length // 2)


def generate_password(length=20):
    """Generate a secure random password"""
    chars = string.ascii_letters + string.digits + string.punctuation
    # Ensure password has at least one of each required character type
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(string.punctuation)
    ]
    # Fill the rest randomly
    password += [secrets.choice(chars) for _ in range(length - 4)]
    # Shuffle to avoid predictable pattern
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)


def check_env_file():
    """Check if .env file exists"""
    return Path('.env').exists()


def create_production_env():
    """Create a production-ready .env file"""
    print("\n🔧 Creating production environment configuration...\n")
    
    # Generate secure values
    secret_key = generate_secret_key()
    admin_password = generate_password()
    
    # Get user input
    print("Please provide the following information:")
    print("(Press Enter to use default values shown in brackets)\n")
    
    admin_user = input("Admin username [admin]: ").strip() or "admin"
    site_url = input("Site URL (e.g., https://yourblog.com): ").strip()
    app_name = input("Application name [My Blog]: ").strip() or "My Blog"
    
    # Email configuration
    print("\n📧 Email Configuration:")
    print("Choose email service:")
    print("1. SendGrid (recommended)")
    print("2. Mailgun")
    print("3. Gmail (development only)")
    print("4. Skip for now")
    
    email_choice = input("Choice [1]: ").strip() or "1"
    
    email_config = ""
    if email_choice == "1":
        print("\nSendGrid Configuration:")
        api_key = input("SendGrid API Key: ").strip()
        sender = input("Sender email: ").strip()
        email_config = f"""
# Email Configuration (SendGrid)
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=apikey
MAIL_PASSWORD={api_key}
MAIL_DEFAULT_SENDER={sender}
"""
    elif email_choice == "2":
        print("\nMailgun Configuration:")
        username = input("Mailgun SMTP username: ").strip()
        password = input("Mailgun SMTP password: ").strip()
        sender = input("Sender email: ").strip()
        email_config = f"""
# Email Configuration (Mailgun)
MAIL_SERVER=smtp.mailgun.org
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME={username}
MAIL_PASSWORD={password}
MAIL_DEFAULT_SENDER={sender}
"""
    elif email_choice == "3":
        print("\nGmail Configuration:")
        print("⚠️  Warning: Gmail is not recommended for production!")
        email = input("Gmail address: ").strip()
        app_password = input("App-specific password: ").strip()
        email_config = f"""
# Email Configuration (Gmail - Development Only)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME={email}
MAIL_PASSWORD={app_password}
MAIL_DEFAULT_SENDER={email}
"""
    
    # Create .env content
    env_content = f"""# Production Environment Configuration
# Generated on {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# CRITICAL: Keep this file secure and never commit it to version control!

# Application Configuration
SECRET_KEY={secret_key}
ADMIN_USER={admin_user}
ADMIN_PASSWORD={admin_password}
SITE_URL={site_url}
APP_NAME={app_name}

# Database Configuration
# For production, use PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost/dbname
# Railway/Heroku will set this automatically
DATABASE_URL=sqlite:///instance/site.db

{email_config}
# Security Settings
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

# Optional: Redis for session storage and rate limiting
# REDIS_URL=redis://localhost:6379/0

# Optional: Sentry for error tracking
# SENTRY_DSN=your-sentry-dsn-here
"""
    
    # Write to file
    with open('.env.production', 'w') as f:
        f.write(env_content)
    
    print("\n✅ Production environment file created: .env.production")
    print("\n⚠️  IMPORTANT SECURITY NOTES:")
    print("1. Your admin password is:", admin_password)
    print("2. Save this password in a secure password manager")
    print("3. Never commit .env files to version control")
    print("4. Copy .env.production to .env for local testing")
    print("5. Set these variables in your hosting platform (Railway/Heroku)")
    
    return True


def validate_configuration():
    """Validate current configuration"""
    print("\n🔍 Validating configuration...\n")
    
    issues = []
    warnings = []
    
    # Check .env file
    if not check_env_file():
        issues.append("❌ No .env file found")
    else:
        print("✅ .env file exists")
        
        # Load and check critical variables
        from dotenv import load_dotenv
        load_dotenv()
        
        critical_vars = ['SECRET_KEY', 'ADMIN_USER', 'ADMIN_PASSWORD']
        for var in critical_vars:
            if not os.getenv(var):
                issues.append(f"❌ Missing required variable: {var}")
            else:
                print(f"✅ {var} is set")
        
        # Check SECRET_KEY strength
        secret_key = os.getenv('SECRET_KEY', '')
        if len(secret_key) < 32:
            warnings.append("⚠️  SECRET_KEY is too short (should be 64+ characters)")
        
        # Check if using default values
        if os.getenv('SECRET_KEY') == 'dev-secret':
            issues.append("❌ Using default SECRET_KEY (INSECURE!)")
        
        # Check HTTPS settings
        if os.getenv('FORCE_HTTPS', 'false').lower() != 'true':
            warnings.append("⚠️  FORCE_HTTPS is not enabled")
    
    # Check requirements.txt
    if not Path('requirements.txt').exists():
        issues.append("❌ requirements.txt not found")
    else:
        print("✅ requirements.txt exists")
    
    # Check critical files
    critical_files = ['app.py', 'models.py', 'wsgi.py']
    for file in critical_files:
        if not Path(file).exists():
            issues.append(f"❌ Missing critical file: {file}")
        else:
            print(f"✅ {file} exists")
    
    # Print results
    print("\n" + "="*50)
    if issues:
        print("\n❌ CRITICAL ISSUES:")
        for issue in issues:
            print(f"  {issue}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  {warning}")
    
    if not issues and not warnings:
        print("\n✅ All checks passed! Ready for deployment.")
    
    print("="*50 + "\n")
    
    return len(issues) == 0


def show_deployment_checklist():
    """Show deployment checklist"""
    print("\n📋 Production Deployment Checklist:\n")
    
    checklist = [
        ("Generate secure SECRET_KEY", "python setup_production.py --generate-keys"),
        ("Create production .env file", "python setup_production.py --create-env"),
        ("Install dependencies", "pip install -r requirements.txt"),
        ("Run database migrations", "flask db upgrade"),
        ("Create admin user", "python scripts/create_admin.py"),
        ("Enable 2FA for admin", "Visit /setup-2fa after deployment"),
        ("Configure email service", "Set MAIL_* variables in .env"),
        ("Set up custom domain", "Configure DNS records"),
        ("Enable HTTPS", "Set FORCE_HTTPS=true"),
        ("Set up monitoring", "Configure Sentry or similar"),
        ("Create initial content", "Write 5-10 blog posts"),
        ("Test all features", "Login, create post, upload image, etc."),
        ("Submit sitemap to Google", "https://search.google.com/search-console"),
    ]
    
    for i, (task, command) in enumerate(checklist, 1):
        print(f"{i:2d}. [ ] {task}")
        if command:
            print(f"       {command}")
        print()


def main():
    """Main function"""
    print("="*60)
    print("  Production Setup Helper")
    print("  Smileys Blog Platform")
    print("="*60)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "--generate-keys":
            print("\n🔑 Generating secure keys...\n")
            print(f"SECRET_KEY={generate_secret_key()}")
            print(f"ADMIN_PASSWORD={generate_password()}")
            print("\n⚠️  Save these securely!")
            
        elif command == "--create-env":
            create_production_env()
            
        elif command == "--validate":
            validate_configuration()
            
        elif command == "--checklist":
            show_deployment_checklist()
            
        else:
            print(f"\n❌ Unknown command: {command}")
            print("\nAvailable commands:")
            print("  --generate-keys  Generate secure keys")
            print("  --create-env     Create production .env file")
            print("  --validate       Validate configuration")
            print("  --checklist      Show deployment checklist")
    else:
        # Interactive mode
        print("\nWhat would you like to do?")
        print("1. Create production environment file")
        print("2. Generate secure keys")
        print("3. Validate configuration")
        print("4. Show deployment checklist")
        print("5. Exit")
        
        choice = input("\nChoice [1]: ").strip() or "1"
        
        if choice == "1":
            create_production_env()
        elif choice == "2":
            print("\n🔑 Generating secure keys...\n")
            print(f"SECRET_KEY={generate_secret_key()}")
            print(f"ADMIN_PASSWORD={generate_password()}")
            print("\n⚠️  Save these securely!")
        elif choice == "3":
            validate_configuration()
        elif choice == "4":
            show_deployment_checklist()
        else:
            print("\nGoodbye!")


if __name__ == "__main__":
    main()
