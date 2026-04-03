/**
 * Modal editor module for manual fiber routes.
 * Manages modal lifecycle, form state, device/port selects, and single-port mode toggling.
 */

console.log('[MODAL EDITOR MODULE] Loading... autocomplete enabled');

import { fetchDevicePorts, validatePort, validateCableName, validateDeviceCoordinates } from './apiClient.js';
import { createDeviceAutocomplete } from './deviceAutocomplete.js';

// Cached DOM references
let manualModal = null;
let manualModalContent = null;
let manualForm = null;
let manualRouteNameInput = null;
let manualRouteDistanceEl = null;
let manualOriginDeviceSelect = null;  // Now an input instead of select
let manualOriginPortSelect = null;
let manualDestDeviceSelect = null;    // Now an input instead of select
let manualDestPortSelect = null;
let manualSinglePortCheckbox = null;
let manualDestNotice = null;

// Autocomplete instances
let originAutocomplete = null;
let destAutocomplete = null;

// Selected device data from autocomplete
let selectedOriginDevice = null;
let selectedDestDevice = null;

// Validation feedback elements (created dynamically)
let nameValidationFeedback = null;
let originPortValidationFeedback = null;
let destPortValidationFeedback = null;

// Editing state
let editingFiberId = null;

// Device option cache reused by frontend builder bootstrap (kept for compatibility)
let cachedDeviceOptions = [];
let modalInitialized = false;

// Validation state
let validationTimers = {};
let validationResults = {
    name: { valid: true, message: '' },
    originPort: { valid: true, message: '' },
    destPort: { valid: true, message: '' }
};

/**
 * Helper to find elements within the page container first, then globally
 */
function findElement(id) {
    const pageContainer = document.querySelector('.network-design-page');
    const element = pageContainer ? pageContainer.querySelector(`#${id}`) : null;
    return element || document.getElementById(id);
}

/**
 * Debounce utility - delays function execution until after wait time
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Create or get validation feedback element
 */
function getOrCreateFeedback(inputElement, feedbackVar) {
    let feedback = feedbackVar;
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.className = 'validation-feedback';
        feedback.style.cssText = 'color: #dc2626; font-size: 0.875rem; margin-top: 0.25rem; display: none;';
        inputElement.parentElement.appendChild(feedback);
    }
    return feedback;
}

/**
 * Show validation error on field
 */
function showFieldError(inputElement, feedbackElement, message) {
    inputElement.style.borderColor = '#dc2626';
    inputElement.style.boxShadow = '0 0 0 1px #dc2626';
    feedbackElement.textContent = message;
    feedbackElement.style.display = 'block';
}

/**
 * Clear validation error from field
 */
function clearFieldError(inputElement, feedbackElement) {
    inputElement.style.borderColor = '';
    inputElement.style.boxShadow = '';
    if (feedbackElement) {
        feedbackElement.style.display = 'none';
        feedbackElement.textContent = '';
    }
}

/**
 * Validate cable name in real-time
 */
async function validateCableNameField() {
    if (!manualRouteNameInput) return;
    
    const name = manualRouteNameInput.value.trim();
    
    // Create feedback element if needed
    nameValidationFeedback = getOrCreateFeedback(manualRouteNameInput, nameValidationFeedback);
    
    // Clear previous validation
    clearFieldError(manualRouteNameInput, nameValidationFeedback);
    
    // Validate required
    if (!name) {
        validationResults.name = { valid: false, message: 'Nome do cabo é obrigatório' };
        showFieldError(manualRouteNameInput, nameValidationFeedback, 'Nome do cabo é obrigatório');
        return;
    }

    // Validate minimum length
    if (name.length < 3) {
        validationResults.name = { valid: false, message: 'Nome deve ter pelo menos 3 caracteres' };
        showFieldError(manualRouteNameInput, nameValidationFeedback, 'Nome deve ter pelo menos 3 caracteres');
        return;
    }
    
    try {
        const result = await validateCableName(name, editingFiberId);
        
        if (!result.available) {
            validationResults.name = { valid: false, message: result.message };
            showFieldError(manualRouteNameInput, nameValidationFeedback, result.message);
        } else {
            validationResults.name = { valid: true, message: '' };
            clearFieldError(manualRouteNameInput, nameValidationFeedback);
        }
    } catch (error) {
        console.error('Error validating cable name:', error);
        // Don't block on validation errors
        validationResults.name = { valid: true, message: '' };
    }
}

