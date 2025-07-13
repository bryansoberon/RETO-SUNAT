from rest_framework import serializers
from .models import Comprobante, DetalleComprobante
from .utils import validar_ruc_sunat


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
    numero = serializers.CharField(max_length=8, min_length=8)
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
    
    def validate_emisor(self, value):
        """Validar datos del emisor"""
        if not value:
            raise serializers.ValidationError("Los datos del emisor son requeridos")
        
        ruc = value.get('ruc')
        if not ruc:
            raise serializers.ValidationError("El RUC del emisor es requerido")
        
        if not ruc.isdigit():
            raise serializers.ValidationError("El RUC del emisor debe contener solo números")
        
        if not validar_ruc_sunat(ruc):
            raise serializers.ValidationError("El RUC del emisor no es válido según el algoritmo oficial de SUNAT")
        
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
        """Validar formato de serie: 2 letras + 3 dígitos (ej: F001, B001)"""
        import re
        if not re.match(r'^[A-Z]{1,2}[0-9]{3}$', value):
            raise serializers.ValidationError("La serie debe tener el formato: 1 o 2 letras seguidas de 3 dígitos (ej: F001, B001)")
        return value

    def validate_numero(self, value):
        if not value.isdigit() or len(value) != 8:
            raise serializers.ValidationError("El número debe tener 8 dígitos numéricos")
        return value

    def validate_items(self, value):
        for item in value:
            required_fields = ['id', 'cantidad', 'descripcion', 'valorUnitario', 'valorTotal']
            for field in required_fields:
                if field not in item:
                    raise serializers.ValidationError(f"Campo '{field}' requerido en items")
            if item['cantidad'] <= 0:
                raise serializers.ValidationError("La cantidad debe ser mayor a 0")
            if item['valorUnitario'] < 0:
                raise serializers.ValidationError("El valor unitario no puede ser negativo")
            # Validar máximo dos decimales
            if round(float(item['valorUnitario']), 2) != float(item['valorUnitario']):
                raise serializers.ValidationError("El valor unitario debe tener máximo dos decimales")
            if round(float(item['valorTotal']), 2) != float(item['valorTotal']):
                raise serializers.ValidationError("El valor total debe tener máximo dos decimales")
        return value

    def validate(self, data):
        from decimal import Decimal, ROUND_HALF_UP
        # Validar que los importes tengan máximo dos decimales
        for field in ['totalGravado', 'totalIGV', 'totalPrecioVenta', 'totalImportePagar']:
            valor = data.get(field)
            if valor is not None:
                valor_str = str(valor)
                if '.' in valor_str and len(valor_str.split('.')[-1]) > 2:
                    raise serializers.ValidationError(f"El campo {field} debe tener máximo dos decimales")
        # Validar que el total coincida con la suma de items
        total_calculado = sum(
            Decimal(str(item.get('valorTotal', 0))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            for item in data.get('items', [])
        )
        if abs(total_calculado - data['totalImportePagar']) > Decimal('0.01'):
            raise serializers.ValidationError(
                f"El total ({data['totalImportePagar']}) no coincide con la suma de items ({total_calculado})"
            )
        # Validar campos obligatorios según tipo de comprobante
        tipo = data.get('tipoDocumento')
        cliente = data.get('cliente', {})
        if tipo == '01':  # Factura
            if cliente.get('tipoDoc') != '6' or len(cliente.get('numeroDoc', '')) != 11:
                raise serializers.ValidationError("Para facturas, el cliente debe tener RUC (tipoDoc=6, 11 dígitos)")
        elif tipo == '03':  # Boleta
            if cliente.get('tipoDoc') != '1' or len(cliente.get('numeroDoc', '')) != 8:
                raise serializers.ValidationError("Para boletas, el cliente debe tener DNI (tipoDoc=1, 8 dígitos)")
        return data
    
    def validate_items(self, value):
        """Validar estructura de los items"""
        for item in value:
            required_fields = ['id', 'cantidad', 'descripcion', 'valorUnitario', 'valorTotal']
            for field in required_fields:
                if field not in item:
                    raise serializers.ValidationError(f"Campo '{field}' requerido en items")
            
            if item['cantidad'] <= 0:
                raise serializers.ValidationError("La cantidad debe ser mayor a 0")
            
            if item['valorUnitario'] < 0:
                raise serializers.ValidationError("El valor unitario no puede ser negativo")
        
        return value


class ValidationResponseSerializer(serializers.Serializer):
    """Serializer para respuestas de validación"""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    errors = serializers.ListField(child=serializers.CharField(), required=False)
    comprobante_id = serializers.IntegerField(required=False)


class ConversionResponseSerializer(serializers.Serializer):
    """Serializer para respuestas de conversión"""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    xml_filename = serializers.CharField(required=False)
    zip_filename = serializers.CharField(required=False)
    comprobante_id = serializers.IntegerField(required=False)
    errors = serializers.ListField(child=serializers.CharField(), required=False) 