import sqlite3
import os

db_path = 'db.sqlite3'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table schema
cursor.execute("PRAGMA table_info(store_incomingparcel)")
columns = cursor.fetchall()

print("store_incomingparcel columns:")
for col in columns:
    print(f"  {col[1]}: {col[2]}")

# Get latest parcel's signature
cursor.execute("SELECT id, wtn_reference, substr(wtn_signature, 1, 100) as sig_preview FROM store_incomingparcel ORDER BY id DESC LIMIT 1")
parcel = cursor.fetchone()
if parcel:
    print(f"\nLatest parcel:")
    print(f"  ID: {parcel[0]}")
    print(f"  Reference: {parcel[1]}")
    print(f"  Signature preview: {parcel[2]}")
    
    if parcel[2]:
        if parcel[2].startswith('gAAAAA'):
            print("  ⚠️ ENCRYPTED (Fernet)")
        elif parcel[2].startswith('data:image'):
            print("  ✓ Base64 data URL")
        elif parcel[2].startswith('iVBOR'):
            print("  ✓ Raw base64 PNG")
        else:
            print("  ❓ Unknown format")

conn.close()