/**
 * Validate port in real-time
 */
async function validatePortField(portSelectElement, feedbackElement, validationKey) {
    if (!portSelectElement) return;
    
    const portId = portSelectElement.value;
    
    // Create feedback element if needed
    const feedback = getOrCreateFeedback(portSelectElement, feedbackElement);
    if (validationKey === 'originPort') {
        originPortValidationFeedback = feedback;
    } else if (validationKey === 'destPort') {
        destPortValidationFeedback = feedback;
    }
    
    // Clear previous validation
    clearFieldError(portSelectElement, feedback);
    
    // Validate required
    if (!portId) {
        validationResults[validationKey] = { valid: false, message: 'Port selection is required' };
        return;
    }
    
    try {
        const result = await validatePort(portId, editingFiberId);
        
        if (!result.available) {
            const message = `Porta ${result.port_name} já está em uso pelo cabo "${result.cable_name}"`;
            validationResults[validationKey] = { valid: false, message };
            showFieldError(portSelectElement, feedback, message);
        } else {
            validationResults[validationKey] = { valid: true, message: '' };
            clearFieldError(portSelectElement, feedback);
        }
    } catch (error) {
        console.error('Error validating port:', error);
        // Don't block on validation errors
        validationResults[validationKey] = { valid: true, message: '' };
    }
}

// Debounced validation functions (300ms delay)
const debouncedNameValidation = debounce(validateCableNameField, 300);
const debouncedOriginPortValidation = debounce(() => {
    validatePortField(manualOriginPortSelect, originPortValidationFeedback, 'originPort');
}, 300);
const debouncedDestPortValidation = debounce(() => {
    validatePortField(manualDestPortSelect, destPortValidationFeedback, 'destPort');
}, 300);
const debouncedDeviceCoordsValidation = debounce(validateDeviceCoordsField, 500);

/**
 * Validate device coordinates
 */
async function validateDeviceCoordsField() {
    const originDeviceId = manualOriginDeviceSelect?.value || null;
    const singlePort = manualSinglePortCheckbox?.checked || false;
    const destDeviceId = singlePort ? null : (manualDestDeviceSelect?.value || null);
    
    if (!originDeviceId) return;
    
    try {
        const result = await validateDeviceCoordinates(originDeviceId, destDeviceId);
        
        if (!result.valid && result.missing_devices && result.missing_devices.length > 0) {
            const message = `Device(s) missing coordinates: ${result.missing_devices.join(', ')}. Cable cannot be drawn on map.`;
            console.warn('[Validation]', message);
            
            // Show warning in UI (non-blocking, just informative)
            const feedbackEl = document.createElement('div');
            feedbackEl.className = 'validation-warning';
            feedbackEl.style.cssText = 'color: #d97706; font-size: 0.875rem; margin-top: 0.5rem; padding: 0.5rem; background: #fef3c7; border-radius: 0.25rem; border-left: 3px solid #f59e0b;';
            feedbackEl.innerHTML = `⚠️ ${message}<br><small>Please update device locations before creating this cable.</small>`;
            
            // Insert after destination device input or origin if single port
            const insertAfter = singlePort ? manualOriginDeviceSelect : manualDestDeviceSelect;
            if (insertAfter && insertAfter.parentElement) {
                // Remove previous warning if exists
                const oldWarning = insertAfter.parentElement.querySelector('.validation-warning');
                if (oldWarning) oldWarning.remove();
                
                insertAfter.parentElement.appendChild(feedbackEl);
            }
        } else {
            // Clear warning if coordinates are valid
            const warnings = document.querySelectorAll('.validation-warning');
            warnings.forEach(w => w.remove());
        }
    } catch (error) {
        console.error('Error validating device coordinates:', error);
    }
}

