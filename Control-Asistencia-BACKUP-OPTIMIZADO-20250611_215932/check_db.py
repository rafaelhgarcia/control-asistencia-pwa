#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar y corregir la estructura de la base de datos
"""

import sqlite3
import os

def check_and_fix_database():
    """Verifica y corrige la estructura de la base de datos"""
    
    db_path = "asistencia.db"
    
    if not os.path.exists(db_path):
        print("❌ Base de datos no existe")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar tablas existentes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"✅ Tablas existentes: {', '.join(tables)}")
        
        # Si existe 'asistencia' pero no 'asistencias', crear un alias/vista
        if 'asistencia' in tables and 'asistencias' not in tables:
            print("🔧 Creando tabla 'asistencias' como alias de 'asistencia'...")
            
            # Crear tabla asistencias con la misma estructura
            cursor.execute("""
                CREATE TABLE asistencias AS 
                SELECT * FROM asistencia WHERE 1=0
            """)
            
            # Copiar datos existentes
            cursor.execute("""
                INSERT INTO asistencias 
                SELECT * FROM asistencia
            """)
            
            conn.commit()
            print("✅ Tabla 'asistencias' creada exitosamente")
        
        # Verificar estructura de empleados
        cursor.execute("PRAGMA table_info(empleados)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"✅ Columnas en empleados: {', '.join(columns)}")
        
        # Verificar si hay administradores
        cursor.execute("SELECT COUNT(*) FROM administradores")
        admin_count = cursor.fetchone()[0]
        print(f"✅ Administradores registrados: {admin_count}")
        
        # Verificar empleados
        cursor.execute("SELECT COUNT(*) FROM empleados")
        emp_count = cursor.fetchone()[0]
        print(f"✅ Empleados registrados: {emp_count}")
        
        # Verificar asistencias
        if 'asistencias' in tables or 'asistencia' in tables:
            table_name = 'asistencias' if 'asistencias' in tables else 'asistencia'
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            asist_count = cursor.fetchone()[0]
            print(f"✅ Registros de asistencia: {asist_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verificando base de datos: {str(e)}")
        return False

def main():
    print("=== VERIFICACIÓN DE BASE DE DATOS ===")
    if check_and_fix_database():
        print("✅ Base de datos verificada y corregida exitosamente")
    else:
        print("❌ Error en la verificación de la base de datos")

if __name__ == "__main__":
    main() 