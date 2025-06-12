import requests
import json
import time
import sqlite3
from datetime import date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:5000"

class SystemTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, success, message=""):
        """Registra el resultado de una prueba"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} - {test_name}"
        if message:
            result += f": {message}"
        
        print(result)
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message
        })
        
    def test_server_connection(self):
        """Prueba 1: Verificar que el servidor esté corriendo"""
        try:
            response = self.session.get(f"{BASE_URL}/")
            self.log_test("Conexión al servidor", response.status_code == 200)
            return response.status_code == 200
        except Exception as e:
            self.log_test("Conexión al servidor", False, str(e))
            return False
    
    def test_database_structure(self):
        """Prueba 2: Verificar estructura de la base de datos"""
        try:
            conn = sqlite3.connect('asistencia.db')
            cursor = conn.cursor()
            
            # Verificar tablas principales
            tables = ['empleados', 'asistencia', 'administradores', 'ubicaciones_autorizadas']
            for table in tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                exists = cursor.fetchone() is not None
                self.log_test(f"Tabla {table}", exists)
            
            # Verificar columnas críticas
            cursor.execute("PRAGMA table_info(empleados)")
            columns = [col[1] for col in cursor.fetchall()]
            pin_exists = 'pin_acceso' in columns
            self.log_test("Columna pin_acceso en empleados", pin_exists)
            
            conn.close()
            return True
            
        except Exception as e:
            self.log_test("Estructura de base de datos", False, str(e))
            return False
    
    def test_admin_login(self):
        """Prueba 3: Login de administrador"""
        try:
            # Probar login correcto
            login_data = {
                'usuario': 'admin',
                'password': 'admin123'
            }
            
            response = self.session.post(
                f"{BASE_URL}/admin/login",
                json=login_data,
                headers={'Content-Type': 'application/json'}
            )
            
            success = response.status_code == 200
            if success:
                data = response.json()
                success = data.get('success', False)
            
            self.log_test("Login de administrador", success)
            
            # Probar login incorrecto
            wrong_data = {
                'usuario': 'admin',
                'password': 'wrong'
            }
            
            response = self.session.post(
                f"{BASE_URL}/admin/login",
                json=wrong_data,
                headers={'Content-Type': 'application/json'}
            )
            
            wrong_rejected = response.status_code != 200 or not response.json().get('success', True)
            self.log_test("Rechazo de credenciales incorrectas", wrong_rejected)
            
            return success
            
        except Exception as e:
            self.log_test("Login de administrador", False, str(e))
            return False
    
    def test_employee_creation(self):
        """Prueba 4: Creación de empleados"""
        try:
            # Primero hacer login
            if not self.test_admin_login():
                return False
            
            # Crear empleado de prueba
            employee_data = {
                'nombre': 'Juan',
                'apellido': 'Pérez',
                'cedula': '12345678',
                'cargo': 'Desarrollador',
                'departamento': 'IT',
                'email': 'juan.perez@test.com',
                'telefono': '555-1234'
            }
            
            response = self.session.post(
                f"{BASE_URL}/api/empleados",
                json=employee_data,
                headers={'Content-Type': 'application/json'}
            )
            
            success = response.status_code == 200
            pin = None
            
            if success:
                data = response.json()
                success = data.get('success', False)
                pin = data.get('pin')
                
            self.log_test("Creación de empleado", success, f"PIN: {pin}" if pin else "")
            
            # Probar duplicado (debe fallar)
            response2 = self.session.post(
                f"{BASE_URL}/api/empleados",
                json=employee_data,
                headers={'Content-Type': 'application/json'}
            )
            
            duplicate_rejected = response2.status_code != 200 or not response2.json().get('success', True)
            self.log_test("Rechazo de empleado duplicado", duplicate_rejected)
            
            return success and pin
            
        except Exception as e:
            self.log_test("Creación de empleado", False, str(e))
            return False
    
    def test_employee_verification(self):
        """Prueba 5: Verificación de PIN de empleado"""
        try:
            # Obtener un PIN de la base de datos
            conn = sqlite3.connect('asistencia.db')
            cursor = conn.cursor()
            cursor.execute("SELECT pin_acceso FROM empleados WHERE activo = TRUE LIMIT 1")
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                self.log_test("Verificación de PIN", False, "No hay empleados para probar")
                return False
            
            pin = result[0]
            
            # Probar PIN correcto
            response = self.session.post(
                f"{BASE_URL}/empleado/verificar",
                json={'pin': pin},
                headers={'Content-Type': 'application/json'}
            )
            
            success = response.status_code == 200
            if success:
                data = response.json()
                success = data.get('success', False)
            
            self.log_test("Verificación de PIN correcto", success)
            
            # Probar PIN incorrecto
            response2 = self.session.post(
                f"{BASE_URL}/empleado/verificar",
                json={'pin': '0000'},
                headers={'Content-Type': 'application/json'}
            )
            
            wrong_rejected = response2.status_code != 200 or not response2.json().get('success', True)
            self.log_test("Rechazo de PIN incorrecto", wrong_rejected)
            
            return success
            
        except Exception as e:
            self.log_test("Verificación de PIN", False, str(e))
            return False
    
    def test_location_apis(self):
        """Prueba 6: APIs de ubicaciones"""
        try:
            # Obtener ubicaciones
            response = self.session.get(f"{BASE_URL}/api/ubicaciones")
            success = response.status_code == 200
            
            locations_count = 0
            if success:
                data = response.json()
                locations_count = len(data) if isinstance(data, list) else 0
            
            self.log_test("Obtener ubicaciones", success, f"{locations_count} ubicaciones")
            
            # Verificar ubicación (usando coordenadas de Miami)
            verify_data = {
                'latitud': 25.7617,
                'longitud': -80.1918
            }
            
            response2 = self.session.post(
                f"{BASE_URL}/api/verificar_ubicacion",
                json=verify_data,
                headers={'Content-Type': 'application/json'}
            )
            
            location_verified = response2.status_code == 200
            if location_verified:
                data = response2.json()
                location_verified = data.get('success', False)
            
            self.log_test("Verificación de ubicación", location_verified)
            
            return success
            
        except Exception as e:
            self.log_test("APIs de ubicaciones", False, str(e))
            return False
    
    def test_attendance_apis(self):
        """Prueba 7: APIs de asistencia"""
        try:
            # Obtener asistencia de hoy
            response = self.session.get(f"{BASE_URL}/api/asistencia/hoy")
            success = response.status_code == 200
            
            records_count = 0
            if success:
                data = response.json()
                records_count = len(data) if isinstance(data, list) else 0
            
            self.log_test("Obtener asistencia de hoy", success, f"{records_count} registros")
            
            return success
            
        except Exception as e:
            self.log_test("APIs de asistencia", False, str(e))
            return False
    
    def test_page_loads(self):
        """Prueba 8: Carga de páginas principales"""
        pages = [
            ('/', 'Página principal'),
            ('/admin/login', 'Login de administrador'),
            ('/empleado', 'Portal de empleado')
        ]
        
        all_success = True
        
        for url, name in pages:
            try:
                response = self.session.get(f"{BASE_URL}{url}")
                success = response.status_code == 200
                self.log_test(f"Carga de {name}", success)
                all_success = all_success and success
            except Exception as e:
                self.log_test(f"Carga de {name}", False, str(e))
                all_success = False
        
        return all_success
    
    def run_all_tests(self):
        """Ejecutar todas las pruebas"""
        print("🧪 INICIANDO PRUEBAS DEL SISTEMA")
        print("=" * 50)
        
        start_time = time.time()
        
        # Ejecutar pruebas en orden
        tests = [
            self.test_server_connection,
            self.test_database_structure,
            self.test_page_loads,
            self.test_admin_login,
            self.test_employee_creation,
            self.test_employee_verification,
            self.test_location_apis,
            self.test_attendance_apis
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"❌ Error en prueba: {e}")
            
            time.sleep(0.5)  # Pausa entre pruebas
        
        # Resumen
        end_time = time.time()
        duration = end_time - start_time
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print("\n" + "=" * 50)
        print("📊 RESUMEN DE PRUEBAS")
        print("=" * 50)
        print(f"⏱️  Tiempo total: {duration:.2f} segundos")
        print(f"✅ Pruebas exitosas: {passed}/{total}")
        print(f"❌ Pruebas fallidas: {total - passed}/{total}")
        print(f"📈 Porcentaje de éxito: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n🎉 ¡TODAS LAS PRUEBAS PASARON! El sistema está funcionando correctamente.")
        else:
            print(f"\n⚠️  {total - passed} pruebas fallaron. Revisar los errores arriba.")
            
        return passed == total

def main():
    """Función principal"""
    print("🚀 VERIFICADOR DE FUNCIONALIDAD DEL SISTEMA")
    print("Sistema de Control de Asistencia")
    print("=" * 50)
    
    tester = SystemTester()
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == '__main__':
    exit(main()) 