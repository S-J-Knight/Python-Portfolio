#!/usr/bin/env python
"""
Script to load data from JSON backup into PostgreSQL database
Handles encoding issues by reading with error handling
"""
import json
import sys
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

from django.core import serializers
from django.db import transaction

def load_data(filename):
    """Load data from JSON file with proper encoding handling"""
    print(f"Reading {filename}...")
    
    # Try different encodings
    encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'latin1']
    
    for encoding in encodings:
        try:
            with open(filename, 'r', encoding=encoding, errors='replace') as f:
                data = f.read()
            
            # Parse JSON
            objects = json.loads(data)
            print(f"✓ Successfully read file with {encoding} encoding")
            print(f"Found {len(objects)} objects to load")
            break
        except Exception as e:
            print(f"✗ Failed with {encoding}: {e}")
            continue
    else:
        print("ERROR: Could not read file with any encoding")
        return False
    
    # Load data
    print("\nLoading data into PostgreSQL...")
    try:
        with transaction.atomic():
            # Re-serialize and deserialize to use Django's loader
            json_data = json.dumps(objects)
            
            count = 0
            for obj in serializers.deserialize('json', json_data):
                obj.save()
                count += 1
                if count % 100 == 0:
                    print(f"Loaded {count} objects...")
            
            print(f"\n✓ Successfully loaded {count} objects into PostgreSQL!")
            return True
            
    except Exception as e:
        print(f"\n✗ ERROR loading data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    filename = 'data_backup_clean.json'
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    
    success = load_data(filename)
    sys.exit(0 if success else 1)
