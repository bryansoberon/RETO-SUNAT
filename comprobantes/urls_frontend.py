from django.urls import path
from django.shortcuts import render

def frontend_view(request):
    """Vista para servir el frontend HTML"""
    return render(request, 'index.html')

urlpatterns = [
    path('', frontend_view, name='frontend'),
]