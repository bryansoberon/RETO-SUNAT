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
    
    class Meta:
        db_table = 'comprobantes'
        verbose_name = 'Comprobante Electrónico'
        verbose_name_plural = 'Comprobantes Electrónicos'
        unique_together = ['tipo_comprobante', 'ruc_emisor', 'serie', 'numero']
    
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