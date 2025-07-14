# comprobantes/soap_client.py

import os
import base64
import zipfile
from io import BytesIO
from datetime import datetime
import xml.etree.ElementTree as ET
from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)

class SUNATSoapClient:
    """Cliente SOAP para envío de comprobantes electrónicos a SUNAT"""
    
    def __init__(self):
        self.beta_url = "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService"
        self.prod_url = "https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService"
        self.test_ruc = "20000000001"  # RUC de pruebas SUNAT
        self.test_usuario = "MODDATOS"
        self.test_password = "MODDATOS"
        
    def get_soap_envelope(self, method, content):
        """Genera el sobre SOAP según especificaciones SUNAT"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
                  xmlns:ser="http://service.sunat.gob.pe" 
                  xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
    <soapenv:Header>
        <wsse:Security>
            <wsse:UsernameToken>
                <wsse:Username>{self.test_ruc}{self.test_usuario}</wsse:Username>
                <wsse:Password>{self.test_password}</wsse:Password>
            </wsse:UsernameToken>
        </wsse:Security>
    </soapenv:Header>
    <soapenv:Body>
        <ser:{method}>
            {content}
        </ser:{method}>
    </soapenv:Body>
</soapenv:Envelope>'''

    def send_bill(self, xml_filename, zip_filename):
        """
        Envía factura a SUNAT usando el método sendBill
        """
        try:
            # Leer archivo ZIP
            zip_path = os.path.join(settings.SUNAT_CONFIG['ZIP_OUTPUT_DIR'], zip_filename)
            if not os.path.exists(zip_path):
                raise Exception(f"Archivo ZIP no encontrado: {zip_path}")
            
            with open(zip_path, 'rb') as f:
                zip_content = f.read()
            
            # Codificar en base64
            zip_base64 = base64.b64encode(zip_content).decode('utf-8')
            
            # Extraer nombre del archivo sin extensión
            zip_name = os.path.splitext(zip_filename)[0]
            
            # Crear contenido SOAP
            soap_content = f'''
            <fileName>{zip_filename}</fileName>
            <contentFile>{zip_base64}</contentFile>
            '''
            
            # Generar sobre SOAP
            soap_envelope = self.get_soap_envelope('sendBill', soap_content)
            
            # Headers HTTP
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'urn:sendBill',
                'User-Agent': 'Mozilla/5.0 (compatible; SUNAT-Client/1.0)'
            }
            
            logger.info(f"Enviando comprobante a SUNAT: {zip_filename}")
            
            # Enviar a SUNAT Beta (ambiente de pruebas)
            response = requests.post(
                self.beta_url,
                data=soap_envelope.encode('utf-8'),
                headers=headers,
                timeout=30,
                verify=True
            )
            
            logger.info(f"Respuesta SUNAT - Status: {response.status_code}")
            
            if response.status_code == 200:
                return self.process_soap_response(response.text, zip_name)
            else:
                return {
                    'success': False,
                    'error': f'Error HTTP {response.status_code}: {response.text}',
                    'soap_response': response.text
                }
                
        except Exception as e:
            logger.error(f"Error enviando a SUNAT: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'soap_response': None
            }

    def send_summary(self, xml_filename, zip_filename):
        """
        Envía resumen diario usando el método sendSummary
        """
        try:
            # Leer archivo ZIP
            zip_path = os.path.join(settings.SUNAT_CONFIG['ZIP_OUTPUT_DIR'], zip_filename)
            with open(zip_path, 'rb') as f:
                zip_content = f.read()
            
            zip_base64 = base64.b64encode(zip_content).decode('utf-8')
            
            soap_content = f'''
            <fileName>{zip_filename}</fileName>
            <contentFile>{zip_base64}</contentFile>
            '''
            
            soap_envelope = self.get_soap_envelope('sendSummary', soap_content)
            
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'urn:sendSummary'
            }
            
            response = requests.post(
                self.beta_url,
                data=soap_envelope.encode('utf-8'),
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return self.process_soap_response(response.text, os.path.splitext(zip_filename)[0])
            else:
                return {
                    'success': False,
                    'error': f'Error HTTP {response.status_code}: {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_status(self, ticket):
        """
        Consulta el estado de un comprobante usando getStatus
        """
        try:
            soap_content = f'''
            <ticket>{ticket}</ticket>
            '''
            
            soap_envelope = self.get_soap_envelope('getStatus', soap_content)
            
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'urn:getStatus'
            }
            
            response = requests.post(
                self.beta_url,
                data=soap_envelope.encode('utf-8'),
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return self.process_soap_response(response.text, ticket)
            else:
                return {
                    'success': False,
                    'error': f'Error HTTP {response.status_code}: {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def process_soap_response(self, soap_response, document_name):
        """
        Procesa la respuesta SOAP de SUNAT
        """
        try:
            # Parsear XML de respuesta
            root = ET.fromstring(soap_response)
            
            # Namespaces SOAP
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ser': 'http://service.sunat.gob.pe'
            }
            
            # Buscar faults (errores)
            fault = root.find('.//soap:Fault', namespaces)
            if fault is not None:
                fault_code = fault.find('faultcode')
                fault_string = fault.find('faultstring')
                
                return {
                    'success': False,
                    'error': f"SOAP Fault - Code: {fault_code.text if fault_code is not None else 'Unknown'}, "
                            f"Message: {fault_string.text if fault_string is not None else 'Unknown'}",
                    'soap_response': soap_response
                }
            
            # Buscar respuesta exitosa
            response_elements = [
                './/ser:sendBillResponse',
                './/ser:sendSummaryResponse', 
                './/ser:getStatusResponse'
            ]
            
            for response_path in response_elements:
                response_elem = root.find(response_path, namespaces)
                if response_elem is not None:
                    return self.parse_successful_response(response_elem, document_name, soap_response)
            
            # Si no se encuentra respuesta conocida
            return {
                'success': False,
                'error': 'Formato de respuesta SOAP no reconocido',
                'soap_response': soap_response
            }
            
        except ET.ParseError as e:
            return {
                'success': False,
                'error': f'Error parseando respuesta SOAP: {str(e)}',
                'soap_response': soap_response
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error procesando respuesta: {str(e)}',
                'soap_response': soap_response
            }

    def parse_successful_response(self, response_elem, document_name, soap_response):
        """
        Parsea una respuesta exitosa de SUNAT
        """
        try:
            result = {
                'success': True,
                'document_name': document_name,
                'timestamp': datetime.now().isoformat(),
                'soap_response': soap_response
            }
            
            # Buscar ticket (para sendSummary)
            ticket_elem = response_elem.find('ticket')
            if ticket_elem is not None:
                result['ticket'] = ticket_elem.text
                result['message'] = f'Resumen enviado exitosamente. Ticket: {ticket_elem.text}'
                return result
            
            # Buscar applicationResponse (CDR)
            app_response = response_elem.find('applicationResponse')
            if app_response is not None:
                cdr_content = app_response.text
                if cdr_content:
                    # Procesar CDR
                    cdr_result = self.process_cdr(cdr_content, document_name)
                    result.update(cdr_result)
                    return result
            
            # Buscar content (para getStatus)
            content_elem = response_elem.find('content')
            if content_elem is not None:
                content = content_elem.text
                if content:
                    cdr_result = self.process_cdr(content, document_name)
                    result.update(cdr_result)
                    return result
            
            # Respuesta exitosa genérica
            result['message'] = 'Comprobante procesado exitosamente por SUNAT'
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error parseando respuesta exitosa: {str(e)}',
                'soap_response': soap_response
            }

    def process_cdr(self, cdr_base64, document_name):
        """
        Procesa el CDR (Constancia de Recepción) de SUNAT
        """
        try:
            # Decodificar base64
            cdr_zip_content = base64.b64decode(cdr_base64)
            
            # Crear directorio CDR si no existe
            cdr_dir = os.path.join(settings.MEDIA_ROOT, 'cdr')
            os.makedirs(cdr_dir, exist_ok=True)
            
            # Guardar ZIP del CDR
            cdr_zip_path = os.path.join(cdr_dir, f'R-{document_name}.zip')
            with open(cdr_zip_path, 'wb') as f:
                f.write(cdr_zip_content)
            
            # Extraer y procesar CDR XML
            with zipfile.ZipFile(BytesIO(cdr_zip_content), 'r') as zip_file:
                # El CDR suele tener el formato R-{document_name}.xml
                cdr_xml_name = f'R-{document_name}.xml'
                
                if cdr_xml_name in zip_file.namelist():
                    cdr_xml_content = zip_file.read(cdr_xml_name).decode('utf-8')
                    
                    # Guardar CDR XML
                    cdr_xml_path = os.path.join(cdr_dir, cdr_xml_name)
                    with open(cdr_xml_path, 'w', encoding='utf-8') as f:
                        f.write(cdr_xml_content)
                    
                    # Parsear CDR para extraer información
                    cdr_info = self.parse_cdr_xml(cdr_xml_content)
                    
                    return {
                        'cdr_received': True,
                        'cdr_zip_path': f'cdr/R-{document_name}.zip',
                        'cdr_xml_path': f'cdr/R-{document_name}.xml',
                        'cdr_info': cdr_info,
                        'message': f'CDR recibido y procesado. Estado: {cdr_info.get("response_code", "Unknown")}'
                    }
                else:
                    return {
                        'cdr_received': True,
                        'cdr_zip_path': f'cdr/R-{document_name}.zip',
                        'error': 'No se encontró el XML del CDR en el archivo ZIP',
                        'available_files': zip_file.namelist()
                    }
                    
        except Exception as e:
            return {
                'cdr_error': str(e),
                'cdr_received': False
            }

    def parse_cdr_xml(self, cdr_xml):
        """
        Parsea el XML del CDR para extraer información relevante
        """
        try:
            root = ET.fromstring(cdr_xml)
            
            # Namespaces comunes en CDR
            namespaces = {
                'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
                'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
                'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2'
            }
            
            cdr_info = {}
            
            # ID del CDR
            id_elem = root.find('.//cbc:ID', namespaces)
            if id_elem is not None:
                cdr_info['cdr_id'] = id_elem.text
            
            # Código de respuesta
            response_code_elem = root.find('.//cbc:ResponseCode', namespaces)
            if response_code_elem is not None:
                cdr_info['response_code'] = response_code_elem.text
            
            # Descripción de respuesta
            description_elem = root.find('.//cbc:Description', namespaces)
            if description_elem is not None:
                cdr_info['description'] = description_elem.text
            
            # Fecha de respuesta
            response_date_elem = root.find('.//cbc:ResponseDate', namespaces)
            if response_date_elem is not None:
                cdr_info['response_date'] = response_date_elem.text
            
            # Hora de respuesta
            response_time_elem = root.find('.//cbc:ResponseTime', namespaces)
            if response_time_elem is not None:
                cdr_info['response_time'] = response_time_elem.text
            
            # Referencia al documento original
            doc_ref_elem = root.find('.//cac:DocumentReference/cbc:ID', namespaces)
            if doc_ref_elem is not None:
                cdr_info['referenced_document'] = doc_ref_elem.text
            
            # Notas adicionales
            notes = root.findall('.//cbc:Note', namespaces)
            if notes:
                cdr_info['notes'] = [note.text for note in notes if note.text]
            
            return cdr_info
            
        except Exception as e:
            return {
                'parse_error': str(e)
            }

    def validate_before_send(self, xml_path):
        """
        Valida el XML antes de enviarlo a SUNAT
        """
        try:
            if not os.path.exists(xml_path):
                return False, "Archivo XML no encontrado"
            
            # Verificar que el XML sea válido
            with open(xml_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            root = ET.fromstring(xml_content)
            
            # Verificaciones básicas
            if 'Invoice' not in root.tag and 'CreditNote' not in root.tag and 'DebitNote' not in root.tag:
                return False, "Tipo de documento no válido"
            
            # Verificar que tenga firma digital
            if 'ds:Signature' not in xml_content:
                return False, "XML no contiene firma digital"
            
            return True, "XML válido para envío"
            
        except Exception as e:
            return False, f"Error validando XML: {str(e)}"