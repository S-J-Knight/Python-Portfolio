"""
Shared pytest fixtures and configuration for all tests.
"""
import pytest
from django.contrib.auth.models import User
from store.models import Customer, Product, PlasticType
from decimal import Decimal


@pytest.fixture
def user(db):
    """Create a test user"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def staff_user(db):
    """Create a staff user for admin tests"""
    return User.objects.create_user(
        username='staffuser',
        email='staff@example.com',
        password='staffpass123',
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def customer(user):
    """Create a customer linked to user"""
    customer, _ = Customer.objects.get_or_create(
        user=user,
        defaults={
            'name': 'Test User',
            'email': 'test@example.com',
            'total_points': 0
        }
    )
    return customer


@pytest.fixture
def customer_with_points(user):
    """Create a customer with points"""
    customer, _ = Customer.objects.get_or_create(
        user=user,
        defaults={
            'name': 'Test User',
            'email': 'test@example.com',
            'total_points': 500
        }
    )
    return customer


@pytest.fixture
def product(db):
    """Create a test product"""
    return Product.objects.create(
        name='Test Product',
        slug='test-product',
        price=Decimal('10.00'),
        stock_quantity=10,
        description='Test description'
    )


@pytest.fixture
def products(db):
    """Create multiple test products"""
    return [
        Product.objects.create(
            name=f'Product {i}',
            slug=f'product-{i}',
            price=Decimal(f'{i * 5}.00'),
            stock_quantity=10
        )
        for i in range(1, 4)
    ]


@pytest.fixture
def plastic_types(db):
    """Create plastic types for recycling tests"""
    pla = PlasticType.objects.create(
        name='PLA',
        points_per_kg_basic=100,
        points_per_kg_premium=120
    )
    petg = PlasticType.objects.create(
        name='PETG',
        points_per_kg_basic=200,
        points_per_kg_premium=240
    )
    return {'pla': pla, 'petg': petg}
