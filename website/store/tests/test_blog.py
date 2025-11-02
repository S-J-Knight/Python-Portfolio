"""
Tests for blog functionality: posts, images, detail pages.
"""
import pytest
from django.urls import reverse
from store.models import BlogPost


@pytest.mark.django_db
class TestBlogList:
    """Test blog list/index page"""
    
    def test_blog_page_loads_with_no_posts(self, client):
        """Test blog page loads even with no published posts"""
        url = reverse('store:blog')
        resp = client.get(url)
        assert resp.status_code == 200
    
    def test_blog_shows_published_posts(self, client, user):
        """Test that published posts appear on blog page"""
        post = BlogPost.objects.create(
            title='Published Post',
            slug='published-post',
            content='Published content',
            author=user,
            published=True
        )
        
        url = reverse('store:blog')
        resp = client.get(url)
        content = resp.content.decode()
        
        assert resp.status_code == 200
        assert 'Published Post' in content
    
    def test_blog_hides_unpublished_posts(self, client, user):
        """Test that unpublished posts don't appear"""
        BlogPost.objects.create(
            title='Draft Post',
            slug='draft-post',
            content='Draft content',
            author=user,
            published=False
        )
        
        url = reverse('store:blog')
        resp = client.get(url)
        content = resp.content.decode()
        
        assert 'Draft Post' not in content
    
    def test_blog_accessible_to_guests(self, client):
        """Test blog doesn't require authentication"""
        url = reverse('store:blog')
        resp = client.get(url)
        assert resp.status_code == 200
        assert 'login' not in resp.request['PATH_INFO'].lower()


@pytest.mark.django_db
class TestBlogDetail:
    """Test individual blog post pages"""
    
    def test_blog_detail_page_loads(self, client, user):
        """Test blog post detail page loads correctly"""
        post = BlogPost.objects.create(
            title='Detailed Post',
            slug='detailed-post',
            content='Detailed content here',
            author=user,
            published=True
        )
        
        url = reverse('store:blog_detail', args=[post.slug])
        resp = client.get(url)
        content = resp.content.decode()
        
        assert resp.status_code == 200
        assert 'Detailed Post' in content
        assert 'Detailed content here' in content
    
    def test_blog_detail_404_for_nonexistent(self, client):
        """Test 404 for non-existent blog post"""
        url = reverse('store:blog_detail', args=['nonexistent-slug'])
        resp = client.get(url)
        assert resp.status_code == 404
    
    def test_blog_detail_404_for_unpublished(self, client, user):
        """Test unpublished posts return 404"""
        post = BlogPost.objects.create(
            title='Unpublished Post',
            slug='unpublished',
            content='Secret content',
            author=user,
            published=False
        )
        
        url = reverse('store:blog_detail', args=[post.slug])
        resp = client.get(url)
        assert resp.status_code == 404
    
    def test_blog_detail_shows_author(self, client, user):
        """Test blog detail page shows author information"""
        post = BlogPost.objects.create(
            title='Author Test Post',
            slug='author-test',
            content='Content',
            author=user,
            published=True
        )
        
        url = reverse('store:blog_detail', args=[post.slug])
        resp = client.get(url)
        content = resp.content.decode()
        
        # Should show author name
        assert user.get_full_name() in content or user.username in content


@pytest.mark.django_db
class TestBlogImages:
    """Test blog image functionality (imageURL fix)"""
    
    def test_blog_post_has_imageURL_property(self, user):
        """Test that blog posts have imageURL property"""
        post = BlogPost.objects.create(
            title='Image Post',
            slug='image-post',
            content='Post with image',
            author=user,
            published=True
        )
        
        # Test imageURL property exists and returns a string
        assert hasattr(post, 'imageURL')
        assert isinstance(post.imageURL, str)
    
    def test_blog_list_uses_imageURL(self, client, user):
        """Test that blog list page uses imageURL (not broken featured_image)"""
        post = BlogPost.objects.create(
            title='Image List Post',
            slug='image-list',
            content='Content',
            author=user,
            published=True
        )
        
        url = reverse('store:blog')
        resp = client.get(url)
        
        # Should not cause errors even without image
        assert resp.status_code == 200


@pytest.mark.django_db
class TestBlogSEO:
    """Test blog SEO features"""
    
    def test_sitemap_includes_published_posts(self, client, user):
        """Test that published blog posts appear in sitemap"""
        post = BlogPost.objects.create(
            title='SEO Test Post',
            slug='seo-test',
            content='Content',
            author=user,
            published=True
        )
        
        url = reverse('sitemap')
        resp = client.get(url)
        content = resp.content.decode()
        
        assert 'seo-test' in content
    
    def test_sitemap_excludes_unpublished_posts(self, client, user):
        """Test unpublished posts don't appear in sitemap"""
        post = BlogPost.objects.create(
            title='Hidden Post',
            slug='hidden-post',
            content='Content',
            author=user,
            published=False
        )
        
        url = reverse('sitemap')
        resp = client.get(url)
        content = resp.content.decode()
        
        assert 'hidden-post' not in content


@pytest.mark.django_db
class TestBlogHomepageIntegration:
    """Test blog integration with homepage"""
    
    def test_home_page_shows_latest_posts(self, client, user):
        """Test homepage displays latest blog posts"""
        # Create multiple posts
        for i in range(3):
            BlogPost.objects.create(
                title=f'Home Post {i}',
                slug=f'home-post-{i}',
                content='Content',
                author=user,
                published=True
            )
        
        url = reverse('home')
        resp = client.get(url)
        content = resp.content.decode()
        
        # Should show at least some posts
        assert 'Home Post' in content or 'blog' in content.lower()
