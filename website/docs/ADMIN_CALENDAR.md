# Admin Calendar Feature

## Overview
The Admin Calendar provides a visual dashboard showing all upcoming events that need attention:
- 📦 **Subscription Collections** - Monthly scheduled deliveries for subscription customers
- 📬 **PAYG Collection Requests** - Customers requesting waste collection
- 🛒 **Orders to Fulfill** - Store orders that need processing/shipping

## How to Access
1. Log into the Django admin panel at `/admin/`
2. Click the **"View Collection & Order Calendar"** button on the admin homepage
3. Or navigate directly to `/admin/calendar/`

## Features

### Calendar Navigation
- Click **Previous** or **Next** to move between months
- Current day is highlighted in orange
- Events are color-coded by type

### Event Types

**🔵 Subscription Collections (Blue)**
- Shows customers with active subscriptions
- Based on their `preferred_delivery_day` field
- Click to view customer details in admin

**🟡 PAYG Collection Requests (Yellow)**
- Shows incoming parcels awaiting collection
- Status must be "Awaiting Parcel"
- Click to view parcel details and update status

**🟢 Orders to Fulfill (Green)**
- Shows store orders with status "Order Received" or "Processing"
- Click to view order details and mark as shipped

### How Events Are Calculated

**Subscription Collections:**
- Pulled from `Customer.preferred_delivery_day`
- Only shows active, non-cancelled subscriptions
- Recurring monthly based on the day set by customer

**PAYG Requests:**
- Pulled from `IncomingParcel` with `status='AWAITING'`
- Shows submission date
- Indicates location from shipping address

**Store Orders:**
- Pulled from `Order` with status `RECEIVED` or `PROCESSING`
- Shows order date
- Displays customer name and order number

## Setting Up Subscription Delivery Dates

For subscription customers to appear on the calendar:
1. Go to the customer's admin page
2. Set `subscription_active = True`
3. Set `preferred_delivery_day` to their chosen monthly collection day
4. Save the customer

The calendar will automatically show their collection on that day each month.

## Troubleshooting

**No events showing:**
- Check that subscription customers have `preferred_delivery_day` set
- Verify PAYG parcels have status = "Awaiting Parcel"
- Ensure orders have status = "Order Received" or "Processing"

**Events not clickable:**
- Links go directly to the admin change page for that object
- You must be logged in as staff to access

## Future Enhancements
- Email notifications for upcoming collections
- Drag-and-drop to reschedule
- Bulk status updates
- Export calendar to PDF/CSV
- Integration with shipping label generation
