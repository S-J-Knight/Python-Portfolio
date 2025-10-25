# 🚀 KnightCycle Deployment Quick Checklist

## Before Upload:
- [ ] Test locally with `DEBUG=False` to catch any issues
- [ ] Run `python manage.py check --deploy` for deployment checks
- [ ] Generate new `SECRET_KEY` for production
- [ ] Backup current database (if updating existing site)
- [ ] Review all environment variables needed

## On IONOS:
- [ ] Set all environment variables in hosting panel
- [ ] Upload files via FTP (exclude __pycache__, .env, tests/)
- [ ] Update paths in `passenger_wsgi.py` (line 11)
- [ ] Update paths in `.htaccess` (line 5)
- [ ] Enable SSL certificate in IONOS panel
- [ ] Point domain DNS to hosting

## After Upload:
- [ ] SSH into server (if available)
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run migrations: `python manage.py migrate`
- [ ] Collect static files: `python manage.py collectstatic`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Test website: https://knightcycle.co.uk
- [ ] Test admin: https://knightcycle.co.uk/admin/

## Post-Launch Testing:
- [ ] Homepage loads correctly
- [ ] Logo displays properly
- [ ] User registration works
- [ ] Login/logout works
- [ ] Newsletter signup works
- [ ] Send waste form works
- [ ] Profile page accessible
- [ ] Static files (CSS/JS/images) load
- [ ] SSL shows green padlock
- [ ] Email notifications send (test parcel notification)

## MailerLite Setup:
- [ ] Get API key from MailerLite dashboard
- [ ] Add `MAILERLITE_API_KEY` to environment variables
- [ ] Test newsletter subscription
- [ ] Verify subscriber appears in MailerLite

## Monitoring:
- [ ] Set up error monitoring
- [ ] Check IONOS logs regularly
- [ ] Monitor database size
- [ ] Set up automated backups

## Optional (But Recommended):
- [ ] Switch to PostgreSQL database
- [ ] Set up Django logging
- [ ] Configure email alerts for errors
- [ ] Add Google Analytics
- [ ] Create sitemap.xml
- [ ] Submit to Google Search Console

---

**Need Help?**
- See: IONOS_DEPLOYMENT_GUIDE.md for detailed instructions
- IONOS Support: Check your hosting panel
- Django Deployment Docs: https://docs.djangoproject.com/en/stable/howto/deployment/
