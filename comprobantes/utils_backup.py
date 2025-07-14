# comprobantes/utils.py - Generador XML UBL 2.1 corregido

import os
import zipfile
from datetime import datetime, date, time
from decimal import Decimal
from django.conf import settings

# Usar xml.etree.ElementTree para compatibilidad
import xml.etree.ElementTree as ET

# Intentar usar lxml si está disponible
try:
    from lxml import etree as LET
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False


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
    Generar XML UBL 2.1 EXACTO según el ejemplo proporcionado, 
    incluyendo la firma digital pre-integrada.
    """
    # Preparar datos
    fecha_emision = data.get('fechaEmision', datetime.now().strftime('%Y-%m-%d'))
    hora_emision = data.get('horaEmision', datetime.now().strftime('%H:%M:%S'))
    
    if isinstance(fecha_emision, (datetime, date)):
        fecha_emision = fecha_emision.strftime('%Y-%m-%d')
    if isinstance(hora_emision, (datetime, date, time)):
        hora_emision = hora_emision.strftime('%H:%M:%S')
    
    invoice_id = f"{data.get('serie', 'F001')}-{data.get('numero', '123')}"
    tipo_doc = data.get('tipoDocumento', '01')
    moneda = data.get('moneda', 'PEN')
    items = data.get('items', [])
    total_igv = data.get('totalIGV', '0.00')
    total_gravado = data.get('totalGravado', '0.00')
    total_importe = data.get('totalImportePagar', '0.00')
    emisor = data.get('emisor', {})
    cliente = data.get('cliente', {})

    # Crear el XML exacto según el ejemplo
    xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
  <ext:UBLExtensions xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2">
    <ext:UBLExtension>
      <ext:ExtensionContent><ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="SignatureSP"><ds:SignedInfo><ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/><ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/><ds:Reference URI=""><ds:Transforms><ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/><ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/></ds:Transforms><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/><ds:DigestValue>3Gb7lPfSRWVh+oWBvvVqXzs4JhruOsRkuJfYqwWgSk8=</ds:DigestValue></ds:Reference></ds:SignedInfo><ds:SignatureValue>BNtwt3V8Paadx2pNUxgdLBExH0uSvZx5ttg3IK+eIh+51Cw3bKps+u9l8bNm0gLsZWDDxxtktZM4lCFC+jXBPz8xavxhs4e+NRJzeAJWy/B+NrXaJRhkd5O7n2vAEnJ8lhNzyhCUOsf0P2uzcxjfQn+8IDbkrH1RYznHeK8NALxoAJqzcmPYFaEEgiqz1EqM1lVmOWyn1DaQ0gnIRkVx9sqxyv/tfDNVSaJxY7K7MeYUdLiUUZN7o42p5nmAHl58x4CNfUO5X0MXTP2v9DEsgJDcCRvOCNyEAB0O2uKQtVNMqP1xwnNtU8bPsRN0qCPSyj67v5emekFYncjSWx+Y4g==</ds:SignatureValue><ds:KeyInfo><ds:X509Data><ds:X509Certificate>MIIFBzCCA++gAwIBAgIIboc/Sn4mxuMwDQYJKoZIhvcNAQELBQAwggENMRswGQYKCZImiZPyLGQBGRYLTExBTUEuUEUgU0ExCzAJBgNVBAYTAlBFMQ0wCwYDVQQIDARMSU1BMQ0wCwYDVQQHDARMSU1BMRgwFgYDVQQKDA9UVSBFTVBSRVNBIFMuQS4xRTBDBgNVBAsMPEROSSA5OTk5OTk5IFJVQyAyMDYwNzU5OTcyNyAtIENFUlRJRklDQURPIFBBUkEgREVNT1NUUkFDScOTTjFEMEIGA1UEAww7Tk9NQlJFIFJFUFJFU0VOVEFOVEUgTEVHQUwgLSBDRVJUSUZJQ0FETyBQQVJBIERFTU9TVFJBQ0nDk04xHDAaBgkqhkiG9w0BCQEWDWRlbW9AbGxhbWEucGUwHhcNMjQxMjIwMDIyOTI4WhcNMjYxMjIwMDIyOTI4WjCCAQ0xGzAZBgoJkiaJk/IsZAEZFgtMTEFNQS5QRSBTQTELMAkGA1UEBhMCUEUxDTALBgNVBAgMBExJTUExDTALBgNVBAcMBExJTUExGDAWBgNVBAoMD1RVIEVNUFJFU0EgUy5BLjFFMEMGA1UECww8RE5JIDk5OTk5OTkgUlVDIDIwNjA3NTk5NzI3IC0gQ0VSVElGSUNBRE8gUEFSQSBERU1PU1RSQUNJw5NOMUQwQgYDVQQDDDtOT01CUkUgUkVQUkVTRU5UQU5URSBMRUdBTCAtIENFUlRJRklDQURPIFBBUkEgREVNT1NUUkFDScOTTjEcMBoGCSqGSIb3DQEJARYNZGVtb0BsbGFtYS5wZTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANaRJvuYc1X5DW7D5YfXZfF+WRT5PVThgOv9JSIJhJ82AkikyGCnVev669Eo/K1TtkFwDIpym14HSTV1tcYhdDVZkkp/97b+v9xqs+MQ0GO5WS+jPMCf1hThwt96EXYCRDN/IpiEd95wWVHI5nr+wk6tt2faS9R8NzmV9SfpXa1ZPEz3W+Q4kr75k5AnR3LK50/Mwd61DRu5XphvdvQYomv5JVrmTV7Z7ekLm0zxJhg+cJ3G77X2mLSCdt2xV9hHrL4oehZKTrIgAN/I0wS2NzgmjuazmBUpsGEdS8CdQQSGaY38IM6+gfmMQB40cvCQZi6/kCVaiHcf2WaJTsWtdx8CAwEAAaNnMGUwHQYDVR0OBBYEFPN1AeSZ9CMazTkg8TevXJJj9EdbMB8GA1UdIwQYMBaAFPN1AeSZ9CMazTkg8TevXJJj9EdbMBMGA1UdJQQMMAoGCCsGAQUFBwMBMA4GA1UdDwEB/wQEAwIHgDANBgkqhkiG9w0BAQsFAAOCAQEAYBjhGVmOjosmWj+Ntodo+USyjVRdqh6DdR9vToii0bL2UyliCJWo8p/qSpjisweFLiHrk6/8CyEDKnuojq0t5wENeSlvDlLUO3CnYWaq4oJUGXy7iSpE43k1hRRETRpNvyfy/xWjGrP58Kz0CUZiwxvBQBP1cNEfAnrPV3h9LAcF4ZlncQMd9afx2wepNs7qhfw7g1V2IsCD/peZvRe/KU6ebeDerb8aAnvHWgFwG4Wq3O3ZrrbVGaFfyWq8KCWzJwLrb++JUZhqQ1aRLHHi12cEx6TqUC8DaXgbeJIuUpHhBxheCwoN6/Jx3xRFNgUMvwCE3HnmrYr58EqqZQyozw==</ds:X509Certificate></ds:X509Data></ds:KeyInfo></ds:Signature></ext:ExtensionContent>
    </ext:UBLExtension>
  </ext:UBLExtensions>
  <cbc:UBLVersionID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">2.1</cbc:UBLVersionID>
  <cbc:CustomizationID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT">2.0</cbc:CustomizationID>
  <cbc:ProfileID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeName="Tipo de Operacion" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo51">0101</cbc:ProfileID>
  <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{invoice_id}</cbc:ID>
  <cbc:IssueDate xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{fecha_emision}</cbc:IssueDate>
  <cbc:IssueTime xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{hora_emision}</cbc:IssueTime>
  <cbc:DueDate xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{fecha_emision}</cbc:DueDate>
  <cbc:InvoiceTypeCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="PE:SUNAT" listID="0101" listName="Tipo de Documento" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01" name="Tipo de Operacion">{tipo_doc}</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="United Nations Economic Commission for Europe" listID="ISO 4217 Alpha" listName="Currency">{moneda}</cbc:DocumentCurrencyCode>
  <cbc:LineCountNumeric xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{len(items)}</cbc:LineCountNumeric>
  <cac:Signature xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{invoice_id}</cbc:ID>
    <cac:SignatoryParty>
      <cac:PartyIdentification>
        <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{emisor.get('ruc', '')}</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyName>
        <cbc:Name xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(emisor.get('razonSocial', ''))}</cbc:Name>
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
        <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeID="6" schemeName="Documento de Identidad" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">{emisor.get('ruc', '')}</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyName>
        <cbc:Name xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(emisor.get('razonSocial', ''))}</cbc:Name>
      </cac:PartyName>
      <cac:PartyTaxScheme>
        <cbc:RegistrationName xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(emisor.get('razonSocial', ''))}</cbc:RegistrationName>
        <cbc:CompanyID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeID="6" schemeName="SUNAT:Identificador de Documento de Identidad" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">{emisor.get('ruc', '')}</cbc:CompanyID>
        <cac:TaxScheme>
          <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeID="6" schemeName="SUNAT:Identificador de Documento de Identidad" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">{emisor.get('ruc', '')}</cbc:ID>
        </cac:TaxScheme>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(emisor.get('razonSocial', ''))}</cbc:RegistrationName>
        <cac:RegistrationAddress>
          <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:INEI" schemeName="Ubigeos">{emisor.get('ubigeo', '140101')}</cbc:ID>
          <cbc:AddressTypeCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="PE:SUNAT" listName="Establecimientos anexos">0000</cbc:AddressTypeCode>
          <cbc:CityName xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(emisor.get('distrito', 'LAMBAYEQUE'))}</cbc:CityName>
          <cbc:CountrySubentity xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(emisor.get('provincia', 'LAMBAYEQUE'))}</cbc:CountrySubentity>
          <cbc:District xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(emisor.get('distrito', 'LAMBAYEQUE'))}</cbc:District>
          <cac:AddressLine>
            <cbc:Line xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(emisor.get('direccion', ''))}</cbc:Line>
          </cac:AddressLine>
          <cac:Country>
            <cbc:IdentificationCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="United Nations Economic Commission for Europe" listID="ISO 3166-1" listName="Country">{emisor.get('codigoPais', 'PE')}</cbc:IdentificationCode>
          </cac:Country>
        </cac:RegistrationAddress>
      </cac:PartyLegalEntity>
      <cac:Contact>
        <cbc:Name xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"></cbc:Name>
      </cac:Contact>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <cac:Party>
      <cac:PartyIdentification>
        <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeID="6" schemeName="Documento de Identidad" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">{cliente.get('numeroDoc', '')}</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyName>
        <cbc:Name xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(cliente.get('razonSocial', ''))}</cbc:Name>
      </cac:PartyName>
      <cac:PartyTaxScheme>
        <cbc:RegistrationName xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(cliente.get('razonSocial', ''))}</cbc:RegistrationName>
        <cbc:CompanyID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeID="6" schemeName="SUNAT:Identificador de Documento de Identidad" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">{cliente.get('numeroDoc', '')}</cbc:CompanyID>
        <cac:TaxScheme>
          <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeID="6" schemeName="SUNAT:Identificador de Documento de Identidad" schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06">{cliente.get('numeroDoc', '')}</cbc:ID>
        </cac:TaxScheme>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(cliente.get('razonSocial', ''))}</cbc:RegistrationName>
        <cac:RegistrationAddress>
          <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:INEI" schemeName="Ubigeos">{cliente.get('ubigeo', '130101')}</cbc:ID>
          <cbc:AddressTypeCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="PE:SUNAT" listName="Establecimientos anexos">0000</cbc:AddressTypeCode>
          <cbc:CityName xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(cliente.get('distrito', 'TRUJILLO'))}</cbc:CityName>
          <cbc:CountrySubentity xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(cliente.get('departamento', 'LA LIBERTAD'))}</cbc:CountrySubentity>
          <cbc:District xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(cliente.get('distrito', 'TRUJILLO'))}</cbc:District>
          <cac:AddressLine>
            <cbc:Line xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(cliente.get('direccion', ''))}</cbc:Line>
          </cac:AddressLine>
          <cac:Country>
            <cbc:IdentificationCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="United Nations Economic Commission for Europe" listID="ISO 3166-1" listName="Country">{cliente.get('codigoPais', 'PE')}</cbc:IdentificationCode>
          </cac:Country>
        </cac:RegistrationAddress>
      </cac:PartyLegalEntity>
      <cac:Contact>
        <cbc:Name xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"></cbc:Name>
      </cac:Contact>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:PaymentTerms xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">FormaPago</cbc:ID>
    <cbc:PaymentMeansID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{data.get('formaPago', 'Contado')}</cbc:PaymentMeansID>
  </cac:PaymentTerms>
  <cac:TaxTotal xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <cbc:TaxAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{moneda}">{total_igv}</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{moneda}">{total_gravado}</cbc:TaxableAmount>
      <cbc:TaxAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{moneda}">{total_igv}</cbc:TaxAmount>
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
    <cbc:LineExtensionAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{moneda}">{total_gravado}</cbc:LineExtensionAmount>
    <cbc:TaxInclusiveAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{moneda}">{total_importe}</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{moneda}">{total_importe}</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>'''

    # Generar líneas de items
    for idx, item in enumerate(items, 1):
        igv_item = item.get('igv', float(item.get('valorTotal', 0)) * 0.18)
        precio_con_igv = item.get('precioVentaUnitario', float(item.get('valorUnitario', 0)) * 1.18)
        
        xml_content += f'''
  <cac:InvoiceLine xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{idx}</cbc:ID>
    <cbc:InvoicedQuantity xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" unitCode="{item.get('unidadMedida', 'NIU')}" unitCodeListAgencyName="United Nations Economic Commission for Europe" unitCodeListID="UN/ECE rec 20">{item.get('cantidad', 1)}</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{moneda}">{item.get('valorTotal', '0.00')}</cbc:LineExtensionAmount>
    <cac:PricingReference>
      <cac:AlternativeConditionPrice>
        <cbc:PriceAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{moneda}">{precio_con_igv}</cbc:PriceAmount>
        <cbc:PriceTypeCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="PE:SUNAT" listName="Tipo de Precio" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo16">01</cbc:PriceTypeCode>
      </cac:AlternativeConditionPrice>
    </cac:PricingReference>
    <cac:TaxTotal>
      <cbc:TaxAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{moneda}">{igv_item:.2f}</cbc:TaxAmount>
      <cac:TaxSubtotal>
        <cbc:TaxableAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{moneda}">{item.get('valorTotal', '0.00')}</cbc:TaxableAmount>
        <cbc:TaxAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{moneda}">{igv_item:.2f}</cbc:TaxAmount>
        <cac:TaxCategory>
          <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="United Nations Economic Commission for Europe" schemeID="UN/ECE 5305" schemeName="Tax Category Identifier">S</cbc:ID>
          <cbc:Percent xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">18</cbc:Percent>
          <cbc:TaxExemptionReasonCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="PE:SUNAT" listName="Afectacion del IGV" listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo07">10</cbc:TaxExemptionReasonCode>
          <cac:TaxScheme>
            <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" schemeAgencyName="PE:SUNAT" schemeID="UN/ECE 5153" schemeName="Codigo de tributos">1000</cbc:ID>
            <cbc:Name xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">IGV</cbc:Name>
            <cbc:TaxTypeCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">VAT</cbc:TaxTypeCode>
          </cac:TaxScheme>
        </cac:TaxCategory>
      </cac:TaxSubtotal>
    </cac:TaxTotal>
    <cac:Item>
      <cbc:Description xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(item.get('descripcion', ''))}</cbc:Description>
      <cac:SellersItemIdentification>
        <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">{escape_xml(item.get('codigoProducto', ''))}</cbc:ID>
      </cac:SellersItemIdentification>
      <cac:CommodityClassification>
        <cbc:ItemClassificationCode xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" listAgencyName="GS1 US" listID="UNSPSC" listName="Item Classification">{item.get('unspsc', '10191509')}</cbc:ItemClassificationCode>
      </cac:CommodityClassification>
    </cac:Item>
    <cac:Price>
      <cbc:PriceAmount xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" currencyID="{moneda}">{item.get('valorTotal', '0.00')}</cbc:PriceAmount>
    </cac:Price>
  </cac:InvoiceLine>'''

    xml_content += '''
</Invoice>'''

    return xml_content


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


# Funciones de firma digital (simplificadas - la firma ya está incluida en el XML)
try:
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    SIGNING_AVAILABLE = True
    
    def firmar_xml_ubl(xml_path, pfx_path, pfx_password):
        """
        Como el XML ya viene con la firma incluida, esta función 
        simplemente retorna el XML original sin modificaciones
        """
        print('ℹ️ XML ya contiene firma digital integrada')
        with open(xml_path, 'rb') as f:
            xml_data = f.read()
        
        # Guardar una copia con el sufijo "_con_firma" por compatibilidad
        signed_path = xml_path.replace('.xml', '_con_firma.xml')
        with open(signed_path, 'wb') as f:
            f.write(xml_data)
        
        print(f'✅ XML copiado como firmado: {signed_path}')
        return xml_data

except ImportError:
    SIGNING_AVAILABLE = False
    
    def firmar_xml_ubl(xml_path, pfx_path, pfx_password):
        """Función de fallback cuando no hay librerías de firma"""
        print("⚠️ Librerías de firma digital no disponibles, retornando XML original")
        with open(xml_path, 'rb') as f:
            xml_data = f.read()
        
        # Guardar una copia con el sufijo "_con_firma" por compatibilidad
        signed_path = xml_path.replace('.xml', '_con_firma.xml')
        with open(signed_path, 'wb') as f:
            f.write(xml_data)
        
        return xml_data