#!/usr/bin/env python3
"""
Script de prueba para verificar la generación de XML UBL 2.1
"""

import sys
import os
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sunat_api.settings')
django.setup()

from comprobantes.utils import generate_ubl_xml

def test_xml_generation():
    """Probar la generación de XML"""
    
    # Datos de prueba que coinciden exactamente con el ejemplo
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
    
    # XML objetivo exacto
    xml_objetivo = '''<?xml version="1.0" encoding="utf-8"?>
<Invoice xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ccts="urn:un:unece:uncefact:documentation:2" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2" xmlns:qdt="urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2" xmlns:udt="urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2" xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
	<ext:UBLExtensions>
		<ext:UBLExtension>
			<ext:ExtensionContent>
              <dummy:Note xmlns:dummy="http://example.org/dummy">Prueba sin firma</dummy:Note>
            </ext:ExtensionContent>
		</ext:UBLExtension>
	</ext:UBLExtensions>
	<cbc:UBLVersionID>2.1</cbc:UBLVersionID>
	<cbc:CustomizationID schemeAgencyName="PE:SUNAT">2.0</cbc:CustomizationID>
	<cbc:ProfileID schemeName="Tipo de Operacion" schemeAgencyName="PE:SUNAT" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo51">0101</cbc:ProfileID>
	<cbc:ID>F001-123</cbc:ID>
	<cbc:IssueDate>2025-07-13</cbc:IssueDate>
	<cbc:IssueTime>00:00:00</cbc:IssueTime>
	<cbc:DueDate>2025-07-13</cbc:DueDate>
	<cbc:InvoiceTypeCode listAgencyName="PE:SUNAT" listName="Tipo de Documento" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01" listID="0101" name="Tipo de Operacion">01</cbc:InvoiceTypeCode>
	<cbc:DocumentCurrencyCode listID="ISO 4217 Alpha" listName="Currency" listAgencyName="United Nations Economic Commission for Europe">PEN</cbc:DocumentCurrencyCode>
            <cbc:LineCountNumeric>1</cbc:LineCountNumeric>
    <cac:Signature>
		<cbc:ID>F001-123</cbc:ID>
		<cac:SignatoryParty>
			<cac:PartyIdentification>
				<cbc:ID>20607599727</cbc:ID>
			</cac:PartyIdentification>
			<cac:PartyName>
				<cbc:Name><![CDATA[INSTITUTO INTERNACIONAL DE SOFTWARE S.A.C.]]></cbc:Name>
			</cac:PartyName>
		</cac:SignatoryParty>
		<cac:DigitalSignatureAttachment>
			<cac:ExternalReference>
				<cbc:URI>#SignatureSP</cbc:URI>
			</cac:ExternalReference>
		</cac:DigitalSignatureAttachment>
	</cac:Signature>
	<cac:AccountingSupplierParty>
		<cac:Party>
			<cac:PartyIdentification>
				<cbc:ID schemeID="6" schemeName="Documento de Identidad" schemeAgencyName="PE:SUNAT" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">20607599727</cbc:ID>
			</cac:PartyIdentification>
			<cac:PartyName>
				<cbc:Name><![CDATA[INSTITUTO INTERNACIONAL DE SOFTWARE S.A.C.]]></cbc:Name>
			</cac:PartyName>
			<cac:PartyTaxScheme>
				<cbc:RegistrationName><![CDATA[INSTITUTO INTERNACIONAL DE SOFTWARE S.A.C.]]></cbc:RegistrationName>
				<cbc:CompanyID schemeID="6" schemeName="SUNAT:Identificador de Documento de Identidad" schemeAgencyName="PE:SUNAT" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">20607599727</cbc:CompanyID>
				<cac:TaxScheme>
					<cbc:ID schemeID="6" schemeName="SUNAT:Identificador de Documento de Identidad" schemeAgencyName="PE:SUNAT" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">20607599727</cbc:ID>
				</cac:TaxScheme>
			</cac:PartyTaxScheme>
			<cac:PartyLegalEntity>
				<cbc:RegistrationName><![CDATA[INSTITUTO INTERNACIONAL DE SOFTWARE S.A.C.]]></cbc:RegistrationName>
				<cac:RegistrationAddress>
					<cbc:ID schemeName="Ubigeos" schemeAgencyName="PE:INEI">140101</cbc:ID>
					<cbc:AddressTypeCode listAgencyName="PE:SUNAT" listName="Establecimientos anexos">0000</cbc:AddressTypeCode>
					<cbc:CityName><![CDATA[LAMBAYEQUE]]></cbc:CityName>
					<cbc:CountrySubentity><![CDATA[LAMBAYEQUE]]></cbc:CountrySubentity>
					<cbc:District><![CDATA[LAMBAYEQUE]]></cbc:District>
					<cac:AddressLine>
						<cbc:Line><![CDATA[8 DE OCTUBRE N 123 - LAMBAYEQUE - LAMBAYEQUE - LAMBAYEQUE]]></cbc:Line>
					</cac:AddressLine>
					<cac:Country>
						<cbc:IdentificationCode listID="ISO 3166-1" listAgencyName="United Nations Economic Commission for Europe" listName="Country">PE</cbc:IdentificationCode>
					</cac:Country>
				</cac:RegistrationAddress>
			</cac:PartyLegalEntity>
			<cac:Contact>
				<cbc:Name><![CDATA[]]></cbc:Name>
			</cac:Contact>
		</cac:Party>
	</cac:AccountingSupplierParty>
	<cac:AccountingCustomerParty>
		<cac:Party>
			<cac:PartyIdentification>
				<cbc:ID schemeID="6" schemeName="Documento de Identidad" schemeAgencyName="PE:SUNAT" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">20605145648</cbc:ID>
			</cac:PartyIdentification>
			<cac:PartyName>
				<cbc:Name><![CDATA[AGROINVERSIONES Y SERVICIOS AJINOR S.R.L. - AGROSERVIS AJINOR S.R.L.]]></cbc:Name>
			</cac:PartyName>
			<cac:PartyTaxScheme>
				<cbc:RegistrationName><![CDATA[AGROINVERSIONES Y SERVICIOS AJINOR S.R.L. - AGROSERVIS AJINOR S.R.L.]]></cbc:RegistrationName>
				<cbc:CompanyID schemeID="6" schemeName="SUNAT:Identificador de Documento de Identidad" schemeAgencyName="PE:SUNAT" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">20605145648</cbc:CompanyID>
				<cac:TaxScheme>
					<cbc:ID schemeID="6" schemeName="SUNAT:Identificador de Documento de Identidad" schemeAgencyName="PE:SUNAT" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">20605145648</cbc:ID>
				</cac:TaxScheme>
			</cac:PartyTaxScheme>
			<cac:PartyLegalEntity>
				<cbc:RegistrationName><![CDATA[AGROINVERSIONES Y SERVICIOS AJINOR S.R.L. - AGROSERVIS AJINOR S.R.L.]]></cbc:RegistrationName>
				<cac:RegistrationAddress>
					<cbc:ID schemeName="Ubigeos" schemeAgencyName="PE:INEI"/>
					<cbc:CityName><![CDATA[]]></cbc:CityName>
					<cbc:CountrySubentity><![CDATA[]]></cbc:CountrySubentity>
					<cbc:District><![CDATA[]]></cbc:District>
					<cac:AddressLine>
						<cbc:Line><![CDATA[MZA. C LOTE. 46 URB. SAN ISIDRO LA LIBERTAD - TRUJILLO - TRUJILLO]]></cbc:Line>
					</cac:AddressLine>                                        
					<cac:Country>
						<cbc:IdentificationCode listID="ISO 3166-1" listAgencyName="United Nations Economic Commission for Europe" listName="Country"/>
					</cac:Country>
				</cac:RegistrationAddress>
			</cac:PartyLegalEntity>
		</cac:Party>
	</cac:AccountingCustomerParty>
	<cac:PaymentTerms>
      <cbc:ID>FormaPago</cbc:ID>
      <cbc:PaymentMeansID>Contado</cbc:PaymentMeansID>
   </cac:PaymentTerms>	
	<cac:TaxTotal>
		<cbc:TaxAmount currencyID="PEN">28.22</cbc:TaxAmount>
		<cac:TaxSubtotal>
			<cbc:TaxableAmount currencyID="PEN">156.78</cbc:TaxableAmount>
			<cbc:TaxAmount currencyID="PEN">28.22</cbc:TaxAmount>
			<cac:TaxCategory>
				<cbc:ID schemeID="UN/ECE 5305" schemeName="Tax Category Identifier" schemeAgencyName="United Nations Economic Commission for Europe">S</cbc:ID>
				<cac:TaxScheme>
					<cbc:ID schemeID="UN/ECE 5153" schemeAgencyID="6">1000</cbc:ID>
					<cbc:Name>IGV</cbc:Name>
					<cbc:TaxTypeCode>VAT</cbc:TaxTypeCode>
				</cac:TaxScheme>
			</cac:TaxCategory>
		</cac:TaxSubtotal>			
	</cac:TaxTotal>
	<cac:LegalMonetaryTotal>
		<cbc:LineExtensionAmount currencyID="PEN">156.78</cbc:LineExtensionAmount>
		<cbc:TaxInclusiveAmount currencyID="PEN">185.00</cbc:TaxInclusiveAmount>
		<cbc:PayableAmount currencyID="PEN">185.00</cbc:PayableAmount>
	</cac:LegalMonetaryTotal>
	<cac:InvoiceLine>
		<cbc:ID>1</cbc:ID>
		<cbc:InvoicedQuantity unitCode="NIU" unitCodeListID="UN/ECE rec 20" unitCodeListAgencyName="United Nations Economic Commission for Europe">1</cbc:InvoicedQuantity>
		<cbc:LineExtensionAmount currencyID="PEN">156.78</cbc:LineExtensionAmount>
		<cac:PricingReference>
			<cac:AlternativeConditionPrice>
				<cbc:PriceAmount currencyID="PEN">185.00</cbc:PriceAmount>
				<cbc:PriceTypeCode listName="Tipo de Precio" listAgencyName="PE:SUNAT" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo16">01</cbc:PriceTypeCode>
			</cac:AlternativeConditionPrice>
		</cac:PricingReference>
		<cac:TaxTotal>
			<cbc:TaxAmount currencyID="PEN">28.22</cbc:TaxAmount>
			<cac:TaxSubtotal>
				<cbc:TaxableAmount currencyID="PEN">156.78</cbc:TaxableAmount>
				<cbc:TaxAmount currencyID="PEN">28.22</cbc:TaxAmount>
				<cac:TaxCategory>
					<cbc:ID schemeID="UN/ECE 5305" schemeName="Tax Category Identifier" schemeAgencyName="United Nations Economic Commission for Europe">S</cbc:ID>
					<cbc:Percent>18</cbc:Percent>
					<cbc:TaxExemptionReasonCode listAgencyName="PE:SUNAT" listName="Afectacion del IGV" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo07">10</cbc:TaxExemptionReasonCode>
					<cac:TaxScheme>
						<cbc:ID schemeID="UN/ECE 5153" schemeName="Codigo de tributos" schemeAgencyName="PE:SUNAT">1000</cbc:ID>
						<cbc:Name>IGV</cbc:Name>
						<cbc:TaxTypeCode>VAT</cbc:TaxTypeCode>
					</cac:TaxScheme>
				</cac:TaxCategory>
			</cac:TaxSubtotal></cac:TaxTotal>
		<cac:Item>
			<cbc:Description><![CDATA[FENA X L]]></cbc:Description>
			<cac:SellersItemIdentification>
				<cbc:ID><![CDATA[195]]></cbc:ID>
			</cac:SellersItemIdentification>
			<cac:CommodityClassification>
				<cbc:ItemClassificationCode listID="UNSPSC" listAgencyName="GS1 US" listName="Item Classification">10191509</cbc:ItemClassificationCode>
			</cac:CommodityClassification>
		</cac:Item>
		<cac:Price>
			<cbc:PriceAmount currencyID="PEN">156.78</cbc:PriceAmount>
		</cac:Price>
	</cac:InvoiceLine>
</Invoice>'''
    
    try:
        # Generar XML
        xml_content = generate_ubl_xml(test_data)
        
        # Guardar en archivo para revisión
        with open('test_generated.xml', 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        print("✅ XML generado exitosamente!")
        print("📁 Archivo guardado como: test_generated.xml")
        
        # Comparar letra por letra
        print("\n🔍 Comparando XML generado con el objetivo...")
        
        # Normalizar espacios y saltos de línea para comparación
        xml_generado_norm = xml_content.replace('\n', '').replace('\r', '').replace(' ', '')
        xml_objetivo_norm = xml_objetivo.replace('\n', '').replace('\r', '').replace(' ', '')
        
        if xml_generado_norm == xml_objetivo_norm:
            print("✅ ¡PERFECTO! El XML generado es IDÉNTICO al objetivo")
            return True
        else:
            print("❌ El XML generado NO coincide exactamente con el objetivo")
            
            # Encontrar diferencias
            min_len = min(len(xml_generado_norm), len(xml_objetivo_norm))
            for i in range(min_len):
                if xml_generado_norm[i] != xml_objetivo_norm[i]:
                    print(f"❌ Diferencia en posición {i}:")
                    print(f"   Generado: '{xml_generado_norm[i]}'")
                    print(f"   Objetivo: '{xml_objetivo_norm[i]}'")
                    print(f"   Contexto generado: '{xml_generado_norm[max(0, i-20):i+20]}'")
                    print(f"   Contexto objetivo: '{xml_objetivo_norm[max(0, i-20):i+20]}'")
                    break
            
            return False
        
    except Exception as e:
        print(f"❌ Error generando XML: {e}")
        return False

if __name__ == '__main__':
    test_xml_generation() 