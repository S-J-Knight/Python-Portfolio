from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

def send_order_confirmation(order):
    """Send order confirmation email"""
    subject = f'Order Confirmation #{order.id}'
    
    context = {
        'order': order,
        'customer': order.customer,
        'items': order.orderitem_set.all(),
        'total': order.get_cart_total_after_points,
    }
    
    html_message = render_to_string('emails/order_confirmation.html', context)
    
    # Better plain text version
    plain_message = f"""
Hi {order.customer.name},

Thank you for your order! We've received your order and will process it soon.

Order #{order.id}
Order Date: {order.date_ordered.strftime('%B %d, %Y')}

Items:
"""
    for item in context['items']:
        plain_message += f"- {item.product.name} x {item.quantity} - £{item.get_total:.2f}\n"
    
    if order.points_used > 0:
        plain_message += f"\nPoints Discount ({order.points_used} pts): -£{order.points_used:.2f}"
    
    plain_message += f"\n\nTotal: £{context['total']:.2f}\n\nWe'll send you another email when your order ships.\n\nQuestions? Contact us at support@yoursite.com"
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.customer.email],
        html_message=html_message,
        fail_silently=False,
    )

def send_order_processing(order):
    """Send email when order moves to processing"""
    subject = f'Your Order #{order.id} is Being Processed'
    
    context = {
        'order': order,
        'customer': order.customer,
    }
    
    html_message = render_to_string('emails/order_processing.html', context)
    
    # Plain text version
    plain_message = f"""
Hi {order.customer.name},

Great news! Your order is now being processed.

Order #{order.id}
Status: Processing

We're carefully preparing your items for shipment.
You'll receive a shipping confirmation with tracking information once your order ships.

Questions? Contact us at support@yoursite.com
    """
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.customer.email],
        html_message=html_message,
        fail_silently=False,
    )

def send_order_shipped(order):
    """Send email when order is shipped"""
    subject = f'Your Order #{order.id} Has Shipped! 📦'
    
    context = {
        'order': order,
        'customer': order.customer,
        'tracking_number': order.tracking_number,
    }
    
    html_message = render_to_string('emails/order_shipped.html', context)
    
    # Plain text version
    tracking_info = f"\nTracking Number: {order.tracking_number}\n" if order.tracking_number else "\nTracking information will be available soon.\n"
    
    plain_message = f"""
Hi {order.customer.name},

Exciting news! Your order is on its way.

Order #{order.id}
{tracking_info}
Your package should arrive within 3-5 business days.

Questions? Contact us at support@yoursite.com
    """
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.customer.email],
        html_message=html_message,
        fail_silently=False,
    )