/**
 * Bind DOM references and event handlers. Should be called once.
 */
export function initModalEditor() {
    manualModal = findElement('manualSaveModal');
    manualModalContent = findElement('manualSaveModalContent');
    manualForm = findElement('manualSaveForm');
    manualRouteNameInput = findElement('manualRouteName');
    manualRouteDistanceEl = findElement('manualRouteDistance');
    manualOriginDeviceSelect = findElement('manualOriginDeviceSelect');
    manualOriginPortSelect = findElement('manualOriginPortSelect');
    manualDestDeviceSelect = findElement('manualDestDeviceSelect');
    manualDestPortSelect = findElement('manualDestPortSelect');
    manualSinglePortCheckbox = findElement('manualSinglePortOnly');
    manualDestNotice = findElement('manualDestNotice');

    // DEBUG: Check what element type we got from template
    console.log('[DEBUG initModalEditor] manualOriginDeviceSelect tagName:', manualOriginDeviceSelect?.tagName);
    console.log('[DEBUG initModalEditor] manualOriginDeviceSelect outerHTML:', manualOriginDeviceSelect?.outerHTML);
    console.log('[DEBUG initModalEditor] manualDestDeviceSelect tagName:', manualDestDeviceSelect?.tagName);

    // Real-time validation listeners
    if (manualRouteNameInput) {
        manualRouteNameInput.addEventListener('input', debouncedNameValidation);
        manualRouteNameInput.addEventListener('blur', validateCableNameField);
    }

    if (manualOriginPortSelect) {
        manualOriginPortSelect.addEventListener('change', debouncedOriginPortValidation);
    }

    if (manualDestPortSelect) {
        manualDestPortSelect.addEventListener('change', debouncedDestPortValidation);
    }

    if (manualOriginDeviceSelect) {
        manualOriginDeviceSelect.addEventListener('change', async () => {
            await loadPortsForOrigin();
            await syncDestinationDevice();
            debouncedDeviceCoordsValidation();
        });
    }

    if (manualDestDeviceSelect) {
        manualDestDeviceSelect.addEventListener('change', async () => {
            await loadPortsForDestination();
            debouncedDeviceCoordsValidation();
        });
    }

    if (manualSinglePortCheckbox) {
        manualSinglePortCheckbox.addEventListener('change', () => {
            void syncDestinationDevice();
            document.dispatchEvent(
                new CustomEvent('fiber:single-port-toggle', {
                    detail: { enabled: manualSinglePortCheckbox.checked },
                })
            );
        });
    }

    modalInitialized = true;

    if (cachedDeviceOptions.length) {
        applyDeviceOptionsToSelects();
    }
}

/**
 * Validate all required fields
 * Returns true if all validations pass, false otherwise
 */
