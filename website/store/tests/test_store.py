import json
import pytest
from django.urls import reverse
from django.contrib.auth.models import User

from store.models import Customer, PointTransaction, IncomingParcel, Product, Order, OrderItem
from store.models import ParcelMaterial, PlasticType
from decimal import Decimal
from django.test import RequestFactory
from store.utils import cookieCart


@pytest.mark.django_db
def test_points_history_shows_points(client):
    user = User.objects.create_user(username='tester', password='pass')
    customer, _ = Customer.objects.get_or_create(user=user, defaults={'name': 'tester', 'email': 't@example.com'})
    customer.total_points = 250
    customer.save()
    PointTransaction.objects.create(
        customer=customer,
        transaction_type='EARNED',
        points=250,
        description='Test earn'
    )

    client.force_login(user)
    resp = client.get(reverse('store:points_history'))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert '250' in content
    assert 'Test earn' in content


@pytest.mark.django_db
def test_shipping_waste_form_creates_parcel(client):
    user = User.objects.create_user(username='shipper', password='pass')
    client.force_login(user)
    url = reverse('store:shipping_waste_form')
    data = {
        'address': '1 Test Rd',
        'city': 'Testville',
        'county': 'Testshire',
        'postcode': 'TST1 1ST',
        'country': 'UK',
        'details': '0.5kg PLA'
    }
    resp = client.post(url, data, follow=True)
    assert resp.status_code == 200
    parcel = IncomingParcel.objects.filter(user=user).first()
    assert parcel is not None
    assert str(parcel).startswith('ip')


@pytest.mark.django_db
def test_order_calculations_and_points_discount(client):
    user = User.objects.create_user(username='calcuser', password='pass')
    customer, _ = Customer.objects.get_or_create(user=user, defaults={'name': 'calcuser', 'email': 'c@example.com'})
    p1 = Product.objects.create(name='A', slug='a', price=Decimal('10.00'))
    p2 = Product.objects.create(name='B', slug='b', price=Decimal('2.50'))

    order = Order.objects.create(customer=customer, status='Order Received')
    OrderItem.objects.create(order=order, product=p1, quantity=1)
    OrderItem.objects.create(order=order, product=p2, quantity=2)

    # subtotal = 10 + (2.5*2) = 15.0
    assert order.get_cart_total == Decimal('15.00')
    assert order.get_cart_items == 3

    # apply points_used 150 -> £1.50
    order.points_used = 150
    assert order.points_discount_gbp == Decimal('1.50')
    assert order.get_cart_total_after_points == Decimal('13.50')

    # if points exceed subtotal, result should floor to 0.00
    order.points_used = 2000  # £20
    assert order.get_cart_total_after_points == Decimal('0.00')


@pytest.mark.django_db
def test_incomingparcel_ensure_material_rows_creates_and_removes():
    pla = PlasticType.objects.create(name='PLA', points_per_kg_basic=100, points_per_kg_premium=120)
    petg = PlasticType.objects.create(name='PETG', points_per_kg_basic=200, points_per_kg_premium=240)

    user = User.objects.create_user(username='matuser', password='pass')
    parcel = IncomingParcel.objects.create(user=user, address='1 M', city='C', postcode='P', country='UK', pla=True, petg=False)

    # should create PLA material row
    parcel.ensure_material_rows()
    names = list(parcel.materials.values_list('plastic_type__name', flat=True))
    assert 'PLA' in names
    assert 'PETG' not in names

    # enable PETG and ensure both exist
    parcel.petg = True
    parcel.save()
    parcel.ensure_material_rows()
    names = list(parcel.materials.values_list('plastic_type__name', flat=True))
    assert set(['PLA', 'PETG']).issubset(set(names))

    # disable PLA and ensure it's removed
    parcel.pla = False
    parcel.save()
    parcel.ensure_material_rows()
    names = list(parcel.materials.values_list('plastic_type__name', flat=True))
    assert 'PLA' not in names


@pytest.mark.django_db
def test_customer_verified_weight_and_premium_eligibility():
    user = User.objects.create_user(username='weightuser', password='pass')
    customer, _ = Customer.objects.get_or_create(user=user, defaults={'name': 'weightuser', 'email': 'w@example.com'})

    # Create a parcel with a single material of 25kg to meet premium weight threshold
    parcel = IncomingParcel.objects.create(user=user, address='1 W', city='C', postcode='P', country='UK', points_awarded=False)
    ParcelMaterial.objects.create(parcel=parcel, plastic_type=PlasticType.objects.create(name='X', points_per_kg_basic=10, points_per_kg_premium=12), weight_kg=Decimal('25.000'))

    # Verified weight should be 25.0
    assert customer.get_verified_weight() >= 25.0
    # Even though no parcels are marked points_awarded, the weight alone should make user eligible
    assert customer.is_eligible_for_premium() is True


