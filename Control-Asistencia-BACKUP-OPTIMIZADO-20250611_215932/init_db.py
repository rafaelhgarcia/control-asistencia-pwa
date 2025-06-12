import sqlite3
import os
from werkzeug.security import generate_password_hash

def init_database():
    """Inicializa la base de datos completa desde cero"""
    
    # Eliminar base de datos existente si hay problemas
    if os.path.exists('asistencia.db'):
        print("Eliminando base de datos existente...")
        os.remove('asistencia.db')
    
    print("Creando nueva base de datos...")
    conn = sqlite3.connect('asistencia.db')
    cursor = conn.cursor()
    
    try:
        # Crear tabla empleados
        print("Creando tabla empleados...")
        cursor.execute('''
            CREATE TABLE empleados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                apellido TEXT NOT NULL,
                cedula TEXT UNIQUE NOT NULL,
                cargo TEXT,
                departamento TEXT,
                email TEXT,
                telefono TEXT,
                pin_acceso TEXT UNIQUE NOT NULL,
                activo BOOLEAN DEFAULT TRUE,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ Tabla empleados creada")
        
        # Crear tabla asistencia
        print("Creando tabla asistencia...")
        cursor.execute('''
            CREATE TABLE asistencia (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empleado_id INTEGER NOT NULL,
                fecha DATE NOT NULL,
                hora_entrada TIME,
                hora_salida TIME,
                latitud_entrada REAL,
                longitud_entrada REAL,
                latitud_salida REAL,
                longitud_salida REAL,
                foto_entrada TEXT,
                foto_salida TEXT,
                ubicacion_entrada TEXT,
                ubicacion_salida TEXT,
                FOREIGN KEY (empleado_id) REFERENCES empleados (id)
            )
        ''')
        print("✅ Tabla asistencia creada")
        
        # Crear tabla administradores
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
        password_hash = generate_password_hash('admin123')
        cursor.execute('INSERT INTO administradores (usuario, password_hash) VALUES (?, ?)', 
                      ('admin', password_hash))
        print("✅ Tabla administradores creada con usuario admin/admin123")
        
        # Crear tabla ubicaciones_autorizadas
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
        
        # Insertar una ubicación de ejemplo
        cursor.execute('''
            INSERT INTO ubicaciones_autorizadas (nombre, descripcion, latitud, longitud, radio_metros)
            VALUES (?, ?, ?, ?, ?)
        ''', ('Oficina Principal', 'Ubicación principal de trabajo', 25.7617, -80.1918, 100))
        print("✅ Ubicación de ejemplo agregada")
        
        conn.commit()
        print("\n🎉 Base de datos inicializada exitosamente!")
        print("👤 Usuario admin: admin")
        print("🔑 Contraseña admin: admin123")
        
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    init_database() 