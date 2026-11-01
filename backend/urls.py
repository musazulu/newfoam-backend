# backend/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

admin.site.site_header = "BeddingZim Admin"
admin.site.site_title = "BeddingZim"
admin.site.index_title = "Welcome to BeddingZim Dashboard"

schema_view = get_schema_view(
    openapi.Info(
        title="Bedding E-commerce API",
        default_version='v1',
        description="API for Zimbabwe Bedding E-commerce Platform",
        contact=openapi.Contact(email="support@bedding.co.zw"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

def health_check(request):
    return JsonResponse({'status': 'ok', 'message': 'BeddingZim API is running'})

urlpatterns = [
    path('', health_check, name='health-check'),
    path('admin/', admin.site.urls),
    path('api/', include([
        path('', include('accounts.urls')),
        path('', include('products.urls')),
        path('orders/', include('orders.urls')),
        path('payments/', include('payments.urls')),
        path('dashboard/', include('dashboard.urls')),
    ])),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
