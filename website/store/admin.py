from django.contrib import admin
from .models import *
from .models import Product

admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(ShippingAddress)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
class ShippingAddressInline(admin.StackedInline):
    model = ShippingAddress
    extra = 0
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline, ShippingAddressInline]
    list_display = ['id', 'customer', 'complete', 'transaction_id', 'get_shipping_address']

    def get_shipping_address(self, obj):
        address = ShippingAddress.objects.filter(order=obj).first()
        if address:
            return f"{address.address}, {address.city}, {address.county}, {address.postcode}"
        return "-"
    get_shipping_address.short_description = 'Shipping Address'

admin.site.register(Order, OrderAdmin)

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name','price','is_active','slug')
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ('name','description')