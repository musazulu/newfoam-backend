# products/serializers.py
from rest_framework import serializers
from .models import Category, Product, ProductImage, ProductReview, ProductLike


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Serializes a ProductImage for the frontend.
    `url` is always the best available URL: ImageKit CDN > uploaded file > None.
    The raw `image` file field is never exposed to the frontend.
    """
    url = serializers.SerializerMethodField()

    class Meta:
        model  = ProductImage
        fields = ['id', 'url', 'alt_text', 'is_primary', 'order']

    def get_url(self, obj):
        url = obj.get_display_url()
        if not url:
            return None
        # If it's a relative path (local dev uploaded file), make it absolute
        if url.startswith('/') or not url.startswith('http'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
        return url


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model  = Category
        fields = ['id', 'name', 'slug', 'description', 'is_active', 'product_count']

    def get_product_count(self, obj):
        return obj.products.filter(is_in_stock=True).count()


class ProductListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer used in list views and product cards.
    Returns one `primary_image` URL instead of the full images array.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'slug', 'short_description',
            'category', 'category_name', 'category_slug',
            'price_usd', 'price_zwl', 'discount_percentage',
            'discounted_price_usd', 'discounted_price_zwl',
            'average_rating', 'total_ratings', 'total_likes', 'total_sold',
            'primary_image',
            'is_featured', 'is_sponsored', 'is_in_stock',
            'size', 'material', 'color', 'dimensions', 'weight',
            'stock_quantity', 'low_stock_threshold',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['discounted_price_usd', 'discounted_price_zwl']

    def get_primary_image(self, obj):
        # images are prefetched in the viewset queryset — no extra DB hit
        images = obj.images.all()
        img = next((i for i in images if i.is_primary), None) or next(iter(images), None)
        if not img:
            return None

        url = img.get_display_url()
        if not url:
            return None

        # Make relative paths absolute (local dev)
        if url.startswith('/') or not url.startswith('http'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
        return url


class ProductDetailSerializer(ProductListSerializer):
    """
    Full serializer used on the product detail page.
    Includes all images and the full description.
    """
    images      = ProductImageSerializer(many=True, read_only=True)
    description = serializers.CharField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            'description', 'sku', 'published_at', 'images',
        ]


class ProductReviewSerializer(serializers.ModelSerializer):
    user_name  = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    comment    = serializers.CharField(allow_blank=True, required=False, default='')

    class Meta:
        model  = ProductReview
        fields = [
            'id', 'user', 'user_name', 'user_email',
            'rating', 'title', 'comment',
            'helpful_votes', 'is_approved',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['user', 'is_approved', 'helpful_votes']

    def get_user_name(self, obj):
        full = obj.user.get_full_name()
        return full if full.strip() else obj.user.username

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value


class ProductLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ProductLike
        fields = ['id', 'user', 'product', 'created_at']


class ProductSearchSerializer(serializers.Serializer):
    query     = serializers.CharField(required=False, allow_blank=True)
    category  = serializers.CharField(required=False, allow_blank=True)
    min_price = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    max_price = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    rating    = serializers.DecimalField(required=False, max_digits=3, decimal_places=1)
    size      = serializers.CharField(required=False, allow_blank=True)
    material  = serializers.CharField(required=False, allow_blank=True)
    sort_by   = serializers.CharField(required=False, default='relevance')
    page      = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=20, min_value=1, max_value=100)
