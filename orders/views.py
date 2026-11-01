from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db import transaction, models
from decimal import Decimal
from .models import Order, OrderItem, DeliveryZone
from .serializers import (
    OrderSerializer, CreateOrderSerializer, OrderStatusUpdateSerializer,
    DeliveryZoneSerializer, DeliveryFeeSerializer, CartSerializer
)
from products.models import Product

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=user)
    
    def create(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            # Calculate subtotal and create order items
            items_data = serializer.validated_data['items']
            subtotal = Decimal('0.00')
            order_items = []
            
            for item_data in items_data:
                product = get_object_or_404(Product, id=item_data['product_id'])
                
                # Check stock
                if product.stock_quantity < item_data['quantity']:
                    return Response(
                        {'error': f'Insufficient stock for {product.name}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Calculate item total
                unit_price = product.discounted_price_usd
                item_total = unit_price * item_data['quantity']
                subtotal += item_total
                
                # Create order item
                order_item = OrderItem(
                    product=product,
                    product_name=product.name,
                    sku=product.sku,
                    quantity=item_data['quantity'],
                    unit_price=unit_price,
                    total_price=item_total,
                    product_image=product.images.filter(is_primary=True).first().image.url if product.images.filter(is_primary=True).exists() else '',
                    product_size=product.size,
                    product_material=product.material
                )
                order_items.append(order_item)
                
                # Update product stock
                product.stock_quantity -= item_data['quantity']
                product.total_sold += item_data['quantity']
                product.save()
            
            # Calculate delivery fee
            try:
                delivery_zone = DeliveryZone.objects.get(
                    city=serializer.validated_data['city'],
                    province=serializer.validated_data.get('province', '')
                )
                delivery_fee = delivery_zone.delivery_fee
            except DeliveryZone.DoesNotExist:
                delivery_fee = Decimal('15.00')  # Default fee
            
            # Create order
            order = Order.objects.create(
                user=request.user,
                customer_name=serializer.validated_data.get('customer_name', request.user.get_full_name()),
                customer_email=serializer.validated_data.get('customer_email', request.user.email),
                customer_phone=serializer.validated_data.get('customer_phone', ''),
                delivery_address=serializer.validated_data['delivery_address'],
                city=serializer.validated_data['city'],
                town=serializer.validated_data.get('town', ''),
                postal_code=serializer.validated_data.get('postal_code', ''),
                delivery_instructions=serializer.validated_data.get('delivery_instructions', ''),
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                tax_amount=Decimal('0.00'),  # No tax for now
                total_amount=subtotal + delivery_fee,
                payment_method=serializer.validated_data['payment_method'],
                payment_status='pending'
            )
            
            # Save order items
            for order_item in order_items:
                order_item.order = order
                order_item.save()
        
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def update_status(self, request, pk=None):
        order = self.get_object()
        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        new_status = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')
        
        # Create status history
        order.status_history.create(
            old_status=order.status,
            new_status=new_status,
            notes=notes,
            changed_by=request.user
        )
        
        # Update order status
        order.status = new_status
        order.save()
        
        # TODO: Send notification to customer
        
        return Response(OrderSerializer(order).data)

class DeliveryZoneViewSet(viewsets.ModelViewSet):
    queryset = DeliveryZone.objects.filter(is_active=True)
    serializer_class = DeliveryZoneSerializer
    permission_classes = [permissions.IsAdminUser]
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def calculate_fee(self, request):
        serializer = DeliveryFeeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        return Response({
            'delivery_fee': str(data['delivery_fee']),
            'estimated_days_min': data['estimated_days_min'],
            'estimated_days_max': data['estimated_days_max']
        })

class CartView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CartSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        items_data = serializer.validated_data['items']
        cart_items = []
        subtotal = Decimal('0.00')
        
        for item_data in items_data:
            product = get_object_or_404(Product, id=item_data['product_id'])
            
            item_total = product.discounted_price_usd * item_data['quantity']
            subtotal += item_total
            
            cart_items.append({
                'product_id': str(product.id),
                'product_name': product.name,
                'sku': product.sku,
                'quantity': item_data['quantity'],
                'unit_price': str(product.discounted_price_usd),
                'total_price': str(item_total),
                'image': product.images.filter(is_primary=True).first().image.url if product.images.filter(is_primary=True).exists() else None,
                'stock_quantity': product.stock_quantity,
                'is_in_stock': product.is_in_stock
            })
        
        return Response({
            'items': cart_items,
            'subtotal': str(subtotal),
            'item_count': len(cart_items)
        })

class OrderStatsView(generics.GenericAPIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        from datetime import datetime, timedelta
        
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        stats = {
            'today': {
                'orders': Order.objects.filter(created_at__date=today).count(),
                'revenue': Order.objects.filter(created_at__date=today, status='delivered').aggregate(
                    total=models.Sum('total_amount')
                )['total'] or Decimal('0.00')
            },
            'this_week': {
                'orders': Order.objects.filter(created_at__date__gte=week_ago).count(),
                'revenue': Order.objects.filter(created_at__date__gte=week_ago, status='delivered').aggregate(
                    total=models.Sum('total_amount')
                )['total'] or Decimal('0.00')
            },
            'this_month': {
                'orders': Order.objects.filter(created_at__date__gte=month_ago).count(),
                'revenue': Order.objects.filter(created_at__date__gte=month_ago, status='delivered').aggregate(
                    total=models.Sum('total_amount')
                )['total'] or Decimal('0.00')
            },
            'total_orders': Order.objects.count(),
            'total_revenue': Order.objects.filter(status='delivered').aggregate(
                total=models.Sum('total_amount')
            )['total'] or Decimal('0.00')
        }
        
        return Response(stats)