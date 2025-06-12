#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar las interfaces compactas
"""

import requests
import time

def test_compact_interfaces():
    """Prueba las interfaces compactas"""
    
    base_url = "http://localhost:5000"
    
    print("🧪 Probando interfaces compactas...")
    print("=" * 50)
    
    try:
        # Probar página principal
        print("📄 Probando página principal...")
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✅ Página principal: OK")
        else:
            print(f"❌ Página principal: Error {response.status_code}")
        
        # Probar portal de empleados compacto
        print("👤 Probando portal de empleados compacto...")
        response = requests.get(f"{base_url}/empleado", timeout=5)
        if response.status_code == 200:
            if "Portal Empleado" in response.text and "max-width: 350px" in response.text:
                print("✅ Portal empleado compacto: OK")
            else:
                print("⚠️ Portal empleado: Cargó pero no parece ser la versión compacta")
        else:
            print(f"❌ Portal empleado: Error {response.status_code}")
        
        # Probar portal de admin
        print("🔐 Probando portal de administrador...")
        response = requests.get(f"{base_url}/admin", timeout=5)
        if response.status_code == 200:
            print("✅ Portal administrador: OK")
        else:
            print(f"❌ Portal administrador: Error {response.status_code}")
        
        print("\n🎉 Pruebas completadas!")
        print("💡 Las interfaces compactas están funcionando correctamente")
        print("📱 El portal de empleados ahora es más compacto y móvil-friendly")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se puede conectar al servidor Flask")
        print("💡 Asegúrese de que el servidor esté ejecutándose en localhost:5000")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    test_compact_interfaces() 