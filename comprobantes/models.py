from django.db import models
from django.utils import timezone


class Comprobante(models.Model):
    """Modelo para almacenar los comprobantes electrónicos generados"""
    
    TIPO_CHOICES = [
        ('01', 'Factura'),
        ('03', 'Boleta'),
        ('07', 'Nota de Crédito'),
        ('08', 'Nota de Débito'),
    ]
    
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('VALIDADO', 'Validado'),
        ('GENERADO', 'Generado'),
        ('ERROR', 'Error'),
        ('ERROR_VALIDACION', 'Error de Validación'),
        ('ENVIADO', 'Enviado a SUNAT'),
        ('ENVIADO_PENDIENTE', 'Enviado - Pendiente de Respuesta'),
        ('PROCESANDO', 'Procesando en SUNAT'),
        ('ACEPTADO', 'Aceptado por SUNAT'),
        ('RECHAZADO', 'Rechazado por SUNAT'),
    ]
    
    # Datos del comprobante
    tipo_comprobante = models.CharField(max_length=2, choices=TIPO_CHOICES)
    ruc_emisor = models.CharField(max_length=11)
    serie = models.CharField(max_length=4)
    numero = models.CharField(max_length=8)
    
    # Datos del cliente
    ruc_cliente = models.CharField(max_length=11, blank=True, null=True)
    nombre_cliente = models.CharField(max_length=200)
    direccion_cliente = models.TextField(blank=True, null=True)
    
    # Montos
    total_gravado = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_igv = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Archivos
    xml_file = models.FileField(upload_to='xml/', blank=True, null=True)
    zip_file = models.FileField(upload_to='zip/', blank=True, null=True)
    
    # Estado y metadatos
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    errores = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Campos SUNAT - Todos opcionales para evitar errores de migración
    ticket_sunat = models.CharField(max_length=100, blank=True, null=True, 
                                   help_text="Ticket devuelto por SUNAT para consultas")
    cdr_zip_path = models.CharField(max_length=500, blank=True, null=True,
                                   help_text="Ruta del archivo ZIP del CDR")
    cdr_xml_path = models.CharField(max_length=500, blank=True, null=True,
                                   help_text="Ruta del archivo XML del CDR")
    fecha_envio_sunat = models.DateTimeField(blank=True, null=True,
                                           help_text="Fecha de envío a SUNAT")
    fecha_respuesta_sunat = models.DateTimeField(blank=True, null=True,
                                                help_text="Fecha de respuesta de SUNAT")
    
    class Meta:
        db_table = 'comprobantes'
        verbose_name = 'Comprobante Electrónico'
        verbose_name_plural = 'Comprobantes Electrónicos'
        # Comentar esto temporalmente para evitar errores
        # unique_together = ['tipo_comprobante', 'ruc_emisor', 'serie', 'numero']
    
    def __str__(self):
        return f"{self.get_tipo_comprobante_display()} - {self.ruc_emisor}-{self.serie}-{self.numero}"
    
    @property
    def nombre_archivo(self):
        """Genera el nombre del archivo según estándar SUNAT"""
        return f"{self.ruc_emisor}-{self.tipo_comprobante}-{self.serie}-{self.numero}"
    
    def get_xml_filename(self):
        """Retorna el nombre del archivo XML"""
        return f"{self.nombre_archivo}.xml"
    
    def get_zip_filename(self):
        """Retorna el nombre del archivo ZIP"""
        return f"{self.nombre_archivo}.zip"
    
    def get_cdr_filename(self):
        """Retorna el nombre del archivo CDR"""
        return f"R-{self.nombre_archivo}.xml"
    
    def is_sent_to_sunat(self):
        """Verifica si el comprobante fue enviado a SUNAT"""
        return self.estado in ['ENVIADO', 'ENVIADO_PENDIENTE', 'PROCESANDO', 'ACEPTADO', 'RECHAZADO']
    
    def is_accepted_by_sunat(self):
        """Verifica si el comprobante fue aceptado por SUNAT"""
        return self.estado == 'ACEPTADO'
    
    def can_be_sent_to_sunat(self):
        """Verifica si el comprobante puede ser enviado a SUNAT"""
        return self.estado == 'GENERADO' and self.xml_file and self.zip_file


class DetalleComprobante(models.Model):
    """Modelo para almacenar los detalles/items del comprobante"""
    
    comprobante = models.ForeignKey(Comprobante, on_delete=models.CASCADE, related_name='detalles')
    descripcion = models.CharField(max_length=500)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    
    class Meta:
        db_table = 'detalles_comprobante'
        verbose_name = 'Detalle de Comprobante'
        verbose_name_plural = 'Detalles de Comprobante'
    
    def __str__(self):
        return f"{self.comprobante} - {self.descripcion[:50]}"


# Modelos SUNAT simplificados para evitar errores de importación

class SUNATResponse(models.Model):
    """Modelo para almacenar las respuestas de SUNAT"""
    
    comprobante = models.ForeignKey(Comprobante, on_delete=models.CASCADE, related_name='sunat_responses')
    soap_method = models.CharField(max_length=20)
    success = models.BooleanField(default=False)
    response_data = models.TextField(blank=True, null=True)  # Simplificado
    soap_response = models.TextField(blank=True, null=True)
    ticket = models.CharField(max_length=100, blank=True, null=True)
    response_code = models.CharField(max_length=10, blank=True, null=True)
    response_description = models.TextField(blank=True, null=True)
    cdr_zip_path = models.CharField(max_length=500, blank=True, null=True)
    cdr_xml_path = models.CharField(max_length=500, blank=True, null=True)
    fecha_envio = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'sunat_responses'
        verbose_name = 'Respuesta SUNAT'
        verbose_name_plural = 'Respuestas SUNAT'
        ordering = ['-fecha_envio']
    
    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.comprobante} - {self.soap_method}"


class SUNATConfiguration(models.Model):
    """Configuración para la conexión con SUNAT"""
    
    name = models.CharField(max_length=100, unique=True)
    ruc_emisor = models.CharField(max_length=11)
    usuario_sunat = models.CharField(max_length=50)
    password_sunat = models.CharField(max_length=100)
    environment = models.CharField(max_length=20, default='beta')
    beta_url = models.URLField(default="https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService")
    production_url = models.URLField(default="https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'sunat_configurations'
        verbose_name = 'Configuración SUNAT'
        verbose_name_plural = 'Configuraciones SUNAT'
    
    def __str__(self):
        return f"{self.name} - {self.ruc_emisor}"


class SUNATLog(models.Model):
    """Log de operaciones con SUNAT"""
    
    comprobante = models.ForeignKey(Comprobante, on_delete=models.CASCADE, 
                                   related_name='sunat_logs', blank=True, null=True)
    level = models.CharField(max_length=10)
    operation = models.CharField(max_length=50)
    message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'sunat_logs'
        verbose_name = 'Log SUNAT'
        verbose_name_plural = 'Logs SUNAT'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"[{self.level}] {self.operation} - {self.timestamp.strftime('%d/%m/%Y %H:%M:%S')}"