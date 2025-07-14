#!/usr/bin/env python3
"""
Script para debuggear el error XML en línea 80, columna 279
"""

import sys
import os
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sunat_api.settings')
django.setup()

from comprobantes.utils import generate_ubl_xml

def debug_xml_generation():
    """Debuggear la generación de XML línea por línea"""
    
    print("🔍 DEBUGGING XML GENERATION ERROR")
    print("=" * 50)
    
    # Datos de prueba
    test_data = {
        'serie': 'F001',
        'numero': '178',
        'tipoDocumento': '01',
        'moneda': 'PEN',
        'fechaEmision': '2025-01-01',
        'horaEmision': '10:30:00',
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
            'ubigeo': '130101',
            'distrito': 'TRUJILLO',
            'departamento': 'LA LIBERTAD',
            'direccion': 'MZA. C LOTE. 46 URB. SAN ISIDRO - TRUJILLO - TRUJILLO - LA LIBERTAD',
            'codigoPais': 'PE'
        },
        'items': [
            {
                'id': '1',
                'cantidad': 1,
                'unidadMedida': 'NIU',
                'descripcion': 'FENA X L',
                'valorUnitario': 156.78,
                'valorTotal': 156.78,
                'precioVentaUnitario': 185.00,
                'igv': 28.22,
                'codigoProducto': '195',
                'unspsc': '10191509'
            }
        ]
    }
    
    try:
        print("🔧 Generando XML...")
        xml_content = generate_ubl_xml(test_data)
        
        # Guardar XML para análisis
        with open('debug_generated.xml', 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        print(f"✅ XML generado: debug_generated.xml")
        print(f"📊 Tamaño: {len(xml_content):,} caracteres")
        
        # Mostrar líneas alrededor de la línea 80
        lines = xml_content.split('\n')
        print(f"\n🔍 Total de líneas: {len(lines)}")
        
        if len(lines) >= 80:
            print(f"\n📋 Líneas 75-85 (área del error):")
            print("-" * 60)
            for i in range(max(0, 75-1), min(len(lines), 85)):
                line_num = i + 1
                marker = "👉" if line_num == 80 else "  "
                print(f"{marker} {line_num:3d}: {lines[i]}")
            print("-" * 60)
            
            # Verificar la línea 80 específicamente
            if len(lines) > 79:
                line_80 = lines[79]  # índice 79 = línea 80
                print(f"\n🔍 ANÁLISIS DE LÍNEA 80:")
                print(f"   Contenido: '{line_80}'")
                print(f"   Longitud: {len(line_80)} caracteres")
                
                if len(line_80) >= 279:
                    char_279 = line_80[278]  # índice 278 = columna 279
                    print(f"   Carácter en columna 279: '{char_279}' (ASCII: {ord(char_279)})")
                    print(f"   Contexto: '{line_80[270:285]}'")
                else:
                    print(f"   ⚠️ La línea 80 solo tiene {len(line_80)} caracteres, no llega a columna 279")
        
        # Verificar XML con parser
        print(f"\n🔍 Verificando XML con parser...")
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_content.encode('utf-8'))
            print("✅ XML parseado correctamente")
        except ET.ParseError as e:
            print(f"❌ Error de parsing XML: {e}")
            
            # Extraer información del error
            error_msg = str(e)
            if "line" in error_msg and "column" in error_msg:
                import re
                match = re.search(r'line (\d+), column (\d+)', error_msg)
                if match:
                    error_line = int(match.group(1))
                    error_col = int(match.group(2))
                    print(f"   Error en línea {error_line}, columna {error_col}")
                    
                    if error_line <= len(lines):
                        problem_line = lines[error_line - 1]
                        print(f"   Línea problemática: '{problem_line}'")
                        
                        if error_col <= len(problem_line):
                            problem_char = problem_line[error_col - 1]
                            print(f"   Carácter problemático: '{problem_char}'")
                            print(f"   Contexto: '{problem_line[max(0, error_col-10):error_col+10]}'")
        
        # Buscar etiquetas no cerradas
        print(f"\n🔍 Buscando etiquetas potencialmente mal cerradas...")
        
        # Contar etiquetas abiertas vs cerradas
        import re
        open_tags = re.findall(r'<([a-zA-Z:][^/>]*?)>', xml_content)
        close_tags = re.findall(r'</([a-zA-Z:]+)>', xml_content)
        
        print(f"   Etiquetas abiertas: {len(open_tags)}")
        print(f"   Etiquetas cerradas: {len(close_tags)}")
        
        # Buscar etiquetas auto-cerradas
        self_closing = re.findall(r'<([a-zA-Z:][^>]*?)/>', xml_content)
        print(f"   Etiquetas auto-cerradas: {len(self_closing)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generando XML: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    debug_xml_generation()