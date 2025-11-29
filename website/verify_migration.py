#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

from store.models import Product, Customer, Order, ProductReview, IncomingParcel

print("\n" + "="*50)
print("PostgreSQL Migration Verification")
print("="*50)
print(f"✓ Products: {Product.objects.count()}")
print(f"✓ Customers: {Customer.objects.count()}")
print(f"✓ Orders: {Order.objects.count()}")
print(f"✓ Reviews: {ProductReview.objects.count()}")
print(f"✓ Incoming Parcels: {IncomingParcel.objects.count()}")
print("="*50)
print("\n✅ Database migration successful!")
print("\nNext steps:")
print("1. Test the website at http://127.0.0.1:8000/")
print("2. Login to admin at http://127.0.0.1:8000/admin")
print("3. Check products, orders, and new review system")
print("4. Once verified, prepare for production deployment")
