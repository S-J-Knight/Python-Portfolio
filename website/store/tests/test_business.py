"""
Tests for business customer functionality including:
- Business registration
- Business dashboard
- Business settings
- Business-only access controls
"""
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from store.models import Customer, ShippingAddress, IncomingParcel, ParcelMaterial, PlasticType


@pytest.mark.django_db
class TestBusinessRegistration:
    """Test business customer registration"""
    
    def test_business_registration_page_loads(self, client):
        """Business registration page should load for all users"""
        response = client.get(reverse('store:business_register'))
        assert response.status_code == 200
        assert 'Business Registration' in response.content.decode()
    
    def test_business_registration_creates_business_customer(self, client):
        """Registering should create a user with is_business=True"""
        data = {
            'company_name': 'Test Corp',
            'contact_name': 'John Doe',
            'username': 'testcorp',
            'email': 'test@testcorp.com',
            'phone': '01234567890',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'subscription_type': 'PAYG',
            'address_road': '123 Test Street',
            'address_city': 'TestCity',
            'address_county': 'TestCounty',
            'postcode': 'TE1 1ST',
        }
        response = client.post(reverse('store:business_register'), data)
        
        # Should redirect to business dashboard
        assert response.status_code == 302
        assert response.url == reverse('store:business_dashboard')
        
        # Check user was created
        user = User.objects.get(username='testcorp')
        assert user.email == 'test@testcorp.com'
        
        # Check customer is business
        customer = Customer.objects.get(user=user)
        assert customer.is_business is True
        assert customer.name == 'Test Corp'
        assert customer.subscription_type == 'PAYG'
        assert customer.subscription_active is False  # PAYG doesn't activate subscription
        
        # Check address was saved
        address = ShippingAddress.objects.get(customer=customer, is_saved=True)
        assert address.address == '123 Test Street'
        assert address.postcode == 'TE1 1ST'
    
    def test_business_registration_validates_required_fields(self, client):
        """Business registration should require all fields"""
        data = {
            'company_name': '',  # Missing
            'username': 'testuser',
            'email': 'test@test.com',
        }
        response = client.post(reverse('store:business_register'), data)
        assert response.status_code == 200
        assert 'Company name is required' in response.content.decode()
    
    def test_business_registration_preserves_form_data_on_error(self, client):
        """Form should preserve data when validation fails"""
        data = {
            'company_name': 'Test Corp',
            'contact_name': 'John Doe',
            'username': 'testcorp',
            'email': 'test@testcorp.com',
            'phone': '01234567890',
            'password1': 'weak',  # Too short
            'password2': 'weak',
            'subscription_type': 'PAYG',
            'address_road': '123 Test Street',
            'address_city': 'TestCity',
            'address_county': 'TestCounty',
            'postcode': 'TE1 1ST',
        }
        response = client.post(reverse('store:business_register'), data)
        
        # Should show error but preserve data
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Test Corp' in content
        assert 'testcorp' in content
        # Passwords should NOT be preserved (security)
        assert 'value="weak"' not in content
    
    def test_business_registration_local_subscription_requires_eligible_postcode(self, client):
        """Local subscription should only work with EX1-EX7 postcodes"""
        data = {
            'company_name': 'Test Corp',
            'contact_name': 'John Doe',
            'username': 'testcorp',
            'email': 'test@testcorp.com',
            'phone': '01234567890',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'subscription_type': 'Local Subscription',
            'address_road': '123 Test Street',
            'address_city': 'TestCity',
            'address_county': 'TestCounty',
            'postcode': 'SW1A 1AA',  # Not eligible
        }
        response = client.post(reverse('store:business_register'), data)
        
        # Should show error
        assert response.status_code == 200
        assert 'only available for postcodes' in response.content.decode()
    
    def test_business_registration_local_subscription_accepts_eligible_postcode(self, client):
        """Local subscription should work with EX1-EX7 postcodes"""
        data = {
            'company_name': 'Test Corp',
            'contact_name': 'John Doe',
            'username': 'testcorp',
            'email': 'test@testcorp.com',
            'phone': '01234567890',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'subscription_type': 'Local Subscription',
            'address_road': '123 Test Street',
            'address_city': 'Exeter',
            'address_county': 'Devon',
            'postcode': 'EX1 1AA',  # Eligible
        }
        response = client.post(reverse('store:business_register'), data)
        
        # Should succeed
        assert response.status_code == 302
        customer = Customer.objects.get(email='test@testcorp.com')
        assert customer.subscription_type == 'Local Subscription'
        assert customer.subscription_active is True
    
    def test_business_registration_rejects_invalid_exeter_postcodes(self, client):
        """Should reject EX10, EX40 etc (not in EX1-EX7 range)"""
        # Test EX10
        data = {
            'company_name': 'Test Corp',
            'contact_name': 'John Doe',
            'username': 'testcorp',
            'email': 'test@testcorp.com',
            'phone': '01234567890',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'subscription_type': 'Local Subscription',
            'address_road': '123 Test Street',
            'address_city': 'Exeter',
            'address_county': 'Devon',
            'postcode': 'EX10 1AA',  # Not eligible
        }
        response = client.post(reverse('store:business_register'), data)
        assert response.status_code == 200
        assert 'only available for postcodes' in response.content.decode()
    
    def test_business_registration_monthly_subscription_activates(self, client):
        """Monthly subscription should set subscription_active=True"""
        data = {
            'company_name': 'Test Corp',
            'contact_name': 'John Doe',
            'username': 'testcorp',
            'email': 'test@testcorp.com',
            'phone': '01234567890',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'subscription_type': 'Monthly Subscription',
            'address_road': '123 Test Street',
            'address_city': 'TestCity',
            'address_county': 'TestCounty',
            'postcode': 'TE1 1ST',
        }
        response = client.post(reverse('store:business_register'), data)
        
        customer = Customer.objects.get(email='test@testcorp.com')
        assert customer.subscription_active is True


