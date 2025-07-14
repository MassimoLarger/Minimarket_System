// Configuración de mensajes de error personalizados
const VALIDATION_MESSAGES = {
    valueMissing: 'Este campo es obligatorio.',
    typeMismatch: 'Por favor, ingrese un valor válido.',
    patternMismatch: 'El formato ingresado no es válido.',
    tooLong: 'El texto es demasiado largo.',
    tooShort: 'El texto es demasiado corto.',
    rangeUnderflow: 'El valor debe ser mayor o igual a {min}.',
    rangeOverflow: 'El valor debe ser menor o igual a {max}.',
    stepMismatch: 'El valor no es válido.',
    badInput: 'Por favor, ingrese un valor válido.'
};

// Mensajes de error para restricciones unique
const UNIQUE_ERROR_MESSAGES = {
    'nombre_minimercado': 'Ya existe un minimercado con este nombre.',
    'nombre_proveedor': 'Ya existe un proveedor con este nombre.',
    'rut': 'Ya existe un proveedor con este RUT.',
    'nombre': 'Ya existe un registro con este nombre.',
    'codigo_barras': 'Ya existe un producto con este código de barras.',
    'code_lote': 'Ya existe un lote con este código.',
    'nombre_reporte': 'Ya existe un reporte con este nombre.',
    // Mensajes específicos por modelo
    'categoria_nombre': 'Ya existe una categoría con este nombre.',
    'producto_nombre': 'Ya existe un producto con este nombre.',
    'seccionbodega_nombre': 'Ya existe una sección de bodega con este nombre.',
    'ofertaproducto_nombre': 'Ya existe una oferta de producto con este nombre.',
    'ofertavencimiento_nombre': 'Ya existe una oferta de vencimiento con este nombre.',
    'alert_nombre': 'Ya existe una alerta con este nombre.'
};

// Mensajes específicos por tipo de campo
const FIELD_SPECIFIC_MESSAGES = {
    email: {
        typeMismatch: 'Por favor, ingrese un email válido.',
        valueMissing: 'El email es obligatorio.'
    },
    password: {
        valueMissing: 'La contraseña es obligatoria.',
        tooShort: 'La contraseña debe tener al menos {minlength} caracteres.'
    },
    number: {
        valueMissing: 'Este campo numérico es obligatorio.',
        rangeUnderflow: 'El valor debe ser mayor o igual a {min}.',
        rangeOverflow: 'El valor debe ser menor o igual a {max}.',
        badInput: 'Por favor, ingrese solo números.'
    },
    text: {
        valueMissing: 'Este campo es obligatorio.',
        patternMismatch: 'El formato ingresado no es válido.'
    },
    date: {
        valueMissing: 'La fecha es obligatoria.',
        typeMismatch: 'Por favor, seleccione una fecha válida.'
    }
};

/**
 * Obtiene el mensaje de error personalizado para un campo
 */
function getCustomErrorMessage(input) {
    const validity = input.validity;
    const inputType = input.type;
    const fieldMessages = FIELD_SPECIFIC_MESSAGES[inputType] || {};
    
    // Verificar cada tipo de error de validación
    for (const errorType in validity) {
        if (validity[errorType]) {
            let message = fieldMessages[errorType] || VALIDATION_MESSAGES[errorType];
            
            if (message) {
                // Reemplazar placeholders con valores reales
                message = message.replace('{min}', input.min || '0');
                message = message.replace('{max}', input.max || '100');
                message = message.replace('{minlength}', input.minLength || '1');
                message = message.replace('{maxlength}', input.maxLength || '255');
                
                return message;
            }
        }
    }
    
    return 'Por favor, corrija este campo.';
}

/**
 * Detecta si un error es de unique constraint
 */
function isUniqueConstraintError(errorMessage) {
    return errorMessage && (
        errorMessage.includes('UNIQUE constraint failed') ||
        errorMessage.includes('duplicate key value') ||
        errorMessage.includes('already exists') ||
        errorMessage.toLowerCase().includes('unique')
    );
}

/**
 * Obtiene el mensaje personalizado para errores de unique constraint
 */
function getUniqueErrorMessage(errorMessage, fieldName) {
    // Intentar obtener el nombre del campo del mensaje de error
    let field = fieldName;
    
    if (!field && errorMessage) {
        // Extraer el nombre del campo del mensaje de error de Django
        const match = errorMessage.match(/Tienda_\w+\.(\w+)/);
        if (match) {
            field = match[1];
        }
    }
    
    // Buscar mensaje específico
    if (field && UNIQUE_ERROR_MESSAGES[field]) {
        return UNIQUE_ERROR_MESSAGES[field];
    }
    
    // Mensaje genérico para unique constraint
    return 'Este valor ya existe. Por favor, ingrese un valor diferente.';
}

/**
 * Muestra un mensaje de error usando SweetAlert2
 */
