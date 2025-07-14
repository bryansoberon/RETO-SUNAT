import os
import zipfile
import uuid
from datetime import datetime
from decimal import Decimal
from django.conf import settings

# Intentar usar lxml, si no está disponible usar xml.etree.ElementTree
try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    import xml.etree.ElementTree as etree
    LXML_AVAILABLE = False
    print("⚠️  lxml no disponible, usando xml.etree.ElementTree (más lento)")

from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
import base64
from signxml import XMLSigner, methods
from cryptography.hazmat.primitives import serialization


def validate_comprobante_data(data):
    """
    Validar datos específicos de SUNAT con nueva estructura JSON
    """
    errors = []
    
    # Validar RUC emisor (debe ser 11 dígitos)
    if len(data['emisor']['ruc']) != 11:
        errors.append("El RUC emisor debe tener 11 dígitos")
    
    # Validar número de documento del cliente según tipo de comprobante
    tipo_doc = data['tipoDocumento']
    cliente = data['cliente']
    
    if tipo_doc == '01':  # Factura
        if cliente.get('tipoDoc') != '6' or len(cliente['numeroDoc']) != 11:
            errors.append("Para facturas, el cliente debe tener RUC (tipoDoc=6, 11 dígitos)")
    elif tipo_doc == '03':  # Boleta
        if cliente.get('tipoDoc') != '1' or len(cliente['numeroDoc']) != 8:
            errors.append("Para boletas, el cliente debe tener DNI (tipoDoc=1, 8 dígitos)")
    
    # Validar serie (máximo 4 caracteres)
    if len(data['serie']) > 4:
        errors.append("La serie no puede tener más de 4 caracteres")
    
    # Validar número (máximo 8 caracteres)
    if len(data['numero']) > 8:
        errors.append("El número no puede tener más de 8 caracteres")
    
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
    Generar XML UBL 2.1 específicamente optimizado para NubeFacT
    """
    # Crear elemento raíz con namespace por defecto correcto para NubeFacT
    root = etree.Element('{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice')
    
    # Establecer namespaces en el orden EXACTO que NubeFacT espera
    root.set('xmlns', 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2')
    root.set('xmlns:cac', 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2')
    root.set('xmlns:cbc', 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2')
    root.set('xmlns:ccts', 'urn:un:unece:uncefact:documentation:2')
    root.set('xmlns:ds', 'http://www.w3.org/2000/09/xmldsig#')
    root.set('xmlns:ext', 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2')
    root.set('xmlns:qdt', 'urn:oasis:names:specification:ubl:schema:xsd:QualifiedDatatypes-2')
    root.set('xmlns:udt', 'urn:un:unece:uncefact:data:specification:UnqualifiedDataTypesSchemaModule:2')
    root.set('xmlns:xsd', 'http://www.w3.org/2001/XMLSchema')
    root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    root.set('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation', 
             'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2')
    
    # UBLExtensions DEBE ser el primer elemento
    ubl_extensions = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}UBLExtensions')
    ubl_extension = etree.SubElement(ubl_extensions, '{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}UBLExtension')
    etree.SubElement(ubl_extension, '{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}ExtensionContent')
    
    # Elementos básicos en orden estricto
    add_basic_elements_nubefact(root, data)
    
    # AccountingSupplierParty DEBE ir antes que AccountingCustomerParty
    add_supplier_party_nubefact(root, data)
    
    # AccountingCustomerParty
    add_customer_party_nubefact(root, data)
    
    # PaymentTerms
    add_payment_terms(root, data)
    
    # TaxTotal
    add_tax_total_nubefact(root, data)
    
    # LegalMonetaryTotal
    add_legal_monetary_total_nubefact(root, data)
    
    # InvoiceLine
    add_invoice_lines_nubefact(root, data)
    
    # Generar XML con formato específico
    xml_str = etree.tostring(root, encoding='utf-8', xml_declaration=False, pretty_print=True).decode('utf-8')
    header = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
    
    return header + xml_str


def add_basic_elements_nubefact(root, data):
    """Elementos básicos en orden específico para NubeFacT"""
    # UBLVersionID
    ubl_version = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}UBLVersionID')
    ubl_version.text = '2.1'
    
    # CustomizationID
    customization_id = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CustomizationID')
    customization_id.set('schemeAgencyName', 'PE:SUNAT')
    customization_id.text = '2.0'
    
    # ProfileID
    profile_id = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ProfileID')
    profile_id.set('schemeAgencyName', 'PE:SUNAT')
    profile_id.set('schemeName', 'Tipo de Operacion')
    profile_id.set('schemeURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo51')
    profile_id.text = '0101'
    
    # ID
    id_element = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
    id_element.text = f"{data['serie']}-{data['numero']}"
    
    # IssueDate
    issue_date = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IssueDate')
    if data.get('fechaEmision'):
        if isinstance(data['fechaEmision'], str):
            issue_date.text = data['fechaEmision']
        else:
            issue_date.text = data['fechaEmision'].strftime('%Y-%m-%d')
    else:
        issue_date.text = datetime.now().strftime('%Y-%m-%d')
    
    # IssueTime
    issue_time = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IssueTime')
    if data.get('horaEmision'):
        if isinstance(data['horaEmision'], str):
            issue_time.text = data['horaEmision']
        else:
            issue_time.text = data['horaEmision'].strftime('%H:%M:%S')
    else:
        issue_time.text = datetime.now().strftime('%H:%M:%S')
    
    # DueDate
    due_date = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}DueDate')
    if data.get('fechaEmision'):
        if isinstance(data['fechaEmision'], str):
            due_date.text = data['fechaEmision']
        else:
            due_date.text = data['fechaEmision'].strftime('%Y-%m-%d')
    else:
        due_date.text = datetime.now().strftime('%Y-%m-%d')
    
    # InvoiceTypeCode
    invoice_type_code = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoiceTypeCode')
    invoice_type_code.set('listAgencyName', 'PE:SUNAT')
    invoice_type_code.set('listID', '0101')
    invoice_type_code.set('listName', 'Tipo de Documento')
    invoice_type_code.set('listURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01')
    invoice_type_code.set('name', 'Tipo de Operacion')
    invoice_type_code.text = data['tipoDocumento']
    
    # DocumentCurrencyCode
    currency_code = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}DocumentCurrencyCode')
    currency_code.set('listAgencyName', 'United Nations Economic Commission for Europe')
    currency_code.set('listID', 'ISO 4217 Alpha')
    currency_code.set('listName', 'Currency')
    currency_code.text = data.get('moneda', 'PEN')
    
    # LineCountNumeric
    line_count = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}LineCountNumeric')
    line_count.text = str(len(data['items']))


def add_supplier_party_nubefact(root, data):
    """Emisor optimizado para NubeFacT"""
    accounting_supplier_party = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}AccountingSupplierParty')
    party = etree.SubElement(accounting_supplier_party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Party')
    
    # PartyIdentification - CRÍTICO para NubeFacT
    party_identification = etree.SubElement(party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyIdentification')
    id_element = etree.SubElement(party_identification, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
    
    # Orden EXACTO de atributos que NubeFacT espera
    id_element.set('schemeAgencyName', 'PE:SUNAT')
    id_element.set('schemeID', '6')
    id_element.set('schemeName', 'Documento de Identidad')
    id_element.set('schemeURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06')
    
    # RUC como texto plano, sin espacios ni caracteres especiales
    ruc = str(data['emisor']['ruc']).strip()
    id_element.text = ruc
    
    # Verificación crítica para NubeFacT
    if not ruc or len(ruc) != 11 or not ruc.isdigit():
        raise ValueError(f"RUC emisor inválido para NubeFacT: '{ruc}' (debe ser 11 dígitos numéricos)")
    
    # PartyName con CDATA
    party_name = etree.SubElement(party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyName')
    name_element = etree.SubElement(party_name, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Name')
    if LXML_AVAILABLE:
        name_element.text = etree.CDATA(data['emisor']['razonSocial'])
    else:
        name_element.text = data['emisor']['razonSocial']
    
    # PartyTaxScheme
    party_tax_scheme = etree.SubElement(party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyTaxScheme')
    registration_name = etree.SubElement(party_tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}RegistrationName')
    if LXML_AVAILABLE:
        registration_name.text = etree.CDATA(data['emisor']['razonSocial'])
    else:
        registration_name.text = data['emisor']['razonSocial']
    
    company_id = etree.SubElement(party_tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CompanyID')
    company_id.set('schemeAgencyName', 'PE:SUNAT')
    company_id.set('schemeID', '6')
    company_id.set('schemeName', 'SUNAT:Identificador de Documento de Identidad')
    company_id.set('schemeURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06')
    company_id.text = ruc
    
    tax_scheme = etree.SubElement(party_tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme')
    tax_scheme_id = etree.SubElement(tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
    tax_scheme_id.set('schemeAgencyName', 'PE:SUNAT')
    tax_scheme_id.set('schemeID', '6')
    tax_scheme_id.set('schemeName', 'SUNAT:Identificador de Documento de Identidad')
    tax_scheme_id.set('schemeURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06')
    tax_scheme_id.text = ruc
    
    # PartyLegalEntity
    party_legal_entity = etree.SubElement(party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyLegalEntity')
    legal_reg_name = etree.SubElement(party_legal_entity, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}RegistrationName')
    if LXML_AVAILABLE:
        legal_reg_name.text = etree.CDATA(data['emisor']['razonSocial'])
    else:
        legal_reg_name.text = data['emisor']['razonSocial']
    
    registration_address = etree.SubElement(party_legal_entity, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}RegistrationAddress')
    address_id = etree.SubElement(registration_address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
    address_id.set('schemeAgencyName', 'PE:INEI')
    address_id.set('schemeName', 'Ubigeos')
    address_id.text = data['emisor']['ubigeo']
    
    address_type_code = etree.SubElement(registration_address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}AddressTypeCode')
    address_type_code.set('listAgencyName', 'PE:SUNAT')
    address_type_code.set('listName', 'Establecimientos anexos')
    address_type_code.text = '0000'
    
    # Elementos de dirección
    city_name = etree.SubElement(registration_address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CityName')
    if LXML_AVAILABLE:
        city_name.text = etree.CDATA(data['emisor']['distrito'])
    else:
        city_name.text = data['emisor']['distrito']
    
    country_subentity = etree.SubElement(registration_address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CountrySubentity')
    if LXML_AVAILABLE:
        country_subentity.text = etree.CDATA(data['emisor']['provincia'])
    else:
        country_subentity.text = data['emisor']['provincia']
    
    district = etree.SubElement(registration_address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}District')
    if LXML_AVAILABLE:
        district.text = etree.CDATA(data['emisor']['distrito'])
    else:
        district.text = data['emisor']['distrito']
    
    address_line = etree.SubElement(registration_address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}AddressLine')
    line = etree.SubElement(address_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Line')
    if LXML_AVAILABLE:
        line.text = etree.CDATA(data['emisor']['direccion'])
    else:
        line.text = data['emisor']['direccion']
    
    country = etree.SubElement(registration_address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Country')
    identification_code = etree.SubElement(country, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IdentificationCode')
    identification_code.set('listAgencyName', 'United Nations Economic Commission for Europe')
    identification_code.set('listID', 'ISO 3166-1')
    identification_code.set('listName', 'Country')
    identification_code.text = data['emisor']['codigoPais']
    
    # Contact - elemento vacío
    contact = etree.SubElement(party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Contact')
    contact_name = etree.SubElement(contact, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Name')


def add_customer_party_nubefact(root, data):
    """Cliente optimizado para NubeFacT"""
    accounting_customer_party = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}AccountingCustomerParty')
    party = etree.SubElement(accounting_customer_party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Party')
    
    # PartyIdentification - CRÍTICO para NubeFacT
    party_identification = etree.SubElement(party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyIdentification')
    id_element = etree.SubElement(party_identification, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
    
    # Orden EXACTO de atributos que NubeFacT espera
    id_element.set('schemeAgencyName', 'PE:SUNAT')
    id_element.set('schemeID', '6')
    id_element.set('schemeName', 'Documento de Identidad')
    id_element.set('schemeURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06')
    
    # Número de documento como texto plano
    numero_doc = str(data['cliente']['numeroDoc']).strip()
    id_element.text = numero_doc
    
    # Verificación para NubeFacT
    if not numero_doc:
        raise ValueError(f"Número de documento cliente vacío para NubeFacT: '{numero_doc}'")
    
    # PartyName
    party_name = etree.SubElement(party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyName')
    name_element = etree.SubElement(party_name, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Name')
    if LXML_AVAILABLE:
        name_element.text = etree.CDATA(data['cliente']['razonSocial'])
    else:
        name_element.text = data['cliente']['razonSocial']
    
    # PartyTaxScheme
    party_tax_scheme = etree.SubElement(party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyTaxScheme')
    registration_name = etree.SubElement(party_tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}RegistrationName')
    if LXML_AVAILABLE:
        registration_name.text = etree.CDATA(data['cliente']['razonSocial'])
    else:
        registration_name.text = data['cliente']['razonSocial']
    
    company_id = etree.SubElement(party_tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CompanyID')
    company_id.set('schemeAgencyName', 'PE:SUNAT')
    company_id.set('schemeID', '6')
    company_id.set('schemeName', 'SUNAT:Identificador de Documento de Identidad')
    company_id.set('schemeURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06')
    company_id.text = numero_doc
    
    tax_scheme = etree.SubElement(party_tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme')
    tax_scheme_id = etree.SubElement(tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
    tax_scheme_id.set('schemeAgencyName', 'PE:SUNAT')
    tax_scheme_id.set('schemeID', '6')
    tax_scheme_id.set('schemeName', 'SUNAT:Identificador de Documento de Identidad')
    tax_scheme_id.set('schemeURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06')
    tax_scheme_id.text = numero_doc
    
    # PartyLegalEntity
    party_legal_entity = etree.SubElement(party, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyLegalEntity')
    legal_reg_name = etree.SubElement(party_legal_entity, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}RegistrationName')
    if LXML_AVAILABLE:
        legal_reg_name.text = etree.CDATA(data['cliente']['razonSocial'])
    else:
        legal_reg_name.text = data['cliente']['razonSocial']
    
    registration_address = etree.SubElement(party_legal_entity, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}RegistrationAddress')
    address_id = etree.SubElement(registration_address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
    address_id.set('schemeAgencyName', 'PE:INEI')
    address_id.set('schemeName', 'Ubigeos')
    
    # Elementos vacíos para cliente
    city_name = etree.SubElement(registration_address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CityName')
    country_subentity = etree.SubElement(registration_address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CountrySubentity')
    district = etree.SubElement(registration_address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}District')
    
    address_line = etree.SubElement(registration_address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}AddressLine')
    line = etree.SubElement(address_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Line')
    if LXML_AVAILABLE:
        line.text = etree.CDATA(data['cliente']['direccion'])
    else:
        line.text = data['cliente']['direccion']
    
    country = etree.SubElement(registration_address, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Country')
    identification_code = etree.SubElement(country, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IdentificationCode')
    identification_code.set('listAgencyName', 'United Nations Economic Commission for Europe')
    identification_code.set('listID', 'ISO 3166-1')
    identification_code.set('listName', 'Country')


def add_payment_terms(root, data):
    """Agregar términos de pago"""
    payment_terms = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PaymentTerms')
    payment_id = etree.SubElement(payment_terms, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
    payment_id.text = 'FormaPago'
    payment_means_id = etree.SubElement(payment_terms, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PaymentMeansID')
    payment_means_id.text = data.get('formaPago', 'Contado')


def add_tax_total_nubefact(root, data):
    """TaxTotal optimizado para NubeFacT"""
    tax_total = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxTotal')
    
    tax_amount = etree.SubElement(tax_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount')
    tax_amount.set('currencyID', data.get('moneda', 'PEN'))
    tax_amount.text = str(data['totalIGV'])
    
    tax_subtotal = etree.SubElement(tax_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxSubtotal')
    
    taxable_amount = etree.SubElement(tax_subtotal, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxableAmount')
    taxable_amount.set('currencyID', data.get('moneda', 'PEN'))
    taxable_amount.text = str(data['totalGravado'])
    
    tax_amount_subtotal = etree.SubElement(tax_subtotal, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount')
    tax_amount_subtotal.set('currencyID', data.get('moneda', 'PEN'))
    tax_amount_subtotal.text = str(data['totalIGV'])
    
    tax_category = etree.SubElement(tax_subtotal, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxCategory')
    tax_category_id = etree.SubElement(tax_category, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
    tax_category_id.set('schemeAgencyName', 'United Nations Economic Commission for Europe')
    tax_category_id.set('schemeID', 'UN/ECE 5305')
    tax_category_id.set('schemeName', 'Tax Category Identifier')
    tax_category_id.text = 'S'
    
    tax_scheme = etree.SubElement(tax_category, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme')
    tax_scheme_id = etree.SubElement(tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
    tax_scheme_id.set('schemeAgencyID', '6')
    tax_scheme_id.set('schemeID', 'UN/ECE 5153')
    tax_scheme_id.text = '1000'
    
    tax_scheme_name = etree.SubElement(tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Name')
    tax_scheme_name.text = 'IGV'
    
    tax_type_code = etree.SubElement(tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxTypeCode')
    tax_type_code.text = 'VAT'


def add_legal_monetary_total_nubefact(root, data):
    """LegalMonetaryTotal optimizado para NubeFacT"""
    legal_monetary_total = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}LegalMonetaryTotal')
    
    line_extension_amount = etree.SubElement(legal_monetary_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}LineExtensionAmount')
    line_extension_amount.set('currencyID', data.get('moneda', 'PEN'))
    line_extension_amount.text = str(data['totalGravado'])
    
    tax_inclusive_amount = etree.SubElement(legal_monetary_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxInclusiveAmount')
    tax_inclusive_amount.set('currencyID', data.get('moneda', 'PEN'))
    tax_inclusive_amount.text = str(data['totalImportePagar'])
    
    payable_amount = etree.SubElement(legal_monetary_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PayableAmount')
    payable_amount.set('currencyID', data.get('moneda', 'PEN'))
    payable_amount.text = str(data['totalImportePagar'])


def add_invoice_lines_nubefact(root, data):
    """InvoiceLines optimizado para NubeFacT"""
    for item in data['items']:
        invoice_line = etree.SubElement(root, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}InvoiceLine')
        
        # ID
        id_element = etree.SubElement(invoice_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
        id_element.text = str(item['id'])
        
        # InvoicedQuantity
        invoiced_quantity = etree.SubElement(invoice_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoicedQuantity')
        invoiced_quantity.set('unitCode', item.get('unidadMedida', 'NIU'))
        invoiced_quantity.set('unitCodeListAgencyName', 'United Nations Economic Commission for Europe')
        invoiced_quantity.set('unitCodeListID', 'UN/ECE rec 20')
        invoiced_quantity.text = str(item['cantidad'])
        
        # LineExtensionAmount
        line_extension_amount = etree.SubElement(invoice_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}LineExtensionAmount')
        line_extension_amount.set('currencyID', data.get('moneda', 'PEN'))
        line_extension_amount.text = str(item['valorTotal'])
        
        # PricingReference
        pricing_reference = etree.SubElement(invoice_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PricingReference')
        alternative_condition_price = etree.SubElement(pricing_reference, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}AlternativeConditionPrice')
        price_amount = etree.SubElement(alternative_condition_price, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PriceAmount')
        price_amount.set('currencyID', data.get('moneda', 'PEN'))
        precio_con_igv = item.get('precioVentaUnitario', item['valorUnitario'])
        price_amount.text = f"{precio_con_igv:.2f}"
        
        price_type_code = etree.SubElement(alternative_condition_price, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PriceTypeCode')
        price_type_code.set('listAgencyName', 'PE:SUNAT')
        price_type_code.set('listName', 'Tipo de Precio')
        price_type_code.set('listURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo16')
        price_type_code.text = item.get('codigoTipoPrecio', '01')
        
        # TaxTotal
        tax_total = etree.SubElement(invoice_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxTotal')
        line_tax_amount = etree.SubElement(tax_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount')
        line_tax_amount.set('currencyID', data.get('moneda', 'PEN'))
        line_tax_amount.text = str(item.get('igv', 0))
        
        line_tax_subtotal = etree.SubElement(tax_total, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxSubtotal')
        line_taxable_amount = etree.SubElement(line_tax_subtotal, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxableAmount')
        line_taxable_amount.set('currencyID', data.get('moneda', 'PEN'))
        line_taxable_amount.text = str(item['valorTotal'])
        
        line_tax_amount_subtotal = etree.SubElement(line_tax_subtotal, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxAmount')
        line_tax_amount_subtotal.set('currencyID', data.get('moneda', 'PEN'))
        line_tax_amount_subtotal.text = str(item.get('igv', 0))
        
        line_tax_category = etree.SubElement(line_tax_subtotal, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxCategory')
        line_tax_category_id = etree.SubElement(line_tax_category, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
        line_tax_category_id.set('schemeAgencyName', 'United Nations Economic Commission for Europe')
        line_tax_category_id.set('schemeID', 'UN/ECE 5305')
        line_tax_category_id.set('schemeName', 'Tax Category Identifier')
        line_tax_category_id.text = 'S'
        
        line_percent = etree.SubElement(line_tax_category, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Percent')
        line_percent.text = str(item.get('porcentajeIGV', 18))
        
        line_tax_exemption_reason_code = etree.SubElement(line_tax_category, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxExemptionReasonCode')
        line_tax_exemption_reason_code.set('listAgencyName', 'PE:SUNAT')
        line_tax_exemption_reason_code.set('listName', 'Afectacion del IGV')
        line_tax_exemption_reason_code.set('listURI', 'urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo07')
        line_tax_exemption_reason_code.text = item.get('tipoAfectacionIGV', '10')
        
        line_tax_scheme = etree.SubElement(line_tax_category, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}TaxScheme')
        line_tax_scheme_id = etree.SubElement(line_tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
        line_tax_scheme_id.set('schemeAgencyName', 'PE:SUNAT')
        line_tax_scheme_id.set('schemeID', 'UN/ECE 5153')
        line_tax_scheme_id.set('schemeName', 'Codigo de tributos')
        line_tax_scheme_id.text = '1000'
        
        line_tax_scheme_name = etree.SubElement(line_tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Name')
        line_tax_scheme_name.text = 'IGV'
        
        line_tax_type_code = etree.SubElement(line_tax_scheme, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}TaxTypeCode')
        line_tax_type_code.text = 'VAT'
        
        # Item
        item_element = etree.SubElement(invoice_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Item')
        
        # Description con CDATA
        description = etree.SubElement(item_element, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Description')
        if LXML_AVAILABLE:
            description.text = etree.CDATA(item['descripcion'])
        else:
            description.text = item['descripcion']
        
        # SellersItemIdentification
        sellers_item_identification = etree.SubElement(item_element, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}SellersItemIdentification')
        sellers_id = etree.SubElement(sellers_item_identification, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
        if LXML_AVAILABLE:
            sellers_id.text = etree.CDATA(item.get('codigoProducto', ''))
        else:
            sellers_id.text = item.get('codigoProducto', '')
        
        # CommodityClassification
        commodity_classification = etree.SubElement(item_element, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}CommodityClassification')
        item_classification_code = etree.SubElement(commodity_classification, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ItemClassificationCode')
        item_classification_code.set('listAgencyName', 'GS1 US')
        item_classification_code.set('listID', 'UNSPSC')
        item_classification_code.set('listName', 'Item Classification')
        item_classification_code.text = item.get('unspsc', '10191509')
        
        # Price
        price = etree.SubElement(invoice_line, '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Price')
        price_amount = etree.SubElement(price, '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}PriceAmount')
        price_amount.set('currencyID', data.get('moneda', 'PEN'))
        price_amount.text = str(item['valorUnitario'])


def validate_xml_structure(xml_content):
    """
    Validar estructura del XML generado
    """
    try:
        # Parsear XML
        etree.fromstring(xml_content.encode('utf-8'))
        
        # Validaciones básicas
        root = etree.fromstring(xml_content.encode('utf-8'))
        
        # Verificar que tenga elementos obligatorios
        required_elements = ['UBLVersionID', 'CustomizationID', 'ID', 'IssueDate', 'IssueTime']
        
        for element_name in required_elements:
            element = root.find(f'.//{{{root.nsmap["cbc"]}}}{element_name}')
            if element is None:
                return {
                    'success': False,
                    'errors': [f'Elemento obligatorio no encontrado: {element_name}']
                }
        
        return {
            'success': True,
            'errors': []
        }
        
    except etree.XMLSyntaxError as e:
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
    """
    Crear archivo ZIP con el XML (requerido por SUNAT)
    """
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Agregar el archivo XML al ZIP
            xml_filename = os.path.basename(xml_path)
            zipf.write(xml_path, xml_filename)
        
        return True
    except Exception as e:
        print(f"Error al crear ZIP: {str(e)}")
        return False


def validar_ruc_sunat(ruc):
    """
    Valida el RUC usando el algoritmo oficial de SUNAT
    
    Args:
        ruc (str): RUC a validar (11 dígitos)
    
    Returns:
        bool: True si el RUC es válido, False en caso contrario
    """
    if not ruc or len(ruc) != 11 or not ruc.isdigit():
        return False
    
    # Pesos para el algoritmo de validación SUNAT
    pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    
    # Tomar los primeros 10 dígitos
    primeros_10 = ruc[:10]
    digito_verificador = int(ruc[10])
    
    # Multiplicar cada dígito por su peso correspondiente
    suma = 0
    for i in range(10):
        suma += int(primeros_10[i]) * pesos[i]
    
    # Calcular el dígito verificador esperado
    resto = suma % 11
    digito_calculado = 11 - resto
    
    # Ajustes según el algoritmo de SUNAT
    if digito_calculado == 11:
        digito_calculado = 0
    elif digito_calculado == 10:
        digito_calculado = 1
    
    # Verificar que coincida con el último dígito del RUC
    return digito_calculado == digito_verificador


def extraer_clave_certificado_pfx(pfx_path, password):
    """Extrae la clave privada y el certificado del archivo PFX y los retorna en formato PEM"""
    with open(pfx_path, 'rb') as f:
        pfx_data = f.read()
    private_key, cert, additional_certs = pkcs12.load_key_and_certificates(
        pfx_data, password.encode(), backend=default_backend()
    )
    # Convertir a PEM
    cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    return private_key_pem, cert_pem


def firmar_xml_ubl(xml_string, private_key, cert):
    """Firma el XML UBL 2.1 e inserta la firma en <ext:ExtensionContent> (SUNAT), compatible con signxml antiguo."""
    print("🔍 Debug: Iniciando proceso de firma...")
    
    # Parsear el XML
    root = etree.fromstring(xml_string.encode('utf-8'))
    print("🔍 Debug: XML parseado correctamente")

    # Firmar el XML (la firma aparecerá como hija del nodo raíz)
    print("🔍 Debug: Iniciando firma con signxml...")
    signer = XMLSigner(
        method=methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
        c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"
    )
    signed_root = signer.sign(root, key=private_key, cert=cert, reference_uri=None)
    print("🔍 Debug: Firma completada con signxml")

    # Buscar el nodo <ds:Signature> generado (hijo directo del nodo raíz)
    signature_node = signed_root.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
    if signature_node is None:
        print("❌ ERROR: No se generó el nodo <ds:Signature> al firmar el XML")
        # Retornar el XML original para debug
        return xml_string
    print("🔍 Debug: Nodo <ds:Signature> encontrado")

    # Buscar el nodo <ext:ExtensionContent> en el árbol firmado
    ns = signed_root.nsmap.copy()
    ns['ext'] = ns.get('ext', 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2')
    extension_content = signed_root.find('.//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent', namespaces=ns)
    if extension_content is None:
        print("❌ ERROR: No se encontró el nodo <ext:ExtensionContent> en el XML firmado")
        return xml_string
    print("🔍 Debug: Nodo <ext:ExtensionContent> encontrado en árbol firmado")

    # Mover la firma al <ext:ExtensionContent> (eliminar de su padre original y añadir al destino)
    signature_node.getparent().remove(signature_node)
    extension_content.append(signature_node)
    print("🔍 Debug: Firma movida a <ext:ExtensionContent>")

    # Retornar el XML firmado como string
    result = etree.tostring(signed_root, encoding='utf-8', xml_declaration=False, pretty_print=True).decode('utf-8')
    print("🔍 Debug: XML firmado serializado correctamente")
    return result