@pytest.mark.django_db
class TestBusinessDashboard:
    """Test business dashboard access and display"""
    
    @pytest.fixture
    def business_user(self):
        """Create a business user"""
        user = User.objects.create_user(
            username='businessuser',
            email='business@test.com',
            password='testpass123'
        )
        customer = Customer.objects.create(
            user=user,
            name='Business Corp',
            email='business@test.com',
            is_business=True,
            subscription_type='Monthly Subscription',
            subscription_active=True
        )
        return user
    
    @pytest.fixture
    def regular_user(self):
        """Create a regular non-business user"""
        user = User.objects.create_user(
            username='regularuser',
            email='regular@test.com',
            password='testpass123'
        )
        Customer.objects.create(
            user=user,
            name='John Doe',
            email='regular@test.com',
            is_business=False
        )
        return user
    
    def test_business_dashboard_requires_login(self, client):
        """Dashboard should require authentication"""
        response = client.get(reverse('store:business_dashboard'))
        assert response.status_code == 302
        assert '/store/login/' in response.url
    
    def test_business_dashboard_loads_for_business_user(self, client, business_user):
        """Business users should access dashboard"""
        client.force_login(business_user)
        response = client.get(reverse('store:business_dashboard'))
        assert response.status_code == 200
        assert 'Business Corp' in response.content.decode()
    
    def test_business_dashboard_blocks_regular_users(self, client, regular_user):
        """Regular users should be blocked from business dashboard"""
        client.force_login(regular_user)
        response = client.get(reverse('store:business_dashboard'))
        assert response.status_code == 200
        assert 'Business Dashboard Access Required' in response.content.decode()
    
    def test_business_dashboard_shows_stats(self, client, business_user):
        """Dashboard should display waste stats"""
        client.force_login(business_user)
        
        # Create some test data
        plastic_type = PlasticType.objects.create(name='PLA', points_per_kg_basic=100, points_per_kg_premium=120)
        parcel = IncomingParcel.objects.create(
            user=business_user,
            status='received'
        )
        ParcelMaterial.objects.create(
            parcel=parcel,
            plastic_type=plastic_type,
            weight_kg=5.5
        )
        
        response = client.get(reverse('store:business_dashboard'))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Total Waste Sent' in content
        assert '5.5' in content
    
    def test_business_dashboard_shows_subscription_badge(self, client, business_user):
        """Dashboard should show subscription status"""
        client.force_login(business_user)
        response = client.get(reverse('store:business_dashboard'))
        content = response.content.decode()
        assert 'Monthly Subscription' in content
        assert 'Subscription Active' in content or '✓' in content
    
    def test_business_dashboard_has_settings_link(self, client, business_user):
        """Dashboard should have settings button"""
        client.force_login(business_user)
        response = client.get(reverse('store:business_dashboard'))
        content = response.content.decode()
        assert 'Settings' in content
        assert reverse('store:business_settings') in content


