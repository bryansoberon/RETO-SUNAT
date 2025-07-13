#!/usr/bin/env python
"""
Script para verificar el estado de la base de datos PostgreSQL
Ejecutar con: python check_database.py
"""

import os
import sys

def check_database_connection():
    """Verificar conexión a la base de datos"""
    print("🔍 Verificando conexión a la base de datos...")
    
    try:
        # Configurar Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sunat_api.settings')
        
        import django
        django.setup()
        
        from django.db import connection
        with connection.cursor() as cursor:
            # Verificar versión de PostgreSQL
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✅ Conexión exitosa a PostgreSQL")
            print(f"   Versión: {version}")
            
            # Verificar nombre de la base de datos
            cursor.execute("SELECT current_database();")
            db_name = cursor.fetchone()[0]
            print(f"   Base de datos: {db_name}")
            
            # Verificar usuario conectado
            cursor.execute("SELECT current_user;")
            user = cursor.fetchone()[0]
            print(f"   Usuario: {user}")
            
            # Verificar host
            cursor.execute("SELECT inet_server_addr();")
            host = cursor.fetchone()[0]
            print(f"   Host: {host}")
            
            # Verificar puerto
            cursor.execute("SELECT inet_server_port();")
            port = cursor.fetchone()[0]
            print(f"   Puerto: {port}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        return False

def check_tables():
    """Verificar si las tablas existen"""
    print("\n🗄️  Verificando tablas de la base de datos...")
    
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            # Listar todas las tablas
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            if tables:
                print("✅ Tablas encontradas:")
                for table in tables:
                    print(f"   - {table[0]}")
                
                # Verificar tablas específicas del proyecto
                table_names = [table[0] for table in tables]
                required_tables = ['comprobantes', 'detalles_comprobante']
                
                for required_table in required_tables:
                    if required_table in table_names:
                        print(f"   ✅ {required_table} - Existe")
                    else:
                        print(f"   ❌ {required_table} - No existe")
                        
            else:
                print("❌ No se encontraron tablas")
                return False
                
            return True
            
    except Exception as e:
        print(f"❌ Error verificando tablas: {str(e)}")
        return False

def check_migrations():
    """Verificar estado de las migraciones"""
    print("\n📋 Verificando estado de migraciones...")
    
    try:
        from django.core.management import execute_from_command_line
        
        # Verificar migraciones pendientes
        print("   Verificando migraciones pendientes...")
        execute_from_command_line(['manage.py', 'showmigrations'])
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando migraciones: {str(e)}")
        return False

def check_sample_data():
    """Verificar si hay datos de ejemplo"""
    print("\n📊 Verificando datos en la base de datos...")
    
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            # Contar comprobantes
            cursor.execute("SELECT COUNT(*) FROM comprobantes;")
            comprobantes_count = cursor.fetchone()[0]
            print(f"   Comprobantes: {comprobantes_count}")
            
            # Contar detalles
            cursor.execute("SELECT COUNT(*) FROM detalles_comprobante;")
            detalles_count = cursor.fetchone()[0]
            print(f"   Detalles: {detalles_count}")
            
            if comprobantes_count > 0:
                print("   ✅ Hay datos en la base de datos")
            else:
                print("   ⚠️  La base de datos está vacía")
                
            return True
            
    except Exception as e:
        print(f"❌ Error verificando datos: {str(e)}")
        return False

def show_database_info():
    """Mostrar información completa de la base de datos"""
    print("\n📋 Información de la Base de Datos:")
    print("=" * 40)
    
    # Verificar variables de entorno
    print("🔧 Variables de entorno:")
    db_name = os.getenv('DB_NAME', 'No configurado')
    db_user = os.getenv('DB_USER', 'No configurado')
    db_host = os.getenv('DB_HOST', 'No configurado')
    db_port = os.getenv('DB_PORT', 'No configurado')
    
    print(f"   DB_NAME: {db_name}")
    print(f"   DB_USER: {db_user}")
    print(f"   DB_HOST: {db_host}")
    print(f"   DB_PORT: {db_port}")
    print(f"   DB_PASSWORD: {'Configurado' if os.getenv('DB_PASSWORD') else 'No configurado'}")

def main():
    """Función principal"""
    print("🔍 Verificación Completa de Base de Datos")
    print("=" * 50)
    
    # Mostrar información de configuración
    show_database_info()
    
    # Verificar conexión
    if not check_database_connection():
        print("\n❌ No se pudo conectar a la base de datos")
        print("💡 Verifica:")
        print("   1. Que PostgreSQL esté corriendo")
        print("   2. Que la contraseña en .env sea correcta")
        print("   3. Que la base de datos 'sunat_api' exista")
        return False
    
    # Verificar tablas
    if not check_tables():
        print("\n❌ Problemas con las tablas")
        print("💡 Ejecuta: python manage.py migrate")
        return False
    
    # Verificar migraciones
    check_migrations()
    
    # Verificar datos
    check_sample_data()
    
    print("\n" + "=" * 50)
    print("🎉 Verificación completada!")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    main() 