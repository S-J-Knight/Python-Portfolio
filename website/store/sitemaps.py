from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from store.models import BlogPost

class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""
    
    def items(self):
        return ['home', 'send_waste', 'about', 'roadmap', 'store:business', 'store:blog', 'store:login']

    def location(self, item):
        return reverse(item)
    
    def priority(self, item):
        if item == 'home':
            return 1.0
        elif item in ['send_waste', 'store:blog']:
            return 0.9
        return 0.7
    
    def changefreq(self, item):
        if item in ['home', 'roadmap', 'store:blog']:
            return 'weekly'
        return 'monthly'


class BlogPostSitemap(Sitemap):
    """Sitemap for blog posts"""
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return BlogPost.objects.filter(published=True)

    def lastmod(self, obj):
        return obj.updated_at
