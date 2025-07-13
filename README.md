# API REST SUNAT - Comprobantes Electrónicos

API REST desarrollada con Django para la generación, validación, firmado digital y empaquetado de comprobantes electrónicos en formato XML UBL 2.1, 100% compatible con los estándares oficiales de SUNAT Perú.

## ✅ Comprobantes Soportados

- **Factura (01)** - XML UBL Invoice con atributos SUNAT
- **Boleta (03)** - XML UBL Invoice con Note obligatorio
- **Nota de Crédito (07)** - XML UBL CreditNote con referencias
- **Nota de Débito (08)** - XML UBL DebitNote con referencias

## ✅ Funcionalidades Avanzadas

- Recepción de datos en formato JSON
- Conversión automática a XML UBL 2.1 con atributos SUNAT
- Validación completa de estructura y datos
- Empaquetado automático en ZIP (requerido por SUNAT)
- Nombres de archivo según estándar SUNAT: `RUC-TIPO-SERIE-NUMERO.xml/zip`
- API RESTful lista para integración

## ✅ Cumplimiento SUNAT 100%

- Atributos `listAgencyName="PE:SUNAT"` en códigos
- Catálogos oficiales: catalogo01, catalogo09, catalogo10
- Elementos obligatorios por tipo de comprobante
- Estructura UBL 2.1 completa y validada

## 🚀 Endpoints Disponibles

### 1. POST /api/v1/validate/
Valida los datos JSON de un comprobante electrónico.

**Ejemplo de Request:**
```json
{
    "tipo_comprobante": "01",
    "ruc_emisor": "20123456789",
    "serie": "F001",
    "numero": "00000001",
    "ruc_cliente": "20123456788",
    "nombre_cliente": "CLIENTE EJEMPLO S.A.C.",
    "direccion_cliente": "Av. Principal 123, Lima",
    "total_gravado": 100.00,
    "total_igv": 18.00,
    "total": 118.00,
    "detalles": [
        {
            "descripcion": "Producto ejemplo",
            "cantidad": 2,
            "precio_unitario": 50.00
        }
    ]
}
```

**Ejemplo de Response:**
```json
{
    "success": true,
    "message": "Comprobante validado correctamente",
    "comprobante_id": 1
}
```

### 2. POST /api/v1/convert/
Convierte datos JSON a XML UBL 2.1 y genera archivo ZIP.

**Ejemplo de Response:**
```json
{
    "success": true,
    "message": "Comprobante convertido y empaquetado correctamente",
    "xml_filename": "20123456789-01-F001-00000001.xml",
    "zip_filename": "20123456789-01-F001-00000001.zip",
    "comprobante_id": 1
}
```

### 3. GET /api/v1/xml/{nombre_xml}/
Descarga el archivo XML por nombre.

**Ejemplo:**
```
GET /api/v1/xml/20123456789-01-F001-00000001.xml/
```

### 4. GET /health/
Verifica el estado de salud del sistema.

**Ejemplo de Response:**
```json
{
    "success": true,
    "message": "API SUNAT funcionando correctamente",
    "status": "healthy",
    "version": "1.0.0"
}
```

## 🛠️ Instalación y Configuración

### Requisitos Previos
- Python 3.8+ (recomendado: Python 3.11 o 3.12)
- pip
- virtualenv (recomendado)

**⚠️ Nota importante:** Python 3.13 es experimental. Algunas librerías como Pillow aún no tienen soporte oficial.

### Pasos de Instalación

1. **Clonar el repositorio:**
```bash
git clone <url-del-repositorio>
cd RETO-SUNAT
```

2. **Crear entorno virtual:**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias:**

**Para Python 3.8 - 3.12:**
```bash
pip install -r requirements.txt
```

**Para Python 3.13 (Windows):**
```bash
# Opción 1: Usar script automático
install_python313.bat

# Opción 2: Instalación manual
pip install Django==4.2.7 djangorestframework==3.14.0 django-cors-headers==4.3.1
pip install requests==2.31.0 python-decouple==3.8 xmlschema==2.5.1
pip install python-dateutil==2.8.2 defusedxml>=0.7.1 zeep==4.2.1
# lxml se instalará automáticamente si hay wheels disponibles
```

