/**
 * modalEditor.js - Modal Form Management Module
 * 
 * Handles fiber cable creation/editing modal:
 * - Open/close modal with animations
 * - Form field population and reset
 * - Single-port mode logic (destination device sync)
 * - Device/port dropdown loading and syncing
 * - Form validation and submission
 * 
 * @module modalEditor
 */

import { fetchDevicePorts } from './apiClient.js';

// DOM element cache
let manualModal = null;
let manualModalContent = null;
let manualForm = null;
let manualRouteNameInput = null;
let manualRouteDistanceEl = null;
let manualOriginDeviceSelect = null;
let manualOriginPortSelect = null;
let manualDestDeviceSelect = null;
let manualDestPortSelect = null;
let manualSinglePortCheckbox = null;
let manualDestNotice = null;

// Current editing state
let editingFiberId = null;

// Cached device select data so we can reapply it whenever the modal is re-initialized
let cachedDeviceOptions = [];
let modalInitialized = false;

/**
 * Initialize the modal editor module.
 * Caches DOM references and sets up event listeners.
 * Should be called once on page load.
 */
export function initModalEditor() {
    manualModal = document.getElementById('manualSaveModal');
    manualModalContent = document.getElementById('manualSaveModalContent');
    manualForm = document.getElementById('manualSaveForm');
    manualRouteNameInput = document.getElementById('manualRouteName');
    manualRouteDistanceEl = document.getElementById('manualRouteDistance');
    manualOriginDeviceSelect = document.getElementById('manualOriginDeviceSelect');
    manualOriginPortSelect = document.getElementById('manualOriginPortSelect');
    manualDestDeviceSelect = document.getElementById('manualDestDeviceSelect');
    manualDestPortSelect = document.getElementById('manualDestPortSelect');
    manualSinglePortCheckbox = document.getElementById('manualSinglePortOnly');
    manualDestNotice = document.getElementById('manualDestNotice');

    // Setup device select change handlers
    if (manualOriginDeviceSelect) {
        manualOriginDeviceSelect.addEventListener('change', async () => {
            await loadPortsForOrigin();
            await syncDestinationDevice();
        });
    }

    if (manualDestDeviceSelect) {
        manualDestDeviceSelect.addEventListener('change', () => {
            loadPortsForDestination();
        });
    }

    if (manualSinglePortCheckbox) {
        manualSinglePortCheckbox.addEventListener('change', () => {
            syncDestinationDevice();
            document.dispatchEvent(new CustomEvent('fiber:single-port-toggle', {
                detail: { enabled: manualSinglePortCheckbox.checked },
            }));
        });
    }

    modalInitialized = true;

    if (cachedDeviceOptions.length) {
        applyDeviceOptionsToSelects();
    }
}

/**
 * Open modal for creating new cable.
 * Resets form fields to default state.
 * 
 * @param {number} distance - Current path distance in km
 */
export function openModalForCreate(distance) {
    if (!manualModal || !manualModalContent) {
        console.warn('Manual save modal not found in the DOM.');
        return;
    }

    editingFiberId = null;
    resetForm();

    if (manualRouteDistanceEl) {
        manualRouteDistanceEl.textContent = `${distance.toFixed(3)} km`;
    }

    showModal();
    syncDestinationDevice();
}

/**
 * Open modal for editing existing cable.
 * Populates form fields with cable metadata.
 * 
 * @param {Object} cableData - Cable metadata
 * @param {number} cableData.id - Cable ID
 * @param {string} cableData.name - Cable name
 * @param {boolean} cableData.single_port - Single port mode
 * @param {number} cableData.origin_device_id - Origin device ID
 * @param {number} cableData.origin_port_id - Origin port ID
 * @param {number} cableData.dest_device_id - Destination device ID
 * @param {number} cableData.dest_port_id - Destination port ID
 * @param {number} distance - Current path distance in km
 */
export async function openModalForEdit(cableData, distance) {
    if (!manualModal || !manualForm) {
        console.warn('Manual save modal not found.');
        return;
    }

    editingFiberId = cableData.id;

    // Populate name
    if (manualRouteNameInput) {
        manualRouteNameInput.value = cableData.name || '';
    }

    // Populate single port checkbox
    if (manualSinglePortCheckbox) {
        manualSinglePortCheckbox.checked = Boolean(cableData.single_port);
    }

    // Populate origin device and ports
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

    // Populate destination device and ports
    const isSinglePort = Boolean(cableData.single_port);
    if (isSinglePort) {
        // Single port mode: sync destination with origin
        if (manualDestDeviceSelect) {
            manualDestDeviceSelect.value = manualOriginDeviceSelect 
                ? manualOriginDeviceSelect.value 
                : '';
        }
        if (manualDestPortSelect) {
            manualDestPortSelect.innerHTML = '<option value="">-- destino desabilitado --</option>';
            manualDestPortSelect.disabled = true;
        }
    } else {
        // Normal mode: load destination ports
        if (manualDestDeviceSelect) {
            manualDestDeviceSelect.disabled = false;
            manualDestDeviceSelect.value = cableData.dest_device_id 
                ? String(cableData.dest_device_id) 
                : '';
            await loadPortsForDestination();

            // Retry logic to ensure ports are loaded before setting value
            if (manualDestPortSelect && cableData.dest_port_id) {
                const setPortValue = () => {
                    const optionsCount = manualDestPortSelect.options.length;
                    if (optionsCount <= 1) {
                        // Ports not yet loaded, retry
                        setTimeout(setPortValue, 100);
                        return;
                    }
                    manualDestPortSelect.disabled = false;
                    manualDestPortSelect.value = String(cableData.dest_port_id);
                };
                setTimeout(setPortValue, 100);
            }
        }
    }

    await syncDestinationDevice();

    // Update distance display
    if (manualRouteDistanceEl) {
        manualRouteDistanceEl.textContent = `${distance.toFixed(3)} km`;
    }

    // Update submit button text
    const submitButton = manualForm.querySelector('button[type="submit"]');
    if (submitButton) submitButton.textContent = 'Atualizar cabo';

    showModal();
}

