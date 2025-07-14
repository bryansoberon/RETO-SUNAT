"""
URL configuration for sunat_api project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from comprobantes.views import frontend_view

urlpatterns = [
    path('', frontend_view, name='frontend'),  # ← NUEVA RUTA PARA FRONTEND
    path('admin/', admin.site.urls),
    path('api/v1/', include('comprobantes.urls')),
    path('health/', include('comprobantes.urls_health')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)