@pytest.mark.django_db
class TestBusinessSettings:
    """Test business settings page"""
    
    @pytest.fixture
    def business_user(self):
        """Create a business user with address"""
        user = User.objects.create_user(
            username='businessuser',
            email='business@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        customer = Customer.objects.create(
            user=user,
            name='Business Corp',
            email='business@test.com',
            is_business=True,
            subscription_type='PAYG'
        )
        ShippingAddress.objects.create(
            customer=customer,
            address='123 Test St',
            city='TestCity',
            county='TestCounty',
            postcode='TE1 1ST',
            country='United Kingdom',
            is_saved=True
        )
        return user
    
    def test_business_settings_requires_login(self, client):
        """Settings should require authentication"""
        response = client.get(reverse('store:business_settings'))
        assert response.status_code == 302
        assert '/store/login/' in response.url
    
    def test_business_settings_loads_for_business_user(self, client, business_user):
        """Business users should access settings"""
        client.force_login(business_user)
        response = client.get(reverse('store:business_settings'))
        assert response.status_code == 200
        assert 'Business Settings' in response.content.decode()
    
    def test_business_settings_shows_current_data(self, client, business_user):
        """Settings should display current customer data"""
        client.force_login(business_user)
        response = client.get(reverse('store:business_settings'))
        content = response.content.decode()
        assert 'Business Corp' in content
        assert 'business@test.com' in content
        assert '123 Test St' in content
    
    def test_business_settings_update_company_info(self, client, business_user):
        """Should update company information"""
        client.force_login(business_user)
        data = {
            'form_type': 'company_info',
            'company_name': 'Updated Corp',
            'contact_name': 'Jane Smith',
            'phone': '07123456789',
            'email': 'updated@test.com'
        }
        response = client.post(reverse('store:business_settings'), data)
        
        # Check redirect and success message
        assert response.status_code == 200
        assert 'updated successfully' in response.content.decode()
        
        # Check database was updated
        customer = Customer.objects.get(user=business_user)
        assert customer.name == 'Updated Corp'
        assert customer.email == 'updated@test.com'
        
        business_user.refresh_from_db()
        assert business_user.first_name == 'Jane'
        assert business_user.last_name == 'Smith'
    
    def test_business_settings_update_address(self, client, business_user):
        """Should update business address"""
        client.force_login(business_user)
        data = {
            'form_type': 'business_address',
            'address_road': '456 New Street',
            'address_city': 'NewCity',
            'address_county': 'NewCounty',
            'postcode': 'NE2 2ST'
        }
        response = client.post(reverse('store:business_settings'), data)
        
        assert response.status_code == 200
        assert 'updated successfully' in response.content.decode()
        
        # Check address was updated
        address = ShippingAddress.objects.get(customer__user=business_user, is_saved=True)
        assert address.address == '456 New Street'
        assert address.postcode == 'NE2 2ST'
    
    def test_business_settings_change_subscription(self, client, business_user):
        """Should change subscription type"""
        client.force_login(business_user)
        data = {
            'form_type': 'subscription',
            'subscription_type': 'Monthly Subscription'
        }
        response = client.post(reverse('store:business_settings'), data)
        
        assert response.status_code == 200
        
        customer = Customer.objects.get(user=business_user)
        assert customer.subscription_type == 'Monthly Subscription'
        assert customer.subscription_active is True
    
    def test_business_settings_validate_local_subscription_postcode(self, client, business_user):
        """Should validate postcode when changing to Local Subscription"""
        client.force_login(business_user)
        data = {
            'form_type': 'subscription',
            'subscription_type': 'Local Subscription'
        }
        response = client.post(reverse('store:business_settings'), data)
        
        # Should fail because postcode is TE1 1ST (not EX1-7)
        assert response.status_code == 200
        assert 'only available for postcodes' in response.content.decode()
    
    def test_business_settings_change_password(self, client, business_user):
        """Should change user password"""
        client.force_login(business_user)
        data = {
            'form_type': 'password',
            'current_password': 'testpass123',
            'new_password1': 'NewSecurePass456!',
            'new_password2': 'NewSecurePass456!'
        }
        response = client.post(reverse('store:business_settings'), data)
        
        assert response.status_code == 200
        assert 'Password changed successfully' in response.content.decode()
        
        # Check password was changed
        business_user.refresh_from_db()
        assert business_user.check_password('NewSecurePass456!')
        
        # User should still be logged in
        assert '_auth_user_id' in client.session
    
    def test_business_settings_password_requires_current_password(self, client, business_user):
        """Should validate current password before changing"""
        client.force_login(business_user)
        data = {
            'form_type': 'password',
            'current_password': 'wrongpassword',
            'new_password1': 'NewSecurePass456!',
            'new_password2': 'NewSecurePass456!'
        }
        response = client.post(reverse('store:business_settings'), data)
        
        assert response.status_code == 200
        assert 'Current password is incorrect' in response.content.decode()


