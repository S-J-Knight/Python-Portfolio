import os
import shutil
import sys
from django.conf import settings
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

# Usage: python restore_db.py <backup_path>
if len(sys.argv) != 2:
    print("Usage: python restore_db.py <backup_path>")
    sys.exit(1)

backup_path = sys.argv[1]
if not os.path.isfile(backup_path):
    print(f"Backup file not found: {backup_path}")
    sys.exit(1)

from django.db import connection
db_path = connection.settings_dict['NAME']

# Make a safety backup of the current DB before restoring
safety_backup = db_path + ".pre_restore_backup"
shutil.copy2(db_path, safety_backup)
print(f"Safety backup of current DB created: {safety_backup}")

# Restore the backup
shutil.copy2(backup_path, db_path)
print(f"Database restored from: {backup_path}")
