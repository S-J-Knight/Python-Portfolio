from django.contrib import admin
from django.contrib.admin import helpers as admin_helpers
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta
import json
from markdownx.admin import MarkdownxModelAdmin
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
    BlogPost,
    NewsletterSubscriber,
    BusinessBoxPreference,
    ProductReview,
    SubscriptionPlan,
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

class BusinessBoxPreferenceInline(admin.TabularInline):
    model = BusinessBoxPreference
    extra = 0
    fields = ('box_number', 'plastic_type')
    ordering = ('box_number',)
    
    def get_readonly_fields(self, request, obj=None):
        # Make box_number readonly for existing preferences
        if obj and obj.pk:
            return ('box_number',)
        return ()

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
    list_display = ('__str__', 'user', 'membership_tier', 'status_badge', 'age_badge', 'wtn_status', 'admin_signed_status', 'points_calculated', 'date_submitted')
    list_filter = ('status', 'date_submitted')
    search_fields = ('id', 'user__username', 'user__email', 'wtn_reference')
    readonly_fields = ('user', 'date_submitted', 'membership_tier', 'age_display', 'wtn_signed_date', 'wtn_admin_approved_date', 'wtn_pdf_path', 'customer_signature_display')
    
    fieldsets = (
        ('Section A - Personal Information', {
            'fields': ('user', 'membership_tier', 'status', 'age_display', 'date_submitted')
        }),
        ('Section B - Waste Transfer Note (WTN)', {
            'fields': ('wtn_reference', 'wtn_signed_date', 'customer_signature_display', 'wtn_admin_approved', 'wtn_admin_signature', 'wtn_admin_approved_date', 'wtn_pdf_path')
        }),
        ('Section C - Box Information', {
            'fields': ('address', 'city', 'county', 'postcode', 'country', 'estimated_weight', 'collection_scheduled_date', 'details')
        }),
        ('Admin Section', {
            'fields': ('admin_comment', 'points_calculated'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ParcelMaterialInline]
    actions = ['mark_as_cancelled', 'mark_as_processed']
    
    def wtn_status(self, obj):
        """Show if WTN has been signed"""
        if obj.wtn_signed_date:
            return format_html(
                '<span style="background:#10b981; color:#fff; padding:4px 10px; border-radius:12px; font-weight:600; font-size:0.8rem;">✓ Signed</span>'
            )
        return format_html(
            '<span style="background:#9ca3af; color:#fff; padding:4px 10px; border-radius:12px; font-weight:600; font-size:0.8rem;">Pending</span>'
        )
    wtn_status.short_description = "WTN"
    
    def admin_signed_status(self, obj):
        """Show if Admin has approved the WTN"""
        if obj.wtn_admin_approved and obj.wtn_pdf_path:
            return format_html(
                '<span style="background:#3b82f6; color:#fff; padding:4px 10px; border-radius:12px; font-weight:600; font-size:0.8rem;">✓ Admin Signed</span>'
            )
        return format_html(
            '<span style="background:#9ca3af; color:#fff; padding:4px 10px; border-radius:12px; font-weight:600; font-size:0.8rem;">Awaiting</span>'
        )
    admin_signed_status.short_description = "Admin Approval"
    
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
    
    def customer_signature_display(self, obj):
        """Display customer's signature image"""
        if obj and obj.wtn_signature:
            return format_html(
                '<div style="border: 1px solid #ddd; padding: 10px; background: #f9f9f9; border-radius: 4px;">'
                '<strong>Customer Signature:</strong><br>'
                '<img src="{}" style="max-width: 300px; height: auto; border: 1px solid #ccc; margin-top: 8px;">'
                '</div>',
                obj.wtn_signature
            )
        return format_html('<span style="color: #999;">{}</span>', 'No signature captured yet')
    customer_signature_display.short_description = "Customer Signature"
    
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
    
    def save_model(self, request, obj, form, change):
        """Handle WTN approval and PDF generation when admin signs"""
        from store.wtn_pdf import generate_wtn_pdf
        from django.utils import timezone
        import logging
        import os
        
        logger = logging.getLogger(__name__)
        
        # Check if admin just approved the WTN
        # Also verify PDF file actually exists if path is set
        pdf_exists = False
        if obj.wtn_pdf_path:
            from django.conf import settings
            pdf_full_path = os.path.join(settings.MEDIA_ROOT, obj.wtn_pdf_path)
            pdf_exists = os.path.exists(pdf_full_path)
            logger.info(f"Checking PDF: path={obj.wtn_pdf_path}, full_path={pdf_full_path}, exists={pdf_exists}")
            if not pdf_exists:
                logger.warning(f"PDF path set but file doesn't exist: {pdf_full_path}")
        
        should_generate_pdf = obj.wtn_admin_approved and not pdf_exists
        
        # Debug output to console
        print(f"=== PDF GENERATION DEBUG ===")
        print(f"Parcel ID: {obj.pk}")
        print(f"wtn_admin_approved: {obj.wtn_admin_approved}")
        print(f"wtn_pdf_path: {obj.wtn_pdf_path}")
        print(f"pdf_exists: {pdf_exists}")
        print(f"should_generate_pdf: {should_generate_pdf}")
        print(f"===========================")
        
        logger.info(f"Save triggered for IncomingParcel {obj.pk}: wtn_admin_approved={obj.wtn_admin_approved}, has_pdf_path={bool(obj.wtn_pdf_path)}, pdf_exists={pdf_exists}, should_generate={should_generate_pdf}")
        
        if should_generate_pdf:
            # Set approval date
            if not obj.wtn_admin_approved_date:
                obj.wtn_admin_approved_date = timezone.now()
            
            # Prefill collection date from customer's preferred delivery day if not set
            if not obj.collection_scheduled_date and obj.user:
                try:
                    from store.models import Customer
                    customer = Customer.objects.get(user=obj.user)
                    if customer.preferred_delivery_day:
                        obj.collection_scheduled_date = customer.preferred_delivery_day
                except Customer.DoesNotExist:
                    pass
            
            # Save first to ensure we have an ID
            super().save_model(request, obj, form, change)
            
            # Generate PDF
            try:
                print(f">>> ATTEMPTING PDF GENERATION for parcel {obj.pk}")
                logger.info(f"Starting PDF generation for IncomingParcel {obj.pk}")
                
                # Generate PDF
                print(f">>> Calling generate_wtn_pdf()...")
                pdf_path = generate_wtn_pdf(obj)
                print(f">>> PDF generated successfully: {pdf_path}")
                logger.info(f"PDF generated successfully: {pdf_path}")
                
                # Store relative path (MEDIA_URL will be prepended when accessed)
                obj.wtn_pdf_path = pdf_path
                print(f">>> PDF path stored in database")
                
                # Clear signatures from database for security (they're now in the PDF)
                if obj.wtn_signature:
                    print(f">>> Clearing customer signature from database")
                    obj.wtn_signature = ''
                    logger.info(f"Customer signature cleared from database for parcel {obj.pk}")
                
                if obj.wtn_admin_signature:
                    print(f">>> Clearing admin signature from database")
                    obj.wtn_admin_signature = ''
                    logger.info(f"Admin signature cleared from database for parcel {obj.pk}")
                
                # Automatically mark as AWAITING (waiting for parcel arrival)
                if obj.status != 'awaiting':
                    obj.status = 'awaiting'
                    logger.info(f"IncomingParcel {obj.pk} automatically marked as awaiting after admin approval")
                
                # Calculate and save points
                total_points = obj.calculate_points()
                if total_points > 0:
                    obj.points_calculated = total_points
                    logger.info(f"IncomingParcel {obj.pk} calculated {total_points} points")
                
                # Save again with updated status
                super().save_model(request, obj, form, change)
                
                print(f">>> PDF generation complete!")
                self.message_user(request, f'✓ WTN approved and PDF generated successfully! Status set to Processed.', level='SUCCESS')
            except Exception as e:
                print(f">>> ERROR in PDF generation: {str(e)}")
                import traceback
                traceback.print_exc()
                logger.error(f"Error generating PDF for IncomingParcel {obj.pk}: {str(e)}")
                self.message_user(request, f'Error generating PDF: {str(e)}', level='ERROR')
        else:
            # Normal save - still calculate points if there are materials
            super().save_model(request, obj, form, change)
            
            # Recalculate points after save (when materials might have changed)
            if obj.pk and obj.materials.exists():
                total_points = obj.calculate_points()
                if obj.points_calculated != total_points:
                    obj.points_calculated = total_points
                    obj.save(update_fields=['points_calculated'])
                    self.message_user(request, f'Points recalculated: {total_points}', level='INFO')
    
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
    list_display = ['order_number_display', 'customer', 'status_badge', 'age_badge', 'tracking_number', 'get_total_display', 'get_shipping_address', 'points_used', 'points_discount']
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
    
    def order_number_display(self, obj):
        """Display order number with OP- prefix"""
        return obj.order_number
    order_number_display.short_description = 'Order #'
    order_number_display.admin_order_field = 'id'
    
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
    list_display = ('name', 'price', 'sale_price', 'is_on_sale', 'is_active', 'stock_quantity', 'slug')
    list_editable = ('is_on_sale', 'is_active')
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ('name', 'description')
    list_filter = ('is_on_sale', 'is_active', 'product_type')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'image', 'is_active')
        }),
        ('Pricing', {
            'fields': ('price', 'is_on_sale', 'sale_price', 'sale_comment'),
            'description': 'Set regular price and optional sale pricing'
        }),
        ('Product Details', {
            'fields': ('product_type', 'colour', 'digital')
        }),
        ('Stock Management', {
            'fields': ('stock_quantity', 'low_stock_threshold')
        }),
    )

