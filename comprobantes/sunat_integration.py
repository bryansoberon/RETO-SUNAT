# comprobantes/sunat_integration.py

import os
import logging
from django.conf import settings
from .soap_client import SUNATSoapClient
from .models import Comprobante, SUNATResponse

logger = logging.getLogger(__name__)

class SUNATIntegration:
    """Clase para manejar la integración completa con SUNAT"""
    
    def __init__(self):
        self.soap_client = SUNATSoapClient()
    
    def send_comprobante_to_sunat(self, comprobante_id):
        """
        Envía un comprobante completo a SUNAT y procesa la respuesta
        """
        try:
            # Obtener comprobante
            comprobante = Comprobante.objects.get(id=comprobante_id)
            
            if comprobante.estado != 'GENERADO':
                return {
                    'success': False,
                    'error': f'El comprobante debe estar en estado GENERADO, actual: {comprobante.estado}'
                }
            
            # Verificar archivos
            if not comprobante.xml_file or not comprobante.zip_file:
                return {
                    'success': False,
                    'error': 'El comprobante no tiene archivos XML y ZIP generados'
                }
            
            xml_filename = os.path.basename(str(comprobante.xml_file))
            zip_filename = os.path.basename(str(comprobante.zip_file))
            
            logger.info(f"Enviando comprobante {comprobante} a SUNAT")
            
            # Validar antes de enviar
            xml_path = os.path.join(settings.MEDIA_ROOT, str(comprobante.xml_file))
            is_valid, validation_message = self.soap_client.validate_before_send(xml_path)
            
            if not is_valid:
                comprobante.estado = 'ERROR_VALIDACION'
                comprobante.errores = validation_message
                comprobante.save()
                
                return {
                    'success': False,
                    'error': f'Validación fallida: {validation_message}'
                }
            
            # Determinar método de envío según tipo de comprobante
            if comprobante.tipo_comprobante in ['01', '03', '07', '08']:  # Facturas, Boletas, NC, ND
                response = self.soap_client.send_bill(xml_filename, zip_filename)
            else:
                response = self.soap_client.send_summary(xml_filename, zip_filename)
            
            # Guardar respuesta en base de datos
            sunat_response = SUNATResponse.objects.create(
                comprobante=comprobante,
                soap_method='sendBill' if comprobante.tipo_comprobante in ['01', '03', '07', '08'] else 'sendSummary',
                success=response.get('success', False),
                response_data=response,
                soap_response=response.get('soap_response', ''),
                ticket=response.get('ticket'),
                cdr_zip_path=response.get('cdr_zip_path'),
                cdr_xml_path=response.get('cdr_xml_path')
            )
            
            # Actualizar estado del comprobante
            if response.get('success'):
                if response.get('ticket'):
                    # Es un resumen, necesita consulta posterior
                    comprobante.estado = 'ENVIADO_PENDIENTE'
                    comprobante.ticket_sunat = response.get('ticket')
                elif response.get('cdr_received'):
                    # CDR recibido directamente
                    comprobante.estado = 'ACEPTADO'
                    comprobante.cdr_zip_path = response.get('cdr_zip_path')
                    comprobante.cdr_xml_path = response.get('cdr_xml_path')
                else:
                    comprobante.estado = 'ENVIADO'
            else:
                comprobante.estado = 'RECHAZADO'
                comprobante.errores = response.get('error', 'Error desconocido')
            
            comprobante.sunat_response = sunat_response
            comprobante.save()
            
            logger.info(f"Comprobante {comprobante} enviado a SUNAT. Estado: {comprobante.estado}")
            
            return {
                'success': response.get('success', False),
                'comprobante_id': comprobante.id,
                'estado': comprobante.estado,
                'message': response.get('message', ''),
                'ticket': response.get('ticket'),
                'cdr_info': response.get('cdr_info'),
                'sunat_response_id': sunat_response.id
            }
            
        except Comprobante.DoesNotExist:
            return {
                'success': False,
                'error': f'Comprobante con ID {comprobante_id} no encontrado'
            }
        except Exception as e:
            logger.error(f"Error enviando comprobante {comprobante_id} a SUNAT: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_ticket_status(self, comprobante_id):
        """
        Consulta el estado de un ticket en SUNAT
        """
        try:
            comprobante = Comprobante.objects.get(id=comprobante_id)
            
            if not comprobante.ticket_sunat:
                return {
                    'success': False,
                    'error': 'El comprobante no tiene ticket asignado'
                }
            
            logger.info(f"Consultando estado de ticket {comprobante.ticket_sunat}")
            
            # Consultar estado en SUNAT
            response = self.soap_client.get_status(comprobante.ticket_sunat)
            
            # Guardar respuesta
            sunat_response = SUNATResponse.objects.create(
                comprobante=comprobante,
                soap_method='getStatus',
                success=response.get('success', False),
                response_data=response,
                soap_response=response.get('soap_response', ''),
                ticket=comprobante.ticket_sunat,
                cdr_zip_path=response.get('cdr_zip_path'),
                cdr_xml_path=response.get('cdr_xml_path')
            )
            
            # Actualizar estado del comprobante
            if response.get('success') and response.get('cdr_received'):
                comprobante.estado = 'ACEPTADO'
                comprobante.cdr_zip_path = response.get('cdr_zip_path')
                comprobante.cdr_xml_path = response.get('cdr_xml_path')
            elif response.get('success'):
                comprobante.estado = 'PROCESANDO'
            else:
                comprobante.estado = 'RECHAZADO'
                comprobante.errores = response.get('error', 'Error desconocido')
            
            comprobante.save()
            
            return {
                'success': response.get('success', False),
                'comprobante_id': comprobante.id,
                'estado': comprobante.estado,
                'ticket': comprobante.ticket_sunat,
                'cdr_info': response.get('cdr_info'),
                'message': response.get('message', ''),
                'sunat_response_id': sunat_response.id
            }
            
        except Comprobante.DoesNotExist:
            return {
                'success': False,
                'error': f'Comprobante con ID {comprobante_id} no encontrado'
            }
        except Exception as e:
            logger.error(f"Error consultando ticket para comprobante {comprobante_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_comprobante_status(self, comprobante_id):
        """
        Obtiene el estado actual de un comprobante
        """
        try:
            comprobante = Comprobante.objects.get(id=comprobante_id)
            
            # Obtener última respuesta de SUNAT
            latest_response = comprobante.sunat_responses.order_by('-fecha_envio').first()
            
            return {
                'success': True,
                'comprobante_id': comprobante.id,
                'estado': comprobante.estado,
                'ticket': comprobante.ticket_sunat,
                'cdr_zip_path': comprobante.cdr_zip_path,
                'cdr_xml_path': comprobante.cdr_xml_path,
                'errores': comprobante.errores,
                'latest_response': {
                    'id': latest_response.id if latest_response else None,
                    'fecha_envio': latest_response.fecha_envio.isoformat() if latest_response else None,
                    'success': latest_response.success if latest_response else None,
                    'soap_method': latest_response.soap_method if latest_response else None
                } if latest_response else None
            }
            
        except Comprobante.DoesNotExist:
            return {
                'success': False,
                'error': f'Comprobante con ID {comprobante_id} no encontrado'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def retry_failed_comprobante(self, comprobante_id):
        """
        Reintenta el envío de un comprobante que falló
        """
        try:
            comprobante = Comprobante.objects.get(id=comprobante_id)
            
            if comprobante.estado not in ['RECHAZADO', 'ERROR_VALIDACION']:
                return {
                    'success': False,
                    'error': f'El comprobante no está en estado de error. Estado actual: {comprobante.estado}'
                }
            
            # Resetear estado y errores
            comprobante.estado = 'GENERADO'
            comprobante.errores = None
            comprobante.save()
            
            # Reintentar envío
            return self.send_comprobante_to_sunat(comprobante_id)
            
        except Comprobante.DoesNotExist:
            return {
                'success': False,
                'error': f'Comprobante con ID {comprobante_id} no encontrado'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def bulk_send_comprobantes(self, comprobante_ids):
        """
        Envía múltiples comprobantes a SUNAT
        """
        results = []
        
        for comprobante_id in comprobante_ids:
            try:
                result = self.send_comprobante_to_sunat(comprobante_id)
                result['comprobante_id'] = comprobante_id
                results.append(result)
            except Exception as e:
                results.append({
                    'comprobante_id': comprobante_id,
                    'success': False,
                    'error': str(e)
                })
        
        # Estadísticas
        successful = sum(1 for r in results if r.get('success'))
        failed = len(results) - successful
        
        return {
            'total_processed': len(results),
            'successful': successful,
            'failed': failed,
            'results': results
        }
    
    def check_pending_tickets(self):
        """
        Verifica todos los comprobantes pendientes de respuesta
        """
        pending_comprobantes = Comprobante.objects.filter(
            estado='ENVIADO_PENDIENTE',
            ticket_sunat__isnull=False
        )
        
        results = []
        
        for comprobante in pending_comprobantes:
            try:
                result = self.check_ticket_status(comprobante.id)
                results.append(result)
            except Exception as e:
                results.append({
                    'comprobante_id': comprobante.id,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'total_checked': len(results),
            'results': results
        }