"""
URL configuration for website project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from store import views as store_views
from store.admin import admin_site

urlpatterns = [
    path('admin/', admin_site.urls),
    path('', store_views.home, name='home'),
    path('home/', store_views.home, name='home'),
    path('store/', include(('store.urls', 'store'), namespace='store')),
    path('about/', store_views.about, name='about'),
    path('roadmap/', store_views.roadmap, name='roadmap'),
    path('send_waste/', store_views.send_waste, name='send_waste'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
