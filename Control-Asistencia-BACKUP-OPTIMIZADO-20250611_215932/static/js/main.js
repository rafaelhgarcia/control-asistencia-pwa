// JavaScript principal para la aplicación de Control de Asistencia

// Configuración global
const CONFIG = {
    API_BASE_URL: '/api',
    REFRESH_INTERVAL: 30000, // 30 segundos
    NOTIFICATION_TIMEOUT: 5000 // 5 segundos
};

// Utilidades globales
const Utils = {
    // Formatear fecha para mostrar
    formatDate: function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('es-ES', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    },

    // Formatear hora para mostrar
    formatTime: function(timeString) {
        if (!timeString) return 'No registrada';
        return timeString;
    },

    // Mostrar notificación
    showNotification: function(type, message, duration = CONFIG.NOTIFICATION_TIMEOUT) {
        // Crear elemento de notificación
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            max-width: 500px;
        `;
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Agregar al DOM
        document.body.appendChild(notification);

        // Remover automáticamente después del tiempo especificado
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);

        return notification;
    },

    // Mostrar loading
    showLoading: function(element) {
        element.classList.add('loading');
        element.style.pointerEvents = 'none';
    },

    // Ocultar loading
    hideLoading: function(element) {
        element.classList.remove('loading');
        element.style.pointerEvents = 'auto';
    },

    // Confirmar acción
    confirm: function(message, callback) {
        if (window.confirm(message)) {
            callback();
        }
    },

    // Validar email
    isValidEmail: function(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    // Validar cédula (básico)
    isValidCedula: function(cedula) {
        return cedula && cedula.length >= 7 && cedula.length <= 10;
    },

    // Debounce function
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Obtener fecha actual en formato YYYY-MM-DD
    getCurrentDate: function() {
        return new Date().toISOString().split('T')[0];
    },

    // Obtener hora actual en formato HH:MM:SS
    getCurrentTime: function() {
        return new Date().toLocaleTimeString('es-ES');
    }
};

// Clase para manejar las APIs
class ApiClient {
    constructor(baseUrl = CONFIG.API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    // Métodos específicos para empleados
    async getEmpleados() {
        return this.request('/empleados');
    }

    async addEmpleado(empleado) {
        return this.request('/empleados', {
            method: 'POST',
            body: JSON.stringify(empleado)
        });
    }

    async deleteEmpleado(id) {
        return this.request(`/empleados/${id}`, {
            method: 'DELETE'
        });
    }

    // Métodos específicos para asistencia
    async getAsistenciaHoy() {
        return this.request('/asistencia/hoy');
    }

    async registrarAsistencia(datos) {
        return this.request('/asistencia', {
            method: 'POST',
            body: JSON.stringify(datos)
        });
    }

    // Métodos específicos para reportes
    async getReporteAsistencia(fechaInicio, fechaFin, empleadoId = null) {
        const params = new URLSearchParams({
            fecha_inicio: fechaInicio,
            fecha_fin: fechaFin
        });
        
        if (empleadoId) {
            params.append('empleado_id', empleadoId);
        }

        return this.request(`/reportes/asistencia?${params}`);
    }
}

// Instancia global del cliente API
const api = new ApiClient();

// Clase para manejar el estado global de la aplicación
class AppState {
    constructor() {
        this.empleados = [];
        this.asistenciaHoy = [];
        this.loading = false;
        this.listeners = {};
    }

    // Agregar listener para cambios de estado
    on(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
    }

    // Emitir evento
    emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(callback => callback(data));
        }
    }

    // Cargar empleados
    async loadEmpleados() {
        try {
            this.loading = true;
            this.empleados = await api.getEmpleados();
            this.emit('empleadosLoaded', this.empleados);
        } catch (error) {
            console.error('Error loading empleados:', error);
            Utils.showNotification('danger', 'Error al cargar empleados');
        } finally {
            this.loading = false;
        }
    }

    // Cargar asistencia de hoy
    async loadAsistenciaHoy() {
        try {
            this.asistenciaHoy = await api.getAsistenciaHoy();
            this.emit('asistenciaLoaded', this.asistenciaHoy);
        } catch (error) {
            console.error('Error loading asistencia:', error);
            Utils.showNotification('danger', 'Error al cargar asistencia');
        }
    }

    // Actualizar datos
    async refresh() {
        await Promise.all([
            this.loadEmpleados(),
            this.loadAsistenciaHoy()
        ]);
    }
}

// Instancia global del estado de la aplicación
const appState = new AppState();

// Clase para manejar notificaciones en tiempo real
class NotificationManager {
    constructor() {
        this.notifications = [];
    }

    show(type, message, options = {}) {
        const notification = {
            id: Date.now(),
            type,
            message,
            timestamp: new Date(),
            ...options
        };

        this.notifications.push(notification);
        return Utils.showNotification(type, message, options.duration);
    }

    success(message, options = {}) {
        return this.show('success', message, options);
    }

    error(message, options = {}) {
        return this.show('danger', message, options);
    }

    warning(message, options = {}) {
        return this.show('warning', message, options);
    }

    info(message, options = {}) {
        return this.show('info', message, options);
    }
}

// Instancia global del gestor de notificaciones
const notifications = new NotificationManager();

// Funciones de inicialización
function initializeApp() {
    // Configurar navegación activa
    setActiveNavigation();
    
    // Configurar tooltips de Bootstrap si están disponibles
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Configurar auto-refresh si está habilitado
    if (shouldAutoRefresh()) {
        setInterval(() => {
            appState.refresh();
        }, CONFIG.REFRESH_INTERVAL);
    }

    // Manejar errores globales
    window.addEventListener('error', function(e) {
        console.error('Global error:', e.error);
        notifications.error('Ha ocurrido un error inesperado');
    });

    // Manejar promesas rechazadas
    window.addEventListener('unhandledrejection', function(e) {
        console.error('Unhandled promise rejection:', e.reason);
        notifications.error('Error en la aplicación');
    });
}

// Configurar navegación activa
function setActiveNavigation() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPath || (currentPath === '/' && href === '/')) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// Determinar si debe auto-refrescar
function shouldAutoRefresh() {
    const currentPath = window.location.pathname;
    return currentPath === '/' || currentPath === '/registro';
}

// Funciones utilitarias para formularios
function validateForm(formId, rules) {
    const form = document.getElementById(formId);
    const elements = form.elements;
    let isValid = true;
    const errors = [];

    for (const [fieldName, fieldRules] of Object.entries(rules)) {
        const field = elements[fieldName];
        if (!field) continue;

        const value = field.value.trim();

        // Validar requerido
        if (fieldRules.required && !value) {
            isValid = false;
            errors.push(`${fieldRules.label || fieldName} es requerido`);
            field.classList.add('is-invalid');
        } else {
            field.classList.remove('is-invalid');
        }

        // Validar longitud mínima
        if (fieldRules.minLength && value.length < fieldRules.minLength) {
            isValid = false;
            errors.push(`${fieldRules.label || fieldName} debe tener al menos ${fieldRules.minLength} caracteres`);
            field.classList.add('is-invalid');
        }

        // Validar email
        if (fieldRules.email && value && !Utils.isValidEmail(value)) {
            isValid = false;
            errors.push(`${fieldRules.label || fieldName} debe ser un email válido`);
            field.classList.add('is-invalid');
        }

        // Validar cédula
        if (fieldRules.cedula && value && !Utils.isValidCedula(value)) {
            isValid = false;
            errors.push(`${fieldRules.label || fieldName} debe ser una cédula válida`);
            field.classList.add('is-invalid');
        }
    }

    return { isValid, errors };
}

// Función para limpiar formulario
function clearForm(formId) {
    const form = document.getElementById(formId);
    form.reset();
    
    // Remover clases de validación
    const inputs = form.querySelectorAll('.form-control, .form-select');
    inputs.forEach(input => {
        input.classList.remove('is-valid', 'is-invalid');
    });
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Exportar para uso global
window.Utils = Utils;
window.api = api;
window.appState = appState;
window.notifications = notifications;
window.validateForm = validateForm;
window.clearForm = clearForm; 