4. **Configurar variables de entorno:**
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

5. **Ejecutar migraciones:**
```bash
python manage.py migrate
```

6. **Crear superusuario (opcional):**
```bash
python manage.py createsuperuser
```

7. **Ejecutar el servidor:**
```bash
python manage.py runserver
```

## 📁 Estructura del Proyecto

```
RETO-SUNAT/
├── sunat_api/                 # Configuración principal de Django
│   ├── __init__.py
│   ├── settings.py           # Configuración del proyecto
│   ├── urls.py               # URLs principales
│   ├── wsgi.py               # Configuración WSGI
│   └── asgi.py               # Configuración ASGI
├── comprobantes/             # Aplicación principal
│   ├── __init__.py
│   ├── models.py             # Modelos de datos
│   ├── views.py              # Vistas de la API
│   ├── serializers.py        # Serializers para JSON
│   ├── urls.py               # URLs de la aplicación
│   ├── utils.py              # Lógica de generación XML UBL
│   ├── admin.py              # Administración Django
│   └── migrations/           # Migraciones de base de datos
├── media/                    # Archivos generados
│   ├── xml/                  # Archivos XML
│   └── zip/                  # Archivos ZIP
├── manage.py                 # Script de gestión Django
├── requirements.txt          # Dependencias Python
└── README.md                 # Este archivo
```

## 🔧 Configuración

### Compatibilidad de Python
Este proyecto es compatible con Python 3.8+ pero tiene consideraciones especiales:

- **Python 3.8 - 3.12**: Completamente compatible
- **Python 3.13**: Funcionalidad básica, algunas librerías limitadas

### Variables de Entorno (.env)
```env
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Configuración SUNAT
Las configuraciones específicas de SUNAT se encuentran en `settings.py`:

```python
SUNAT_CONFIG = {
    'XML_OUTPUT_DIR': os.path.join(BASE_DIR, 'media', 'xml'),
    'ZIP_OUTPUT_DIR': os.path.join(BASE_DIR, 'media', 'zip'),
    'UBL_VERSION': '2.1',
    'COUNTRY_CODE': 'PE',
    'AGENCY_NAME': 'PE:SUNAT',
}
```

## 📊 Base de Datos

El proyecto utiliza SQLite por defecto. Los modelos principales son:

- **Comprobante**: Almacena información del comprobante electrónico
- **DetalleComprobante**: Almacena los detalles/items del comprobante

## 🧪 Testing

Para ejecutar las pruebas:

```bash
python manage.py test
```

## 📝 Ejemplos de Uso

### Ejemplo con cURL

**Validar comprobante:**
```bash
curl -X POST http://localhost:8000/api/v1/validate/ \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_comprobante": "01",
    "ruc_emisor": "20123456789",
    "serie": "F001",
    "numero": "00000001",
    "nombre_cliente": "CLIENTE EJEMPLO",
    "total": 118.00,
    "detalles": [{"descripcion": "Producto", "cantidad": 1, "precio_unitario": 100.00}]
  }'
```

**Convertir a XML:**
```bash
curl -X POST http://localhost:8000/api/v1/convert/ \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_comprobante": "01",
    "ruc_emisor": "20123456789",
    "serie": "F001",
    "numero": "00000001",
    "nombre_cliente": "CLIENTE EJEMPLO",
    "total": 118.00,
    "detalles": [{"descripcion": "Producto", "cantidad": 1, "precio_unitario": 100.00}]
  }'
```

## 🔒 Seguridad

- Validación completa de datos de entrada
- Sanitización de archivos XML
- Control de acceso a archivos
- Logging de errores y operaciones

## 📞 Soporte

Para soporte técnico o consultas sobre la implementación, contactar al equipo de desarrollo.

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo LICENSE para más detalles.

---

**Desarrollado con ❤️ para cumplir con los estándares SUNAT Perú** 