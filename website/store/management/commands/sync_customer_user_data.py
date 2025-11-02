"""
Management command to sync Customer data with User model.

This command syncs name and email fields from User model to Customer model
for all existing records, ensuring data consistency.

Usage:
    python manage.py sync_customer_user_data
    python manage.py sync_customer_user_data --dry-run  # Preview changes without saving
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from store.models import Customer


class Command(BaseCommand):
    help = 'Sync Customer name/email with User model data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving to database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))
            self.stdout.write('')
        
        customers = Customer.objects.select_related('user').all()
        total = customers.count()
        updated = 0
        skipped = 0
        errors = 0
        
        self.stdout.write(f'Found {total} customers to check...\n')
        
        for customer in customers:
            if not customer.user:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Customer "{customer.name}" (ID: {customer.id}) has no linked User - skipping')
                )
                skipped += 1
                continue
            
            user = customer.user
            needs_update = False
            changes = []
            
            # Check if name needs syncing (User -> Customer)
            user_full_name = f"{user.first_name} {user.last_name}".strip()
            if user_full_name and customer.name != user_full_name:
                changes.append(f'name: "{customer.name}" → "{user_full_name}"')
                if not dry_run:
                    customer.name = user_full_name
                needs_update = True
            
            # Check if email needs syncing (User -> Customer)
            if user.email and customer.email != user.email:
                changes.append(f'email: "{customer.email}" → "{user.email}"')
                if not dry_run:
                    customer.email = user.email
                needs_update = True
            
            if needs_update:
                try:
                    if not dry_run:
                        customer.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Updated Customer "{customer.name}" (ID: {customer.id})')
                    )
                    for change in changes:
                        self.stdout.write(f'  - {change}')
                    updated += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error updating Customer ID {customer.id}: {str(e)}')
                    )
                    errors += 1
            else:
                skipped += 1
        
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'✓ Sync complete!'))
        self.stdout.write(f'  Total customers: {total}')
        self.stdout.write(self.style.SUCCESS(f'  Updated: {updated}'))
        self.stdout.write(f'  Already in sync: {skipped - (customers.filter(user__isnull=True).count())}')
        self.stdout.write(f'  No linked user: {customers.filter(user__isnull=True).count()}')
        
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'  Errors: {errors}'))
        
        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY RUN - No changes were saved'))
            self.stdout.write('Run without --dry-run to apply changes')
