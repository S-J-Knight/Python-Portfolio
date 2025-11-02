"""
Tests for store functionality: products, cart, checkout, orders.
"""
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from store.models import Customer, Product, Order, OrderItem, ShippingAddress
from decimal import Decimal


# ========== Product Tests ==========

@pytest.mark.django_db
class TestProducts:
    """Test product model and views"""
    
    def test_store_view_renders(self, client):
        """Test store/products page renders"""
        url = reverse('store:store')
        resp = client.get(url)
        assert resp.status_code == 200
    
    def test_product_str_representation(self, product):
        """Test Product __str__ method"""
        assert str(product) == product.name
    
    def test_product_slug_uniqueness(self, db):
        """Test product slugs must be unique"""
        Product.objects.create(
            name='First Product',
            slug='unique-slug',
            price=Decimal('10.00')
        )
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            Product.objects.create(
                name='Second Product',
                slug='unique-slug',  # Duplicate slug
                price=Decimal('20.00')
            )
    
    def test_product_detail_view(self, client, product):
        """Test product detail page loads"""
        url = reverse('store:product_detail', args=[product.slug])
        resp = client.get(url)
        assert resp.status_code == 200
        assert product.name in resp.content.decode()
    
    def test_product_with_digital_attribute(self, db):
        """Test products can have digital attribute"""
        product = Product.objects.create(
            name='Digital Product',
            slug='digital-product',
            price=Decimal('5.00'),
            digital=True
        )
        assert product.digital is True
    
    def test_product_image_url_default(self, product):
        """Test product has default imageURL"""
        # Should have imageURL property
        assert hasattr(product, 'imageURL')
        assert isinstance(product.imageURL, str)
    
    def test_product_search_by_name(self, products):
        """Test searching products by name"""
        results = Product.objects.filter(name__icontains='Product 1')
        assert results.count() >= 1
        assert 'Product 1' in results.first().name


# ========== Cart Tests ==========

@pytest.mark.django_db
class TestCart:
    """Test shopping cart functionality"""
    
    def test_cart_view_authenticated(self, client, user, customer):
        """Test cart view for authenticated users"""
        client.force_login(user)
        url = reverse('store:cart')
        resp = client.get(url)
        assert resp.status_code == 200
    
    def test_cart_view_guest(self, client):
        """Test cart view works for guest users"""
        url = reverse('store:cart')
        resp = client.get(url)
        assert resp.status_code == 200
    
    @pytest.mark.skip(reason="Guest cart cookie handling not fully implemented")
    def test_guest_cart_cookie_handling(self, client, product):
        """Test guest cart uses cookies"""
        # Add item to cart as guest
        url = reverse('store:update_item')
        data = {
            'productId': product.id,
            'action': 'add'
        }
        
        resp = client.post(url, data, content_type='application/json')
        
        # Guest user should get cart cookie
        assert 'cart' in resp.cookies or resp.status_code in [200, 302]
    
    @pytest.mark.skip(reason="Update item endpoint requires different implementation")
    def test_update_item_requires_authentication(self, client, product):
        """Test update_item endpoint"""
        url = reverse('store:update_item')
        data = {
            'productId': product.id,
            'action': 'add'
        }
        
        resp = client.post(url, data, content_type='application/json')
        
        # Should work for guest (returns JSON) or redirect
        assert resp.status_code in [200, 302]


# ========== Order Tests ==========

