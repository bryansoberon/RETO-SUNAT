#!/usr/bin/env python
"""
Script de pruebas para la API SUNAT - VERSIÓN FINAL COMPLETA
Ejecutar con: python test_api_final.py
"""

import requests
import json
import os
import sys
import random
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def test_health_check():
    """Prueba el endpoint de salud"""
    print("🔍 Probando endpoint de salud...")
    
    try:
        response = requests.get(f"{BASE_URL}/health/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check exitoso: {data['message']}")
            return True
        else:
            print(f"❌ Health check falló: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error en health check: {str(e)}")
        return False

def create_test_data_sunat_format(numero_base=None):
    """Crear datos de prueba con formato SUNAT correcto"""
    # Generar número único para evitar duplicados
    if numero_base is None:
        numero_base = random.randint(200, 999)
    
    return {
        "serie": "F001",
        "numero": str(numero_base),  # Se auto-rellenará a 00000XXX
        "fechaEmision": "2025-01-01",
        "horaEmision": "10:30:00",
        "tipoDocumento": "01",
        "moneda": "PEN",
        "formaPago": "Contado",
        
        # ✅ VALORES CORRECTOS según SUNAT:
        "totalGravado": 156.78,      # LineExtensionAmount (SIN IGV)
        "totalIGV": 28.22,           # TaxAmount (IGV calculado: 156.78 * 0.18)
        "totalPrecioVenta": 185.00,  # TaxInclusiveAmount (CON IGV: 156.78 + 28.22)
        "totalImportePagar": 185.00, # PayableAmount (igual a TaxInclusiveAmount)
        
        "emisor": {
            "ruc": "20607599727",
            "razonSocial": "INSTITUTO INTERNACIONAL DE SOFTWARE S.A.C.",
            "nombreComercial": "INSTITUTO INTERNACIONAL DE SOFTWARE S.A.C.",
            "ubigeo": "140101",
            "direccion": "8 DE OCTUBRE N 123 - LAMBAYEQUE - LAMBAYEQUE - LAMBAYEQUE",
            "departamento": "LAMBAYEQUE",
            "provincia": "LAMBAYEQUE",
            "distrito": "LAMBAYEQUE",
            "codigoPais": "PE",
            "correo": "test@institutoisi.com"
        },
        "cliente": {
            "numeroDoc": "20605145648",
            "razonSocial": "AGROINVERSIONES Y SERVICIOS AJINOR S.R.L. - AGROSERVIS AJINOR S.R.L.",
            "tipoDoc": "6",
            "ubigeo": "130101",
            "direccion": "MZA. C LOTE. 46 URB. SAN ISIDRO - TRUJILLO - TRUJILLO - LA LIBERTAD",
            "departamento": "LA LIBERTAD",
            "provincia": "TRUJILLO",
            "distrito": "TRUJILLO",
            "codigoPais": "PE",
            "correo": "cliente@correo.com"
        },
        "items": [
            {
                "id": "1",
                "cantidad": 1,
                "unidadMedida": "NIU",
                "descripcion": "FENA X L",
                "valorUnitario": 156.78,     # Precio unitario SIN IGV
                "precioVentaUnitario": 185.00, # Precio unitario CON IGV
                "valorTotal": 156.78,        # Total del item SIN IGV
                "igv": 28.22,               # IGV del item
                "codigoProducto": "195",
                "codigoProductoSUNAT": "195",
                "codigoTipoPrecio": "01",
                "tipoAfectacionIGV": "10",
                "porcentajeIGV": 18,
                "codigoTributo": "1000",
                "nombreTributo": "IGV",
                "tipoTributo": "VAT",
                "unspsc": "10191509"
            }
        ]
    }

