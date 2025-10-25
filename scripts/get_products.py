import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

from store.models import Product

products = Product.objects.all()

for p in products:
    print(f"\n{'='*60}")
    print(f"Product: {p.name}")
    print(f"Price: £{p.price}")
    print(f"Slug: {p.slug}")
    print(f"Description:")
    print(p.description if p.description else "No description")
    print(f"{'='*60}\n")
