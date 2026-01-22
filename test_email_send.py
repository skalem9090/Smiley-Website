"""Quick test to send an email and check if it works"""
import os
from dotenv import load_dotenv
import resend

load_dotenv()

# Get API key
api_key = os.getenv('RESEND_API_KEY')
print(f"API Key found: {bool(api_key)}")
print(f"API Key starts with: {api_key[:10] if api_key else 'NOT FOUND'}...")

if not api_key:
    print("ERROR: RESEND_API_KEY not found in .env file")
    exit(1)

# Set API key
resend.api_key = api_key

# Get email to send to
test_email = input("Enter your email address to test: ").strip()

if not test_email:
    print("No email provided, exiting")
    exit(1)

print(f"\nSending test email to: {test_email}")

try:
    params = {
        "from": "Smileys Blog <onboarding@resend.dev>",
        "to": [test_email],
        "subject": "Test Email from Smileys Blog",
        "html": "<h1>Success!</h1><p>If you received this, your email is working!</p>",
    }
    
    response = resend.Emails.send(params)
    print(f"\n✅ SUCCESS!")
    print(f"Email ID: {response.get('id')}")
    print(f"\nCheck your inbox (and spam folder) for: {test_email}")
    print(f"\nYou can also check the Resend dashboard:")
    print(f"https://resend.com/emails/{response.get('id')}")
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
