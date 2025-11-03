"""
Management command to process expired subscriptions.

This command should be run daily via cron to automatically:
- Mark expired subscriptions as inactive
- Reset subscription_setup_complete flag
- Switch to PAYG
- Clear subscription data

Usage:
    python manage.py process_expired_subscriptions
"""

from django.core.management.base import BaseCommand
from datetime import date
from store.models import Customer


class Command(BaseCommand):
    help = 'Process expired subscriptions and reset them to PAYG'

    def handle(self, *args, **options):
        today = date.today()
        
        # Find all customers with expired subscriptions
        expired_customers = Customer.objects.filter(
            is_business=True,
            subscription_cancelled=True,
            subscription_end_date__lt=today,
            subscription_active=True  # Still marked as active but expired
        )
        
        count = expired_customers.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expired subscriptions found.'))
            return
        
        # Process each expired subscription
        for customer in expired_customers:
            old_type = customer.subscription_type
            
            # Reset subscription data
            customer.subscription_active = False
            customer.subscription_type = 'PAYG'
            customer.subscription_setup_complete = False
            customer.subscription_cancelled = False
            customer.subscription_end_date = None
            
            # Don't delete box preferences or delivery day - keep for reference
            # but they'll need to go through setup again if they resubscribe
            
            customer.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Processed expired subscription for {customer.name} (was {old_type}, now PAYG)'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully processed {count} expired subscription(s).'
            )
        )
