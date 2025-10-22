from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from store.models import Order, OrderStatus

class Command(BaseCommand):
    help = 'Delete abandoned carts (Potential Orders older than 2 hours with no items or abandoned for 24+ hours)'

    def handle(self, *args, **options):
        cutoff_time = timezone.now() - timedelta(hours=2)
        
        # Delete empty potential orders older than 2 hours
        empty_orders = Order.objects.filter(
            status=OrderStatus.POTENTIAL,
            date_ordered__lt=cutoff_time,
            orderitem__isnull=True
        )
        empty_count = empty_orders.count()
        empty_orders.delete()
        
        # Delete potential orders with items but abandoned for 24+ hours
        abandoned_cutoff = timezone.now() - timedelta(hours=24)
        abandoned_orders = Order.objects.filter(
            status=OrderStatus.POTENTIAL,
            date_ordered__lt=abandoned_cutoff
        )
        abandoned_count = abandoned_orders.count()
        abandoned_orders.delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Deleted {empty_count} empty carts and {abandoned_count} abandoned carts'
            )
        )