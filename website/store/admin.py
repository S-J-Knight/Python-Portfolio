from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta
import json
from .models import (
    Customer,
    Product,
    Order,
    OrderItem,
    ShippingAddress,
    IncomingParcel,
    ParcelMaterial,
    PointTransaction,
    PlasticType,
    OrderStatus,
)
from .emails import send_order_confirmation, send_order_processing, send_order_shipped

class CustomAdminSite(admin.AdminSite):
    site_header = "Store Admin"
    site_title = "Store Admin Portal"
    index_title = "Dashboard"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='admin_dashboard'),
        ]
        return custom_urls + urls
    
    def dashboard_view(self, request):
        """Custom dashboard showing pending tasks"""
        # Get pending orders (Order Received status - ready to process)
        pending_orders = Order.objects.filter(
            status=OrderStatus.RECEIVED
        ).select_related('customer').prefetch_related('orderitem_set__product').order_by('-date_ordered')
        
        # Get orders in processing (being fulfilled)
        processing_orders = Order.objects.filter(
            status=OrderStatus.PROCESSING
        ).select_related('customer').order_by('-date_ordered')
        
        # Get pending parcels (Submitted but not processed)
        pending_parcels = IncomingParcel.objects.filter(
            status='Submitted'
        ).select_related('user').prefetch_related('materials').order_by('-date_submitted')
        
        # Flag stale parcels (>7 days old)
        stale_cutoff = timezone.now() - timedelta(days=7)
        for parcel in pending_parcels:
            parcel.is_stale = parcel.date_submitted < stale_cutoff
        
        # Get recent activity (last 7 days)
        recent_cutoff = timezone.now() - timedelta(days=7)
        recent_orders = Order.objects.filter(
            date_ordered__gte=recent_cutoff,
            status__in=[OrderStatus.SHIPPED, OrderStatus.DELIVERED]
        ).order_by('-date_ordered')[:10]
        
        recent_parcels = IncomingParcel.objects.filter(
            date_submitted__gte=recent_cutoff,
            status='Processed'
        ).order_by('-date_submitted')[:10]
        
        context = {
            **self.each_context(request),
            'title': 'Admin Dashboard',
            'pending_orders': pending_orders,
            'pending_orders_count': pending_orders.count(),
            'processing_orders': processing_orders,
            'processing_orders_count': processing_orders.count(),
            'pending_parcels': pending_parcels,
            'pending_parcels_count': pending_parcels.count(),
            'recent_orders': recent_orders,
            'recent_parcels': recent_parcels,
        }
        
        return TemplateResponse(request, 'admin/dashboard.html', context)
    
    def index(self, request, extra_context=None):
        """Override default index to redirect to custom dashboard"""
        return self.dashboard_view(request)

# Create custom admin site instance
admin_site = CustomAdminSite(name='admin')

@admin.register(PlasticType, site=admin_site)
class PlasticTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'points_per_kg_basic', 'points_per_kg_premium', 'description')
    fields = ('name', 'description', 'points_per_kg_basic', 'points_per_kg_premium')

class ParcelMaterialInline(admin.TabularInline):
    model = ParcelMaterial
    extra = 0
    fields = ('plastic_type', 'weight_kg', 'calculated_points')
    readonly_fields = ('calculated_points',)
    
    def calculated_points(self, obj):
        """Show calculated points for this material"""
        if obj and obj.pk:
            return f"{obj.calculate_points()} pts"
        return "—"
    calculated_points.short_description = "Points"

