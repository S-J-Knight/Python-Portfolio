import datetime
from django.shortcuts import render
from django.http import JsonResponse
from .models import *
import json

def store(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        order = Order.objects.filter(customer=customer, complete=False).first()
        cartItems = order.get_cart_items if order else 0
    else:
        cartItems = 0
    products = Product.objects.all()
    context = {'products': products, 'cartItems': cartItems}
    return render(request, 'store/store.html', context)

def cart(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        # Only get the current incomplete order, do NOT create a new one
        order = Order.objects.filter(customer=customer, complete=False).first()
        items = order.orderitem_set.all() if order else []
        cartItems = order.get_cart_items if order else 0
    else:
        items = []
        order = None
        cartItems = 0
    context = {'items': items, 'order': order, 'cartItems': cartItems}
    return render(request, 'store/cart.html', context)


def checkout(request):
    if request.user.is_authenticated:
        customer = request.user.customer
        last_address = ShippingAddress.objects.filter(customer=customer, is_saved=True).order_by('-date_added').first()
        needs_shipping = last_address is None
        order = Order.objects.filter(customer=customer, complete=False).first()
        items = order.orderitem_set.all() if order else []
        cartItems = order.get_cart_items if order else 0
    else:
        needs_shipping = True
        last_address = None
        items = []
        order = None
        cartItems = 0
    context = {'items': items, 'order': order, 'cartItems': cartItems, 'needs_shipping': needs_shipping, 'last_address': last_address}
    return render(request, 'store/checkout.html', context)

def updateItem(request):
	data = json.loads(request.body)
	productId = data['productId']
	action = data['action']
	print('Action:', action)
	print('Product:', productId)

	customer = request.user.customer
	product = Product.objects.get(id=productId)
	order, created = Order.objects.get_or_create(customer=customer, complete=False)

	orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

	if action == 'add':
		orderItem.quantity = (orderItem.quantity + 1)
	elif action == 'remove':
		orderItem.quantity = (orderItem.quantity - 1)

	orderItem.save()

	if orderItem.quantity <= 0:
		orderItem.delete()

	return JsonResponse('Item was added', safe=False)


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

    return JsonResponse('Payment submitted..', safe=False)