@admin.register(PointTransaction, site=admin_site)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'transaction_type', 'points', 'description', 'date_created')
    list_filter = ('transaction_type', 'date_created')
    search_fields = ('customer__name', 'customer__email', 'description')
    readonly_fields = ('date_created',)

@admin.register(BlogPost, site=admin_site)
class BlogPostAdmin(MarkdownxModelAdmin):
    list_display = ['title', 'author', 'published', 'created_at']
    list_filter = ['published', 'created_at']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['published']
    
    def save_model(self, request, obj, form, change):
        """Auto-set author to current user if not set"""
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)

@admin.register(NewsletterSubscriber, site=admin_site)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'subscribed_at', 'is_active')
    list_filter = ('is_active', 'subscribed_at')
    search_fields = ('email', 'name')
    ordering = ('-subscribed_at',)
    readonly_fields = ('subscribed_at',)

@admin.register(ProductReview, site=admin_site)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'customer', 'rating', 'display_name', 'is_verified_purchase', 'is_approved', 'created_at')
    list_filter = ('rating', 'is_verified_purchase', 'is_approved', 'created_at')
    search_fields = ('product__name', 'customer__name', 'customer__email', 'review_text', 'display_name')
    list_editable = ('is_approved',)
    readonly_fields = ('customer', 'product', 'is_verified_purchase', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Review Information', {
            'fields': ('product', 'customer', 'rating', 'review_text', 'display_name')
        }),
        ('Verification & Status', {
            'fields': ('is_verified_purchase', 'is_approved', 'created_at', 'updated_at')
        }),
    )