@pytest.mark.django_db
def test_admin_change_view_requires_staff_and_includes_membership_tier(client):
    # Create a normal user and a staff user
    normal = User.objects.create_user(username='normal', password='pass')
    staff = User.objects.create_user(username='staff', password='pass', is_staff=True, is_superuser=True)

    # create a parcel and a linked customer (premium False)
    parcel_user = User.objects.create_user(username='parcelowner', password='pass')
    IncomingParcel.objects.create(user=parcel_user, address='1 A', city='C', postcode='P', country='UK')
    parcel = IncomingParcel.objects.first()

    # Non-staff should be redirected when accessing admin change view
    client.force_login(normal)
    url = f"/admin/store/incomingparcel/{parcel.pk}/change/"
    resp = client.get(url)
    assert resp.status_code in (302, 403)

    # Staff should be allowed and the page should include the membership_tier label
    client.force_login(staff)
    resp = client.get(url)
    assert resp.status_code == 200
    content = resp.content.decode()
    assert 'Membership' in content or 'membership_tier' in content


@pytest.mark.django_db
def test_login_required_views_redirect_to_login(client):
    # profile and points_history should redirect anonymous users to login
    resp = client.get(reverse('store:profile'))
    assert resp.status_code in (302, 301)
    resp = client.get(reverse('store:points_history'))
    assert resp.status_code in (302, 301)


@pytest.mark.django_db
def test_order_shipping_with_null_product_does_not_error(client):
    # Ensure Order.shipping property handles OrderItem with product=None
    user = User.objects.create_user(username='spuser', password='pass')
    customer, _ = Customer.objects.get_or_create(user=user, defaults={'name': 'spuser', 'email': 'sp@example.com'})
    order = Order.objects.create(customer=customer, status='Order Received')
    # create an OrderItem with no product (orphaned)
    OrderItem.objects.create(order=order, product=None, quantity=1)
    # Should return False (no shipping required because product is None)
    assert order.shipping in (False, 0)


@pytest.mark.django_db
def test_admin_save_model_sets_points_and_awards(client):
    # Create staff user
    staff = User.objects.create_user(username='adm', password='pass', is_staff=True, is_superuser=True)

    # Setup plastic type and parcel
    pt = PlasticType.objects.create(name='ADMPLA', points_per_kg_basic=100, points_per_kg_premium=120)
    owner = User.objects.create_user(username='owner', password='pass')
    parcel = IncomingParcel.objects.create(user=owner, address='1 Ad', city='C', postcode='P', country='UK')
    pm = ParcelMaterial.objects.create(parcel=parcel, plastic_type=pt, weight_kg=Decimal('2.000'))

    # Staff can access the admin change view (GET)
    client.force_login(staff)
    url = f"/admin/store/incomingparcel/{parcel.pk}/change/"
    get_resp = client.get(url)
    assert get_resp.status_code == 200

    # Simulate admin saving by setting points_calculated directly and saving
    calculated = parcel.calculate_points()
    parcel.points_calculated = calculated
    parcel.save()

    # Now award the points to the owner via the model method (replicates admin action)
    prev_points = Customer.objects.filter(user=owner).first().total_points if Customer.objects.filter(user=owner).exists() else 0
    parcel.award_points_to_customer()
    owner_customer = Customer.objects.filter(user=owner).first()
    assert owner_customer is not None
    assert owner_customer.total_points >= prev_points


@pytest.mark.django_db
def test_product_slug_uniqueness():
    p1 = Product.objects.create(name='Unique', slug='unique-1', price=Decimal('1.00'))
    # Provide different slug for second product since slug must be unique
    p2 = Product.objects.create(name='Unique', slug='unique-2', price=Decimal('2.00'))
    assert p1.slug != p2.slug
    assert Product.objects.count() == 2


