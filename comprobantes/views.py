import os
import zipfile
from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework import status
import json
import logging

from .serializers import (
    ComprobanteInputSerializer, 
    ValidationResponseSerializer,
    ConversionResponseSerializer
)
from .models import Comprobante, DetalleComprobante
from .utils import (
    validate_comprobante_data,
    generate_ubl_xml,
    create_zip_file,
    validate_xml_structure,
    extraer_clave_certificado_pfx,
    firmar_xml_ubl
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@parser_classes([JSONParser])
def validate_comprobante(request):
    """
    Endpoint para validar datos JSON de comprobante electrónico
    POST /api/v1/validate/
    """
    try:
        # Validar datos de entrada
        serializer = ComprobanteInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Datos de entrada inválidos',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validaciones adicionales específicas de SUNAT
        validation_result = validate_comprobante_data(serializer.validated_data)
        
        if validation_result['success']:
            # Mapear datos del JSON al modelo
            data = serializer.validated_data
            
            # Guardar comprobante en estado PENDIENTE
            comprobante = Comprobante.objects.create(
                tipo_comprobante=data['tipoDocumento'],
                ruc_emisor=data['emisor']['ruc'],
                serie=data['serie'],
                numero=data['numero'],
                ruc_cliente=data['cliente']['numeroDoc'],
                nombre_cliente=data['cliente']['razonSocial'],
                direccion_cliente=data['cliente'].get('direccion', ''),
                total_gravado=data['totalGravado'],
                total_igv=data['totalIGV'],
                total=data['totalImportePagar'],
                estado='VALIDADO'
            )
            
            # Crear detalles del comprobante
            for item_data in data['items']:
                DetalleComprobante.objects.create(
                    comprobante=comprobante,
                    descripcion=item_data['descripcion'],
                    cantidad=item_data['cantidad'],
                    precio_unitario=item_data['valorUnitario'],
                    subtotal=item_data['valorTotal']
                )
            
            return Response({
                'success': True,
                'message': 'Comprobante validado correctamente',
                'comprobante_id': comprobante.id
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Error en validación SUNAT',
                'errors': validation_result['errors']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error en validación: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error interno del servidor',
            'errors': [str(e)]
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


CERT_PATH = os.path.join(settings.BASE_DIR, 'CERTIFICADO.pfx')
CERT_PASS = 'prueba123'

# Cargar clave y certificado una sola vez (cache)
PRIVATE_KEY = None
CERT = None

def get_cert_and_key():
    global PRIVATE_KEY, CERT
    if PRIVATE_KEY is None or CERT is None:
        PRIVATE_KEY, CERT = extraer_clave_certificado_pfx(CERT_PATH, CERT_PASS)
    return PRIVATE_KEY, CERT

@api_view(['POST'])
@parser_classes([JSONParser])
def convert_to_xml(request):
    """
    Endpoint para convertir JSON a XML UBL 2.1, firmar y generar ZIP
    POST /api/v1/convert/
    """
    try:
        # Validar datos de entrada
        serializer = ComprobanteInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Datos de entrada inválidos',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Buscar o crear comprobante
        comprobante, created = Comprobante.objects.get_or_create(
            tipo_comprobante=serializer.validated_data['tipoDocumento'],
            ruc_emisor=serializer.validated_data['emisor']['ruc'],
            serie=serializer.validated_data['serie'],
            numero=serializer.validated_data['numero'],
            defaults={
                'ruc_cliente': serializer.validated_data['cliente']['numeroDoc'],
                'nombre_cliente': serializer.validated_data['cliente']['razonSocial'],
                'direccion_cliente': serializer.validated_data['cliente']['direccion'],
                'total_gravado': serializer.validated_data['totalGravado'],
                'total_igv': serializer.validated_data['totalIGV'],
                'total': serializer.validated_data['totalImportePagar'],
                'estado': 'PENDIENTE'
            }
        )
        
        # Generar XML UBL 2.1
        xml_content = generate_ubl_xml(serializer.validated_data)

        # Firmar el XML
        private_key, cert = get_cert_and_key()
        xml_firmado = firmar_xml_ubl(xml_content, private_key, cert)
        
        # Validar estructura XML
        xml_validation = validate_xml_structure(xml_firmado)
        if not xml_validation['success']:
            comprobante.estado = 'ERROR'
            comprobante.errores = json.dumps(xml_validation['errors'])
            comprobante.save()
            return Response({
                'success': False,
                'message': 'Error en estructura XML',
                'errors': xml_validation['errors']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Guardar archivo XML firmado
        xml_filename = comprobante.get_xml_filename()
        xml_path = os.path.join(settings.SUNAT_CONFIG['XML_OUTPUT_DIR'], xml_filename)
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_firmado)
        
        # Crear archivo ZIP
        zip_filename = comprobante.get_zip_filename()
        zip_path = os.path.join(settings.SUNAT_CONFIG['ZIP_OUTPUT_DIR'], zip_filename)
        create_zip_file(xml_path, zip_path)
        
        # Actualizar modelo
        comprobante.xml_file = f'xml/{xml_filename}'
        comprobante.zip_file = f'zip/{zip_filename}'
        comprobante.estado = 'GENERADO'
        comprobante.save()
        
        return Response({
            'success': True,
            'message': 'Comprobante convertido, firmado y empaquetado correctamente',
            'xml_filename': xml_filename,
            'zip_filename': zip_filename,
            'comprobante_id': comprobante.id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error en conversión: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error interno del servidor',
            'errors': [str(e)]
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_xml_file(request, nombre_xml):
    """
    Endpoint para obtener archivo XML por nombre
    GET /api/v1/xml/<nombre_xml>/
    """
    try:
        # Buscar el archivo XML
        xml_path = os.path.join(settings.SUNAT_CONFIG['XML_OUTPUT_DIR'], nombre_xml)
        
        if not os.path.exists(xml_path):
            raise Http404("Archivo XML no encontrado")
        
        # Retornar archivo
        response = FileResponse(
            open(xml_path, 'rb'),
            content_type='application/xml'
        )
        response['Content-Disposition'] = f'attachment; filename="{nombre_xml}"'
        return response
        
    except Http404:
        return Response({
            'success': False,
            'message': 'Archivo XML no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error al obtener XML: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error interno del servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def health_check(request):
    """
    Endpoint de salud del sistema
    GET /health/
    """
    try:
        # Verificar conexión a base de datos
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return Response({
            'success': True,
            'message': 'API SUNAT funcionando correctamente',
            'status': 'healthy',
            'version': '1.0.0'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error en health check: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error en el sistema',
            'status': 'unhealthy',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 