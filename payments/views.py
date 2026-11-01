from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.conf import settings
from django.shortcuts import get_object_or_404
from .models import Payment, Refund
from .serializers import (
    PaymentSerializer, CreatePaymentSerializer, EcoCashPaymentSerializer,
    OneMoneyPaymentSerializer, BankTransferPaymentSerializer, CardPaymentSerializer,
    RefundSerializer
)
from orders.models import Order

class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(user=user)
    
    def create(self, request):
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order = get_object_or_404(Order, id=serializer.validated_data['order_id'], user=request.user)
        
        if order.status != 'pending_payment':
            return Response(
                {'error': 'Order is not in pending payment status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment_method = serializer.validated_data['payment_method']
        
        # Create payment record
        payment = Payment.objects.create(
            order=order,
            user=request.user,
            amount=order.total_amount,
            currency=order.currency,
            payment_method=payment_method,
            status='pending'
        )
        
        # Process based on payment method
        if payment_method in ['ecocash', 'onemoney']:
            phone_number = serializer.validated_data.get('phone_number')
            if not phone_number:
                return Response(
                    {'error': 'Phone number required for mobile money payments'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            payment.phone_number = phone_number
            payment.save()
            
            # TODO: Integrate with EcoCash/OneMoney API
            # For now, simulate successful payment
            payment.status = 'completed'
            payment.payment_reference = f"MM-{payment.id.hex[:8].upper()}"
            payment.save()
            
            # Update order status
            order.status = 'paid'
            order.payment_status = 'completed'
            order.payment_reference = payment.payment_reference
            order.save()
            
            return Response(PaymentSerializer(payment).data)
        
        elif payment_method == 'bank_transfer':
            # For bank transfer, payment remains pending until confirmed
            payment.save()
            return Response({
                'payment': PaymentSerializer(payment).data,
                'message': 'Please complete the bank transfer and upload proof',
                'bank_details': {
                    'bank_name': 'CBZ Bank',
                    'account_name': 'Bedding Company Zimbabwe',
                    'account_number': '1234567890',
                    'branch': 'Harare Main Branch',
                    'reference': f"ORDER-{order.order_number}"
                }
            })
        
        elif payment_method == 'card':
            token = serializer.validated_data.get('token')
            if not token:
                return Response(
                    {'error': 'Card token required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                import stripe
                stripe.api_key = settings.STRIPE_SECRET_KEY

                # Create Stripe charge
                charge = stripe.Charge.create(
                    amount=int(order.total_amount * 100),  # Convert to cents
                    currency=order.currency.lower(),
                    source=token,
                    description=f"Order {order.order_number}",
                    metadata={
                        'order_id': str(order.id),
                        'order_number': order.order_number
                    }
                )
                
                payment.status = 'completed'
                payment.transaction_id = charge.id
                payment.payment_reference = charge.id
                payment.card_last_four = charge.source.last4
                payment.card_brand = charge.source.brand
                payment.save()
                
                # Update order
                order.status = 'paid'
                order.payment_status = 'completed'
                order.payment_reference = charge.id
                order.save()
                
                return Response(PaymentSerializer(payment).data)
                
            except stripe.error.StripeError as e:
                payment.status = 'failed'
                payment.save()
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                payment.status = 'failed'
                payment.save()
                return Response(
                    {'error': f'Payment processing error: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(
            {'error': 'Invalid payment method'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def refund(self, request, pk=None):
        payment = self.get_object()
        
        if payment.status != 'completed':
            return Response(
                {'error': 'Payment must be completed to issue refund'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        refund_amount = request.data.get('amount', payment.amount)
        reason = request.data.get('reason', '')
        
        refund = Refund.objects.create(
            payment=payment,
            amount=refund_amount,
            currency=payment.currency,
            reason=reason,
            processed_by=request.user
        )
        
        # TODO: Process refund through payment gateway
        refund.status = 'completed'
        refund.refund_reference = f"REF-{refund.id.hex[:8].upper()}"
        refund.save()
        
        # Update order status
        payment.order.status = 'refunded'
        payment.order.save()
        
        return Response(RefundSerializer(refund).data)

class PaymentWebhookView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # TODO: Implement webhook handling for different payment gateways
        payload = request.data
        payment_gateway = request.headers.get('X-Payment-Gateway', 'unknown')
        
        # Store webhook for processing
        from .models import PaymentWebhook
        webhook = PaymentWebhook.objects.create(
            payment_gateway=payment_gateway,
            event_type=payload.get('event_type', 'unknown'),
            payload=payload
        )
        
        # Process webhook based on gateway
        if payment_gateway == 'stripe':
            self._process_stripe_webhook(webhook, payload)
        elif payment_gateway in ['ecocash', 'onemoney']:
            self._process_mobile_money_webhook(webhook, payload)
        
        return Response({'received': True})

    def _process_stripe_webhook(self, webhook, payload):
        # Process Stripe webhook
        event_type = payload.get('type')
        
        if event_type == 'charge.succeeded':
            charge_id = payload['data']['object']['id']
            try:
                payment = Payment.objects.get(transaction_id=charge_id)
                payment.status = 'completed'
                payment.payment_date = payload['created']
                payment.save()
                
                # Update order
                payment.order.status = 'paid'
                payment.order.payment_status = 'completed'
                payment.order.save()
                
                webhook.is_processed = True
                webhook.save()
                
            except Payment.DoesNotExist:
                webhook.processing_error = f"Payment not found for charge: {charge_id}"
                webhook.save()
        
        elif event_type == 'charge.refunded':
            # Handle refunds
            pass

    def _process_mobile_money_webhook(self, webhook, payload):
        # Process mobile money webhook
        # This would integrate with EcoCash/OneMoney APIs
        pass