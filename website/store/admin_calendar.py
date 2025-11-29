"""
Admin Calendar View for Knightcycle
Shows upcoming events: subscription collections, PAYG requests, and store orders
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
import calendar as cal
from .models import Customer, IncomingParcel, Order, OrderStatus, ParcelStatus


def calculate_recurring_date(reference_date, target_year, target_month):
    """
    Calculate the recurring date for a given month based on a reference date pattern.
    
    For example, if reference_date is the 4th Thursday of December 2025,
    this will return the 4th Thursday of the target month/year.
    
    Args:
        reference_date: The original preferred_delivery_day (e.g., 2025-12-25)
        target_year: The year to calculate for
        target_month: The month to calculate for
    
    Returns:
        A date object representing the same day pattern in the target month,
        or None if the pattern doesn't exist in that month
    """
    # Get the weekday (0=Monday, 6=Sunday) and the day from the reference
    ref_weekday = reference_date.weekday()
    ref_day = reference_date.day
    
    # Find which occurrence of this weekday it is in the reference month
    # (e.g., 1st Monday, 2nd Tuesday, 4th Thursday, etc.)
    occurrence = 0
    for day in range(1, ref_day + 1):
        test_date = datetime(reference_date.year, reference_date.month, day).date()
        if test_date.weekday() == ref_weekday:
            occurrence += 1
    
    # Now find the same occurrence in the target month
    count = 0
    for day in range(1, 32):  # Max days in any month
        try:
            test_date = datetime(target_year, target_month, day).date()
            if test_date.weekday() == ref_weekday:
                count += 1
                if count == occurrence:
                    return test_date
        except ValueError:
            # Day doesn't exist in this month
            break
    
    # If the occurrence doesn't exist (e.g., 5th Monday in a month with only 4 Mondays),
    # return the last occurrence of that weekday
    for day in range(31, 0, -1):
        try:
            test_date = datetime(target_year, target_month, day).date()
            if test_date.weekday() == ref_weekday:
                return test_date
        except ValueError:
            continue
    
    return None


@staff_member_required
def admin_calendar_view(request):
    """
    Display a calendar showing:
    - Subscription collection dates (based on preferred_delivery_day)
    - PAYG collection requests (IncomingParcel with status=AWAITING)
    - Store orders to fulfill (Order with status=RECEIVED or PROCESSING)
    """
    # Get current month/year or from query params
    now = timezone.now()
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    
    # Calculate previous and next month for navigation
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year
    
    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year
    
    # Get calendar data
    cal_obj = cal.Calendar(firstweekday=0)  # Monday as first day
    month_days = cal_obj.monthdatescalendar(year, month)
    
    # Fetch events for this month
    month_start = datetime(year, month, 1).date()
    if month == 12:
        month_end = datetime(year + 1, 1, 1).date()
    else:
        month_end = datetime(year, month + 1, 1).date()
    
    events = get_events_for_month(month_start, month_end)
    
    # Organize events by date
    events_by_date = {}
    for event in events:
        date_key = event['date'].strftime('%Y-%m-%d')
        if date_key not in events_by_date:
            events_by_date[date_key] = []
        events_by_date[date_key].append(event)
    
    context = {
        'title': 'Collection & Order Calendar',
        'current_month': datetime(year, month, 1),
        'month_days': month_days,
        'month_name': cal.month_name[month],
        'year': year,
        'month': month,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'events_by_date': events_by_date,
        'today': now.date(),
    }
    
    return render(request, 'admin/store/calendar.html', context)


def get_events_for_month(month_start, month_end):
    """
    Fetch all events for the given month range
    Returns a list of event dictionaries
    """
    events = []
    
    # 1. Subscription Collections - recurring monthly based on preferred_delivery_day pattern
    subscription_customers = Customer.objects.filter(
        subscription_active=True,
        subscription_cancelled=False,
        preferred_delivery_day__isnull=False
    ).select_related('user')
    
    for customer in subscription_customers:
        # Calculate the recurring date for this month based on the customer's preferred_delivery_day
        collection_date = calculate_recurring_date(
            customer.preferred_delivery_day,
            month_start.year,
            month_start.month
        )
        
        # Only add if the calculated date is within the current month
        if collection_date and month_start <= collection_date < month_end:
            events.append({
                'date': collection_date,
                'type': 'subscription',
                'title': f'📦 Subscription Collection: {customer.name}',
                'description': f'{customer.subscription_type or "Monthly Subscription"}',
                'customer': customer,
                'link': f'/admin/store/customer/{customer.id}/change/',
                'color': '#3b82f6',  # blue
            })
    
    # 2. PAYG Collection Requests - awaiting parcels
    payg_parcels = IncomingParcel.objects.filter(
        status=ParcelStatus.AWAITING,
        date_submitted__date__gte=month_start,
        date_submitted__date__lt=month_end
    ).select_related('user').order_by('date_submitted')
    
    for parcel in payg_parcels:
        customer_name = "Unknown"
        if parcel.user:
            try:
                customer = Customer.objects.get(user=parcel.user)
                customer_name = customer.name
            except Customer.DoesNotExist:
                customer_name = parcel.user.username
        
        events.append({
            'date': parcel.date_submitted.date(),
            'type': 'payg_request',
            'title': f'📬 PAYG Collection Request: {customer_name}',
            'description': f'Parcel {parcel} - {parcel.address}, {parcel.city}',
            'parcel': parcel,
            'link': f'/admin/store/incomingparcel/{parcel.id}/change/',
            'color': '#eab308',  # yellow
        })
    
    # 3. Store Orders to Fulfill - orders that need attention
    pending_orders = Order.objects.filter(
        Q(status=OrderStatus.RECEIVED) | Q(status=OrderStatus.PROCESSING),
        date_ordered__date__gte=month_start,
        date_ordered__date__lt=month_end
    ).select_related('customer').order_by('date_ordered')
    
    for order in pending_orders:
        customer_name = order.customer.name if order.customer else "Guest"
        
        events.append({
            'date': order.date_ordered.date(),
            'type': 'order',
            'title': f'🛒 Order to Fulfill: {customer_name}',
            'description': f'Order {order.order_number} - Status: {order.status}',
            'order': order,
            'link': f'/admin/store/order/{order.id}/change/',
            'color': '#22c55e',  # green
        })
    
    # 4. WTN Pending Admin Approval - purple events
    pending_wtn_parcels = IncomingParcel.objects.filter(
        wtn_signed_date__isnull=False,
        wtn_admin_approved=False,
        wtn_signed_date__date__gte=month_start,
        wtn_signed_date__date__lt=month_end
    ).select_related('user').order_by('wtn_signed_date')
    
    for parcel in pending_wtn_parcels:
        customer_name = "Unknown"
        if parcel.user:
            try:
                customer = Customer.objects.get(user=parcel.user)
                customer_name = customer.name
            except Customer.DoesNotExist:
                customer_name = parcel.user.username
        
        events.append({
            'date': parcel.wtn_signed_date.date(),
            'type': 'wtn_approval',
            'title': f'📋 WTN Needs Countersign: {customer_name}',
            'description': f'{parcel} - Ref: {parcel.wtn_reference}',
            'parcel': parcel,
            'link': f'/admin/store/incomingparcel/{parcel.id}/change/',
            'color': '#a855f7',  # bright purple
        })
    
    # 5. Schedule Collection - purple events (after WTN approved)
    schedule_collection_parcels = IncomingParcel.objects.filter(
        wtn_admin_approved=True,
        collection_scheduled_date__isnull=False,
        collection_scheduled_date__gte=month_start,
        collection_scheduled_date__lt=month_end,
        status=ParcelStatus.AWAITING  # Not yet collected
    ).select_related('user').order_by('collection_scheduled_date')
    
    for parcel in schedule_collection_parcels:
        customer_name = "Unknown"
        business_name = "Unknown Business"
        if parcel.user:
            try:
                customer = Customer.objects.get(user=parcel.user)
                customer_name = customer.name
                business_name = customer.name
            except Customer.DoesNotExist:
                customer_name = parcel.user.username
                business_name = customer_name
        
        events.append({
            'date': parcel.collection_scheduled_date,
            'type': 'schedule_collection',
            'title': f'📦 Schedule Collection: {business_name}',
            'description': f'{parcel} - Box ready for DPD pickup',
            'parcel': parcel,
            'link': f'/admin/store/incomingparcel/{parcel.id}/change/',
            'color': '#a855f7',  # bright purple
        })
    
    return sorted(events, key=lambda x: x['date'])
