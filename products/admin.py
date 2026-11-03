"""
products/admin.py

Professional Django admin for the New Foam product catalogue.

Features:
  - Upload images directly from the admin — files are sent to ImageKit CDN
    automatically on save. The CDN URL is stored; no local file is kept.
  - Paste an image URL instead of uploading a file (both work).
  - Live image preview inside every inline row.
  - Primary image badge clearly visible in the inline.
  - "Set as primary" action per inline row.
  - Bulk admin actions: mark featured, unmark featured, activate stock,
    deactivate stock, duplicate product.
  - Product list shows thumbnail, stock badge, price, discount badge.
  - Category list shows product count and active/inactive toggle.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import slugify
from django.db import models as db_models
from django.db.models import Count
from django import forms
from django.contrib import messages
from .models import Category, Product, ProductImage, ProductReview, ProductLike


# ─────────────────────────────────────────────────────────────────────────────
# Custom widget: larger textarea for description fields
# ─────────────────────────────────────────────────────────────────────────────
class WideTextarea(forms.Textarea):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('attrs', {}).update({'rows': 4, 'style': 'width:100%;'})
        super().__init__(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# ProductImage inline — used inside ProductAdmin
# ─────────────────────────────────────────────────────────────────────────────
class ProductImageInlineForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'image_url', 'alt_text', 'is_primary', 'order']
        widgets = {
            'image_url': forms.URLInput(attrs={
                'placeholder': 'https://example.com/image.jpg  (or upload a file above)',
                'style': 'width:100%;',
            }),
            'alt_text': forms.TextInput(attrs={
                'placeholder': 'e.g. "Queen mattress — side view"',
                'style': 'width:100%;',
            }),
            'order': forms.NumberInput(attrs={'style': 'width:60px;'}),
        }
        help_texts = {
            'image': (
                'Upload a JPG/PNG/WEBP file. '
                'It will be uploaded to ImageKit CDN automatically. '
                'Leave blank if you are pasting a URL below.'
            ),
            'image_url': (
                'If you already have a hosted image URL paste it here. '
                'Leave blank if you are uploading a file above.'
            ),
            'is_primary': 'Tick this box to make this the main product image shown in listings.',
            'order':      'Images with lower numbers appear first in galleries.',
        }


class ProductImageInline(admin.TabularInline):
    model        = ProductImage
    form         = ProductImageInlineForm
    extra        = 1          # one blank row ready to fill
    max_num      = 10         # reasonable ceiling
    can_delete   = True
    show_change_link = False
    ordering     = ('order', 'created_at')

    # Columns shown in the inline table
    fields = (
        'preview_thumbnail',
        'image',
        'image_url',
        'alt_text',
        'is_primary',
        'order',
    )
    readonly_fields = ('preview_thumbnail',)

    # ── thumbnail shown for every saved image row ────────────────────────────
    def preview_thumbnail(self, obj):
        url = obj.get_display_url() if obj.pk else None
        if url:
            return format_html(
                '<img src="{url}" '
                '     style="height:80px; width:80px; object-fit:cover; '
                '            border-radius:6px; border:2px solid {border};" '
                '     title="{title}" />',
                url=url,
                border='#2563eb' if obj.is_primary else '#e5e7eb',
                title='PRIMARY IMAGE' if obj.is_primary else obj.alt_text or '',
            )
        return format_html(
            '<span style="color:#9ca3af; font-size:12px;">No image yet</span>'
        )
    preview_thumbnail.short_description = 'Preview'

    # ── primary badge in column header area ──────────────────────────────────
    def get_fields(self, request, obj=None):
        return self.fields


# ─────────────────────────────────────────────────────────────────────────────
# ProductReview inline
# ─────────────────────────────────────────────────────────────────────────────
class ProductReviewInline(admin.StackedInline):
    model          = ProductReview
    extra          = 0
    can_delete     = True
    show_change_link = True
    readonly_fields  = ['user', 'rating', 'helpful_votes', 'created_at', 'updated_at']
    fields           = [
        'user', 'rating', 'title', 'comment',
        'is_approved', 'helpful_votes', 'created_at',
    ]

    def has_add_permission(self, request, obj=None):
        # Reviews are submitted by users — not created from admin
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Category admin
# ─────────────────────────────────────────────────────────────────────────────
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = [
        'name', 'slug', 'parent', 'product_count',
        'is_active', 'created_at',
    ]
    list_filter   = ['is_active', 'parent']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering      = ['name']
    list_editable = ['is_active']
    list_per_page = 30

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'image', 'parent', 'is_active'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _product_count=Count('products')
        )

    @admin.display(description='Products', ordering='_product_count')
    def product_count(self, obj):
        count = getattr(obj, '_product_count', 0)
        colour = '#16a34a' if count > 0 else '#9ca3af'
        return format_html(
            '<span style="font-weight:600; color:{colour};">{count}</span>',
            colour=colour,
            count=count,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Product admin — the main event
# ─────────────────────────────────────────────────────────────────────────────
class ProductAdminForm(forms.ModelForm):
    class Meta:
        model   = Product
        fields  = '__all__'
        widgets = {
            'description':       WideTextarea(),
            'short_description': forms.TextInput(attrs={'style': 'width:100%;'}),
        }


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form        = ProductAdminForm
    inlines     = [ProductImageInline, ProductReviewInline]
    list_per_page = 20

    # ── list view columns ────────────────────────────────────────────────────
    list_display = [
        'product_thumbnail',
        'name',
        'category',
        'price_display',
        'stock_badge',
        'rating_display',
        'is_featured',
        'is_in_stock',
        'updated_at',
    ]
    list_filter   = [
        'category',
        'is_featured',
        'is_in_stock',
        'is_sponsored',
        'size',
        'material',
    ]
    search_fields = ['name', 'sku', 'description', 'short_description']
    prepopulated_fields = {'slug': ('name',)}
    ordering      = ['-created_at']
    list_editable = ['is_featured', 'is_in_stock']
    date_hierarchy = 'created_at'
    save_on_top   = True          # Save buttons at top AND bottom

    readonly_fields = [
        'average_rating', 'total_ratings', 'total_likes',
        'total_sold', 'created_at', 'updated_at',
        'product_image_gallery',
    ]

    # ── detail view fieldsets ────────────────────────────────────────────────
    fieldsets = (
        ('📝  Basic Information', {
            'fields': (
                'name', 'slug', 'category',
                'short_description', 'description',
            ),
        }),
        ('💰  Pricing', {
            'fields': (
                ('price_usd', 'price_zwl'),
                'discount_percentage',
            ),
        }),
        ('📦  Inventory', {
            'fields': (
                ('sku', 'stock_quantity', 'low_stock_threshold'),
                ('is_in_stock',),
            ),
        }),
        ('🔧  Specifications', {
            'fields': (
                ('size', 'material', 'color'),
                ('dimensions', 'weight'),
            ),
            'classes': ('collapse',),
        }),
        ('📣  Marketing', {
            'fields': (
                ('is_featured', 'is_sponsored'),
                'published_at',
            ),
        }),
        ('🖼️  Images (current)', {
            'fields': ('product_image_gallery',),
            'description': (
                'Scroll down to the <strong>Images</strong> section to '
                'add, remove, or reorder images.'
            ),
        }),
        ('📊  Statistics', {
            'fields': (
                ('average_rating', 'total_ratings'),
                ('total_likes', 'total_sold'),
                ('created_at', 'updated_at'),
            ),
            'classes': ('collapse',),
        }),
    )

    # fieldsets used on the ADD form (no readonly stats)
    add_fieldsets = (
        ('📝  Basic Information', {
            'fields': (
                'name', 'slug', 'category',
                'short_description', 'description',
            ),
        }),
        ('💰  Pricing', {
            'fields': (
                ('price_usd', 'price_zwl'),
                'discount_percentage',
            ),
        }),
        ('📦  Inventory', {
            'fields': (
                ('sku', 'stock_quantity', 'low_stock_threshold'),
                'is_in_stock',
            ),
        }),
        ('🔧  Specifications', {
            'fields': (
                ('size', 'material', 'color'),
                ('dimensions', 'weight'),
            ),
        }),
        ('📣  Marketing', {
            'fields': (
                ('is_featured', 'is_sponsored'),
            ),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return self.fieldsets

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        return self.readonly_fields

    # ── list view computed columns ───────────────────────────────────────────
    @admin.display(description='Image')
    def product_thumbnail(self, obj):
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        if img:
            url = img.get_display_url()
            if url:
                return format_html(
                    '<img src="{}" style="height:48px; width:48px; '
                    'object-fit:cover; border-radius:4px;" />',
                    url,
                )
        return format_html(
            '<div style="height:48px; width:48px; background:#f3f4f6; '
            'border-radius:4px; display:flex; align-items:center; '
            'justify-content:center; color:#9ca3af; font-size:18px;">📷</div>'
        )

    @admin.display(description='Price (USD)', ordering='price_usd')
    def price_display(self, obj):
        if obj.discount_percentage:
            return format_html(
                '<span style="text-decoration:line-through; color:#9ca3af;">'
                '${orig}</span> '
                '<span style="color:#dc2626; font-weight:600;">${disc}</span> '
                '<span style="background:#fef2f2; color:#dc2626; '
                'font-size:11px; padding:2px 5px; border-radius:3px;">'
                '-{pct}%</span>',
                orig=obj.price_usd,
                disc=obj.discounted_price_usd,
                pct=obj.discount_percentage,
            )
        return format_html(
            '<span style="font-weight:600;">${}</span>', obj.price_usd
        )

    @admin.display(description='Stock', ordering='stock_quantity')
    def stock_badge(self, obj):
        qty = obj.stock_quantity
        if qty == 0:
            colour, bg, label = '#dc2626', '#fef2f2', 'OUT OF STOCK'
        elif qty <= obj.low_stock_threshold:
            colour, bg, label = '#d97706', '#fffbeb', f'LOW  {qty}'
        else:
            colour, bg, label = '#16a34a', '#f0fdf4', str(qty)
        return format_html(
            '<span style="background:{bg}; color:{colour}; font-weight:600; '
            'font-size:11px; padding:3px 8px; border-radius:4px;">{label}</span>',
            bg=bg, colour=colour, label=label,
        )

    @admin.display(description='Rating', ordering='average_rating')
    def rating_display(self, obj):
        if obj.total_ratings == 0:
            return format_html('<span style="color:#9ca3af;">No ratings</span>')
        stars = '★' * int(obj.average_rating) + '☆' * (5 - int(obj.average_rating))
        return format_html(
            '<span style="color:#f59e0b;" title="{rating}/5 from {n} reviews">'
            '{stars}</span> '
            '<span style="color:#6b7280; font-size:11px;">({n})</span>',
            stars=stars,
            rating=obj.average_rating,
            n=obj.total_ratings,
        )

    # ── image gallery shown in the detail view (read-only overview) ──────────
    @admin.display(description='Current images')
    def product_image_gallery(self, obj):
        images = obj.images.all()
        if not images:
            return format_html(
                '<p style="color:#9ca3af;">No images yet — '
                'add them in the <strong>Images</strong> section below.</p>'
            )
        html = '<div style="display:flex; flex-wrap:wrap; gap:10px; margin-top:6px;">'
        for img in images:
            url = img.get_display_url()
            if not url:
                continue
            border = '3px solid #2563eb' if img.is_primary else '2px solid #e5e7eb'
            label  = (
                '<div style="background:#2563eb; color:#fff; font-size:10px; '
                'text-align:center; padding:2px 0; border-radius:0 0 4px 4px;">'
                'PRIMARY</div>'
                if img.is_primary else ''
            )
            html += (
                f'<div style="border:{border}; border-radius:6px; overflow:hidden;">'
                f'  <img src="{url}" style="height:90px; width:90px; '
                f'       object-fit:cover; display:block;" '
                f'       title="{img.alt_text or img.order}" />'
                f'  {label}'
                f'</div>'
            )
        html += '</div>'
        return format_html(html)

    # ── bulk actions ─────────────────────────────────────────────────────────
    actions = [
        'action_mark_featured',
        'action_unmark_featured',
        'action_mark_in_stock',
        'action_mark_out_of_stock',
        'action_mark_sponsored',
        'action_duplicate',
    ]

    @admin.action(description='✅  Mark selected products as Featured')
    def action_mark_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} product(s) marked as featured.', messages.SUCCESS)

    @admin.action(description='❌  Remove Featured from selected products')
    def action_unmark_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} product(s) removed from featured.', messages.SUCCESS)

    @admin.action(description='📦  Mark selected products as In Stock')
    def action_mark_in_stock(self, request, queryset):
        updated = queryset.update(is_in_stock=True)
        self.message_user(request, f'{updated} product(s) marked as in stock.', messages.SUCCESS)

    @admin.action(description='🚫  Mark selected products as Out of Stock')
    def action_mark_out_of_stock(self, request, queryset):
        updated = queryset.update(is_in_stock=False)
        self.message_user(request, f'{updated} product(s) marked as out of stock.', messages.SUCCESS)

    @admin.action(description='📣  Mark selected products as Sponsored')
    def action_mark_sponsored(self, request, queryset):
        updated = queryset.update(is_sponsored=True)
        self.message_user(request, f'{updated} product(s) marked as sponsored.', messages.SUCCESS)

    @admin.action(description='📋  Duplicate selected products (copies without images)')
    def action_duplicate(self, request, queryset):
        created = 0
        for product in queryset:
            base_slug = product.slug
            new_slug  = f'{base_slug}-copy'
            counter   = 1
            while Product.objects.filter(slug=new_slug).exists():
                new_slug = f'{base_slug}-copy-{counter}'
                counter += 1

            new_sku = f'{product.sku}-COPY'
            sku_counter = 1
            while Product.objects.filter(sku=new_sku).exists():
                new_sku = f'{product.sku}-COPY-{sku_counter}'
                sku_counter += 1

            product.pk   = None
            product.id   = None
            product.slug = new_slug
            product.sku  = new_sku
            product.name = f'{product.name} (Copy)'
            product.is_featured  = False
            product.is_sponsored = False
            product.total_sold   = 0
            product.total_likes  = 0
            product.average_rating = 0
            product.total_ratings  = 0
            product.save()
            created += 1

        self.message_user(
            request,
            f'{created} product(s) duplicated. Add images to the copies.',
            messages.SUCCESS,
        )

    def get_queryset(self, request):
        # Prefetch images so thumbnails don't trigger N+1 queries
        return (
            super().get_queryset(request)
            .select_related('category')
            .prefetch_related('images')
        )


# ─────────────────────────────────────────────────────────────────────────────
# Stand-alone ProductImage admin (useful for bulk URL imports)
# ─────────────────────────────────────────────────────────────────────────────
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display  = ['preview_thumbnail', 'product', 'is_primary', 'order', 'created_at']
    list_filter   = ['is_primary', 'product__category']
    search_fields = ['product__name', 'alt_text']
    list_editable = ['is_primary', 'order']
    ordering      = ['product', 'order']
    list_per_page = 40
    raw_id_fields = ['product']

    fields = ['product', 'image', 'image_url', 'alt_text', 'is_primary', 'order']

    @admin.display(description='Preview')
    def preview_thumbnail(self, obj):
        url = obj.get_display_url()
        if url:
            return format_html(
                '<img src="{}" style="height:52px; width:52px; '
                'object-fit:cover; border-radius:4px;" />',
                url,
            )
        return '—'


# ─────────────────────────────────────────────────────────────────────────────
# Review admin
# ─────────────────────────────────────────────────────────────────────────────
@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display  = ['product', 'user', 'stars', 'title', 'is_approved', 'created_at']
    list_filter   = ['rating', 'is_approved', 'created_at']
    search_fields = ['product__name', 'user__email', 'title', 'comment']
    list_editable = ['is_approved']
    readonly_fields = ['created_at', 'updated_at', 'helpful_votes']
    ordering      = ['-created_at']

    @admin.display(description='Rating', ordering='rating')
    def stars(self, obj):
        filled = '★' * obj.rating
        empty  = '☆' * (5 - obj.rating)
        return format_html(
            '<span style="color:#f59e0b;">{}</span>'
            '<span style="color:#d1d5db;">{}</span>',
            filled, empty,
        )


# ─────────────────────────────────────────────────────────────────────────────
# ProductLike admin (read-only audit)
# ─────────────────────────────────────────────────────────────────────────────
@admin.register(ProductLike)
class ProductLikeAdmin(admin.ModelAdmin):
    list_display  = ['user', 'product', 'created_at']
    list_filter   = ['created_at']
    search_fields = ['user__email', 'product__name']
    readonly_fields = ['user', 'product', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
