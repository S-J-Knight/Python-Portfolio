import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

from store.models import IncomingParcel

# Clear all signature fields
count = IncomingParcel.objects.all().update(wtn_signature='', wtn_admin_signature='')
print(f'Cleared signatures from {count} parcels')
