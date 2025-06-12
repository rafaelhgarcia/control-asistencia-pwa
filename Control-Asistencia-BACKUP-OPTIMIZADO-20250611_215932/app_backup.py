from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import json
import os
import base64
from datetime import datetime, date
import sqlite3
import hashlib
import secrets
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Configuración de la aplicación
DATABASE = 'data/asistencia.db'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Crear directorio de uploads si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    """Inicializa la base de datos con las tablas necesarias"""
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Tabla de administradores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS administradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre TEXT NOT NULL,
            email TEXT,
            activo BOOLEAN DEFAULT TRUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de empleados actualizada
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            cedula TEXT UNIQUE NOT NULL,
            cargo TEXT,
            departamento TEXT,
            email TEXT,
            telefono TEXT,
            foto_perfil TEXT,
            pin_acceso TEXT,
            activo BOOLEAN DEFAULT TRUE,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de ubicaciones autorizadas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ubicaciones_autorizadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            latitud REAL NOT NULL,
            longitud REAL NOT NULL,
            radio_metros INTEGER DEFAULT 50,
            activa BOOLEAN DEFAULT TRUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de registros de asistencia actualizada
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asistencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER,
            fecha DATE,
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
            estado TEXT DEFAULT 'presente',
            observaciones TEXT,
            FOREIGN KEY (empleado_id) REFERENCES empleados (id)
        )
    ''')
    
    # Insertar administrador por defecto
    cursor.execute('SELECT COUNT(*) FROM administradores')
    if cursor.fetchone()[0] == 0:
        admin_password = hash_password('admin123')
        cursor.execute('''
            INSERT INTO administradores (usuario, password_hash, nombre, email)
            VALUES (?, ?, ?, ?)
        ''', ('admin', admin_password, 'Administrador', 'admin@empresa.com'))
    
    # Insertar ubicación por defecto
    cursor.execute('SELECT COUNT(*) FROM ubicaciones_autorizadas')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO ubicaciones_autorizadas (nombre, descripcion, latitud, longitud, radio_metros)
            VALUES (?, ?, ?, ?, ?)
        ''', ('Oficina Principal', 'Ubicación principal de la empresa', 0.0, 0.0, 100))
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Obtiene una conexión a la base de datos"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """Genera hash de contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verifica contraseña"""
    return hash_password(password) == password_hash

def login_required(f):
    """Decorador para rutas que requieren autenticación"""
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calcula distancia entre dos puntos GPS en metros"""
    from math import radians, cos, sin, asin, sqrt
    
    # Convertir a radianes
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Fórmula haversine
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radio de la Tierra en metros
    r = 6371000
    return c * r

def allowed_file(filename):
    """Verifica si el archivo es una imagen permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Rutas principales
@app.route('/')
def index():
    """Página de selección de perfil"""
    return render_template('select_profile.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    """Login de administrador"""
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']
        
        conn = get_db_connection()
        admin = conn.execute(
            'SELECT * FROM administradores WHERE usuario = ? AND activo = TRUE',
            (usuario,)
        ).fetchone()
        conn.close()
        
        if admin and verify_password(password, admin['password_hash']):
            session['admin_logged_in'] = True
            session['admin_id'] = admin['id']
            session['admin_name'] = admin['nombre']
            flash('Bienvenido al panel de administración', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def logout():
    """Logout de administrador"""
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Dashboard del administrador"""
    return render_template('admin_dashboard.html')

@app.route('/admin/empleados')
@login_required
def admin_empleados():
    """Gestión de empleados para administrador"""
    conn = get_db_connection()
    empleados = conn.execute('SELECT * FROM empleados WHERE activo = TRUE ORDER BY apellido, nombre').fetchall()
    conn.close()
    return render_template('admin_empleados.html', empleados=empleados)

@app.route('/admin/ubicaciones')
@login_required
def admin_ubicaciones():
    """Gestión de ubicaciones autorizadas"""
    conn = get_db_connection()
    ubicaciones = conn.execute('SELECT * FROM ubicaciones_autorizadas ORDER BY nombre').fetchall()
    conn.close()
    return render_template('admin_ubicaciones.html', ubicaciones=ubicaciones)

@app.route('/admin/reportes')
@login_required
def admin_reportes():
    """Reportes para administrador"""
    return render_template('admin_reportes.html')

