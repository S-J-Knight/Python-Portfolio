#!/usr/bin/env python
"""Fix PostgreSQL sequences after data migration"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

from django.db import connection

def fix_sequences():
    """Reset all PostgreSQL sequences to match current max IDs"""
    with connection.cursor() as cursor:
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name LIKE 'store_%'
        """)
        
        tables = cursor.fetchall()
        
        for (table_name,) in tables:
            # Reset sequence for each table
            try:
                cursor.execute(f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table_name}', 'id'),
                        COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                        true
                    );
                """)
                result = cursor.fetchone()
                if result:
                    print(f"✓ Fixed {table_name}: sequence set to {result[0]}")
            except Exception as e:
                print(f"⚠ Skipped {table_name}: {e}")
        
        # Also fix Django's built-in tables
        for table in ['auth_user', 'auth_group', 'django_content_type', 'django_site']:
            try:
                cursor.execute(f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table}', 'id'),
                        COALESCE((SELECT MAX(id) FROM {table}), 1),
                        true
                    );
                """)
                result = cursor.fetchone()
                if result:
                    print(f"✓ Fixed {table}: sequence set to {result[0]}")
            except Exception as e:
                print(f"⚠ Skipped {table}: {e}")

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Fixing PostgreSQL Sequences")
    print("="*60)
    fix_sequences()
    print("="*60)
    print("\n✅ All sequences fixed! You can now create new records.\n")
