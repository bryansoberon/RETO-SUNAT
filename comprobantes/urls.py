from django.urls import path
from . import views

app_name = 'comprobantes'

urlpatterns = [
    # Endpoints originales
    path('validate/', views.validate_comprobante, name='validate'),
    path('convert/', views.convert_to_xml, name='convert'),
    path('xml/<str:nombre_xml>/', views.get_xml_file, name='get_xml'),
    
    # Endpoints SUNAT
    path('send-to-sunat/<int:comprobante_id>/', views.send_to_sunat, name='send_to_sunat'),
    path('check-sunat-status/<int:comprobante_id>/', views.check_sunat_status, name='check_sunat_status'),
    path('comprobante-status/<int:comprobante_id>/', views.get_comprobante_status, name='comprobante_status'),
    path('retry-sunat/<int:comprobante_id>/', views.retry_sunat_send, name='retry_sunat'),
    path('bulk-send-sunat/', views.bulk_send_to_sunat, name='bulk_send_sunat'),
    path('check-pending-tickets/', views.check_pending_tickets, name='check_pending_tickets'),
    path('cdr/<int:comprobante_id>/', views.get_cdr_file, name='get_cdr'),
    path('sunat-dashboard/', views.sunat_dashboard, name='sunat_dashboard'),
]