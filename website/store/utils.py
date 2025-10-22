import json
from .models import Product, Order, OrderItem, Customer

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
        # Get or create customer
        customer, created = Customer.objects.get_or_create(
            user=request.user,
            defaults={
                'name': request.user.username,
                'email': request.user.email
            }
        )
        
        order, created = Order.objects.get_or_create(customer=customer, status='Order Received')
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
        needs_shipping = order.shipping
        
        # Get last saved address if exists
        last_address = None
        from .models import ShippingAddress
        saved = ShippingAddress.objects.filter(customer=customer, is_saved=True).order_by('-date_added').first()
        if saved:
            last_address = {
                'address': saved.address,
                'city': saved.city,
                'county': saved.county,
                'postcode': saved.postcode,
                'country': saved.country,
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