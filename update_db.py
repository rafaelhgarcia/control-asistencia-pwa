import sqlite3

def update_database():
    """Actualiza la estructura de la base de datos para agregar columnas faltantes"""
    conn = sqlite3.connect('asistencia.db')
    cursor = conn.cursor()
    
    try:
        print("Verificando estructura de la base de datos...")
        
        # Verificar si existe la columna pin_acceso en empleados
        cursor.execute("PRAGMA table_info(empleados)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"Columnas actuales en empleados: {columns}")
        
        # Agregar columna pin_acceso si no existe
        if 'pin_acceso' not in columns:
            print("Agregando columna pin_acceso...")
            cursor.execute('ALTER TABLE empleados ADD COLUMN pin_acceso TEXT')
            print("✅ Columna pin_acceso agregada")
        else:
            print("✅ Columna pin_acceso ya existe")
        
        # Verificar estructura de la tabla asistencia
        cursor.execute("PRAGMA table_info(asistencia)")
        asistencia_columns = [column[1] for column in cursor.fetchall()]
        print(f"Columnas actuales en asistencia: {asistencia_columns}")
        
        # Agregar columnas faltantes en asistencia
        new_columns = [
            ('latitud_entrada', 'REAL'),
            ('longitud_entrada', 'REAL'),
            ('latitud_salida', 'REAL'),
            ('longitud_salida', 'REAL'),
            ('foto_entrada', 'TEXT'),
            ('foto_salida', 'TEXT'),
            ('ubicacion_entrada', 'TEXT'),
            ('ubicacion_salida', 'TEXT')
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in asistencia_columns:
                print(f"Agregando columna {col_name}...")
                cursor.execute(f'ALTER TABLE asistencia ADD COLUMN {col_name} {col_type}')
                print(f"✅ Columna {col_name} agregada")
            else:
                print(f"✅ Columna {col_name} ya existe")
        
        # Verificar si existe la tabla ubicaciones_autorizadas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ubicaciones_autorizadas'")
        if not cursor.fetchone():
            print("Creando tabla ubicaciones_autorizadas...")
            cursor.execute('''
                CREATE TABLE ubicaciones_autorizadas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    descripcion TEXT,
                    latitud REAL NOT NULL,
                    longitud REAL NOT NULL,
                    radio_metros INTEGER NOT NULL DEFAULT 50,
                    activa BOOLEAN DEFAULT TRUE,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ Tabla ubicaciones_autorizadas creada")
        else:
            print("✅ Tabla ubicaciones_autorizadas ya existe")
        
        # Verificar si existe la tabla administradores
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='administradores'")
        if not cursor.fetchone():
            print("Creando tabla administradores...")
            cursor.execute('''
                CREATE TABLE administradores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insertar administrador por defecto
            from werkzeug.security import generate_password_hash
            password_hash = generate_password_hash('admin123')
            cursor.execute('INSERT INTO administradores (usuario, password_hash) VALUES (?, ?)', 
                          ('admin', password_hash))
            print("✅ Tabla administradores creada con usuario admin/admin123")
        else:
            print("✅ Tabla administradores ya existe")
        
        conn.commit()
        print("\n🎉 Base de datos actualizada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error actualizando base de datos: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    update_database() 