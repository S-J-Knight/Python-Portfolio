import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

from store.models import IncomingParcel

p = IncomingParcel.objects.latest('id')
print(f'Latest parcel ID: {p.id}')
print(f'WTN Reference: {p.wtn_reference}')
print(f'Customer sig length: {len(p.wtn_signature) if p.wtn_signature else 0}')
print(f'Admin sig length: {len(p.wtn_admin_signature) if p.wtn_admin_signature else 0}')

if p.wtn_signature:
    print(f'\nCustomer sig starts with: {p.wtn_signature[:100]}')
    # Check if it's encrypted (starts with gAAAAA) or base64 PNG (starts with data:image or iVBOR)
    if p.wtn_signature.startswith('gAAAAA'):
        print('⚠️ ENCRYPTED DATA DETECTED')
    elif p.wtn_signature.startswith('data:image'):
        print('✓ Looks like base64 data URL')
    elif p.wtn_signature.startswith('iVBOR'):
        print('✓ Looks like raw base64 PNG')
    else:
        print('❓ Unknown format')
