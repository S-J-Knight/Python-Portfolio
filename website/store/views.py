import json
import datetime
from decimal import Decimal
from django.apps import apps
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import *
from .utils import cookieCart, cartData
from .models import PlasticType


# ========== Public Pages ==========
def home(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    return render(request, 'pages/home.html', {
        'cartItems': cartItems,
        'user': request.user,
    })

def about(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    return render(request, 'pages/about.html', {'cartItems': cartItems})


# ========== Store Views ==========
def store(request):
    data = cartData(request)
    cartItems = data['cartItems']
    products = Product.objects.all()
    context = {'products': products, 'cartItems': cartItems}
    return render(request, 'store/store.html', context)

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    data = cartData(request)
    cartItems = data['cartItems']
    context = {
        'product': product,
        'cartItems': cartItems,
    }
    return render(request, 'store/product_detail.html', context)

def cart(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    order = data.get('order')
    items = data.get('items')

    customer = None
    available_points = 0
    available_points_gbp = Decimal('0.00')
    max_points_usable = 0

    if request.user.is_authenticated:
        customer = Customer.objects.filter(user=request.user).first()
        if customer:
            available_points = int(customer.total_points or 0)
            if order:
                # Max points equals cart total in pence
                max_points_usable = int((order.get_cart_total * Decimal('100')).quantize(Decimal('1')))
                max_points_usable = min(available_points, max_points_usable)
            # Convert points -> pounds (1 point = £0.01)
            available_points_gbp = (Decimal(available_points) / Decimal('100')).quantize(Decimal('0.01'))

    context = {
        'items': items,
        'order': order,
        'cartItems': cartItems,
        'customer': customer,
        'available_points': available_points,
        'available_points_gbp': available_points_gbp,
        'max_points_usable': max_points_usable,
    }
    return render(request, 'store/cart.html', context)

def checkout(request):
    data = cartData(request)
    cartItems = data['cartItems']
    order = data['order']
    items = data['items']
    needs_shipping = data['needs_shipping']
    last_address = data['last_address']
    context = {
        'items': items,
        'order': order,
        'cartItems': cartItems,
        'needs_shipping': needs_shipping,
        'last_address': last_address
    }
    return render(request, 'store/checkout.html', context)


# ========== Cart/Order Processing ==========
@require_POST
def update_item(request):
    """Accept JSON { productId, action } from cart.js."""
    data = json.loads(request.body)
    productId = data.get('productId')
    action = data.get('action')

    if request.user.is_authenticated:
        customer, _ = Customer.objects.get_or_create(
            user=request.user,
            defaults={'name': request.user.username, 'email': request.user.email}
        )
        order, _ = Order.objects.get_or_create(customer=customer, status='Order Received')
        product = get_object_or_404(Product, pk=productId)
        order_item, _ = OrderItem.objects.get_or_create(order=order, product=product)

        if action == 'add':
            order_item.quantity = (order_item.quantity or 0) + 1
            order_item.save()
        elif action == 'remove':
            order_item.quantity = (order_item.quantity or 0) - 1
            if order_item.quantity <= 0:
                order_item.delete()
            else:
                order_item.save()
        elif action == 'delete':
            order_item.delete()
        return JsonResponse({'status': 'ok'})

    return JsonResponse({'status': 'guest'})

def processOrder(request):
    transaction_id = datetime.datetime.now().timestamp()
    data = json.loads(request.body)

    if request.user.is_authenticated:
        customer = request.user.customer
        order = Order.objects.filter(customer=customer, status='Order Received').first()
        if not order:
            return JsonResponse('No order with status "Order Received" found', safe=False)

        # Deduct points if used
        if order.points_used > 0:
            customer.total_points -= order.points_used
            customer.save()
            
            # Create transaction record
            PointTransaction.objects.create(
                customer=customer,
                transaction_type='REDEEMED',
                points=-order.points_used,  # Negative for redemption
                description=f"Redeemed for order #{order.id}"
            )

        total = float(data['form']['total'])
        order.transaction_id = transaction_id

        if round(total, 2) == round(float(order.get_cart_total_after_points), 2):  # Changed to use after_points total
            order.status = 'Order Received'
        order.save()

        if order.shipping:
            if not ShippingAddress.objects.filter(order=order).exists():
                ShippingAddress.objects.create(
                    customer=customer,
                    order=order,
                    address=data['shipping']['address'],
                    city=data['shipping']['city'],
                    county=data['shipping']['county'],
                    postcode=data['shipping']['postcode'],
                    country=data['shipping']['country'],
                    is_saved=data['shipping'].get('save', False),
                )
    else:
        # Guest checkout
        print('User is not logged in')
        print('COOKIES:', request.COOKIES)
        name = data['form']['name']
        email = data['form']['email']

        cookieData = cookieCart(request)
        items = cookieData['items']

        customer, created = Customer.objects.get_or_create(email=email)
        customer.name = name
        customer.save()

        order = Order.objects.create(customer=customer, status='Order Received')

        for item in items:
            product = Product.objects.get(id=item['id'])
            OrderItem.objects.create(
                product=product,
                order=order,
                quantity=item['quantity'],
            )

        total = float(data['form']['total'])
        order.transaction_id = transaction_id

        if round(total, 2) == round(float(order.get_cart_total), 2):
            order.status = 'Order Received'
        order.save()

        if order.shipping:
            ShippingAddress.objects.create(
                customer=customer,
                order=order,
                address=data['shipping']['address'],
                city=data['shipping']['city'],
                county=data['shipping']['county'],
                postcode=data['shipping']['postcode'],
                country=data['shipping']['country'],
            )

    return JsonResponse('Payment submitted..', safe=False)


# ========== Auth Views ==========
def login(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    error = ''
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return render(request, 'pages/home.html', {
                'cartItems': cartItems,
                'message': 'Login successful!'
            })
        else:
            error = 'Invalid username or password.'
    return render(request, 'pages/login.html', {'cartItems': cartItems, 'error': error})

def register(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    error = ''
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if password1 != password2:
            error = 'Passwords do not match.'
        elif User.objects.filter(username=username).exists():
            error = 'Username already exists.'
        else:
            user = User.objects.create_user(username=username, email=email, password=password1)
            auth_login(request, user)
            return render(request, 'pages/home.html', {
                'cartItems': cartItems,
                'message': 'Account created and logged in!'
            })
    return render(request, 'pages/login.html', {
        'cartItems': cartItems,
        'error': error,
        'show_register': True
    })

def logout(request):
    auth_logout(request)
    return render(request, 'pages/home.html', {'message': 'Logged out successfully!'})


# ========== User Profile & Orders ==========
@login_required
def profile(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)  # <-- ADD THIS LINE
    
    customer, _ = Customer.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.username, 'email': request.user.email}
    )
    
    # Get recent transactions (last 3)
    recent_transactions = PointTransaction.objects.filter(
        customer=customer
    ).order_by('-date_created')[:3]
    
    address_obj = ShippingAddress.objects.filter(
        customer=customer,
        is_saved=True
    ).order_by('-date_added').first()

    # Get recent point-earning parcels (last 3)
    recent_parcels = IncomingParcel.objects.filter(
        user=request.user,
        points_calculated__isnull=False
    ).order_by('-date_submitted')[:3]
    
    # Get all plastic types for point rates display
    plastic_types = PlasticType.objects.all().order_by('name')
    
    # Get premium progress data
    parcel_count = customer.get_parcel_count()
    verified_weight = customer.get_verified_weight()
    premium_progress = customer.get_premium_progress()

    # Handle POST for address update
    if request.method == 'POST':
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        county = request.POST.get('county', '').strip()
        postcode = request.POST.get('postcode', '').strip()
        country = request.POST.get('country', '').strip()

        if address and city and postcode and country:
            address_obj, created = ShippingAddress.objects.update_or_create(
                customer=customer,
                is_saved=True,
                defaults={
                    'address': address,
                    'city': city,
                    'county': county,
                    'postcode': postcode,
                    'country': country,
                }
            )
            return render(request, 'pages/profile.html', {
                'cartItems': cartItems,
                'customer': customer,
                'recent_transactions': recent_transactions,  # Add this
                'plastic_types': plastic_types,
                'is_premium': customer.is_premium,
                'parcel_count': parcel_count,
                'verified_weight': verified_weight,
                'premium_progress': premium_progress,
                'address_obj': address_obj,
                'message': 'Address updated successfully!'
            })
        else:
            return render(request, 'pages/profile.html', {
                'cartItems': cartItems,
                'customer': customer,
                'recent_transactions': recent_transactions,  # Add this
                'plastic_types': plastic_types,
                'is_premium': customer.is_premium,
                'parcel_count': parcel_count,
                'verified_weight': verified_weight,
                'premium_progress': premium_progress,
                'address_obj': address_obj,
                'error': 'All fields except county are required.'
            })

    return render(request, 'pages/profile.html', {
        'cartItems': cartItems,
        'customer': customer,
        'recent_transactions': recent_transactions,  # Add this
        'plastic_types': plastic_types,
        'is_premium': customer.is_premium,
        'parcel_count': parcel_count,
        'verified_weight': verified_weight,
        'premium_progress': premium_progress,
        'address_obj': address_obj,
    })

@login_required
def orders(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    customer = getattr(request.user, 'customer', None)
    orders = []
    if customer:
        orders = Order.objects.filter(customer=customer).order_by('-date_ordered')

    IncomingParcel = apps.get_model('store', 'IncomingParcel')
    parcels = []
    if IncomingParcel:
        parcels = IncomingParcel.objects.filter(user=request.user).order_by('-date_submitted')

    context = {
        'orders': orders,
        'parcels': parcels,
        'cartItems': cartItems,
    }
    return render(request, 'pages/orders.html', context)

@login_required
def order_detail(request, order_id):
    customer = getattr(request.user, 'customer', None)
    order = None
    items = []
    address_obj = None
    if customer:
        order = Order.objects.filter(customer=customer, id=order_id).first()
        if order:
            items = order.orderitem_set.all()
            address_obj = order.shippingaddress_set.first()
            if request.method == 'POST' and address_obj:
                address_obj.address = request.POST.get('address', address_obj.address)
                address_obj.city = request.POST.get('city', address_obj.city)
                address_obj.county = request.POST.get('county', address_obj.county)
                address_obj.postcode = request.POST.get('postcode', address_obj.postcode)
                address_obj.country = request.POST.get('country', address_obj.country)
                address_obj.save()
    if not order:
        return render(request, 'pages/order_detail.html', {'order': None, 'items': []})
    return render(request, 'pages/order_detail.html', {'order': order, 'items': items})

@login_required
def inbound_parcel_detail(request, pk):
    parcel = get_object_or_404(IncomingParcel, pk=pk, user=request.user)
    data = cartData(request)
    return render(request, 'pages/inbound_parcels_details.html', {
        'parcel': parcel,
        'cartItems': data.get('cartItems', 0),
    })


# ========== Waste Recycling ==========
@login_required
def shipping_waste_form(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)

    if request.method == 'POST':
        # Get address fields
        address = request.POST.get('address')
        city = request.POST.get('city')
        county = request.POST.get('county', '')
        postcode = request.POST.get('postcode')
        country = request.POST.get('country')
        details = request.POST.get('details', '')

        # Create the IncomingParcel - use ParcelStatus.AWAITING (which is 'awaiting')
        parcel = IncomingParcel.objects.create(
            user=request.user,
            address=address,
            city=city,
            county=county,
            postcode=postcode,
            country=country,
            details=details,
            status=ParcelStatus.AWAITING  # This will use 'awaiting' (lowercase)
        )

        # Get selected waste types from checkboxes
        waste_types = request.POST.getlist('waste_types')
        
        # Create ParcelMaterial entries for each selected type
        for waste_type_name in waste_types:
            try:
                plastic_type = PlasticType.objects.get(name=waste_type_name)
                ParcelMaterial.objects.create(
                    parcel=parcel,
                    plastic_type=plastic_type,
                    weight_kg=None  # Weight will be filled in by admin
                )
            except PlasticType.DoesNotExist:
                pass  # Skip if plastic type doesn't exist

        return redirect('store:shipping_waste_success')

    # GET request - show form
    plastic_types = PlasticType.objects.all()
    
    return render(request, 'pages/shipping_waste_form.html', {
        'cartItems': cartItems,
        'plastic_types': plastic_types,
    })

def send_waste(request):
    """Public page - accessible to guests"""
    data = cartData(request)  # works for guests too
    return render(request, 'pages/send_waste.html', {
        'cartItems': data.get('cartItems', 0),
    })

def shipping_waste_success(request):
    """Public success page"""
    data = cartData(request)
    return render(request, 'pages\shipping_waste_success.html', {
        'cartItems': data.get('cartItems', 0),
    })

# Add apply_points HERE, before points_history
@login_required
@require_POST
def apply_points(request):
    """Apply points discount to cart"""
    data = json.loads(request.body or '{}')
    points_to_use = max(0, int(data.get('points', 0)))

    customer = Customer.objects.get(user=request.user)
    order, _ = Order.objects.get_or_create(customer=customer, status='Order Received')

    # Max usable points is limited by both available balance and cart total (in pence)
    cart_total_pence = int((order.get_cart_total * Decimal('100')).quantize(Decimal('1')))
    max_usable = min(customer.total_points, cart_total_pence)

    if points_to_use > max_usable:
        return JsonResponse({'error': 'Not enough points or exceeds cart total'}, status=400)

    order.points_used = points_to_use
    order.save()

    discount_gbp = (Decimal(points_to_use) / Decimal('100')).quantize(Decimal('0.01'))
    new_total = order.get_cart_total_after_points

    return JsonResponse({
        'success': True,
        'points_used': points_to_use,
        'discount': f'£{discount_gbp:.2f}',
        'new_total': f'£{new_total:.2f}',
    })

@login_required
def points_history(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    customer = getattr(request.user, 'customer', None)
    transactions = []
    if customer:
        transactions = PointTransaction.objects.filter(customer=customer).order_by('-date_created')  # Changed from date_submitted

    return render(request, 'pages/points_history.html', {
        'cartItems': cartItems,
        'transactions': transactions,
    })

