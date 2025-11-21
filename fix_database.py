"""
Script de Migración Completa para Solucionar el Error de created_by
Ejecuta esto para agregar la columna faltante a la base de datos
"""

import sqlite3
from pathlib import Path
from datetime import datetime
import shutil

def backup_database(db_path):
    """Crear backup de seguridad antes de la migración"""
    print("\n📦 Creando backup de seguridad...")
    
    if not db_path.exists():
        print("   ⚠️ Base de datos no existe, no se requiere backup")
        return None
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = db_path.parent / f"database_backup_{timestamp}.db"
        shutil.copy2(db_path, backup_path)
        print(f"   ✅ Backup creado: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"   ❌ Error al crear backup: {e}")
        return None

def check_column_exists(cursor, table_name, column_name):
    """Verificar si una columna existe en una tabla"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate_known_faces_table(db_path):
    """Migrar tabla known_faces agregando columna created_by"""
    print("\n🔧 Migrando tabla known_faces...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la tabla existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='known_faces'")
        if not cursor.fetchone():
            print("   ⚠️ Tabla known_faces no existe, creando desde cero...")
            create_known_faces_table(cursor)
            conn.commit()
            conn.close()
            return True
        
        # Verificar columnas existentes
        cursor.execute("PRAGMA table_info(known_faces)")
        existing_columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        print(f"   📋 Columnas actuales: {', '.join(existing_columns.keys())}")
        
        # Definir todas las columnas requeridas
        required_columns = {
            'lastname': 'TEXT',
            'age': 'INTEGER',
            'cedula': 'TEXT',
            'birth_date': 'TEXT',
            'crime': 'TEXT',
            'case_number': 'TEXT',
            'created_by': 'INTEGER'  # ← Esta es la columna faltante
        }
        
        # Agregar columnas faltantes
        for col_name, col_type in required_columns.items():
            if col_name not in existing_columns:
                print(f"   ➕ Agregando columna: {col_name} ({col_type})")
                try:
                    if col_name == 'created_by':
                        # Agregar con FOREIGN KEY
                        cursor.execute(f"""
                            ALTER TABLE known_faces 
                            ADD COLUMN {col_name} {col_type}
                            REFERENCES users(id)
                        """)
                    else:
                        cursor.execute(f"ALTER TABLE known_faces ADD COLUMN {col_name} {col_type}")
                    print(f"      ✅ Columna {col_name} agregada exitosamente")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        print(f"      ⚠️ Columna {col_name} ya existe")
                    else:
                        print(f"      ❌ Error: {e}")
                        raise
            else:
                print(f"   ✓ Columna {col_name} ya existe")
        
        # Verificar y popular cédulas vacías
        cursor.execute("SELECT COUNT(*) FROM known_faces WHERE cedula IS NULL OR cedula = ''")
        null_cedulas = cursor.fetchone()[0]
        
        if null_cedulas > 0:
            print(f"\n   🔄 Asignando cédulas automáticas a {null_cedulas} registros...")
            cursor.execute("""
                UPDATE known_faces 
                SET cedula = 'AUTO_' || printf('%05d', id)
                WHERE cedula IS NULL OR cedula = ''
            """)
            print(f"      ✅ Cédulas asignadas")
        
        # Crear índices si no existen
        print("\n   📑 Creando índices...")
        indices = [
            ("idx_known_faces_cedula", "known_faces(cedula)"),
            ("idx_known_faces_case_number", "known_faces(case_number)"),
            ("idx_known_faces_created_by", "known_faces(created_by)")
        ]
        
        for index_name, index_on in indices:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {index_on}")
                print(f"      ✅ Índice {index_name} creado")
            except Exception as e:
                print(f"      ⚠️ Índice {index_name}: {e}")
        
        conn.commit()
        
        # Verificar resultado final
        cursor.execute("PRAGMA table_info(known_faces)")
        final_columns = [row[1] for row in cursor.fetchall()]
        print(f"\n   ✅ Columnas finales: {', '.join(final_columns)}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error durante migración: {e}")
        return False

def create_known_faces_table(cursor):
    """Crear tabla known_faces desde cero con todas las columnas"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS known_faces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            lastname TEXT,
            age INTEGER,
            cedula TEXT UNIQUE NOT NULL,
            birth_date TEXT,
            crime TEXT,
            case_number TEXT,
            embedding BLOB NOT NULL,
            image_path TEXT NOT NULL,
            created_at REAL NOT NULL,
            created_by INTEGER,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)
    print("   ✅ Tabla known_faces creada con todas las columnas")

def verify_migration(db_path):
    """Verificar que la migración fue exitosa"""
    print("\n🔍 Verificando migración...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar columnas
        cursor.execute("PRAGMA table_info(known_faces)")
        columns = [row[1] for row in cursor.fetchall()]
        
        required = ['id', 'name', 'lastname', 'age', 'cedula', 'birth_date', 
                   'crime', 'case_number', 'embedding', 'image_path', 
                   'created_at', 'created_by']
        
        missing = [col for col in required if col not in columns]
        
        if missing:
            print(f"   ❌ Faltan columnas: {', '.join(missing)}")
            conn.close()
            return False
        
        print("   ✅ Todas las columnas requeridas presentes")
        
        # Verificar registros
        cursor.execute("SELECT COUNT(*) FROM known_faces")
        count = cursor.fetchone()[0]
        print(f"   📊 Registros en la tabla: {count}")
        
        # Verificar índices
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='known_faces'")
        indices = [row[0] for row in cursor.fetchall()]
        print(f"   📑 Índices creados: {len(indices)}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error en verificación: {e}")
        return False

def main():
    """Ejecutar migración completa"""
    print("=" * 80)
    print("🔧 SCRIPT DE MIGRACIÓN COMPLETA - FIX DATABASE")
    print("=" * 80)
    print("\nEste script solucionará el error:")
    print("❌ 'table known_faces has no column named created_by'")
    print("\n" + "=" * 80)
    
    db_path = Path('data/database.db')
    
    # 1. Crear backup
    backup_path = backup_database(db_path)
    
    if not db_path.exists():
        print("\n⚠️ Base de datos no existe. Se creará al ejecutar main.py")
        print("   Por favor ejecuta: python main.py")
        return
    
    # 2. Ejecutar migración
    success = migrate_known_faces_table(db_path)
    
    if not success:
        print("\n❌ La migración falló")
        if backup_path:
            print(f"   Puedes restaurar el backup desde: {backup_path}")
        return
    
    # 3. Verificar migración
    verified = verify_migration(db_path)
    
    # 4. Mostrar resumen
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE LA MIGRACIÓN")
    print("=" * 80)
    
    if verified:
        print("\n✅ ¡MIGRACIÓN COMPLETADA EXITOSAMENTE!")
        print("\n✓ La columna 'created_by' ha sido agregada")
        print("✓ Todos los índices han sido creados")
        print("✓ La base de datos está lista para usar")
        print("\n🎉 Ahora puedes agregar rostros sin problemas")
        print("\n📝 Siguiente paso: Ejecuta python main.py")
    else:
        print("\n⚠️ La migración completó con advertencias")
        print("   Revisa los mensajes anteriores para más detalles")
        if backup_path:
            print(f"\n💾 Backup disponible en: {backup_path}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()