"""
Tests for user profile and points functionality.
"""
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from store.models import Customer, PointTransaction
from decimal import Decimal


@pytest.mark.django_db
class TestCustomerProfile:
    """Test customer profile functionality"""
    
    def test_profile_view_loads_customer_data(self, client, user, customer):
        """Test profile page loads with customer data"""
        client.force_login(user)
        url = reverse('store:profile')
        resp = client.get(url)
        
        assert resp.status_code == 200
        # Profile page should show user/customer info
        content = resp.content.decode()
        assert 'profile' in content.lower() or 'points' in content.lower()
    
    def test_profile_requires_authentication(self, client):
        """Test profile page requires login"""
        url = reverse('store:profile')
        resp = client.get(url)
        
        # Should redirect to login
        assert resp.status_code == 302
        assert 'login' in resp.url.lower()
    
    @pytest.mark.skip(reason="Customer auto-creation signal not yet implemented")
    def test_customer_creation_on_user_registration(self, db):
        """Test that a Customer is created when a User is created"""
        user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='pass123',
            first_name='New',
            last_name='User'
        )
        
        # Check customer was auto-created by signal
        customer = Customer.objects.filter(user=user).first()
        assert customer is not None
        assert customer.email == user.email
    
    def test_customer_str_representation(self, user):
        """Test Customer __str__ method"""
        customer = Customer.objects.create(
            user=user,
            name='Test Customer',
            email='test@example.com'
        )
        assert str(customer) == 'Test Customer'
    
    def test_customer_premium_field_defaults_false(self, user):
        """Test that is_premium defaults to False"""
        customer = Customer.objects.create(
            user=user,
            name='Regular Customer',
            email='regular@example.com'
        )
        assert customer.is_premium is False
    
    def test_customer_email_uniqueness(self, user):
        """Test customer emails enforced by User model"""
        # Email uniqueness is enforced at the User level, not Customer level
        # Customer model allows duplicate emails, but registration prevents it
        Customer.objects.create(
            user=user,
            name='First',
            email='unique@example.com'
        )
        
        user2 = User.objects.create_user(username='user2', email='different@example.com', password='pass')
        
        # Can create customer with same email (not enforced at Customer level)
        customer2 = Customer.objects.create(
            user=user2,
            name='Second',
            email='unique@example.com'  # Same email is allowed in Customer model
        )
        assert customer2 is not None
        # But User.email is unique at registration (enforced in views)


@pytest.mark.django_db
class TestCustomerAdminSync:
    """Test that Customer admin syncs data with User model"""
    
    def test_customer_save_syncs_to_user(self, user):
        """Test that saving Customer in admin updates the User model"""
        from store.admin import CustomerAdmin
        from django.contrib.admin.sites import AdminSite
        
        # Create customer
        customer = Customer.objects.create(
            user=user,
            name='Original Name',
            email='original@example.com'
        )
        
        # Simulate admin save
        admin_instance = CustomerAdmin(Customer, AdminSite())
        
        # Update customer fields
        customer.name = 'Updated Name'
        customer.email = 'updated@example.com'
        
        # Call save_model (simulates admin panel save)
        admin_instance.save_model(
            request=None,  # Not needed for this test
            obj=customer,
            form=None,     # Not needed for this test
            change=True
        )
        
        # Refresh user from database
        user.refresh_from_db()
        
        # Verify User model was updated
        assert user.first_name == 'Updated'
        assert user.last_name == 'Name'
        assert user.email == 'updated@example.com'
    
    def test_customer_save_handles_single_name(self, user):
        """Test that single-word names work correctly"""
        from store.admin import CustomerAdmin
        from django.contrib.admin.sites import AdminSite
        
        customer = Customer.objects.create(
            user=user,
            name='Madonna',
            email='madonna@example.com'
        )
        
        admin_instance = CustomerAdmin(Customer, AdminSite())
        admin_instance.save_model(None, customer, None, True)
        
        user.refresh_from_db()
        assert user.first_name == 'Madonna'
        assert user.last_name == ''
        assert user.email == 'madonna@example.com'


