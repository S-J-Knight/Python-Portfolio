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

def send_wtn_reminder_email(customer, parcel, collection_date):
    """Send WTN reminder email 3 working days before collection"""
    subject = f'Action Required: Complete Your Waste Transfer Notice - Collection {collection_date.strftime("%d %B %Y")}'
    
    # Build WTN URL
    from django.urls import reverse
    wtn_url = f"{settings.SITE_URL}{reverse('store:waste_transfer_notice', args=[parcel.id])}"
    
    plain_message = f"""Hello {customer.name},

Your Waste Transfer Notice (WTN) form for your upcoming collection is needing to be completed. Can you please complete this at your earliest convenience as we cannot collect the box off you until you have done so.

Collection Date: {collection_date.strftime("%A, %d %B %Y")}

Complete your WTN here: {wtn_url}

If no one is available on the day you have previously scheduled, please email collection@knightcycle.co.uk and we can rearrange it.

Failure to sign the WTN will not mean you lose your collection, it just means it will not be scheduled until it has been completed.

Thank you for choosing us,
All the best,

Knightcycle
"""

    html_message = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #116944 0%, #0d5435 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0;">
            <h1 style="margin: 0; font-size: 24px;"> Action Required</h1>
        </div>
        
        <div style="background: white; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px;">
            <p>Hello <strong>{customer.name}</strong>,</p>
            
            <p>Your <strong>Waste Transfer Notice (WTN)</strong> form for your upcoming collection is needing to be completed. Can you please complete this at your earliest convenience as we cannot collect the box off you until you have done so.</p>
            
            <div style="background: #f0fdf4; border-left: 4px solid #116944; padding: 15px; margin: 20px 0;">
                <strong style="color: #116944;"> Collection Date:</strong><br>
                <span style="font-size: 18px;">{collection_date.strftime("%A, %d %B %Y")}</span>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{wtn_url}" style="background: #116944; color: white; padding: 14px 30px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">
                     Complete WTN Now
                </a>
            </div>
            
            <p style="font-size: 14px; color: #666; border-top: 1px solid #e5e7eb; padding-top: 20px; margin-top: 20px;">
                <strong>Need to reschedule?</strong><br>
                If no one is available on the day you have previously scheduled, please email 
                <a href="mailto:collection@knightcycle.co.uk" style="color: #116944;">collection@knightcycle.co.uk</a> 
                and we can rearrange it.
            </p>
            
            <p style="font-size: 14px; color: #666;">
                <em>Failure to sign the WTN will not mean you lose your collection, it just means it will not be scheduled until it has been completed.</em>
            </p>
            
            <p>Thank you for choosing us,<br>
            All the best,</p>
            
            <p style="color: #116944; font-weight: 600;">Knightcycle</p>
        </div>
    </div>
</body>
</html>
"""

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[customer.user.email],
        html_message=html_message,
        fail_silently=False,
    )
