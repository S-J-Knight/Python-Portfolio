"""
Tests for Business Subscription Management Features
Tests cancellation, resubscription, custom pricing, and access control
"""
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from store.models import Customer, BusinessBoxPreference, PlasticType


class TestSubscriptionCancellation(TestCase):
    """Test subscription cancellation workflow"""
    
    def setUp(self):
        """Create test user and business customer"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testbusiness',
            email='test@business.com',
            password='testpass123'
        )
        self.customer = Customer.objects.create(
            user=self.user,
            name='Test Business Ltd',
            email='test@business.com',
            is_business=True,
            subscription_type='WEEKLY',
            subscription_active=True,
            preferred_delivery_day=date.today() + timedelta(days=7),
            subscription_setup_complete=True
        )
        
        self.client.login(username='testbusiness', password='testpass123')
    
    def test_cancel_subscription_sets_flags(self):
        """Test that cancelling subscription sets cancelled flag and end date"""
        response = self.client.post(reverse('store:business_service_management'), {
            'subscription_type': 'CANCEL_SUBSCRIPTION',
        })
        
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.subscription_cancelled)
        self.assertEqual(self.customer.subscription_end_date, self.customer.preferred_delivery_day)
        self.assertFalse(self.customer.subscription_active)
        self.assertEqual(self.customer.subscription_type, 'PAYG')
    
    def test_cancelled_subscription_maintains_access_until_end_date(self):
        """Test that cancelled subscriptions can still access subscription_setup until end date"""
        # Cancel subscription
        self.customer.subscription_cancelled = True
        self.customer.subscription_end_date = date.today() + timedelta(days=3)
        self.customer.subscription_active = False
        self.customer.save()
        
        # Should still have access
        response = self.client.get(reverse('store:subscription_setup'))
        self.assertEqual(response.status_code, 200)
    
    def test_cancelled_subscription_loses_access_after_end_date(self):
        """Test that cancelled subscriptions lose access after end date"""
        # Cancel subscription with past end date
        self.customer.subscription_cancelled = True
        self.customer.subscription_end_date = date.today() - timedelta(days=1)
        self.customer.subscription_active = False
        self.customer.save()
        
        # Should not have access
        response = self.client.get(reverse('store:subscription_setup'))
        self.assertRedirects(response, reverse('store:business_dashboard'))
    
    def test_dashboard_shows_cancellation_badge(self):
        """Test that dashboard shows cancellation status correctly"""
        # Cancel subscription
        self.customer.subscription_cancelled = True
        self.customer.subscription_end_date = date.today() + timedelta(days=7)
        self.customer.subscription_active = False
        self.customer.save()
        
        response = self.client.get(reverse('store:business_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Subscription Cancelled')
        self.assertContains(response, 'Final Collection')


class TestSubscriptionResubscription(TestCase):
    """Test resubscription after cancellation"""
    
    def setUp(self):
        """Create test user, business customer, and box preferences"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testbusiness',
            email='test@business.com',
            password='testpass123'
        )
        self.customer = Customer.objects.create(
            user=self.user,
            name='Test Business Ltd',
            email='test@business.com',
            is_business=True,
            subscription_type='PAYG',
            subscription_active=False,
            subscription_cancelled=True,
            subscription_end_date=date.today() - timedelta(days=1),  # Past end date
            preferred_delivery_day=date.today() - timedelta(days=1),
            subscription_setup_complete=True,
            multi_box_enabled=True,
            box_count=5
        )
        
        # Create some old box preferences
        plastic_type = PlasticType.objects.create(name='PET', points_per_kg_basic=100)
        for i in range(5):
            BusinessBoxPreference.objects.create(
                customer=self.customer,
                box_number=i+1,
                plastic_type=plastic_type
            )
        
        self.client.login(username='testbusiness', password='testpass123')
    
    def test_resubscription_deletes_old_boxes(self):
        """Test that resubscribing after end date deletes old box preferences"""
        # Verify we have 5 box preferences before
        self.assertEqual(BusinessBoxPreference.objects.filter(customer=self.customer).count(), 5)
        
        # Attempt to change to weekly subscription (triggers resubscription)
        response = self.client.post(reverse('store:business_service_management'), {
            'subscription_type': 'Monthly Subscription',
        })
        
        # Should redirect to subscription_setup
        self.assertRedirects(response, reverse('store:subscription_setup'))
        
        # Box preferences should be deleted
        self.customer.refresh_from_db()
        self.assertEqual(BusinessBoxPreference.objects.filter(customer=self.customer).count(), 0)
    
    def test_resubscription_resets_setup_fields(self):
        """Test that resubscribing resets subscription setup fields"""
        # Change to weekly subscription
        response = self.client.post(reverse('store:business_service_management'), {
            'subscription_type': 'Monthly Subscription',
        })
        
        self.customer.refresh_from_db()
        self.assertIsNone(self.customer.preferred_delivery_day)
        self.assertFalse(self.customer.subscription_setup_complete)
        self.assertFalse(self.customer.multi_box_enabled)
        self.assertEqual(self.customer.box_count, 1)
        self.assertFalse(self.customer.subscription_cancelled)
        self.assertIsNone(self.customer.subscription_end_date)
    
    def test_resubscription_on_end_date_not_triggered(self):
        """Test that resubscription cleanup doesn't trigger on the end date itself"""
        # Set end date to today
        self.customer.subscription_end_date = date.today()
        self.customer.save()
        
        # Create box preferences
        box_count_before = BusinessBoxPreference.objects.filter(customer=self.customer).count()
        
        # Attempt to change subscription
        response = self.client.post(reverse('store:business_settings'), {
            'form_type': 'subscription',
            'subscription_type': 'WEEKLY',
            'company_name': 'Test Business Ltd',
            'email': 'test@business.com',
        })
        
        # Box preferences should NOT be deleted (end date is today, still have access)
        box_count_after = BusinessBoxPreference.objects.filter(customer=self.customer).count()
        self.assertEqual(box_count_before, box_count_after)