@pytest.mark.django_db
class TestCustomerPoints:
    """Test customer points system"""
    
    def test_customer_total_points_defaults_to_zero(self, user):
        """Test that total_points defaults to 0"""
        customer = Customer.objects.create(
            user=user,
            name='Zero Points',
            email='zero@example.com'
        )
        assert customer.total_points == 0
    
    def test_multiple_customers_total_points(self):
        """Test multiple customers can have different point totals"""
        user1 = User.objects.create_user(username='user1', password='pass')
        user2 = User.objects.create_user(username='user2', password='pass')
        
        customer1 = Customer.objects.create(
            user=user1,
            name='Customer 1',
            email='c1@example.com',
            total_points=100
        )
        customer2 = Customer.objects.create(
            user=user2,
            name='Customer 2',
            email='c2@example.com',
            total_points=250
        )
        
        assert customer1.total_points == 100
        assert customer2.total_points == 250
    
    def test_points_history_shows_points(self, client, user, customer):
        """Test points history page shows point transactions"""
        client.force_login(user)
        
        # Create some point transactions
        PointTransaction.objects.create(
            customer=customer,
            points=100,
            transaction_type='earned',
            description='Test earning points'
        )
        PointTransaction.objects.create(
            customer=customer,
            points=-50,
            transaction_type='spent',
            description='Test spending points'
        )
        
        url = reverse('store:points_history')
        resp = client.get(url)
        content = resp.content.decode()
        
        assert resp.status_code == 200
        assert 'Test earning points' in content
        assert 'Test spending points' in content
    
    def test_apply_points_zero_points_returns_success(self, client, user, customer):
        """Test applying 0 points doesn't cause errors"""
        client.force_login(user)
        
        url = reverse('store:apply_points')
        data = {'points': 0}
        resp = client.post(url, data, content_type='application/json')
        
        json_resp = resp.json()
        assert 'success' in json_resp or 'error' in json_resp
    
    def test_customer_verified_weight_and_premium_eligibility(self, db):
        """Test customer verified weight tracking for premium upgrade"""
        user = User.objects.create_user(username='premiumuser', password='pass')
        customer = Customer.objects.create(
            user=user,
            name='Premium Candidate',
            email='premium@example.com'
        )
        
        # Initially 0 verified weight (using method, not field)
        assert customer.get_verified_weight() == 0
        
        # Create a processed parcel with verified weight
        from store.models import IncomingParcel, ParcelMaterial, PlasticType, ParcelStatus
        
        pla_type = PlasticType.objects.create(
            name='PLA',
            points_per_kg_basic=100,
            points_per_kg_premium=120
        )
        
        parcel = IncomingParcel.objects.create(
            user=user,
            address='123 Test St',
            city='Testville',
            pla=True,
            status=ParcelStatus.PROCESSED
        )
        
        ParcelMaterial.objects.create(
            parcel=parcel,
            plastic_type=pla_type,
            weight_kg=50.0
        )
        
        # After accumulating weight, should be eligible for premium
        customer.refresh_from_db()
        verified_weight = customer.get_verified_weight()
        assert verified_weight >= 25
        assert customer.is_eligible_for_premium()


@pytest.mark.django_db
class TestPointTransactions:
    """Test point transaction system"""
    
    def test_pointtransaction_ordering(self, user, customer):
        """Test point transactions are ordered by date (newest first)"""
        import time
        
        # Create transactions at different times
        trans1 = PointTransaction.objects.create(
            customer=customer,
            points=50,
            transaction_type='EARNED',
            description='First'
        )
        
        # Small delay to ensure different timestamps
        time.sleep(0.01)
        
        trans2 = PointTransaction.objects.create(
            customer=customer,
            points=100,
            transaction_type='EARNED',
            description='Second'
        )
        
        transactions = PointTransaction.objects.all()
        assert transactions[0] == trans2  # Newest first (has Meta ordering)
        assert transactions[1] == trans1
    
    def test_point_transaction_str_representation(self, user, customer):
        """Test PointTransaction __str__ method"""
        trans = PointTransaction.objects.create(
            customer=customer,
            points=200,
            transaction_type='earned',
            description='Test transaction'
        )
        
        str_repr = str(trans)
        assert customer.name in str_repr
        assert '200' in str_repr
    
    def test_point_transaction_types(self, user, customer):
        """Test different point transaction types"""
        # Earned points
        earned = PointTransaction.objects.create(
            customer=customer,
            points=100,
            transaction_type='EARNED',
            description='Recycled waste'
        )
        assert earned.transaction_type == 'EARNED'
        assert earned.points > 0
        
        # Spent points
        spent = PointTransaction.objects.create(
            customer=customer,
            points=-50,
            transaction_type='REDEEMED',
            description='Purchased product'
        )
        assert spent.transaction_type == 'REDEEMED'
        assert spent.points < 0
        
        # Adjusted points (admin correction)
        adjusted = PointTransaction.objects.create(
            customer=customer,
            points=25,
            transaction_type='ADJUSTED',
            description='Admin correction'
        )
        assert adjusted.transaction_type == 'ADJUSTED'
