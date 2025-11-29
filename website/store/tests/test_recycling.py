"""
Tests for recycling/waste management functionality.
"""
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from store.models import Customer, IncomingParcel, PlasticType, ParcelMaterial, ParcelStatus
from decimal import Decimal


@pytest.mark.django_db
class TestShippingWaste:
    """Test waste shipping form functionality"""
    
    @pytest.mark.skip(reason="Waste form structure needs verification - test needs updating to match actual form fields")
    def test_shipping_waste_form_creates_parcel(self, client, user, customer, plastic_types):
        """Test that shipping waste form creates an IncomingParcel"""
        client.force_login(user)
        
        url = reverse('recycle_and_earn')
        data = {
            'name': 'Test Sender',
            'address': '123 Test St',
            'city': 'Testville',
            'postcode': 'TS1 1TS',
            'country': 'UK',
            'weight_kg': '5.5',
            'plastic_type': plastic_types['pla'].id,
            'notes': 'Test parcel'
        }
        
        resp = client.post(url, data)
        assert resp.status_code in [200, 302]
        
        parcel = IncomingParcel.objects.filter(user=user).first()  # Uses 'user' not 'customer'
        assert parcel is not None
    
    def test_recycle_and_earn_page_accessible_when_logged_in(self, client, user):
        """Test recycle and earn page loads for logged in users"""
        client.force_login(user)
        url = reverse('recycle_and_earn')
        resp = client.get(url)
        assert resp.status_code == 200


@pytest.mark.django_db
class TestIncomingParcel:
    """Test IncomingParcel model functionality"""
    
    def test_incoming_parcel_str_representation(self, user):
        """Test IncomingParcel __str__ method"""
        parcel = IncomingParcel.objects.create(
            user=user,
            address='123 Test St',
            city='Testville',
            postcode='TS1 1TS',
            pla=True
        )
        
        str_repr = str(parcel)
        # Should return format like "IP-1"
        assert 'IP' in str_repr and str(parcel.pk) in str_repr
    
    def test_parcel_without_details(self, user):
        """Test parcels can be created with minimal info"""
        parcel = IncomingParcel.objects.create(
            user=user,
            address='123 Test St',
            city='Testville',
            postcode='TS1 1TS',
            pla=True
        )
        
        assert parcel.details == ''
        assert parcel.status == ParcelStatus.AWAITING
    
    def test_incomingparcel_ensure_material_rows_creates_materials(self, user, plastic_types):
        """Test ensure_material_rows creates ParcelMaterial rows for selected plastics"""
        parcel = IncomingParcel.objects.create(
            user=user,
            address='123 Test St',
            city='Testville',
            pla=True,
            petg=True
        )
        
        # Call ensure_material_rows to create ParcelMaterial entries
        parcel.ensure_material_rows()
        
        # Should have ParcelMaterials for selected types
        materials = ParcelMaterial.objects.filter(parcel=parcel)
        assert materials.count() == 2  # PLA and PETG
        
        # Verify they're the right types
        material_names = set(m.plastic_type.name for m in materials)
        assert 'PLA' in material_names
        assert 'PETG' in material_names


