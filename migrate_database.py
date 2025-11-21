
import sqlite3
from pathlib import Path
from loguru import logger

def migrate_database():
    """Migrar base de datos existente"""
    
    db_path = Path('data/database.db')
    
    if not db_path.exists():
        logger.error(f"Base de datos no encontrada: {db_path}")
        print("❌ No se encontró la base de datos.")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Verificar si la tabla existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='known_faces'")
        if not cursor.fetchone():
            logger.info("Tabla known_faces no existe, creando...")
            create_new_table(cursor)
        else:
            logger.info("Tabla known_faces existe, verificando columnas...")
            migrate_existing_table(cursor)
        
        conn.commit()
        conn.close()
        
        logger.success("✅ Migración completada exitosamente")
        print("✅ Base de datos migrada correctamente")
        return True
        
    except Exception as e:
        logger.error(f"Error durante migración: {e}")
        print(f"❌ Error durante migración: {e}")
        return False


def create_new_table(cursor):
    """Crear tabla known_faces desde cero"""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS known_faces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            lastname TEXT,
            age INTEGER,
            cedula TEXT UNIQUE,
            birth_date TEXT,
            crime TEXT,
            case_number TEXT,
            embedding BLOB NOT NULL,
            image_path TEXT NOT NULL,
            created_at REAL NOT NULL,
            created_by INTEGER,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    
    # Crear índices
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_known_faces_cedula 
        ON known_faces(cedula)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_known_faces_case_number 
        ON known_faces(case_number)
    ''')
    
    logger.info("Tabla known_faces creada exitosamente")


def migrate_existing_table(cursor):
    """Migrar tabla existing agregando nuevas columnas"""
    
    # Obtener información de las columnas existentes
    cursor.execute("PRAGMA table_info(known_faces)")
    columns = [row[1] for row in cursor.fetchall()]
    
    logger.info(f"Columnas actuales: {columns}")
    
    # Definir columnas requeridas
    required_columns = {
        'lastname': 'TEXT',
        'age': 'INTEGER',
        'cedula': 'TEXT UNIQUE',
        'birth_date': 'TEXT',
        'crime': 'TEXT',
        'case_number': 'TEXT'
    }
    
    # Agregar columnas faltantes
    for col_name, col_type in required_columns.items():
        if col_name not in columns:
            logger.info(f"Agregando columna: {col_name}")
            try:
                # Para cedula que debe ser UNIQUE, manejar diferente
                if col_name == 'cedula':
                    cursor.execute(f'ALTER TABLE known_faces ADD COLUMN {col_name} {col_type} DEFAULT NULL')
                else:
                    cursor.execute(f'ALTER TABLE known_faces ADD COLUMN {col_name} {col_type}')
                logger.info(f"✅ Columna {col_name} agregada")
            except Exception as e:
                logger.error(f"Error al agregar columna {col_name}: {e}")
                # Si falla por ser UNIQUE, agregar sin constraint
                if 'UNIQUE' in col_type:
                    cursor.execute(f'ALTER TABLE known_faces ADD COLUMN {col_name} TEXT')
                    logger.info(f"✅ Columna {col_name} agregada (sin UNIQUE constraint)")
        else:
            logger.info(f"✓ Columna {col_name} ya existe")
    
    # Crear índices si no existen
    try:
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_known_faces_cedula 
            ON known_faces(cedula)
        ''')
        logger.info("Índice cedula creado/verificado")
    except Exception as e:
        logger.warning(f"No se pudo crear índice cedula: {e}")
    
    try:
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_known_faces_case_number 
            ON known_faces(case_number)
        ''')
        logger.info("Índice case_number creado/verificado")
    except Exception as e:
        logger.warning(f"No se pudo crear índice case_number: {e}")
    
    # Poblar cedula con valores por defecto si están vacías
    cursor.execute("SELECT COUNT(*) FROM known_faces WHERE cedula IS NULL")
    null_count = cursor.fetchone()[0]
    
    if null_count > 0:
        logger.info(f"Poblando {null_count} registros con cédula por defecto...")
        cursor.execute('''
            UPDATE known_faces 
            SET cedula = 'UNKNOWN_' || id
            WHERE cedula IS NULL
        ''')
        logger.info(f"✅ {null_count} registros actualizados")


def backup_database():
    """Crear backup de la base de datos antes de migrar"""
    import shutil
    from datetime import datetime
    
    db_path = Path('data/database.db')
    
    if db_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = Path(f'data/database_backup_{timestamp}.db')
        
        shutil.copy2(db_path, backup_path)
        logger.info(f"✅ Backup creado: {backup_path}")
        print(f"✅ Backup creado: {backup_path}")
        return True
    
    return False


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("🔄 Script de Migración de Base de Datos")
    print("=" * 60)
    
    # Crear backup
    print("\n📦 Creando backup...")
    if backup_database():
        print("✅ Backup completado")
    
    # Ejecutar migración
    print("\n🔄 Ejecutando migración...")
    success = migrate_database()
    
    if success:
        print("\n✅ Migración completada exitosamente")
        print("Ahora puedes ejecutar: python main.py")
        sys.exit(0)
    else:
        print("\n❌ Error en la migración")
        print("Por favor revisa los logs en logs/error.log")
        sys.exit(1)