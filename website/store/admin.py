from django.contrib import admin
from django.template.response import TemplateResponse
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
)

@admin.register(PlasticType)
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

@admin.register(IncomingParcel)
class IncomingParcelAdmin(admin.ModelAdmin):
    change_form_template = 'admin/store/incomingparcel/change_form.html'
    list_display = ('__str__', 'user', 'membership_tier', 'status', 'points_calculated', 'date_submitted')
    list_filter = ('status',)
    search_fields = ('id', 'user__username', 'user__email')
    readonly_fields = ('date_submitted', 'membership_tier')
    fields = (
        'user', 
        'membership_tier',
        'status',
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
    
    def membership_tier(self, obj):
        """Show if user is premium or basic"""
        if obj and obj.user:
            customer = Customer.objects.filter(user=obj.user).first()
            if customer and customer.is_premium:
                return "⭐ Premium (20% bonus)"
            return "Basic"
        return "—"
    membership_tier.short_description = "Membership"
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add plastic type rates to context for JavaScript"""
        extra_context = extra_context or {}
        
        # Get the parcel
        obj = self.get_object(request, object_id)
        
        # Get plastic type rates
        plastic_types = PlasticType.objects.all()
        rates = {}
        for pt in plastic_types:
            rates[str(pt.pk)] = {
                'basic': float(pt.points_per_kg_basic),
                'premium': float(pt.points_per_kg_premium)
            }
        
        # Check if user is premium
        is_premium = False
        if obj and obj.user:
            customer = Customer.objects.filter(user=obj.user).first()
            is_premium = customer.is_premium if customer else False
        
        extra_context['plastic_type_rates'] = json.dumps(rates)
        extra_context['is_premium'] = is_premium
        
        return super().change_view(request, object_id, form_url, extra_context=extra_context)
    
    def save_model(self, request, obj, form, change):
        # Don't override if admin manually set points
        # Only auto-calculate if points field is completely empty (None)
        super().save_model(request, obj, form, change)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

class ShippingAddressInline(admin.StackedInline):
    model = ShippingAddress
    extra = 0
    max_num = 1
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline, ShippingAddressInline]
    list_display = ['id', 'customer', 'status', 'tracking_number', 'transaction_id', 'get_shipping_address']
    def get_shipping_address(self, obj):
        address = ShippingAddress.objects.filter(order=obj).first()
        if address:
            return f"{address.address}, {address.city}, {address.county}, {address.postcode}"
        return "-"
    get_shipping_address.short_description = 'Shipping Address'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_active', 'slug')
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ('name', 'description')

@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'transaction_type', 'points', 'description', 'date_created')
    list_filter = ('transaction_type', 'date_created')
    search_fields = ('customer__name', 'customer__email', 'description')
    readonly_fields = ('date_created',)

# Register remaining models once
admin.site.register(Customer)
admin.site.register(OrderItem)
admin.site.register(ShippingAddress)