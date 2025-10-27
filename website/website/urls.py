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
from django.http import HttpResponse
from store import views as store_views
from store.admin import admin_site

# SEO file views
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /cart/",
        "Disallow: /checkout/",
        "Disallow: /process_order/",
        "Disallow: /update_item/",
        "Disallow: /apply_points/",
        "",
        "Sitemap: https://www.knightcycle.co.uk/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

def sitemap_xml(request):
    """Simple sitemap generator"""
    from store.models import BlogPost
    from django.urls import reverse
    
    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    
    # Static pages
    static_pages = [
        ('home', 1.0, 'weekly'),
        ('send_waste', 0.9, 'monthly'),
        ('about', 0.7, 'monthly'),
        ('roadmap', 0.7, 'weekly'),
    ]
    
    for name, priority, changefreq in static_pages:
        try:
            url = request.build_absolute_uri(reverse(name))
            xml.append(f'  <url>')
            xml.append(f'    <loc>{url}</loc>')
            xml.append(f'    <changefreq>{changefreq}</changefreq>')
            xml.append(f'    <priority>{priority}</priority>')
            xml.append(f'  </url>')
        except:
            pass
    
    # Store pages
    store_pages = [
        ('store:business', 0.8, 'monthly'),
        ('store:blog', 0.8, 'weekly'),
        ('store:login', 0.5, 'yearly'),
    ]
    
    for name, priority, changefreq in store_pages:
        try:
            url = request.build_absolute_uri(reverse(name))
            xml.append(f'  <url>')
            xml.append(f'    <loc>{url}</loc>')
            xml.append(f'    <changefreq>{changefreq}</changefreq>')
            xml.append(f'    <priority>{priority}</priority>')
            xml.append(f'  </url>')
        except:
            pass
    
    # Blog posts
    try:
        for post in BlogPost.objects.filter(published=True):
            url = request.build_absolute_uri(reverse('store:blog_detail', args=[post.slug]))
            xml.append(f'  <url>')
            xml.append(f'    <loc>{url}</loc>')
            xml.append(f'    <lastmod>{post.updated_at.strftime("%Y-%m-%d")}</lastmod>')
            xml.append(f'    <changefreq>weekly</changefreq>')
            xml.append(f'    <priority>0.8</priority>')
            xml.append(f'  </url>')
    except:
        pass
    
    xml.append('</urlset>')
    
    return HttpResponse('\n'.join(xml), content_type='application/xml')

urlpatterns = [
    path('admin/', admin_site.urls),
    path('', store_views.home, name='home'),
    path('home/', store_views.home, name='home'),
    path('store/', include(('store.urls', 'store'), namespace='store')),
    path('about/', store_views.about, name='about'),
    path('roadmap/', store_views.roadmap, name='roadmap'),
    path('send_waste/', store_views.send_waste, name='send_waste'),
    path('robots.txt', robots_txt),
    path('sitemap.xml', sitemap_xml, name='sitemap'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