@admin.register(Customer, site=admin_site)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'user', 'total_points', 'is_premium', 'is_business', 'multi_box_enabled', 'box_count', 'newsletter_subscribed')
    list_filter = ('is_premium', 'is_business', 'multi_box_enabled', 'subscription_active', 'newsletter_subscribed')
    search_fields = ('name', 'email', 'user__username', 'user__email')
    readonly_fields = ('total_points', 'subscription_setup_complete')
    inlines = [BusinessBoxPreferenceInline]
    actions = ['add_box_to_customer', 'add_points_to_customer']
    
    def add_points_to_customer(self, request, queryset):
        """Add points to selected customers via admin action"""
        from django import forms
        from django.contrib import messages
        
        # If we're processing the form submission
        if 'apply' in request.POST:
            points_form = request.POST.get('points_amount')
            reason = request.POST.get('reason', 'Admin Addition')
            
            # Get customer IDs from hidden inputs
            customer_ids = request.POST.getlist(admin_helpers.ACTION_CHECKBOX_NAME)
            queryset = self.model.objects.filter(pk__in=customer_ids)
            
            try:
                points = int(points_form)
                if points <= 0:
                    self.message_user(request, 'Points must be a positive number.', level=messages.ERROR)
                    return
                
                updated = 0
                for customer in queryset:
                    # Create point transaction
                    PointTransaction.objects.create(
                        customer=customer,
                        points=points,
                        transaction_type='Admin Addition',
                        description=reason or 'Admin Addition'
                    )
                    
                    # Update customer total points
                    customer.total_points += points
                    customer.save()
                    updated += 1
                
                self.message_user(request, f'Successfully added {points} points to {updated} customer(s).', level=messages.SUCCESS)
                return
            except (ValueError, TypeError) as e:
                self.message_user(request, f'Invalid points amount: {str(e)}', level=messages.ERROR)
                return
        
        # Show the form
        from django.shortcuts import render
        
        context = {
            'title': 'Add Points to Customers',
            'queryset': queryset,
            'opts': self.model._meta,
            'action_checkbox_name': admin_helpers.ACTION_CHECKBOX_NAME,
        }
        
        return render(request, 'admin/add_points_form.html', context)
    
    add_points_to_customer.short_description = 'Add points to selected customers'
    
    def get_fieldsets(self, request, obj=None):
        """Dynamically adjust fieldsets based on customer type"""
        fieldsets = [
            ('Basic Information', {
                'fields': ('user', 'name', 'email')
            }),
        ]
        
        # Business customers get business-specific fields
        if obj and obj.is_business:
            fieldsets.append(
                ('Business Information', {
                    'fields': ('is_business', 'subscription_type', 'subscription_active', 'subscription_cancelled', 'subscription_end_date', 'subscription_setup_complete', 'preferred_delivery_day')
                })
            )
            fieldsets.append(
                ('Multi-Box Settings', {
                    'fields': ('multi_box_enabled', 'box_count', 'custom_subscription_price'),
                    'description': 'Enable multiple boxes for this business customer. Set custom price for special pricing. Box preferences can be added below.'
                })
            )
            fieldsets.append(
                ('Points', {
                    'fields': ('total_points',),
                    'description': 'Business customers earn points but cannot be premium members.'
                })
            )
        else:
            # Regular customers get standard fields
            fieldsets.append(
                ('Account Type', {
                    'fields': ('is_business',)
                })
            )
            fieldsets.append(
                ('Points & Premium', {
                    'fields': ('total_points', 'is_premium')
                })
            )
        
        # Newsletter for all
        fieldsets.append(
            ('Newsletter', {
                'fields': ('newsletter_subscribed', 'mailerlite_subscriber_id')
            })
        )
        
        return fieldsets
    
    def add_box_to_customer(self, request, queryset):
        """Add a new box to selected business customers"""
        updated = 0
        skipped = 0
        
        # Get first plastic type as default (or None if no types exist yet)
        first_plastic = PlasticType.objects.first()
        
        for customer in queryset:
            if customer.is_business and customer.subscription_active:
                # Increment box count
                customer.box_count += 1
                customer.multi_box_enabled = True
                customer.save()
                
                # Don't create a BusinessBoxPreference yet - let customer choose
                # This will trigger the needs_box_update flow in subscription_setup
                updated += 1
            else:
                skipped += 1
        
        if updated > 0:
            self.message_user(request, f'Successfully added a box to {updated} customer(s). They will be prompted to select plastic types on their next login.')
        if skipped > 0:
            self.message_user(request, f'Skipped {skipped} non-business or inactive customers.', level='WARNING')
    
    add_box_to_customer.short_description = 'Add a new box to selected customers'
    
    def save_model(self, request, obj, form, change):
        """Sync Customer data with User model to keep them in sync"""
        if obj.user:
            # Parse name into first_name and last_name
            name_parts = obj.name.split(' ', 1) if obj.name else ['', '']
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            # Update User model fields
            obj.user.first_name = first_name
            obj.user.last_name = last_name
            obj.user.email = obj.email
            obj.user.save()
        
        # If subscription is being cancelled or ended, reset setup requirements
        if change and obj.is_business:
            # Check if subscription has expired (end date is in the past)
            from datetime import date
            today = date.today()
            
            if (obj.subscription_cancelled and 
                obj.subscription_end_date and 
                obj.subscription_end_date < today):
                # Subscription has expired - reset setup flag so they go through setup again
                obj.subscription_setup_complete = False
                obj.subscription_active = False
                obj.subscription_type = 'PAYG'
        
        super().save_model(request, obj, form, change)


