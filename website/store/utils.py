import json
from decimal import Decimal
from .models import Product, Order, OrderItem, ShippingAddress, Customer, OrderStatus  # Added OrderStatus

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
    return {'cartItems': cartItems, 'order': order, 'items': items, 'needs_shipping': order['shipping']}

def cartData(request):
    """Authenticated cart data without auto-creating blank orders."""
    if request.user.is_authenticated:
        customer, _ = Customer.objects.get_or_create(
            user=request.user,
            defaults={'name': request.user.username, 'email': request.user.email},
        )

        # Find 'Potential Order' (not 'Order Received')
        order = (Order.objects
                 .filter(customer=customer, status=OrderStatus.POTENTIAL)
                 .order_by('-id')
                 .first())

        if order:
            items = order.orderitem_set.all()
            cartItems = order.get_cart_items
            needs_shipping = order.shipping
        else:
            order = None
            items = []
            cartItems = 0
            needs_shipping = False

        # Last saved address
        last = ShippingAddress.objects.filter(customer=customer, is_saved=True).order_by('-date_added').first()
        last_address = None
        if last:
            last_address = {
                'address': last.address, 'city': last.city, 'county': last.county,
                'postcode': last.postcode, 'country': last.country,
            }
    else:
        cookieData = cookieCart(request)
        cartItems = cookieData['cartItems']
        order = cookieData['order']
        items = cookieData['items']
        needs_shipping = cookieData.get('needs_shipping', False)
        last_address = None

    return {
        'cartItems': cartItems,
        'order': order,
        'items': items,
        'needs_shipping': needs_shipping,
        'last_address': last_address,
    }

def get_cart_total(request):
    if request.user.is_authenticated:
        customer = getattr(request.user, 'customer', None)
        order = (Order.objects
                 .filter(customer=customer, status=OrderStatus.POTENTIAL)  # Changed from 'Order Received'
                 .order_by('-id')
                 .first())
        if order:
            return order.get_cart_total
    return 0