from django.core.management.base import BaseCommand
from store.models import OrderItem

class Command(BaseCommand):
    help = 'Remove orphaned OrderItems (where product is None) from the database.'

    def handle(self, *args, **options):
        count = 0
        for item in OrderItem.objects.filter(product=None):
            item.delete()
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Removed {count} orphaned OrderItems.'))
