# Deployment Security Guide

## ✅ What We Set Up

### 1. `.gitignore` (Root Level)
- **Location**: `c:\Users\Sam\Desktop\Python-Portfolio\.gitignore`
- **Purpose**: Tells git to NEVER track sensitive files
- **Includes**: `.env`, `.env.local`, `db.sqlite3`, `__pycache__/`, etc.

### 2. `.env` File (Website Directory)
- **Location**: `c:\Users\Sam\Desktop\Python-Portfolio\website\.env`
- **Purpose**: Stores your actual API keys and secrets
- **⚠️ NEVER COMMIT THIS TO GIT!**
- **Contains**:
  - `MAILERLITE_API_KEY` - Your actual MailerLite key
  - `SECRET_KEY` - Django secret key
  - `DEBUG` - True/False for development/production

### 3. `.env.example` (Safe to Commit)
- **Location**: `c:\Users\Sam\Desktop\Python-Portfolio\website\.env.example`
- **Purpose**: Template showing what variables are needed (without actual values)
- **✅ Safe to commit** - shows structure but no secrets

### 4. Updated `settings.py`
- Now loads environment variables from `.env` automatically
- Falls back to defaults if `.env` doesn't exist

---

## 🚀 Deploying to Production

### Option 1: Railway / Heroku / Render
These platforms use environment variables in their dashboard:

**Railway:**
1. Go to your project → Variables tab
2. Add: `MAILERLITE_API_KEY` = `your-key-here`
3. Add: `SECRET_KEY` = `new-random-secret-key`
4. Add: `DEBUG` = `False`

**Heroku:**
```bash
heroku config:set MAILERLITE_API_KEY="your-key"
heroku config:set SECRET_KEY="your-secret-key"
heroku config:set DEBUG=False
```

**Render:**
1. Dashboard → Environment → Add environment variable
2. Add each variable from your `.env` file

### Option 2: VPS (DigitalOcean, AWS, etc.)
1. SSH into your server
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   nano .env  # Edit and add your actual values
   ```
3. Secure it:
   ```bash
   chmod 600 .env  # Only owner can read/write
   ```

### Option 3: PythonAnywhere
1. Go to Web tab → Environment variables section
2. Add each variable from your `.env` file
3. Or upload `.env` file to your project directory

---

## 🔒 Security Best Practices

### DO:
✅ Keep `.env` in `.gitignore`  
✅ Commit `.env.example` (template only)  
✅ Use different API keys for dev/staging/production  
✅ Regenerate SECRET_KEY for production  
✅ Set `DEBUG=False` in production  
✅ Use environment variables in production platforms  

### DON'T:
❌ NEVER commit `.env` to git  
❌ NEVER share API keys in chat/email/screenshots  
❌ NEVER use the same SECRET_KEY in dev and production  
❌ NEVER leave `DEBUG=True` in production  
❌ NEVER hardcode secrets in settings.py  

---

## 🔄 Team Collaboration

### When someone clones your repo:
1. They copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. They add their own API keys to `.env`
3. Their `.env` stays local (not committed)

### For new team members:
1. Share API keys through secure channels (1Password, LastPass, etc.)
2. Tell them to create their `.env` from `.env.example`
3. Never share secrets via email/Slack/Discord

---

## 🆘 If You Accidentally Commit Secrets

### If you haven't pushed yet:
```bash
git reset HEAD~1  # Undo last commit
# Edit .env out of staging
git add .gitignore  # Make sure .gitignore is committed
git commit -m "Add .gitignore"
```

### If you already pushed:
1. **IMMEDIATELY regenerate all exposed keys**:
   - MailerLite: Delete old token, create new one
   - Django: Generate new SECRET_KEY
2. Remove from git history (complex - ask for help if needed)
3. Update `.env` with new keys

---

## 📋 Checklist Before Going Live

- [ ] `.env` file exists with all required variables
- [ ] `.env` is in `.gitignore`
- [ ] `.env.example` is committed (without secrets)
- [ ] `DEBUG=False` in production `.env`
- [ ] New `SECRET_KEY` generated for production
- [ ] API keys are different for dev/production
- [ ] Environment variables set in hosting platform
- [ ] Test newsletter signup on live site
- [ ] Verify MailerLite receives subscribers

---

## 🔑 Generate New SECRET_KEY

For production, generate a new secret key:

```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

Or run this command:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 📝 Current Status

✅ `.env` file created with your API key  
✅ `.gitignore` configured to exclude `.env`  
✅ `settings.py` loads from `.env` automatically  
✅ `.env.example` template created  
✅ python-dotenv installed  
✅ MailerLite integration tested and working  

**You're ready to commit your code safely!** 🎉

The `.env` file will NOT be included in git commits, keeping your API keys secure.
