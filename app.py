from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import os
import base64
import random
from datetime import date, datetime, time
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import math
import logging

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_super_segura_2024'
app.config['UPLOAD_FOLDER'] = 'static/fotos'

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear directorio de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def init_db():
    """Inicializa la base de datos con todas las tablas necesarias"""
    try:
        conn = sqlite3.connect('asistencia.db')
        cursor = conn.cursor()
        
        # Tabla empleados
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
                pin_acceso TEXT UNIQUE NOT NULL,
                activo BOOLEAN DEFAULT TRUE,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla asistencia
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS asistencia (
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
        
        # Tabla administradores
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS administradores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla ubicaciones autorizadas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ubicaciones_autorizadas (
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
        
        # Verificar si existe el administrador por defecto
        admin_exists = cursor.execute('SELECT COUNT(*) FROM administradores WHERE usuario = ?', ('admin',)).fetchone()[0]
        if admin_exists == 0:
            password_hash = generate_password_hash('admin123')
            cursor.execute('INSERT INTO administradores (usuario, password_hash) VALUES (?, ?)', 
                          ('admin', password_hash))
            logger.info("Administrador por defecto creado: admin/admin123")
        
        # Verificar si existe una ubicación por defecto
        ubicacion_exists = cursor.execute('SELECT COUNT(*) FROM ubicaciones_autorizadas').fetchone()[0]
        if ubicacion_exists == 0:
            cursor.execute('''
                INSERT INTO ubicaciones_autorizadas (nombre, descripcion, latitud, longitud, radio_metros)
                VALUES (?, ?, ?, ?, ?)
            ''', ('Oficina Principal', 'Ubicación principal de trabajo', 25.7617, -80.1918, 100))
            logger.info("Ubicación por defecto creada")
        
        conn.commit()
        logger.info("Base de datos inicializada correctamente")
        
    except Exception as e:
        logger.error(f"Error inicializando base de datos: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def get_db_connection():
    """Obtiene una conexión a la base de datos con configuración optimizada"""
    try:
        conn = sqlite3.connect('asistencia.db', timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        raise

def validate_session():
    """Valida que existe una sesión activa"""
    return 'admin_id' in session

def login_required(f):
    """Decorador para requerir login de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not validate_session():
            return jsonify({'success': False, 'message': 'No autorizado'}), 401
        return f(*args, **kwargs)
    return decorated_function

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calcula la distancia entre dos puntos GPS usando la fórmula Haversine"""
    try:
        R = 6371000  # Radio de la Tierra en metros
        lat1_rad = math.radians(float(lat1))
        lon1_rad = math.radians(float(lon1))
        lat2_rad = math.radians(float(lat2))
        lon2_rad = math.radians(float(lon2))
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    except Exception as e:
        logger.error(f"Error calculando distancia: {e}")
        return float('inf')

def generate_unique_pin():
    """Genera un PIN único de 4 dígitos"""
    try:
        conn = get_db_connection()
        for _ in range(100):  # Máximo 100 intentos
            pin = str(random.randint(1000, 9999))
            existing = conn.execute('SELECT id FROM empleados WHERE pin_acceso = ?', (pin,)).fetchone()
            if not existing:
                conn.close()
                return pin
        conn.close()
        raise Exception("No se pudo generar un PIN único")
    except Exception as e:
        logger.error(f"Error generando PIN: {e}")
        raise

def validate_employee_data(data):
    """Valida los datos del empleado"""
    required_fields = ['nombre', 'apellido', 'cedula']
    errors = []
    
    for field in required_fields:
        if not data.get(field) or not data[field].strip():
            errors.append(f'El campo {field} es obligatorio')
    
    if data.get('email') and '@' not in data['email']:
        errors.append('Email inválido')
    
    return errors

# RUTAS PRINCIPALES
@app.route('/')
def index():
    """Página principal con selección de perfil"""
    return render_template('select_profile.html')

@app.route('/manifest.json')
def manifest():
    """Servir manifest.json para PWA"""
    return app.send_static_file('manifest.json')

@app.route('/sw.js')
def service_worker():
    """Servir service worker para PWA"""
    return app.send_static_file('sw.js')

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    """Login de administrador"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            usuario = data.get('usuario', '').strip()
            password = data.get('password', '')
            
            if not usuario or not password:
                return jsonify({'success': False, 'message': 'Usuario y contraseña requeridos'}), 400
            
            conn = get_db_connection()
            admin = conn.execute('SELECT * FROM administradores WHERE usuario = ?', (usuario,)).fetchone()
            conn.close()
            
            if admin and check_password_hash(admin['password_hash'], password):
                session['admin_id'] = admin['id']
                session['admin_usuario'] = admin['usuario']
                logger.info(f"Login exitoso para administrador: {usuario}")
                
                if request.is_json:
                    return jsonify({'success': True, 'redirect': '/admin/dashboard'})
                return redirect(url_for('admin_dashboard'))
            else:
                logger.warning(f"Intento de login fallido para usuario: {usuario}")
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Credenciales inválidas'}), 401
                flash('Credenciales inválidas')
                
        except Exception as e:
            logger.error(f"Error en login: {e}")
            if request.is_json:
                return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500
            flash('Error interno del servidor')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def logout():
    """Cerrar sesión de administrador"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Panel de administración"""
    return render_template('admin_dashboard.html')

@app.route('/admin/empleados')
@login_required
def admin_empleados():
    """Gestión de empleados"""
    return render_template('admin_empleados.html')

@app.route('/admin/ubicaciones')
@login_required
def admin_ubicaciones():
    """Gestión de ubicaciones"""
    return render_template('admin_ubicaciones.html')

@app.route('/admin/reportes')
@login_required
def admin_reportes():
    """Reportes de asistencia"""
    return render_template('admin_reportes.html')

@app.route('/empleado')
def empleado_portal():
    """Portal de acceso para empleados"""
    return render_template('empleado_portal_compacto.html')

@app.route('/empleado/verificar', methods=['POST'])
def verificar_empleado():
    """Verificar PIN de empleado"""
    try:
        data = request.get_json()
        pin = data.get('pin', '').strip()
        
        if not pin or len(pin) != 4:
            return jsonify({'success': False, 'message': 'PIN debe tener 4 dígitos'}), 400
        
        conn = get_db_connection()
        empleado = conn.execute('''
            SELECT * FROM empleados WHERE pin_acceso = ? AND activo = TRUE
        ''', (pin,)).fetchone()
        conn.close()
        
        if empleado:
            session['empleado_id'] = empleado['id']
            session['empleado_nombre'] = f"{empleado['nombre']} {empleado['apellido']}"
            return jsonify({
                'success': True,
                'empleado': {
                    'id': empleado['id'],
                    'nombre': empleado['nombre'],
                    'apellido': empleado['apellido'],
                    'cargo': empleado['cargo']
                }
            })
        else:
            return jsonify({'success': False, 'message': 'PIN inválido o empleado inactivo'}), 401
            
    except Exception as e:
        logger.error(f"Error verificando empleado: {e}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500

@app.route('/empleado/registro')
def empleado_registro():
    """Página de registro de asistencia"""
    if 'empleado_id' not in session:
        return redirect(url_for('empleado_portal'))
    return render_template('empleado_registro_compacto.html')

# APIs OPTIMIZADAS
@app.route('/api/empleados', methods=['GET'])
def api_get_empleados():
    """API para obtener lista de empleados"""
    try:
        conn = get_db_connection()
        empleados = conn.execute('SELECT * FROM empleados ORDER BY apellido, nombre').fetchall()
        conn.close()
        return jsonify([dict(emp) for emp in empleados])
    except Exception as e:
        logger.error(f"Error obteniendo empleados: {e}")
        return jsonify({'success': False, 'message': 'Error obteniendo empleados'}), 500

@app.route('/api/empleados', methods=['POST'])
@login_required
def api_add_empleado():
    """API para agregar nuevo empleado"""
    try:
        data = request.get_json()
        
        # Validar datos
        errors = validate_employee_data(data)
        if errors:
            return jsonify({'success': False, 'message': '; '.join(errors)}), 400
        
        # Generar PIN único
        pin = generate_unique_pin()
        
        conn = get_db_connection()
        
        # Verificar que no exista la cédula
        existing = conn.execute('SELECT id FROM empleados WHERE cedula = ?', (data['cedula'],)).fetchone()
        if existing:
            conn.close()
            return jsonify({'success': False, 'message': 'Ya existe un empleado con esa cédula'}), 400
        
        # Insertar empleado
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO empleados (nombre, apellido, cedula, cargo, departamento, email, telefono, pin_acceso)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['nombre'].strip(),
            data['apellido'].strip(), 
            data['cedula'].strip(),
            data.get('cargo', '').strip(),
            data.get('departamento', '').strip(),
            data.get('email', '').strip(),
            data.get('telefono', '').strip(),
            pin
        ))
        
        empleado_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Empleado creado: {data['nombre']} {data['apellido']} (ID: {empleado_id}, PIN: {pin})")
        
        return jsonify({
            'success': True,
            'message': f'Empleado agregado exitosamente. PIN: {pin}',
            'pin': pin,
            'empleado_id': empleado_id
        })
        
    except Exception as e:
        logger.error(f"Error agregando empleado: {e}")
        return jsonify({'success': False, 'message': f'Error agregando empleado: {str(e)}'}), 500

@app.route('/api/ubicaciones', methods=['GET'])
def api_get_ubicaciones():
    """API para obtener ubicaciones autorizadas"""
    try:
        conn = get_db_connection()
        ubicaciones = conn.execute('SELECT * FROM ubicaciones_autorizadas WHERE activa = TRUE ORDER BY nombre').fetchall()
        conn.close()
        return jsonify([dict(ub) for ub in ubicaciones])
    except Exception as e:
        logger.error(f"Error obteniendo ubicaciones: {e}")
        return jsonify({'success': False, 'message': 'Error obteniendo ubicaciones'}), 500

@app.route('/api/ubicaciones', methods=['POST'])
@login_required
def api_add_ubicacion():
    """API para agregar ubicación autorizada"""
    try:
        data = request.get_json()
        
        required_fields = ['nombre', 'latitud', 'longitud', 'radio_metros']
        for field in required_fields:
            if field not in data or data[field] is None:
                return jsonify({'success': False, 'message': f'Campo {field} requerido'}), 400
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO ubicaciones_autorizadas (nombre, descripcion, latitud, longitud, radio_metros)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['nombre'].strip(),
            data.get('descripcion', '').strip(),
            float(data['latitud']),
            float(data['longitud']),
            int(data['radio_metros'])
        ))
        conn.commit()
        conn.close()
        
        logger.info(f"Ubicación creada: {data['nombre']}")
        return jsonify({'success': True, 'message': 'Ubicación agregada exitosamente'})
        
    except Exception as e:
        logger.error(f"Error agregando ubicación: {e}")
        return jsonify({'success': False, 'message': f'Error agregando ubicación: {str(e)}'}), 500

@app.route('/api/verificar_ubicacion', methods=['POST'])
def api_verificar_ubicacion():
    """API para verificar si el empleado está en ubicación autorizada"""
    try:
        data = request.get_json()
        lat = float(data['latitud'])
        lon = float(data['longitud'])
        
        conn = get_db_connection()
        ubicaciones = conn.execute('SELECT * FROM ubicaciones_autorizadas WHERE activa = TRUE').fetchall()
        conn.close()
        
        for ubicacion in ubicaciones:
            distancia = calculate_distance(lat, lon, ubicacion['latitud'], ubicacion['longitud'])
            if distancia <= ubicacion['radio_metros']:
                return jsonify({
                    'success': True,
                    'ubicacion': {
                        'id': ubicacion['id'],
                        'nombre': ubicacion['nombre'],
                        'descripcion': ubicacion['descripcion']
                    },
                    'distancia': round(distancia, 2)
                })
        
        return jsonify({
            'success': False,
            'message': 'No está en una ubicación autorizada'
        }), 400
        
    except Exception as e:
        logger.error(f"Error verificando ubicación: {e}")
        return jsonify({'success': False, 'message': 'Error verificando ubicación'}), 500

@app.route('/api/asistencia_empleado', methods=['POST'])
def api_registrar_asistencia_empleado():
    """API para registrar asistencia de empleado"""
    try:
        data = request.get_json()
        
        if 'empleado_id' not in session:
            return jsonify({'success': False, 'message': 'Sesión de empleado requerida'}), 401
        
        empleado_id = session['empleado_id']
        tipo = data['tipo']  # 'entrada' o 'salida'
        latitud = float(data['latitud'])
        longitud = float(data['longitud'])
        foto_base64 = data.get('foto', '')
        ubicacion = data.get('ubicacion', '')
        
        if tipo not in ['entrada', 'salida']:
            return jsonify({'success': False, 'message': 'Tipo inválido'}), 400
        
        fecha_actual = date.today()
        hora_actual = datetime.now().time().strftime('%H:%M:%S')
        
        # Guardar foto
        foto_filename = None
        if foto_base64:
            try:
                foto_data = base64.b64decode(foto_base64.split(',')[1])
                foto_filename = f"{empleado_id}_{tipo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                foto_path = os.path.join(app.config['UPLOAD_FOLDER'], foto_filename)
                
                with open(foto_path, 'wb') as f:
                    f.write(foto_data)
                    
                logger.info(f"Foto guardada: {foto_filename}")
            except Exception as e:
                logger.error(f"Error guardando foto: {e}")
                return jsonify({'success': False, 'message': 'Error guardando foto'}), 500
        
        conn = get_db_connection()
        
        # Verificar registro existente
        registro_existente = conn.execute('''
            SELECT * FROM asistencia WHERE empleado_id = ? AND fecha = ?
        ''', (empleado_id, fecha_actual)).fetchone()
        
        if registro_existente:
            if tipo == 'entrada':
                if registro_existente['hora_entrada']:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Ya registró entrada hoy'}), 400
                
                conn.execute('''
                    UPDATE asistencia SET 
                    hora_entrada = ?, latitud_entrada = ?, longitud_entrada = ?, 
                    foto_entrada = ?, ubicacion_entrada = ?
                    WHERE empleado_id = ? AND fecha = ?
                ''', (hora_actual, latitud, longitud, foto_filename, ubicacion, empleado_id, fecha_actual))
            else:
                if registro_existente['hora_salida']:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Ya registró salida hoy'}), 400
                
                conn.execute('''
                    UPDATE asistencia SET 
                    hora_salida = ?, latitud_salida = ?, longitud_salida = ?, 
                    foto_salida = ?, ubicacion_salida = ?
                    WHERE empleado_id = ? AND fecha = ?
                ''', (hora_actual, latitud, longitud, foto_filename, ubicacion, empleado_id, fecha_actual))
        else:
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
        
        logger.info(f"Asistencia registrada: Empleado {empleado_id}, {tipo} a las {hora_actual}")
        
        return jsonify({
            'success': True,
            'message': f'{tipo.capitalize()} registrada exitosamente',
            'hora': hora_actual,
            'ubicacion': ubicacion
        })
        
    except Exception as e:
        logger.error(f"Error registrando asistencia: {e}")
        return jsonify({'success': False, 'message': f'Error registrando asistencia: {str(e)}'}), 500

@app.route('/api/asistencia/hoy')
def api_asistencia_hoy():
    """API para obtener asistencia del día actual"""
    try:
        fecha_actual = date.today()
        
        conn = get_db_connection()
        registros = conn.execute('''
            SELECT a.*, e.nombre, e.apellido, e.cedula, e.cargo,
                   (e.nombre || ' ' || e.apellido) as empleado_nombre
            FROM asistencia a
            JOIN empleados e ON a.empleado_id = e.id
            WHERE a.fecha = ?
            ORDER BY e.apellido, e.nombre
        ''', (fecha_actual,)).fetchall()
        conn.close()
        
        return jsonify([dict(reg) for reg in registros])
        
    except Exception as e:
        logger.error(f"Error obteniendo asistencia de hoy: {e}")
        return jsonify({'success': False, 'message': 'Error obteniendo asistencia'}), 500

@app.route('/api/reportes/asistencia')
@login_required
def api_reporte_asistencia():
    """API para generar reportes de asistencia"""
    try:
        fecha_inicio = request.args.get('fecha_inicio', date.today().strftime('%Y-%m-%d'))
        fecha_fin = request.args.get('fecha_fin', date.today().strftime('%Y-%m-%d'))
        empleado_id = request.args.get('empleado_id')
        
        conn = get_db_connection()
        
        query = '''
            SELECT a.*, e.nombre, e.apellido, e.cedula, e.cargo, e.departamento,
                   (e.nombre || ' ' || e.apellido) as empleado_nombre
            FROM asistencia a
            JOIN empleados e ON a.empleado_id = e.id
            WHERE a.fecha BETWEEN ? AND ?
        '''
        params = [fecha_inicio, fecha_fin]
        
        if empleado_id:
            query += ' AND a.empleado_id = ?'
            params.append(empleado_id)
            
        query += ' ORDER BY a.fecha DESC, e.apellido, e.nombre'
        
        registros = conn.execute(query, params).fetchall()
        
        # Generar estadísticas
        total_empleados = conn.execute('SELECT COUNT(*) FROM empleados WHERE activo = TRUE').fetchone()[0]
        
        conn.close()
        
        estadisticas = {
            'total_empleados': total_empleados,
            'presentes': len([r for r in registros if r['hora_entrada']]),
            'ausentes': total_empleados - len(set(r['empleado_id'] for r in registros)),
            'tardanzas': len([r for r in registros if r['hora_entrada'] and r['hora_entrada'] > '09:00:00']),
            'promedio_horas': 8.0  # Placeholder
        }
        
        return jsonify({
            'registros': [dict(reg) for reg in registros],
            'estadisticas': estadisticas
        })
        
    except Exception as e:
        logger.error(f"Error generando reporte: {e}")
        return jsonify({'success': False, 'message': 'Error generando reporte'}), 500

# MANEJO DE ERRORES
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Error interno del servidor: {error}")
    return render_template('error.html', error="Error interno del servidor"), 500

# Inicialización
if __name__ == '__main__':
    init_db()
    logger.info("Iniciando servidor Flask...")
    app.run(debug=True, host='0.0.0.0', port=5000) 