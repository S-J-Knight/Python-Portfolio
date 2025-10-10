import json
from .models import *

def cookieCart(request):
    try:
        cart = json.loads(request.COOKIES['cart'])
    except:
        cart = {}
        print('CART:', cart)

    items = []
    order = {'get_cart_total':0, 'get_cart_items':0, 'shipping':False}
    cartItems = order['get_cart_items']

    for i in cart:
        try:
            cartItems += cart[i]['quantity']

            product = Product.objects.get(id=i)
            total = (product.price * cart[i]['quantity'])

            order['get_cart_total'] += total
            order['get_cart_items'] += cart[i]['quantity']

            item = {
                'id':product.id,
                'product':{'id':product.id,'name':product.name, 'price':product.price, 
                'imageURL':product.imageURL}, 'quantity':cart[i]['quantity'],
                'digital':product.digital,'get_total':total,
            }
            items.append(item)

            if product.digital == False: order['shipping'] = True
        except:
            pass
    return {'cartItems':cartItems, 'order':order, 'items':items}

def cartData(request):
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
        cookieData = cookieCart(request)
        cartItems = cookieData['cartItems']
        order = cookieData['order']
        items = cookieData['items']
    context = {'items': items, 'order': order, 'cartItems': cartItems, 'needs_shipping': needs_shipping, 'last_address': last_address}
    return context