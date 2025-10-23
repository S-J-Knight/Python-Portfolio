from django.contrib import admin
from django.urls import path, include
from store import views as store_views
from store.admin import admin_site

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', store_views.home, name='home'),                          # root -> home
    path('store/', include(('store.urls', 'store'), namespace='store')),
]