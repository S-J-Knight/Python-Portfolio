from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify       # <-- add
from django.urls import reverse             # <-- add

class ParcelStatus(models.TextChoices):
    AWAITING = 'awaiting', 'Awaiting Parcel'
    RECEIVED = 'received', 'Received'
    PROCESSED = 'processed', 'Processed'

class MaterialType(models.TextChoices):
    PLA = 'PLA', 'PLA'
    PETG = 'PETG', 'PETG'
    # add more when supported (ABS, TPU, etc.)

# Assuming you already have IncomingParcel model
class IncomingParcel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='incoming_parcels', null=True, blank=True)

    # shipping_waste_form fields (nullable to allow migration)
    address = models.CharField(max_length=255, blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    county = models.CharField(max_length=100, blank=True, default='')
    postcode = models.CharField(max_length=20, blank=True, default='')
    country = models.CharField(max_length=100, blank=True, default='')
    details = models.TextField(blank=True, default='')

    # plastics selected by user (checkboxes on the form)
    pla = models.BooleanField(default=False)
    petg = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=ParcelStatus.choices, default=ParcelStatus.AWAITING)
    date_submitted = models.DateTimeField(default=timezone.now)
    admin_comment = models.TextField(blank=True, default='')  # notes visible to user

    def __str__(self):
        return f"ip{self.pk}"

    def selected_materials(self):
        out = []
        if self.pla:
            out.append(MaterialType.PLA)
        if self.petg:
            out.append(MaterialType.PETG)
        return out

    def ensure_material_rows(self):
        wanted = set(self.selected_materials())
        have = set(self.materials.values_list('material', flat=True))
        # create any missing rows (one per selected material)
        for m in wanted - have:
            ParcelMaterial.objects.create(parcel=self, material=m)
        # remove extras if they exist
        for m in have - wanted:
            self.materials.filter(material=m).delete()

class ParcelMaterial(models.Model):
    parcel = models.ForeignKey(IncomingParcel, on_delete=models.CASCADE, related_name='materials')
    material = models.CharField(max_length=10, choices=MaterialType.choices)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)

    class Meta:
        unique_together = ('parcel', 'material')

    def __str__(self):
        return f"{self.parcel} - {self.material}"

# auto-sync rows whenever a parcel is saved (created or updated)
@receiver(post_save, sender=IncomingParcel)
def _parcel_post_save(sender, instance, **kwargs):
    instance.ensure_material_rows()

# Create your models here.

class Customer(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
	name = models.CharField(max_length=200, null=True)
	email = models.CharField(max_length=200)
	is_premium = models.BooleanField(default=False)
	is_business = models.BooleanField(default=False)

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

	@property
	def imageURL(self):
		try:
			return self.image.url
		except:
			return ''

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
	STATUS_CHOICES = [
		('Order Received', 'Order Received'),
		('Processing', 'Processing'),
		('Order Shipped', 'Order Shipped'),
	]
	status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='Order Received')
	tracking_number = models.CharField(max_length=64, blank=True, null=True)
	transaction_id = models.CharField(max_length=100, null=True)

	def __str__(self):
		return str(self.id)
		
	@property
	def shipping(self):
		shipping = False
		orderitems = self.orderitem_set.all()
		for i in orderitems:
			if i.product and getattr(i.product, 'digital', None) is not None:
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
		if self.product:
			return self.product.price * self.quantity
		return 0

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