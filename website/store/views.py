import json
import datetime
from decimal import Decimal, ROUND_FLOOR
from django.apps import apps
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, F
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import connection

from .models import *
from .utils import cookieCart, cartData  # ✅ Removed guestOrder
from .emails import send_order_confirmation

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


POINT_VALUE = Decimal('0.01')  # £ per point

# ========== Public Pages ==========
def home(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    
    from django.db.models import Sum
    
    # Count processed parcels (lowercase 'processed')
    total_parcels = IncomingParcel.objects.filter(status='processed').count()
    
    # Get total mass from processed parcels
    total_mass = IncomingParcel.objects.filter(
        status='processed'
    ).aggregate(
        total=Sum('materials__weight_kg')
    )['total'] or 0
    
    # Get latest 2 published blog posts for homepage preview
    latest_posts = BlogPost.objects.filter(published=True).order_by('-created_at')[:2]
    
    context = {
        'cartItems': cartItems,
        'total_parcels': total_parcels,
        'total_mass': total_mass,
        'latest_posts': latest_posts,
    }
    return render(request, 'pages/home.html', context)

def about(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    return render(request, 'pages/about.html', {'cartItems': cartItems})

def privacy(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    return render(request, 'pages/privacy.html', {'cartItems': cartItems})

def roadmap(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    return render(request, 'pages/roadmap.html', {'cartItems': cartItems})

# ========== Store Views ==========
def store(request):
    data = cartData(request)
    cartItems = data['cartItems']
    product_type = request.GET.get('product_type', '')
    colour = request.GET.get('colour', '')
    products = Product.objects.all()
    if product_type:
        products = products.filter(product_type=product_type)
    if colour:
        products = products.filter(colour=colour)

    context = {
        'products': products,
        'product_type_choices': Product.PRODUCT_TYPE_CHOICES,
        'colour_choices': Product.COLOUR_CHOICES,
        'selected_product_type': product_type,
        'selected_colour': colour,
        'cartItems': cartItems
    }
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
    data = json.loads(request.body or '{}')
    product_id = data.get('productId')
    action = data.get('action')
    try:
        qty = int(data.get('quantity', 1))
    except (TypeError, ValueError):
        qty = 1

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Auth required for this endpoint'}, status=401)

    customer = request.user.customer
    use_locks = connection.vendor != 'sqlite'

    with transaction.atomic():
        if use_locks:
            product = Product.objects.select_for_update().get(id=product_id)
            order = (Order.objects.select_for_update()
                     .filter(customer=customer, status=OrderStatus.POTENTIAL)
                     .order_by('-id').first()) or Order.objects.create(customer=customer, status=OrderStatus.POTENTIAL)
            order_item, _ = OrderItem.objects.select_for_update().get_or_create(order=order, product=product)
        else:
            product = Product.objects.get(id=product_id)
            order = (Order.objects
                     .filter(customer=customer, status=OrderStatus.POTENTIAL)
                     .order_by('-id').first()) or Order.objects.create(customer=customer, status=OrderStatus.POTENTIAL)
            order_item, _ = OrderItem.objects.get_or_create(order=order, product=product)

        if action == 'add':
            # Add treats qty<=0 as 1 (no negative adds)
            qty = max(1, qty)
            new_qty = order_item.quantity + qty
            if product.stock_quantity <= 0:
                return JsonResponse({'error': 'Product is out of stock'}, status=400)
            if new_qty > product.stock_quantity:
                return JsonResponse({'error': f'Only {product.stock_quantity} items available'}, status=400)
            order_item.quantity = new_qty
            order_item.save()
            return JsonResponse({'ok': True, 'quantity': order_item.quantity})

        elif action == 'remove':
            qty = max(1, qty)
            order_item.quantity = max(0, order_item.quantity - qty)
            if order_item.quantity == 0:
                order_item.delete()
                return JsonResponse({'ok': True, 'deleted': True})
            order_item.save()
            return JsonResponse({'ok': True, 'quantity': order_item.quantity})

        elif action == 'set':
            if qty <= 0:
                order_item.delete()
                return JsonResponse({'ok': True, 'deleted': True})
            if qty > product.stock_quantity:
                return JsonResponse({'error': f'Only {product.stock_quantity} items available'}, status=400)
            order_item.quantity = qty
            order_item.save()
            return JsonResponse({'ok': True, 'quantity': order_item.quantity})

    return JsonResponse({'ok': True})

def processOrder(request):
    transaction_id = datetime.datetime.now().timestamp()
    data = json.loads(request.body)

    if request.user.is_authenticated:
        customer = request.user.customer
        
        # Get the POTENTIAL order (the cart being checked out)
        order = (Order.objects
                .filter(customer=customer, status=OrderStatus.POTENTIAL)
                .annotate(item_count=Count('orderitem'))
                .filter(item_count__gt=0)
                .order_by('-id')
                .first())
        
        if not order:
            return JsonResponse({'error': 'Cart is empty'}, status=400)
        
        # Check stock before processing
        for item in order.orderitem_set.all():
            if item.product.stock_quantity < item.quantity:
                return JsonResponse({
                    'error': f'{item.product.name} is out of stock or insufficient quantity available'
                }, status=400)
        
        with transaction.atomic():
            # Deduct stock
            for item in order.orderitem_set.all():
                product = item.product
                product.stock_quantity -= item.quantity
                product.save()
                print(f"✅ Deducted {item.quantity} from {product.name}. New stock: {product.stock_quantity}")

            # >>> ADD: points deduction (clamped and persisted) <<<
            cart_total = Decimal(order.get_cart_total)
            max_by_total = int((cart_total / POINT_VALUE).to_integral_value(rounding=ROUND_FLOOR))
            balance = int(customer.total_points or 0)
            usable = min(int(order.points_used or 0), balance, max_by_total)

            order.points_used = usable
            order.points_discount = (Decimal(usable) * POINT_VALUE).quantize(Decimal('0.01'))

            if usable > 0:
                Customer.objects.filter(pk=customer.pk).update(total_points=F('total_points') - usable)
                PointTransaction.objects.create(
                    customer=customer,
                    transaction_type='REDEEMED',
                    points=-usable,
                    description=f'Redeemed for Order #{order.id}',
                )
            # <<< END add >>>

            total = float(data['form']['total'])
            order.transaction_id = transaction_id
            order.status = OrderStatus.RECEIVED
            order.save(update_fields=['status','transaction_id','points_used','points_discount'])

            # Send confirmation email
            try:
                send_order_confirmation(order)
            except Exception as e:
                print(f"Failed to send confirmation email: {e}")
            
            # Handle shipping address
            if order.shipping == True:
                ShippingAddress.objects.create(
                    customer=customer,
                    order=order,
                    address=data['shipping']['address'],
                    city=data['shipping']['city'],
                    county=data['shipping']['county'],
                    postcode=data['shipping']['postcode'],
                    country=data['shipping']['country'],
                )
    
    else:
        # Guest order - stock control for guests
        print('Processing guest order...')
        cart = json.loads(request.COOKIES.get('cart', '{}'))
        
        # Check stock for guest orders
        out_of_stock = []
        for product_id, item_data in cart.items():
            product = Product.objects.get(id=product_id)
            quantity = item_data['quantity']
            
            if product.stock_quantity < quantity:
                out_of_stock.append(product.name)
        
        if out_of_stock:
            return JsonResponse({
                'error': f'Out of stock: {", ".join(out_of_stock)}'
            }, status=400)
        
        # Deduct stock for guest orders
        with transaction.atomic():
            for product_id, item_data in cart.items():
                product = Product.objects.get(id=product_id)
                quantity = item_data['quantity']
                product.stock_quantity -= quantity
                product.save()
                print(f"✅ [GUEST] Deducted {quantity} from {product.name}. New stock: {product.stock_quantity}")
    
    return JsonResponse('Payment submitted successfully', safe=False)

@require_POST
def apply_points(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Login required'}, status=401)

    data = json.loads(request.body or '{}')
    requested = int(data.get('points', 0) or 0)
    requested = max(0, requested)

    customer = request.user.customer
    order = (Order.objects
             .filter(customer=customer, status=OrderStatus.POTENTIAL)
             .order_by('-id').first()) or Order.objects.create(customer=customer, status=OrderStatus.POTENTIAL)

    cart_total = Decimal(order.get_cart_total)
    max_by_total = int((cart_total / POINT_VALUE).to_integral_value(rounding=ROUND_FLOOR))
    balance = int(customer.total_points or 0)
    use = min(requested, balance, max_by_total)

    discount = (Decimal(use) * POINT_VALUE).quantize(Decimal('0.01'))
    order.points_used = use
    order.points_discount = discount
    order.save(update_fields=['points_used', 'points_discount'])

    new_total = (cart_total - discount).quantize(Decimal('0.01'))
    return JsonResponse({
        'success': True,
        'points_used': use,
        'discount': f'{discount}',
        'new_total': f'{new_total}',
        'balance_left': balance - use,
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
                
                # Check if email was previously subscribed to newsletter
                newsletter_subscribed = False
                try:
                    newsletter_subscriber = NewsletterSubscriber.objects.get(email=email, is_active=True)
                    newsletter_subscribed = True
                except NewsletterSubscriber.DoesNotExist:
                    pass
                
                # Create customer with full name and newsletter subscription status
                Customer.objects.get_or_create(
                    user=user,
                    defaults={
                        'name': f"{first_name} {last_name}",
                        'email': email,
                        'newsletter_subscribed': newsletter_subscribed
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
                # Get the existing saved address or create a new one
                if address_obj:
                    # Update existing
                    address_obj.address = address
                    address_obj.city = city
                    address_obj.county = county
                    address_obj.postcode = postcode
                    address_obj.country = country
                    address_obj.save()
                else:
                    # Create new
                    address_obj = ShippingAddress.objects.create(
                        customer=customer,
                        is_saved=True,
                        address=address,
                        city=city,
                        county=county,
                        postcode=postcode,
                        country=country,
                    )
                message = 'Address updated successfully!'
            else:
                error = 'Address, city, postcode, and country are required.'
        
        # Update newsletter subscription
        elif form_type == 'newsletter':
            from store.mailerlite import mailerlite_client
            import logging
            logger = logging.getLogger(__name__)
            
            newsletter_subscribed = request.POST.get('newsletter_subscribed') == 'on'
            
            # Check if MailerLite is configured
            if not mailerlite_client.is_configured():
                # Just update local status if API not configured (dev mode)
                customer.newsletter_subscribed = newsletter_subscribed
                customer.save()
                if newsletter_subscribed:
                    message = 'Newsletter preference saved! (Note: MailerLite API not configured - email subscription will be activated when deployed)'
                else:
                    message = 'Newsletter preference updated.'
            elif newsletter_subscribed and not customer.newsletter_subscribed:
                # Subscribe to newsletter
                result = mailerlite_client.add_subscriber(
                    email=customer.email,
                    name=customer.name
                )
                if result:
                    # Store the subscriber ID if available
                    if isinstance(result, dict) and 'data' in result:
                        customer.mailerlite_subscriber_id = result['data'].get('id')
                    customer.newsletter_subscribed = True
                    customer.save()
                    message = 'Successfully subscribed to newsletter!'
                else:
                    logger.error(f"Failed to subscribe {customer.email} to MailerLite")
                    error = 'Failed to subscribe to newsletter. Please contact support if this persists.'
            
            elif not newsletter_subscribed and customer.newsletter_subscribed:
                # Unsubscribe from newsletter
                if customer.mailerlite_subscriber_id:
                    success = mailerlite_client.delete_subscriber(customer.mailerlite_subscriber_id)
                    if success:
                        customer.newsletter_subscribed = False
                        customer.mailerlite_subscriber_id = None
                        customer.save()
                        message = 'Successfully unsubscribed from newsletter.'
                    else:
                        logger.error(f"Failed to unsubscribe {customer.email} from MailerLite")
                        error = 'Failed to unsubscribe. Please contact support if this persists.'
                else:
                    # No subscriber ID stored, just update local status
                    customer.newsletter_subscribed = False
                    customer.save()
                    message = 'Newsletter subscription status updated.'

    context = {
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
        'points_in_pounds': customer.total_points / 100,  # Add this line
    }

    return render(request, 'pages/profile.html', context)

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

    # Combine orders and parcels into a single sorted list
    combined = []
    
    # Add orders with their date
    for order in orders:
        combined.append({
            'type': 'order',
            'object': order,
            'date': order.date_ordered
        })
    
    # Add parcels with their date
    for parcel in parcels:
        # Use the first available date field
        parcel_date = (
            parcel.date_submitted or 
            getattr(parcel, 'submitted_at', None) or 
            getattr(parcel, 'created_at', None)
        )
        if parcel_date:
            combined.append({
                'type': 'parcel',
                'object': parcel,
                'date': parcel_date
            })
    
    # Sort combined list by date (most recent first)
    combined.sort(key=lambda x: x['date'], reverse=True)

    context = {
        'orders': orders,
        'parcels': parcels,
        'combined': combined,
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

def recycle_and_earn(request):
    """Public page - accessible to guests"""
    data = cartData(request)  # works for guests too
    return render(request, 'pages/recycle_and_earn.html', {
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

def finalize_checkout(request, order_id):
    """Finalize the checkout process, update order status, and send confirmation email."""
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    customer = getattr(request.user, 'customer', None)
    order = None

    if customer:
        order = Order.objects.filter(customer=customer, id=order_id, status=OrderStatus.POTENTIAL).first()
        if order:
            with transaction.atomic():
                # Re-cap against balance and order value
                cart_total = Decimal(order.get_cart_total)
                max_by_total = int((cart_total / POINT_VALUE).to_integral_value(rounding=ROUND_FLOOR))
                balance = int(order.customer.total_points or 0)
                usable = min(int(order.points_used or 0), balance, max_by_total)

                # Persist final used/discount
                order.points_used = usable
                order.points_discount = (Decimal(usable) * POINT_VALUE).quantize(Decimal('0.01'))

                # Deduct from customer balance and record a transaction
                if usable > 0:
                    Customer.objects.filter(pk=order.customer_id).update(total_points=F('total_points') - usable)
                    PointTransaction.objects.create(
                        customer=order.customer,
                        transaction_type='REDEEMED',
                        points=-usable,
                        description=f'Redeemed for Order #{order.id}',
                    )

                order.status = OrderStatus.ORDER_RECEIVED
                order.save(update_fields=['status', 'points_used', 'points_discount', 'transaction_id'])

                # Send confirmation email
                try:
                    send_order_confirmation(order)
                except Exception as e:
                    print(f"Failed to send confirmation email: {e}")

                return JsonResponse({'success': True, 'order_id': order.id})

    return JsonResponse({'error': 'Invalid request'}, status=400)

def blog(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    
    # Get all published blog posts
    posts = BlogPost.objects.filter(published=True)
    
    context = {
        'cartItems': cartItems,
        'posts': posts,
    }
    return render(request, 'store/blog.html', context)


def blog_detail(request, slug):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    
    post = get_object_or_404(BlogPost, slug=slug, published=True)
    
    # Get related posts (latest 3, excluding current)
    related_posts = BlogPost.objects.filter(
        published=True
    ).exclude(id=post.id)[:3]
    
    context = {
        'cartItems': cartItems,
        'post': post,
        'related_posts': related_posts,
    }
    return render(request, 'store/blog_detail.html', context)


def business(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    
    from django.db.models import Sum
    
    # Get stats for business page
    total_parcels = IncomingParcel.objects.filter(status='processed').count()
    total_mass = IncomingParcel.objects.filter(
        status='processed'
    ).aggregate(
        total=Sum('materials__weight_kg')
    )['total'] or 0
    
    context = {
        'cartItems': cartItems,
        'total_parcels': total_parcels,
        'total_mass': total_mass,
    }
    return render(request, 'store/business.html', context)


@require_POST
def newsletter_signup(request):
    """Handle newsletter subscription via AJAX"""
    from .mailerlite import mailerlite_client
    
    try:
        email = request.POST.get('email', '').strip()
        name = request.POST.get('name', '').strip()
        
        if not email:
            return JsonResponse({'success': False, 'message': 'Email is required'})
        
        # Save to local database
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email,
            defaults={'name': name, 'is_active': True}
        )
        
        if not created:
            if subscriber.is_active:
                return JsonResponse({'success': False, 'message': 'You are already subscribed!'})
            else:
                # Reactivate if previously unsubscribed
                subscriber.is_active = True
                subscriber.save()
        
        # If user is logged in, also update their Customer profile
        if request.user.is_authenticated:
            try:
                customer = Customer.objects.get(user=request.user)
                customer.newsletter_subscribed = True
                # Save subscriber ID if we get one from MailerLite later
                customer.save()
            except Customer.DoesNotExist:
                pass  # Customer doesn't exist yet, no problem
        
        # Sync to MailerLite (if configured)
        if mailerlite_client.is_configured():
            result = mailerlite_client.add_subscriber(email, name)
            if result:
                # Store MailerLite subscriber ID in Customer model if user is logged in
                if request.user.is_authenticated:
                    try:
                        customer = Customer.objects.get(user=request.user)
                        if isinstance(result, dict) and 'data' in result:
                            customer.mailerlite_subscriber_id = result['data'].get('id')
                            customer.save()
                    except Customer.DoesNotExist:
                        pass
                
                if created:
                    return JsonResponse({'success': True, 'message': 'Thank you for subscribing!'})
                else:
                    return JsonResponse({'success': True, 'message': 'Welcome back! Your subscription has been reactivated.'})
            else:
                # MailerLite failed but local database succeeded
                return JsonResponse({
                    'success': True, 
                    'message': 'Subscribed! (Note: Email sync pending)'
                })
        else:
            # MailerLite not configured, just use local database
            if created:
                return JsonResponse({'success': True, 'message': 'Thank you for subscribing!'})
            else:
                return JsonResponse({'success': True, 'message': 'Welcome back! Your subscription has been reactivated.'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'An error occurred. Please try again.'})

def contact(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    context = {'cartItems': cartItems}
    return render(request, 'store/contact.html', context)