export async function validateAllFields() {
    const singlePort = manualSinglePortCheckbox?.checked || false;
    
    // Validate name
    await validateCableNameField();
    
    // Validate origin port
    if (manualOriginPortSelect?.value) {
        await validatePortField(manualOriginPortSelect, originPortValidationFeedback, 'originPort');
    }
    
    // Validate destination port (only if not single port mode)
    if (!singlePort && manualDestPortSelect?.value) {
        await validatePortField(manualDestPortSelect, destPortValidationFeedback, 'destPort');
    }
    
    // Check required fields
    const nameValid = validationResults.name.valid;
    const originDeviceValid = manualOriginDeviceSelect?.value ? true : false;
    const originPortValid = validationResults.originPort.valid && manualOriginPortSelect?.value;
    const destValid = singlePort || (
        manualDestDeviceSelect?.value && 
        validationResults.destPort.valid && 
        manualDestPortSelect?.value
    );
    
    // Highlight missing required fields
    if (!manualRouteNameInput?.value) {
        showFieldError(
            manualRouteNameInput,
            nameValidationFeedback || getOrCreateFeedback(manualRouteNameInput, nameValidationFeedback),
            'Nome do cabo é obrigatório'
        );
    }

    if (!manualOriginDeviceSelect?.value) {
        const feedback = getOrCreateFeedback(manualOriginDeviceSelect, null);
        showFieldError(manualOriginDeviceSelect, feedback, 'Dispositivo origem é obrigatório');
    }

    if (!manualOriginPortSelect?.value) {
        const feedback = getOrCreateFeedback(manualOriginPortSelect, originPortValidationFeedback);
        showFieldError(manualOriginPortSelect, feedback, 'Porta origem é obrigatória');
    }

    if (!singlePort && !manualDestDeviceSelect?.value) {
        const feedback = getOrCreateFeedback(manualDestDeviceSelect, null);
        showFieldError(manualDestDeviceSelect, feedback, 'Dispositivo destino é obrigatório');
    }

    if (!singlePort && !manualDestPortSelect?.value) {
        const feedback = getOrCreateFeedback(manualDestPortSelect, destPortValidationFeedback);
        showFieldError(manualDestPortSelect, feedback, 'Porta destino é obrigatória');
    }
    
    return nameValid && originDeviceValid && originPortValid && destValid;
}

/**
 * Clear all validation states
 */
export function clearValidationStates() {
    validationResults = {
        name: { valid: true, message: '' },
        originPort: { valid: true, message: '' },
        destPort: { valid: true, message: '' }
    };
    
    if (manualRouteNameInput) {
        clearFieldError(manualRouteNameInput, nameValidationFeedback);
    }
    if (manualOriginPortSelect) {
        clearFieldError(manualOriginPortSelect, originPortValidationFeedback);
    }
    if (manualDestPortSelect) {
        clearFieldError(manualDestPortSelect, destPortValidationFeedback);
    }
    if (manualOriginDeviceSelect) {
        manualOriginDeviceSelect.style.borderColor = '';
        manualOriginDeviceSelect.style.boxShadow = '';
    }
    if (manualDestDeviceSelect) {
        manualDestDeviceSelect.style.borderColor = '';
        manualDestDeviceSelect.style.boxShadow = '';
    }
}

/**
 * Open modal for creating new route.
 */
export function openModalForCreate(distanceKm) {
    if (!manualModal || !manualModalContent) {
        console.warn('Manual save modal not found in DOM.');
        return;
    }

    editingFiberId = null;
    resetForm();

    if (manualRouteDistanceEl) {
        manualRouteDistanceEl.textContent = `${distanceKm.toFixed(3)} km`;
    }

    showModal();
    void syncDestinationDevice();
}

/**
 * Open modal populated with cable data.
 */