@pytest.mark.django_db
class TestBusinessNavigation:
    """Test navigation for business customers"""
    
    @pytest.fixture
    def business_user(self):
        """Create a business user"""
        user = User.objects.create_user(
            username='businessuser',
            email='business@test.com',
            password='testpass123'
        )
        Customer.objects.create(
            user=user,
            name='Business Corp',
            email='business@test.com',
            is_business=True
        )
        return user
    
    @pytest.fixture
    def regular_user(self):
        """Create a regular user"""
        user = User.objects.create_user(
            username='regularuser',
            email='regular@test.com',
            password='testpass123'
        )
        Customer.objects.create(
            user=user,
            name='John Doe',
            email='regular@test.com',
            is_business=False
        )
        return user
    
    def test_business_user_sees_company_name_in_nav(self, client, business_user):
        """Business users should see company name in navigation"""
        client.force_login(business_user)
        response = client.get(reverse('home'))
        content = response.content.decode()
        assert 'Hi Business Corp' in content
        assert 'Dashboard' in content
    
    def test_regular_user_sees_username_in_nav(self, client, regular_user):
        """Regular users should see username in navigation"""
        client.force_login(regular_user)
        response = client.get(reverse('home'))
        content = response.content.decode()
        assert 'Hi regularuser' in content
        assert 'Profile' in content
    
    def test_business_user_redirected_from_profile_to_dashboard(self, client, business_user):
        """Business users accessing /profile/ should redirect to dashboard"""
        client.force_login(business_user)
        response = client.get(reverse('store:profile'))
        assert response.status_code == 302
        assert response.url == reverse('store:business_dashboard')


@pytest.mark.django_db
class TestBusinessExports:
    """Test business CSV export functionality"""
    
    @pytest.fixture
    def business_user_with_parcels(self):
        """Create business user with parcel data"""
        user = User.objects.create_user(
            username='businessuser',
            email='business@test.com',
            password='testpass123'
        )
        customer = Customer.objects.create(
            user=user,
            name='Business Corp',
            email='business@test.com',
            is_business=True
        )
        
        # Create test parcels
        plastic_type = PlasticType.objects.create(name='PLA', points_per_kg_basic=100, points_per_kg_premium=120)
        parcel = IncomingParcel.objects.create(
            user=user,
            status='received',
            points_calculated=550
        )
        ParcelMaterial.objects.create(
            parcel=parcel,
            plastic_type=plastic_type,
            weight_kg=5.5
        )
        
        return user
    
    def test_business_export_requires_login(self, client):
        """Export should require authentication"""
        response = client.get(reverse('store:business_dashboard_export'))
        assert response.status_code == 302
    
    def test_business_export_generates_csv(self, client, business_user_with_parcels):
        """Should generate CSV file"""
        client.force_login(business_user_with_parcels)
        response = client.get(reverse('store:business_dashboard_export'))
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert 'attachment' in response['Content-Disposition']
        
        # Check CSV content
        content = response.content.decode()
        assert 'Order ID' in content
        assert 'Status' in content
        assert 'Weight' in content
        assert '5.5' in content or '550' in content


@pytest.mark.django_db
class TestBusinessInvoices:
    """Test business invoices page"""
    
    @pytest.fixture
    def business_user(self):
        """Create a business user"""
        user = User.objects.create_user(
            username='businessuser',
            email='business@test.com',
            password='testpass123'
        )
        Customer.objects.create(
            user=user,
            name='Business Corp',
            email='business@test.com',
            is_business=True
        )
        return user
    
    def test_business_invoices_requires_login(self, client):
        """Invoices should require authentication"""
        response = client.get(reverse('store:business_invoices'))
        assert response.status_code == 302
    
    def test_business_invoices_loads_for_business_user(self, client, business_user):
        """Business users should access invoices"""
        client.force_login(business_user)
        response = client.get(reverse('store:business_invoices'))
        assert response.status_code == 200
