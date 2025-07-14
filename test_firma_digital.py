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

from comprobantes.utils import generate_ubl_xml, extraer_clave_certificado_pfx, firmar_xml_ubl
from django.conf import settings

def test_firma_digital():
    """Probar la firma digital en XML UBL 2.1"""
    
    # Datos de prueba
    from datetime import datetime
    
    test_data = {
        'serie': 'F001',
        'numero': '123',
        'tipoDocumento': '01',
        'moneda': 'PEN',
        'fechaEmision': datetime.strptime('2025-07-13', '%Y-%m-%d'),
        'horaEmision': datetime.strptime('00:00:00', '%H:%M:%S'),
        'formaPago': 'Contado',
        'totalGravado': 156.78,
        'totalIGV': 28.22,
        'totalImportePagar': 185.00,
        'emisor': {
            'ruc': '20607599727',
            'razonSocial': 'INSTITUTO INTERNACIONAL DE SOFTWARE S.A.C.',
            'ubigeo': '140101',
            'distrito': 'LAMBAYEQUE',
            'provincia': 'LAMBAYEQUE',
            'direccion': '8 DE OCTUBRE N 123 - LAMBAYEQUE - LAMBAYEQUE - LAMBAYEQUE',
            'codigoPais': 'PE'
        },
        'cliente': {
            'numeroDoc': '20605145648',
            'razonSocial': 'AGROINVERSIONES Y SERVICIOS AJINOR S.R.L. - AGROSERVIS AJINOR S.R.L.',
            'direccion': 'MZA. C LOTE. 46 URB. SAN ISIDRO LA LIBERTAD - TRUJILLO - TRUJILLO'
        },
        'items': [
            {
                'id': 1,
                'cantidad': 1,
                'unidadMedida': 'NIU',
                'descripcion': 'FENA X L',
                'valorUnitario': 156.78,
                'valorTotal': 156.78,
                'precioVentaUnitario': 185.00,
                'igv': 28.22,
                'porcentajeIGV': 18,
                'tipoAfectacionIGV': '10',
                'codigoProducto': '195',
                'unspsc': '10191509'
            }
        ]
    }
    
    try:
        print("🔧 Generando XML UBL 2.1...")
        xml_content = generate_ubl_xml(test_data)
        
        # Guardar XML sin firma
        with open('test_sin_firma.xml', 'w', encoding='utf-8') as f:
            f.write(xml_content)
        print("✅ XML sin firma guardado como: test_sin_firma.xml")
        
        # Verificar que no hay firma digital
        if '<ds:Signature' in xml_content:
            print("❌ ERROR: El XML sin firma contiene elementos de firma digital")
            return False
        else:
            print("✅ XML sin firma digital (correcto)")
        
        # Extraer certificado y clave
        print("\n🔐 Extrayendo certificado y clave...")
        cert_path = os.path.join(settings.BASE_DIR, 'CERTIFICADO.pfx')
        cert_pass = 'prueba123'
        
        if not os.path.exists(cert_path):
            print(f"❌ ERROR: No se encuentra el certificado en {cert_path}")
            return False
        
        private_key, cert = extraer_clave_certificado_pfx(cert_path, cert_pass)
        print("✅ Certificado y clave extraídos correctamente")
        
        # Firmar el XML
        print("\n✍️ Firmando XML...")
        xml_firmado = firmar_xml_ubl(xml_content, private_key, cert)
        
        # Guardar XML firmado
        with open('test_con_firma.xml', 'w', encoding='utf-8') as f:
            f.write(xml_firmado)
        print("✅ XML firmado guardado como: test_con_firma.xml")
        
        # Verificar que la firma está en el lugar correcto
        print("\n🔍 Verificando ubicación de la firma...")
        
        # Verificar que hay firma digital
        if '<ds:Signature' not in xml_firmado:
            print("❌ ERROR: El XML firmado no contiene firma digital")
            return False
        
        # Verificar que la firma está dentro de UBLExtensions
        if '<ext:UBLExtensions>' in xml_firmado and '<ds:Signature' in xml_firmado:
            # Buscar la posición de UBLExtensions y Signature
            ubl_pos = xml_firmado.find('<ext:UBLExtensions>')
            sig_pos = xml_firmado.find('<ds:Signature')
            
            if sig_pos > ubl_pos:
                print("✅ La firma digital está dentro de UBLExtensions (correcto)")
            else:
                print("❌ ERROR: La firma digital no está dentro de UBLExtensions")
                return False
        else:
            print("❌ ERROR: No se encontró la estructura UBLExtensions o firma")
            return False
        
        # Verificar estructura específica de SUNAT
        if '<ext:UBLExtension>' in xml_firmado and '<ext:ExtensionContent>' in xml_firmado:
            print("✅ Estructura UBLExtension/ExtensionContent presente (correcto)")
        else:
            print("❌ ERROR: Falta estructura UBLExtension/ExtensionContent")
            return False
        
        # Verificar que no hay elementos Signature duplicados (usando lxml)
        from lxml import etree
        root = etree.fromstring(xml_firmado.encode('utf-8'))
        ns = root.nsmap.copy()
        ns['ds'] = ns.get('ds', 'http://www.w3.org/2000/09/xmldsig#')
        ns['ext'] = ns.get('ext', 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2')
        signatures = root.findall('.//ds:Signature', namespaces=ns)
        print(f"🔍 Nodos <ds:Signature> encontrados: {len(signatures)}")
        
        if len(signatures) == 1:
            print("✅ Solo hay un nodo <ds:Signature> (correcto)")
        else:
            print(f"❌ ERROR: Se encontraron {len(signatures)} nodos <ds:Signature> (debería ser 1)")
            return False
        
        # Verificar que la firma está dentro de <ext:ExtensionContent>
        signature = signatures[0]
        parent = signature.getparent()
        if parent.tag.endswith('ExtensionContent'):
            print("✅ La firma está dentro de <ext:ExtensionContent> (correcto)")
        else:
            print(f"❌ ERROR: La firma no está dentro de <ext:ExtensionContent>, sino en: {parent.tag}")
            return False
        
        print("\n🎉 ¡PRUEBA EXITOSA! La firma digital se coloca correctamente")
        print("\n📋 Resumen:")
        print("   ✅ XML generado sin firma digital")
        print("   ✅ Certificado y clave extraídos")
        print("   ✅ XML firmado correctamente")
        print("   ✅ Firma colocada en UBLExtensions")
        print("   ✅ Estructura UBLExtension/ExtensionContent correcta")
        print("   ✅ Solo una firma digital presente")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba de firma digital: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🧪 PRUEBA DE FIRMA DIGITAL XML UBL 2.1")
    print("=" * 50)
    
    success = test_firma_digital()
    
    if success:
        print("\n🎯 RESULTADO: PRUEBA EXITOSA")
        sys.exit(0)
    else:
        print("\n💥 RESULTADO: PRUEBA FALLIDA")
        sys.exit(1) 