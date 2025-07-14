#!/usr/bin/env python
"""
Script de pruebas para la integración completa con SUNAT
Ejecutar con: python test_sunat_integration.py
"""

import requests
import json
import os
import sys
import time
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
            
            # Verificar características SUNAT
            features = data.get('features', {})
            print(f"   🔧 Generación XML: {'✅' if features.get('xml_generation') else '❌'}")
            print(f"   🔐 Firma digital: {'✅' if features.get('digital_signature') else '❌'}")
            print(f"   📡 Integración SUNAT: {'✅' if features.get('sunat_integration') else '❌'}")
            print(f"   📄 Procesamiento CDR: {'✅' if features.get('cdr_processing') else '❌'}")
            
            return True
        else:
            print(f"❌ Health check falló: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error en health check: {str(e)}")
        return False

def create_test_comprobante():
    """Crear un comprobante de prueba para SUNAT"""
    print("\n🔍 Creando comprobante de prueba...")
    
    # Generar número único basado en timestamp
    timestamp = str(int(time.time()))[-6:]
    
    test_data = {
        "serie": "F001",
        "numero": timestamp,  # Número único
        "fechaEmision": "2025-01-01",
        "horaEmision": "10:30:00",
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
            "numeroDoc": "20000000001",  # RUC de pruebas SUNAT
            "razonSocial": "EMPRESA DE PRUEBAS SUNAT",
            "tipoDoc": "6",
            "ubigeo": "130101",
            "direccion": "AV. PRUEBAS 123 - LIMA",
            "departamento": "LIMA",
            "provincia": "LIMA",
            "distrito": "LIMA",
            "codigoPais": "PE",
            "correo": "pruebas@sunat.gob.pe"
        },
        "items": [
            {
                "id": "1",
                "cantidad": 1,
                "unidadMedida": "NIU",
                "descripcion": "PRODUCTO DE PRUEBA SUNAT",
                "valorUnitario": 156.78,
                "precioVentaUnitario": 185.00,
                "valorTotal": 156.78,
                "igv": 28.22,
                "codigoProducto": "PROD001",
                "codigoProductoSUNAT": "PROD001",
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
            print(f"✅ Comprobante creado exitosamente")
            print(f"   ID: {data.get('comprobante_id')}")
            print(f"   XML: {data.get('xml_filename')}")
            print(f"   ZIP: {data.get('zip_filename')}")
            print(f"   Listo para SUNAT: {'✅' if data.get('can_send_to_sunat') else '❌'}")
            return data.get('comprobante_id')
        else:
            print(f"❌ Error creando comprobante: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def test_send_to_sunat(comprobante_id):
    """Probar envío a SUNAT"""
    print(f"\n🔍 Enviando comprobante {comprobante_id} a SUNAT...")
    
    try:
        response = requests.post(f"{API_BASE}/send-to-sunat/{comprobante_id}/")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Respuesta de SUNAT recibida")
            print(f"   Éxito: {'✅' if data.get('success') else '❌'}")
            print(f"   Estado: {data.get('estado')}")
            print(f"   Mensaje: {data.get('message', 'Sin mensaje')}")
            
            if data.get('ticket'):
                print(f"   🎫 Ticket: {data.get('ticket')}")
            
            if data.get('cdr_info'):
                cdr_info = data.get('cdr_info')
                print(f"   📄 CDR Info:")
                print(f"      Código: {cdr_info.get('response_code')}")
                print(f"      Descripción: {cdr_info.get('description')}")
            
            return data
        else:
            print(f"❌ Error enviando a SUNAT: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def test_check_status(comprobante_id):
    """Probar consulta de estado"""
    print(f"\n🔍 Consultando estado del comprobante {comprobante_id}...")
    
    try:
        response = requests.get(f"{API_BASE}/comprobante-status/{comprobante_id}/")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Estado consultado")
            print(f"   Estado actual: {data.get('estado')}")
            print(f"   Ticket: {data.get('ticket', 'Sin ticket')}")
            
            if data.get('cdr_xml_path'):
                print(f"   📄 CDR disponible: {data.get('cdr_xml_path')}")
            
            if data.get('errores'):
                print(f"   ❌ Errores: {data.get('errores')}")
            
            return data
        else:
            print(f"❌ Error consultando estado: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def test_check_ticket_status(comprobante_id):
    """Probar consulta de ticket en SUNAT"""
    print(f"\n🔍 Consultando ticket en SUNAT para comprobante {comprobante_id}...")
    
    try:
        response = requests.get(f"{API_BASE}/check-sunat-status/{comprobante_id}/")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Consulta de ticket exitosa")
            print(f"   Éxito: {'✅' if data.get('success') else '❌'}")
            print(f"   Estado: {data.get('estado')}")
            print(f"   Mensaje: {data.get('message', 'Sin mensaje')}")
            
            if data.get('cdr_info'):
                cdr_info = data.get('cdr_info')
                print(f"   📄 CDR Info:")
                print(f"      Código: {cdr_info.get('response_code')}")
                print(f"      Descripción: {cdr_info.get('description')}")
                if cdr_info.get('notes'):
                    print(f"      Notas: {', '.join(cdr_info.get('notes'))}")
            
            return data
        else:
            print(f"❌ Error consultando ticket: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def test_download_cdr(comprobante_id):
    """Probar descarga de CDR"""
    print(f"\n🔍 Intentando descargar CDR para comprobante {comprobante_id}...")
    
    try:
        response = requests.get(f"{API_BASE}/cdr/{comprobante_id}/")
        
        if response.status_code == 200:
            print(f"✅ CDR descargado exitosamente")
            print(f"   Tamaño: {len(response.content):,} bytes")
            print(f"   Content-Type: {response.headers.get('Content-Type')}")
            
            # Guardar CDR para inspección
            cdr_filename = f"cdr_comprobante_{comprobante_id}.xml"
            with open(cdr_filename, 'wb') as f:
                f.write(response.content)
            print(f"   💾 CDR guardado como: {cdr_filename}")
            
            return True
        elif response.status_code == 404:
            print(f"⚠️  CDR no disponible aún")
            return False
        else:
            print(f"❌ Error descargando CDR: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_sunat_dashboard():
    """Probar dashboard de estadísticas SUNAT"""
    print(f"\n🔍 Consultando dashboard SUNAT...")
    
    try:
        response = requests.get(f"{API_BASE}/sunat-dashboard/")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Dashboard consultado exitosamente")
            
            stats = data.get('estadisticas', {})
            print(f"   📊 Estadísticas:")
            print(f"      Total comprobantes: {stats.get('total_comprobantes')}")
            print(f"      Enviados a SUNAT: {stats.get('enviados_sunat')}")
            print(f"      Aceptados: {stats.get('aceptados_sunat')}")
            print(f"      Rechazados: {stats.get('rechazados_sunat')}")
            print(f"      Pendientes: {stats.get('pendientes_envio')}")
            print(f"      Tasa aceptación: {stats.get('tasa_aceptacion')}%")
            
            print(f"   📈 Distribución por estados:")
            for estado in data.get('estados_distribucion', []):
                print(f"      {estado.get('estado')}: {estado.get('count')}")
            
            return data
        else:
            print(f"❌ Error consultando dashboard: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def test_bulk_operations():
    """Probar operaciones en lote"""
    print(f"\n🔍 Probando operaciones en lote...")
    
    # Crear múltiples comprobantes
    comprobante_ids = []
    for i in range(3):
        comprobante_id = create_test_comprobante()
        if comprobante_id:
            comprobante_ids.append(comprobante_id)
        time.sleep(1)  # Evitar duplicados por timestamp
    
    if not comprobante_ids:
        print("❌ No se pudieron crear comprobantes para prueba en lote")
        return False
    
    print(f"✅ Comprobantes creados para lote: {comprobante_ids}")
    
    # Envío en lote
    try:
        response = requests.post(
            f"{API_BASE}/bulk-send-sunat/",
            json={'comprobante_ids': comprobante_ids}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Envío en lote completado")
            print(f"   Total procesados: {data.get('total_processed')}")
            print(f"   Exitosos: {data.get('successful')}")
            print(f"   Fallidos: {data.get('failed')}")
            
            return True
        else:
            print(f"❌ Error en envío en lote: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_pending_tickets():
    """Probar verificación de tickets pendientes"""
    print(f"\n🔍 Verificando tickets pendientes...")
    
    try:
        response = requests.post(f"{API_BASE}/check-pending-tickets/")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Verificación de tickets completada")
            print(f"   Total verificados: {data.get('total_checked')}")
            
            for result in data.get('results', []):
                if result.get('success'):
                    print(f"   ✅ Comprobante {result.get('comprobante_id')}: {result.get('estado')}")
                else:
                    print(f"   ❌ Comprobante {result.get('comprobante_id')}: {result.get('error')}")
            
            return True
        else:
            print(f"❌ Error verificando tickets: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def full_integration_test():
    """Prueba de integración completa"""
    print("🚀 INICIANDO PRUEBA DE INTEGRACIÓN COMPLETA CON SUNAT")
    print("=" * 70)
    
    # 1. Health check
    if not test_health_check():
        print("\n❌ Health check falló - Abortando pruebas")
        return False
    
    # 2. Crear comprobante
    comprobante_id = create_test_comprobante()
    if not comprobante_id:
        print("\n❌ No se pudo crear comprobante - Abortando pruebas")
        return False
    
    # 3. Enviar a SUNAT
    send_result = test_send_to_sunat(comprobante_id)
    if not send_result:
        print("\n❌ Error enviando a SUNAT")
        return False
    
    # 4. Verificar estado
    status_result = test_check_status(comprobante_id)
    
    # 5. Si hay ticket, consultar estado en SUNAT
    if send_result.get('ticket'):
        print(f"\n⏳ Esperando 5 segundos antes de consultar ticket...")
        time.sleep(5)
        test_check_ticket_status(comprobante_id)
    
    # 6. Intentar descargar CDR
    test_download_cdr(comprobante_id)
    
    # 7. Dashboard
    test_sunat_dashboard()
    
    # 8. Operaciones en lote (opcional)
    print(f"\n🔍 ¿Ejecutar pruebas en lote? (puede tomar tiempo) (s/n): ", end="")
    if input().lower() in ['s', 'si', 'y', 'yes']:
        test_bulk_operations()
        test_pending_tickets()
    
    print("\n" + "=" * 70)
    print("🎉 PRUEBA DE INTEGRACIÓN COMPLETA FINALIZADA")
    print("=" * 70)
    
    return True

def main():
    """Función principal"""
    print("🧪 TESTING INTEGRACIÓN SUNAT")
    print("=" * 50)
    print("📋 Este script probará:")
    print("   1. ✅ Health check con características SUNAT")
    print("   2. 📄 Creación de comprobante UBL 2.1")
    print("   3. 📡 Envío a SUNAT (ambiente beta)")
    print("   4. 🔍 Consulta de estado")
    print("   5. 🎫 Verificación de tickets")
    print("   6. 📄 Descarga de CDR")
    print("   7. 📊 Dashboard de estadísticas")
    print("   8. 🔄 Operaciones en lote")
    print("=" * 50)
    
    # Verificar que el servidor esté corriendo
    try:
        response = requests.get(f"{BASE_URL}/health/", timeout=5)
        if response.status_code != 200:
            raise Exception("Servidor no responde correctamente")
    except Exception as e:
        print(f"\n❌ El servidor no está corriendo o no responde")
        print(f"   Error: {str(e)}")
        print(f"   Ejecuta: python manage.py runserver")
        return False
    
    print(f"\n🔍 Selecciona el tipo de prueba:")
    print(f"   1. Prueba completa de integración")
    print(f"   2. Solo health check")
    print(f"   3. Solo crear y enviar un comprobante")
    print(f"   4. Solo dashboard")
    print(f"   5. Solo operaciones en lote")
    
    try:
        opcion = input(f"\nIngresa opción (1-5) [1]: ").strip() or "1"
        
        if opcion == "1":
            return full_integration_test()
        elif opcion == "2":
            return test_health_check()
        elif opcion == "3":
            comprobante_id = create_test_comprobante()
            if comprobante_id:
                test_send_to_sunat(comprobante_id)
                test_check_status(comprobante_id)
            return comprobante_id is not None
        elif opcion == "4":
            return test_sunat_dashboard() is not None
        elif opcion == "5":
            test_bulk_operations()
            test_pending_tickets()
            return True
        else:
            print("❌ Opción inválida")
            return False
    except KeyboardInterrupt:
        print("\n\n⚠️  Prueba interrumpida por el usuario")
        return False
    except Exception as e:
        print(f"\n❌ Error en prueba: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)