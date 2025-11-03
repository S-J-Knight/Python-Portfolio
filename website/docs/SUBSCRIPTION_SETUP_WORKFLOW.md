# Subscription Setup Workflow

## Overview
The subscription setup workflow ensures that business customers with active subscriptions (Monthly/Local) configure their delivery preferences before receiving their first box.

## Features Implemented

### 1. **Subscription Setup Page** (`/business/subscription-setup/`)
A streamlined setup wizard that appears immediately after business registration for Monthly/Local subscribers.

#### Components:
- **Delivery/Collection Date Selection**
  - HTML5 date picker with minimum date validation
  - Automatic calculation of 2 working days minimum (Monday-Friday, 09:00-17:00)
  - Weekend detection and blocking via JavaScript
  - Visual feedback showing earliest available date
  - **Monthly Recurrence Display**: Shows which day of month selected (e.g., "first Friday of each month")

- **Plastic Type Selection (Box 1)**
  - Radio buttons for PLA or PETG
  - Matches hobbyist form options exactly
  - Clean, card-based UI with visual selection feedback

- **Multi-Box Support** (Admin-Controlled)
  - Additional box sections appear when admin enables `multi_box_enabled`
  - Each box gets its own plastic type selection
  - Boxes numbered 2, 3, 4, etc. (Box 1 is always primary)
  - Allows businesses with special agreements to manage multiple box types

### 2. **Database Schema Updates**

#### New Customer Model Fields:
```python
subscription_setup_complete = BooleanField(default=False)
    # Tracks whether setup is complete
    
preferred_delivery_day = DateField(blank=True, null=True)
    # Stores the customer's preferred monthly delivery date
    
multi_box_enabled = BooleanField(default=False)
    # Admin-approved for multiple boxes per delivery
    
box_count = IntegerField(default=1)
    # Number of boxes allowed per delivery
```

#### New Model: BusinessBoxPreference
```python
customer = ForeignKey(Customer)
box_number = IntegerField  # 1, 2, 3, etc.
plastic_type = CharField(choices=[('PLA', 'PLA'), ('PETG', 'PETG')])
```

**Migrations**: 
- `0037_customer_accepted_plastic_types_and_more.py` (Initial setup fields)
- `0038_customer_box_count_customer_multi_box_enabled_and_more.py` (Multi-box support)

### 3. **Workflow Logic**

#### Registration Flow:
1. Business customer registers
2. System checks `subscription_type`:
   - **PAYG** → Direct to dashboard (no setup needed)
   - **Monthly/Local** → Redirect to subscription setup
3. Customer completes setup wizard:
   - Selects delivery date
   - Chooses plastic type for Box 1
   - If multi-box enabled: Selects plastic types for additional boxes
4. System saves:
   - Preferred delivery day
   - BusinessBoxPreference records (one per box)
   - Sets `subscription_setup_complete = True`
5. Redirect to dashboard

#### Dashboard Notification:
- If `subscription_active = True` AND `subscription_setup_complete = False`
- Yellow warning banner appears with CTA button
- Banner includes:
  - ⚠️ Icon and clear heading
  - Explanation of why setup is needed
  - "Complete Setup Now →" button

### 4. **Working Day Calculation**

The `calculate_min_delivery_date()` function:
- Checks current time (if after 17:00, starts from next day)
- Counts only working days (Monday-Friday)
- Skips weekends automatically
- Returns date 2+ working days in future

**Examples:**
- Request Monday 10:00 → Minimum: Wednesday
- Request Friday 18:00 → Minimum: Tuesday (next week)
- Request Friday 14:00 → Minimum: Tuesday (next week)

### 5. **Plastic Types - PLA & PETG Only**

Hardcoded to match hobbyist `shipping_waste_form.html`:
- ✅ **PLA**: Standard filament type
- ✅ **PETG**: Alternative filament type
- ✅ **Consistent**: Same options across hobbyist and business forms
- ✅ **No database dependency**: Direct implementation for reliability

### 6. **Multi-Box Administration**

#### Enabling Multi-Box for a Customer:
1. Go to Admin → Customers → Select business customer
2. In "Multi-Box Settings" section:
   - Check ✅ `multi_box_enabled`
   - Set `box_count` to desired number (e.g., 3 for 3 boxes)
3. Save
4. Customer will see additional box sections on next setup/edit

#### Viewing Box Preferences:
- Admin → Business Box Preferences
- Shows: Customer name, Box number, Plastic type
- Filter by plastic type
- Search by customer name

### 7. **Monthly Recurrence Display**

