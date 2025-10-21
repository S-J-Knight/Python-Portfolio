from django.contrib import admin
from .models import (
    Customer,
    Product,
    Order,
    OrderItem,
    ShippingAddress,
    IncomingParcel,
    ParcelMaterial,
)

class ParcelMaterialInline(admin.TabularInline):
    model = ParcelMaterial
    extra = 0
    can_delete = False
    fields = ('material', 'weight_kg')
    readonly_fields = ('material',)
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(IncomingParcel)
class IncomingParcelAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'status', 'date_submitted')
    list_filter = ('status',)
    search_fields = ('id', 'user__username', 'user__email')
    readonly_fields = ('date_submitted',)
    fields = (
        'user', 'status',
        'address', 'city', 'county', 'postcode', 'country',
        'details',
        'admin_comment',
        'date_submitted',
    )
    inlines = [ParcelMaterialInline]

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

# Register remaining models once
admin.site.register(Customer)
admin.site.register(OrderItem)
admin.site.register(ShippingAddress)