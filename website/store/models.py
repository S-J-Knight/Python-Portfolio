from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify       # <-- add
from django.urls import reverse             # <-- add
from decimal import Decimal

class ParcelStatus(models.TextChoices):
    AWAITING = 'awaiting', 'Awaiting Parcel'
    RECEIVED = 'received', 'Received'
    PROCESSED = 'processed', 'Processed'

class MaterialType(models.TextChoices):
    PLA = 'PLA', 'PLA'
    PETG = 'PETG', 'PETG'
    # add more when supported (ABS, TPU, etc.)

class PlasticType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    points_per_kg_basic = models.IntegerField(default=100, help_text="Points per kg for basic members")
    points_per_kg_premium = models.IntegerField(default=120, help_text="Points per kg for premium members (20% bonus)")
    
    def __str__(self):
        return self.name

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
    admin_comment = models.TextField(blank=True, default='')
    points_calculated = models.IntegerField(null=True, blank=True, help_text="Auto-calculated based on weight, editable by admin")
    points_awarded = models.BooleanField(default=False)  # track if points were already awarded
    
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
        """Ensure ParcelMaterial rows exist for selected plastics"""
        wanted = set(self.selected_materials())
        have = set(self.materials.values_list('plastic_type__name', flat=True))
        
        # Create any missing rows (one per selected material)
        for material_name in wanted - have:
            try:
                plastic_type = PlasticType.objects.get(name=material_name)
                ParcelMaterial.objects.create(parcel=self, plastic_type=plastic_type)
            except PlasticType.DoesNotExist:
                pass
        
        # Remove extras if they exist
        for material_name in have - wanted:
            plastic_type = PlasticType.objects.get(name=material_name)
            self.materials.filter(plastic_type=plastic_type).delete()

    def calculate_points(self):
        """
        Auto-calculate points based on:
        - Material weight
        - Plastic type point values
        - Customer membership tier (basic vs premium)
        """
        customer = Customer.objects.filter(user=self.user).first()
        is_premium = customer.is_premium if customer else False
        
        total_points = 0
        for material in self.materials.all():
            if material.weight_kg and material.plastic_type:
                # Get points per kg based on membership
                if is_premium:
                    points_per_kg = material.plastic_type.points_per_kg_premium
                else:
                    points_per_kg = material.plastic_type.points_per_kg_basic
                
                # Calculate points for this material
                material_points = int(material.weight_kg * points_per_kg)
                total_points += material_points
        
        return total_points

    def save(self, *args, **kwargs):
        # Don't auto-calculate if admin has manually set points
        # Only calculate if points_calculated is None AND we have an existing pk
        super().save(*args, **kwargs)  # Save first so materials exist

    def award_points_to_customer(self):
        """Award points to the user's customer account"""
        if self.points_calculated and not self.points_awarded and self.user:
            customer, _ = Customer.objects.get_or_create(
                user=self.user,
                defaults={'name': self.user.username, 'email': self.user.email}
            )
            customer.total_points += self.points_calculated
            customer.save()
            self.points_awarded = True
            self.save(update_fields=['points_awarded'])

class ParcelMaterial(models.Model):
    parcel = models.ForeignKey(IncomingParcel, on_delete=models.CASCADE, related_name='materials')
    plastic_type = models.ForeignKey(PlasticType, on_delete=models.CASCADE)  # Remove null=True, blank=True
    weight_kg = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    
    def __str__(self):
        return f"{self.plastic_type.name if self.plastic_type else 'Unknown'} - {self.weight_kg}kg"
    
    def calculate_points(self):
        """Calculate points for this specific material"""
        if not self.weight_kg or not self.plastic_type:
            return 0
        
        # Check if parcel user is premium
        customer = Customer.objects.filter(user=self.parcel.user).first()
        is_premium = customer.is_premium if customer else False
        
        if is_premium:
            points_per_kg = self.plastic_type.points_per_kg_premium
        else:
            points_per_kg = self.plastic_type.points_per_kg_basic
        
        return int(self.weight_kg * points_per_kg)

