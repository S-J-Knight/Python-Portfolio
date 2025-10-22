import json
import datetime
from decimal import Decimal
from django.apps import apps
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

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
        # Get or create the most recent 'Potential Order'
        order = (Order.objects
                 .filter(customer=customer, status=OrderStatus.POTENTIAL)
                 .order_by('-id')
                 .first())
        
        if not order:
            order = Order.objects.create(customer=customer, status=OrderStatus.POTENTIAL)
        
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
        
        # Clean up empty orders after item removal
        if not order.orderitem_set.exists():
            order.delete()
            
        return JsonResponse({'status': 'ok'})

    return JsonResponse({'status': 'guest'})

def processOrder(request):
    transaction_id = datetime.datetime.now().timestamp()
    data = json.loads(request.body)

    customer, _ = Customer.objects.get_or_create(
        user=request.user,  # Added 'user=' here
        defaults={'name': request.user.username, 'email': request.user.email},
    )

    with transaction.atomic():
        # Find 'Potential Order' with items
        order = (Order.objects
                 .select_for_update()
                 .filter(customer=customer, status=OrderStatus.POTENTIAL)
                 .annotate(item_count=Count('orderitem'))
                 .filter(item_count__gt=0)
                 .order_by('-id')
                 .first())
        if not order:
            return JsonResponse({'error': 'No active order found'}, status=400)

        expected_total = float(order.get_cart_total_after_points)
        received_total = float(data['form']['total'])
        if abs(received_total - expected_total) >= 0.02:
            return JsonResponse({'error': f'Total mismatch: expected £{expected_total:.2f}, got £{received_total:.2f}'}, status=400)

        if order.points_used > 0:
            customer.total_points -= order.points_used
            customer.save()
            PointTransaction.objects.create(
                customer=customer,
                transaction_type='REDEEMED',
                points=-order.points_used,
                description=f"Redeemed for order #{order.id}",
            )

        order.transaction_id = transaction_id
        order.status = OrderStatus.RECEIVED  # Changed to 'Order Received'
        order.save()

        # Shipping (safe defaults)
        if order.shipping:
            shipping = data.get('shipping', {}) or {}
            ShippingAddress.objects.get_or_create(
                order=order,
                defaults=dict(
                    customer=customer,
                    address=shipping.get('address', ''),
                    city=shipping.get('city', ''),
                    county=shipping.get('county', ''),
                    postcode=shipping.get('postcode', ''),
                    country=shipping.get('country', ''),
                    is_saved=bool(shipping.get('save')),
                ),
            )

    return JsonResponse('Payment submitted successfully', safe=False)

@login_required
@require_POST
def apply_points(request):
    """Apply points discount to cart without creating empty orders."""
    data = json.loads(request.body or '{}')
    points_to_use = max(0, int(data.get('points', 0)))

    customer = Customer.objects.get(user=request.user)

    # Find 'Potential Order' with items
    order = (Order.objects
             .filter(customer=customer, status=OrderStatus.POTENTIAL)  # Changed
             .annotate(item_count=Count('orderitem'))
             .filter(item_count__gt=0)
             .order_by('-id')
             .first())
    if not order:
        return JsonResponse({'error': 'Your cart is empty.'}, status=400)

    cart_total_pence = int((order.get_cart_total * Decimal('100')).quantize(Decimal('1')))
    max_usable = min(int(customer.total_points), cart_total_pence)

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
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if not first_name or not last_name:
            error = 'First and last name are required.'
        elif not username:
            error = 'Username is required.'
        elif User.objects.filter(username=username).exists():
            error = 'Username already exists.'
        elif not email:
            error = 'Email is required.'
        elif User.objects.filter(email=email).exists():
            error = 'Email already exists.'
        elif password1 != password2:
            error = 'Passwords do not match.'
        else:
            # Validate password using Django's password validators
            try:
                validate_password(password1, user=None)
            except ValidationError as e:
                error = ' '.join(e.messages)
            else:
                # Create user
                user = User.objects.create_user(
                    username=username, 
                    email=email, 
                    password=password1,
                    first_name=first_name,
                    last_name=last_name
                )
                # Create customer with full name
                Customer.objects.get_or_create(
                    user=user,
                    defaults={
                        'name': f"{first_name} {last_name}",
                        'email': email
                    }
                )
                auth_login(request, user)
                return redirect('home')
                
    return render(request, 'pages/login.html', {
        'cartItems': cartItems,
        'error': error,
        'show_register': bool(error) or request.method == 'POST'
    })

def logout(request):
    auth_logout(request)
    return render(request, 'pages/home.html', {'message': 'Logged out successfully!'})


# ========== User Profile & Orders ==========
@login_required
def profile(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    
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

    message = None
    error = None

    # Handle POST for profile updates
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        # Update personal info (name & email)
        if form_type == 'personal_info':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            
            if not first_name or not last_name:
                error = 'First and last name are required.'
            elif not email:
                error = 'Email is required.'
            elif User.objects.filter(email=email).exclude(id=request.user.id).exists():
                error = 'This email is already in use by another account.'
            else:
                # Update User model
                request.user.first_name = first_name
                request.user.last_name = last_name
                request.user.email = email
                request.user.save()
                
                # Update Customer model
                customer.name = f"{first_name} {last_name}"
                customer.email = email
                customer.save()
                
                message = 'Personal information updated successfully!'
        
        # Update address
        elif form_type == 'address':
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
                message = 'Address updated successfully!'
            else:
                error = 'Address, city, postcode, and country are required.'

    return render(request, 'pages/profile.html', {
        'cartItems': cartItems,
        'customer': customer,
        'recent_transactions': recent_transactions,
        'recent_parcels': recent_parcels,
        'plastic_types': plastic_types,
        'is_premium': customer.is_premium,
        'parcel_count': parcel_count,
        'verified_weight': verified_weight,
        'premium_progress': premium_progress,
        'address_obj': address_obj,
        'message': message,
        'error': error,
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
    return render(request, 'pages/shipping_waste_success.html', {  # Changed backslash to forward slash
        'cartItems': data.get('cartItems', 0),
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

