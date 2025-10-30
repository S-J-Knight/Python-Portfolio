import os
import datetime
from django.conf import settings
import django
import shutil

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

# Monthly backup directory
backup_dir = os.path.expanduser(os.path.join(os.path.dirname(__file__), 'db_backups_monthly'))
os.makedirs(backup_dir, exist_ok=True)

# Database path
from django.db import connection
db_path = connection.settings_dict['NAME']

# Create backup filename for the month (YYYY-MM)
now = datetime.datetime.now()
backup_filename = f'db_backup_{now.year}-{now.month:02d}.sqlite3'
backup_path = os.path.join(backup_dir, backup_filename)

# Only create/replace the backup for this month
shutil.copy2(db_path, backup_path)
print(f"Monthly backup created: {backup_path}")

# (Optional) Keep all monthly backups, or add logic to keep only N months if desired
