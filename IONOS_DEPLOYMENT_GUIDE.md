# 🚀 KnightCycle IONOS Deployment Guide

**Domain**: knightcycle.co.uk  
**Hosting**: IONOS Web Hosting Plus

---

## 📋 Pre-Deployment Checklist

### ✅ Files Already Configured:
- [x] Domain added to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`
- [x] `SITE_URL` setting added for emails
- [x] Logo implemented
- [x] Cart hidden (no store yet)
- [x] Newsletter subscription integrated
- [x] Localhost URLs replaced with dynamic `SITE_URL`

### ⚠️ Still Need to Do:

---

## 🔧 Step 1: Create Environment Variables on IONOS

In your IONOS hosting panel, set these environment variables:

```bash
# Production Settings
DEBUG=False
SECRET_KEY=your-new-super-secret-key-here-generate-new-one
ALLOWED_HOSTS=knightcycle.co.uk,www.knightcycle.co.uk

# Site Configuration
SITE_URL=https://knightcycle.co.uk

# MailerLite Integration (optional for now)
MAILERLITE_API_KEY=your-mailerlite-api-key
MAILERLITE_GROUP_ID=your-group-id-if-needed

# Database (if using PostgreSQL - recommended for production)
DATABASE_URL=your-database-connection-string
```

**Generate a new SECRET_KEY:**
```python
# Run this in Python to generate a secure key:
import secrets
print(secrets.token_urlsafe(50))
```

---

## 🗄️ Step 2: Database Setup

### Option A: Keep SQLite (Simple, but not recommended for production)
- Upload `db.sqlite3` via FTP
- Ensure file permissions are correct

### Option B: Use PostgreSQL/MySQL (Recommended)
1. Create a database in IONOS panel
2. Note down credentials
3. Install database adapter:
   ```bash
   pip install psycopg2-binary  # for PostgreSQL
   # or
   pip install mysqlclient  # for MySQL
   ```
4. Update `settings.py` to use DATABASE_URL

---

## 📦 Step 3: Prepare Files for Upload

### Files to Upload (via FTP):
```
website/
├── manage.py
├── website/
├── store/
├── templates/
├── static/
├── db.sqlite3 (if using SQLite)
└── requirements.txt (create this!)
```

### Create `requirements.txt`:
```bash
cd c:\Users\havea\Desktop\Portfolio\Python-Portfolio\website
pip freeze > requirements.txt
```

### Files NOT to Upload:
- ❌ `.env` (use IONOS environment variables instead)
- ❌ `__pycache__/`
- ❌ `.pytest_cache/`
- ❌ `scripts/` (optional utility scripts)
- ❌ `tests/`
- ❌ `docs/`

---

## 🌐 Step 4: Domain Configuration

### In IONOS Dashboard:

1. **Connect Domain to Hosting**
   - Go to Domains & SSL
   - Point `knightcycle.co.uk` to your hosting space
   - Add `www.knightcycle.co.uk` as alias

2. **SSL Certificate**
   - Enable free SSL certificate in IONOS
   - Force HTTPS redirect

3. **DNS Settings** (should auto-configure, but verify):
   ```
   A Record:  knightcycle.co.uk → Your IONOS server IP
   CNAME:     www → knightcycle.co.uk
   ```

---

## 📤 Step 5: Upload via FTP

### FTP Credentials (from IONOS):
- **Host**: Usually `knightcycle.co.uk` or provided by IONOS
- **Username**: From IONOS panel
- **Password**: From IONOS panel
- **Port**: 21 (FTP) or 22 (SFTP)

### Upload Steps:
1. Connect via FileZilla or IONOS File Manager
2. Upload entire `website/` folder contents
3. Ensure file permissions are correct (755 for directories, 644 for files)

---

## 🐍 Step 6: Python Environment on IONOS

### IONOS Python Setup:
1. **Check Python Version** - IONOS should have Python 3.x
2. **Install Dependencies**:
   ```bash
   # SSH into your hosting (if available)
   pip install -r requirements.txt
   ```

3. **Run Migrations**:
   ```bash
   python manage.py migrate
   ```

4. **Collect Static Files**:
   ```bash
   python manage.py collectstatic --noinput
   ```

5. **Create Superuser**:
   ```bash
   python manage.py createsuperuser
   ```

---

## ⚙️ Step 7: Configure WSGI/ASGI

IONOS typically uses **Passenger** for Python apps. Create `.htaccess` file:

```apache
PassengerEnabled On
PassengerAppRoot /path/to/your/website
PassengerStartupFile passenger_wsgi.py
PassengerPython /path/to/python3

# Force HTTPS
RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
```

Create `passenger_wsgi.py` in website root:
```python
import sys
import os

# Add your project directory to the sys.path
project_home = '/path/to/your/website'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variable for Django settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'website.settings'

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

---

## 🔒 Step 8: Security Checklist

### In Production `.env` or Environment Variables:
- [x] `DEBUG=False` ✅ **CRITICAL**
- [x] New `SECRET_KEY` generated
- [x] `ALLOWED_HOSTS` includes your domain
- [x] SSL certificate enabled
- [x] CSRF settings configured

### Additional Security (Optional but Recommended):
```python
# Add to settings.py for production:
SECURE_SSL_REDIRECT = True  # Force HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

---

## 📧 Step 9: Email Configuration

### For Production Emails:
```python
# In settings.py or environment variables:
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.ionos.co.uk'  # Check IONOS docs for actual host
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@knightcycle.co.uk'
EMAIL_HOST_PASSWORD = 'your-email-password'
DEFAULT_FROM_EMAIL = 'noreply@knightcycle.co.uk'
```

---

## ✅ Step 10: Post-Deployment Testing

### Test These Features:
1. ✅ Homepage loads at https://knightcycle.co.uk
2. ✅ Logo displays correctly
3. ✅ User registration and login work
4. ✅ Newsletter signup works
5. ✅ Send waste form submission
6. ✅ Profile page accessible
7. ✅ Admin panel at https://knightcycle.co.uk/admin/
8. ✅ Static files (CSS, JS, images) load
9. ✅ SSL certificate active (green padlock)

### Check Logs:
- Monitor IONOS error logs for any issues
- Check Django logs if configured

---

## 🆘 Troubleshooting

### Common Issues:

**500 Internal Server Error:**
- Check `DEBUG=False` is set
- Verify `ALLOWED_HOSTS` includes your domain
- Check file permissions
- Review error logs

**Static Files Not Loading:**
- Run `python manage.py collectstatic`
- Check `STATIC_ROOT` and `STATIC_URL` settings
- Verify static files uploaded correctly

**Database Errors:**
- Ensure migrations ran: `python manage.py migrate`
- Check database credentials
- Verify database file permissions (SQLite)

**CSS/Logo Not Showing:**
- Check `{% load static %}` in templates
- Verify `STATIC_URL` setting
- Run collectstatic again

---

## 📞 IONOS Support

If you need help:
- IONOS Support: Check your IONOS dashboard for support options
- Python/Django docs: https://docs.djangoproject.com/en/stable/howto/deployment/

---

## 🎉 You're Live!

Once deployed, your site will be accessible at:
- **https://knightcycle.co.uk**
- **https://www.knightcycle.co.uk**

Remember to:
1. Set `MAILERLITE_API_KEY` when ready for newsletter integration
2. Monitor your site regularly
3. Keep Django and dependencies updated
4. Back up your database regularly

**Good luck with the launch! 🚀♻️**
