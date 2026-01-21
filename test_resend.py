"""
Test Resend Email Configuration

Run this script to test your Resend email setup.
"""

import os
from dotenv import load_dotenv
from resend_email_service import ResendEmailService

# Load environment variables
load_dotenv()

def test_resend():
    """Test Resend email configuration"""
    
    print("=" * 60)
    print("RESEND EMAIL CONFIGURATION TEST")
    print("=" * 60)
    print()
    
    # Check if API key is set
    api_key = os.getenv('RESEND_API_KEY')
    from_email = os.getenv('RESEND_FROM_EMAIL', 'onboarding@resend.dev')
    from_name = os.getenv('RESEND_FROM_NAME', 'Smileys Blog')
    
    print("Configuration:")
    print(f"  API Key: {'✓ Set' if api_key else '✗ Not set'}")
    print(f"  From Email: {from_email}")
    print(f"  From Name: {from_name}")
    print()
    
    if not api_key:
        print("❌ ERROR: RESEND_API_KEY not found in environment variables")
        print()
        print("Please add to your .env file:")
        print("  RESEND_API_KEY=re_your_api_key_here")
        print("  RESEND_FROM_EMAIL=noreply@yourdomain.com")
        print("  RESEND_FROM_NAME=Smileys Blog")
        print()
        print("Get your API key at: https://resend.com/api-keys")
        return
    
    # Initialize service
    print("Initializing Resend service...")
    email_service = ResendEmailService(
        api_key=api_key,
        from_email=from_email,
        from_name=from_name
    )
    print("✓ Service initialized")
    print()
    
    # Test configuration
    print("Testing configuration...")
    result = email_service.test_configuration()
    print()
    
    print("Test Results:")
    print(f"  Success: {'✓ Yes' if result['success'] else '✗ No'}")
    print(f"  Message: {result['message']}")
    print()
    
    if result['success']:
        print("=" * 60)
        print("✅ SUCCESS! Your Resend configuration is working!")
        print("=" * 60)
        print()
        print(f"A test email was sent to: {from_email}")
        print("Check your inbox to confirm delivery.")
        print()
        print("Next steps:")
        print("  1. Check your email inbox")
        print("  2. If email is in spam, mark it as 'Not Spam'")
        print("  3. Consider verifying your domain for better deliverability")
        print("  4. Your blog is ready to send emails!")
    else:
        print("=" * 60)
        print("❌ FAILED! There was an issue with your configuration")
        print("=" * 60)
        print()
        print("Common issues:")
        print("  - Invalid API key (check it starts with 're_')")
        print("  - API key doesn't have 'Sending access' permission")
        print("  - Network connectivity issues")
        print()
        print("Troubleshooting:")
        print("  1. Verify your API key at: https://resend.com/api-keys")
        print("  2. Make sure the key has 'Sending access' permission")
        print("  3. Check your internet connection")
        print("  4. Try creating a new API key")
    
    print()

if __name__ == '__main__':
    test_resend()
