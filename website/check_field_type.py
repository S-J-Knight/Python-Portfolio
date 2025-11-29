import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

from store.models import IncomingParcel

# Get the latest parcel
p = IncomingParcel.objects.latest('id')
print(f'Latest parcel ID: {p.id}')

# Check the actual field type
field = IncomingParcel._meta.get_field('wtn_signature')
print(f'\nField type: {type(field)}')
print(f'Field class: {field.__class__.__name__}')
print(f'Field module: {field.__class__.__module__}')

# Check if it's using EncryptedTextField
if 'Encrypted' in field.__class__.__name__:
    print('⚠️ STILL USING EncryptedTextField!')
else:
    print('✓ Using regular TextField')
