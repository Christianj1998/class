import sqlite3
from pathlib import Path

def migrate():
    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()
    
    # Para rostros existentes sin datos adicionales
    cursor.execute('''
        UPDATE known_faces 
        SET lastname = 'Por definir',
            age = 0,
            birth_date = '1900-01-01',
            crime = 'No especificado',
            case_number = 'N/A'
        WHERE lastname IS NULL
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Migración completada")

if __name__ == "__main__":
    migrate()
