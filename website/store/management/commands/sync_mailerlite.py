"""
Management command to sync newsletter subscribers to MailerLite
Usage: python manage.py sync_mailerlite
"""
from django.core.management.base import BaseCommand
from store.models import NewsletterSubscriber
from store.mailerlite import mailerlite_client


class Command(BaseCommand):
    help = 'Sync local newsletter subscribers to MailerLite'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually syncing',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if not mailerlite_client.is_configured():
            self.stdout.write(
                self.style.ERROR('MailerLite is not configured. Please set MAILERLITE_API_KEY in your environment.')
            )
            return
        
        # Get all active subscribers
        subscribers = NewsletterSubscriber.objects.filter(is_active=True)
        total = subscribers.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('No active subscribers found.'))
            return
        
        self.stdout.write(f'Found {total} active subscriber(s) to sync...\n')
        
        success_count = 0
        exists_count = 0
        failed_count = 0
        
        for subscriber in subscribers:
            if dry_run:
                self.stdout.write(f'  [DRY RUN] Would sync: {subscriber.email} ({subscriber.name or "no name"})')
                success_count += 1
            else:
                result = mailerlite_client.add_subscriber(
                    email=subscriber.email,
                    name=subscriber.name if subscriber.name else None
                )
                
                if result:
                    if result.get('status') == 'exists':
                        self.stdout.write(
                            self.style.WARNING(f'  ✓ Already in MailerLite: {subscriber.email}')
                        )
                        exists_count += 1
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Synced: {subscriber.email}')
                        )
                        success_count += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Failed: {subscriber.email}')
                    )
                    failed_count += 1
        
        # Summary
        self.stdout.write('\n' + '='*50)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'DRY RUN: {success_count} subscriber(s) would be synced'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully synced: {success_count}'))
            if exists_count > 0:
                self.stdout.write(self.style.WARNING(f'Already existed: {exists_count}'))
            if failed_count > 0:
                self.stdout.write(self.style.ERROR(f'Failed: {failed_count}'))
