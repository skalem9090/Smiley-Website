# Resend Email Setup Guide

This guide will help you set up Resend for sending emails from your blog.

## Why Resend?

- **Free Tier:** 3,000 emails/month, 100 emails/day
- **No Phone Verification:** Unlike Twilio/SendGrid
- **Simple Setup:** Just an API key needed
- **Great Deliverability:** Built by the Vercel team
- **Modern API:** Clean, developer-friendly

## Setup Steps

### 1. Create Resend Account

1. Go to [https://resend.com](https://resend.com)
2. Click "Sign Up" (top right)
3. Sign up with your email (no phone number required!)
4. Verify your email address

### 2. Get Your API Key

1. After logging in, go to **API Keys** in the left sidebar
2. Click **"Create API Key"**
3. Give it a name (e.g., "Smileys Blog Production")
4. Select permissions: **"Sending access"**
5. Click **"Create"**
6. **Copy the API key** (starts with `re_...`)
   - ⚠️ You'll only see this once! Save it securely.

### 3. Verify Your Domain (Optional but Recommended)

For better deliverability, verify your domain:

1. Go to **Domains** in the left sidebar
2. Click **"Add Domain"**
3. Enter your domain (e.g., `yourdomain.com`)
4. Add the DNS records shown to your domain provider
5. Wait for verification (usually 5-30 minutes)

**If you don't have a custom domain yet:**
- You can use Resend's shared domain for testing
- Your emails will come from `onboarding@resend.dev`
- This works fine for testing but use your own domain for production

### 4. Configure Your Application

Add these to your `.env` file:

```env
# Resend Configuration
RESEND_API_KEY=re_your_actual_api_key_here
RESEND_FROM_EMAIL=noreply@yourdomain.com
RESEND_FROM_NAME=Smileys Blog
```

**Important:**
- Replace `re_your_actual_api_key_here` with your actual API key
- If you haven't verified a domain, use: `onboarding@resend.dev`
- Once domain is verified, use: `noreply@yourdomain.com`

### 5. Install Dependencies

```bash
pip install resend
```

Or if using the requirements file:

```bash
pip install -r requirements.txt
```

### 6. Test Your Configuration

Run this Python script to test:

```python
from resend_email_service import ResendEmailService

# Initialize service
email_service = ResendEmailService()

# Test configuration
result = email_service.test_configuration()
print(result)
```

Or test from your app:

```bash
python -c "from resend_email_service import ResendEmailService; import os; os.environ['RESEND_API_KEY']='your_key'; print(ResendEmailService().test_configuration())"
```

## Usage Examples

### Send a Simple Email

```python
from resend_email_service import ResendEmailService

email_service = ResendEmailService()

success, message = email_service.send_email(
    to="user@example.com",
    subject="Hello from Smileys Blog!",
    html="<p>This is a test email.</p>",
    text="This is a test email."
)

print(f"Success: {success}, Message: {message}")
```

### Send Newsletter Confirmation

```python
success, message = email_service.send_confirmation_email(
    email="subscriber@example.com",
    token="abc123token"
)
```

### Send Welcome Email

```python
success, message = email_service.send_welcome_email(
    email="subscriber@example.com"
)
```

## Free Tier Limits

- **3,000 emails per month**
- **100 emails per day**
- **No credit card required**
- **Forever free** (not a trial)

This is perfect for:
- Small to medium blogs
- Newsletter with up to ~100 subscribers (weekly emails)
- Transactional emails (confirmations, notifications)

## Troubleshooting

### "API key not configured"
- Make sure `RESEND_API_KEY` is in your `.env` file
- Check that the key starts with `re_`
- Restart your application after adding the key

### "Domain not verified"
- Use `onboarding@resend.dev` for testing
- Or verify your domain in Resend dashboard
- DNS changes can take up to 48 hours

### "Rate limit exceeded"
- Free tier: 100 emails/day
- Wait 24 hours or upgrade to paid plan
- Consider batching emails if sending many at once

### Emails going to spam
- Verify your domain (adds SPF, DKIM records)
- Use a professional from_email (not gmail.com)
- Avoid spam trigger words in subject/content
- Include unsubscribe link in newsletters

## Upgrading

If you need more emails:

| Plan | Price | Emails/Month | Emails/Day |
|------|-------|--------------|------------|
| Free | $0 | 3,000 | 100 |
| Pro | $20 | 50,000 | 1,000 |
| Business | $80 | 200,000 | 5,000 |

## Comparison with Other Services

| Service | Free Tier | Phone Required | Ease of Setup |
|---------|-----------|----------------|---------------|
| **Resend** | 3,000/month | ❌ No | ⭐⭐⭐⭐⭐ |
| SendGrid | 100/day | ✅ Yes | ⭐⭐⭐ |
| Mailgun | 5,000/3mo | ✅ Yes | ⭐⭐⭐ |
| Brevo | 300/day | ❌ No | ⭐⭐⭐⭐ |
| Gmail SMTP | 500/day | ❌ No | ⭐⭐⭐⭐ |

## Support

- **Documentation:** https://resend.com/docs
- **API Reference:** https://resend.com/docs/api-reference
- **Status Page:** https://status.resend.com
- **Support:** support@resend.com

## Next Steps

1. ✅ Create Resend account
2. ✅ Get API key
3. ✅ Add to `.env` file
4. ✅ Test configuration
5. ⏭️ Verify your domain (optional)
6. ⏭️ Start sending emails!

---

**Need help?** Check the [Resend documentation](https://resend.com/docs) or contact their support team.