export async function openModalForEdit(cableData, distanceKm) {
    if (!manualModal || !manualForm) {
        console.warn('Manual save modal not found.');
        return;
    }

    clearValidationStates();
    editingFiberId = cableData.id;

    if (manualRouteNameInput) {
        manualRouteNameInput.value = cableData.name || '';
    }

    if (manualSinglePortCheckbox) {
        manualSinglePortCheckbox.checked = Boolean(cableData.single_port);
    }

    if (manualOriginDeviceSelect) {
        manualOriginDeviceSelect.value = cableData.origin_device_id
            ? String(cableData.origin_device_id)
            : '';
        await loadPortsForOrigin();
        if (manualOriginPortSelect) {
            manualOriginPortSelect.value = cableData.origin_port_id
                ? String(cableData.origin_port_id)
                : '';
        }
    }

    const isSinglePort = Boolean(cableData.single_port);
    if (isSinglePort) {
        if (manualDestDeviceSelect) {
            manualDestDeviceSelect.value = manualOriginDeviceSelect?.value ?? '';
        }
        if (manualDestPortSelect) {
            manualDestPortSelect.innerHTML = '<option value="">-- destino desabilitado --</option>';
            manualDestPortSelect.disabled = true;
        }
    } else if (manualDestDeviceSelect) {
        manualDestDeviceSelect.disabled = false;
        manualDestDeviceSelect.value = cableData.dest_device_id
            ? String(cableData.dest_device_id)
            : '';
    }

    // syncDestinationDevice loads dest ports for non-single-port cables;
    // set the dest port value immediately after it finishes (no polling timer).
    await syncDestinationDevice();

    if (!isSinglePort && manualDestPortSelect && cableData.dest_port_id) {
        manualDestPortSelect.disabled = false;
        manualDestPortSelect.value = String(cableData.dest_port_id);
    }

    if (manualRouteDistanceEl) {
        manualRouteDistanceEl.textContent = `${distanceKm.toFixed(3)} km`;
    }

    const submitButton = manualForm.querySelector('button[type="submit"]');
    if (submitButton) submitButton.textContent = 'Atualizar cabo';

    const titleEl = document.getElementById('manualSaveModalTitle');
    if (titleEl) titleEl.textContent = 'Editar dados do cabo';

    showModal();
}

/** Close modal with fade-out animation. */
export function closeModal() {
    if (!manualModal || !manualModalContent) return;

    manualModal.classList.remove('opacity-100');
    manualModal.classList.add('opacity-0');
    manualModalContent.classList.remove('opacity-100', 'scale-100');
    manualModalContent.classList.add('opacity-0', 'scale-95');

    setTimeout(() => {
        manualModal.classList.add('pointer-events-none');
    }, 300);

    editingFiberId = null;

    if (manualForm) {
        const submitButton = manualForm.querySelector('button[type="submit"]');
        if (submitButton) submitButton.textContent = 'Salvar rota';
    }
}

/** Return current editing fiber id or null. */
export function getEditingFiberId() {
    return editingFiberId;
}

/** True when modal visible. */
export function isModalOpen() {
    if (!manualModal) return false;
    return (
        !manualModal.classList.contains('pointer-events-none') &&
        manualModal.classList.contains('opacity-100')
    );
}

/** True when editing existing cable. */
export function isEditMode() {
    return editingFiberId !== null;
}

/** Reset form fields and selects. */
export function resetForm() {
    if (!manualForm) return;

    manualForm.reset();

    // Clear validation states
    clearValidationStates();

    if (manualOriginPortSelect) {
        manualOriginPortSelect.innerHTML = '<option value="">Selecione...</option>';
    }

    if (manualDestPortSelect) {
        manualDestPortSelect.innerHTML = '<option value="">Selecione...</option>';
        manualDestPortSelect.disabled = false;
    }

    if (manualDestDeviceSelect) {
        manualDestDeviceSelect.disabled = false;
    }

    if (manualSinglePortCheckbox) {
        manualSinglePortCheckbox.checked = false;
    }

    if (manualDestNotice) {
        manualDestNotice.classList.add('hidden');
    }

    const submitButton = manualForm.querySelector('button[type="submit"]');
    if (submitButton) submitButton.textContent = 'Salvar rota';
}

function formatDeviceLabel(option) {
    if (!option) return '';
    return option.site ? `${option.name} (${option.site})` : option.name;
}

