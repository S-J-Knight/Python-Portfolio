"""
Management command to send WTN reminder emails
Run this daily via cron: python manage.py send_wtn_reminders
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from store.models import Customer, IncomingParcel
from store.emails import send_wtn_reminder_email


class Command(BaseCommand):
    help = 'Send WTN reminder emails 3 working days before collection'

    def handle(self, *args, **options):
        """
        Find all subscription customers with collections in 3 working days
        who haven't signed their WTN yet
        """
        today = timezone.now().date()
        target_date = self.add_working_days(today, 3)
        
        self.stdout.write(f"Checking for collections on: {target_date}")
        
        # Get all subscription customers with collection date = target_date
        customers = Customer.objects.filter(
            subscription_active=True,
            subscription_cancelled=False,
            preferred_delivery_day=target_date
        )
        
        reminders_sent = 0
        
        for customer in customers:
            # Check if they have an unsigned WTN for this collection
            # Get or create the IncomingParcel for this collection
            parcel, created = IncomingParcel.objects.get_or_create(
                user=customer.user,
                collection_scheduled_date=target_date,
                defaults={
                    'address': '',  # Will be filled from saved address
                    'status': 'awaiting'
                }
            )
            
            # Send reminder ONLY if:
            # 1. WTN not signed yet
            # 2. Reminder hasn't been sent already
            if not parcel.wtn_signed_date and not parcel.wtn_reminder_sent:
                try:
                    send_wtn_reminder_email(customer, parcel, target_date)
                    
                    # Mark reminder as sent to prevent spam
                    parcel.wtn_reminder_sent = True
                    parcel.wtn_reminder_sent_date = timezone.now()
                    parcel.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Sent WTN reminder to {customer.name} ({customer.user.email})'
                        )
                    )
                    reminders_sent += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'✗ Failed to send to {customer.name}: {str(e)}'
                        )
                    )
            elif parcel.wtn_reminder_sent:
                self.stdout.write(
                    self.style.WARNING(
                        f'⊘ Skipped {customer.name} - Reminder already sent on {parcel.wtn_reminder_sent_date.strftime("%d %b %Y")}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Complete! Sent {reminders_sent} WTN reminder(s)'
            )
        )
    
    def add_working_days(self, start_date, days_to_add):
        """Add working days (Mon-Fri) to a date"""
        current_date = start_date
        days_added = 0
        
        while days_added < days_to_add:
            current_date += timedelta(days=1)
            # Monday = 0, Sunday = 6
            if current_date.weekday() < 5:  # Monday to Friday
                days_added += 1
        
        return current_date