@app.route('/empleado')
def empleado_portal():
    """Portal de empleado"""
    return render_template('empleado_portal.html')

@app.route('/empleado/verificar', methods=['POST'])
def verificar_empleado():
    """Verificar empleado por PIN"""
    data = request.json
    pin = data.get('pin')
    
    conn = get_db_connection()
    empleado = conn.execute(
        'SELECT * FROM empleados WHERE pin_acceso = ? AND activo = TRUE',
        (pin,)
    ).fetchone()
    conn.close()
    
    if empleado:
        return jsonify({
            'success': True,
            'empleado': dict(empleado)
        })
    else:
        return jsonify({
            'success': False,
            'message': 'PIN incorrecto o empleado no encontrado'
        }), 400

@app.route('/empleado/registro')
def empleado_registro():
    """Página de registro de asistencia para empleado"""
    return render_template('empleado_registro.html')

# APIs para empleados
@app.route('/api/empleados', methods=['GET'])
def api_get_empleados():
    """API para obtener todos los empleados"""
    conn = get_db_connection()
    empleados = conn.execute('SELECT * FROM empleados WHERE activo = TRUE ORDER BY apellido, nombre').fetchall()
    conn.close()
    return jsonify([dict(emp) for emp in empleados])

@app.route('/api/empleados', methods=['POST'])
@login_required
def api_add_empleado():
    """API para agregar un nuevo empleado"""
    data = request.json
    
    # Generar PIN de 4 dígitos único
    import random
    conn = get_db_connection()
    while True:
        pin = str(random.randint(1000, 9999))
        existing = conn.execute('SELECT id FROM empleados WHERE pin_acceso = ?', (pin,)).fetchone()
        if not existing:
            break
    
    try:
        conn.execute('''
            INSERT INTO empleados (nombre, apellido, cedula, cargo, departamento, email, telefono, pin_acceso)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['nombre'], data['apellido'], data['cedula'], data['cargo'], 
              data['departamento'], data.get('email', ''), data.get('telefono', ''), pin))
        conn.commit()
        conn.close()
        return jsonify({
            'success': True, 
            'message': f'Empleado agregado exitosamente. PIN de acceso: {pin}',
            'pin': pin
        })
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Ya existe un empleado con esa cédula'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ubicaciones', methods=['GET'])
def api_get_ubicaciones():
    """API para obtener ubicaciones autorizadas"""
    conn = get_db_connection()
    ubicaciones = conn.execute('SELECT * FROM ubicaciones_autorizadas WHERE activa = TRUE').fetchall()
    conn.close()
    return jsonify([dict(ub) for ub in ubicaciones])

@app.route('/api/ubicaciones', methods=['POST'])
@login_required
def api_add_ubicacion():
    """API para agregar ubicación autorizada"""
    data = request.json
    
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO ubicaciones_autorizadas (nombre, descripcion, latitud, longitud, radio_metros)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['nombre'], data['descripcion'], data['latitud'], data['longitud'], data['radio_metros']))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Ubicación agregada exitosamente'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/verificar_ubicacion', methods=['POST'])
def api_verificar_ubicacion():
    """API para verificar si el empleado está en ubicación autorizada"""
    data = request.json
    lat = data['latitud']
    lon = data['longitud']
    
    conn = get_db_connection()
    ubicaciones = conn.execute('SELECT * FROM ubicaciones_autorizadas WHERE activa = TRUE').fetchall()
    conn.close()
    
    for ubicacion in ubicaciones:
        distancia = calculate_distance(lat, lon, ubicacion['latitud'], ubicacion['longitud'])
        if distancia <= ubicacion['radio_metros']:
            return jsonify({
                'success': True,
                'ubicacion': dict(ubicacion),
                'distancia': round(distancia, 2)
            })
    
    return jsonify({
        'success': False,
        'message': 'No está en una ubicación autorizada'
    }), 400

@app.route('/api/asistencia_empleado', methods=['POST'])
def api_registrar_asistencia_empleado():
    """API para registrar asistencia de empleado con foto y GPS"""
    data = request.json
    empleado_id = data['empleado_id']
    tipo = data['tipo']  # 'entrada' o 'salida'
    latitud = data['latitud']
    longitud = data['longitud']
    foto_base64 = data['foto']
    ubicacion = data['ubicacion']
    
    fecha_actual = date.today()
    hora_actual = datetime.now().time()
    
    # Guardar foto
    foto_filename = None
    if foto_base64:
        try:
            # Decodificar base64
            foto_data = base64.b64decode(foto_base64.split(',')[1])
            foto_filename = f"{empleado_id}_{tipo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            foto_path = os.path.join(UPLOAD_FOLDER, foto_filename)
            
            with open(foto_path, 'wb') as f:
                f.write(foto_data)
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error al guardar foto: {str(e)}'}), 500
    
    conn = get_db_connection()
    
    # Verificar si ya existe un registro para este empleado hoy
    registro_existente = conn.execute('''
        SELECT * FROM asistencia WHERE empleado_id = ? AND fecha = ?
    ''', (empleado_id, fecha_actual)).fetchone()
    
    try:
        if registro_existente:
            if tipo == 'entrada':
                if registro_existente['hora_entrada']:
                    return jsonify({'success': False, 'message': 'Ya se registró la entrada para hoy'}), 400
                
                conn.execute('''
                    UPDATE asistencia SET 
                    hora_entrada = ?, latitud_entrada = ?, longitud_entrada = ?, 
                    foto_entrada = ?, ubicacion_entrada = ?
                    WHERE empleado_id = ? AND fecha = ?
                ''', (hora_actual, latitud, longitud, foto_filename, ubicacion, empleado_id, fecha_actual))
            else:  # salida
                if registro_existente['hora_salida']:
                    return jsonify({'success': False, 'message': 'Ya se registró la salida para hoy'}), 400
                
                conn.execute('''
                    UPDATE asistencia SET 
                    hora_salida = ?, latitud_salida = ?, longitud_salida = ?, 
                    foto_salida = ?, ubicacion_salida = ?
                    WHERE empleado_id = ? AND fecha = ?
                ''', (hora_actual, latitud, longitud, foto_filename, ubicacion, empleado_id, fecha_actual))
        else:
            # Crear nuevo registro
            if tipo == 'entrada':
                conn.execute('''
                    INSERT INTO asistencia (
                        empleado_id, fecha, hora_entrada, latitud_entrada, 
                        longitud_entrada, foto_entrada, ubicacion_entrada
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (empleado_id, fecha_actual, hora_actual, latitud, longitud, foto_filename, ubicacion))
            else:
                conn.execute('''
                    INSERT INTO asistencia (
                        empleado_id, fecha, hora_salida, latitud_salida, 
                        longitud_salida, foto_salida, ubicacion_salida
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (empleado_id, fecha_actual, hora_actual, latitud, longitud, foto_filename, ubicacion))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'{tipo.capitalize()} registrada exitosamente',
            'hora': hora_actual.strftime('%H:%M:%S'),
            'ubicacion': ubicacion
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/asistencia/hoy')
def api_asistencia_hoy():
    """API para obtener la asistencia del día actual"""
    fecha_actual = date.today()
    
    conn = get_db_connection()
    registros = conn.execute('''
        SELECT a.*, e.nombre, e.apellido, e.cedula, e.cargo
        FROM asistencia a
        JOIN empleados e ON a.empleado_id = e.id
        WHERE a.fecha = ?
        ORDER BY e.apellido, e.nombre
    ''', (fecha_actual,)).fetchall()
    conn.close()
    
    return jsonify([dict(reg) for reg in registros])

@app.route('/api/reportes/asistencia')
@login_required
def api_reporte_asistencia():
    """API para generar reportes de asistencia"""
    fecha_inicio = request.args.get('fecha_inicio', date.today().strftime('%Y-%m-%d'))
    fecha_fin = request.args.get('fecha_fin', date.today().strftime('%Y-%m-%d'))
    
    conn = get_db_connection()
    registros = conn.execute('''
        SELECT a.*, e.nombre, e.apellido, e.cedula, e.cargo, e.departamento
        FROM asistencia a
        JOIN empleados e ON a.empleado_id = e.id
        WHERE a.fecha BETWEEN ? AND ?
        ORDER BY a.fecha DESC, e.apellido, e.nombre
    ''', (fecha_inicio, fecha_fin)).fetchall()
    conn.close()
    
    return jsonify([dict(reg) for reg in registros])

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000) 