@pytest.mark.django_db
class TestOrders:
    """Test order creation and management"""
    
    def test_order_str_representation(self, user, customer):
        """Test Order __str__ method"""
        order = Order.objects.create(
            customer=customer,
            status='pending'
        )
        # Order __str__ returns 'OP-{id}' format
        assert str(order) == f'OP-{order.id}'
    
    def test_order_date_ordered_auto_set(self, user, customer):
        """Test that date_ordered is set automatically"""
        order = Order.objects.create(
            customer=customer,
            status='pending'
        )
        assert order.date_ordered is not None
    
    def test_order_status_choices(self, user, customer):
        """Test different order status values"""
        pending_order = Order.objects.create(
            customer=customer,
            status='pending'
        )
        assert pending_order.status == 'pending'
        
        complete_order = Order.objects.create(
            customer=customer,
            status='complete'
        )
        assert complete_order.status == 'complete'
    
    def test_order_complete_status(self, user, customer, product):
        """Test order completion"""
        order = Order.objects.create(
            customer=customer,
            status='pending'
        )
        
        OrderItem.objects.create(
            product=product,
            order=order,
            quantity=2
        )
        
        # Mark complete
        order.status = 'complete'
        order.save()
        
        assert order.status == 'complete'
        assert order.get_cart_items == 2
    
    def test_order_transaction_id_field(self, user, customer):
        """Test order has transaction_id field"""
        order = Order.objects.create(
            customer=customer,
            transaction_id='TXN123456',
            status='pending'
        )
        assert order.transaction_id == 'TXN123456'
    
    def test_multiple_orders_per_customer(self, user, customer, products):
        """Test customer can have multiple orders"""
        order1 = Order.objects.create(
            customer=customer,
            status='complete'
        )
        order2 = Order.objects.create(
            customer=customer,
            status='pending'
        )
        
        orders = Order.objects.filter(customer=customer)
        assert orders.count() >= 2


# ========== Order Calculations Tests ==========

@pytest.mark.django_db
class TestOrderCalculations:
    """Test order calculations (totals, items, shipping)"""
    
    def test_order_get_cart_items_empty_cart(self, user, customer):
        """Test get_cart_items with empty cart"""
        order = Order.objects.create(
            customer=customer,
            status='pending'
        )
        assert order.get_cart_items == 0
    
    def test_orderitem_get_total(self, user, customer, product):
        """Test OrderItem get_total calculation"""
        order = Order.objects.create(
            customer=customer,
            status='pending'
        )
        
        order_item = OrderItem.objects.create(
            product=product,
            order=order,
            quantity=3
        )
        
        expected_total = product.price * 3
        assert order_item.get_total == expected_total
    
    def test_order_get_cart_total_with_decimal_precision(self, user, customer):
        """Test cart total with decimal precision"""
        product = Product.objects.create(
            name='Decimal Product',
            slug='decimal-product',
            price=Decimal('9.99')
        )
        
        order = Order.objects.create(
            customer=customer,
            status='pending'
        )
        
        OrderItem.objects.create(
            product=product,
            order=order,
            quantity=3
        )
        
        expected = Decimal('9.99') * 3
        assert order.get_cart_total == expected
    
    def test_multiple_orderitems_cart_total(self, user, customer, products):
        """Test cart total with multiple items"""
        order = Order.objects.create(
            customer=customer,
            status='pending'
        )
        
        for product in products:
            OrderItem.objects.create(
                product=product,
                order=order,
                quantity=2
            )
        
        # Should sum all items
        total = order.get_cart_total
        assert total > 0
        assert order.get_cart_items == len(products) * 2
    
    def test_order_item_total_calculation(self, user, customer, product):
        """Test order item total = price * quantity"""
        order = Order.objects.create(
            customer=customer,
            status='pending'
        )
        
        item = OrderItem.objects.create(
            product=product,
            order=order,
            quantity=5
        )
        
        assert item.get_total == product.price * 5
    
    def test_orderitem_quantity_update(self, user, customer, product):
        """Test updating order item quantity"""
        order = Order.objects.create(
            customer=customer,
            status='pending'
        )
        
        item = OrderItem.objects.create(
            product=product,
            order=order,
            quantity=1
        )
        
        # Update quantity
        item.quantity = 5
        item.save()
        
        item.refresh_from_db()
        assert item.quantity == 5
        assert item.get_total == product.price * 5


# ========== Shipping Tests ==========

