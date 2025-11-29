"""
Tests for Waste Transfer Notice (WTN) functionality including:
- WTN form display and signing
- Admin countersignature workflow
- PDF generation
- Email reminder system
- Spam prevention
- Flag reset on signing
"""
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from io import StringIO
from django.core.management import call_command
from unittest.mock import patch, MagicMock
import os
from django.conf import settings

from store.models import Customer, IncomingParcel, ShippingAddress
from store.emails import send_wtn_reminder_email
from store.wtn_pdf import generate_wtn_pdf


@pytest.mark.django_db
class TestWTNFormAndSigning:
    """Test WTN form display and customer signing"""
    
    @pytest.fixture
    def business_customer(self):
        """Create a business customer with saved address"""
        user = User.objects.create_user(
            username='testbusiness',
            email='business@test.com',
            password='pass123'
        )
        customer = Customer.objects.create(
            user=user,
            name='Test Business',
            email='business@test.com',
            is_business=True,
            subscription_active=True,
            subscription_type='TIER1'
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
        return customer
    
    @pytest.fixture
    def parcel(self, business_customer):
        """Create an IncomingParcel for testing"""
        return IncomingParcel.objects.create(
            user=business_customer.user,
            address='123 Test St, TestCity',
            collection_scheduled_date=timezone.now().date() + timedelta(days=3),
            status='awaiting'
        )
    
    def test_wtn_form_loads_for_authorized_user(self, client, business_customer, parcel):
        """WTN form should load for the parcel owner"""
        client.force_login(business_customer.user)
        response = client.get(reverse('store:waste_transfer_notice', args=[parcel.id]))
        
        assert response.status_code == 200
        assert 'Waste Transfer Notice' in response.content.decode()
        assert business_customer.name in response.content.decode()
    
    def test_wtn_form_requires_login(self, client, parcel):
        """WTN form should redirect to login if not authenticated"""
        response = client.get(reverse('store:waste_transfer_notice', args=[parcel.id]))
        assert response.status_code == 302
        assert '/login' in response.url
    
    def test_wtn_form_rejects_other_users_parcel(self, client, parcel):
        """WTN form should 404 if accessing another user's parcel"""
        other_user = User.objects.create_user(username='other', password='pass123')
        client.force_login(other_user)
        
        response = client.get(reverse('store:waste_transfer_notice', args=[parcel.id]))
        assert response.status_code == 404
    
    def test_wtn_signing_success(self, client, business_customer, parcel):
        """Signing WTN with valid data should save signature and weight"""
        client.force_login(business_customer.user)
        
        data = {
            'estimated_weight': '5.5',
            'signature_data': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...'
        }
        
        response = client.post(
            reverse('store:waste_transfer_notice', args=[parcel.id]),
            data
        )
        
        # Should redirect to profile
        assert response.status_code == 302
        assert response.url == reverse('store:profile')
        
        # Check parcel was updated
        parcel.refresh_from_db()
        assert parcel.estimated_weight == 5.5
        assert parcel.wtn_signature == data['signature_data']
        assert parcel.wtn_signed_date is not None
        assert parcel.wtn_reference == f"WTN-{parcel.id:06d}"
        
        # Check spam prevention flags were reset
        assert parcel.wtn_reminder_sent == False
        assert parcel.wtn_reminder_sent_date is None
    
    def test_wtn_signing_resets_reminder_flags(self, client, business_customer, parcel):
        """Signing WTN should reset reminder flags even if they were set"""
        # Set reminder flags as if email was sent
        parcel.wtn_reminder_sent = True
        parcel.wtn_reminder_sent_date = timezone.now()
        parcel.save()
        
        client.force_login(business_customer.user)
        
        data = {
            'estimated_weight': '5.5',
            'signature_data': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...'
        }
        
        client.post(reverse('store:waste_transfer_notice', args=[parcel.id]), data)
        
        parcel.refresh_from_db()
        assert parcel.wtn_reminder_sent == False
        assert parcel.wtn_reminder_sent_date is None
    
    def test_wtn_signing_requires_weight(self, client, business_customer, parcel):
        """Signing without weight should show error"""
        client.force_login(business_customer.user)
        
        data = {
            'estimated_weight': '',
            'signature_data': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...'
        }
        
        response = client.post(
            reverse('store:waste_transfer_notice', args=[parcel.id]),
            data
        )
        
        assert response.status_code == 200
        assert 'Please enter the estimated weight' in response.content.decode()
    
    def test_wtn_signing_requires_signature(self, client, business_customer, parcel):
        """Signing without signature should show error"""
        client.force_login(business_customer.user)
        
        data = {
            'estimated_weight': '5.5',
            'signature_data': ''
        }
        
        response = client.post(
            reverse('store:waste_transfer_notice', args=[parcel.id]),
            data
        )
        
        assert response.status_code == 200
        assert 'Please provide your signature' in response.content.decode()
    
    def test_wtn_signing_validates_weight_range(self, client, business_customer, parcel):
        """Weight must be between 0.1 and 30 kg"""
        client.force_login(business_customer.user)
        
        # Test too heavy
        data = {
            'estimated_weight': '50',
            'signature_data': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...'
        }
        response = client.post(
            reverse('store:waste_transfer_notice', args=[parcel.id]),
            data
        )
        assert 'Weight must be between 0.1 kg and 30 kg' in response.content.decode()
        
        # Test zero weight
        data['estimated_weight'] = '0'
        response = client.post(
            reverse('store:waste_transfer_notice', args=[parcel.id]),
            data
        )
        assert 'Weight must be between 0.1 kg and 30 kg' in response.content.decode()


@pytest.mark.django_db
class TestWTNAdminWorkflow:
    """Test admin countersignature and approval"""
    
    @pytest.fixture
    def signed_parcel(self):
        """Create a parcel with customer signature"""
        user = User.objects.create_user(username='customer', password='pass123')
        customer = Customer.objects.create(
            user=user,
            name='Test Customer',
            email='customer@test.com',
            is_business=True
        )
        
        parcel = IncomingParcel.objects.create(
            user=user,
            address='123 Test St',
            collection_scheduled_date=timezone.now().date() + timedelta(days=3),
            status='awaiting',
            estimated_weight=5.5,
            wtn_signature='data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...',
            wtn_signed_date=timezone.now(),
            wtn_reference='WTN-000001'
        )
        return parcel
    
    def test_admin_can_countersign_wtn(self, signed_parcel, admin_user):
        """Admin should be able to countersign WTN via save_model"""
        from django.contrib.admin.sites import AdminSite
        from store.admin import IncomingParcelAdmin
        from django.test import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage
        
        # Create request
        factory = RequestFactory()
        request = factory.post('/admin/store/incomingparcel/{}/change/'.format(signed_parcel.pk))
        request.user = admin_user
        
        # Add messages framework
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        # Create admin instance
        admin_site = AdminSite()
        parcel_admin = IncomingParcelAdmin(IncomingParcel, admin_site)
        
        # Set admin signature and approval
        signed_parcel.wtn_admin_signature = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...'
        signed_parcel.wtn_admin_approved = True
        
        # Create a mock form
        form = MagicMock()
        
        # Call save_model
        parcel_admin.save_model(request, signed_parcel, form, change=True)
        
        # Check parcel was approved
        signed_parcel.refresh_from_db()
        assert signed_parcel.wtn_admin_approved == True
        assert signed_parcel.wtn_admin_approved_date is not None
        assert signed_parcel.wtn_pdf_path is not None


@pytest.mark.django_db
class TestWTNPDFGeneration:
    """Test WTN PDF generation with ReportLab"""
    
    @pytest.fixture
    def signed_parcel(self):
        """Create a parcel ready for PDF generation"""
        user = User.objects.create_user(username='customer', password='pass123')
        customer = Customer.objects.create(
            user=user,
            name='Test Customer',
            email='customer@test.com',
            is_business=True
        )
        
        parcel = IncomingParcel.objects.create(
            user=user,
            address='123 Test St, TestCity, TE1 1ST',
            collection_scheduled_date=timezone.now().date() + timedelta(days=7),
            status='awaiting',
            estimated_weight=5.5,
            wtn_signature='data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...',
            wtn_signed_date=timezone.now(),
            wtn_reference='WTN-000001',
            wtn_admin_approved=True,
            wtn_admin_signature='data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...',
            wtn_admin_approved_date=timezone.now()
        )
        return parcel
    
    def test_generate_wtn_pdf_creates_file(self, signed_parcel):
        """PDF generation should create a file in media/wtn_pdfs/business_folder/"""
        pdf_path = generate_wtn_pdf(signed_parcel)
        
        # Check return path is relative and includes business folder
        assert pdf_path.startswith('wtn_pdfs/')
        assert pdf_path.endswith('.pdf')
        assert '_WTN.pdf' in pdf_path  # Should have date format
        
        # Check file exists
        full_path = os.path.join(settings.MEDIA_ROOT, pdf_path)
        assert os.path.exists(full_path)
        
        # Check file has content
        file_size = os.path.getsize(full_path)
        assert file_size > 1000  # Should be at least 1KB
        
        # Cleanup
        os.remove(full_path)
    
    def test_generate_wtn_pdf_filename_format(self, signed_parcel):
        """PDF filename should match DD_MM_YYYY_WTN.pdf format"""
        pdf_path = generate_wtn_pdf(signed_parcel)
        
        # Check filename format (should be DD_MM_YYYY_WTN.pdf)
        import re
        assert re.search(r'\d{2}_\d{2}_\d{4}_WTN\.pdf$', pdf_path)
        
        # Check business folder is included
        assert f'{signed_parcel.user.id}_' in pdf_path or 'user_' in pdf_path
        
        # Cleanup
        full_path = os.path.join(settings.MEDIA_ROOT, pdf_path)
        if os.path.exists(full_path):
            os.remove(full_path)


@pytest.mark.django_db
class TestWTNEmailReminders:
    """Test WTN email reminder system"""
    
    @pytest.fixture
    def subscription_customer(self):
        """Create a subscription customer"""
        user = User.objects.create_user(
            username='subscriber',
            email='subscriber@test.com',
            password='pass123'
        )
        customer = Customer.objects.create(
            user=user,
            name='Subscriber Customer',
            email='subscriber@test.com',
            is_business=True,
            subscription_active=True,
            subscription_type='TIER1',
            preferred_delivery_day=timezone.now().date() + timedelta(days=3)
        )
        return customer
    
    @patch('store.emails.send_mail')
    def test_send_wtn_reminder_email(self, mock_send_mail, subscription_customer):
        """Email reminder should be sent successfully"""
        parcel = IncomingParcel.objects.create(
            user=subscription_customer.user,
            address='123 Test St',
            collection_scheduled_date=timezone.now().date() + timedelta(days=3)
        )
        
        send_wtn_reminder_email(
            subscription_customer,
            parcel,
            timezone.now().date() + timedelta(days=3)
        )
        
        # Check send_mail was called
        assert mock_send_mail.called
        call_args = mock_send_mail.call_args[1]
        
        assert 'Waste Transfer Notice' in call_args['subject']
        assert subscription_customer.email in call_args['recipient_list']
        assert 'Complete your WTN' in call_args['message']


@pytest.mark.django_db
class TestWTNReminderCommand:
    """Test send_wtn_reminders management command"""
    
    @pytest.fixture
    def subscription_customer_due_in_3_days(self):
        """Create customer with collection in 3 working days"""
        from store.management.commands.send_wtn_reminders import Command
        cmd = Command()
        target_date = cmd.add_working_days(timezone.now().date(), 3)
        
        user = User.objects.create_user(
            username='subscriber',
            email='subscriber@test.com',
            password='pass123'
        )
        customer = Customer.objects.create(
            user=user,
            name='Subscriber Customer',
            email='subscriber@test.com',
            is_business=True,
            subscription_active=True,
            subscription_type='TIER1',
            subscription_cancelled=False,
            preferred_delivery_day=target_date
        )
        return customer
    
    @patch('store.emails.send_mail')
    def test_command_sends_reminders(self, mock_send_mail, subscription_customer_due_in_3_days):
        """Command should send email to customers with collections in 3 days"""
        out = StringIO()
        call_command('send_wtn_reminders', stdout=out)
        
        output = out.getvalue()
        
        # Check email was sent
        assert mock_send_mail.called
        assert 'Sent 1 WTN reminder' in output
        assert subscription_customer_due_in_3_days.name in output
    
    @patch('store.emails.send_mail')
    def test_command_sets_reminder_sent_flag(self, mock_send_mail, subscription_customer_due_in_3_days):
        """Command should set wtn_reminder_sent flag after sending"""
        call_command('send_wtn_reminders', stdout=StringIO())
        
        # Check parcel was created and flag set
        parcel = IncomingParcel.objects.filter(
            user=subscription_customer_due_in_3_days.user
        ).first()
        
        assert parcel is not None
        assert parcel.wtn_reminder_sent == True
        assert parcel.wtn_reminder_sent_date is not None
    
    @patch('store.emails.send_mail')
    def test_command_prevents_spam(self, mock_send_mail, subscription_customer_due_in_3_days):
        """Command should NOT send email if reminder already sent"""
        # First run - should send
        call_command('send_wtn_reminders', stdout=StringIO())
        first_call_count = mock_send_mail.call_count
        
        # Second run - should skip (spam prevention)
        out = StringIO()
        call_command('send_wtn_reminders', stdout=out)
        second_call_count = mock_send_mail.call_count
        
        # Email should only be sent once
        assert second_call_count == first_call_count
        
        output = out.getvalue()
        assert 'Skipped' in output
        assert 'already sent' in output
    
    @patch('store.emails.send_mail')
    def test_command_skips_signed_wtns(self, mock_send_mail, subscription_customer_due_in_3_days):
        """Command should skip parcels with already signed WTNs"""
        # Create parcel with signed WTN
        from store.management.commands.send_wtn_reminders import Command
        cmd = Command()
        target_date = cmd.add_working_days(timezone.now().date(), 3)
        
        IncomingParcel.objects.create(
            user=subscription_customer_due_in_3_days.user,
            collection_scheduled_date=target_date,
            wtn_signed_date=timezone.now(),
            wtn_signature='data:image/png;base64,...'
        )
        
        out = StringIO()
        call_command('send_wtn_reminders', stdout=out)
        
        # Should not send email for already-signed WTN
        assert mock_send_mail.call_count == 0
    
    def test_add_working_days_skips_weekends(self):
        """add_working_days should skip Saturday and Sunday"""
        from store.management.commands.send_wtn_reminders import Command
        cmd = Command()
        
        # Test from a Friday (should skip weekend)
        friday = datetime(2025, 11, 21).date()  # Friday
        result = cmd.add_working_days(friday, 3)
        
        # 3 working days from Friday = Wednesday (skip Sat/Sun, Mon+Tue+Wed)
        wednesday = datetime(2025, 11, 26).date()
        assert result == wednesday
    
    @patch('store.emails.send_mail')
    def test_command_skips_cancelled_subscriptions(self, mock_send_mail):
        """Command should not send to cancelled subscriptions"""
        from store.management.commands.send_wtn_reminders import Command
        cmd = Command()
        target_date = cmd.add_working_days(timezone.now().date(), 3)
        
        user = User.objects.create_user(username='cancelled', password='pass123')
        Customer.objects.create(
            user=user,
            name='Cancelled Customer',
            email='cancelled@test.com',
            is_business=True,
            subscription_active=True,
            subscription_cancelled=True,  # Cancelled!
            preferred_delivery_day=target_date
        )
        
        call_command('send_wtn_reminders', stdout=StringIO())
        
        # Should not send to cancelled subscriptions
        assert mock_send_mail.call_count == 0


@pytest.mark.django_db
class TestWTNModelMethods:
    """Test IncomingParcel WTN helper methods"""
    
    def test_get_wtn_status_unsigned(self):
        """Unsigned WTN should show 'Pending' status"""
        user = User.objects.create_user(username='test', password='pass123')
        parcel = IncomingParcel.objects.create(
            user=user,
            address='123 Test St'
        )
        
        assert parcel.get_wtn_status() == 'pending'
    
    def test_get_wtn_status_signed(self):
        """Signed WTN should show 'Signed' status"""
        user = User.objects.create_user(username='test', password='pass123')
        parcel = IncomingParcel.objects.create(
            user=user,
            address='123 Test St',
            wtn_signed_date=timezone.now()
        )
        
        assert parcel.get_wtn_status() == 'signed'
    
    def test_get_wtn_status_approved(self):
        """Approved WTN should show 'Approved' status"""
        user = User.objects.create_user(username='test', password='pass123')
        parcel = IncomingParcel.objects.create(
            user=user,
            address='123 Test St',
            wtn_signed_date=timezone.now(),
            wtn_admin_approved=True
        )
        
        assert parcel.get_wtn_status() == 'approved'
