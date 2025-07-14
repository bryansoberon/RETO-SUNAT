# comprobantes/serializers.py

from rest_framework import serializers
from .models import Comprobante, DetalleComprobante
from .utils import validar_ruc_sunat
from decimal import Decimal, ROUND_HALF_UP


class DetalleComprobanteSerializer(serializers.ModelSerializer):
    """Serializer para los detalles del comprobante"""
    
    class Meta:
        model = DetalleComprobante
        fields = ['descripcion', 'cantidad', 'precio_unitario', 'subtotal']


class ComprobanteSerializer(serializers.ModelSerializer):
    """Serializer para el comprobante principal"""
    
    detalles = DetalleComprobanteSerializer(many=True, read_only=True)
    
    class Meta:
        model = Comprobante
        fields = [
            'id', 'tipo_comprobante', 'ruc_emisor', 'serie', 'numero',
            'ruc_cliente', 'nombre_cliente', 'direccion_cliente',
            'total_gravado', 'total_igv', 'total', 'estado',
            'xml_file', 'zip_file', 'errores', 'fecha_creacion',
            'detalles'
        ]
        read_only_fields = ['id', 'estado', 'xml_file', 'zip_file', 'errores', 'fecha_creacion']


class ComprobanteInputSerializer(serializers.Serializer):
    """Serializer para validar datos de entrada JSON con formato específico"""
    
    # Datos básicos del comprobante
    serie = serializers.CharField(max_length=4, min_length=4)
    numero = serializers.CharField(max_length=8, min_length=1)  # ← CORREGIDO: min_length=1
    fechaEmision = serializers.DateField(required=False)
    horaEmision = serializers.TimeField(required=False)
    tipoDocumento = serializers.ChoiceField(choices=[('01', 'Factura'), ('03', 'Boleta'), ('07', 'Nota de Crédito'), ('08', 'Nota de Débito')])
    moneda = serializers.CharField(max_length=3, default='PEN')
    formaPago = serializers.CharField(max_length=50, required=False)
    
    # Totales
    totalGravado = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    totalIGV = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    totalPrecioVenta = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    totalImportePagar = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Emisor
    emisor = serializers.DictField()
    
    # Cliente
    cliente = serializers.DictField()
    
    # Items
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    
    def validate_numero(self, value):
        """Validar y formatear número de comprobante"""
        # Convertir a string y validar que solo contenga dígitos
        numero_str = str(value).strip()
        
        if not numero_str.isdigit():
            raise serializers.ValidationError("El número debe contener solo dígitos")
        
        # Validar rango razonable (máximo 8 dígitos)
        if len(numero_str) > 8:
            raise serializers.ValidationError("El número no puede tener más de 8 dígitos")
        
        # Rellenar con ceros a la izquierda para llegar a 8 dígitos
        numero_formateado = numero_str.zfill(8)
        
        return numero_formateado
    
    def validate_emisor(self, value):
        """Validar datos del emisor"""
        if not value:
            raise serializers.ValidationError("Los datos del emisor son requeridos")
        
        ruc = value.get('ruc')
        if not ruc:
            raise serializers.ValidationError("El RUC del emisor es requerido")
        
        if not ruc.isdigit():
            raise serializers.ValidationError("El RUC del emisor debe contener solo números")
        
        if len(ruc) != 11:
            raise serializers.ValidationError("El RUC del emisor debe tener 11 dígitos")
        
        if not validar_ruc_sunat(ruc):
            raise serializers.ValidationError("El RUC del emisor no es válido según el algoritmo oficial de SUNAT")
        
        # Validar otros campos requeridos del emisor
        required_fields = ['razonSocial', 'ubigeo', 'direccion', 'codigoPais']
        for field in required_fields:
            if not value.get(field):
                raise serializers.ValidationError(f"El campo '{field}' del emisor es requerido")
        
        return value
    
    def validate_cliente(self, value):
        """Validar datos del cliente"""
        if not value:
            raise serializers.ValidationError("Los datos del cliente son requeridos")
        
        numero_doc = value.get('numeroDoc')
        if not numero_doc:
            raise serializers.ValidationError("El número de documento del cliente es requerido")
        
        if not numero_doc.isdigit():
            raise serializers.ValidationError("El número de documento del cliente debe contener solo números")
        
        # Validar otros campos requeridos del cliente
        required_fields = ['razonSocial', 'tipoDoc']
        for field in required_fields:
            if not value.get(field):
                raise serializers.ValidationError(f"El campo '{field}' del cliente es requerido")
        
        return value
    
    def validate_moneda(self, value):
        """Validar código de moneda según catálogo SUNAT"""
        catalogo_monedas = {'PEN', 'USD', 'EUR'}
        if value not in catalogo_monedas:
            raise serializers.ValidationError(f"Moneda inválida. Debe ser uno de: {', '.join(catalogo_monedas)}")
        return value

    def validate_tipoDocumento(self, value):
        """Validar tipo de documento según catálogo SUNAT"""
        catalogo_tipos = {'01', '03', '07', '08'}
        if value not in catalogo_tipos:
            raise serializers.ValidationError(f"Tipo de documento inválido. Debe ser uno de: {', '.join(catalogo_tipos)}")
        return value

    def validate_serie(self, value):
        """Validar formato de serie: 1-2 letras + 3 dígitos (ej: F001, B001)"""
        import re
        if not re.match(r'^[A-Z]{1,2}[0-9]{3}$', value):
            raise serializers.ValidationError("La serie debe tener el formato: 1 o 2 letras seguidas de 3 dígitos (ej: F001, B001)")
        return value

    def validate_items(self, value):
        """Validar estructura de los items"""
        if not value or len(value) == 0:
            raise serializers.ValidationError("Debe incluir al menos un item")
        
        for i, item in enumerate(value, 1):
            # Verificar campos requeridos
            required_fields = ['id', 'cantidad', 'descripcion', 'valorUnitario', 'valorTotal']
            for field in required_fields:
                if field not in item:
                    raise serializers.ValidationError(f"Campo '{field}' requerido en item {i}")
            
            # Validar tipos y valores
            try:
                cantidad = float(item['cantidad'])
                if cantidad <= 0:
                    raise serializers.ValidationError(f"La cantidad del item {i} debe ser mayor a 0")
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"La cantidad del item {i} debe ser un número válido")
            
            try:
                valor_unitario = float(item['valorUnitario'])
                if valor_unitario < 0:
                    raise serializers.ValidationError(f"El valor unitario del item {i} no puede ser negativo")
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"El valor unitario del item {i} debe ser un número válido")
            
            try:
                valor_total = float(item['valorTotal'])
                if valor_total < 0:
                    raise serializers.ValidationError(f"El valor total del item {i} no puede ser negativo")
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"El valor total del item {i} debe ser un número válido")
            
            # Validar consistencia cantidad * precio = total (con tolerancia)
            total_calculado = cantidad * valor_unitario
            if abs(total_calculado - valor_total) > 0.01:
                raise serializers.ValidationError(
                    f"Item {i}: El valor total ({valor_total}) no coincide con cantidad × precio unitario ({total_calculado:.2f})"
                )
            
            # Validar máximo dos decimales
            for field_name, field_value in [('cantidad', cantidad), ('valorUnitario', valor_unitario), ('valorTotal', valor_total)]:
                if round(field_value, 2) != field_value:
                    raise serializers.ValidationError(f"El campo '{field_name}' del item {i} debe tener máximo dos decimales")
            
            # Validar descripción no vacía
            if not item['descripcion'] or not item['descripcion'].strip():
                raise serializers.ValidationError(f"La descripción del item {i} no puede estar vacía")
        
        return value

    def validate(self, data):
        """Validación de datos cruzados - CORREGIDA según estándares SUNAT"""
        # Validar que los importes tengan máximo dos decimales
        decimal_fields = ['totalGravado', 'totalIGV', 'totalPrecioVenta', 'totalImportePagar']
        for field in decimal_fields:
            valor = data.get(field)
            if valor is not None:
                valor_str = str(valor)
                if '.' in valor_str and len(valor_str.split('.')[-1]) > 2:
                    raise serializers.ValidationError(f"El campo {field} debe tener máximo dos decimales")
        
        # Calcular totales desde los items
        total_items = Decimal('0')
        for item in data.get('items', []):
            valor_total = Decimal(str(item.get('valorTotal', 0))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_items += valor_total
        
        # Calcular IGV (18% del total de items)
        igv_calculado = (total_items * Decimal('0.18')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Total con IGV
        total_con_igv = total_items + igv_calculado
        
        # Obtener valores enviados
        total_gravado_enviado = Decimal(str(data.get('totalGravado', 0)))
        igv_enviado = Decimal(str(data.get('totalIGV', 0)))
        total_precio_venta_enviado = Decimal(str(data.get('totalPrecioVenta', 0)))  # ← NUEVO
        total_pagar_enviado = Decimal(str(data['totalImportePagar']))
        
        # Validaciones con tolerancia de 0.01
        tolerancia = Decimal('0.01')
        
        # 1. Validar que totalGravado coincida con suma de items (SIN IGV)
        if abs(total_items - total_gravado_enviado) > tolerancia:
            raise serializers.ValidationError(
                f"El total gravado ({total_gravado_enviado}) no coincide con la suma de items ({total_items}). "
                f"Diferencia: {abs(total_items - total_gravado_enviado)}"
            )
        
        # 2. Validar que el IGV sea correcto
        if abs(igv_calculado - igv_enviado) > tolerancia:
            raise serializers.ValidationError(
                f"El IGV ({igv_enviado}) no coincide con el calculado ({igv_calculado}). "
                f"Diferencia: {abs(igv_calculado - igv_enviado)}"
            )
        
        # 3. Validar que totalPrecioVenta = totalGravado + IGV (CON IGV)
        if abs(total_con_igv - total_precio_venta_enviado) > tolerancia:
            raise serializers.ValidationError(
                f"El total precio venta ({total_precio_venta_enviado}) no coincide con el calculado ({total_con_igv}). "
                f"Debe ser: Items {total_items} + IGV {igv_calculado} = {total_con_igv}"
            )
        
        # 4. Validar que el total a pagar coincida con total precio venta
        if abs(total_precio_venta_enviado - total_pagar_enviado) > tolerancia:
            raise serializers.ValidationError(
                f"El total a pagar ({total_pagar_enviado}) debe coincidir con el total precio venta ({total_precio_venta_enviado})"
            )
        
        # Validar campos obligatorios según tipo de comprobante
        tipo = data.get('tipoDocumento')
        cliente = data.get('cliente', {})
        
        if tipo == '01':  # Factura
            if cliente.get('tipoDoc') != '6':
                raise serializers.ValidationError("Para facturas, el cliente debe tener tipoDoc = '6' (RUC)")
            if len(cliente.get('numeroDoc', '')) != 11:
                raise serializers.ValidationError("Para facturas, el cliente debe tener RUC de 11 dígitos")
        elif tipo == '03':  # Boleta
            if cliente.get('tipoDoc') != '1':
                raise serializers.ValidationError("Para boletas, el cliente debe tener tipoDoc = '1' (DNI)")
            if len(cliente.get('numeroDoc', '')) != 8:
                raise serializers.ValidationError("Para boletas, el cliente debe tener DNI de 8 dígitos")
        
        # Validar montos mínimos
        if total_pagar_enviado <= 0:
            raise serializers.ValidationError("El total a pagar debe ser mayor a cero")
        
        if total_gravado_enviado < 0:
            raise serializers.ValidationError("El total gravado no puede ser negativo")
        
        if igv_enviado < 0:
            raise serializers.ValidationError("El IGV no puede ser negativo")
        
        return data


class ValidationResponseSerializer(serializers.Serializer):
    """Serializer para respuestas de validación"""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    errors = serializers.ListField(child=serializers.CharField(), required=False)
    comprobante_id = serializers.IntegerField(required=False)
    
    # Campos adicionales para debug
    debug_info = serializers.DictField(required=False)


class ConversionResponseSerializer(serializers.Serializer):
    """Serializer para respuestas de conversión"""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    xml_filename = serializers.CharField(required=False)
    zip_filename = serializers.CharField(required=False)
    comprobante_id = serializers.IntegerField(required=False)
    errors = serializers.ListField(child=serializers.CharField(), required=False)
    
    # Campos adicionales para información del proceso
    file_size = serializers.IntegerField(required=False)
    generation_time = serializers.FloatField(required=False)


class HealthCheckResponseSerializer(serializers.Serializer):
    """Serializer para respuestas de health check"""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    status = serializers.CharField()
    version = serializers.CharField(required=False)
    timestamp = serializers.DateTimeField(required=False)
    database_status = serializers.CharField(required=False)
    error = serializers.CharField(required=False)