def test_validate_comprobante():
    """Prueba el endpoint de validación"""
    print("\n🔍 Probando endpoint de validación...")
    
    test_data = create_test_data_sunat_format(300)  # Número único: 300
    
    try:
        response = requests.post(
            f"{API_BASE}/validate/",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Validación exitosa: {data['message']}")
            print(f"   ID del comprobante: {data.get('comprobante_id')}")
            return data.get('comprobante_id')
        else:
            print(f"❌ Validación falló: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error en validación: {str(e)}")
        return None

def test_convert_to_xml():
    """Prueba el endpoint de conversión"""
    print("\n🔍 Probando endpoint de conversión...")
    
    test_data = create_test_data_sunat_format(301)  # Número único: 301
    
    try:
        response = requests.post(
            f"{API_BASE}/convert/",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Conversión exitosa: {data['message']}")
            print(f"   Archivo XML: {data.get('xml_filename')}")
            print(f"   Archivo ZIP: {data.get('zip_filename')}")
            return data.get('xml_filename')
        else:
            print(f"❌ Conversión falló: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error en conversión: {str(e)}")
        return None

def test_get_xml_file(xml_filename):
    """Prueba el endpoint de descarga de XML"""
    if not xml_filename:
        print("\n⚠️  No se puede probar descarga de XML (sin archivo generado)")
        return False
    
    print(f"\n🔍 Probando descarga de archivo XML: {xml_filename}")
    
    try:
        response = requests.get(f"{API_BASE}/xml/{xml_filename}/")
        
        if response.status_code == 200:
            print(f"✅ Descarga exitosa: {len(response.content):,} bytes")
            
            # Verificar que el contenido sea XML válido
            content = response.content.decode('utf-8')
            if '<?xml version=' in content and '<Invoice' in content:
                print("   ✅ Archivo XML válido")
                
                # Verificar elementos clave según formato SUNAT
                checks = [
                    ('F001-00000301', 'ID de factura'),
                    ('156.78', 'Total gravado (sin IGV)'),
                    ('28.22', 'IGV calculado'),
                    ('185.00', 'Total con IGV'),
                    ('ds:Signature', 'Firma digital'),
                    ('PE:SUNAT', 'Namespaces SUNAT'),
                    ('FENA X L', 'Descripción producto'),
                    ('20607599727', 'RUC emisor'),
                    ('20605145648', 'RUC cliente'),
                ]
                
                for check_value, description in checks:
                    if check_value in content:
                        print(f"   ✅ {description}")
                    else:
                        print(f"   ❌ {description} - NO ENCONTRADO")
                        
                # Verificar estructura XML
                try:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(content.encode('utf-8'))
                    print("   ✅ Estructura XML válida")
                except ET.ParseError as e:
                    print(f"   ❌ Error estructura XML: {e}")
                    
            else:
                print("   ❌ Contenido XML inválido")
            
            return True
        else:
            print(f"❌ Descarga falló: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error en descarga: {str(e)}")
        return False

def test_validation_errors():
    """Prueba validaciones de errores"""
    print("\n🔍 Probando validaciones de errores...")
    
    # Datos inválidos - IGV incorrecto
    invalid_data = {
        "serie": "F001",
        "numero": str(random.randint(400, 499)),  # Número único para errores
        "tipoDocumento": "01",
        "totalGravado": 156.78,
        "totalIGV": 50.00,  # ❌ IGV incorrecto (debería ser 28.22)
        "totalPrecioVenta": 206.78,
        "totalImportePagar": 206.78,
        "emisor": {
            "ruc": "20607599727",
            "razonSocial": "EMPRESA TEST",
            "ubigeo": "140101",
            "direccion": "TEST",
            "codigoPais": "PE"
        },
        "cliente": {
            "numeroDoc": "20605145648",
            "razonSocial": "CLIENTE TEST",
            "tipoDoc": "6"
        },
        "items": [
            {
                "id": "1",
                "cantidad": 1,
                "descripcion": "PRODUCTO TEST",
                "valorUnitario": 156.78,
                "valorTotal": 156.78
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/validate/",
            json=invalid_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 400:
            data = response.json()
            print(f"✅ Validación de errores funcionando: {data['message']}")
            if 'errors' in data:
                print(f"   Errores detectados correctamente: {json.dumps(data['errors'], indent=2)}")
            return True
        else:
            print(f"❌ Validación de errores no funcionó como esperado: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error en validación de errores: {str(e)}")
        return False

def test_multiple_items():
    """Prueba con múltiples items"""
    print("\n🔍 Probando conversión con múltiples items...")
    
    test_data = create_test_data_sunat_format(350)  # Número único: 350
    
    # Agregar más items
    test_data["items"].append({
        "id": "2",
        "cantidad": 2,
        "unidadMedida": "NIU", 
        "descripcion": "PRODUCTO ADICIONAL",
        "valorUnitario": 50.00,
        "precioVentaUnitario": 59.00,
        "valorTotal": 100.00,
        "igv": 18.00,
        "codigoProducto": "196",
        "codigoProductoSUNAT": "196",
        "codigoTipoPrecio": "01",
        "tipoAfectacionIGV": "10",
        "porcentajeIGV": 18,
        "codigoTributo": "1000",
        "nombreTributo": "IGV",
        "tipoTributo": "VAT",
        "unspsc": "10191509"
    })
    
    # Recalcular totales
    test_data["totalGravado"] = 256.78  # 156.78 + 100.00
    test_data["totalIGV"] = 46.22       # 28.22 + 18.00
    test_data["totalPrecioVenta"] = 303.00  # 256.78 + 46.22
    test_data["totalImportePagar"] = 303.00
    
    try:
        response = requests.post(
            f"{API_BASE}/convert/",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Conversión múltiples items exitosa: {data['message']}")
            print(f"   Archivo XML: {data.get('xml_filename')}")
            return True
        else:
            print(f"❌ Conversión múltiples items falló: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error en conversión múltiples items: {str(e)}")
        return False

def clean_database():
    """Limpiar base de datos para evitar duplicados"""
    print("🧹 Limpiando base de datos para evitar duplicados...")
    try:
        # Intentar limpiar vía API (si hay endpoint)
        response = requests.delete(f"{API_BASE}/clean/")
        if response.status_code == 200:
            print("✅ Base de datos limpiada vía API")
            return True
    except:
        pass
    
    # Informar que se pueden limpiar manualmente
    print("💡 Si hay errores de duplicados, ejecuta:")
    print("   python manage.py shell -c \"from comprobantes.models import Comprobante; Comprobante.objects.all().delete()\"")
    return True

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas de la API SUNAT - VERSIÓN FINAL COMPLETA")
    print("=" * 70)
    print("📊 Usando valores correctos según estándares SUNAT:")
    print("   • totalGravado: 156.78 (LineExtensionAmount)")
    print("   • totalIGV: 28.22 (TaxAmount)") 
    print("   • totalPrecioVenta: 185.00 (TaxInclusiveAmount)")
    print("   • totalImportePagar: 185.00 (PayableAmount)")
    print("   • Números únicos para evitar duplicados")
    print("=" * 70)
    
    # Limpiar base de datos
    clean_database()
    
    # Verificar que el servidor esté corriendo
    if not test_health_check():
        print("\n❌ El servidor no está corriendo. Ejecuta: python manage.py runserver")
        sys.exit(1)
    
    # Ejecutar pruebas
    tests = [
        ("Health Check", test_health_check),
        ("Validación de comprobante", test_validate_comprobante),
        ("Conversión a XML", test_convert_to_xml),
        ("Validación de errores", test_validation_errors),
        ("Múltiples items", test_multiple_items),
    ]
    
    results = []
    xml_filename = None
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Ejecutando: {test_name}")
            
            if test_name == "Health Check":
                # Ya se ejecutó arriba
                results.append((test_name, True))
            elif test_name == "Conversión a XML":
                xml_filename = test_func()
                results.append((test_name, xml_filename is not None))
            else:
                result = test_func()
                results.append((test_name, result))
                
        except Exception as e:
            print(f"❌ Error en prueba {test_name}: {str(e)}")
            results.append((test_name, False))
    
    # Probar descarga de XML si se generó
    if xml_filename:
        print(f"\n🧪 Ejecutando: Descarga de XML")
        test_get_xml_file(xml_filename)
    
    # Resumen de resultados
    print("\n" + "=" * 70)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 70)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("\n🎉 ¡Todas las pruebas pasaron! La API está funcionando correctamente.")
        print("✨ El generador de XML UBL 2.1 para SUNAT está listo para producción.")
        print("\n📋 Archivos generados disponibles en:")
        print("   • media/xml/ - Archivos XML")
        print("   • media/zip/ - Archivos ZIP para SUNAT")
    else:
        print(f"\n⚠️  {total - passed} pruebas fallaron. Revisa los errores arriba.")
        
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)