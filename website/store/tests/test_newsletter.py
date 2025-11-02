"""
Tests for newsletter signup functionality.
"""
import pytest
from django.urls import reverse
from store.models import NewsletterSubscriber


@pytest.mark.django_db
class TestNewsletterSignup:
    """Test newsletter subscription functionality"""
    
    def test_newsletter_signup_creates_subscriber(self, client):
        """Test that newsletter signup creates a subscriber record"""
        url = reverse('store:newsletter_signup')
        data = {
            'email': 'newsletter@example.com',
            'name': 'Newsletter User'
        }
        
        resp = client.post(url, data)
        assert resp.status_code == 200
        
        json_resp = resp.json()
        assert json_resp['success'] is True
        
        # Check subscriber was created
        subscriber = NewsletterSubscriber.objects.filter(email='newsletter@example.com').first()
        assert subscriber is not None
        assert subscriber.name == 'Newsletter User'
        assert subscriber.is_active is True
    
    def test_newsletter_requires_email(self, client):
        """Test that email is required for newsletter signup"""
        url = reverse('store:newsletter_signup')
        data = {'name': 'No Email User'}
        
        resp = client.post(url, data)
        json_resp = resp.json()
        
        assert json_resp['success'] is False
        assert 'email' in json_resp['message'].lower()
    
    def test_newsletter_duplicate_rejected(self, client):
        """Test duplicate newsletter signups are rejected"""
        url = reverse('store:newsletter_signup')
        data = {
            'email': 'duplicate@example.com',
            'name': 'Duplicate User'
        }
        
        # First signup - should succeed
        resp1 = client.post(url, data)
        assert resp1.json()['success'] is True
        
        # Second signup - should be rejected
        resp2 = client.post(url, data)
        json_resp = resp2.json()
        assert json_resp['success'] is False
        assert 'already subscribed' in json_resp['message'].lower()
    
    def test_newsletter_reactivates_unsubscribed(self, client):
        """Test that previously unsubscribed users can resubscribe"""
        # Create inactive subscriber
        NewsletterSubscriber.objects.create(
            email='inactive@example.com',
            name='Inactive User',
            is_active=False
        )
        
        url = reverse('store:newsletter_signup')
        data = {
            'email': 'inactive@example.com',
            'name': 'Inactive User'
        }
        
        resp = client.post(url, data)
        json_resp = resp.json()
        
        assert json_resp['success'] is True
        assert 'reactivated' in json_resp['message'].lower() or 'Welcome back' in json_resp['message']
        
        # Check subscriber was reactivated
        subscriber = NewsletterSubscriber.objects.get(email='inactive@example.com')
        assert subscriber.is_active is True
    
    def test_newsletter_links_to_customer_if_logged_in(self, client, user, customer):
        """Test newsletter signup updates customer profile if logged in"""
        client.force_login(user)
        
        url = reverse('store:newsletter_signup')
        data = {
            'email': user.email,
            'name': user.get_full_name()
        }
        
        resp = client.post(url, data)
        assert resp.json()['success'] is True
        
        # Check customer newsletter flag was updated
        customer.refresh_from_db()
        assert customer.newsletter_subscribed is True


@pytest.mark.django_db
class TestNewsletterDataValidation:
    """Test newsletter data validation"""
    
    def test_newsletter_accepts_name_only_email(self, client):
        """Test newsletter works with just email (name optional)"""
        url = reverse('store:newsletter_signup')
        data = {'email': 'nameonly@example.com'}
        
        resp = client.post(url, data)
        assert resp.status_code == 200
        
        subscriber = NewsletterSubscriber.objects.filter(email='nameonly@example.com').first()
        assert subscriber is not None
    
    def test_newsletter_trims_whitespace(self, client):
        """Test that email/name whitespace is trimmed"""
        url = reverse('store:newsletter_signup')
        data = {
            'email': '  whitespace@example.com  ',
            'name': '  Whitespace User  '
        }
        
        resp = client.post(url, data)
        assert resp.json()['success'] is True
        
        subscriber = NewsletterSubscriber.objects.get(email='whitespace@example.com')
        assert subscriber.email == 'whitespace@example.com'  # No whitespace


@pytest.mark.django_db
class TestNewsletterCheckboxToggle:
    """Test newsletter checkbox subscribe/unsubscribe in profile"""
    
    def test_newsletter_checkbox_subscribe(self, client, user, customer):
        """Test ticking newsletter checkbox subscribes user"""
        client.force_login(user)
        
        # Initially not subscribed
        assert customer.newsletter_subscribed is False
        
        url = reverse('store:profile')
        data = {
            'form_type': 'newsletter',
            'newsletter_subscribed': 'on'
        }
        
        resp = client.post(url, data)
        assert resp.status_code == 200
        
        # Check customer was subscribed
        customer.refresh_from_db()
        assert customer.newsletter_subscribed is True
    
    def test_newsletter_checkbox_unsubscribe(self, client, user, customer):
        """Test unticking newsletter checkbox unsubscribes user"""
        client.force_login(user)
        
        # Start with subscribed customer
        customer.newsletter_subscribed = True
        customer.save()
        
        url = reverse('store:profile')
        # Not including 'newsletter_subscribed' in POST data = checkbox unticked
        data = {'form_type': 'newsletter'}
        
        resp = client.post(url, data)
        assert resp.status_code == 200
        
        # Check customer was unsubscribed
        customer.refresh_from_db()
        assert customer.newsletter_subscribed is False
    
    def test_newsletter_checkbox_toggle_multiple_times(self, client, user, customer):
        """Test toggling newsletter checkbox multiple times works correctly"""
        client.force_login(user)
        url = reverse('store:profile')
        
        # Start unsubscribed
        assert customer.newsletter_subscribed is False
        
        # Subscribe (tick checkbox)
        client.post(url, {'form_type': 'newsletter', 'newsletter_subscribed': 'on'})
        customer.refresh_from_db()
        assert customer.newsletter_subscribed is True
        
        # Unsubscribe (untick checkbox)
        client.post(url, {'form_type': 'newsletter'})
        customer.refresh_from_db()
        assert customer.newsletter_subscribed is False
        
        # Subscribe again
        client.post(url, {'form_type': 'newsletter', 'newsletter_subscribed': 'on'})
        customer.refresh_from_db()
        assert customer.newsletter_subscribed is True
