from django.contrib import admin
from .models import Comprobante, DetalleComprobante
from django.conf import settings


class DetalleComprobanteInline(admin.TabularInline):
    """Inline para mostrar detalles del comprobante"""
    model = DetalleComprobante
    extra = 0
    readonly_fields = ['subtotal']


@admin.register(Comprobante)
class ComprobanteAdmin(admin.ModelAdmin):
    """Administración de comprobantes electrónicos"""
    
    list_display = [
        'tipo_comprobante', 'ruc_emisor', 'serie', 'numero', 
        'nombre_cliente', 'total', 'estado', 'fecha_creacion'
    ]
    
    list_filter = [
        'tipo_comprobante', 'estado', 'fecha_creacion'
    ]
    
    search_fields = [
        'ruc_emisor', 'ruc_cliente', 'nombre_cliente', 'serie', 'numero'
    ]
    
    readonly_fields = [
        'fecha_creacion', 'fecha_actualizacion', 'xml_file', 'zip_file'
    ]
    
    fieldsets = (
        ('Información del Comprobante', {
            'fields': ('tipo_comprobante', 'ruc_emisor', 'serie', 'numero')
        }),
        ('Información del Cliente', {
            'fields': ('ruc_cliente', 'nombre_cliente', 'direccion_cliente')
        }),
        ('Montos', {
            'fields': ('total_gravado', 'total_igv', 'total')
        }),
        ('Archivos', {
            'fields': ('xml_file', 'zip_file'),
            'classes': ('collapse',)
        }),
        ('Estado y Metadatos', {
            'fields': ('estado', 'errores', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [DetalleComprobanteInline]
    
    actions = ['regenerar_xml', 'regenerar_zip']
    
    def regenerar_xml(self, request, queryset):
        """Acción para regenerar archivos XML"""
        from .utils import generate_ubl_xml, validate_xml_structure
        import os
        
        for comprobante in queryset:
            try:
                # Preparar datos para generar XML
                data = {
                    'tipo_comprobante': comprobante.tipo_comprobante,
                    'ruc_emisor': comprobante.ruc_emisor,
                    'serie': comprobante.serie,
                    'numero': comprobante.numero,
                    'ruc_cliente': comprobante.ruc_cliente,
                    'nombre_cliente': comprobante.nombre_cliente,
                    'direccion_cliente': comprobante.direccion_cliente,
                    'total_gravado': float(comprobante.total_gravado),
                    'total_igv': float(comprobante.total_igv),
                    'total': float(comprobante.total),
                    'detalles': [
                        {
                            'descripcion': detalle.descripcion,
                            'cantidad': float(detalle.cantidad),
                            'precio_unitario': float(detalle.precio_unitario)
                        }
                        for detalle in comprobante.detalles.all()
                    ]
                }
                
                # Generar XML
                xml_content = generate_ubl_xml(data)
                
                # Validar XML
                validation = validate_xml_structure(xml_content)
                if validation['success']:
                    # Guardar archivo
                    xml_filename = comprobante.get_xml_filename()
                    xml_path = os.path.join(settings.SUNAT_CONFIG['XML_OUTPUT_DIR'], xml_filename)
                    
                    with open(xml_path, 'w', encoding='utf-8') as f:
                        f.write(xml_content)
                    
                    comprobante.xml_file = f'xml/{xml_filename}'
                    comprobante.estado = 'GENERADO'
                    comprobante.errores = None
                    comprobante.save()
                    
                    self.message_user(request, f'XML regenerado para {comprobante}')
                else:
                    comprobante.estado = 'ERROR'
                    comprobante.errores = str(validation['errors'])
                    comprobante.save()
                    
                    self.message_user(request, f'Error al regenerar XML para {comprobante}: {validation["errors"]}', level='ERROR')
                    
            except Exception as e:
                self.message_user(request, f'Error al regenerar XML para {comprobante}: {str(e)}', level='ERROR')
    
    regenerar_xml.short_description = "Regenerar archivos XML"
    
    def regenerar_zip(self, request, queryset):
        """Acción para regenerar archivos ZIP"""
        from .utils import create_zip_file
        import os
        
        for comprobante in queryset:
            try:
                if comprobante.xml_file:
                    xml_path = os.path.join(settings.MEDIA_ROOT, str(comprobante.xml_file))
                    zip_filename = comprobante.get_zip_filename()
                    zip_path = os.path.join(settings.SUNAT_CONFIG['ZIP_OUTPUT_DIR'], zip_filename)
                    
                    if create_zip_file(xml_path, zip_path):
                        comprobante.zip_file = f'zip/{zip_filename}'
                        comprobante.save()
                        self.message_user(request, f'ZIP regenerado para {comprobante}')
                    else:
                        self.message_user(request, f'Error al crear ZIP para {comprobante}', level='ERROR')
                else:
                    self.message_user(request, f'No hay archivo XML para {comprobante}', level='WARNING')
                    
            except Exception as e:
                self.message_user(request, f'Error al regenerar ZIP para {comprobante}: {str(e)}', level='ERROR')
    
    regenerar_zip.short_description = "Regenerar archivos ZIP"


@admin.register(DetalleComprobante)
class DetalleComprobanteAdmin(admin.ModelAdmin):
    """Administración de detalles de comprobantes"""
    
    list_display = ['comprobante', 'descripcion', 'cantidad', 'precio_unitario', 'subtotal']
    list_filter = ['comprobante__tipo_comprobante']
    search_fields = ['descripcion', 'comprobante__nombre_cliente']
    readonly_fields = ['subtotal'] 