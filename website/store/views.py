import datetime
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import *
from .utils import cookieCart, cartData

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
        order, _ = Order.objects.get_or_create(customer=customer, complete=False)
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
        return JsonResponse({'status': 'ok'})
    # guest: cart.js manages cookie cart; return ok so frontend can refresh/update UI
    return JsonResponse({'status': 'guest'})

def processOrder(request):
    transaction_id = datetime.datetime.now().timestamp()
    data = json.loads(request.body)

    if request.user.is_authenticated:
        customer = request.user.customer
        order = Order.objects.filter(customer=customer, complete=False).first()
        if not order:
            return JsonResponse('No incomplete order found', safe=False)
        total = float(data['form']['total'])
        order.transaction_id = transaction_id

        # Only mark complete if the totals match
        if total == float(order.get_cart_total):
            order.complete = True
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
            complete=False,
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
        order.complete = True
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
    return render(request, 'pages/home.html', {'cartItems': cartItems})

def about(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    return render(request, 'pages/about.html', {'cartItems': cartItems})

def send_waste(request):
    data = cartData(request)
    cartItems = data.get('cartItems', 0)
    return render(request, 'pages/send_waste.html', {'cartItems': cartItems})
