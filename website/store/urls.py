from django.urls import path
from . import views

# Application namespace for reversing with 'store:...'
app_name = 'store'

urlpatterns = [
    path('', views.store, name="store"),
    path('cart/', views.cart, name="cart"),
    path('checkout/', views.checkout, name="checkout"),

    path('update_item/', views.updateItem, name="update_item"),
    path('process_order/', views.processOrder, name="process_order"),
    path('store/', views.store, name='store'),
     path('product/<slug:slug>/', views.product_detail, name='product_detail'),
]