# comprobantes/utils.py

import os
import zipfile
from datetime import datetime, date, time
from decimal import Decimal
from django.conf import settings

# Usar siempre xml.etree.ElementTree sin problemas de namespace
import xml.etree.ElementTree as ET

from lxml import etree as LET


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
    Generar XML UBL 2.1 COMPLETO, idéntico al ejemplo SUNAT, usando lxml.
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

    NSMAP = {
        None: 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
        'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
        'ds': 'http://www.w3.org/2000/09/xmldsig#'
    }
    root = LET.Element('Invoice', nsmap=NSMAP, Id=invoice_id)

    # PRIMERO: UBLExtensions y espacio para la firma (debe ser el primer hijo)
    ext_UBLExtensions = LET.Element(LET.QName(NSMAP['ext'], 'UBLExtensions'))
    ext_UBLExtension = LET.SubElement(ext_UBLExtensions, LET.QName(NSMAP['ext'], 'UBLExtension'))
    ext_ExtensionContent = LET.SubElement(ext_UBLExtension, LET.QName(NSMAP['ext'], 'ExtensionContent'))
    root.append(ext_UBLExtensions)
    # La firma digital se insertará aquí por el proceso de firmado

    # Cabecera UBL
    LET.SubElement(root, LET.QName(NSMAP['cbc'], 'UBLVersionID')).text = '2.1'
    LET.SubElement(root, LET.QName(NSMAP['cbc'], 'CustomizationID'), schemeAgencyName="PE:SUNAT").text = '2.0'
    LET.SubElement(root, LET.QName(NSMAP['cbc'], 'ProfileID'), schemeAgencyName="PE:SUNAT", schemeName="Tipo de Operacion", schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo51").text = '0101'
    LET.SubElement(root, LET.QName(NSMAP['cbc'], 'ID')).text = invoice_id
    LET.SubElement(root, LET.QName(NSMAP['cbc'], 'IssueDate')).text = fecha_emision
    LET.SubElement(root, LET.QName(NSMAP['cbc'], 'IssueTime')).text = hora_emision
    LET.SubElement(root, LET.QName(NSMAP['cbc'], 'DueDate')).text = fecha_emision
    LET.SubElement(root, LET.QName(NSMAP['cbc'], 'InvoiceTypeCode'), listAgencyName="PE:SUNAT", listID="0101", listName="Tipo de Documento", listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01", name="Tipo de Operacion").text = tipo_doc
    LET.SubElement(root, LET.QName(NSMAP['cbc'], 'DocumentCurrencyCode'), listAgencyName="United Nations Economic Commission for Europe", listID="ISO 4217 Alpha", listName="Currency").text = moneda
    LET.SubElement(root, LET.QName(NSMAP['cbc'], 'LineCountNumeric')).text = str(len(items))

    # Firma (Signature)
    cac_Signature = LET.SubElement(root, LET.QName(NSMAP['cac'], 'Signature'))
    LET.SubElement(cac_Signature, LET.QName(NSMAP['cbc'], 'ID')).text = invoice_id
    cac_SignatoryParty = LET.SubElement(cac_Signature, LET.QName(NSMAP['cac'], 'SignatoryParty'))
    cac_PartyIdentification = LET.SubElement(cac_SignatoryParty, LET.QName(NSMAP['cac'], 'PartyIdentification'))
    LET.SubElement(cac_PartyIdentification, LET.QName(NSMAP['cbc'], 'ID')).text = emisor.get('ruc', '')
    cac_PartyName = LET.SubElement(cac_SignatoryParty, LET.QName(NSMAP['cac'], 'PartyName'))
    LET.SubElement(cac_PartyName, LET.QName(NSMAP['cbc'], 'Name')).text = emisor.get('razonSocial', '')
    cac_DigitalSignatureAttachment = LET.SubElement(cac_Signature, LET.QName(NSMAP['cac'], 'DigitalSignatureAttachment'))
    cac_ExternalReference = LET.SubElement(cac_DigitalSignatureAttachment, LET.QName(NSMAP['cac'], 'ExternalReference'))
    # Cambiar URI a cadena vacía para SUNAT
    LET.SubElement(cac_ExternalReference, LET.QName(NSMAP['cbc'], 'URI')).text = ''

    # Proveedor (AccountingSupplierParty)
    cac_AccountingSupplierParty = LET.SubElement(root, LET.QName(NSMAP['cac'], 'AccountingSupplierParty'))
    cac_Party = LET.SubElement(cac_AccountingSupplierParty, LET.QName(NSMAP['cac'], 'Party'))
    cac_PartyIdentification = LET.SubElement(cac_Party, LET.QName(NSMAP['cac'], 'PartyIdentification'))
    LET.SubElement(cac_PartyIdentification, LET.QName(NSMAP['cbc'], 'ID'), schemeAgencyName="PE:SUNAT", schemeID="6", schemeName="Documento de Identidad", schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06").text = emisor.get('ruc', '')
    cac_PartyName = LET.SubElement(cac_Party, LET.QName(NSMAP['cac'], 'PartyName'))
    LET.SubElement(cac_PartyName, LET.QName(NSMAP['cbc'], 'Name')).text = emisor.get('razonSocial', '')
    cac_PartyTaxScheme = LET.SubElement(cac_Party, LET.QName(NSMAP['cac'], 'PartyTaxScheme'))
    LET.SubElement(cac_PartyTaxScheme, LET.QName(NSMAP['cbc'], 'RegistrationName')).text = emisor.get('razonSocial', '')
    LET.SubElement(cac_PartyTaxScheme, LET.QName(NSMAP['cbc'], 'CompanyID'), schemeAgencyName="PE:SUNAT", schemeID="6", schemeName="SUNAT:Identificador de Documento de Identidad", schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06").text = emisor.get('ruc', '')
    cac_TaxScheme = LET.SubElement(cac_PartyTaxScheme, LET.QName(NSMAP['cac'], 'TaxScheme'))
    LET.SubElement(cac_TaxScheme, LET.QName(NSMAP['cbc'], 'ID'), schemeAgencyName="PE:SUNAT", schemeID="6", schemeName="SUNAT:Identificador de Documento de Identidad", schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06").text = emisor.get('ruc', '')
    cac_PartyLegalEntity = LET.SubElement(cac_Party, LET.QName(NSMAP['cac'], 'PartyLegalEntity'))
    LET.SubElement(cac_PartyLegalEntity, LET.QName(NSMAP['cbc'], 'RegistrationName')).text = emisor.get('razonSocial', '')
    cac_RegistrationAddress = LET.SubElement(cac_PartyLegalEntity, LET.QName(NSMAP['cac'], 'RegistrationAddress'))
    LET.SubElement(cac_RegistrationAddress, LET.QName(NSMAP['cbc'], 'ID'), schemeAgencyName="PE:INEI", schemeName="Ubigeos").text = emisor.get('ubigeo', '')
    LET.SubElement(cac_RegistrationAddress, LET.QName(NSMAP['cbc'], 'AddressTypeCode'), listAgencyName="PE:SUNAT", listName="Establecimientos anexos").text = '0000'
    LET.SubElement(cac_RegistrationAddress, LET.QName(NSMAP['cbc'], 'CityName')).text = emisor.get('distrito', '')
    LET.SubElement(cac_RegistrationAddress, LET.QName(NSMAP['cbc'], 'CountrySubentity')).text = emisor.get('provincia', '')
    LET.SubElement(cac_RegistrationAddress, LET.QName(NSMAP['cbc'], 'District')).text = emisor.get('distrito', '')
    cac_AddressLine = LET.SubElement(cac_RegistrationAddress, LET.QName(NSMAP['cac'], 'AddressLine'))
    LET.SubElement(cac_AddressLine, LET.QName(NSMAP['cbc'], 'Line')).text = emisor.get('direccion', '')
    cac_Country = LET.SubElement(cac_RegistrationAddress, LET.QName(NSMAP['cac'], 'Country'))
    LET.SubElement(cac_Country, LET.QName(NSMAP['cbc'], 'IdentificationCode'), listAgencyName="United Nations Economic Commission for Europe", listID="ISO 3166-1", listName="Country").text = emisor.get('codigoPais', 'PE')
    cac_Contact = LET.SubElement(cac_Party, LET.QName(NSMAP['cac'], 'Contact'))
    LET.SubElement(cac_Contact, LET.QName(NSMAP['cbc'], 'Name')).text = ''

    # Cliente (AccountingCustomerParty)
    cac_AccountingCustomerParty = LET.SubElement(root, LET.QName(NSMAP['cac'], 'AccountingCustomerParty'))
    cac_Party = LET.SubElement(cac_AccountingCustomerParty, LET.QName(NSMAP['cac'], 'Party'))
    cac_PartyIdentification = LET.SubElement(cac_Party, LET.QName(NSMAP['cac'], 'PartyIdentification'))
    LET.SubElement(cac_PartyIdentification, LET.QName(NSMAP['cbc'], 'ID'), schemeAgencyName="PE:SUNAT", schemeID="6", schemeName="Documento de Identidad", schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06").text = cliente.get('numeroDoc', '')
    cac_PartyName = LET.SubElement(cac_Party, LET.QName(NSMAP['cac'], 'PartyName'))
    LET.SubElement(cac_PartyName, LET.QName(NSMAP['cbc'], 'Name')).text = cliente.get('razonSocial', '')
    cac_PartyTaxScheme = LET.SubElement(cac_Party, LET.QName(NSMAP['cac'], 'PartyTaxScheme'))
    LET.SubElement(cac_PartyTaxScheme, LET.QName(NSMAP['cbc'], 'RegistrationName')).text = cliente.get('razonSocial', '')
    LET.SubElement(cac_PartyTaxScheme, LET.QName(NSMAP['cbc'], 'CompanyID'), schemeAgencyName="PE:SUNAT", schemeID="6", schemeName="SUNAT:Identificador de Documento de Identidad", schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06").text = cliente.get('numeroDoc', '')
    cac_TaxScheme = LET.SubElement(cac_PartyTaxScheme, LET.QName(NSMAP['cac'], 'TaxScheme'))
    LET.SubElement(cac_TaxScheme, LET.QName(NSMAP['cbc'], 'ID'), schemeAgencyName="PE:SUNAT", schemeID="6", schemeName="SUNAT:Identificador de Documento de Identidad", schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06").text = cliente.get('numeroDoc', '')
    cac_PartyLegalEntity = LET.SubElement(cac_Party, LET.QName(NSMAP['cac'], 'PartyLegalEntity'))
    LET.SubElement(cac_PartyLegalEntity, LET.QName(NSMAP['cbc'], 'RegistrationName')).text = cliente.get('razonSocial', '')
    cac_RegistrationAddress = LET.SubElement(cac_PartyLegalEntity, LET.QName(NSMAP['cac'], 'RegistrationAddress'))
    LET.SubElement(cac_RegistrationAddress, LET.QName(NSMAP['cbc'], 'ID'), schemeAgencyName="PE:INEI", schemeName="Ubigeos").text = cliente.get('ubigeo', '130101')
    LET.SubElement(cac_RegistrationAddress, LET.QName(NSMAP['cbc'], 'AddressTypeCode'), listAgencyName="PE:SUNAT", listName="Establecimientos anexos").text = '0000'
    LET.SubElement(cac_RegistrationAddress, LET.QName(NSMAP['cbc'], 'CityName')).text = cliente.get('distrito', 'TRUJILLO')
    LET.SubElement(cac_RegistrationAddress, LET.QName(NSMAP['cbc'], 'CountrySubentity')).text = cliente.get('departamento', 'LA LIBERTAD')
    LET.SubElement(cac_RegistrationAddress, LET.QName(NSMAP['cbc'], 'District')).text = cliente.get('distrito', 'TRUJILLO')
    cac_AddressLine = LET.SubElement(cac_RegistrationAddress, LET.QName(NSMAP['cac'], 'AddressLine'))
    LET.SubElement(cac_AddressLine, LET.QName(NSMAP['cbc'], 'Line')).text = cliente.get('direccion', '')
    cac_Country = LET.SubElement(cac_RegistrationAddress, LET.QName(NSMAP['cac'], 'Country'))
    LET.SubElement(cac_Country, LET.QName(NSMAP['cbc'], 'IdentificationCode'), listAgencyName="United Nations Economic Commission for Europe", listID="ISO 3166-1", listName="Country").text = cliente.get('codigoPais', 'PE')
    cac_Contact = LET.SubElement(cac_Party, LET.QName(NSMAP['cac'], 'Contact'))
    LET.SubElement(cac_Contact, LET.QName(NSMAP['cbc'], 'Name')).text = ''

    # PaymentTerms
    cac_PaymentTerms = LET.SubElement(root, LET.QName(NSMAP['cac'], 'PaymentTerms'))
    LET.SubElement(cac_PaymentTerms, LET.QName(NSMAP['cbc'], 'ID')).text = 'FormaPago'
    LET.SubElement(cac_PaymentTerms, LET.QName(NSMAP['cbc'], 'PaymentMeansID')).text = data.get('formaPago', 'Contado')

    # TaxTotal
    cac_TaxTotal = LET.SubElement(root, LET.QName(NSMAP['cac'], 'TaxTotal'))
    LET.SubElement(cac_TaxTotal, LET.QName(NSMAP['cbc'], 'TaxAmount'), currencyID=moneda).text = str(total_igv)
    cac_TaxSubtotal = LET.SubElement(cac_TaxTotal, LET.QName(NSMAP['cac'], 'TaxSubtotal'))
    LET.SubElement(cac_TaxSubtotal, LET.QName(NSMAP['cbc'], 'TaxableAmount'), currencyID=moneda).text = str(total_gravado)
    LET.SubElement(cac_TaxSubtotal, LET.QName(NSMAP['cbc'], 'TaxAmount'), currencyID=moneda).text = str(total_igv)
    cac_TaxCategory = LET.SubElement(cac_TaxSubtotal, LET.QName(NSMAP['cac'], 'TaxCategory'))
    LET.SubElement(cac_TaxCategory, LET.QName(NSMAP['cbc'], 'ID'), schemeAgencyName="United Nations Economic Commission for Europe", schemeID="UN/ECE 5305", schemeName="Tax Category Identifier").text = 'S'
    LET.SubElement(cac_TaxCategory, LET.QName(NSMAP['cbc'], 'Percent')).text = '18'
    LET.SubElement(cac_TaxCategory, LET.QName(NSMAP['cbc'], 'TaxExemptionReasonCode'), listAgencyName="PE:SUNAT", listName="Afectacion del IGV", listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo07").text = '10'
    cac_TaxScheme = LET.SubElement(cac_TaxCategory, LET.QName(NSMAP['cac'], 'TaxScheme'))
    LET.SubElement(cac_TaxScheme, LET.QName(NSMAP['cbc'], 'ID'), schemeAgencyID="6", schemeID="UN/ECE 5153").text = '1000'
    LET.SubElement(cac_TaxScheme, LET.QName(NSMAP['cbc'], 'Name')).text = 'IGV'
    LET.SubElement(cac_TaxScheme, LET.QName(NSMAP['cbc'], 'TaxTypeCode')).text = 'VAT'

    # LegalMonetaryTotal
    cac_LegalMonetaryTotal = LET.SubElement(root, LET.QName(NSMAP['cac'], 'LegalMonetaryTotal'))
    LET.SubElement(cac_LegalMonetaryTotal, LET.QName(NSMAP['cbc'], 'LineExtensionAmount'), currencyID=moneda).text = str(total_gravado)
    LET.SubElement(cac_LegalMonetaryTotal, LET.QName(NSMAP['cbc'], 'TaxInclusiveAmount'), currencyID=moneda).text = str(total_importe)
    LET.SubElement(cac_LegalMonetaryTotal, LET.QName(NSMAP['cbc'], 'PayableAmount'), currencyID=moneda).text = str(total_importe)

    # InvoiceLine(s)
    for idx, item in enumerate(items, 1):
        cac_InvoiceLine = LET.SubElement(root, LET.QName(NSMAP['cac'], 'InvoiceLine'))
        LET.SubElement(cac_InvoiceLine, LET.QName(NSMAP['cbc'], 'ID')).text = str(idx)
        LET.SubElement(cac_InvoiceLine, LET.QName(NSMAP['cbc'], 'InvoicedQuantity'), unitCode=item.get('unidadMedida', 'NIU'), unitCodeListAgencyName="United Nations Economic Commission for Europe", unitCodeListID="UN/ECE rec 20").text = str(item.get('cantidad', 1))
        LET.SubElement(cac_InvoiceLine, LET.QName(NSMAP['cbc'], 'LineExtensionAmount'), currencyID=moneda).text = str(item.get('valorTotal', '0.00'))
        cac_PricingReference = LET.SubElement(cac_InvoiceLine, LET.QName(NSMAP['cac'], 'PricingReference'))
        cac_AlternativeConditionPrice = LET.SubElement(cac_PricingReference, LET.QName(NSMAP['cac'], 'AlternativeConditionPrice'))
        LET.SubElement(cac_AlternativeConditionPrice, LET.QName(NSMAP['cbc'], 'PriceAmount'), currencyID=moneda).text = str(item.get('precioVentaUnitario', '0.00'))
        LET.SubElement(cac_AlternativeConditionPrice, LET.QName(NSMAP['cbc'], 'PriceTypeCode'), listAgencyName="PE:SUNAT", listName="Tipo de Precio", listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo16").text = '01'
        cac_TaxTotal = LET.SubElement(cac_InvoiceLine, LET.QName(NSMAP['cac'], 'TaxTotal'))
        LET.SubElement(cac_TaxTotal, LET.QName(NSMAP['cbc'], 'TaxAmount'), currencyID=moneda).text = str(item.get('igv', '0.00'))
        cac_TaxSubtotal = LET.SubElement(cac_TaxTotal, LET.QName(NSMAP['cac'], 'TaxSubtotal'))
        LET.SubElement(cac_TaxSubtotal, LET.QName(NSMAP['cbc'], 'TaxableAmount'), currencyID=moneda).text = str(item.get('valorTotal', '0.00'))
        LET.SubElement(cac_TaxSubtotal, LET.QName(NSMAP['cbc'], 'TaxAmount'), currencyID=moneda).text = str(item.get('igv', '0.00'))
        cac_TaxCategory = LET.SubElement(cac_TaxSubtotal, LET.QName(NSMAP['cac'], 'TaxCategory'))
        LET.SubElement(cac_TaxCategory, LET.QName(NSMAP['cbc'], 'ID'), schemeAgencyName="United Nations Economic Commission for Europe", schemeID="UN/ECE 5305", schemeName="Tax Category Identifier").text = 'S'
        LET.SubElement(cac_TaxCategory, LET.QName(NSMAP['cbc'], 'Percent')).text = '18'
        LET.SubElement(cac_TaxCategory, LET.QName(NSMAP['cbc'], 'TaxExemptionReasonCode'), listAgencyName="PE:SUNAT", listName="Afectacion del IGV", listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo07").text = '10'
        cac_TaxScheme = LET.SubElement(cac_TaxCategory, LET.QName(NSMAP['cac'], 'TaxScheme'))
        LET.SubElement(cac_TaxScheme, LET.QName(NSMAP['cbc'], 'ID'), schemeAgencyName="PE:SUNAT", schemeID="UN/ECE 5153", schemeName="Codigo de tributos").text = '1000'
        LET.SubElement(cac_TaxScheme, LET.QName(NSMAP['cbc'], 'Name')).text = 'IGV'
        LET.SubElement(cac_TaxScheme, LET.QName(NSMAP['cbc'], 'TaxTypeCode')).text = 'VAT'
        cac_Item = LET.SubElement(cac_InvoiceLine, LET.QName(NSMAP['cac'], 'Item'))
        LET.SubElement(cac_Item, LET.QName(NSMAP['cbc'], 'Description')).text = item.get('descripcion', '')
        cac_SellersItemIdentification = LET.SubElement(cac_Item, LET.QName(NSMAP['cac'], 'SellersItemIdentification'))
        LET.SubElement(cac_SellersItemIdentification, LET.QName(NSMAP['cbc'], 'ID')).text = item.get('codigoProducto', '')
        cac_CommodityClassification = LET.SubElement(cac_Item, LET.QName(NSMAP['cac'], 'CommodityClassification'))
        LET.SubElement(cac_CommodityClassification, LET.QName(NSMAP['cbc'], 'ItemClassificationCode'), listAgencyName="GS1 US", listID="UNSPSC", listName="Item Classification").text = item.get('unspsc', '')
        cac_Price = LET.SubElement(cac_InvoiceLine, LET.QName(NSMAP['cac'], 'Price'))
        LET.SubElement(cac_Price, LET.QName(NSMAP['cbc'], 'PriceAmount'), currencyID=moneda).text = str(item.get('valorTotal', '0.00'))

    xml_content = LET.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    return xml_content.decode('utf-8')


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
    from lxml import etree as LET
    SIGNING_AVAILABLE = True
    
    def firmar_xml_ubl(xml_path, pfx_path, pfx_password):
        print('🔍 Debug: Iniciando proceso de firma con lxml...')
        parser = LET.XMLParser(remove_blank_text=True)
        with open(xml_path, 'rb') as f:
            xml_data = f.read()
        root = LET.fromstring(xml_data, parser=parser)
        print('🔍 Debug: XML parseado correctamente con lxml')

        # Asegurar que el nodo raíz tenga solo el atributo Id (no ID)
        nsmap = {
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
        }
        invoice_id_elem = root.find('.//cbc:ID', namespaces=nsmap)
        invoice_id = invoice_id_elem.text if invoice_id_elem is not None else 'F001-123'
        root.attrib.pop('ID', None)  # Eliminar si existe
        root.set('Id', invoice_id)
        # Registrar el atributo Id como tipo ID en lxml para signxml
        from lxml import etree
        etree.ElementTree(root).getroot().set('Id', invoice_id)
        try:
            etree.ElementTree(root).getroot().set_id_attribute('Id')
            print('🔍 set_id_attribute aplicado correctamente')
        except Exception as e:
            print(f"set_id_attribute no soportado: {e}")
        print(f'✅ Nodo raíz con atributo Id: {invoice_id}')
        print(f'🔍 Atributos del nodo raíz antes de firmar: {root.attrib}')

        # Registrar el atributo Id como tipo ID en lxml
        LET.cleanup_namespaces(root)
        root_id_attr = root.attrib.get('Id')
        if root_id_attr:
            root_id_element = root
            # lxml requiere registrar el atributo como tipo ID usando set_id_attribute
            # Pero signxml lo detecta automáticamente si el atributo es exactamente 'Id'
            pass  # No se requiere código extra aquí para signxml
        print(f'🔍 Atributo Id listo para firma: {root.attrib.get("Id")}')

        # Extraer clave y certificado
        with open(pfx_path, 'rb') as f:
            pfx_data = f.read()
        private_key, cert, _ = pkcs12.load_key_and_certificates(
            pfx_data, pfx_password.encode(), backend=default_backend())
        from cryptography.hazmat.primitives import serialization
        cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)

        # Buscar el nodo <ext:ExtensionContent> (solo para verificar que existe)
        nsmap = {
            'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'ds': 'http://www.w3.org/2000/09/xmldsig#'
        }
        ext_content = root.find('.//ext:ExtensionContent', namespaces=nsmap)
        if ext_content is None:
            raise Exception('No se encontró <ext:ExtensionContent>')

        # Firmar el nodo raíz (root) para UBL/SUNAT
        signer = XMLSigner(
            method=methods.enveloped,
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
            c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"
        )
        print('🔍 Debug: Iniciando firma con signxml (enveloped en nodo raíz)...')
        signed_root = signer.sign(
            root,
            key=private_key,
            cert=cert_pem,
            reference_uri="#" + invoice_id,
            always_add_key_value=False,
            signature_properties={"Id": "SignatureSP"}
        )
        print('🔍 Debug: Firma completada con signxml')

        # No mover la firma, solo serializar el XML firmado tal cual
        xml_firmado = LET.tostring(
            signed_root,
            pretty_print=False,
            xml_declaration=True,
            encoding='UTF-8',
            standalone=None
        )
        with open(xml_path.replace('.xml', '_con_firma.xml'), 'wb') as f:
            f.write(xml_firmado)
        print(f'✅ XML firmado guardado como: {xml_path.replace(".xml", "_con_firma.xml")})')
        return xml_firmado

except ImportError:
    SIGNING_AVAILABLE = False
    
    def extraer_clave_certificado_pfx(pfx_path, password):
        raise ImportError("Librerías de firma digital no disponibles. Instalar: pip install cryptography signxml")
    
    def firmar_xml_ubl(xml_string, private_key, cert):
        print("⚠️  Librerías de firma digital no disponibles, retornando XML sin firma")
        return xml_string