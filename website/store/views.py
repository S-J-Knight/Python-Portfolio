def order_detail(request, order_id):
    if not request.user.is_authenticated:
        return render(request, 'pages/login.html', {'error': 'Please log in to view order details.'})
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
def orders(request):
    if not request.user.is_authenticated:
        return render(request, 'pages/login.html', {'error': 'Please log in to view your orders.'})
    customer = getattr(request.user, 'customer', None)
    orders = []
    if customer:
        orders = Order.objects.filter(customer=customer).order_by('-date_ordered')
    return render(request, 'pages/orders.html', {'orders': orders, 'user': request.user})
def shipping_waste_form(request):
    if not request.user.is_authenticated:
        return render(request, 'pages/login.html', {'error': 'Please log in to access the shipping form.'})
    message = ''
    error = ''
    if request.method == 'POST':
        address = request.POST.get('address')
        city = request.POST.get('city')
        county = request.POST.get('county')
        postcode = request.POST.get('postcode')
        country = request.POST.get('country')
        details = request.POST.get('details')
        if address and city and postcode and country:
            from .models import IncomingParcel
            IncomingParcel.objects.create(
                user=request.user,
                address=address,
                city=city,
                county=county,
                postcode=postcode,
                country=country,
                details=details
            )
            message = 'Shipment submitted!'
        else:
            error = 'Please fill in all required fields.'
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    order = data.get('order', None)
    items = data.get('items', [])
    return render(request, 'pages/shipping_waste_form.html', {
        'user': request.user,
        'message': message,
        'error': error,
        'cartItems': cartItems,
        'order': order,
        'items': items,
    })
def logout(request):
    auth_logout(request)
    return render(request, 'pages/home.html', {'message': 'Logged out successfully!'})

def profile(request):
    if not request.user.is_authenticated:
        return render(request, 'pages/login.html', {'error': 'Please log in to view your profile.'})
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    customer = getattr(request.user, 'customer', None)
    address_obj = None
    if customer:
        address_obj = ShippingAddress.objects.filter(customer=customer, is_saved=True).order_by('-date_added').first()
    message = ''
    error = ''
    if request.method == 'POST':
        address = request.POST.get('address')
        city = request.POST.get('city')
        county = request.POST.get('county')
        postcode = request.POST.get('postcode')
        country = request.POST.get('country')
        if address and city and postcode and country:
            # Save new address
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
            address_obj = ShippingAddress.objects.filter(customer=customer, is_saved=True).order_by('-date_added').first()
        else:
            error = 'Please fill in all required fields.'
    is_premium = getattr(customer, 'is_premium', False) if customer else False
    is_business = getattr(customer, 'is_business', False) if customer else False
    from .models import IncomingParcel
    incoming_parcels = IncomingParcel.objects.filter(user=request.user).order_by('-date_submitted')
    return render(request, 'pages/profile.html', {
        'cartItems': cartItems,
        'user': request.user,
        'address_obj': address_obj,
        'message': message,
        'error': error,
        'is_premium': is_premium,
        'is_business': is_business,
        'incoming_parcels': incoming_parcels,
    })
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
import datetime
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import *
from .utils import cookieCart, cartData
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User

def store(request):
    data = cartData(request)
    cartItems = data['cartItems']
    products = Product.objects.all()  # <-- Add this line
    context = {'products': products, 'cartItems': cartItems}
    return render(request, 'store/store.html', context)

def cart(request):
    data = cartData(request)
    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    context = {'items':items, 'order':order, 'cartItems':cartItems}
    return render(request, 'store/cart.html', context)

def checkout(request):
    data = cartData(request)
    cartItems = data['cartItems']
    order = data['order']
    items = data['items']
    needs_shipping = data['needs_shipping']
    last_address = data['last_address']
    context = {'items': items, 'order': order, 'cartItems': cartItems, 'needs_shipping': needs_shipping, 'last_address': last_address}
    return render(request, 'store/checkout.html', context)

@require_POST
def update_item(request):
    """
    Accept JSON { productId, action } from cart.js.
    Handles authenticated users (guest logic kept in cart.js/cookies).
    """
    data = json.loads(request.body)
    productId = data.get('productId')
    action = data.get('action')

    if request.user.is_authenticated:
        customer, _ = Customer.objects.get_or_create(user=request.user, defaults={'name': request.user.username, 'email': request.user.email})
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
    # guest: cart.js manages cookie cart; return ok so frontend can refresh/update UI
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

        # Only mark as received if the totals match
        if total == float(order.get_cart_total):
            order.status = 'Order Received'
        order.save()

        if order.shipping == True:
            # Only create if not already exists for this order
            if not ShippingAddress.objects.filter(order=order).exists():
                ShippingAddress.objects.create(
                    customer=customer,
                    order=order,
                    address=data['shipping']['address'],
                    city=data['shipping']['city'],
                    county=data['shipping']['county'],
                    postcode=data['shipping']['postcode'],
                    country=data['shipping']['country'],
                    is_saved=data['shipping'].get('save', False),  # True if user ticked the box
                )
    else:
        print('User is not logged in')
        print('COOKIES:', request.COOKIES)
        name = data['form']['name']
        email = data['form']['email']

        cookieData = cookieCart(request)
        items = cookieData['items']

        customer, created = Customer.objects.get_or_create(
            email=email,
        )
        customer.name = name
        customer.save()

        order = Order.objects.create(
            customer=customer,
            status='Order Received',
        )

        for item in items:
            product = Product.objects.get(id=item['id'])
            orderItem = OrderItem.objects.create(
                product=product,
                order=order,
                quantity=item['quantity'],
            )

    total = float(data['form']['total'])
    order.transaction_id = transaction_id

    if round(total, 2) == round(float(order.get_cart_total), 2):
        order.status = 'Order Received'
    order.save()

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

    return JsonResponse('Payment submitted..', safe=False)

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    data = cartData(request)
    cartItems = data['cartItems']
    context = {
        'product': product,
        'cartItems': cartItems,
    }
    return render(request, 'store/product_detail.html', context)

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

def send_waste(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    return render(request, 'pages/send_waste.html', {'cartItems': cartItems})

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
            return render(request, 'pages/home.html', {'cartItems': cartItems, 'message': 'Login successful!'})
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
            return render(request, 'pages/home.html', {'cartItems': cartItems, 'message': 'Account created and logged in!'})
    return render(request, 'pages/login.html', {'cartItems': cartItems, 'error': error, 'show_register': True})

def create_user(request):
    username = request.POST.get('username')
    email = request.POST.get('email')
    password = request.POST.get('password')

    user = User.objects.create_user(username, email, password)

    return JsonResponse({'status': 'user created'})

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return JsonResponse({'status': 'login successful'})
        else:
            return JsonResponse({'status': 'invalid credentials'}, status=401)

    return JsonResponse({'status': 'method not allowed'}, status=405)