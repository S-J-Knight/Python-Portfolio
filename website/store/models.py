from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
from django.utils import timezone

# Create your models here.

class Customer(models.Model):
	user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
	name = models.CharField(max_length=200, null=True)
	email = models.CharField(max_length=200)

	def __str__(self):
		return self.name


class Product(models.Model):
	name = models.CharField(max_length=200)
	slug = models.SlugField(unique=True, blank=True, max_length=255 )
	price = models.DecimalField(max_digits=7, decimal_places=2)
	description = models.TextField(blank=True)
	digital = models.BooleanField(default=False,null=True, blank=True)
	image = models.ImageField(upload_to='static/images/Products/', blank=True, null=True)
	is_active = models.BooleanField(default=True)
	created = models.DateTimeField(default=timezone.now)
	updated = models.DateTimeField(auto_now=True)

	def __str__(self):
		return self.name

	def save(self, *args, **kwargs):
		if not self.slug:
			base = slugify(self.name)[:200]
			slug = base
			# ensure unique slug
			i = 1
			while Product.objects.filter(slug=slug).exists():
				slug = f"{base}-{i}"
				i += 1
			self.slug = slug
		super().save(*args, **kwargs)
  
	def get_absolute_url(self):
		return reverse('store:product_detail', kwargs={'slug': self.slug})	

class Order(models.Model):
	customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
	date_ordered = models.DateTimeField(auto_now_add=True)
	complete = models.BooleanField(default=False)
	transaction_id = models.CharField(max_length=100, null=True)

	def __str__(self):
		return str(self.id)
		
	@property
	def shipping(self):
		shipping = False
		orderitems = self.orderitem_set.all()
		for i in orderitems:
			if i.product.digital == False:
				shipping = True
		return shipping

	@property
	def get_cart_total(self):
		orderitems = self.orderitem_set.all()
		total = sum([item.get_total for item in orderitems])
		return total 

	@property
	def get_cart_items(self):
		orderitems = self.orderitem_set.all()
		total = sum([item.quantity for item in orderitems])
		return total 

class OrderItem(models.Model):
	product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
	order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True)
	quantity = models.IntegerField(default=0, null=True, blank=True)
	date_added = models.DateTimeField(auto_now_add=True)

	@property
	def get_total(self):
		total = self.product.price * self.quantity
		return total

class ShippingAddress(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=200)
    county = models.CharField(max_length=200)
    postcode = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="Unknown")
    is_saved = models.BooleanField(default=False)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.address}, {self.city}, {self.postcode}"