# Create your models here.

class Customer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200, null=True)
    email = models.CharField(max_length=200, null=True)
    total_points = models.IntegerField(default=0)
    is_premium = models.BooleanField(default=False)

    def __str__(self):
        return self.name or "Unnamed Customer"
    
    def get_verified_weight(self):
        """Get total verified weight from all parcels"""
        from django.db.models import Sum
        total = ParcelMaterial.objects.filter(
            parcel__user=self.user,
            weight_kg__isnull=False
        ).aggregate(total_weight=Sum('weight_kg'))['total_weight']
        return float(total or 0)
    
    def get_parcel_count(self):
        """Get count of verified parcels (those with points awarded)"""
        return IncomingParcel.objects.filter(
            user=self.user,
            points_awarded=True
        ).count()
    
    def get_premium_progress(self):
        """Calculate progress toward premium (0-100)"""
        if self.is_premium:
            return 100
        
        parcel_count = self.get_parcel_count()
        verified_weight = self.get_verified_weight()
        
        # Progress is whichever is higher (10 parcels OR 25kg)
        parcel_progress = min((parcel_count / 10) * 100, 100)
        weight_progress = min((verified_weight / 25) * 100, 100)
        
        return max(parcel_progress, weight_progress)
    
    def is_eligible_for_premium(self):
        """Check if customer meets premium requirements"""
        # Don't check if already premium
        if self.is_premium:
            return False
        
        # Check both conditions: 10 parcels OR 25kg
        return self.get_parcel_count() >= 10 or self.get_verified_weight() >= 25
    
    def parcels_needed(self):
        """Calculate parcels remaining to unlock premium"""
        return max(0, 10 - self.get_parcel_count())
    
    def weight_needed(self):
        """Calculate kg remaining to unlock premium"""
        return max(0, 25 - self.get_verified_weight())

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

class OrderStatus(models.TextChoices):
    POTENTIAL = 'Potential Order', 'Potential Order'  # New: cart not checked out yet
    RECEIVED = 'Order Received', 'Order Received'     # When user completes checkout
    PROCESSING = 'Processing', 'Processing'
    SHIPPED = 'Shipped', 'Shipped'
    DELIVERED = 'Delivered', 'Delivered'
    CANCELLED = 'Cancelled', 'Cancelled'

class Order(models.Model):
	customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
	date_ordered = models.DateTimeField(auto_now_add=True)
	status = models.CharField(
		max_length=20,
		choices=OrderStatus.choices,
		default=OrderStatus.POTENTIAL  # Changed from 'Order Received'
	)
	transaction_id = models.CharField(max_length=100, null=True, blank=True)
	tracking_number = models.CharField(max_length=100, null=True, blank=True)
	points_used = models.IntegerField(default=0)  # Add this field

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
		total = sum([item.get_total for item in orderitems])  # Decimal
		return total 

	@property
	def points_discount_gbp(self):
		"""£ value of points used (1 point = £0.01)"""
		return (Decimal(self.points_used) / Decimal('100')).quantize(Decimal('0.01'))

	@property
	def get_cart_total_after_points(self):
		"""Total after applying points discount (Decimal)"""
		subtotal = self.get_cart_total                       # Decimal
		discount = Decimal(self.points_used) / Decimal('100')
		final_total = subtotal - discount
		if final_total < Decimal('0.00'):
			final_total = Decimal('0.00')
		return final_total.quantize(Decimal('0.01'))

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

class PointTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('EARNED', 'Earned from Parcel'),
        ('REDEEMED', 'Redeemed for Discount'),
        ('ADJUSTED', 'Manual Adjustment'),
        ('BONUS', 'Bonus Points'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='point_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, default='EARNED')
    points = models.IntegerField()  # Positive for earned, negative for redeemed
    description = models.CharField(max_length=255)
    related_parcel = models.ForeignKey('IncomingParcel', on_delete=models.SET_NULL, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_created']
    
    def __str__(self):
        return f"{self.customer} - {self.points} points - {self.transaction_type}"