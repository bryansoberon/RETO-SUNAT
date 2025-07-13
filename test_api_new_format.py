#!/usr/bin/env python
"""
Script de pruebas para la API SUNAT con nuevo formato JSON
Ejecutar con: python test_api_new_format.py
"""

import requests
import json
import os
import sys
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

def test_validate_comprobante():
    """Prueba el endpoint de validación con nuevo formato"""
    print("\n🔍 Probando endpoint de validación...")
    
    # Datos de prueba con nuevo formato
    test_data = {
        "serie": "F001",
        "numero": "123",
        "fechaEmision": "2025-01-05",
        "horaEmision": "10:00:00",
        "tipoDocumento": "01",
        "moneda": "PEN",
        "formaPago": "Contado",
        "totalGravado": 156.78,
        "totalIGV": 28.22,
        "totalPrecioVenta": 185.00,
        "totalImportePagar": 185.00,
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
            "razonSocial": "CLIENTE DE MUESTRA SAC",
            "tipoDoc": "6",
            "ubigeo": "130101",
            "direccion": "AV. PRINCIPAL 123 - TRUJILLO",
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
                "valorUnitario": 156.78,
                "precioVentaUnitario": 185.00,
                "valorTotal": 156.78,
                "igv": 28.22,
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
            print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error en validación: {str(e)}")
        return None

def test_convert_to_xml():
    """Prueba el endpoint de conversión con nuevo formato"""
    print("\n🔍 Probando endpoint de conversión...")
    
    # Datos de prueba con nuevo formato
    test_data = {
        "serie": "F001",
        "numero": "124",
        "fechaEmision": "2025-01-05",
        "horaEmision": "10:00:00",
        "tipoDocumento": "01",
        "moneda": "PEN",
        "formaPago": "Contado",
        "totalGravado": 156.78,
        "totalIGV": 28.22,
        "totalPrecioVenta": 185.00,
        "totalImportePagar": 185.00,
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
            "razonSocial": "CLIENTE DE MUESTRA SAC",
            "tipoDoc": "6",
            "ubigeo": "130101",
            "direccion": "AV. PRINCIPAL 123 - TRUJILLO",
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
                "valorUnitario": 156.78,
                "precioVentaUnitario": 185.00,
                "valorTotal": 156.78,
                "igv": 28.22,
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
            print(f"✅ Descarga exitosa: {len(response.content)} bytes")
            return True
        else:
            print(f"❌ Descarga falló: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error en descarga: {str(e)}")
        return False

def test_validation_errors():
    """Prueba validaciones de errores con nuevo formato"""
    print("\n🔍 Probando validaciones de errores...")
    
    # Datos inválidos
    invalid_data = {
        "serie": "F001",
        "numero": "123",
        "tipoDocumento": "01",
        "totalImportePagar": 185.00,
        "emisor": {
            "ruc": "123",  # RUC muy corto
            "razonSocial": "EMPRESA TEST"
        },
        "cliente": {
            "numeroDoc": "123",  # Número muy corto
            "razonSocial": "CLIENTE TEST"
        },
        "items": []  # Sin items
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
            return True
        else:
            print(f"❌ Validación de errores no funcionó como esperado: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error en validación de errores: {str(e)}")
        return False

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas de la API SUNAT con nuevo formato")
    print("=" * 60)
    
    # Verificar que el servidor esté corriendo
    if not test_health_check():
        print("\n❌ El servidor no está corriendo. Ejecuta: python manage.py runserver")
        sys.exit(1)
    
    # Ejecutar pruebas
    tests = [
        ("Validación de comprobante", test_validate_comprobante),
        ("Conversión a XML", test_convert_to_xml),
        ("Validación de errores", test_validation_errors),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            if test_name == "Conversión a XML":
                xml_filename = test_func()
                results.append((test_name, xml_filename is not None))
                
                # Probar descarga de XML si se generó
                if xml_filename:
                    test_get_xml_file(xml_filename)
            else:
                result = test_func()
                results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error en prueba {test_name}: {str(e)}")
            results.append((test_name, False))
    
    # Resumen de resultados
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! La API está funcionando correctamente.")
    else:
        print("⚠️  Algunas pruebas fallaron. Revisa los errores arriba.")

if __name__ == "__main__":
    main() 