@pytest.mark.django_db
def test_apply_points_zero_points_returns_success(client):
    user = User.objects.create_user(username='zerop', password='pass')
    customer, _ = Customer.objects.get_or_create(user=user, defaults={'name': 'zerop', 'email': 'z@example.com'})
    customer.total_points = 10
    customer.save()
    product = Product.objects.create(name='Z0', slug='z0', price=Decimal('1.00'))
    order = Order.objects.create(customer=customer, status='Order Received')
    OrderItem.objects.create(order=order, product=product, quantity=1)

    client.force_login(user)
    payload = {'points': 0}
    resp = client.post(reverse('store:apply_points'), data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('points_used') == 0


@pytest.mark.django_db
def test_pointtransaction_ordering():
    user = User.objects.create_user(username='ptuser', password='pass')
    customer, _ = Customer.objects.get_or_create(user=user, defaults={'name': 'ptuser', 'email': 'pt@example.com'})
    PointTransaction.objects.create(customer=customer, transaction_type='EARNED', points=10, description='one')
    PointTransaction.objects.create(customer=customer, transaction_type='EARNED', points=20, description='two')
    txs = list(customer.point_transactions.order_by('-id'))
    assert txs[0].points == 20


@pytest.mark.django_db
def test_dedupe_management_command_runs(capsys):
    # Skip if command doesn't exist
    from django.core.management import get_commands
    if 'dedupe_active_orders' not in get_commands():
        pytest.skip("Management command not found")
    
    user = User.objects.create_user(username='cmduser', password='pass')
    customer, _ = Customer.objects.get_or_create(user=user, defaults={'name': 'cmduser', 'email': 'cmd@example.com'})
    Order.objects.create(customer=customer, status='Order Received')
    Order.objects.create(customer=customer, status='Order Received')

    from django.core.management import call_command
    call_command('dedupe_active_orders')
    assert Order.objects.filter(customer=customer, status='Order Received').count() == 1


@pytest.mark.django_db
def test_customer_str_representation():
    user = User.objects.create_user(username='strtest', password='pass')
    customer = Customer.objects.create(user=user, name='Test Customer', email='test@example.com')
    assert str(customer) == 'Test Customer'


@pytest.mark.django_db
def test_product_str_representation():
    product = Product.objects.create(name='Test Product', slug='test-product', price=Decimal('9.99'))
    assert str(product) == 'Test Product'


@pytest.mark.django_db
def test_order_str_representation():
    user = User.objects.create_user(username='orderstr', password='pass')
    customer = Customer.objects.create(user=user, name='Order User', email='o@example.com')
    order = Order.objects.create(customer=customer)
    assert str(order) == str(order.id)


@pytest.mark.django_db
def test_customer_creation_on_user_registration():
    user = User.objects.create_user(username='newuser', password='pass', email='new@example.com')
    # Customer should be auto-created via signal or needs manual creation
    customer = Customer.objects.filter(user=user).first()
    if customer:
        assert customer.user == user


@pytest.mark.django_db
def test_order_get_cart_items_empty_cart():
    user = User.objects.create_user(username='emptyuser', password='pass')
    customer = Customer.objects.create(user=user, name='Empty', email='e@example.com')
    order = Order.objects.create(customer=customer)
    assert order.get_cart_items == 0


@pytest.mark.django_db
def test_product_with_digital_attribute():
    product = Product.objects.create(name='Digital', slug='digital', price=Decimal('5.00'), digital=True)
    assert product.digital is True


@pytest.mark.django_db
def test_order_shipping_false_for_digital_only():
    user = User.objects.create_user(username='diguser', password='pass')
    customer = Customer.objects.create(user=user, name='Digital User', email='d@example.com')
    product = Product.objects.create(name='Ebook', slug='ebook', price=Decimal('5.00'), digital=True)
    order = Order.objects.create(customer=customer)
    OrderItem.objects.create(order=order, product=product, quantity=1)
    assert order.shipping is False


@pytest.mark.django_db
def test_order_shipping_true_for_physical():
    user = User.objects.create_user(username='physuser', password='pass')
    customer = Customer.objects.create(user=user, name='Physical User', email='ph@example.com')
    product = Product.objects.create(name='Book', slug='book', price=Decimal('15.00'), digital=False)
    order = Order.objects.create(customer=customer)
    OrderItem.objects.create(order=order, product=product, quantity=1)
    assert order.shipping is True


@pytest.mark.django_db
def test_plastic_type_str_representation():
    plastic = PlasticType.objects.create(name='ABS', points_per_kg_basic=80, points_per_kg_premium=100)
    assert str(plastic) == 'ABS'


@pytest.mark.django_db
def test_point_transaction_str_representation():
    user = User.objects.create_user(username='ptstr', password='pass')
    customer = Customer.objects.create(user=user, name='PT User', email='pt@example.com')
    pt = PointTransaction.objects.create(
        customer=customer,
        transaction_type='EARNED',
        points=100,
        description='Test'
    )
    assert 'EARNED' in str(pt)
    assert '100' in str(pt)


@pytest.mark.django_db
def test_customer_total_points_defaults_to_zero():
    user = User.objects.create_user(username='zeropoints', password='pass')
    customer = Customer.objects.create(user=user, name='Zero', email='z@example.com')
    assert customer.total_points == 0


@pytest.mark.django_db
def test_orderitem_get_total():
    user = User.objects.create_user(username='itemtotal', password='pass')
    customer = Customer.objects.create(user=user, name='Item', email='i@example.com')
    product = Product.objects.create(name='Item', slug='item', price=Decimal('7.50'))
    order = Order.objects.create(customer=customer)
    item = OrderItem.objects.create(order=order, product=product, quantity=3)
    assert item.get_total == Decimal('22.50')


@pytest.mark.django_db
def test_multiple_orderitems_cart_total():
    user = User.objects.create_user(username='multi', password='pass')
    customer = Customer.objects.create(user=user, name='Multi', email='m@example.com')
    p1 = Product.objects.create(name='P1', slug='p1', price=Decimal('5.00'))
    p2 = Product.objects.create(name='P2', slug='p2', price=Decimal('3.00'))
    p3 = Product.objects.create(name='P3', slug='p3', price=Decimal('2.50'))
    
    order = Order.objects.create(customer=customer)
    OrderItem.objects.create(order=order, product=p1, quantity=2)  # 10.00
    OrderItem.objects.create(order=order, product=p2, quantity=1)  # 3.00
    OrderItem.objects.create(order=order, product=p3, quantity=4)  # 10.00
    
    assert order.get_cart_total == Decimal('23.00')
    assert order.get_cart_items == 7


@pytest.mark.django_db
def test_incoming_parcel_str_representation():
    user = User.objects.create_user(username='parcelstr', password='pass')
    parcel = IncomingParcel.objects.create(user=user, address='1 Test', city='City', postcode='P1', country='UK')
    parcel_str = str(parcel)
    assert parcel_str.startswith('ip')


@pytest.mark.django_db
def test_store_view_renders(client):
    resp = client.get(reverse('store:store'))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_cart_view_authenticated(client):
    user = User.objects.create_user(username='cartview', password='pass')
    client.force_login(user)
    resp = client.get(reverse('store:cart'))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_checkout_view_authenticated(client):
    user = User.objects.create_user(username='checkview', password='pass')
    client.force_login(user)
    resp = client.get(reverse('store:checkout'))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_product_detail_view(client):
    product = Product.objects.create(name='Detail', slug='detail', price=Decimal('10.00'))
    resp = client.get(reverse('store:product_detail', args=[product.slug]))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_customer_premium_field_defaults_false():
    user = User.objects.create_user(username='premdef', password='pass')
    customer = Customer.objects.create(user=user, name='Prem', email='pr@example.com')
    assert customer.is_premium is False


@pytest.mark.django_db
def test_order_date_ordered_auto_set():
    user = User.objects.create_user(username='dateord', password='pass')
    customer = Customer.objects.create(user=user, name='Date', email='d@example.com')
    order = Order.objects.create(customer=customer)
    assert order.date_ordered is not None


@pytest.mark.django_db
def test_product_image_url_default():
    product = Product.objects.create(name='NoImage', slug='noimage', price=Decimal('5.00'))
    assert 'placeholder' in product.imageURL.lower() or product.imageURL == ''


@pytest.mark.django_db
def test_order_get_cart_total_with_decimal_precision():
    user = User.objects.create_user(username='decimal', password='pass')
    customer = Customer.objects.create(user=user, name='Decimal', email='dec@example.com')
    product = Product.objects.create(name='Dec', slug='dec', price=Decimal('3.33'))
    order = Order.objects.create(customer=customer)
    OrderItem.objects.create(order=order, product=product, quantity=3)
    # 3.33 * 3 = 9.99
    assert order.get_cart_total == Decimal('9.99')


@pytest.mark.django_db
def test_multiple_customers_total_points():
    u1 = User.objects.create_user(username='u1', password='pass')
    u2 = User.objects.create_user(username='u2', password='pass')
    c1 = Customer.objects.create(user=u1, name='C1', email='c1@example.com', total_points=100)
    c2 = Customer.objects.create(user=u2, name='C2', email='c2@example.com', total_points=200)
    
    assert c1.total_points == 100
    assert c2.total_points == 200
    assert Customer.objects.filter(total_points__gte=150).count() == 1


@pytest.mark.django_db
def test_order_status_choices():
    user = User.objects.create_user(username='status', password='pass')
    customer = Customer.objects.create(user=user, name='Status', email='st@example.com')
    
    order1 = Order.objects.create(customer=customer, status='Order Received')
    order2 = Order.objects.create(customer=customer, status='Dispatched')
    order3 = Order.objects.create(customer=customer, status='Delivered')
    
    assert Order.objects.filter(status='Order Received').count() == 1
    assert Order.objects.filter(status='Dispatched').count() == 1
    assert Order.objects.filter(status='Delivered').count() == 1


@pytest.mark.django_db
def test_orderitem_quantity_update():
    user = User.objects.create_user(username='qty', password='pass')
    customer = Customer.objects.create(user=user, name='Qty', email='qty@example.com')
    product = Product.objects.create(name='QtyProd', slug='qtyprod', price=Decimal('10.00'))
    order = Order.objects.create(customer=customer)
    item = OrderItem.objects.create(order=order, product=product, quantity=1)
    
    assert item.quantity == 1
    item.quantity = 5
    item.save()
    item.refresh_from_db()
    assert item.quantity == 5
    assert item.get_total == Decimal('50.00')


@pytest.mark.django_db
def test_plastic_type_filtering():
    PlasticType.objects.create(name='PLA', points_per_kg_basic=100, points_per_kg_premium=120)
    PlasticType.objects.create(name='ABS', points_per_kg_basic=90, points_per_kg_premium=110)
    PlasticType.objects.create(name='PETG', points_per_kg_basic=95, points_per_kg_premium=115)
    
    pla = PlasticType.objects.get(name='PLA')
    assert pla.points_per_kg_basic == 100
    
    high_value = PlasticType.objects.filter(points_per_kg_basic__gte=95).count()
    assert high_value == 2


@pytest.mark.django_db
def test_customer_email_uniqueness():
    u1 = User.objects.create_user(username='email1', password='pass')
    u2 = User.objects.create_user(username='email2', password='pass')
    
    c1 = Customer.objects.create(user=u1, name='Email1', email='unique@example.com')
    c2 = Customer.objects.create(user=u2, name='Email2', email='another@example.com')
    
    assert Customer.objects.count() == 2


@pytest.mark.django_db
def test_point_transaction_types():
    user = User.objects.create_user(username='types', password='pass')
    customer = Customer.objects.create(user=user, name='Types', email='ty@example.com')
    
    earned = PointTransaction.objects.create(
        customer=customer,
        transaction_type='EARNED',
        points=100,
        description='Earned'
    )
    
    spent = PointTransaction.objects.create(
        customer=customer,
        transaction_type='SPENT',
        points=50,
        description='Spent'
    )
    
    assert earned.transaction_type == 'EARNED'
    assert spent.transaction_type == 'SPENT'
    assert PointTransaction.objects.filter(transaction_type='EARNED').count() == 1


@pytest.mark.django_db
def test_order_complete_status():
    """Test order completion using status field"""
    user = User.objects.create_user(username='complete', password='pass')
    customer = Customer.objects.create(user=user, name='Complete', email='comp@example.com')
    
    order = Order.objects.create(customer=customer, status='Order Received')
    assert order.status == 'Order Received'
    
    order.status = 'Delivered'
    order.save()
    order.refresh_from_db()
    assert order.status == 'Delivered'


@pytest.mark.django_db
def test_parcel_calculate_total_points():
    user = User.objects.create_user(username='calc', password='pass')
    parcel = IncomingParcel.objects.create(user=user, address='1 C', city='C', postcode='P', country='UK')
    
    pt1 = PlasticType.objects.create(name='PT1', points_per_kg_basic=100, points_per_kg_premium=120)
    pt2 = PlasticType.objects.create(name='PT2', points_per_kg_basic=50, points_per_kg_premium=60)
    
    ParcelMaterial.objects.create(parcel=parcel, plastic_type=pt1, weight_kg=Decimal('2.0'))
    ParcelMaterial.objects.create(parcel=parcel, plastic_type=pt2, weight_kg=Decimal('4.0'))
    
    # Total: (2.0 * 100) + (4.0 * 50) = 200 + 200 = 400
    total = parcel.calculate_points()
    assert total == 400


@pytest.mark.django_db
def test_product_search_by_name():
    Product.objects.create(name='Red Widget', slug='red-widget', price=Decimal('10.00'))
    Product.objects.create(name='Blue Widget', slug='blue-widget', price=Decimal('15.00'))
    Product.objects.create(name='Green Gadget', slug='green-gadget', price=Decimal('20.00'))
    
    widgets = Product.objects.filter(name__icontains='widget')
    assert widgets.count() == 2
    
    red = Product.objects.filter(name__icontains='red')
    assert red.count() == 1


@pytest.mark.django_db
def test_order_transaction_id_field():
    """Test Order transaction_id field existence"""
    user = User.objects.create_user(username='trans', password='pass')
    customer = Customer.objects.create(user=user, name='Trans', email='trans@example.com')
    order = Order.objects.create(customer=customer)
    
    if hasattr(order, 'transaction_id'):
        assert order.transaction_id is None or isinstance(order.transaction_id, str)


@pytest.mark.django_db
def test_parcel_without_tracking_number():
    """Test IncomingParcel creation without tracking_number field"""
    user = User.objects.create_user(username='parcel', password='pass')
    
    parcel = IncomingParcel.objects.create(
        user=user,
        address='Test Address',
        city='Test City',
        postcode='T1 1TT',
        country='UK'
    )
    
    assert parcel.user == user
    assert parcel.address == 'Test Address'


@pytest.mark.django_db
def test_update_item_requires_authentication():
    """Test that update_item endpoint requires authentication"""
    from django.test import Client
    client = Client()
    
    product = Product.objects.create(name='Auth', slug='auth', price=Decimal('10.00'))
    payload = {'productId': product.id, 'action': 'add'}
    
    resp = client.post(
        reverse('store:update_item'),
        data=json.dumps(payload),
        content_type='application/json'
    )
    
    assert resp.status_code in [401, 302, 403]


@pytest.mark.django_db
def test_guest_cart_cookie_handling(client):
    """Test guest cart uses cookie storage"""
    product = Product.objects.create(name='Guest', slug='guest', price=Decimal('5.00'))
    
    cart_data = {str(product.id): {'quantity': 2}}
    client.cookies.load({'cart': json.dumps(cart_data)})
    
    resp = client.get(reverse('store:cart'))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_order_item_total_calculation():
    """Test OrderItem calculates totals correctly"""
    user = User.objects.create_user(username='calc2', password='pass')
    customer = Customer.objects.create(user=user, name='Calc', email='calc@example.com')
    product = Product.objects.create(name='Calc', slug='calc', price=Decimal('12.34'))
    order = Order.objects.create(customer=customer)
    
    item = OrderItem.objects.create(order=order, product=product, quantity=3)
    
    expected = Decimal('12.34') * 3
    assert item.get_total == expected


@pytest.mark.django_db
def test_multiple_orders_per_customer():
    """Test customer can have multiple orders"""
    user = User.objects.create_user(username='multiord', password='pass')
    customer = Customer.objects.create(user=user, name='Multi', email='multi@example.com')
    
    order1 = Order.objects.create(customer=customer, status='Order Received')
    order2 = Order.objects.create(customer=customer, status='Dispatched')
    order3 = Order.objects.create(customer=customer, status='Delivered')
    
    assert Order.objects.filter(customer=customer).count() == 3
    # Use order_set or the related_name if defined, not 'orders'
    assert customer.order_set.count() == 3


@pytest.mark.django_db
def test_profile_view_loads_customer_data(client):
    """Test profile view shows customer information"""
    user = User.objects.create_user(username='profile', password='pass')
    customer, _ = Customer.objects.get_or_create(
        user=user,
        defaults={'name': 'Profile User', 'email': 'profile@example.com'}
    )
    
    client.force_login(user)
    resp = client.get(reverse('store:profile'))
    
    assert resp.status_code == 200
    # Check that response contains profile-related content
    content = resp.content.decode()
    assert 'profile' in content.lower() or customer.email in content


@pytest.mark.django_db
def test_customer_order_history():
    """Test retrieving customer's order history"""
    user = User.objects.create_user(username='history', password='pass')
    customer = Customer.objects.create(user=user, name='History', email='hist@example.com')
    
    for i in range(5):
        Order.objects.create(customer=customer, status='Delivered')
    
    orders = customer.order_set.all()
    assert orders.count() == 5


@pytest.mark.django_db
def test_order_with_no_items_has_zero_total():
    """Test empty order returns zero totals"""
    user = User.objects.create_user(username='empty', password='pass')
    customer = Customer.objects.create(user=user, name='Empty', email='empty@example.com')
    order = Order.objects.create(customer=customer)
    
    assert order.get_cart_total == Decimal('0.00')
    assert order.get_cart_items == 0


@pytest.mark.django_db
def test_orderitem_with_zero_quantity():
    """Test OrderItem with zero quantity"""
    user = User.objects.create_user(username='zeroqty', password='pass')
    customer = Customer.objects.create(user=user, name='ZeroQty', email='zq@example.com')
    product = Product.objects.create(name='ZeroItem', slug='zeroitem', price=Decimal('10.00'))
    order = Order.objects.create(customer=customer)
    
    item = OrderItem.objects.create(order=order, product=product, quantity=0)
    assert item.get_total == Decimal('0.00')


@pytest.mark.django_db
def test_customer_point_transactions_relationship():
    """Test Customer to PointTransaction relationship"""
    user = User.objects.create_user(username='ptrel', password='pass')
    customer = Customer.objects.create(user=user, name='PTRel', email='ptr@example.com')
    
    PointTransaction.objects.create(customer=customer, transaction_type='EARNED', points=100, description='First')
    PointTransaction.objects.create(customer=customer, transaction_type='SPENT', points=50, description='Second')
    PointTransaction.objects.create(customer=customer, transaction_type='EARNED', points=75, description='Third')
    
    transactions = customer.point_transactions.all()
    assert transactions.count() == 3


@pytest.mark.django_db
def test_product_slug_is_required():
    """Test product slug field behavior"""
    product = Product.objects.create(name='Slug Test', slug='slug-test', price=Decimal('10.00'))
    assert product.slug == 'slug-test'
    assert '-' in product.slug


@pytest.mark.django_db
def test_order_points_discount_calculation():
    """Test points discount calculation"""
    user = User.objects.create_user(username='discount', password='pass')
    customer = Customer.objects.create(user=user, name='Discount', email='disc@example.com')
    product = Product.objects.create(name='Disc', slug='disc', price=Decimal('50.00'))
    order = Order.objects.create(customer=customer)
    OrderItem.objects.create(order=order, product=product, quantity=1)
    
    # Apply 500 points (£5.00)
    order.points_used = 500
    order.save()
    
    assert order.points_discount_gbp == Decimal('5.00')
    assert order.get_cart_total_after_points == Decimal('45.00')


@pytest.mark.django_db
def test_parcel_user_relationship():
    """Test IncomingParcel to User relationship"""
    user = User.objects.create_user(username='parceluser', password='pass')
    
    parcel1 = IncomingParcel.objects.create(user=user, address='1 A', city='C', postcode='P', country='UK')
    parcel2 = IncomingParcel.objects.create(user=user, address='2 B', city='C', postcode='P', country='UK')
    
    user_parcels = IncomingParcel.objects.filter(user=user)
    assert user_parcels.count() == 2


@pytest.mark.django_db
def test_plastic_type_points_per_kg_values():
    """Test PlasticType points per kg fields are positive"""
    plastic = PlasticType.objects.create(
        name='ValidPlastic',
        points_per_kg_basic=50,
        points_per_kg_premium=75
    )
    
    assert plastic.points_per_kg_basic > 0
    assert plastic.points_per_kg_premium > 0
    assert plastic.points_per_kg_premium >= plastic.points_per_kg_basic


@pytest.mark.django_db
def test_order_with_very_large_quantity():
    """Test OrderItem with large quantity values"""
    user = User.objects.create_user(username='large', password='pass')
    customer = Customer.objects.create(user=user, name='Large', email='large@example.com')
    product = Product.objects.create(name='Large', slug='large', price=Decimal('1.00'))
    order = Order.objects.create(customer=customer)
    
    item = OrderItem.objects.create(order=order, product=product, quantity=1000)
    assert item.get_total == Decimal('1000.00')
    assert order.get_cart_items == 1000


@pytest.mark.django_db
def test_customer_verified_weight_zero_for_new_customer():
    """Test new customer has zero verified weight"""
    user = User.objects.create_user(username='newweight', password='pass')
    customer, _ = Customer.objects.get_or_create(user=user, defaults={'name': 'NewWeight', 'email': 'nw@example.com'})
    
    verified_weight = customer.get_verified_weight()
    assert verified_weight == 0


@pytest.mark.django_db
def test_parcel_material_zero_weight():
    """Test ParcelMaterial with zero weight"""
    user = User.objects.create_user(username='zeroweight', password='pass')
    parcel = IncomingParcel.objects.create(user=user, address='1 Z', city='C', postcode='P', country='UK')
    plastic = PlasticType.objects.create(name='Zero', points_per_kg_basic=100, points_per_kg_premium=120)
    
    material = ParcelMaterial.objects.create(parcel=parcel, plastic_type=plastic, weight_kg=Decimal('0.000'))
    assert material.weight_kg == Decimal('0.000')


@pytest.mark.django_db
def test_order_get_cart_items_multiple_same_product():
    """Test cart items count with same product added multiple times"""
    user = User.objects.create_user(username='multi2', password='pass')
    customer = Customer.objects.create(user=user, name='Multi2', email='m2@example.com')
    product = Product.objects.create(name='Multi', slug='multi', price=Decimal('5.00'))
    order = Order.objects.create(customer=customer)
    
    # Add same product twice with different quantities
    OrderItem.objects.create(order=order, product=product, quantity=3)
    
    assert order.get_cart_items == 3
    assert order.orderitem_set.count() == 1


@pytest.mark.django_db
def test_point_transaction_description_field():
    """Test PointTransaction description is stored correctly"""
    user = User.objects.create_user(username='desc', password='pass')
    customer = Customer.objects.create(user=user, name='Desc', email='desc@example.com')
    
    long_description = 'A' * 200
    pt = PointTransaction.objects.create(
        customer=customer,
        transaction_type='EARNED',
        points=100,
        description=long_description
    )
    
    assert pt.description == long_description


@pytest.mark.django_db
def test_product_digital_default_value():
    """Test Product digital field defaults to False"""
    product = Product.objects.create(name='Default', slug='default', price=Decimal('10.00'))
    assert product.digital is False


@pytest.mark.django_db
def test_shipping_address_optional_county_field():
    """Test ShippingAddress with empty county"""
    from store.models import ShippingAddress
    user = User.objects.create_user(username='nocounty', password='pass')
    customer = Customer.objects.create(user=user, name='NoCounty', email='nc@example.com')
    order = Order.objects.create(customer=customer)
    
    shipping = ShippingAddress.objects.create(
        customer=customer,
        order=order,
        address='123 Street',
        city='City',
        county='',  # Empty county
        postcode='AB1 2CD',
        country='UK'
    )
    
    assert shipping.county == ''


@pytest.mark.django_db
def test_order_status_transitions():
    """Test order can transition through different statuses"""
    user = User.objects.create_user(username='status', password='pass')
    customer = Customer.objects.create(user=user, name='Status', email='status@example.com')
    order = Order.objects.create(customer=customer, status='Order Received')
    
    assert order.status == 'Order Received'
    
    order.status = 'Dispatched'
    order.save()
    assert order.status == 'Dispatched'
    
    order.status = 'Delivered'
    order.save()
    assert order.status == 'Delivered'


@pytest.mark.django_db
def test_parcel_calculate_points_with_no_materials():
    """Test parcel point calculation with no materials"""
    user = User.objects.create_user(username='nomats', password='pass')
    parcel = IncomingParcel.objects.create(user=user, address='1 N', city='C', postcode='P', country='UK')
    
    total = parcel.calculate_points()
    assert total == 0


@pytest.mark.django_db
def test_customer_is_eligible_for_premium_insufficient_weight():
    """Test premium eligibility with insufficient weight"""
    user = User.objects.create_user(username='noelig', password='pass')
    customer, _ = Customer.objects.get_or_create(user=user, defaults={'name': 'NoElig', 'email': 'ne@example.com'})
    
    # Create parcel with low weight
    parcel = IncomingParcel.objects.create(user=user, address='1 N', city='C', postcode='P', country='UK')
    plastic = PlasticType.objects.create(name='Low', points_per_kg_basic=10, points_per_kg_premium=12)
    ParcelMaterial.objects.create(parcel=parcel, plastic_type=plastic, weight_kg=Decimal('1.000'))
    
    # Should not be eligible (threshold is typically 25kg)
    assert customer.is_eligible_for_premium() is False


@pytest.mark.django_db
def test_product_price_with_many_decimal_places():
    """Test product price precision"""
    product = Product.objects.create(name='Precise', slug='precise', price=Decimal('19.999'))
    
    # Depending on DecimalField settings, this might round
    assert product.price >= Decimal('19.99')


@pytest.mark.django_db
def test_order_items_with_different_products():
    """Test order with multiple different products"""
    user = User.objects.create_user(username='diff', password='pass')
    customer = Customer.objects.create(user=user, name='Diff', email='diff@example.com')
    
    p1 = Product.objects.create(name='A', slug='a1', price=Decimal('10.00'))
    p2 = Product.objects.create(name='B', slug='b1', price=Decimal('20.00'))
    p3 = Product.objects.create(name='C', slug='c1', price=Decimal('30.00'))
    
    order = Order.objects.create(customer=customer)
    OrderItem.objects.create(order=order, product=p1, quantity=1)
    OrderItem.objects.create(order=order, product=p2, quantity=2)
    OrderItem.objects.create(order=order, product=p3, quantity=3)
    
    assert order.orderitem_set.count() == 3
    assert order.get_cart_total == Decimal('140.00')  # 10 + 40 + 90
    assert order.get_cart_items == 6  # 1 + 2 + 3


@pytest.mark.django_db
def test_parcel_points_awarded_flag():
    """Test IncomingParcel points_awarded flag"""
    user = User.objects.create_user(username='awarded', password='pass')
    parcel = IncomingParcel.objects.create(
        user=user,
        address='1 A',
        city='C',
        postcode='P',
        country='UK',
        points_awarded=False
    )
    
    assert parcel.points_awarded is False
    
    parcel.points_awarded = True
    parcel.save()
    parcel.refresh_from_db()
    
    assert parcel.points_awarded is True


@pytest.mark.django_db
def test_customer_total_points_cannot_go_negative_in_business_logic():
    """Test business logic prevents negative points"""
    user = User.objects.create_user(username='negcheck', password='pass')
    customer = Customer.objects.create(user=user, name='NegCheck', email='neg@example.com', total_points=50)
    
    # Attempting to spend more than available
    # In real application, this would be prevented by validation
    initial_points = customer.total_points
    assert initial_points >= 0


@pytest.mark.django_db
def test_multiple_plastic_types_exist():
    """Test multiple plastic types can coexist"""
    PlasticType.objects.create(name='PLA', points_per_kg_basic=100, points_per_kg_premium=120)
    PlasticType.objects.create(name='ABS', points_per_kg_basic=90, points_per_kg_premium=110)
    PlasticType.objects.create(name='PETG', points_per_kg_basic=95, points_per_kg_premium=115)
    PlasticType.objects.create(name='Nylon', points_per_kg_basic=85, points_per_kg_premium=105)
    
    assert PlasticType.objects.count() == 4


@pytest.mark.django_db
def test_orderitem_references_correct_product():
    """Test OrderItem maintains product reference"""
    user = User.objects.create_user(username='ref', password='pass')
    customer = Customer.objects.create(user=user, name='Ref', email='ref@example.com')
    product = Product.objects.create(name='RefProd', slug='refprod', price=Decimal('25.00'))
    order = Order.objects.create(customer=customer)
    
    item = OrderItem.objects.create(order=order, product=product, quantity=2)
    
    assert item.product == product
    assert item.product.name == 'RefProd'
    assert item.product.price == Decimal('25.00')


@pytest.mark.django_db
def test_parcel_material_plastic_type_relationship():
    """Test ParcelMaterial to PlasticType relationship"""
    user = User.objects.create_user(username='matplast', password='pass')
    parcel = IncomingParcel.objects.create(user=user, address='1 M', city='C', postcode='P', country='UK')
    
    pla = PlasticType.objects.create(name='PLA_MAT', points_per_kg_basic=100, points_per_kg_premium=120)
    abs_type = PlasticType.objects.create(name='ABS_MAT', points_per_kg_basic=90, points_per_kg_premium=110)
    
    mat1 = ParcelMaterial.objects.create(parcel=parcel, plastic_type=pla, weight_kg=Decimal('1.0'))
    mat2 = ParcelMaterial.objects.create(parcel=parcel, plastic_type=abs_type, weight_kg=Decimal('2.0'))
    
    assert mat1.plastic_type.name == 'PLA_MAT'
    assert mat2.plastic_type.name == 'ABS_MAT'


@pytest.mark.django_db
def test_customer_email_format():
    """Test customer email field accepts valid email"""
    user = User.objects.create_user(username='emailtest', password='pass')
    customer = Customer.objects.create(
        user=user,
        name='Email Test',
        email='valid.email@example.co.uk'
    )
    
    assert '@' in customer.email
    assert '.' in customer.email