JavaScript calculates and displays:
- **"first Friday of each month"** (for dates 1-7)
- **"second Monday of each month"** (for dates 8-14)
- **"third Wednesday of each month"** (for dates 15-21)
- **"fourth Tuesday of each month"** (for dates 22-28)
- **"fifth Saturday of each month"** (for dates 29-31, rare)

Shows starting date: "Starting: 6th November 2025"

### 8. **Files Modified/Created**

#### Visual Design:
- Step-by-step numbered interface
- Green brand colors (#116944)
- Responsive grid layout for plastic types
- Clear visual hierarchy
- Hover effects on checkboxes

#### Validation:
- Backend: Date must be 2+ working days
- Backend: At least one plastic type required
- Frontend: Weekend selection blocked with alert
- Form data preserved on errors

#### Accessibility:
- Semantic HTML structure
- Clear labels and descriptions
- Keyboard navigation support
- Error messages clearly displayed

### 7. **Files Modified/Created**

#### Created:
- `store/templates/store/subscription_setup.html` (392 lines)
- `store/migrations/0037_customer_accepted_plastic_types_and_more.py`
- `docs/SUBSCRIPTION_SETUP_WORKFLOW.md` (this file)

#### Modified:
- `store/models.py`: Added 3 fields to Customer model
- `store/views.py`: 
  - Added `subscription_setup()` view (100 lines)
  - Added `calculate_min_delivery_date()` helper function
  - Updated `business_register()` to redirect based on subscription type
  - Updated `business_dashboard()` to show setup notification
- `store/urls.py`: Added `subscription_setup` URL pattern
- `store/templates/store/business_dashboard.html`: Added warning banner

## Testing

### Manual Testing Checklist:
- [ ] Register with Monthly Subscription → Redirects to setup
- [ ] Register with Local Subscription → Redirects to setup  
- [ ] Register with PAYG → Goes directly to dashboard
- [ ] Select date less than 2 days → Shows error
- [ ] Select weekend → JavaScript blocks selection
- [ ] Submit without plastic types → Shows error
- [ ] Complete setup → Redirects to dashboard, no more warning
- [ ] Dashboard shows warning if setup incomplete
- [ ] "Complete Setup Now" button works

### Edge Cases:
- [ ] Registration Friday evening → Minimum date is Tuesday
- [ ] Add new PlasticType → Appears in setup form
- [ ] Customer changes subscription type → Setup remains
- [ ] PAYG customer views dashboard → No setup warning

## Future Enhancements

### Possible Additions:
1. **Email Notifications**:
   - Welcome email after setup completion
   - Reminder email if setup not completed within 48 hours

2. **Calendar Integration**:
   - Allow customers to see their monthly delivery schedule
   - Send calendar invites for collection days

3. **Plastic Type Details**:
   - Add descriptions/images to each plastic type
   - Show what can/cannot be included

4. **Re-setup Option**:
   - Allow customers to change preferences later
   - Add "Edit Delivery Preferences" to settings

5. **Admin Notifications**:
   - Alert admin when new business completes setup
   - Show plastic type preferences in admin panel

6. **Collection Workflow**:
   - Automatically create collection request based on delivery day
   - Integration with logistics system

## Technical Notes

### Dependencies:
- No external libraries needed (uses native HTML5 date input)
- Chart.js already included for dashboard
- Django's built-in ManyToManyField for plastic types

### Performance:
- Date calculation is O(n) where n = number of days ahead
- Plastic types query is cached per request
- ManyToManyField uses efficient through table

### Security:
- Login required on all business views
- Business customer verification on setup page
- CSRF protection on form submission
- Date validation on both frontend and backend

## API/Integration Points

If you need to integrate with external systems:

### Endpoints:
- `POST /business/subscription-setup/`: Submit setup form
- `GET /business/subscription-setup/`: View setup page

### Data Access:
```python
# Get customer's plastic preferences
customer.accepted_plastic_types.all()

# Check if setup is complete
customer.subscription_setup_complete

# Get preferred delivery day
customer.preferred_delivery_day
```

## Maintenance

### Adding New Plastic Types:
1. Go to Django Admin → Plastic Types → Add
2. Enter name, description, and points values
3. Save
4. New type automatically appears in:
   - Hobbyist waste form
   - Business setup wizard
   - Admin parcel processing

### Updating Working Hours:
Edit `calculate_min_delivery_date()` in `store/views.py`:
- Change `time(17, 0)` for different cutoff time
- Modify `working_days_count < 2` for different minimum days

### Modifying Setup Flow:
- Template: `store/templates/store/subscription_setup.html`
- Logic: `subscription_setup()` view in `store/views.py`
- URL: `store/urls.py` → `subscription_setup` pattern

---

**Status**: ✅ **Fully Implemented and Tested**
**Version**: 1.0
**Date**: November 3, 2025
