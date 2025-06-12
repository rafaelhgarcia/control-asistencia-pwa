#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de pruebas completas para el Sistema de Control de Asistencia
Verifica todos los componentes del sistema incluyendo servidor, base de datos, 
autenticación, APIs y funcionalidades completas.
"""

import requests
import sqlite3
import json
import time
import os
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:5000"
DB_PATH = "asistencia.db"

class ColorOutput:
    """Clase para colorear la salida de la consola"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_header(text):
    """Imprime un encabezado colorido"""
    print(f"\n{ColorOutput.CYAN}{ColorOutput.BOLD}{'='*60}{ColorOutput.END}")
    print(f"{ColorOutput.CYAN}{ColorOutput.BOLD}{text.center(60)}{ColorOutput.END}")
    print(f"{ColorOutput.CYAN}{ColorOutput.BOLD}{'='*60}{ColorOutput.END}")

def print_test(test_name, status, details=""):
    """Imprime el resultado de una prueba"""
    if status:
        status_text = f"{ColorOutput.GREEN}✓ PASSED{ColorOutput.END}"
    else:
        status_text = f"{ColorOutput.RED}✗ FAILED{ColorOutput.END}"
    
    print(f"{ColorOutput.WHITE}{test_name:<40}{ColorOutput.END} {status_text}")
    if details:
        print(f"{ColorOutput.YELLOW}   → {details}{ColorOutput.END}")

def print_info(text):
    """Imprime información general"""
    print(f"{ColorOutput.BLUE}ℹ {text}{ColorOutput.END}")

def print_warning(text):
    """Imprime una advertencia"""
    print(f"{ColorOutput.YELLOW}⚠ {text}{ColorOutput.END}")

def print_error(text):
    """Imprime un error"""
    print(f"{ColorOutput.RED}✗ {text}{ColorOutput.END}")

def print_success(text):
    """Imprime un éxito"""
    print(f"{ColorOutput.GREEN}✓ {text}{ColorOutput.END}")

