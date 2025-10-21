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
    path('home/', views.home, name='home'),
    path('send_waste/', views.send_waste, name='send_waste'),
    path('login/', views.login, name="login"),
    path('register/', views.register, name="register"),
    path('logout/', views.logout, name="logout"),
    path('profile/', views.profile, name="profile"),
    path('orders/', views.orders, name='orders'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('shipping_waste_form/', views.shipping_waste_form, name='shipping_waste_form'),
]