class TestCustomSubscriptionPricing(TestCase):
    """Test custom subscription pricing for multi-box deals"""
    
    def setUp(self):
        """Create test user and business customer"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testbusiness',
            email='test@business.com',
            password='testpass123'
        )
        self.customer = Customer.objects.create(
            user=self.user,
            name='Test Business Ltd',
            email='test@business.com',
            is_business=True,
            subscription_active=True
        )
        
        self.client.login(username='testbusiness', password='testpass123')
    
    def test_custom_subscription_option_shown_when_set(self):
        """Test that Custom Subscription option appears when custom_subscription_price is set"""
        # Set custom price (admin would do this)
        self.customer.custom_subscription_price = 99.99
        self.customer.save()
        
        response = self.client.get(reverse('store:business_service_management'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Custom Subscription')
        self.assertContains(response, '£99.99')
    
    def test_custom_subscription_option_hidden_when_not_set(self):
        """Test that Custom Subscription option doesn't appear without custom_subscription_price"""
        # Ensure no custom price
        self.customer.custom_subscription_price = None
        self.customer.save()
        
        response = self.client.get(reverse('store:business_service_management'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Custom Subscription - £')
    
    def test_customer_can_select_custom_subscription(self):
        """Test that customer can select custom subscription when available"""
        # Set custom price
        self.customer.custom_subscription_price = 150.00
        self.customer.subscription_type = 'PAYG'
        self.customer.save()
        
        # Switch to custom subscription
        response = self.client.post(reverse('store:business_service_management'), {
            'subscription_type': 'Custom Subscription',
        })
        
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.subscription_type, 'Custom Subscription')


class TestSubscriptionSetupAccess(TestCase):
    """Test subscription setup access control"""
    
    def setUp(self):
        """Create test user and business customer"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testbusiness',
            email='test@business.com',
            password='testpass123'
        )
        self.customer = Customer.objects.create(
            user=self.user,
            name='Test Business Ltd',
            email='test@business.com',
            is_business=True
        )
        
        self.client.login(username='testbusiness', password='testpass123')
    
    def test_active_subscription_has_access(self):
        """Test that active subscriptions can access subscription_setup"""
        self.customer.subscription_active = True
        self.customer.save()
        
        response = self.client.get(reverse('store:subscription_setup'))
        self.assertEqual(response.status_code, 200)
    
    def test_cancelled_before_end_date_has_access(self):
        """Test that cancelled subscriptions before end date can access subscription_setup"""
        self.customer.subscription_active = False
        self.customer.subscription_cancelled = True
        self.customer.subscription_end_date = date.today() + timedelta(days=5)
        self.customer.save()
        
        response = self.client.get(reverse('store:subscription_setup'))
        self.assertEqual(response.status_code, 200)
    
    def test_cancelled_after_end_date_no_access(self):
        """Test that cancelled subscriptions after end date cannot access subscription_setup"""
        self.customer.subscription_active = False
        self.customer.subscription_cancelled = True
        self.customer.subscription_end_date = date.today() - timedelta(days=1)
        self.customer.save()
        
        response = self.client.get(reverse('store:subscription_setup'))
        self.assertRedirects(response, reverse('store:business_dashboard'))
    
    def test_payg_no_access(self):
        """Test that PAYG subscriptions cannot access subscription_setup"""
        self.customer.subscription_type = 'PAYG'
        self.customer.subscription_active = False
        self.customer.subscription_cancelled = False
        self.customer.save()
        
        response = self.client.get(reverse('store:subscription_setup'))
        self.assertRedirects(response, reverse('store:business_dashboard'))


class TestSubscriptionTermsDisplay(TestCase):
    """Test subscription terms and cancellation messages"""
    
    def setUp(self):
        """Create test user and business customer"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testbusiness',
            email='test@business.com',
            password='testpass123'
        )
        self.customer = Customer.objects.create(
            user=self.user,
            name='Test Business Ltd',
            email='test@business.com',
            is_business=True,
            subscription_active=True,
            preferred_delivery_day=date.today() + timedelta(days=14)
        )
        
        self.client.login(username='testbusiness', password='testpass123')
    
    def test_dashboard_shows_subscription_status(self):
        """Test that dashboard page shows subscription status"""
        response = self.client.get(reverse('store:business_dashboard'))
        self.assertEqual(response.status_code, 200)
        # Check for subscription badge
        self.assertContains(response, 'Subscription')
    
    def test_dashboard_shows_cancellation_status(self):
        """Test that dashboard page shows cancellation status when cancelled"""
        self.customer.subscription_cancelled = True
        self.customer.subscription_end_date = date.today() + timedelta(days=7)
        self.customer.subscription_active = False
        self.customer.save()
        
        response = self.client.get(reverse('store:business_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Subscription Cancelled')
        self.assertContains(response, 'Final Collection')
    
    def test_subscription_setup_shows_multi_box_message(self):
        """Test that subscription setup shows multi-box discount message"""
        self.customer.multi_box_enabled = False
        self.customer.save()
        
        response = self.client.get(reverse('store:subscription_setup'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Want more than 1 box?')
        self.assertContains(response, 'Knightcycle can offer you a discount')
        self.assertContains(response, 'collection@knightcycle.co.uk')
    
    def test_subscription_setup_hides_multi_box_message_when_enabled(self):
        """Test that multi-box message is hidden when multi_box_enabled is True"""
        self.customer.multi_box_enabled = True
        self.customer.save()
        
        response = self.client.get(reverse('store:subscription_setup'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Want more than 1 box?')