function showValidationError(message, input, isUniqueError = false) {
    let title = 'Error de Validación';
    let finalMessage = message;
    
    // Si es un error de unique constraint, personalizar el mensaje
    if (isUniqueError || isUniqueConstraintError(message)) {
        title = 'Valor Duplicado';
        const fieldName = input ? (input.name || input.id) : null;
        finalMessage = getUniqueErrorMessage(message, fieldName);
    }
    
    Swal.fire({
        icon: 'error',
        title: title,
        text: finalMessage,
        confirmButtonText: 'Entendido',
        confirmButtonColor: '#e74c3c',
        allowOutsideClick: false,
        allowEscapeKey: false
    }).then(() => {
        // Enfocar el campo con error después de cerrar el modal
        if (input && input.focus) {
            input.focus();
        }
    });
}

/**
 * Muestra errores de unique constraint específicamente
 */
function showUniqueConstraintError(fieldName, input) {
    const message = UNIQUE_ERROR_MESSAGES[fieldName] || 'Este nombre ya existe. Por favor, ingrese un nombre diferente.';
    showValidationError(message, input, true);
}

/**
 * Valida caracteres especiales en campos de texto
 */
function validateSpecialCharacters(input) {
    // Solo validar campos de tipo text y textarea, excluyendo explícitamente campos numéricos y otros tipos especiales
    const isTextInput = (input.type === 'text' || input.tagName.toLowerCase() === 'textarea') && 
                       input.type !== 'email' && input.type !== 'password' && 
                       input.type !== 'number' && input.type !== 'date' && 
                       input.type !== 'time' && input.type !== 'url' &&
                       input.type !== 'tel' && input.type !== 'search';
    
    // Excluir explícitamente campos numéricos por nombre/id para mayor seguridad
    const isNumericField = input.name && (
        input.name.includes('stock') || 
        input.name.includes('precio') || 
        input.name.includes('costo') || 
        input.name.includes('cantidad') || 
        input.name.includes('dias') || 
        input.name.includes('umbral') ||
        input.name.includes('anticipacion')
    ) || input.id && (
        input.id.includes('stock') || 
        input.id.includes('precio') || 
        input.id.includes('costo') || 
        input.id.includes('cantidad') || 
        input.id.includes('dias') || 
        input.id.includes('umbral') ||
        input.id.includes('anticipacion')
    );
    
    if (isTextInput && !isNumericField && input.value.trim() !== '') {
        // Verificar si es un campo de dirección
        const isAddressField = input.name === 'direccion' || input.id === 'direccion' || 
                              input.name.toLowerCase().includes('direccion') || 
                              input.id.toLowerCase().includes('direccion') ||
                              input.name.toLowerCase().includes('address') || 
                              input.id.toLowerCase().includes('address');
        
        let allowedPattern;
        let errorMessage;
        
        if (isAddressField) {
            // Para campos de dirección: permitir letras, números, espacios, guiones (-), guiones bajos (_), ampersands (&), comas (,) y numerales (#)
            allowedPattern = /^[a-zA-Z0-9\s\-_&,#áéíóúÁÉÍÓÚñÑüÜ]*$/;
            errorMessage = 'En las direcciones solo se permiten letras, números, espacios y los caracteres especiales: - _ & , #';
        } else {
            // Para otros campos de texto: solo letras, números, espacios, guiones (-), guiones bajos (_) y ampersands (&)
            allowedPattern = /^[a-zA-Z0-9\s\-_&áéíóúÁÉÍÓÚñÑüÜ]*$/;
            errorMessage = 'Solo se permiten letras, números, espacios y los caracteres especiales: - _ &';
        }
        
        if (!allowedPattern.test(input.value)) {
            showValidationError(errorMessage, input);
            return false;
        }
    }
    
    return true;
}

/**
 * Valida un campo individual
 */
function validateField(input) {
    // Primero validar caracteres especiales
    if (!validateSpecialCharacters(input)) {
        return false;
    }
    
    // Luego validar con las reglas HTML5 estándar
    if (!input.checkValidity()) {
        const errorMessage = getCustomErrorMessage(input);
        showValidationError(errorMessage, input);
        return false;
    }
    return true;
}

/**
 * Valida todos los campos de un formulario
 */
function validateForm(form) {
    const inputs = form.querySelectorAll('input, textarea, select');
    
    // Verificar si es un formulario de alertas
    const isAlertForm = form.id === 'formCrearAlerta' || form.id === 'formEditarAlerta';
    
    for (let input of inputs) {
        // Para formularios de alertas, solo validar campos visibles
        // Para otros formularios, validar todos los campos como antes
        let shouldValidate = true;
        
        if (isAlertForm) {
            const isVisible = input.offsetParent !== null && 
                             getComputedStyle(input).display !== 'none' && 
                             getComputedStyle(input).visibility !== 'hidden';
            shouldValidate = isVisible;
        }
        
        if (shouldValidate && (input.hasAttribute('required') || input.hasAttribute('min') || input.hasAttribute('max') || 
            input.hasAttribute('pattern') || input.type === 'email' || input.type === 'number' || 
            input.type === 'date' || input.type === 'text' || input.tagName.toLowerCase() === 'textarea')) {
            if (!validateField(input)) {
                return false;
            }
        }
    }
    return true;
}

/**
 * Inicializa el sistema de validación personalizado
 */
function initCustomValidation() {
    // Deshabilitar validación HTML5 nativa en todos los formularios
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.setAttribute('novalidate', 'true');
        
        // Interceptar el evento submit solo si no se está cerrando el modal
        form.addEventListener('submit', function(e) {
            // Verificar si se está cerrando el modal
            if (form.dataset.closing === 'true') {
                return; // Permitir el cierre sin validación
            }
            
            if (!validateForm(this)) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }
        });
    });
    
    // Agregar event listeners para botones de cancelar y cerrar
    addModalCloseListeners();
    
    // Solo limpiar estilos de error al escribir, sin validación en tiempo real
    const inputs = document.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        // Solo limpiar estilos de error al escribir, sin validación
        input.addEventListener('input', function() {
            this.classList.remove('is-invalid', 'is-valid');
        });
    });
}