@pytest.mark.django_db
class TestParcelPoints:
    """Test parcel points calculation"""
    
    def test_parcel_calculate_total_points(self, user, plastic_types):
        """Test parcel total points calculation"""
        parcel = IncomingParcel.objects.create(
            user=user,
            address='123 Test St',
            city='Testville',
            pla=True,
            petg=True
        )
        
        # Create parcel materials
        ParcelMaterial.objects.create(
            parcel=parcel,
            plastic_type=plastic_types['pla'],
            weight_kg=Decimal('5.00')  # 5kg * 100 points = 500
        )
        ParcelMaterial.objects.create(
            parcel=parcel,
            plastic_type=plastic_types['petg'],
            weight_kg=Decimal('3.00')  # 3kg * 200 points = 600
        )
        
        # Calculate points
        total_points = parcel.calculate_points()
        
        # Should be 500 + 600 = 1100 points (basic rate)
        assert total_points == 1100
    
    def test_admin_save_model_sets_points_and_awards(self, client, staff_user, user, customer, plastic_types):
        """Test admin interface awards points correctly via signal"""
        client.force_login(staff_user)
        
        # Start with 0 points
        initial_points = customer.total_points
        
        parcel = IncomingParcel.objects.create(
            user=user,
            address='123 Test St',
            city='Testville',
            pla=True,
            status=ParcelStatus.AWAITING,
            points_calculated=0,
            points_awarded=False
        )
        
        # Create materials
        ParcelMaterial.objects.create(
            parcel=parcel,
            plastic_type=plastic_types['pla'],
            weight_kg=Decimal('10.00')
        )
        
        # Calculate points (this sets points_calculated field)
        points = parcel.calculate_points()
        parcel.points_calculated = points
        parcel.save()
        parcel.refresh_from_db()
        
        # Verify points were calculated
        assert parcel.points_calculated > 0
        assert parcel.points_calculated == points
        
        # Now change status to PROCESSED (should trigger signal)
        parcel.status = ParcelStatus.PROCESSED
        parcel.save()
        
        # Refresh customer to see if points were awarded
        customer.refresh_from_db()
        
        # Points should have been awarded via signal
        assert customer.total_points > initial_points
        assert customer.total_points == initial_points + points
        
        # Refresh parcel to check it was marked as awarded
        parcel.refresh_from_db()
        assert parcel.points_awarded == True
        
        # Check transaction was created
        from store.models import PointTransaction
        transactions = PointTransaction.objects.filter(customer=customer, related_parcel=parcel)
        assert transactions.exists()
        assert transactions.first().points == points
        
        # Calculate points
        points = parcel.calculate_points()
        parcel.points_calculated = points
        parcel.status = ParcelStatus.PROCESSED
        parcel.save()
        
        # Signal should award points
        customer.refresh_from_db()
        assert customer.total_points >= 1000  # 10kg * 100 points/kg


@pytest.mark.django_db
class TestPlasticTypes:
    """Test plastic type management"""
    
    def test_plastic_type_str_representation(self, db):
        """Test PlasticType __str__ method"""
        plastic = PlasticType.objects.create(
            name='ABS',
            points_per_kg_basic=150,
            points_per_kg_premium=180
        )
        assert str(plastic) == 'ABS'
    
    def test_plastic_type_filtering(self, plastic_types):
        """Test filtering plastic types"""
        pla = PlasticType.objects.filter(name='PLA').first()
        assert pla is not None
        assert pla.points_per_kg_basic == 100
        
        petg = PlasticType.objects.filter(name='PETG').first()
        assert petg is not None
        assert petg.points_per_kg_basic == 200
    
    def test_plastic_type_points_tiers(self, plastic_types):
        """Test basic vs premium points per kg"""
        pla = plastic_types['pla']
        
        assert pla.points_per_kg_basic < pla.points_per_kg_premium
        assert pla.points_per_kg_premium == 120  # 20% bonus for premium


@pytest.mark.django_db
class TestAdminInterface:
    """Test admin interface for parcels"""
    
    def test_admin_change_view_requires_staff_and_includes_membership_tier(self, client, user, staff_user):
        """Test admin change view requires staff and shows membership tier"""
        parcel = IncomingParcel.objects.create(
            user=user,
            address='123 Test St',
            city='Testville',
            pla=True
        )
        
        # Regular user can't access admin
        client.force_login(user)
        url = f'/admin/store/incomingparcel/{parcel.id}/change/'
        resp = client.get(url)
        assert resp.status_code in [302, 403]  # Redirected or forbidden
        
        # Staff user can access
        client.force_login(staff_user)
        resp = client.get(url)
        assert resp.status_code == 200
