#!/usr/bin/env python
"""
Script para configurar la conexión a PostgreSQL manualmente
Ejecutar con: python configure_db.py
"""

import os
import sys

def configure_environment():
    """Configurar variables de entorno para PostgreSQL"""
    print("🔧 Configurando variables de entorno...")
    
    # Solicitar contraseña de PostgreSQL
    password = input("Ingresa la contraseña de PostgreSQL (usuario postgres): ")
    
    # Configurar variables de entorno
    os.environ['DB_NAME'] = 'sunat_api'
    os.environ['DB_USER'] = 'postgres'
    os.environ['DB_PASSWORD'] = '123'
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_PORT'] = '5432'
    
    print("✅ Variables de entorno configuradas")
    return True

def test_connection():
    """Probar conexión a PostgreSQL"""
    print("\n🔌 Probando conexión a PostgreSQL...")
    
    try:
        # Configurar Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sunat_api.settings')
        
        import django
        django.setup()
        
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✅ Conexión exitosa a PostgreSQL")
            print(f"   Versión: {version}")
            return True
            
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        return False

def run_migrations():
    """Ejecutar migraciones"""
    print("\n🗄️  Ejecutando migraciones...")
    
    try:
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Migraciones ejecutadas correctamente")
        return True
    except Exception as e:
        print(f"❌ Error en migraciones: {str(e)}")
        return False

def create_superuser():
    """Crear superusuario"""
    print("\n👤 ¿Quieres crear un superusuario? (s/n): ", end="")
    response = input().lower()
    
    if response in ['s', 'si', 'sí', 'y', 'yes']:
        try:
            from django.core.management import execute_from_command_line
            execute_from_command_line(['manage.py', 'createsuperuser'])
            print("✅ Superusuario creado")
            return True
        except Exception as e:
            print(f"❌ Error creando superusuario: {str(e)}")
            return False
    else:
        print("⏭️  Saltando creación de superusuario")
        return True

def main():
    """Función principal"""
    print("🚀 Configuración Manual de PostgreSQL")
    print("=" * 40)
    
    # Configurar entorno
    if not configure_environment():
        return False
    
    # Probar conexión
    if not test_connection():
        print("\n💡 Soluciones posibles:")
        print("1. Verifica que PostgreSQL esté corriendo")
        print("2. Verifica la contraseña del usuario postgres")
        print("3. Verifica que la base de datos 'sunat_api' exista")
        return False
    
    # Ejecutar migraciones
    if not run_migrations():
        return False
    
    # Crear superusuario
    create_superuser()
    
    print("\n" + "=" * 40)
    print("🎉 Configuración completada!")
    print("=" * 40)
    print("\n📋 Para ejecutar el servidor:")
    print("python manage.py runserver")
    print("\n📋 Para probar la API:")
    print("python test_api.py")
    
    return True

if __name__ == "__main__":
    main() 