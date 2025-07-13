from django.urls import path
from . import views

app_name = 'comprobantes'

urlpatterns = [
    # Endpoint para validar datos JSON
    path('validate/', views.validate_comprobante, name='validate'),
    
    # Endpoint para convertir JSON a XML UBL 2.1
    path('convert/', views.convert_to_xml, name='convert'),
    
    # Endpoint para obtener archivo XML por nombre
    path('xml/<str:nombre_xml>/', views.get_xml_file, name='get_xml'),
] 