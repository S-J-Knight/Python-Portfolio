from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.store, name='store'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart, name='cart'),
    path('update_item/', views.update_item, name='update_item'),
    path('checkout/', views.checkout, name="checkout"),

    path('process_order/', views.processOrder, name="process_order"),
    path('home/', views.home, name='home')
]