@admin.register(IncomingParcel, site=admin_site)
class IncomingParcelAdmin(admin.ModelAdmin):
    change_form_template = 'admin/store/incomingparcel/change_form.html'
    list_display = ('__str__', 'user', 'membership_tier', 'status_badge', 'age_badge', 'points_calculated', 'date_submitted')
    list_filter = ('status', 'date_submitted')
    search_fields = ('id', 'user__username', 'user__email')
    readonly_fields = ('date_submitted', 'membership_tier', 'age_display')
    fields = (
        'user', 
        'membership_tier',
        'status',
        'age_display',
        'date_submitted',
        'address', 
        'city', 
        'county', 
        'postcode', 
        'country',
        'details',
        'admin_comment',
        'points_calculated',
    )
    inlines = [ParcelMaterialInline]
    actions = ['mark_as_cancelled', 'mark_as_processed']
    
    def status_badge(self, obj):
        colors = {
            'Submitted': '#fbbf24',  # yellow
            'Verified': '#3b82f6',   # blue
            'Processed': '#10b981',  # green
            'Cancelled': '#ef4444',  # red
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{}; color:#fff; padding:4px 10px; border-radius:12px; font-weight:600; font-size:0.8rem;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = "Status"
    
    def age_badge(self, obj):
        """Show how old the submission is"""
        age = timezone.now() - obj.date_submitted
        days = age.days
        
        if days == 0:
            label = "Today"
            color = "#10b981"
        elif days <= 3:
            label = f"{days}d ago"
            color = "#3b82f6"
        elif days <= 7:
            label = f"{days}d ago"
            color = "#fbbf24"
        else:
            label = f"{days}d ago ⚠️"
            color = "#ef4444"
        
        return format_html(
            '<span style="background:{}; color:#fff; padding:4px 8px; border-radius:8px; font-size:0.75rem;">{}</span>',
            color, label
        )
    age_badge.short_description = "Age"
    
    def age_display(self, obj):
        """Show age in readonly field"""
        if obj:
            age = timezone.now() - obj.date_submitted
            return f"{age.days} days ago"
        return "—"
    age_display.short_description = "Submission Age"
    
    def membership_tier(self, obj):
        """Show if user is premium or basic"""
        if obj and obj.user:
            customer = Customer.objects.filter(user=obj.user).first()
            if customer and customer.is_premium:
                return "⭐ Premium (20% bonus)"
            return "Basic"
        return "—"
    membership_tier.short_description = "Membership"
    
    def mark_as_cancelled(self, request, queryset):
        """Bulk action to mark parcels as cancelled"""
        count = queryset.update(status='Cancelled')
        self.message_user(request, f'{count} parcel(s) marked as cancelled.')
    mark_as_cancelled.short_description = "Mark as Cancelled (No Show)"
    
    def mark_as_processed(self, request, queryset):
        """Bulk action to mark as processed"""
        count = 0
        for parcel in queryset:
            if parcel.status != 'Processed':
                parcel.status = 'Processed'
                parcel.save()
                count += 1
        self.message_user(request, f'{count} parcel(s) marked as processed.')
    mark_as_processed.short_description = "Mark as Processed"
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add plastic type rates to context for JavaScript"""
        extra_context = extra_context or {}
        
        obj = self.get_object(request, object_id)
        plastic_types = PlasticType.objects.all()
        rates = {}
        for pt in plastic_types:
            rates[str(pt.pk)] = {
                'basic': float(pt.points_per_kg_basic),
                'premium': float(pt.points_per_kg_premium)
            }
        
        is_premium = False
        if obj and obj.user:
            customer = Customer.objects.filter(user=obj.user).first()
            is_premium = customer.is_premium if customer else False
        
        extra_context['plastic_type_rates'] = json.dumps(rates)
        extra_context['is_premium'] = is_premium
        
        return super().change_view(request, object_id, form_url, extra_context=extra_context)
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('get_total',)
    
    def get_total(self, obj):
        if obj and obj.pk:
            return f"£{obj.get_total:.2f}"
        return "—"
    get_total.short_description = "Total"

class ShippingAddressInline(admin.StackedInline):
    model = ShippingAddress
    extra = 0
    max_num = 1
    can_delete = False

@admin.register(Order, site=admin_site)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline, ShippingAddressInline]
    list_display = ['id', 'customer', 'status_badge', 'age_badge', 'tracking_number', 'get_total_display', 'get_shipping_address', 'points_used', 'points_discount']
    list_filter = ('status', 'date_ordered')
    search_fields = ('id', 'customer__name', 'customer__email', 'tracking_number')
    readonly_fields = ('date_ordered', 'transaction_id', 'age_display', 'points_used', 'points_discount')
    actions = ['mark_as_processing', 'mark_as_shipped']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('customer', 'status', 'date_ordered', 'age_display', 'transaction_id')
        }),
        ('Shipping', {
            'fields': ('tracking_number',)
        }),
        ('Points', {
            'fields': ('points_used',),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'Potential Order': '#9ca3af',
            'Order Received': '#fbbf24',
            'Processing': '#3b82f6',
            'Shipped': '#8b5cf6',
            'Delivered': '#10b981',
            'Cancelled': '#ef4444',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{}; color:#fff; padding:4px 10px; border-radius:12px; font-weight:600; font-size:0.8rem;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = "Status"
    
    def age_badge(self, obj):
        """Show how old the order is"""
        age = timezone.now() - obj.date_ordered
        days = age.days
        
        if days == 0:
            label = "Today"
            color = "#10b981"
        elif days <= 2:
            label = f"{days}d"
            color = "#3b82f6"
        elif days <= 5:
            label = f"{days}d"
            color = "#fbbf24"
        else:
            label = f"{days}d ⚠️"
            color = "#ef4444"
        
        return format_html(
            '<span style="background:{}; color:#fff; padding:4px 8px; border-radius:8px; font-size:0.75rem;">{}</span>',
            color, label
        )
    age_badge.short_description = "Age"
    
    def age_display(self, obj):
        if obj:
            age = timezone.now() - obj.date_ordered
            return f"{age.days} days ago"
        return "—"
    age_display.short_description = "Order Age"
    
    def get_total_display(self, obj):
        total = obj.get_cart_total_after_points
        return f"£{total:.2f}"
    get_total_display.short_description = "Total"
    
    def get_shipping_address(self, obj):
        address = ShippingAddress.objects.filter(order=obj).first()
        if address:
            return f"{address.address}, {address.city}, {address.postcode}"
        return "-"
    get_shipping_address.short_description = 'Shipping Address'
    
    def save_model(self, request, obj, form, change):
        """Send email when status changes"""
        if change:  # Only for existing orders
            old_obj = Order.objects.get(pk=obj.pk)
            
            # Check if status changed
            if old_obj.status != obj.status:
                super().save_model(request, obj, form, change)
                
                # Send appropriate email based on new status
                if obj.status == OrderStatus.RECEIVED:
                    send_order_confirmation(obj)
                elif obj.status == OrderStatus.PROCESSING:
                    send_order_processing(obj)
                elif obj.status == OrderStatus.SHIPPED:
                    send_order_shipped(obj)
            else:
                super().save_model(request, obj, form, change)
        else:
            super().save_model(request, obj, form, change)
    
    def mark_as_processing(self, request, queryset):
        """Bulk action with email notifications"""
        count = 0
        for order in queryset.filter(status=OrderStatus.RECEIVED):
            order.status = OrderStatus.PROCESSING
            order.save()
            send_order_processing(order)
            count += 1
        self.message_user(request, f'{count} order(s) marked as processing and customers notified.')
    mark_as_processing.short_description = "Mark as Processing (Send Email)"
    
    def mark_as_shipped(self, request, queryset):
        """Bulk action with email notifications"""
        count = 0
        for order in queryset.filter(status=OrderStatus.PROCESSING):
            order.status = OrderStatus.SHIPPED
            order.save()
            send_order_shipped(order)
            count += 1
        self.message_user(request, f'{count} order(s) marked as shipped and customers notified.')
    mark_as_shipped.short_description = "Mark as Shipped (Send Email)"

@admin.register(Product, site=admin_site)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_active', 'slug')
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ('name', 'description')

@admin.register(PointTransaction, site=admin_site)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'transaction_type', 'points', 'description', 'date_created')
    list_filter = ('transaction_type', 'date_created')
    search_fields = ('customer__name', 'customer__email', 'description')
    readonly_fields = ('date_created',)

# Register remaining models
admin_site.register(Customer)
admin_site.register(OrderItem)
admin_site.register(ShippingAddress)