class BusinessCustomer(Customer):
    """Proxy model to show only business customers in admin"""
    class Meta:
        proxy = True
        verbose_name = 'Business Customer'
        verbose_name_plural = 'Business Customers'


@admin.register(BusinessCustomer, site=admin_site)
class BusinessCustomerAdmin(admin.ModelAdmin):
    """Dedicated admin view for business customers only"""
    list_display = (
        'name', 
        'email', 
        'subscription_type_badge',
        'subscription_status_badge',
        'box_count',
        'total_points',
        'newsletter_subscribed',
        'preferred_delivery_day'
    )
    list_filter = (
        'subscription_type',
        'subscription_active', 
        'subscription_cancelled',
        'multi_box_enabled',
        'newsletter_subscribed'
    )
    search_fields = ('name', 'email', 'user__username', 'user__email')
    readonly_fields = ('total_points', 'subscription_setup_complete', 'mailerlite_subscriber_id')
    inlines = [BusinessBoxPreferenceInline]
    
    fieldsets = [
        ('Company Information', {
            'fields': ('user', 'name', 'email')
        }),
        ('Subscription Details', {
            'fields': (
                'subscription_type', 
                'subscription_active', 
                'subscription_cancelled', 
                'subscription_end_date',
                'subscription_setup_complete',
                'preferred_delivery_day'
            )
        }),
        ('Multi-Box Configuration', {
            'fields': ('multi_box_enabled', 'box_count', 'custom_subscription_price'),
            'description': 'Configure multiple boxes and custom pricing for this business.'
        }),
        ('Points & Newsletter', {
            'fields': ('total_points', 'newsletter_subscribed', 'mailerlite_subscriber_id')
        }),
    ]
    
    def get_queryset(self, request):
        """Filter to show only business customers"""
        qs = super().get_queryset(request)
        return qs.filter(is_business=True)
    
    def subscription_type_badge(self, obj):
        """Colored badge for subscription type"""
        colors = {
            'PAYG': '#6b7280',
            'Monthly Subscription': '#3b82f6',
            'Local Subscription': '#10b981',
            'Custom Subscription': '#8b5cf6',
        }
        color = colors.get(obj.subscription_type, '#6b7280')
        display_text = obj.subscription_type if obj.subscription_type else 'PAYG'
        
        return format_html(
            '<span style="background:{}; color:#fff; padding:4px 10px; border-radius:12px; font-weight:600; font-size:0.75rem;">{}</span>',
            color, display_text
        )
    subscription_type_badge.short_description = 'Subscription Type'
    
    def subscription_status_badge(self, obj):
        """Show subscription status with color coding"""
        if obj.subscription_active:
            return format_html(
                '<span style="background:#10b981; color:#fff; padding:4px 10px; border-radius:12px; font-weight:600; font-size:0.75rem;">✓ Active</span>'
            )
        elif obj.subscription_cancelled:
            end_date = obj.subscription_end_date.strftime('%d %b') if obj.subscription_end_date else '?'
            return format_html(
                '<span style="background:#ef4444; color:#fff; padding:4px 10px; border-radius:12px; font-weight:600; font-size:0.75rem;">⚠ Cancelled (Until {})</span>',
                end_date
            )
        else:
            return format_html(
                '<span style="background:#6b7280; color:#fff; padding:4px 10px; border-radius:12px; font-weight:600; font-size:0.75rem;">○ Inactive</span>'
            )
    subscription_status_badge.short_description = 'Status'
    
    def has_add_permission(self, request):
        """Prevent adding through this view - use main Customer admin"""
        return False


@admin.register(BusinessBoxPreference, site=admin_site)
class BusinessBoxPreferenceAdmin(admin.ModelAdmin):
    list_display = ('customer', 'box_number', 'plastic_type')
    list_filter = ('plastic_type',)
    search_fields = ('customer__name', 'customer__user__username')
    ordering = ('customer', 'box_number')


@admin.register(SubscriptionPlan, site=admin_site)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'monthly_price', 'setup_fee', 'minimum_months', 'price_locked', 'is_active', 'display_order')
    list_filter = ('is_active', 'price_locked')
    search_fields = ('name', 'description')
    list_editable = ('display_order', 'is_active')
    ordering = ('display_order', 'name')
    
    fieldsets = (
        ('Plan Details', {
            'fields': ('name', 'display_order', 'is_active')
        }),
        ('Pricing', {
            'fields': ('monthly_price', 'setup_fee', 'minimum_months', 'price_locked')
        }),
        ('Notes', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
    )


# Register remaining models
admin_site.register(OrderItem)
admin_site.register(ShippingAddress)