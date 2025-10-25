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
    path('points-history/', views.points_history, name='points_history'),
    path('orders/', views.orders, name='orders'),
    path('orders/parcels/<int:pk>/', views.inbound_parcel_detail, name='inbound_parcel_detail'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('shipping_waste_form/', views.shipping_waste_form, name='shipping_waste_form'),
    path('shipping_waste_success/', views.shipping_waste_success, name='shipping_waste_success'),
    path('apply_points/', views.apply_points, name='apply_points'),
    path('blog/', views.blog, name='blog'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('business/', views.business, name='business'),
    path('newsletter/signup/', views.newsletter_signup, name='newsletter_signup'),
    path('contact/', views.contact, name='contact'),
]