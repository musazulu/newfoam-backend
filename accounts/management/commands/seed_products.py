"""
Management command to seed the database with sample products.
Run with: python manage.py seed_products
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from products.models import Category, Product, ProductImage


CATEGORIES = [
    {'name': 'Mattresses', 'slug': 'mattresses', 'description': 'Comfortable mattresses for every sleep style'},
    {'name': 'Bed Frames',  'slug': 'bed-frames',  'description': 'Sturdy and stylish bed frames'},
    {'name': 'Pillows',     'slug': 'pillows',      'description': 'Supportive pillows for a great night\'s sleep'},
    {'name': 'Duvets',      'slug': 'duvets',       'description': 'Warm and cozy duvets and comforters'},
    {'name': 'Bed Sheets',  'slug': 'bed-sheets',   'description': 'Soft and breathable bed linen'},
    {'name': 'Headboards',  'slug': 'headboards',   'description': 'Elegant headboards to complete your bedroom'},
]

PRODUCTS = [
    # Mattresses
    {
        'name': 'Serenity Foam Mattress - Queen',
        'slug': 'serenity-foam-mattress-queen',
        'category_slug': 'mattresses',
        'description': 'Premium memory foam mattress with 5 comfort zones for perfect spinal support. Hypoallergenic cover with cooling gel layer keeps you comfortable all night.',
        'short_description': 'Memory foam with 5 comfort zones and cooling gel layer.',
        'price_usd': '299.00',
        'price_zwl': '107640.00',
        'discount_percentage': 10,
        'sku': 'MAT-SF-QN-001',
        'stock_quantity': 25,
        'size': 'queen',
        'material': 'microfiber',
        'color': 'White',
        'dimensions': '152cm x 203cm x 25cm',
        'weight': '28.5',
        'is_featured': True,
        'average_rating': '4.70',
        'total_ratings': 43,
        'image_url': 'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&q=80',
    },
    {
        'name': 'OrthoSleep Bonnell Spring Mattress - King',
        'slug': 'orthosleep-bonnell-spring-king',
        'category_slug': 'mattresses',
        'description': 'Bonnell spring system with plush pillow top for the ultimate hotel-quality sleep experience. Reinforced edges prevent roll-off.',
        'short_description': 'Bonnell spring with plush pillow top — hotel quality.',
        'price_usd': '449.00',
        'price_zwl': '161640.00',
        'discount_percentage': 0,
        'sku': 'MAT-BS-KG-002',
        'stock_quantity': 15,
        'size': 'king',
        'material': 'cotton',
        'color': 'Ivory',
        'dimensions': '183cm x 203cm x 30cm',
        'weight': '42.0',
        'is_featured': True,
        'average_rating': '4.50',
        'total_ratings': 28,
        'image_url': 'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=800&q=80',
    },
    {
        'name': 'Budget Foam Mattress - Single',
        'slug': 'budget-foam-mattress-single',
        'category_slug': 'mattresses',
        'description': 'High-density foam mattress ideal for student rooms, guest rooms, and bunk beds. Easy to handle and maintain.',
        'short_description': 'High-density foam — great value for single beds.',
        'price_usd': '89.00',
        'price_zwl': '32040.00',
        'discount_percentage': 15,
        'sku': 'MAT-BF-SG-003',
        'stock_quantity': 50,
        'size': 'single',
        'material': 'polyester',
        'color': 'White',
        'dimensions': '91cm x 188cm x 15cm',
        'weight': '10.0',
        'is_featured': False,
        'average_rating': '4.20',
        'total_ratings': 67,
        'image_url': 'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=800&q=80',
    },
    # Bed Frames
    {
        'name': 'Walnut Wood Bed Frame - Queen',
        'slug': 'walnut-wood-bed-frame-queen',
        'category_slug': 'bed-frames',
        'description': 'Solid walnut wood bed frame with slatted base — no box spring needed. Minimalist Scandinavian design that fits any bedroom decor.',
        'short_description': 'Solid walnut, Scandinavian design, no box spring needed.',
        'price_usd': '520.00',
        'price_zwl': '187200.00',
        'discount_percentage': 5,
        'sku': 'BED-WW-QN-001',
        'stock_quantity': 12,
        'size': 'queen',
        'material': 'wool',
        'color': 'Walnut Brown',
        'dimensions': '165cm x 215cm x 45cm',
        'weight': '55.0',
        'is_featured': True,
        'average_rating': '4.80',
        'total_ratings': 19,
        'image_url': 'https://images.unsplash.com/photo-1588046130717-0eb0c9a3ba15?w=800&q=80',
    },
    {
        'name': 'Metal Platform Bed Frame - Double',
        'slug': 'metal-platform-bed-frame-double',
        'category_slug': 'bed-frames',
        'description': 'Heavy-duty steel frame with powder-coated finish. Anti-slip feet protect floors. Easy to assemble with included tools.',
        'short_description': 'Heavy-duty steel, powder-coated, easy assembly.',
        'price_usd': '185.00',
        'price_zwl': '66600.00',
        'discount_percentage': 20,
        'sku': 'BED-MP-DB-002',
        'stock_quantity': 30,
        'size': 'double',
        'material': 'polyester',
        'color': 'Matte Black',
        'dimensions': '142cm x 210cm x 35cm',
        'weight': '22.0',
        'is_featured': False,
        'average_rating': '4.30',
        'total_ratings': 54,
        'image_url': 'https://images.unsplash.com/photo-1616594039964-ae9021a400a0?w=800&q=80',
    },
    # Pillows
    {
        'name': 'Luxury Goose Down Pillow - Pack of 2',
        'slug': 'luxury-goose-down-pillow-pack-2',
        'category_slug': 'pillows',
        'description': 'Fill your sleep with cloud-like softness. Premium white goose down fill with 400 thread count Egyptian cotton cover. Machine washable.',
        'short_description': 'Goose down fill, 400TC Egyptian cotton cover. Pack of 2.',
        'price_usd': '75.00',
        'price_zwl': '27000.00',
        'discount_percentage': 0,
        'sku': 'PIL-GD-P2-001',
        'stock_quantity': 80,
        'size': '',
        'material': 'cotton',
        'color': 'White',
        'dimensions': '50cm x 75cm',
        'weight': '1.2',
        'is_featured': True,
        'average_rating': '4.90',
        'total_ratings': 112,
        'image_url': 'https://images.unsplash.com/photo-1584100936595-c0654b55a2e2?w=800&q=80',
    },
    {
        'name': 'Memory Foam Contour Pillow',
        'slug': 'memory-foam-contour-pillow',
        'category_slug': 'pillows',
        'description': 'Ergonomic contoured shape supports neck and shoulders. Ideal for side and back sleepers. Includes breathable bamboo cover.',
        'short_description': 'Ergonomic neck support with bamboo cover.',
        'price_usd': '45.00',
        'price_zwl': '16200.00',
        'discount_percentage': 10,
        'sku': 'PIL-MF-CN-002',
        'stock_quantity': 45,
        'size': '',
        'material': 'bamboo',
        'color': 'Off-White',
        'dimensions': '60cm x 40cm x 12cm',
        'weight': '1.5',
        'is_featured': False,
        'average_rating': '4.60',
        'total_ratings': 89,
        'image_url': 'https://images.unsplash.com/photo-1592789705501-f9ae4278a9c9?w=800&q=80',
    },
    # Duvets
    {
        'name': 'All-Season Microfibre Duvet - King',
        'slug': 'all-season-microfibre-duvet-king',
        'category_slug': 'duvets',
        'description': '10.5 tog rating — perfect for year-round use. Microfibre fill is hypoallergenic and machine washable. Anti-shift corner ties keep the insert in place.',
        'short_description': '10.5 tog, hypoallergenic, machine washable.',
        'price_usd': '95.00',
        'price_zwl': '34200.00',
        'discount_percentage': 0,
        'sku': 'DUV-AM-KG-001',
        'stock_quantity': 35,
        'size': 'king',
        'material': 'microfiber',
        'color': 'White',
        'dimensions': '230cm x 220cm',
        'weight': '2.8',
        'is_featured': True,
        'average_rating': '4.50',
        'total_ratings': 37,
        'image_url': 'https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=800&q=80',
    },
    # Bed Sheets
    {
        'name': 'Egyptian Cotton Sheet Set - Queen (1000TC)',
        'slug': 'egyptian-cotton-sheet-set-queen-1000tc',
        'category_slug': 'bed-sheets',
        'description': '4-piece set: fitted sheet, flat sheet, and 2 pillowcases. 1000 thread count Egyptian cotton for ultra-soft luxury feel. Deep pockets fit mattresses up to 40cm.',
        'short_description': '1000TC Egyptian cotton, 4-piece set, deep pockets.',
        'price_usd': '120.00',
        'price_zwl': '43200.00',
        'discount_percentage': 12,
        'sku': 'SHT-EC-QN-001',
        'stock_quantity': 60,
        'size': 'queen',
        'material': 'cotton',
        'color': 'Pearl White',
        'dimensions': 'Fitted: 152x203cm, Flat: 230x270cm',
        'weight': '1.8',
        'is_featured': True,
        'average_rating': '4.80',
        'total_ratings': 76,
        'image_url': 'https://images.unsplash.com/photo-1600369671373-8b9dc5b46f01?w=800&q=80',
    },
    {
        'name': 'Bamboo Blend Sheet Set - Double',
        'slug': 'bamboo-blend-sheet-set-double',
        'category_slug': 'bed-sheets',
        'description': 'Naturally cooling bamboo-cotton blend keeps you comfortable in warm weather. Wrinkle-resistant and gets softer with every wash.',
        'short_description': 'Bamboo-cotton blend — naturally cooling and wrinkle-resistant.',
        'price_usd': '85.00',
        'price_zwl': '30600.00',
        'discount_percentage': 0,
        'sku': 'SHT-BB-DB-002',
        'stock_quantity': 40,
        'size': 'double',
        'material': 'bamboo',
        'color': 'Sage Green',
        'dimensions': 'Fitted: 137x191cm, Flat: 200x275cm',
        'weight': '1.5',
        'is_featured': False,
        'average_rating': '4.70',
        'total_ratings': 48,
        'image_url': 'https://images.unsplash.com/photo-1560185007-cde436f6a4d0?w=800&q=80',
    },
    # Headboards
    {
        'name': 'Velvet Upholstered Headboard - Queen',
        'slug': 'velvet-upholstered-headboard-queen',
        'category_slug': 'headboards',
        'description': 'Floor-standing velvet headboard with deep button tufting. Wall-mounted or free-standing. Fits all standard queen bed frames.',
        'short_description': 'Tufted velvet, floor-standing or wall-mounted.',
        'price_usd': '210.00',
        'price_zwl': '75600.00',
        'discount_percentage': 0,
        'sku': 'HDB-VU-QN-001',
        'stock_quantity': 18,
        'size': 'queen',
        'material': 'linen',
        'color': 'Dusty Rose',
        'dimensions': '160cm x 120cm x 8cm',
        'weight': '12.0',
        'is_featured': True,
        'average_rating': '4.60',
        'total_ratings': 22,
        'image_url': 'https://images.unsplash.com/photo-1540518614846-7eded433c457?w=800&q=80',
    },
]


class Command(BaseCommand):
    help = 'Seed the database with sample categories and products'

    def handle(self, *args, **options):
        self.stdout.write('Creating categories...')
        cat_map = {}
        for c in CATEGORIES:
            obj, created = Category.objects.get_or_create(
                slug=c['slug'],
                defaults={'name': c['name'], 'description': c['description'], 'is_active': True}
            )
            cat_map[c['slug']] = obj
            status = 'created' if created else 'exists'
            self.stdout.write(f"  {c['name']} — {status}")

        self.stdout.write('Creating products...')
        created_count = 0
        for p in PRODUCTS:
            cat = cat_map.get(p['category_slug'])
            if not cat:
                self.stdout.write(self.style.WARNING(f"  Skipping {p['name']} — category not found"))
                continue

            product, created = Product.objects.get_or_create(
                slug=p['slug'],
                defaults={
                    'name': p['name'],
                    'category': cat,
                    'description': p['description'],
                    'short_description': p['short_description'],
                    'price_usd': p['price_usd'],
                    'price_zwl': p['price_zwl'],
                    'discount_percentage': p['discount_percentage'],
                    'sku': p['sku'],
                    'stock_quantity': p['stock_quantity'],
                    'is_in_stock': True,
                    'size': p['size'],
                    'material': p['material'],
                    'color': p['color'],
                    'dimensions': p['dimensions'],
                    'weight': p['weight'],
                    'is_featured': p['is_featured'],
                    'is_sponsored': False,
                    'average_rating': p['average_rating'],
                    'total_ratings': p['total_ratings'],
                }
            )

            if created:
                # Add primary image
                ProductImage.objects.create(
                    product=product,
                    image_url=p['image_url'],
                    alt_text=p['name'],
                    is_primary=True,
                    order=0,
                )
                created_count += 1
                self.stdout.write(f"  + {p['name']}")
            else:
                self.stdout.write(f"  = {p['name']} (already exists)")

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {created_count} products created across {len(CATEGORIES)} categories.'
        ))
