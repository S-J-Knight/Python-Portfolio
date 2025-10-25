from store.models import ShippingAddress
from django.db.models import Count

def remove_duplicate_shipping_addresses():
    # Find orders with more than one shipping address
    duplicates = (
        ShippingAddress.objects.values('order')
        .annotate(address_count=Count('id'))
        .filter(address_count__gt=1)
    )
    for entry in duplicates:
        order_id = entry['order']
        addresses = ShippingAddress.objects.filter(order_id=order_id).order_by('date_added')
        # Keep the first, delete the rest
        for address in addresses[1:]:
            print(f"Deleting duplicate ShippingAddress id={address.id} for order {order_id}")
            address.delete()

if __name__ == "__main__":
    remove_duplicate_shipping_addresses()
    print("Duplicate shipping addresses removed.")
