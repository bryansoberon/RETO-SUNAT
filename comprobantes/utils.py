# comprobantes/utils.py

import os
import zipfile
from datetime import datetime
from decimal import Decimal
from django.conf import settings

# Usar siempre xml.etree.ElementTree sin problemas de namespace
import xml.etree.ElementTree as ET


def validate_comprobante_data(data):
    """Validar datos específicos de SUNAT"""
    errors = []
    
    # Validar RUC emisor
    if len(data['emisor']['ruc']) != 11:
        errors.append("El RUC emisor debe tener 11 dígitos")
    
    # Validar según tipo de comprobante
    tipo_doc = data['tipoDocumento']
    cliente = data['cliente']
    
    if tipo_doc == '01':  # Factura
        if cliente.get('tipoDoc') != '6' or len(cliente['numeroDoc']) != 11:
            errors.append("Para facturas, el cliente debe tener RUC (tipoDoc=6, 11 dígitos)")
    elif tipo_doc == '03':  # Boleta
        if cliente.get('tipoDoc') != '1' or len(cliente['numeroDoc']) != 8:
            errors.append("Para boletas, el cliente debe tener DNI (tipoDoc=1, 8 dígitos)")
    
    # Validar montos
    if data['totalImportePagar'] <= 0:
        errors.append("El total debe ser mayor a 0")
    
    if data['totalIGV'] < 0:
        errors.append("El IGV no puede ser negativo")
    
    # Validar items
    if not data.get('items') or len(data['items']) == 0:
        errors.append("Debe incluir al menos un item")
    
    return {
        'success': len(errors) == 0,
        'errors': errors
    }