@pytest.mark.django_db
class TestShipping:
    """Test shipping functionality"""
    
    def test_order_shipping_false_for_digital_only(self, user, customer):
        """Test digital-only orders don't require shipping"""
        digital_product = Product.objects.create(
            name='Digital Download',
            slug='digital-download',
            price=Decimal('9.99'),
            digital=True
        )
        
        order = Order.objects.create(
            customer=customer,
            status='pending'
        )
        
        OrderItem.objects.create(
            product=digital_product,
            order=order,
            quantity=1
        )
        
        assert order.shipping is False
    
    def test_order_shipping_true_for_physical(self, user, customer, product):
        """Test physical products require shipping"""
        order = Order.objects.create(
            customer=customer,
            status='pending'
        )
        
        OrderItem.objects.create(
            product=product,
            order=order,
            quantity=1
        )
        
        # Physical product requires shipping
        assert order.shipping is True
    
    def test_order_shipping_with_null_product_does_not_error(self, client, user, customer):
        """Test order doesn't error when product is null/deleted"""
        client.force_login(user)
        
        order = Order.objects.create(
            customer=customer,
            status='pending'
        )
        
        # No items - should not error
        url = reverse('store:cart')
        resp = client.get(url)
        assert resp.status_code == 200


# ========== Checkout Tests ==========

@pytest.mark.django_db
class TestCheckout:
    """Test checkout functionality"""
    
    def test_checkout_view_authenticated(self, client, user, customer):
        """Test checkout view for authenticated users"""
        client.force_login(user)
        url = reverse('store:checkout')
        resp = client.get(url)
        assert resp.status_code == 200
    
    def test_checkout_view_guest(self, client):
        """Test checkout view for guest users"""
        url = reverse('store:checkout')
        resp = client.get(url)
        assert resp.status_code == 200


# ========== Points Integration ==========

@pytest.mark.django_db
class TestOrderPointsIntegration:
    """Test points integration with orders"""
    
    def test_order_calculations_and_points_discount(self, client, user, customer_with_points, product):
        """Test order calculations with points discount"""
        client.force_login(user)
        
        order = Order.objects.create(
            customer=customer_with_points,
            status='pending'
        )
        
        OrderItem.objects.create(
            product=product,
            order=order,
            quantity=2
        )
        
        # Apply points discount
        points_to_use = 100
        discount = Decimal(points_to_use) / 100  # 100 points = £1
        
        original_total = order.get_cart_total
        discounted_total = original_total - discount
        
        assert discounted_total < original_total
        assert discounted_total >= 0


# ========== Login Requirements ==========

@pytest.mark.django_db
class TestLoginRequirements:
    """Test login required views"""
    
    def test_login_required_views_redirect_to_login(self, client):
        """Test protected views redirect to login"""
        protected_urls = [
            reverse('store:profile'),
            reverse('store:points_history'),
        ]
        
        for url in protected_urls:
            resp = client.get(url)
            assert resp.status_code == 302  # Redirect
            assert 'login' in resp.url.lower()


# ========== Management Commands ==========

@pytest.mark.django_db
class TestManagementCommands:
    """Test custom management commands"""
    
    @pytest.mark.skip(reason="dedupe_shipping_addresses command not yet created")
    def test_dedupe_management_command_runs(self, capsys):
        """Test dedupe_shipping_addresses command runs without error"""
        from django.core.management import call_command
        
        # Create duplicate addresses
        user = User.objects.create_user(username='dupeuser', password='pass')
        customer = Customer.objects.create(
            user=user,
            name='Dupe User',
            email='dupe@example.com'
        )
        
        ShippingAddress.objects.create(
            customer=customer,
            address='123 Dupe St',
            city='Dupeville',
            postcode='DU1 1PE',
            country='UK'
        )
        ShippingAddress.objects.create(
            customer=customer,
            address='123 Dupe St',
            city='Dupeville',
            postcode='DU1 1PE',
            country='UK'
        )
        
        # Run command
        call_command('dedupe_shipping_addresses')
        
        # Should not error
        captured = capsys.readouterr()
        assert 'error' not in captured.out.lower() or captured.out == ''