/**
 * Función para validar formularios específicos desde JavaScript
 */
function validateSpecificForm(formId) {
    const form = document.getElementById(formId);
    if (!form) {
        console.warn(`Formulario con ID '${formId}' no encontrado`);
        return false;
    }
    
    // Verificar si se está cerrando el modal
    if (form.dataset.closing === 'true') {
        return false; // No validar si se está cerrando
    }
    
    // Verificar si es una acción POST
    const method = form.method ? form.method.toLowerCase() : 'get';
    if (method !== 'post') {
        // Si no es POST, simplemente cerrar el formulario/modal
        closeFormOrModal(form);
        return false;
    }
    
    return validateForm(form);
}

/**
 * Función para validar un campo específico desde JavaScript
 */
function validateSpecificField(fieldId) {
    const field = document.getElementById(fieldId);
    if (field) {
        return validateField(field);
    }
    return false;
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Esperar un poco para asegurar que SweetAlert2 esté cargado
    setTimeout(initCustomValidation, 100);
    
    // Re-ejecutar listeners cuando se muestren modales (para elementos dinámicos)
    document.addEventListener('shown.bs.modal', function() {
        setTimeout(addModalCloseListeners, 50);
    });
});

// Función para re-inicializar listeners (útil para contenido dinámico)
function reinitializeValidation() {
    addModalCloseListeners();
}

/**
 * Agrega event listeners para botones de cancelar y cerrar modales
 */
function addModalCloseListeners() {
    // Buscar todos los botones de cancelar y cerrar
    const closeButtons = document.querySelectorAll('[data-bs-dismiss="modal"], .btn-close, .modal .btn-secondary');
    
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Encontrar el formulario dentro del modal
            const modal = this.closest('.modal');
            if (modal) {
                const form = modal.querySelector('form');
                if (form) {
                    // Marcar el formulario como "cerrando" para evitar validación
                    form.dataset.closing = 'true';
                    
                    // Limpiar el flag después de un breve delay
                    setTimeout(() => {
                        form.dataset.closing = 'false';
                        // Resetear el formulario al cerrar
                        form.reset();
                        // Limpiar clases de validación
                        const inputs = form.querySelectorAll('input, select, textarea');
                        inputs.forEach(input => {
                            input.classList.remove('is-valid', 'is-invalid');
                        });
                    }, 100);
                }
            }
        });
    });
    
    // También agregar listener para el evento de cierre del modal
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('hidden.bs.modal', function() {
            const form = this.querySelector('form');
            if (form) {
                form.dataset.closing = 'false';
                // Resetear el formulario al cerrar
                form.reset();
                // Limpiar clases de validación
                const inputs = form.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    input.classList.remove('is-valid', 'is-invalid');
                });
            }
        });
    });
}

/**
 * Función auxiliar para cerrar formularios o modales
 */
function closeFormOrModal(form) {
    // Marcar como cerrando para evitar validación
    form.dataset.closing = 'true';
    
    // Buscar si el formulario está dentro de un modal
    const modal = form.closest('.modal');
    if (modal) {
        // Si está en un modal de Bootstrap
        const modalInstance = bootstrap.Modal.getInstance(modal);
        if (modalInstance) {
            modalInstance.hide();
        } else {
            // Fallback para cerrar modal
            modal.style.display = 'none';
            document.body.classList.remove('modal-open');
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) backdrop.remove();
        }
    } else {
        // Si no está en un modal, ocultar el formulario
        form.style.display = 'none';
    }
    
    // Limpiar el flag después de cerrar
    setTimeout(() => {
        form.dataset.closing = 'false';
    }, 100);
}

// Exponer funciones globalmente
window.validateSpecificForm = validateSpecificForm;
window.validateSpecificField = validateSpecificField;
window.validateSpecialCharacters = validateSpecialCharacters;
window.showValidationError = showValidationError;
window.showUniqueConstraintError = showUniqueConstraintError;
window.isUniqueConstraintError = isUniqueConstraintError;
window.getUniqueErrorMessage = getUniqueErrorMessage;
window.closeFormOrModal = closeFormOrModal;
window.reinitializeValidation = reinitializeValidation;
window.addModalCloseListeners = addModalCloseListeners;