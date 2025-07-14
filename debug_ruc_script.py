#!/usr/bin/env python3
"""
Script para debuggear el problema del RUC
"""

import sys
import os
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sunat_api.settings')
django.setup()

from lxml import etree

def debug_ruc_in_xml(xml_file_path):
    """Debuggear el RUC en un archivo XML"""
    
    print("🔍 DEBUGGEANDO RUC EN XML")
    print("=" * 50)
    
    try:
        # Leer el archivo XML
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # Parsear el XML
        root = etree.fromstring(xml_content.encode('utf-8'))
        
        # Definir namespaces
        ns = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
        }
        
        # Buscar todos los IDs de PartyIdentification
        party_ids = root.findall('.//cac:PartyIdentification/cbc:ID', namespaces=ns)
        
        print(f"📊 Encontrados {len(party_ids)} elementos cac:PartyIdentification/cbc:ID")
        print()
        
        for i, id_element in enumerate(party_ids, 1):
            print(f"🔸 ID #{i}:")
            print(f"   Contenido: '{id_element.text}'")
            print(f"   Longitud: {len(id_element.text) if id_element.text else 0}")
            print(f"   Tipo: {type(id_element.text)}")
            
            if id_element.text:
                # Verificar caracteres uno por uno
                chars = []
                for j, char in enumerate(id_element.text):
                    ascii_val = ord(char)
                    chars.append(f"'{char}'({ascii_val})")
                print(f"   Caracteres: {' '.join(chars)}")
                
                # Verificar si es numérico
                print(f"   Es numérico: {id_element.text.isdigit()}")
                print(f"   Es RUC válido: {len(id_element.text) == 11 and id_element.text.isdigit()}")
            else:
                print("   ❌ CONTENIDO VACÍO!")
            
            # Verificar atributos
            print(f"   Atributos:")
            for attr_name, attr_value in id_element.attrib.items():
                print(f"     {attr_name}: '{attr_value}'")
            
            print()
        
        # Buscar específicamente el patrón que falla
        print("🔍 BÚSQUEDA ESPECÍFICA DE XPATH:")
        
        # Probar diferentes XPath
        xpaths = [
            ".//cac:PartyIdentification/cbc:ID",
            "//cac:PartyIdentification/cbc:ID",
            ".//cac:AccountingSupplierParty//cac:PartyIdentification/cbc:ID",
            ".//cac:AccountingCustomerParty//cac:PartyIdentification/cbc:ID"
        ]
        
        for xpath in xpaths:
            try:
                elements = root.findall(xpath, namespaces=ns)
                print(f"   {xpath}: {len(elements)} elementos encontrados")
                for elem in elements:
                    print(f"     -> '{elem.text}'")
            except Exception as e:
                print(f"   {xpath}: ERROR - {e}")
        
        print("\n" + "=" * 50)
        print("✅ Debug completado")
        
    except Exception as e:
        print(f"❌ Error al debuggear: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Buscar el archivo XML más reciente
    xml_dir = 'media/xml'
    if os.path.exists(xml_dir):
        xml_files = [f for f in os.listdir(xml_dir) if f.endswith('.xml')]
        if xml_files:
            # Tomar el más reciente
            xml_files.sort(reverse=True)
            xml_file = os.path.join(xml_dir, xml_files[0])
            print(f"📁 Analizando archivo: {xml_file}")
            debug_ruc_in_xml(xml_file)
        else:
            print("❌ No se encontraron archivos XML en media/xml/")
    else:
        print("❌ Directorio media/xml/ no existe")