from django.urls import path
from . import views
from .admin_calendar import admin_calendar_view

app_name = 'store'

urlpatterns = [
    path('', views.store, name='store'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart, name='cart'),
    path('update_item/', views.update_item, name='update_item'),
    path('checkout/', views.checkout, name="checkout"),

    path('process_order/', views.processOrder, name="process_order"),
    path('home/', views.home, name='home'),
    path('login/', views.login, name="login"),
    path('register/', views.register, name="register"),
    path('business/register/', views.business_register, name="business_register"),
    path('logout/', views.logout, name="logout"),
    path('profile/', views.profile, name="profile"),
    path('points-history/', views.points_history, name='points_history'),
    path('orders/', views.orders, name='orders'),
    path('orders/parcels/<int:pk>/', views.inbound_parcel_detail, name='inbound_parcel_detail'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('shipping_waste_form/', views.shipping_waste_form, name='shipping_waste_form'),
    path('shipping_waste_success/', views.shipping_waste_success, name='shipping_waste_success'),
    path('waste-transfer-notice/<int:parcel_id>/', views.waste_transfer_notice, name='waste_transfer_notice'),
    path('apply_points/', views.apply_points, name='apply_points'),
    path('blog/', views.blog, name='blog'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('business/', views.business, name='business'),
    path('business/dashboard/', views.business_dashboard, name='business_dashboard'),
    path('business/dashboard/export/', views.business_dashboard_export, name='business_dashboard_export'),
    path('business/invoices/', views.business_invoices, name='business_invoices'),
    path('business/settings/', views.business_settings, name='business_settings'),
    path('business/service-management/', views.business_service_management, name='business_service_management'),
    path('business/subscription-setup/', views.subscription_setup, name='subscription_setup'),
    path('newsletter/signup/', views.newsletter_signup, name='newsletter_signup'),
    path('contact/', views.contact, name='contact'),
    path('product/<slug:slug>/review/', views.submit_review, name='submit_review'),
    
    # Admin Calendar
    path('admin/calendar/', admin_calendar_view, name='admin_calendar'),
]