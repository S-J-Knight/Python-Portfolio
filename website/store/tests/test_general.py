"""
Tests for general website functionality: public pages, SEO, GDPR compliance.
"""
import pytest
from django.urls import reverse


# ========== Public Pages ==========

@pytest.mark.django_db
class TestPublicPages:
    """Test that public pages are accessible without authentication"""
    
    def test_home_page_loads(self, client):
        """Test home page is accessible"""
        url = reverse('home')
        resp = client.get(url)
        assert resp.status_code == 200
    
    def test_about_page_loads(self, client):
        """Test About page is accessible"""
        url = reverse('about')
        resp = client.get(url)
        assert resp.status_code == 200
    
    def test_privacy_page_loads(self, client):
        """Test Privacy Policy page is accessible"""
        url = reverse('privacy')
        resp = client.get(url)
        assert resp.status_code == 200
        assert 'Privacy Policy' in resp.content.decode()
    
    def test_roadmap_page_loads(self, client):
        """Test Roadmap page is accessible"""
        url = reverse('roadmap')
        resp = client.get(url)
        assert resp.status_code == 200
    
    def test_contact_page_loads(self, client):
        """Test Contact page is accessible"""
        url = reverse('store:contact')
        resp = client.get(url)
        assert resp.status_code == 200
    
    def test_business_page_loads(self, client):
        """Test Business page is accessible"""
        url = reverse('store:business')
        resp = client.get(url)
        assert resp.status_code == 200
    
    def test_send_waste_page_loads(self, client):
        """Test Send Waste page is accessible"""
        url = reverse('send_waste')
        resp = client.get(url)
        assert resp.status_code == 200
    
    def test_all_public_pages_no_auth_required(self, client):
        """Test that all public pages don't redirect to login"""
        public_urls = [
            reverse('home'),
            reverse('about'),
            reverse('privacy'),
            reverse('roadmap'),
            reverse('send_waste'),
            reverse('store:contact'),
            reverse('store:business'),
            reverse('store:blog'),
        ]
        
        for url in public_urls:
            resp = client.get(url)
            assert resp.status_code == 200, f"Failed for {url}"
            assert 'login' not in resp.request['PATH_INFO'].lower()


# ========== Privacy & GDPR ==========

@pytest.mark.django_db
class TestPrivacyAndGDPR:
    """Test GDPR compliance and privacy features"""
    
    def test_privacy_policy_has_gdpr_content(self, client):
        """Test privacy policy contains required GDPR information"""
        url = reverse('privacy')
        resp = client.get(url)
        content = resp.content.decode()
        
        # Check for key GDPR sections
        assert 'cookies' in content.lower()
        assert 'CSRF' in content or 'essential' in content.lower()
        assert 'info@knightcycle.co.uk' in content
    
    def test_only_essential_cookies_set(self, client):
        """Test that only essential cookies are set (no tracking)"""
        url = reverse('home')
        resp = client.get(url)
        
        cookies = resp.cookies
        cookie_names = [cookie.key for cookie in cookies.values()]
        
        # Only allow Django essential cookies
        allowed_cookies = ['csrftoken', 'sessionid', 'cart']
        
        for cookie_name in cookie_names:
            assert cookie_name in allowed_cookies, f"Unexpected tracking cookie: {cookie_name}"


# ========== SEO ==========

@pytest.mark.django_db
class TestSEO:
    """Test SEO features: sitemap, robots.txt"""
    
    def test_sitemap_loads(self, client):
        """Test that sitemap.xml is accessible"""
        url = reverse('sitemap')
        resp = client.get(url)
        assert resp.status_code == 200
        assert 'xml' in resp['Content-Type']
    
    def test_sitemap_includes_privacy_page(self, client):
        """Test sitemap includes privacy policy"""
        url = reverse('sitemap')
        resp = client.get(url)
        content = resp.content.decode()
        assert 'privacy' in content.lower()
    
    def test_robots_txt_loads(self, client):
        """Test robots.txt is accessible"""
        resp = client.get('/robots.txt')
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'text/plain'
    
    def test_robots_txt_disallows_private_pages(self, client):
        """Test robots.txt blocks private pages"""
        resp = client.get('/robots.txt')
        content = resp.content.decode()
        
        assert 'Disallow: /admin/' in content
        assert 'Disallow: /cart/' in content
        assert 'Disallow: /checkout/' in content
    
    def test_robots_txt_has_sitemap(self, client):
        """Test robots.txt includes sitemap reference"""
        resp = client.get('/robots.txt')
        content = resp.content.decode()
        assert 'Sitemap:' in content
        assert 'sitemap.xml' in content


# ========== Footer ==========

@pytest.mark.django_db
class TestFooter:
    """Test footer links and content"""
    
    def test_footer_links_present(self, client):
        """Test footer contains all expected links"""
        url = reverse('home')
        resp = client.get(url)
        content = resp.content.decode()
        
        # Check for footer links
        assert 'About' in content
        assert 'Privacy' in content
        assert 'Contact' in content
        assert 'Blog' in content
    
    def test_footer_copyright_present(self, client):
        """Test footer contains copyright notice"""
        url = reverse('home')
        resp = client.get(url)
        content = resp.content.decode()
        
        assert '© 2025 KnightCycle' in content or 'KnightCycle' in content


# ========== Home Page ==========

@pytest.mark.django_db
class TestHomePage:
    """Test home page specific functionality"""
    
    def test_home_page_shows_stats(self, client):
        """Test home page displays recycling statistics"""
        url = reverse('home')
        resp = client.get(url)
        content = resp.content.decode()
        
        # Should have some stats display
        assert 'kg' in content.lower() or 'parcel' in content.lower()