def generate_ubl_xml(data):
    """
    Generar XML UBL 2.1 usando la estructura EXACTA del ejemplo proporcionado
    """
    
    # Preparar datos
    fecha_emision = data.get('fechaEmision', datetime.now().strftime('%Y-%m-%d'))
    hora_emision = data.get('horaEmision', datetime.now().strftime('%H:%M:%S'))
    
    if isinstance(fecha_emision, datetime):
        fecha_emision = fecha_emision.strftime('%Y-%m-%d')
    if isinstance(hora_emision, datetime):
        hora_emision = hora_emision.strftime('%H:%M:%S')
    
    # Construir XML usando string completo (sin problemas de namespaces)
    xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
  <ext:UBLExtensions xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2">
    <ext:UBLExtension>
      <ext:ExtensionContent>
        <!-- Firma digital será insertada aquí por el proceso de firmado -->
      </ext:ExtensionContent>
    </ext:UBLExtension>
  </ext:UBLExtensions>
  <cbc:UBLVersionID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">2.1</cbc:UBLVersionID>
  <cbc:CustomizationID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT">2.0</cbc:CustomizationID>
  <cbc:ProfileID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeName="Tipo de Operacion" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo51">0101</cbc:ProfileID>
  <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{data['serie']}-{data['numero']}</cbc:ID>
  <cbc:IssueDate xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{fecha_emision}</cbc:IssueDate>
  <cbc:IssueTime xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{hora_emision}</cbc:IssueTime>
  <cbc:DueDate xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{fecha_emision}</cbc:DueDate>
  <cbc:InvoiceTypeCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="PE:SUNAT" listID="0101" listName="Tipo de Documento" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01" name="Tipo de Operacion">{data['tipoDocumento']}</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="United Nations Economic Commission for Europe" listID="ISO 4217 Alpha" listName="Currency">{data.get('moneda', 'PEN')}</cbc:DocumentCurrencyCode>
  <cbc:LineCountNumeric xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{len(data['items'])}</cbc:LineCountNumeric>
  <cac:Signature xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{data['serie']}-{data['numero']}</cbc:ID>
    <cac:SignatoryParty>
      <cac:PartyIdentification>
        <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{data['emisor']['ruc']}</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyName>
        <cbc:Name xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(data['emisor']['razonSocial'])}</cbc:Name>
      </cac:PartyName>
    </cac:SignatoryParty>
    <cac:DigitalSignatureAttachment>
      <cac:ExternalReference>
        <cbc:URI xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">#SignatureSP</cbc:URI>
      </cac:ExternalReference>
    </cac:DigitalSignatureAttachment>
  </cac:Signature>
  <cac:AccountingSupplierParty xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <cac:Party>
      <cac:PartyIdentification>
        <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeID="6" schemeName="Documento de Identidad" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">{data['emisor']['ruc']}</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyName>
        <cbc:Name xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(data['emisor']['razonSocial'])}</cbc:Name>
      </cac:PartyName>
      <cac:PartyTaxScheme>
        <cbc:RegistrationName xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(data['emisor']['razonSocial'])}</cbc:RegistrationName>
        <cbc:CompanyID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeID="6" schemeName="SUNAT:Identificador de Documento de Identidad" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">{data['emisor']['ruc']}</cbc:CompanyID>
        <cac:TaxScheme>
          <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeID="6" schemeName="SUNAT:Identificador de Documento de Identidad" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">{data['emisor']['ruc']}</cbc:ID>
        </cac:TaxScheme>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(data['emisor']['razonSocial'])}</cbc:RegistrationName>
        <cac:RegistrationAddress>
          <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:INEI" schemeName="Ubigeos">{data['emisor']['ubigeo']}</cbc:ID>
          <cbc:AddressTypeCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="PE:SUNAT" listName="Establecimientos anexos">0000</cbc:AddressTypeCode>
          <cbc:CityName xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(data['emisor'].get('distrito', ''))}</cbc:CityName>
          <cbc:CountrySubentity xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(data['emisor'].get('provincia', ''))}</cbc:CountrySubentity>
          <cbc:District xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(data['emisor'].get('distrito', ''))}</cbc:District>
          <cac:AddressLine>
            <cbc:Line xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(data['emisor']['direccion'])}</cbc:Line>
          </cac:AddressLine>
          <cac:Country>
            <cbc:IdentificationCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="United Nations Economic Commission for Europe" listID="ISO 3166-1" listName="Country">{data['emisor']['codigoPais']}</cbc:IdentificationCode>
          </cac:Country>
        </cac:RegistrationAddress>
      </cac:PartyLegalEntity>
      <cac:Contact>
        <cbc:Name xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"/>
      </cac:Contact>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <cac:Party>
      <cac:PartyIdentification>
        <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeID="6" schemeName="Documento de Identidad" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">{data['cliente']['numeroDoc']}</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyName>
        <cbc:Name xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(data['cliente']['razonSocial'])}</cbc:Name>
      </cac:PartyName>
      <cac:PartyTaxScheme>
        <cbc:RegistrationName xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(data['cliente']['razonSocial'])}</cbc:RegistrationName>
        <cbc:CompanyID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeID="6" schemeName="SUNAT:Identificador de Documento de Identidad" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">{data['cliente']['numeroDoc']}</cbc:CompanyID>
        <cac:TaxScheme>
          <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeID="6" schemeName="SUNAT:Identificador de Documento de Identidad" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">{data['cliente']['numeroDoc']}</cbc:ID>
        </cac:TaxScheme>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(data['cliente']['razonSocial'])}</cbc:RegistrationName>
        <cac:RegistrationAddress>
          <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:INEI" schemeName="Ubigeos">{data['cliente'].get('ubigeo', '130101')}</cbc:ID>
          <cbc:AddressTypeCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="PE:SUNAT" listName="Establecimientos anexos">0000</cbc:AddressTypeCode>
          <cbc:CityName xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(data['cliente'].get('distrito', 'TRUJILLO'))}</cbc:CityName>
          <cbc:CountrySubentity xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(data['cliente'].get('departamento', 'LA LIBERTAD'))}</cbc:CountrySubentity>
          <cbc:District xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(data['cliente'].get('distrito', 'TRUJILLO'))}</cbc:District>
          <cac:AddressLine>
            <cbc:Line xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(data['cliente'].get('direccion', ''))}</cbc:Line>
          </cac:AddressLine>
          <cac:Country>
            <cbc:IdentificationCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="United Nations Economic Commission for Europe" listID="ISO 3166-1" listName="Country">{data['cliente'].get('codigoPais', 'PE')}</cbc:IdentificationCode>
          </cac:Country>
        </cac:RegistrationAddress>
      </cac:PartyLegalEntity>
      <cac:Contact>
        <cbc:Name xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"/>
      </cac:Contact>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:PaymentTerms xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">FormaPago</cbc:ID>
    <cbc:PaymentMeansID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{data.get('formaPago', 'Contado')}</cbc:PaymentMeansID>
  </cac:PaymentTerms>
  <cac:TaxTotal xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <cbc:TaxAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{data.get('moneda', 'PEN')}">{data['totalIGV']}</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{data.get('moneda', 'PEN')}">{data['totalGravado']}</cbc:TaxableAmount>
      <cbc:TaxAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{data.get('moneda', 'PEN')}">{data['totalIGV']}</cbc:TaxAmount>
      <cac:TaxCategory>
        <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="United Nations Economic Commission for Europe" schemeID="UN/ECE 5305" schemeName="Tax Category Identifier">S</cbc:ID>
        <cbc:Percent xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">18</cbc:Percent>
        <cbc:TaxExemptionReasonCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="PE:SUNAT" listName="Afectacion del IGV" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo07">10</cbc:TaxExemptionReasonCode>
        <cac:TaxScheme>
          <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyID="6" schemeID="UN/ECE 5153">1000</cbc:ID>
          <cbc:Name xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">IGV</cbc:Name>
          <cbc:TaxTypeCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">VAT</cbc:TaxTypeCode>
        </cac:TaxScheme>
      </cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <cbc:LineExtensionAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{data.get('moneda', 'PEN')}">{data['totalGravado']}</cbc:LineExtensionAmount>
    <cbc:TaxInclusiveAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{data.get('moneda', 'PEN')}">{data['totalImportePagar']}</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{data.get('moneda', 'PEN')}">{data['totalImportePagar']}</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
{generate_invoice_lines_exact_format(data)}
</Invoice>'''

    return xml_content


def generate_invoice_lines_exact_format(data):
    """Generar líneas de items en el formato exacto del ejemplo"""
    lines = []
    
    for item in data['items']:
        igv_item = item.get('igv', float(item['valorTotal']) * 0.18)
        precio_con_igv = item.get('precioVentaUnitario', float(item['valorUnitario']) * 1.18)
        
        line = f'''  <cac:InvoiceLine xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{item['id']}</cbc:ID>
    <cbc:InvoicedQuantity xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" unitCode="{item.get('unidadMedida', 'NIU')}" unitCodeListAgencyName="United Nations Economic Commission for Europe" unitCodeListID="UN/ECE rec 20">{item['cantidad']}</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{data.get('moneda', 'PEN')}">{item['valorTotal']}</cbc:LineExtensionAmount>
    <cac:PricingReference>
      <cac:AlternativeConditionPrice>
        <cbc:PriceAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{data.get('moneda', 'PEN')}">{precio_con_igv:.0f}</cbc:PriceAmount>
        <cbc:PriceTypeCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="PE:SUNAT" listName="Tipo de Precio" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo16">{item.get('codigoTipoPrecio', '01')}</cbc:PriceTypeCode>
      </cac:AlternativeConditionPrice>
    </cac:PricingReference>
    <cac:TaxTotal>
      <cbc:TaxAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{data.get('moneda', 'PEN')}">{igv_item:.2f}</cbc:TaxAmount>
      <cac:TaxSubtotal>
        <cbc:TaxableAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{data.get('moneda', 'PEN')}">{item['valorTotal']}</cbc:TaxableAmount>
        <cbc:TaxAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{data.get('moneda', 'PEN')}">{igv_item:.2f}</cbc:TaxAmount>
        <cac:TaxCategory>
          <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="United Nations Economic Commission for Europe" schemeID="UN/ECE 5305" schemeName="Tax Category Identifier">S</cbc:ID>
          <cbc:Percent xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{item.get('porcentajeIGV', 18)}</cbc:Percent>
          <cbc:TaxExemptionReasonCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="PE:SUNAT" listName="Afectacion del IGV" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo07">{item.get('tipoAfectacionIGV', '10')}</cbc:TaxExemptionReasonCode>
          <cac:TaxScheme>
            <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeID="UN/ECE 5153" schemeName="Codigo de tributos">1000</cbc:ID>
            <cbc:Name xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">IGV</cbc:Name>
            <cbc:TaxTypeCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">VAT</cbc:TaxTypeCode>
          </cac:TaxScheme>
        </cac:TaxCategory>
      </cac:TaxSubtotal>
    </cac:TaxTotal>
    <cac:Item>
      <cbc:Description xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(item['descripcion'])}</cbc:Description>
      <cac:SellersItemIdentification>
        <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(item.get('codigoProducto', ''))}</cbc:ID>
      </cac:SellersItemIdentification>
      <cac:CommodityClassification>
        <cbc:ItemClassificationCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="GS1 US" listID="UNSPSC" listName="Item Classification">{item.get('unspsc', '10191509')}</cbc:ItemClassificationCode>
      </cac:CommodityClassification>
    </cac:Item>
    <cac:Price>
      <cbc:PriceAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{data.get('moneda', 'PEN')}">{item['valorUnitario']}</cbc:PriceAmount>
    </cac:Price>
  </cac:InvoiceLine>'''
        
        lines.append(line)
    
    return '\n'.join(lines)


def escape_xml(text):
    """Escapar caracteres especiales en XML"""
    if not text:
        return ""
    
    # Escapar caracteres XML básicos
    text = str(text)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    
    return text


def validate_xml_structure(xml_content):
    """Validar estructura del XML generado"""
    try:
        # Intentar parsear el XML
        root = ET.fromstring(xml_content.encode('utf-8'))
        
        # Verificar elementos obligatorios básicos
        required_elements = ['UBLVersionID', 'ID', 'IssueDate']
        
        for element_name in required_elements:
            found = False
            for elem in root.iter():
                if elem.tag.endswith(element_name):
                    found = True
                    break
            
            if not found:
                return {
                    'success': False,
                    'errors': [f'Elemento obligatorio no encontrado: {element_name}']
                }
        
        return {
            'success': True,
            'errors': []
        }
        
    except ET.ParseError as e:
        return {
            'success': False,
            'errors': [f'Error de sintaxis XML: {str(e)}']
        }
    except Exception as e:
        return {
            'success': False,
            'errors': [f'Error al validar XML: {str(e)}']
        }


def create_zip_file(xml_path, zip_path):
    """Crear archivo ZIP con el XML (requerido por SUNAT)"""
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            xml_filename = os.path.basename(xml_path)
            zipf.write(xml_path, xml_filename)
        return True
    except Exception as e:
        print(f"Error al crear ZIP: {str(e)}")
        return False


def validar_ruc_sunat(ruc):
    """Valida el RUC usando el algoritmo oficial de SUNAT"""
    if not ruc or len(ruc) != 11 or not ruc.isdigit():
        return False
    
    pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    primeros_10 = ruc[:10]
    digito_verificador = int(ruc[10])
    
    suma = 0
    for i in range(10):
        suma += int(primeros_10[i]) * pesos[i]
    
    resto = suma % 11
    digito_calculado = 11 - resto
    
    if digito_calculado == 11:
        digito_calculado = 0
    elif digito_calculado == 10:
        digito_calculado = 1
    
    return digito_calculado == digito_verificador


# Funciones de firma digital
try:
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from signxml import XMLSigner, methods
    SIGNING_AVAILABLE = True
    
    def extraer_clave_certificado_pfx(pfx_path, password):
        """Extrae la clave privada y el certificado del archivo PFX"""
        with open(pfx_path, 'rb') as f:
            pfx_data = f.read()
        private_key, cert, additional_certs = pkcs12.load_key_and_certificates(
            pfx_data, password.encode(), backend=default_backend()
        )
        cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        return private_key_pem, cert_pem

    def firmar_xml_ubl(xml_string, private_key, cert):
        """
        Firma el XML UBL 2.1 siguiendo el formato exacto del ejemplo proporcionado
        """
        print("🔍 Debug: Iniciando proceso de firma...")
        
        try:
            # Parsear el XML original
            root = ET.fromstring(xml_string.encode('utf-8'))
            print("🔍 Debug: XML parseado correctamente")

            # Firmar usando signxml
            print("🔍 Debug: Iniciando firma con signxml...")
            signer = XMLSigner(
                method=methods.enveloped,
                signature_algorithm="rsa-sha256",
                digest_algorithm="sha256",
                c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"
            )
            
            # Configurar atributos de la firma
            signed_root = signer.sign(root, key=private_key, cert=cert, reference_uri="")
            print("🔍 Debug: Firma completada con signxml")

            # Buscar el nodo de firma generado
            signature_node = None
            for elem in signed_root.iter():
                if elem.tag.endswith('Signature') and 'xmldsig' in elem.tag:
                    signature_node = elem
                    break
            
            if signature_node is None:
                print("❌ ERROR: No se generó el nodo <ds:Signature>")
                return xml_string
            
            print("🔍 Debug: Nodo <ds:Signature> encontrado")

            # Agregar el atributo Id="SignatureSP" al nodo de firma
            signature_node.set('Id', 'SignatureSP')

            # Buscar el nodo ExtensionContent
            extension_content = None
            for elem in signed_root.iter():
                if elem.tag.endswith('ExtensionContent'):
                    extension_content = elem
                    break
            
            if extension_content is None:
                print("❌ ERROR: No se encontró ExtensionContent")
                return xml_string
            
            print("🔍 Debug: Nodo ExtensionContent encontrado")

            # Limpiar ExtensionContent y mover la firma ahí
            extension_content.clear()
            
            # Remover la firma de su ubicación original
            signature_parent = signature_node.getparent()
            if signature_parent is not None:
                signature_parent.remove(signature_node)
            
            # Agregar la firma al ExtensionContent
            extension_content.append(signature_node)
            print("🔍 Debug: Firma movida a ExtensionContent")

            # Serializar el XML con la estructura correcta
            xml_firmado = ET.tostring(signed_root, encoding='utf-8', xml_declaration=False).decode('utf-8')
            
            # Agregar header XML
            xml_final = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_firmado
            
            print("🔍 Debug: XML firmado serializado correctamente")
            return xml_final
            
        except Exception as e:
            print(f"❌ Error en firma digital: {e}")
            import traceback
            traceback.print_exc()
            return xml_string

except ImportError:
    SIGNING_AVAILABLE = False
    
    def extraer_clave_certificado_pfx(pfx_path, password):
        raise ImportError("Librerías de firma digital no disponibles. Instalar: pip install cryptography signxml")
    
    def firmar_xml_ubl(xml_string, private_key, cert):
        print("⚠️  Librerías de firma digital no disponibles, retornando XML sin firma")
        return xml_string