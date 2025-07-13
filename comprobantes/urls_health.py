from django.urls import path
from . import views

urlpatterns = [
    # Endpoint de salud del sistema
    path('', views.health_check, name='health'),
] 