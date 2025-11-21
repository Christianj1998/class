import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Dict
from pathlib import Path
from loguru import logger
import time

@dataclass
class FaceLogEntry:
    id: int
    timestamp: float
    camera_id: int
    camera_name: str
    face_name: str
    age: Optional[int]
    gender: Optional[str]
    confidence: float
    screenshot_path: Optional[str]
    user_id: Optional[int] = None

    def __post_init__(self):
        if isinstance(self.timestamp, bytes):
            self.timestamp = float(self.timestamp.decode('utf-8'))
        elif isinstance(self.timestamp, str):
            self.timestamp = float(self.timestamp)

class FaceDatabase:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database with required tables and handle migrations"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        email TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'viewer',
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        created_at REAL NOT NULL,
                        last_login REAL,
                        created_by INTEGER,
                        FOREIGN KEY (created_by) REFERENCES users(id)
                    )
                ''')
                
                # Create face_logs table with user_id
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS face_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        camera_id INTEGER NOT NULL,
                        camera_name TEXT NOT NULL,
                        face_name TEXT NOT NULL,
                        age INTEGER,
                        gender TEXT,
                        confidence REAL NOT NULL,
                        screenshot_path TEXT,
                        user_id INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                ''')
                
                # Create known_faces table with new columns
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
                
                # Create audit_log table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        user_id INTEGER NOT NULL,
                        action TEXT NOT NULL,
                        details TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                ''')
                
                # ====== MIGRATION SECTION ======
                # Check and add missing columns to known_faces
                cursor.execute("PRAGMA table_info(known_faces)")
                columns = [row[1] for row in cursor.fetchall()]
                
                required_columns = {
                    'lastname': 'TEXT',
                    'age': 'INTEGER',
                    'cedula': 'TEXT',
                    'birth_date': 'TEXT',
                    'crime': 'TEXT',
                    'case_number': 'TEXT'
                }
                
                for col_name, col_type in required_columns.items():
                    if col_name not in columns:
                        logger.warning(f"Migrating known_faces table: adding {col_name} column")
                        try:
                            cursor.execute(f'ALTER TABLE known_faces ADD COLUMN {col_name} {col_type}')
                            logger.info(f"✅ Column {col_name} added successfully")
                        except sqlite3.OperationalError as e:
                            logger.error(f"Migration failed for {col_name}: {e}")
                
                # Ensure cedula has values (migrate existing records)
                cursor.execute("SELECT COUNT(*) FROM known_faces WHERE cedula IS NULL OR cedula = ''")
                result = cursor.fetchone()
                null_count = result[0] if result else 0
                
                if null_count > 0:
                    logger.warning(f"Populating {null_count} records with default cedula values")
                    cursor.execute('''
                        UPDATE known_faces 
                        SET cedula = 'UNKNOWN_' || id
                        WHERE cedula IS NULL OR cedula = ''
                    ''')
                    logger.info(f"✅ Updated {null_count} records")
                
                # Create indexes for better performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_face_logs_timestamp 
                    ON face_logs(timestamp)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_face_logs_camera_id 
                    ON face_logs(camera_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_face_logs_face_name 
                    ON face_logs(face_name)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_face_logs_user_id 
                    ON face_logs(user_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_known_faces_cedula 
                    ON known_faces(cedula)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_known_faces_case_number 
                    ON known_faces(case_number)
                ''')
                
                # Check if user_id column exists in face_logs (MIGRATION)
                cursor.execute("PRAGMA table_info(face_logs)")
                face_logs_columns = [row[1] for row in cursor.fetchall()]
                
                if 'user_id' not in face_logs_columns:
                    logger.warning("Migrating face_logs table: adding user_id column")
                    try:
                        cursor.execute('''
                            ALTER TABLE face_logs 
                            ADD COLUMN user_id INTEGER REFERENCES users(id)
                        ''')
                        logger.info("✅ Column user_id added to face_logs")
                    except sqlite3.OperationalError as e:
                        logger.error(f"Migration failed: {e}")
                
                # Create default admin user if no users exist
                cursor.execute('SELECT COUNT(*) FROM users')
                if cursor.fetchone()[0] == 0:
                    import bcrypt
                    import secrets
                    import string
                    
                    random_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
                    
                    salt = bcrypt.gensalt()
                    hashed = bcrypt.hashpw(random_password.encode('utf-8'), salt)
                    
                    cursor.execute('''
                        INSERT INTO users (username, email, password_hash, role, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', ('admin', 'admin@system.local', hashed.decode('utf-8'), 'admin', time.time()))
                    
                    logger.warning("=" * 60)
                    logger.warning("DEFAULT ADMIN USER CREATED")
                    logger.warning(f"Username: admin")
                    logger.warning(f"Password: {random_password}")
                    logger.warning("SAVE THIS PASSWORD - IT WILL NOT BE SHOWN AGAIN!")
                    logger.warning("=" * 60)
                    
                    credentials_file = self.db_path.parent / "ADMIN_CREDENTIALS.txt"
                    with open(credentials_file, 'w') as f:
                        f.write(f"Admin Credentials (Created: {time.strftime('%Y-%m-%d %H:%M:%S')})\n")
                        f.write(f"Username: admin\n")
                        f.write(f"Password: {random_password}\n")
                        f.write("\nDELETE THIS FILE AFTER FIRST LOGIN AND PASSWORD CHANGE!\n")
                    logger.info(f"Credentials saved to: {credentials_file}")
                
                conn.commit()
                logger.success("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    # ============ USER MANAGEMENT ============
    
    def create_user(self, username: str, email: str, password_hash: str, 
                   role: str = 'viewer', created_by: Optional[int] = None) -> Optional[int]:
        """Create a new user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, role, created_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (username, email, password_hash, role, time.time(), created_by))
                conn.commit()
                user_id = cursor.lastrowid
                
                # Log audit
                if created_by:
                    self.log_audit(created_by, 'create_user', f"Created user: {username}")
                
                return user_id
        except sqlite3.IntegrityError as e:
            logger.error(f"User already exists: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM users WHERE username = ?
                ''', (username,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM users WHERE id = ?
                ''', (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, username, email, role, is_active, created_at, last_login
                    FROM users
                    ORDER BY username
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user fields"""
        try:
            allowed_fields = ['email', 'role', 'is_active']
            updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
            
            if not updates:
                return False
            
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [user_id]
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE users SET {set_clause} WHERE id = ?
                ''', values)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    def update_user_password(self, user_id: int, password_hash: str) -> bool:
        """Update user password"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET password_hash = ? WHERE id = ?
                ''', (password_hash, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            return False
    
    def update_last_login(self, user_id: int) -> bool:
        """Update last login timestamp"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET last_login = ? WHERE id = ?
                ''', (time.time(), user_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            return False
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user (soft delete - sets is_active to False)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET is_active = 0 WHERE id = ?
                ''', (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    # ============ AUDIT LOG ============
    
    def log_audit(self, user_id: int, action: str, details: Optional[str] = None):
        """Log user action for audit trail"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO audit_log (timestamp, user_id, action, details)
                    VALUES (?, ?, ?, ?)
                ''', (time.time(), user_id, action, details))
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging audit: {e}")
    
    def get_audit_logs(self, user_id: Optional[int] = None, limit: int = 100) -> List[Dict]:
        """Get audit logs"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if user_id:
                    cursor.execute('''
                        SELECT a.*, u.username 
                        FROM audit_log a
                        JOIN users u ON a.user_id = u.id
                        WHERE a.user_id = ?
                        ORDER BY a.timestamp DESC
                        LIMIT ?
                    ''', (user_id, limit))
                else:
                    cursor.execute('''
                        SELECT a.*, u.username 
                        FROM audit_log a
                        JOIN users u ON a.user_id = u.id
                        ORDER BY a.timestamp DESC
                        LIMIT ?
                    ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting audit logs: {e}")
            return []

    # ============ FACE LOGS ============
    
    def log_face_event(self, event, user_id: Optional[int] = None) -> int:
        """Log a face recognition event"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO face_logs (
                        timestamp, camera_id, camera_name, face_name,
                        age, gender, confidence, screenshot_path, user_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    float(event.timestamp),
                    int(event.camera_id),
                    str(event.camera_name),
                    str(event.face_name),
                    int(event.age) if event.age else None,
                    str(event.gender) if event.gender else None,
                    float(event.confidence),
                    str(event.screenshot_path) if event.screenshot_path else None,
                    user_id
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error logging face event: {e}")
            raise

    def get_face_logs(self, limit: int = 100, 
                 camera_id: Optional[int] = None,
                 face_name: Optional[str] = None,
                 start_time: Optional[float] = None,
                 end_time: Optional[float] = None) -> List[FaceLogEntry]:
        """Retrieve face logs with optional filters"""
        try:
            query = '''
                SELECT id, timestamp, camera_id, camera_name, face_name, 
                       age, gender, confidence, screenshot_path, user_id
                FROM face_logs
            '''
            params = []
            conditions = []
            
            if camera_id is not None:
                conditions.append("camera_id = ?")
                params.append(camera_id)
                
            if face_name is not None:
                conditions.append("face_name = ?")
                params.append(face_name)
                
            if start_time is not None:
                conditions.append("timestamp >= ?")
                params.append(float(start_time))
                
            if end_time is not None:
                conditions.append("timestamp <= ?")
                params.append(float(end_time))
                
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                entries = []
                for row in cursor.fetchall():
                    try:
                        entries.append(FaceLogEntry(
                            id=row['id'],
                            timestamp=float(row['timestamp']),
                            camera_id=row['camera_id'],
                            camera_name=row['camera_name'],
                            face_name=row['face_name'],
                            age=row['age'],
                            gender=row['gender'],
                            confidence=float(row['confidence']),
                            screenshot_path=row['screenshot_path'],
                            user_id=row['user_id']
                        ))
                    except Exception as e:
                        logger.error(f"Error converting row {dict(row)}: {e}")
                        continue
                        
                return entries
                
        except Exception as e:
            logger.error(f"Error retrieving face logs: {e}")
            return []

    # ============ KNOWN FACES ============
    
    def add_known_face(self, name: str, lastname: str, age: int, cedula: str,
                      birth_date: str, crime: str, case_number: str,
                      embedding: bytes, image_path: str, 
                      created_by: Optional[int] = None) -> bool:
        """Add a known face to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO known_faces (name, lastname, age, cedula, birth_date, 
                                            crime, case_number, embedding, image_path, 
                                            created_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, lastname, age, cedula, birth_date, crime, case_number,
                      embedding, image_path, time.time(), created_by))
                conn.commit()
                
                if created_by:
                    self.log_audit(created_by, 'add_face', 
                                 f"Added face: {name} {lastname} - Cedula: {cedula}")
                
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Face with cedula '{cedula}' already exists")
            return False
        except Exception as e:
            logger.error(f"Error adding known face: {e}")
            return False

    def get_known_faces(self) -> List[dict]:
        """Retrieve all known faces from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, lastname, age, cedula, birth_date, crime, 
                           case_number, embedding, image_path 
                    FROM known_faces
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error retrieving known faces: {e}")
            return []

    def delete_known_face(self, cedula: str, deleted_by: Optional[int] = None) -> bool:
        """Delete a known face from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM known_faces WHERE cedula = ?
                ''', (cedula,))
                conn.commit()
                
                if deleted_by and cursor.rowcount > 0:
                    self.log_audit(deleted_by, 'delete_face', f"Deleted face: {cedula}")
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting known face: {e}")
            return False