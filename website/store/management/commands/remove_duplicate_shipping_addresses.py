from django.core.management.base import BaseCommand
from store.models import ShippingAddress
from django.db.models import Count

class Command(BaseCommand):
    help = 'Remove duplicate shipping addresses, keeping only the first for each order.'

    def handle(self, *args, **options):
        duplicates = (
            ShippingAddress.objects.values('order')
            .annotate(address_count=Count('id'))
            .filter(address_count__gt=1)
        )
        total_deleted = 0
        for entry in duplicates:
            order_id = entry['order']
            addresses = ShippingAddress.objects.filter(order_id=order_id).order_by('date_added')
            # Keep the first, delete the rest
            for address in addresses[1:]:
                self.stdout.write(f"Deleting duplicate ShippingAddress id={address.id} for order {order_id}")
                address.delete()
                total_deleted += 1
        self.stdout.write(self.style.SUCCESS(f"Removed {total_deleted} duplicate shipping addresses."))
