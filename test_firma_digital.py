#!/usr/bin/env python3
"""
Script de prueba para verificar la firma digital en XML UBL 2.1
"""

import sys
import os
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sunat_api.settings')
django.setup()

from comprobantes.utils import generate_ubl_xml, firmar_xml_ubl
from django.conf import settings

import os
from lxml import etree as LET

print('🧪 PRUEBA DE FIRMA DIGITAL XML UBL 2.1')
print('='*50)

xml_sin_firma = 'test_sin_firma.xml'
xml_con_firma = 'test_sin_firma_con_firma.xml'

# Paso 1: Generar XML sin firma (esto lo hace tu sistema normalmente)
print('🔧 Generando XML UBL 2.1...')
if not os.path.exists(xml_sin_firma):
    raise Exception('No existe test_sin_firma.xml')
print(f'✅ XML sin firma guardado como: {xml_sin_firma}')

# Paso 2: Firmar el XML automáticamente si no existe
if not os.path.exists(xml_con_firma):
    print('✍️ Firmando XML automáticamente...')
    cert_path = 'CERTIFICADO.pfx'
    cert_pass = 'prueba123'
    if not os.path.exists(cert_path):
        raise Exception(f'No existe el certificado: {cert_path}')
    firmar_xml_ubl(xml_sin_firma, cert_path, cert_pass)
    print(f'✅ XML firmado guardado como: {xml_con_firma}')

# Paso 3: Verificar la estructura y la firma
print('🔍 Verificando ubicación de la firma...')
parser = LET.XMLParser(remove_blank_text=True)
root = LET.parse(xml_con_firma, parser).getroot()
nsmap = {
    'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'ds': 'http://www.w3.org/2000/09/xmldsig#'
}
ublext = root.find('.//ext:UBLExtensions', namespaces=nsmap)
if ublext is None:
    print('❌ ERROR: No se encontró la estructura UBLExtensions')
    print('\n💥 RESULTADO: PRUEBA FALLIDA')
    exit(1)
ext_content = ublext.find('.//ext:ExtensionContent', namespaces=nsmap)
if ext_content is None:
    print('❌ ERROR: No se encontró ExtensionContent')
    print('\n💥 RESULTADO: PRUEBA FALLIDA')
    exit(1)
signature = ext_content.find('.//ds:Signature', namespaces=nsmap)
if signature is None:
    print('❌ ERROR: No se encontró la firma digital en ExtensionContent')
    print('\n💥 RESULTADO: PRUEBA FALLIDA')
    exit(1)
print('✅ Firma digital encontrada en el lugar correcto')

# Validar prefijos y namespaces
if not signature.tag.endswith('Signature') or not signature.prefix == 'ds':
    print('❌ ERROR: El prefijo o namespace de la firma no es ds:')
    print(f'  Tag: {signature.tag}, Prefix: {signature.prefix}')
    print('\n💥 RESULTADO: PRUEBA FALLIDA')
    exit(1)
print('✅ Prefijo y namespace de la firma correctos (ds:)')

print('\n🎉 RESULTADO: PRUEBA EXITOSA') 