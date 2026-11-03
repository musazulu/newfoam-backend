# products/views.py
from rest_framework import viewsets, permissions, status, filters, serializers
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Category, Product, ProductReview, ProductLike
from .serializers import (
    CategorySerializer, ProductListSerializer, ProductDetailSerializer,
    ProductReviewSerializer, ProductLikeSerializer, ProductSearchSerializer
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_in_stock=True)
    permission_classes = [permissions.AllowAny]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['size', 'material', 'is_featured']
    search_fields = ['name', 'description', 'short_description']
    ordering_fields = ['price_usd', 'average_rating', 'created_at', 'total_sold']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        queryset = super().get_queryset()

        category_slug = self.request.query_params.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')

        if min_price:
            try:
                queryset = queryset.filter(price_usd__gte=float(min_price))
            except (ValueError, TypeError):
                pass

        if max_price:
            try:
                queryset = queryset.filter(price_usd__lte=float(max_price))
            except (ValueError, TypeError):
                pass

        rating = self.request.query_params.get('rating')
        if rating:
            try:
                queryset = queryset.filter(average_rating__gte=float(rating))
            except (ValueError, TypeError):
                pass

        featured = self.request.query_params.get('featured')
        if featured == 'true':
            queryset = queryset.filter(is_featured=True)

        search_query = self.request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(short_description__icontains=search_query)
            )

        return queryset

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        product = self.get_object()
        like, created = ProductLike.objects.get_or_create(
            user=request.user,
            product=product
        )

        if created:
            product.total_likes += 1
            product.save()
            return Response({'liked': True}, status=status.HTTP_201_CREATED)
        else:
            like.delete()
            product.total_likes = max(0, product.total_likes - 1)
            product.save()
            return Response({'liked': False}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        featured_products = self.get_queryset().filter(is_featured=True)[:8]
        serializer = self.get_serializer(featured_products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def sponsored(self, request):
        sponsored_products = self.get_queryset().filter(is_sponsored=True)[:4]
        serializer = self.get_serializer(sponsored_products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def search(self, request):
        serializer = ProductSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        queryset = self.get_queryset()
        data = serializer.validated_data

        if data.get('query'):
            queryset = queryset.filter(
                Q(name__icontains=data['query']) |
                Q(description__icontains=data['query']) |
                Q(short_description__icontains=data['query'])
            )

        if data.get('category'):
            queryset = queryset.filter(category__slug=data['category'])

        if data.get('min_price'):
            queryset = queryset.filter(price_usd__gte=data['min_price'])

        if data.get('max_price'):
            queryset = queryset.filter(price_usd__lte=data['max_price'])

        if data.get('rating'):
            queryset = queryset.filter(average_rating__gte=data['rating'])

        if data.get('size'):
            queryset = queryset.filter(size=data['size'])

        if data.get('material'):
            queryset = queryset.filter(material=data['material'])

        sort_by = data.get('sort_by', 'relevance')
        if sort_by == 'price_low_high':
            queryset = queryset.order_by('price_usd')
        elif sort_by == 'price_high_low':
            queryset = queryset.order_by('-price_usd')
        elif sort_by == 'rating':
            queryset = queryset.order_by('-average_rating')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'popular':
            queryset = queryset.order_by('-total_sold')

        page = data.get('page', 1)
        page_size = data.get('page_size', 20)
        start = (page - 1) * page_size
        end = start + page_size

        paginated_queryset = queryset[start:end]
        total_count = queryset.count()

        serializer = self.get_serializer(paginated_queryset, many=True, context={'request': request})

        return Response({
            'results': serializer.data,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size
        })


class ProductReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        product_pk = self.kwargs.get('pk')
        if product_pk:
            return ProductReview.objects.filter(product_id=product_pk, is_approved=True)
        return ProductReview.objects.filter(is_approved=True)

    def perform_create(self, serializer):
        product_pk = self.kwargs.get('pk')
        if not product_pk:
            raise serializers.ValidationError("Product ID is required")

        product = get_object_or_404(Product, pk=product_pk)

        if ProductReview.objects.filter(product=product, user=self.request.user).exists():
            raise serializers.ValidationError("You have already reviewed this product")

        serializer.save(product=product, user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def helpful(self, request, pk=None):
        review = self.get_object()
        if request.user != review.user:
            review.helpful_votes += 1
            review.save()
            return Response({'helpful_votes': review.helpful_votes})
        return Response({'error': 'Cannot vote on your own review'},
                       status=status.HTTP_400_BAD_REQUEST)


class AdminProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer