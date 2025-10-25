# MailerLite Integration Setup Guide

## 1. Create Your MailerLite Account
1. Go to https://www.mailerlite.com/ and sign up (free plan)
2. Verify your email address
3. Complete the onboarding

## 2. Get Your API Key
1. Log into your MailerLite dashboard
2. Go to **Integrations** → **MailerLite API**
3. Click **Generate new token**
4. Give it a name (e.g., "KnightCycle Website")
5. Copy the API key (you'll only see it once!)

## 3. (Optional) Create a Subscriber Group
1. Go to **Subscribers** → **Groups**
2. Click **Create group**
3. Name it "Newsletter Subscribers" or "Website Signups"
4. Copy the Group ID from the URL (e.g., `12345678`)

## 4. Set Environment Variables

### For Development (Windows PowerShell):
```powershell
# Set for current session
$env:MAILERLITE_API_KEY="your-api-key-here"
$env:MAILERLITE_GROUP_ID="your-group-id-here"  # Optional

# Or set permanently (choose one):
# Option A: Add to PowerShell profile
notepad $PROFILE
# Add these lines:
$env:MAILERLITE_API_KEY="your-api-key-here"
$env:MAILERLITE_GROUP_ID="your-group-id-here"

# Option B: Use .env file (recommended)
# Create a .env file in your project root and add python-dotenv
```

### For Production:
Set environment variables in your hosting platform:
- Heroku: `heroku config:set MAILERLITE_API_KEY=your-key`
- Railway: Add in Variables tab
- PythonAnywhere: In Web tab → Environment variables
- AWS/DigitalOcean: In your environment config

## 5. Test the Integration

### Test 1: Subscribe via Website
1. Start your Django server: `python manage.py runserver`
2. Go to your homepage
3. Scroll to the "Stay Updated" section
4. Enter an email and click Subscribe
5. Check your MailerLite dashboard → Subscribers

### Test 2: Sync Existing Subscribers (if any)
```bash
# Dry run first (see what would be synced)
python manage.py sync_mailerlite --dry-run

# Actually sync
python manage.py sync_mailerlite
```

## 6. Verify Everything Works

✅ **Check Local Database**: Django Admin → Newsletter Subscribers  
✅ **Check MailerLite**: Dashboard → Subscribers  
✅ **Test Duplicate**: Try subscribing with same email twice (should show "already subscribed")  

## 7. Create Your First Campaign (Optional)

1. Go to **Campaigns** → **Create campaign**
2. Choose **Email**
3. Design your welcome email or newsletter
4. Select your subscriber group
5. Send test email to yourself
6. Schedule or send

## Features Now Available

### Automatic Sync
- ✅ New signups on your website automatically go to MailerLite
- ✅ Local backup in Django database (if MailerLite is down)
- ✅ Duplicate detection (won't add same email twice)

### Manual Management
- View all subscribers in Django admin
- Export emails for bulk operations
- Sync historical subscribers with management command

### Future Integration Ideas
- Send automatic email when blog post is published
- Welcome email automation in MailerLite
- Segment subscribers (hobbyists vs businesses)
- A/B testing campaigns

## Troubleshooting

### "MailerLite is not configured" Error
- Check environment variables are set: `echo $env:MAILERLITE_API_KEY`
- Restart Django server after setting env vars

### "API request failed" Error
- Verify API key is correct
- Check your internet connection
- Verify API key has correct permissions in MailerLite

### Subscribers Not Appearing in MailerLite
- Check MailerLite dashboard for any account issues
- Verify email addresses are valid
- Check Django logs for error messages

## Next Steps

1. **Set up automation in MailerLite**:
   - Welcome email for new subscribers
   - Weekly/monthly newsletter schedule

2. **Create email templates**:
   - Blog post notification template
   - Recycling tips series
   - Product launch announcements

3. **Segment your audience**:
   - Create separate groups for hobbyists vs businesses
   - Tag subscribers based on interests

4. **Build campaigns**:
   - Launch announcement
   - Educational series on recycling
   - Success stories from customers

## Resources

- [MailerLite Documentation](https://www.mailerlite.com/help)
- [MailerLite API Docs](https://developers.mailerlite.com/docs/)
- [Email Marketing Best Practices](https://www.mailerlite.com/blog/email-marketing-best-practices)

---

**Need Help?** Check the Django logs or MailerLite support if you run into issues!
