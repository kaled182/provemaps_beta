/**
 * Modal editor module for manual fiber routes.
 * Manages modal lifecycle, form state, device/port selects, and single-port mode toggling.
 */

import { fetchDevicePorts } from './apiClient.js';

// Cached DOM references
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

// Editing state
let editingFiberId = null;

// Device option cache reused by frontend builder bootstrap
let cachedDeviceOptions = [];
let modalInitialized = false;

/**
 * Helper to find elements within the page container first, then globally
 */
function findElement(id) {
    const pageContainer = document.querySelector('.network-design-page');
    const element = pageContainer ? pageContainer.querySelector(`#${id}`) : null;
    return element || document.getElementById(id);
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

    if (manualOriginDeviceSelect) {
        manualOriginDeviceSelect.addEventListener('change', async () => {
            await loadPortsForOrigin();
            await syncDestinationDevice();
        });
    }

    if (manualDestDeviceSelect) {
        manualDestDeviceSelect.addEventListener('change', () => {
            void loadPortsForDestination();
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
        await loadPortsForDestination();

        if (manualDestPortSelect && cableData.dest_port_id) {
            const ensureValueSet = () => {
                const optionsCount = manualDestPortSelect.options.length;
                if (optionsCount <= 1) {
                    setTimeout(ensureValueSet, 100);
                    return;
                }
                manualDestPortSelect.disabled = false;
                manualDestPortSelect.value = String(cableData.dest_port_id);
            };
            setTimeout(ensureValueSet, 100);
        }
    }

    await syncDestinationDevice();

    if (manualRouteDistanceEl) {
        manualRouteDistanceEl.textContent = `${distanceKm.toFixed(3)} km`;
    }

    const submitButton = manualForm.querySelector('button[type="submit"]');
    if (submitButton) submitButton.textContent = 'Atualizar cabo';

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
    if (!manualOriginDeviceSelect || !manualOriginPortSelect) return;
    const deviceId = manualOriginDeviceSelect.value;
    await loadPortsForSelect(deviceId, manualOriginPortSelect);
}

async function loadPortsForDestination() {
    if (!manualDestDeviceSelect || !manualDestPortSelect) return;
    const deviceId = manualDestDeviceSelect.value;
    await loadPortsForSelect(deviceId, manualDestPortSelect);
}

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