function populateDeviceSelect(select, options = []) {
    if (!select) return;

    const previousValue = select.value;
    const placeholder = select.dataset?.placeholder || 'Select...';

    select.innerHTML = `<option value="">${placeholder}</option>`;

    options.forEach((option) => {
        const opt = document.createElement('option');
        opt.value = String(option.id);
        opt.textContent = formatDeviceLabel(option);
        select.appendChild(opt);
    });

    if (previousValue) {
        const exists = options.some((option) => String(option.id) === String(previousValue));
        select.value = exists ? String(previousValue) : '';
    } else {
        select.value = '';
    }
}

function applyDeviceOptionsToSelects() {
    populateDeviceSelect(manualOriginDeviceSelect, cachedDeviceOptions);
    populateDeviceSelect(manualDestDeviceSelect, cachedDeviceOptions);
    void syncDestinationDevice();
}

/** Persist latest device options for future modal openings. */
export function setDeviceOptions(options = []) {
    cachedDeviceOptions = Array.isArray(options) ? options : [];
    if (modalInitialized) {
        applyDeviceOptionsToSelects();
    }
}

async function loadPortsForOrigin() {
    if (!manualOriginPortSelect) return;
    await loadPortsForSelect(manualOriginDeviceSelect?.value || null, manualOriginPortSelect);
}

async function loadPortsForDestination() {
    if (!manualDestPortSelect) return;
    await loadPortsForSelect(manualDestDeviceSelect?.value || null, manualDestPortSelect);
}

async function loadPortsForSelect(deviceId, targetSelect) {
    if (!targetSelect) return;

    console.log('[loadPortsForSelect] Loading ports for device:', deviceId);

    targetSelect.innerHTML = '<option value="">Carregando...</option>';

    if (!deviceId) {
        console.warn('[loadPortsForSelect] No device ID provided');
        targetSelect.innerHTML = '<option value="">Selecione...</option>';
        return;
    }

    try {
        console.log('[loadPortsForSelect] Fetching ports for device:', deviceId);
        const data = await fetchDevicePorts(deviceId);
        console.log('[loadPortsForSelect] Received', data?.ports?.length || 0, 'ports');
        targetSelect.innerHTML = '<option value="">Selecione...</option>';

        if (Array.isArray(data.ports)) {
            data.ports.forEach((port) => {
                const option = document.createElement('option');
                option.value = String(port.id);
                option.textContent = port.name;
                targetSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load ports:', error);
        targetSelect.innerHTML = '<option value="">Falha ao carregar</option>';
    }
}

async function syncDestinationDevice() {
    const singlePort = manualSinglePortCheckbox?.checked ?? false;

    if (manualDestNotice) {
        manualDestNotice.classList.toggle('hidden', !singlePort);
    }

    if (manualDestDeviceSelect) {
        manualDestDeviceSelect.disabled = singlePort;
        if (singlePort) {
            manualDestDeviceSelect.value = manualOriginDeviceSelect?.value ?? '';
        }
    }

    if (manualDestPortSelect) {
        if (singlePort) {
            manualDestPortSelect.innerHTML = '<option value="">-- destino desabilitado --</option>';
            manualDestPortSelect.disabled = true;
        } else {
            manualDestPortSelect.disabled = false;
            if (manualDestDeviceSelect?.value) {
                await loadPortsForSelect(manualDestDeviceSelect.value, manualDestPortSelect);
            } else {
                manualDestPortSelect.innerHTML = '<option value="">Selecione...</option>';
            }
        }
    }
}

/** External hook to refresh destination state after flow actions. */
export async function refreshDestinationState() {
    await syncDestinationDevice();
}

/** Placeholder for future validation rules. */
export function updateEditButtonState() {
    // Implement validation gating when needed.
}

function showModal() {
    if (!manualModal || !manualModalContent) return;

    manualModal.classList.remove('pointer-events-none');
    manualModal.classList.add('opacity-100');
    manualModalContent.classList.add('opacity-100', 'scale-100');
    manualModalContent.classList.remove('opacity-0', 'scale-95');

    if (manualRouteNameInput) {
        requestAnimationFrame(() => manualRouteNameInput.focus());
    }
}
