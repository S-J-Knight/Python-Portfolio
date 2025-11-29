#!/usr/bin/env python
"""Fix PostgreSQL sequences for admin log table"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

from django.db import connection

def fix_sequences():
    """Fix all PostgreSQL sequences"""
    with connection.cursor() as cursor:
        # Fix django_admin_log sequence
        cursor.execute("""
            SELECT setval(
                pg_get_serial_sequence('django_admin_log', 'id'),
                COALESCE((SELECT MAX(id) FROM django_admin_log), 1),
                true
            );
        """)
        print("✓ Fixed django_admin_log sequence")

if __name__ == '__main__':
    fix_sequences()
    print("\nAll sequences fixed successfully!")
