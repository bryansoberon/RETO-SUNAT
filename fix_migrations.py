#!/usr/bin/env python3
"""
Script para solucionar problemas con migraciones Django
Ejecutar con: python fix_migrations.py
"""

import os
import sys
import subprocess
import django
from pathlib import Path

def setup_django():
    """Configurar Django"""
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sunat_api.settings')
        django.setup()
        return True
    except Exception as e:
        print(f"❌ Error configurando Django: {e}")
        return False

def run_command(command, description):
    """Ejecutar comando Django"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True, cwd=os.getcwd())
        print(f"✅ {description} completado")
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}")
        print(f"   Error: {e.stderr.strip()}")
        print(f"   Output: {e.stdout.strip()}")
        return False, e.stderr

def check_database_connection():
    """Verificar conexión a base de datos"""
    print("🔍 Verificando conexión a base de datos...")
    
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✅ Conexión a base de datos exitosa")
        return True
    except Exception as e:
        print(f"❌ Error de conexión a base de datos: {e}")
        print("\n💡 Posibles soluciones:")
        print("   1. Verificar que MySQL esté corriendo")
        print("   2. Verificar credenciales en .env")
        print("   3. Verificar que la base de datos 'sunat_api' exista")
        return False

def check_migrations_folder():
    """Verificar que exista la carpeta de migraciones"""
    migrations_path = Path("comprobantes/migrations")
    
    if not migrations_path.exists():
        print("📁 Creando carpeta de migraciones...")
        migrations_path.mkdir(parents=True, exist_ok=True)
        
        # Crear __init__.py
        init_file = migrations_path / "__init__.py"
        init_file.write_text(" ")
        print("✅ Carpeta de migraciones creada")
        return True
    
    print("✅ Carpeta de migraciones existe")
    return True

def reset_migrations():
    """Resetear migraciones"""
    print("🔄 Reseteando migraciones...")
    
    migrations_path = Path("comprobantes/migrations")
    
    # Eliminar archivos de migración excepto __init__.py
    if migrations_path.exists():
        for file in migrations_path.glob("*.py"):
            if file.name != "__init__.py":
                file.unlink()
                print(f"   🗑️  Eliminado: {file.name}")
    
    print("✅ Migraciones reseteadas")

def create_fresh_migrations():
    """Crear migraciones desde cero"""
    print("🆕 Creando migraciones frescas...")
    
    # Eliminar migraciones existentes
    reset_migrations()
    
    # Crear nuevas migraciones
    success, output = run_command(
        "python manage.py makemigrations comprobantes", 
        "Creando migraciones"
    )
    
    return success

def check_models_syntax():
    """Verificar sintaxis de models.py"""
    print("🔍 Verificando sintaxis de models.py...")
    
    try:
        from comprobantes import models
        print("✅ Sintaxis de models.py correcta")
        return True
    except Exception as e:
        print(f"❌ Error en models.py: {e}")
        return False

def show_migration_status():
    """Mostrar estado actual de migraciones"""
    print("📋 Estado actual de migraciones:")
    
    success, output = run_command(
        "python manage.py showmigrations",
        "Consultando estado de migraciones"
    )
    
    return success

def apply_migrations():
    """Aplicar migraciones"""
    print("⚡ Aplicando migraciones...")
    
    success, output = run_command(
        "python manage.py migrate",
        "Aplicando migraciones"
    )
    
    return success

def create_superuser_prompt():
    """Preguntar si crear superusuario"""
    print(f"\n👤 ¿Deseas crear un superusuario? (s/n): ", end="")
    response = input().lower()
    
    if response in ['s', 'si', 'sí', 'y', 'yes']:
        run_command(
            "python manage.py createsuperuser",
            "Creando superusuario"
        )

def check_database_tables():
    """Verificar que las tablas se crearon correctamente"""
    print("🔍 Verificando tablas en base de datos...")
    
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            
            if tables:
                print("✅ Tablas encontradas:")
                for table in tables:
                    print(f"   📋 {table[0]}")
                
                # Verificar tablas específicas
                table_names = [table[0] for table in tables]
                required_tables = [
                    'comprobantes', 
                    'detalles_comprobante',
                    'sunat_responses',
                    'sunat_configurations', 
                    'sunat_logs'
                ]
                
                missing_tables = []
                for table in required_tables:
                    if table in table_names:
                        print(f"   ✅ {table}")
                    else:
                        print(f"   ❌ {table} - FALTANTE")
                        missing_tables.append(table)
                
                if missing_tables:
                    print(f"\n⚠️  Faltan tablas: {', '.join(missing_tables)}")
                    return False
                else:
                    print(f"\n✅ Todas las tablas requeridas están presentes")
                    return True
            else:
                print("❌ No se encontraron tablas")
                return False
                
    except Exception as e:
        print(f"❌ Error verificando tablas: {e}")
        return False

def diagnose_migration_errors():
    """Diagnosticar errores comunes de migración"""
    print("🔍 Diagnosticando problemas de migración...")
    
    # 1. Verificar archivos de migración
    migrations_path = Path("comprobantes/migrations")
    migration_files = list(migrations_path.glob("*.py"))
    migration_files = [f for f in migration_files if f.name != "__init__.py"]
    
    print(f"📁 Archivos de migración encontrados: {len(migration_files)}")
    for file in migration_files:
        print(f"   📄 {file.name}")
    
    # 2. Verificar dependencias en migraciones
    for file in migration_files:
        try:
            content = file.read_text()
            if "dependencies" in content:
                print(f"   🔗 {file.name} tiene dependencias")
        except Exception as e:
            print(f"   ❌ Error leyendo {file.name}: {e}")
    
    # 3. Verificar estado de Django
    try:
        success, output = run_command(
            "python manage.py check",
            "Verificando sistema Django"
        )
        if not success:
            return False
    except Exception as e:
        print(f"❌ Error en check Django: {e}")
        return False
    
    return True

def main():
    """Función principal"""
    print("🛠️  SOLUCIONADOR DE MIGRACIONES - API SUNAT")
    print("=" * 60)
    
    # Verificar configuración básica
    if not setup_django():
        return False
    
    # Verificar conexión a base de datos
    if not check_database_connection():
        return False
    
    # Verificar sintaxis de modelos
    if not check_models_syntax():
        print("\n💡 Corrige los errores en models.py antes de continuar")
        return False
    
    # Verificar carpeta de migraciones
    check_migrations_folder()
    
    # Mostrar estado actual
    show_migration_status()
    
    # Diagnosticar problemas
    diagnose_migration_errors()
    
    print(f"\n🔧 Opciones de solución:")
    print(f"   1. Crear migraciones frescas (recomendado)")
    print(f"   2. Solo aplicar migraciones existentes")
    print(f"   3. Resetear completamente y recrear")
    print(f"   4. Solo verificar estado actual")
    
    try:
        opcion = input(f"\nSelecciona opción (1-4) [1]: ").strip() or "1"
        
        if opcion == "1":
            # Crear migraciones frescas
            if create_fresh_migrations():
                if apply_migrations():
                    check_database_tables()
                    create_superuser_prompt()
                    print("\n🎉 ¡Migraciones completadas exitosamente!")
                    return True
            
        elif opcion == "2":
            # Solo aplicar migraciones
            if apply_migrations():
                check_database_tables()
                print("\n🎉 ¡Migraciones aplicadas exitosamente!")
                return True
            
        elif opcion == "3":
            # Reset completo
            print("\n⚠️  ADVERTENCIA: Esto eliminará todas las migraciones existentes")
            confirm = input("¿Estás seguro? (s/n): ").lower()
            if confirm in ['s', 'si', 'sí', 'y', 'yes']:
                reset_migrations()
                if create_fresh_migrations():
                    if apply_migrations():
                        check_database_tables()
                        create_superuser_prompt()
                        print("\n🎉 ¡Reset y migraciones completadas!")
                        return True
            
        elif opcion == "4":
            # Solo verificar
            show_migration_status()
            check_database_tables()
            return True
            
        else:
            print("❌ Opción inválida")
            return False
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Operación interrumpida por el usuario")
        return False
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        return False
    
    return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ Proceso completado exitosamente")
            print("💡 Ahora puedes ejecutar: python manage.py runserver")
        else:
            print("\n❌ Proceso completado con errores")
            print("💡 Revisa los errores mostrados arriba")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
        sys.exit(1)