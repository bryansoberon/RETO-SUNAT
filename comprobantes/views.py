# comprobantes/views.py

import os
import traceback
from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework import status
import json
import logging

from .serializers import (
    ComprobanteInputSerializer, 
)
from .models import Comprobante, DetalleComprobante
from .utils import (
    validate_comprobante_data,
    generate_ubl_xml,
    create_zip_file,
    validate_xml_structure,
    SIGNING_AVAILABLE
)

if SIGNING_AVAILABLE:
    from .utils import firmar_xml_ubl

logger = logging.getLogger(__name__)

def frontend_view(request):
    """Vista para servir el frontend HTML"""
    return render(request, 'index.html')

@api_view(['POST'])
def validate_comprobante(request):
    """Endpoint para validar datos JSON de comprobante electrónico"""
    try:
        print("🔍 Datos recibidos para validación:")
        print(json.dumps(request.data, indent=2, default=str))
        serializer = ComprobanteInputSerializer(data=request.data)
        if not serializer.is_valid():
            print("❌ Errores de serializer:")
            print(serializer.errors)
            return Response({
                'success': False,
                'message': 'Datos de entrada inválidos',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        validation_result = validate_comprobante_data(serializer.validated_data)
        if validation_result['success']:
            data = serializer.validated_data
            try:
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
                for item_data in data['items']:
                    DetalleComprobante.objects.create(
                        comprobante=comprobante,
                        descripcion=item_data['descripcion'],
                        cantidad=item_data['cantidad'],
                        precio_unitario=item_data['valorUnitario'],
                        subtotal=item_data['valorTotal']
                    )
                print(f"✅ Comprobante validado y guardado con ID: {comprobante.id}")
                return Response({
                    'success': True,
                    'message': 'Comprobante validado correctamente',
                    'comprobante_id': comprobante.id
                }, status=status.HTTP_200_OK)
            except Exception as db_error:
                print(f"❌ Error de base de datos: {str(db_error)}")
                return Response({
                    'success': False,
                    'message': 'Error al guardar en base de datos',
                    'errors': [str(db_error)]
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'success': False,
                'message': 'Error en validación SUNAT',
                'errors': validation_result['errors']
            }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(f"❌ Error general en validación: {str(e)}")
        traceback.print_exc()
        return Response({
            'success': False,
            'message': 'Error interno del servidor',
            'errors': [str(e)]
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@parser_classes([JSONParser])
def convert_to_xml(request):
    """Endpoint para convertir JSON a XML UBL 2.1 y generar ZIP"""
    try:
        print("🔍 Datos recibidos para conversión:")
        print(json.dumps(request.data, indent=2, default=str))
        serializer = ComprobanteInputSerializer(data=request.data)
        if not serializer.is_valid():
            print("❌ Errores de serializer en conversión:")
            print(serializer.errors)
            return Response({
                'success': False,
                'message': 'Datos de entrada inválidos',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            comprobante, created = Comprobante.objects.get_or_create(
                tipo_comprobante=serializer.validated_data['tipoDocumento'],
                ruc_emisor=serializer.validated_data['emisor']['ruc'],
                serie=serializer.validated_data['serie'],
                numero=serializer.validated_data['numero'],
                defaults={
                    'ruc_cliente': serializer.validated_data['cliente']['numeroDoc'],
                    'nombre_cliente': serializer.validated_data['cliente']['razonSocial'],
                    'direccion_cliente': serializer.validated_data['cliente'].get('direccion', ''),
                    'total_gravado': serializer.validated_data['totalGravado'],
                    'total_igv': serializer.validated_data['totalIGV'],
                    'total': serializer.validated_data['totalImportePagar'],
                    'estado': 'PENDIENTE'
                }
            )
            print(f"📋 Comprobante {'creado' if created else 'encontrado'} con ID: {comprobante.id}")
        except Exception as db_error:
            print(f"❌ Error de base de datos: {str(db_error)}")
            return Response({
                'success': False,
                'message': 'Error al acceder a la base de datos',
                'errors': [str(db_error)]
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            print("🔧 Generando XML UBL 2.1...")
            xml_content = generate_ubl_xml(serializer.validated_data)
            print(f"✅ XML generado correctamente ({len(xml_content)} caracteres)")
        except Exception as xml_error:
            print(f"❌ Error al generar XML: {str(xml_error)}")
            traceback.print_exc()
            comprobante.estado = 'ERROR'
            comprobante.errores = f"Error generando XML: {str(xml_error)}"
            comprobante.save()
            return Response({
                'success': False,
                'message': 'Error al generar XML',
                'errors': [str(xml_error)]
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            print("🔍 Validando estructura XML...")
            xml_validation = validate_xml_structure(xml_content)
            if not xml_validation['success']:
                print(f"❌ XML inválido: {xml_validation['errors']}")
                comprobante.estado = 'ERROR'
                comprobante.errores = json.dumps(xml_validation['errors'])
                comprobante.save()
                return Response({
                    'success': False,
                    'message': 'Error en estructura XML',
                    'errors': xml_validation['errors']
                }, status=status.HTTP_400_BAD_REQUEST)
            print("✅ Estructura XML válida")
        except Exception as validation_error:
            print(f"❌ Error en validación XML: {str(validation_error)}")
            return Response({
                'success': False,
                'message': 'Error al validar XML',
                'errors': [str(validation_error)]
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        xml_firmado = xml_content
        try:
            if SIGNING_AVAILABLE:
                print("🔐 Procesando firma digital...")
                cert_path = os.path.join(settings.BASE_DIR, 'CERTIFICADO.pfx')
                cert_pass = 'prueba123'
                if os.path.exists(cert_path):
                    temp_xml_path = 'temp_para_firma.xml'
                    with open(temp_xml_path, 'w', encoding='utf-8') as f:
                        f.write(xml_content)
                    xml_firmado_bytes = firmar_xml_ubl(temp_xml_path, cert_path, cert_pass)
                    xml_firmado = xml_firmado_bytes.decode('utf-8')
                    print("✅ XML firmado correctamente")
                    print(f"🔍 Path archivo firmado: {temp_xml_path.replace('.xml', '_con_firma.xml')}")
                    print(f"🔍 Primeros 500 caracteres del XML firmado:\n{xml_firmado[:500]}")
                    if '<ds:Signature' not in xml_firmado:
                        print('⚠️  ADVERTENCIA: El XML firmado no contiene <ds:Signature>')
                else:
                    print("⚠️  Certificado no encontrado, continuando sin firma")
            else:
                print("⚠️  Librerías de firma no disponibles, continuando sin firma")
        except Exception as signing_error:
            print(f"⚠️  Error en firma digital (continuando sin firma): {str(signing_error)}")
            xml_firmado = xml_content
        try:
            xml_filename = comprobante.get_xml_filename()
            xml_path = os.path.join(settings.SUNAT_CONFIG['XML_OUTPUT_DIR'], xml_filename)
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(xml_firmado)
            print(f"📁 XML guardado: {xml_filename}")
        except Exception as file_error:
            print(f"❌ Error al guardar XML: {str(file_error)}")
            return Response({
                'success': False,
                'message': 'Error al guardar archivo XML',
                'errors': [str(file_error)]
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            zip_filename = comprobante.get_zip_filename()
            zip_path = os.path.join(settings.SUNAT_CONFIG['ZIP_OUTPUT_DIR'], zip_filename)
            if create_zip_file(xml_path, zip_path):
                print(f"📦 ZIP creado: {zip_filename}")
            else:
                print("⚠️  Error al crear ZIP (continuando)")
                zip_filename = None
        except Exception as zip_error:
            print(f"⚠️  Error al crear ZIP: {str(zip_error)}")
            zip_filename = None
        try:
            comprobante.xml_file = f'xml/{xml_filename}'
            if zip_filename:
                comprobante.zip_file = f'zip/{zip_filename}'
            comprobante.estado = 'GENERADO'
            comprobante.errores = None
            comprobante.save()
            print(f"✅ Comprobante actualizado en base de datos")
        except Exception as db_update_error:
            print(f"❌ Error al actualizar comprobante: {str(db_update_error)}")
        return Response({
            'success': True,
            'message': 'Comprobante convertido y empaquetado correctamente',
            'xml_filename': xml_filename,
            'zip_filename': zip_filename,
            'comprobante_id': comprobante.id
        }, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"❌ Error general en conversión: {str(e)}")
        traceback.print_exc()
        return Response({
            'success': False,
            'message': 'Error interno del servidor',
            'errors': [str(e)]
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_xml_file(request, nombre_xml):
    """Endpoint para obtener archivo XML por nombre"""
    try:
        xml_path = os.path.join(settings.SUNAT_CONFIG['XML_OUTPUT_DIR'], nombre_xml)
        if not os.path.exists(xml_path):
            print(f"❌ Archivo XML no encontrado: {xml_path}")
            raise Http404("Archivo XML no encontrado")
        print(f"📄 Sirviendo archivo XML: {nombre_xml}")
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
        print(f"❌ Error al obtener XML: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error interno del servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def health_check(request):
    """Endpoint de salud del sistema"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        xml_dir = settings.SUNAT_CONFIG['XML_OUTPUT_DIR']
        zip_dir = settings.SUNAT_CONFIG['ZIP_OUTPUT_DIR']
        xml_dir_exists = os.path.exists(xml_dir)
        zip_dir_exists = os.path.exists(zip_dir)
        if not xml_dir_exists:
            os.makedirs(xml_dir, exist_ok=True)
        if not zip_dir_exists:
            os.makedirs(zip_dir, exist_ok=True)
        status_info = {
            'database': 'OK',
            'xml_directory': 'OK' if xml_dir_exists else 'CREATED',
            'zip_directory': 'OK' if zip_dir_exists else 'CREATED',
            'signing_available': SIGNING_AVAILABLE
        }
        return Response({
            'success': True,
            'message': 'API SUNAT funcionando correctamente',
            'status': 'healthy',
            'version': '1.0.0',
            'details': status_info
        }, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"❌ Error en health check: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error en el sistema',
            'status': 'unhealthy',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'POST'])
def send_to_sunat(request, comprobante_id):
    return Response({"ok": True, "msg": "send_to_sunat placeholder"})

@api_view(['GET'])
def check_sunat_status(request, comprobante_id):
    return Response({"ok": True, "msg": "check_sunat_status placeholder"})

@api_view(['GET'])
def get_comprobante_status(request, comprobante_id):
    return Response({"ok": True, "msg": "get_comprobante_status placeholder"})

@api_view(['GET'])
def retry_sunat_send(request, comprobante_id):
    return Response({"ok": True, "msg": "retry_sunat_send placeholder"})

@api_view(['POST'])
def bulk_send_to_sunat(request):
    return Response({"ok": True, "msg": "bulk_send_to_sunat placeholder"})

@api_view(['GET'])
def check_pending_tickets(request):
    return Response({"ok": True, "msg": "check_pending_tickets placeholder"})

@api_view(['GET'])
def get_cdr_file(request, comprobante_id):
    return Response({"ok": True, "msg": "get_cdr_file placeholder"})

@api_view(['GET'])
def sunat_dashboard(request):
    return Response({"ok": True, "msg": "sunat_dashboard placeholder"})