/**
 * Close the modal with fade-out animation.
 */
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

    // Reset submit button text
    if (manualForm) {
        const submitButton = manualForm.querySelector('button[type="submit"]');
        if (submitButton) submitButton.textContent = 'Salvar rota';
    }
}

/**
 * Get current editing fiber ID.
 * 
 * @returns {number|null} Fiber ID if editing, null if creating
 */
export function getEditingFiberId() {
    return editingFiberId;
}

/**
 * Determine whether the modal is currently visible.
 *
 * @returns {boolean}
 */
export function isModalOpen() {
    if (!manualModal) {
        return false;
    }
    return !manualModal.classList.contains('pointer-events-none') && manualModal.classList.contains('opacity-100');
}

/**
 * Check if modal is in editing mode.
 * 
 * @returns {boolean} True if editing existing cable, false if creating new
 */
export function isEditMode() {
    return editingFiberId !== null;
}

/**
 * Reset form to initial state.
 * Clears all fields and resets dropdowns.
 */
export function resetForm() {
    if (!manualForm) return;

    manualForm.reset();

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
    if (!option) {
        return '';
    }
    if (option.site) {
        return `${option.name} (${option.site})`;
    }
    return option.name;
}

function populateDeviceSelect(select, options = []) {
    if (!select) {
        return;
    }

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

export function setDeviceOptions(options = []) {
    cachedDeviceOptions = Array.isArray(options) ? options : [];
    if (modalInitialized) {
        applyDeviceOptionsToSelects();
    }
}

/**
 * Load ports for origin device.
 * Populates origin port dropdown.
 */
async function loadPortsForOrigin() {
    if (!manualOriginDeviceSelect || !manualOriginPortSelect) return;
    const deviceId = manualOriginDeviceSelect.value;
    await loadPortsForSelect(deviceId, manualOriginPortSelect);
}

/**
 * Load ports for destination device.
 * Populates destination port dropdown.
 */
async function loadPortsForDestination() {
    if (!manualDestDeviceSelect || !manualDestPortSelect) return;
    const deviceId = manualDestDeviceSelect.value;
    await loadPortsForSelect(deviceId, manualDestPortSelect);
}

/**
 * Load ports for a device into a select element.
 * 
 * @param {string} deviceId - Device ID
 * @param {HTMLSelectElement} targetSelect - Target select element
 */
async function loadPortsForSelect(deviceId, targetSelect) {
    if (!targetSelect) return;

    targetSelect.innerHTML = '<option value="">Carregando...</option>';

    if (!deviceId) {
        targetSelect.innerHTML = '<option value="">Selecione...</option>';
        return;
    }

    try {
        const data = await fetchDevicePorts(deviceId);
        targetSelect.innerHTML = '<option value="">Selecione...</option>';

        if (Array.isArray(data.ports)) {
            data.ports.forEach((port) => {
                const option = document.createElement('option');
                option.value = port.id;
                option.textContent = port.name;
                targetSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load ports:', error);
        targetSelect.innerHTML = '<option value="">Falha ao carregar</option>';
    }
}

/**
 * Sync destination device with origin when single-port mode is enabled.
 * Disables destination port select in single-port mode.
 */
async function syncDestinationDevice() {
    const singlePort = manualSinglePortCheckbox && manualSinglePortCheckbox.checked;

    // Show/hide destination notice
    if (manualDestNotice) {
        manualDestNotice.classList.toggle('hidden', !singlePort);
    }

    // Handle destination device select
    if (manualDestDeviceSelect) {
        manualDestDeviceSelect.disabled = singlePort;
        if (singlePort) {
            manualDestDeviceSelect.value = manualOriginDeviceSelect 
                ? manualOriginDeviceSelect.value 
                : '';
        }
    }

    // Handle destination port select
    if (manualDestPortSelect) {
        if (singlePort) {
            manualDestPortSelect.innerHTML = '<option value="">-- destino desabilitado --</option>';
            manualDestPortSelect.disabled = true;
        } else {
            manualDestPortSelect.disabled = false;
            if (manualDestDeviceSelect && manualDestDeviceSelect.value) {
                await loadPortsForSelect(manualDestDeviceSelect.value, manualDestPortSelect);
            } else {
                manualDestPortSelect.innerHTML = '<option value="">Selecione...</option>';
            }
        }
    }
}

export async function refreshDestinationState() {
    await syncDestinationDevice();
}

/**
 * Show modal with fade-in animation.
 */
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

/**
 * Update edit button state in modal.
 * Called after form changes to enable/disable submit button.
 */
export function updateEditButtonState() {
    // Placeholder for future validation logic
    // Can check if all required fields are filled
}
