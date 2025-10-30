import os
import datetime
from django.conf import settings
import django
import shutil

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

# Backup directory
backup_dir = os.path.expanduser(os.path.join(os.path.dirname(__file__), 'db_backups'))
os.makedirs(backup_dir, exist_ok=True)

# Database path
from django.db import connection
db_path = connection.settings_dict['NAME']

# Create backup filename
now = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
backup_path = os.path.join(backup_dir, f'db_backup_{now}.sqlite3')

# Copy database file
shutil.copy2(db_path, backup_path)
print(f"Backup created: {backup_path}")

# Keep only the 14 most recent backups
backups = sorted([
    os.path.join(backup_dir, f) for f in os.listdir(backup_dir)
    if f.startswith('db_backup_') and f.endswith('.sqlite3')
], key=os.path.getmtime)

if len(backups) > 14:
    for old_backup in backups[:-14]:
        os.remove(old_backup)
        print(f"Deleted old backup: {old_backup}")
