import json
import datetime
from django.apps import apps
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import *
from .utils import cookieCart, cartData


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
    cartItems = data['cartItems']
    order = data['order']
    items = data['items']
    context = {'items': items, 'order': order, 'cartItems': cartItems}
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

        total = float(data['form']['total'])
        order.transaction_id = transaction_id

        if round(total, 2) == round(float(order.get_cart_total), 2):
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
    cartItems = data.get('cartItems', 0)
    customer = getattr(request.user, 'customer', None)
    address_obj = None
    if customer:
        address_obj = ShippingAddress.objects.filter(
            customer=customer,
            is_saved=True
        ).order_by('-date_added').first()

    message = ''
    error = ''
    if request.method == 'POST':
        address = request.POST.get('address')
        city = request.POST.get('city')
        county = request.POST.get('county')
        postcode = request.POST.get('postcode')
        country = request.POST.get('country')
        if address and city and postcode and country:
            ShippingAddress.objects.create(
                customer=customer,
                address=address,
                city=city,
                county=county,
                postcode=postcode,
                country=country,
                is_saved=True
            )
            message = 'Shipping address updated!'
            address_obj = ShippingAddress.objects.filter(
                customer=customer,
                is_saved=True
            ).order_by('-date_added').first()
        else:
            error = 'Please fill in all required fields.'

    is_premium = getattr(customer, 'is_premium', False) if customer else False
    is_business = getattr(customer, 'is_business', False) if customer else False

    return render(request, 'pages/profile.html', {
        'cartItems': cartItems,
        'user': request.user,
        'address_obj': address_obj,
        'message': message,
        'error': error,
        'is_premium': is_premium,
        'is_business': is_business,
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
    """Original shipping waste form (different from send_waste)"""
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    message = ''
    error = ''
    
    if request.method == 'POST':
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        county = request.POST.get('county', '').strip()
        postcode = request.POST.get('postcode', '').strip()
        country = request.POST.get('country', '').strip()
        details = request.POST.get('details', '').strip()
        waste_types = request.POST.getlist('waste_types')  # ['PLA', 'PETG', etc.]
        
        if not address or not city or not postcode or not country or not waste_types:
            error = 'Please fill in all required fields and select at least one waste type.'
        else:
            # Create the IncomingParcel
            parcel = IncomingParcel.objects.create(
                user=request.user,
                address=address,
                city=city,
                county=county,
                postcode=postcode,
                country=country,
                details=details,
                pla='PLA' in waste_types,
                petg='PETG' in waste_types,
            )
            # The post_save signal will auto-create ParcelMaterial rows
            message = 'Shipment submitted successfully!'
            # Optionally redirect to orders
            # return redirect('store:orders')
    
    return render(request, 'pages/shipping_waste_form.html', {
        'cartItems': cartItems,
        'message': message,
        'error': error,
    })

@login_required
def send_waste(request):
    """Renders the send_waste.html page (different from shipping_waste_form)"""
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    return render(request, 'pages/send_waste.html', {'cartItems': cartItems})