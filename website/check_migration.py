from store.models import Product, Customer, Order, ProductReview, IncomingParcel
print(f"✓ Products: {Product.objects.count()}")
print(f"✓ Customers: {Customer.objects.count()}")
print(f"✓ Orders: {Order.objects.count()}")
print(f"✓ Reviews: {ProductReview.objects.count()}")
print(f"✓ Incoming Parcels: {IncomingParcel.objects.count()}")
print("\n Database migration successful!")