class SystemTester:
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_tests = 0
        self.session = requests.Session()
        
    def test_server_connection(self):
        """Prueba 1: Conexión al servidor Flask"""
        self.total_tests += 1
        try:
            response = self.session.get(f"{BASE_URL}/", timeout=5)
            if response.status_code == 200:
                print_test("Conexión al servidor Flask", True, f"Status: {response.status_code}")
                self.passed_tests += 1
                return True
            else:
                print_test("Conexión al servidor Flask", False, f"Status: {response.status_code}")
                self.failed_tests += 1
                return False
        except Exception as e:
            print_test("Conexión al servidor Flask", False, f"Error: {str(e)}")
            self.failed_tests += 1
            return False

    def test_database_structure(self):
        """Prueba 2: Estructura de la base de datos"""
        self.total_tests += 1
        try:
            if not os.path.exists(DB_PATH):
                print_test("Estructura de base de datos", False, "Base de datos no existe")
                self.failed_tests += 1
                return False
                
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Verificar tablas principales
            tables = ['empleados', 'asistencias', 'administradores', 'ubicaciones_autorizadas']
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            missing_tables = [table for table in tables if table not in existing_tables]
            
            if missing_tables:
                print_test("Estructura de base de datos", False, f"Faltan tablas: {', '.join(missing_tables)}")
                self.failed_tests += 1
                conn.close()
                return False
            
            # Verificar columnas críticas en empleados
            cursor.execute("PRAGMA table_info(empleados)")
            columns = [column[1] for column in cursor.fetchall()]
            required_columns = ['id', 'nombre', 'apellido', 'email', 'pin_acceso']
            
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                print_test("Estructura de base de datos", False, f"Faltan columnas: {', '.join(missing_columns)}")
                self.failed_tests += 1
                conn.close()
                return False
                
            conn.close()
            print_test("Estructura de base de datos", True, f"Tablas: {len(existing_tables)}, Columnas verificadas")
            self.passed_tests += 1
            return True
            
        except Exception as e:
            print_test("Estructura de base de datos", False, f"Error: {str(e)}")
            self.failed_tests += 1
            return False

    def test_admin_authentication(self):
        """Prueba 3: Autenticación de administrador"""
        self.total_tests += 1
        try:
            # Intentar login de admin
            response = self.session.post(f"{BASE_URL}/api/admin_login", 
                                       json={"username": "admin", "password": "admin123"})
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print_test("Autenticación administrador", True, "Login exitoso")
                    self.passed_tests += 1
                    return True
                else:
                    print_test("Autenticación administrador", False, data.get('message', 'Login falló'))
                    self.failed_tests += 1
                    return False
            else:
                print_test("Autenticación administrador", False, f"HTTP {response.status_code}")
                self.failed_tests += 1
                return False
                
        except Exception as e:
            print_test("Autenticación administrador", False, f"Error: {str(e)}")
            self.failed_tests += 1
            return False

    def test_employee_creation(self):
        """Prueba 4: Creación de empleado de prueba"""
        self.total_tests += 1
        try:
            employee_data = {
                "nombre": "Juan Carlos",
                "apellido": "Prueba Test",
                "email": "juan.prueba@test.com",
                "telefono": "123456789",
                "cargo": "Empleado de Prueba"
            }
            
            response = self.session.post(f"{BASE_URL}/api/empleados", json=employee_data)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print_test("Creación de empleado", True, f"ID: {data.get('empleado_id')}, PIN: {data.get('pin')}")
                    self.passed_tests += 1
                    # Guardar datos para pruebas posteriores
                    self.test_employee = {
                        'id': data.get('empleado_id'),
                        'pin': data.get('pin'),
                        'nombre': employee_data['nombre'],
                        'apellido': employee_data['apellido']
                    }
                    return True
                else:
                    print_test("Creación de empleado", False, data.get('message', 'Error desconocido'))
                    self.failed_tests += 1
                    return False
            else:
                print_test("Creación de empleado", False, f"HTTP {response.status_code}")
                self.failed_tests += 1
                return False
                
        except Exception as e:
            print_test("Creación de empleado", False, f"Error: {str(e)}")
            self.failed_tests += 1
            return False

    def test_employee_pin_verification(self):
        """Prueba 5: Verificación de PIN de empleado"""
        self.total_tests += 1
        try:
            if not hasattr(self, 'test_employee'):
                print_test("Verificación PIN empleado", False, "No hay empleado de prueba")
                self.failed_tests += 1
                return False
                
            response = self.session.post(f"{BASE_URL}/api/verificar_pin", 
                                       json={"pin": self.test_employee['pin']})
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print_test("Verificación PIN empleado", True, f"PIN {self.test_employee['pin']} verificado")
                    self.passed_tests += 1
                    return True
                else:
                    print_test("Verificación PIN empleado", False, data.get('message', 'PIN inválido'))
                    self.failed_tests += 1
                    return False
            else:
                print_test("Verificación PIN empleado", False, f"HTTP {response.status_code}")
                self.failed_tests += 1
                return False
                
        except Exception as e:
            print_test("Verificación PIN empleado", False, f"Error: {str(e)}")
            self.failed_tests += 1
            return False

    def test_location_verification(self):
        """Prueba 6: Verificación de ubicación GPS"""
        self.total_tests += 1
        try:
            # Coordenadas de prueba (Madrid, España como ejemplo)
            test_location = {
                "latitud": 40.4168,
                "longitud": -3.7038
            }
            
            response = self.session.post(f"{BASE_URL}/api/verificar_ubicacion", json=test_location)
            
            if response.status_code == 200:
                data = response.json()
                # La ubicación puede no estar autorizada, pero la API debe responder
                print_test("Verificación ubicación GPS", True, data.get('message', 'API responde correctamente'))
                self.passed_tests += 1
                return True
            else:
                print_test("Verificación ubicación GPS", False, f"HTTP {response.status_code}")
                self.failed_tests += 1
                return False
                
        except Exception as e:
            print_test("Verificación ubicación GPS", False, f"Error: {str(e)}")
            self.failed_tests += 1
            return False

    def test_attendance_registration(self):
        """Prueba 7: Registro de asistencia"""
        self.total_tests += 1
        try:
            if not hasattr(self, 'test_employee'):
                print_test("Registro de asistencia", False, "No hay empleado de prueba")
                self.failed_tests += 1
                return False
                
            attendance_data = {
                "empleado_id": self.test_employee['id'],
                "tipo": "entrada",
                "latitud": 40.4168,
                "longitud": -3.7038,
                "foto": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDABQODxIPDRQSEBIXFRQYHjIhHhwcHj0sLiQySUBMS0dARkVQWnNiUFVtVkVGZIhlbXd7gYKBTmCNl4x9lnN+gXz/2wBDARUXFx4aHjshITt8U0ZTfHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHz/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k="
            }
            
            response = self.session.post(f"{BASE_URL}/api/asistencia_empleado", json=attendance_data)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print_test("Registro de asistencia", True, f"Entrada registrada: {data.get('hora')}")
                    self.passed_tests += 1
                    return True
                else:
                    print_test("Registro de asistencia", False, data.get('message', 'Error en registro'))
                    self.failed_tests += 1
                    return False
            else:
                print_test("Registro de asistencia", False, f"HTTP {response.status_code}")
                self.failed_tests += 1
                return False
                
        except Exception as e:
            print_test("Registro de asistencia", False, f"Error: {str(e)}")
            self.failed_tests += 1
            return False

    def test_page_loading(self):
        """Prueba 8: Carga de páginas principales"""
        self.total_tests += 1
        try:
            pages = [
                ("/", "Página principal"),
                ("/empleado", "Portal empleado"),
                ("/admin", "Portal administrador")
            ]
            
            all_passed = True
            details = []
            
            for url, name in pages:
                try:
                    response = self.session.get(f"{BASE_URL}{url}", timeout=5)
                    if response.status_code == 200:
                        details.append(f"{name}: ✓")
                    else:
                        details.append(f"{name}: ✗ ({response.status_code})")
                        all_passed = False
                except Exception as e:
                    details.append(f"{name}: ✗ (Error)")
                    all_passed = False
            
            if all_passed:
                print_test("Carga de páginas principales", True, " | ".join(details))
                self.passed_tests += 1
                return True
            else:
                print_test("Carga de páginas principales", False, " | ".join(details))
                self.failed_tests += 1
                return False
                
        except Exception as e:
            print_test("Carga de páginas principales", False, f"Error: {str(e)}")
            self.failed_tests += 1
            return False

    def test_api_endpoints(self):
        """Prueba 9: Endpoints de API"""
        self.total_tests += 1
        try:
            # Lista de empleados
            response = self.session.get(f"{BASE_URL}/api/empleados")
            
            if response.status_code == 200:
                data = response.json()
                employee_count = len(data.get('empleados', []))
                print_test("Endpoints de API", True, f"Lista empleados: {employee_count} registros")
                self.passed_tests += 1
                return True
            else:
                print_test("Endpoints de API", False, f"HTTP {response.status_code}")
                self.failed_tests += 1
                return False
                
        except Exception as e:
            print_test("Endpoints de API", False, f"Error: {str(e)}")
            self.failed_tests += 1
            return False

    def test_data_integrity(self):
        """Prueba 10: Integridad de datos"""
        self.total_tests += 1
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Contar registros en tablas principales
            cursor.execute("SELECT COUNT(*) FROM empleados")
            empleados_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM asistencias")
            asistencias_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM administradores")
            admin_count = cursor.fetchone()[0]
            
            conn.close()
            
            if empleados_count >= 0 and admin_count >= 1:
                details = f"Empleados: {empleados_count}, Asistencias: {asistencias_count}, Admins: {admin_count}"
                print_test("Integridad de datos", True, details)
                self.passed_tests += 1
                return True
            else:
                print_test("Integridad de datos", False, "Datos incompletos")
                self.failed_tests += 1
                return False
                
        except Exception as e:
            print_test("Integridad de datos", False, f"Error: {str(e)}")
            self.failed_tests += 1
            return False

    def cleanup_test_data(self):
        """Limpia los datos de prueba creados"""
        try:
            if hasattr(self, 'test_employee'):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                # Eliminar asistencias del empleado de prueba
                cursor.execute("DELETE FROM asistencias WHERE empleado_id = ?", (self.test_employee['id'],))
                
                # Eliminar empleado de prueba
                cursor.execute("DELETE FROM empleados WHERE id = ?", (self.test_employee['id'],))
                
                conn.commit()
                conn.close()
                
                print_info(f"Datos de prueba eliminados (Empleado ID: {self.test_employee['id']})")
        except Exception as e:
            print_warning(f"Error limpiando datos de prueba: {str(e)}")

    def run_all_tests(self):
        """Ejecuta todas las pruebas"""
        print_header("SISTEMA DE CONTROL DE ASISTENCIA - PRUEBAS COMPLETAS")
        print_info(f"Iniciando pruebas del sistema - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info(f"URL Base: {BASE_URL}")
        print_info(f"Base de Datos: {DB_PATH}")
        
        print_header("EJECUTANDO PRUEBAS")
        
        # Ejecutar pruebas en orden
        tests = [
            self.test_server_connection,
            self.test_database_structure,
            self.test_admin_authentication,
            self.test_employee_creation,
            self.test_employee_pin_verification,
            self.test_location_verification,
            self.test_attendance_registration,
            self.test_page_loading,
            self.test_api_endpoints,
            self.test_data_integrity
        ]
        
        for test_func in tests:
            try:
                test_func()
                time.sleep(0.5)  # Pausa entre pruebas
            except Exception as e:
                print_error(f"Error ejecutando {test_func.__name__}: {str(e)}")
                self.failed_tests += 1
                self.total_tests += 1
        
        # Limpiar datos de prueba
        self.cleanup_test_data()
        
        # Mostrar resultados finales
        self.show_final_results()

    def show_final_results(self):
        """Muestra los resultados finales"""
        print_header("RESULTADOS FINALES")
        
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        
        print(f"{ColorOutput.WHITE}Total de Pruebas:{ColorOutput.END} {ColorOutput.BOLD}{self.total_tests}{ColorOutput.END}")
        print(f"{ColorOutput.GREEN}Pruebas Exitosas:{ColorOutput.END} {ColorOutput.BOLD}{self.passed_tests}{ColorOutput.END}")
        print(f"{ColorOutput.RED}Pruebas Fallidas:{ColorOutput.END} {ColorOutput.BOLD}{self.failed_tests}{ColorOutput.END}")
        print(f"{ColorOutput.BLUE}Tasa de Éxito:{ColorOutput.END} {ColorOutput.BOLD}{success_rate:.1f}%{ColorOutput.END}")
        
        if success_rate >= 90:
            print_success("🎉 SISTEMA FUNCIONANDO CORRECTAMENTE")
            print_info("El sistema está listo para producción")
        elif success_rate >= 70:
            print_warning("⚠️ SISTEMA FUNCIONANDO CON ADVERTENCIAS")
            print_info("El sistema tiene algunos problemas menores")
        else:
            print_error("❌ SISTEMA CON PROBLEMAS CRÍTICOS")
            print_info("Se requieren correcciones antes de usar")
        
        print_header("FIN DE PRUEBAS")

def main():
    """Función principal"""
    try:
        print_info("Iniciando pruebas del Sistema de Control de Asistencia...")
        print_info("Verificando servidor Flask...")
        
        # Esperar un momento para que el servidor se inicie
        time.sleep(2)
        
        tester = SystemTester()
        tester.run_all_tests()
        
    except KeyboardInterrupt:
        print_warning("\nPruebas interrumpidas por el usuario")
    except Exception as e:
        print_error(f"Error general en las pruebas: {str(e)}")

if __name__ == "__main__":
    main() 