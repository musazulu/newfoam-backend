from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

User = get_user_model()

class Category(models.Model):
    """Product categories as per requirements"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='children')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """Main product model for bedding items"""
    # Product types from requirements
    BED_TYPE_CHOICES = [
        ('single', 'Single'),
        ('double', 'Double'),
        ('queen', 'Queen'),
        ('king', 'King'),
        ('super_king', 'Super King'),
    ]
    
    MATERIAL_CHOICES = [
        ('cotton', 'Cotton'),
        ('polyester', 'Polyester'),
        ('linen', 'Linen'),
        ('wool', 'Wool'),
        ('bamboo', 'Bamboo'),
        ('silk', 'Silk'),
        ('microfiber', 'Microfiber'),
    ]
    
    # Basic information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=250)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    
    # Pricing - Both USD and ZWL as per requirements
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    price_zwl = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, 
                                   validators=[MinValueValidator(Decimal('0.01'))])
    discount_percentage = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(100)])
    
    # Stock and availability
    sku = models.CharField(max_length=100, unique=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    is_in_stock = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_sponsored = models.BooleanField(default=False)
    
    # Product specifications
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    size = models.CharField(max_length=50, choices=BED_TYPE_CHOICES, blank=True)
    material = models.CharField(max_length=50, choices=MATERIAL_CHOICES, blank=True)
    color = models.CharField(max_length=50, blank=True)
    dimensions = models.CharField(max_length=100, blank=True, help_text="e.g., 200cm x 150cm x 30cm")
    weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, help_text="Weight in kg")
    
    # Ratings and engagement
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_ratings = models.PositiveIntegerField(default=0)
    total_likes = models.PositiveIntegerField(default=0)
    total_sold = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['average_rating']),
            models.Index(fields=['price_usd']),
            models.Index(fields=['is_featured']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def discounted_price_usd(self):
        if self.discount_percentage > 0:
            discount_amount = (Decimal(self.discount_percentage) / Decimal(100)) * self.price_usd
            return self.price_usd - discount_amount
        return self.price_usd

    @property
    def discounted_price_zwl(self):
        if self.price_zwl and self.discount_percentage > 0:
            discount_amount = (Decimal(self.discount_percentage) / Decimal(100)) * self.price_zwl
            return self.price_zwl - discount_amount
        return self.price_zwl
    
    def update_stock(self, quantity):
        """Update stock after purchase"""
        if quantity > self.stock_quantity:
            raise ValueError("Insufficient stock")
        self.stock_quantity -= quantity
        self.total_sold += quantity
        if self.stock_quantity <= self.low_stock_threshold:
            # Could trigger a low stock notification here
            pass
        self.save()

    

class ProductImage(models.Model):
    """Multiple images per product.
    
    Two ways to provide an image:
      1. Upload a file via the admin — it gets sent to ImageKit and the
         returned CDN URL is stored in `image_url` automatically.
      2. Paste a URL directly into `image_url` (e.g. Unsplash, existing CDN).
    
    The first image added to a product is automatically set as primary.
    Only one image per product can be primary at a time.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        help_text="Upload an image file — it will be sent to ImageKit CDN automatically."
    )
    image_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="CDN URL (auto-filled after upload, or paste a URL directly)."
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        help_text="Describe the image for accessibility and SEO."
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="The primary image is shown in product listings and cards."
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{'[PRIMARY] ' if self.is_primary else ''}Image for {self.product.name}"

    def get_display_url(self):
        """Return the best available URL for this image."""
        if self.image_url:
            return self.image_url
        if self.image:
            return self.image.url
        return None

    def save(self, *args, **kwargs):
        # ── 1. Upload file to ImageKit if a new file was attached ──────────
        if self.image and not self.image_url:
            url = self._upload_to_imagekit()
            if url:
                self.image_url = url
                # Clear the local file reference — the CDN URL is the source of truth
                self.image = None

        # ── 2. Auto-set primary if this is the first image for the product ─
        if not self.pk:  # new record
            if not ProductImage.objects.filter(product=self.product).exists():
                self.is_primary = True

        # ── 3. Enforce single primary: demote others when this is set ──────
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)

        super().save(*args, **kwargs)

        # ── 4. Guarantee at least one primary exists ───────────────────────
        if not ProductImage.objects.filter(product=self.product, is_primary=True).exists():
            first = ProductImage.objects.filter(product=self.product).first()
            if first:
                ProductImage.objects.filter(pk=first.pk).update(is_primary=True)

    def _upload_to_imagekit(self):
        """Upload self.image file to ImageKit via REST API. Returns CDN URL or None."""
        from django.conf import settings as django_settings
        private_key = getattr(django_settings, 'IMAGEKIT_PRIVATE_KEY', '')
        if not private_key:
            return None
        try:
            import base64
            import requests as req

            # ImageKit upload API uses HTTP Basic Auth: private_key as username, empty password
            credentials = base64.b64encode(f"{private_key}:".encode()).decode()

            self.image.seek(0)
            file_name = self.image.name.split('/')[-1] or 'product-image.jpg'

            response = req.post(
                'https://upload.imagekit.io/api/v1/files/upload',
                headers={'Authorization': f'Basic {credentials}'},
                data={
                    'fileName': file_name,
                    'folder': '/products/',
                    'useUniqueFileName': 'true',
                },
                files={'file': (file_name, self.image, 'image/jpeg')},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data.get('url') or data.get('filePath')
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"ImageKit upload failed: {e}")
            return None

class ProductLike(models.Model):
    """Track which users like which products"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_likes')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'product']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} likes {self.product}"

class ProductReview(models.Model):
    """Product reviews and ratings"""
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField(blank=True)
    is_approved = models.BooleanField(default=True)  # Admin can moderate
    helpful_votes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['product', 'user']  # One review per user per product
    
    def __str__(self):
        return f"{self.user}'s review of {self.product} ({self.rating} stars)"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update product average rating
        reviews = self.product.reviews.filter(is_approved=True)
        if reviews.exists():
            avg_rating = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.product.average_rating = round(avg_rating, 2)
            self.product.total_ratings = reviews.count()
            self.product.save()