"""
Tests for management commands.
"""
import pytest
from io import StringIO
from django.core.management import call_command
from django.contrib.auth.models import User
from store.models import Customer


@pytest.mark.django_db
class TestSyncCustomerUserData:
    """Test sync_customer_user_data management command"""
    
    def test_sync_updates_customer_from_user(self):
        """Test command syncs User data to Customer"""
        # Create user with specific data
        user = User.objects.create_user(
            username='testuser',
            email='user@example.com',
            first_name='John',
            last_name='Doe',
            password='pass123'
        )
        
        # Create customer with outdated data
        customer = Customer.objects.create(
            user=user,
            name='Old Name',
            email='old@example.com'
        )
        
        # Run sync command
        out = StringIO()
        call_command('sync_customer_user_data', stdout=out)
        
        # Refresh customer from database
        customer.refresh_from_db()
        
        # Verify customer was synced with user data
        assert customer.name == 'John Doe'
        assert customer.email == 'user@example.com'
        
        # Check command output
        output = out.getvalue()
        assert 'Updated: 1' in output
        assert 'Sync complete' in output
    
    def test_sync_dry_run_no_changes(self):
        """Test --dry-run flag doesn't modify database"""
        user = User.objects.create_user(
            username='testuser',
            email='user@example.com',
            first_name='Jane',
            last_name='Smith',
            password='pass123'
        )
        
        customer = Customer.objects.create(
            user=user,
            name='Old Name',
            email='old@example.com'
        )
        
        original_name = customer.name
        original_email = customer.email
        
        # Run sync with dry-run
        out = StringIO()
        call_command('sync_customer_user_data', '--dry-run', stdout=out)
        
        # Refresh and verify no changes
        customer.refresh_from_db()
        assert customer.name == original_name
        assert customer.email == original_email
        
        # Check dry-run messages
        output = out.getvalue()
        assert 'DRY RUN' in output
        assert 'No changes were saved' in output
    
    def test_sync_skips_customers_without_user(self):
        """Test command handles customers with no linked user"""
        # Create customer without user
        customer = Customer.objects.create(
            name='Orphan Customer',
            email='orphan@example.com'
        )
        
        out = StringIO()
        call_command('sync_customer_user_data', stdout=out)
        
        # Customer should remain unchanged
        customer.refresh_from_db()
        assert customer.name == 'Orphan Customer'
        
        # Check output mentions skipped customer
        output = out.getvalue()
        assert 'no linked User' in output or 'No linked user: 1' in output
    
    def test_sync_already_synced_customers(self):
        """Test command doesn't update already-synced customers"""
        user = User.objects.create_user(
            username='testuser',
            email='synced@example.com',
            first_name='Already',
            last_name='Synced',
            password='pass123'
        )
        
        # Create customer already in sync
        customer = Customer.objects.create(
            user=user,
            name='Already Synced',
            email='synced@example.com'
        )
        
        out = StringIO()
        call_command('sync_customer_user_data', stdout=out)
        
        output = out.getvalue()
        assert 'Already in sync: 1' in output
        assert 'Updated: 0' in output
    
    def test_sync_handles_empty_user_name(self):
        """Test command handles users with no first/last name"""
        user = User.objects.create_user(
            username='noname',
            email='noname@example.com',
            password='pass123'
        )
        # No first_name or last_name set
        
        customer = Customer.objects.create(
            user=user,
            name='Has Name',
            email='old@example.com'
        )
        
        out = StringIO()
        call_command('sync_customer_user_data', stdout=out)
        
        # Email should sync, but name should remain if user has no name
        customer.refresh_from_db()
        assert customer.email == 'noname@example.com'
        # Name stays as-is because user has no name to sync
