let kmlModal;
let kmlModalContent;
let kmlOriginDeviceSelect;
let kmlOriginPortSelect;
let kmlDestDeviceSelect;
let kmlDestPortSelect;
let kmlSinglePortCheckbox;
let kmlDestNotice;
let kmlGroupSelect;
let kmlResponsibleSelect;
let importFormEl;
let deviceOptions = Array.isArray(window.__FIBER_DEVICE_OPTIONS)
    ? window.__FIBER_DEVICE_OPTIONS
    : [];
let initialized = false;

const originChangeHandler = async () => {
    await populatePorts(kmlOriginDeviceSelect?.value, kmlOriginPortSelect);
    await syncKmlDestination();
};

const destChangeHandler = async () => {
    if (kmlDestDeviceSelect?.disabled) {
        return;
    }
    await populatePorts(kmlDestDeviceSelect?.value, kmlDestPortSelect);
};

const singlePortChangeHandler = () => {
    void syncKmlDestination();
};

const modalClickHandler = (event) => {
    if (event.target === kmlModal) {
        closeKmlModal();
    }
};

const importSubmitHandler = async (event) => {
    event.preventDefault();
    const formData = new FormData(importFormEl);
    const csrfToken = ensureCsrfToken();

    try {
        const response = await fetch('/api/v1/inventory/fibers/import-kml/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
            },
            credentials: 'same-origin',
            body: formData,
        });

        const data = await response.json();
        if (response.ok) {
            showKmlToast(`Rota importada com sucesso (${data.points ?? '?'} pontos).`, 'success');
            closeKmlModal();
            importFormEl.reset();
            await populatePorts('', kmlOriginPortSelect);
            await populatePorts('', kmlDestPortSelect);
            await syncKmlDestination();

            document.dispatchEvent(new CustomEvent('fiber:cable-created', {
                detail: { fiberId: data.fiber_id },
            }));
        } else {
            showKmlToast(data.error || 'Erro ao importar rota.', 'error');
        }
    } catch (error) {
        console.error('KML import failed:', error);
        showKmlToast('Erro de rede ao importar rota.', 'error');
    }
};

function ensureCsrfToken() {
    const hiddenInputs = document.querySelectorAll('input[name="csrfmiddlewaretoken"]');
    const token = window.CSRF_TOKEN || hiddenInputs[0]?.value || '';
    if (!token) {
        console.warn('[import_kml] CSRF token not found.');
    }
    hiddenInputs.forEach((input) => {
        input.value = token;
    });
    return token;
}

function formatDeviceOption(option) {
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
    const placeholder = select.dataset.placeholder || 'Select...';
    select.innerHTML = `<option value="">${placeholder}</option>`;

    options.forEach((option) => {
        const opt = document.createElement('option');
        opt.value = String(option.id);
        opt.textContent = formatDeviceOption(option);
        select.appendChild(opt);
    });

    if (previousValue) {
        const exists = options.some((option) => String(option.id) === String(previousValue));
        select.value = exists ? String(previousValue) : '';
    }
}

function refreshDeviceSelects() {
    populateDeviceSelect(kmlOriginDeviceSelect, deviceOptions);
    populateDeviceSelect(kmlDestDeviceSelect, deviceOptions);
}

function showKmlToast(message, type) {
    const host = document.getElementById('toastHost');
    if (!host) { alert(message); return; }
    const toast = document.createElement('div');
    toast.style.cssText = `background:${type === 'success' ? '#065f46' : '#7f1d1d'};color:#fff;padding:.75rem 1rem;border-radius:.5rem;margin-top:.5rem;font-size:.875rem;box-shadow:0 4px 12px rgba(0,0,0,.3)`;
    toast.textContent = message;
    host.classList.remove('hidden');
    host.appendChild(toast);
    setTimeout(() => { toast.remove(); if (!host.children.length) host.classList.add('hidden'); }, 4000);
}

async function loadKmlGroups() {
    if (!kmlGroupSelect) return;
    try {
        const res = await fetch('/api/v1/inventory/cable-groups/', { credentials: 'same-origin' });
        if (!res.ok) return;
        const data = await res.json();
        kmlGroupSelect.innerHTML = '<option value="">— Sem grupo —</option>';
        (data.results || []).forEach(g => {
            const opt = document.createElement('option');
            opt.value = g.id;
            opt.textContent = g.name;
            kmlGroupSelect.appendChild(opt);
        });
    } catch { /* ignore */ }
}

async function loadKmlResponsibles() {
    if (!kmlResponsibleSelect) return;
    try {
        const res = await fetch('/api/users/?is_active=true', { credentials: 'same-origin' });
        if (!res.ok) return;
        const data = await res.json();
        kmlResponsibleSelect.innerHTML = '<option value="">— Sem responsável —</option>';
        (data.users || []).forEach(u => {
            const opt = document.createElement('option');
            opt.value = u.id;
            opt.textContent = u.full_name || u.username;
            kmlResponsibleSelect.appendChild(opt);
        });
    } catch { /* ignore */ }
}

function openKmlModal() {
    if (!kmlModal || !kmlModalContent) {
        console.warn('KML modal not found in the DOM.');
        return;
    }
    kmlModal.classList.remove('pointer-events-none');
    kmlModal.classList.add('opacity-100');
    kmlModalContent.classList.add('opacity-100', 'scale-100');
    kmlModalContent.classList.remove('opacity-0', 'scale-95');
}

function closeKmlModal() {
    if (!kmlModal || !kmlModalContent) {
        return;
    }
    kmlModal.classList.remove('opacity-100');
    kmlModal.classList.add('opacity-0');
    kmlModalContent.classList.remove('opacity-100', 'scale-100');
    kmlModalContent.classList.add('opacity-0', 'scale-95');
    setTimeout(() => {
        if (kmlModal) kmlModal.classList.add('pointer-events-none');
    }, 300);
}

async function populatePorts(deviceId, targetSelect) {
    if (!targetSelect) return;
    targetSelect.innerHTML = '<option value="">Carregando...</option>';
    if (!deviceId) {
        targetSelect.innerHTML = '<option value="">Selecione...</option>';
        return;
    }

    try {
        const response = await fetch(`/api/v1/inventory/devices/${deviceId}/ports/`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            },
            cache: 'no-store',
            credentials: 'same-origin',
        });
        if (!response.ok) {
            targetSelect.innerHTML = '<option value="">Falha ao carregar</option>';
            return;
        }
        const data = await response.json();
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

async function syncKmlDestination() {
    const singlePort = kmlSinglePortCheckbox && kmlSinglePortCheckbox.checked;

    if (kmlDestNotice) {
        kmlDestNotice.classList.toggle('hidden', !singlePort);
    }

    if (kmlDestDeviceSelect) {
        kmlDestDeviceSelect.disabled = singlePort;
        if (singlePort) {
            kmlDestDeviceSelect.value = kmlOriginDeviceSelect ? kmlOriginDeviceSelect.value : '';
        }
    }

    if (kmlDestPortSelect) {
        if (singlePort) {
            kmlDestPortSelect.disabled = true;
            kmlDestPortSelect.innerHTML = '<option value="">-- destino desabilitado --</option>';
        } else {
            kmlDestPortSelect.disabled = false;
            await populatePorts(kmlDestDeviceSelect ? kmlDestDeviceSelect.value : '', kmlDestPortSelect);
        }
    }
}

function attachEventListeners() {
    if (kmlOriginDeviceSelect && !kmlOriginDeviceSelect.dataset.boundOrigin) {
        kmlOriginDeviceSelect.addEventListener('change', originChangeHandler);
        kmlOriginDeviceSelect.dataset.boundOrigin = 'true';
    }

    if (kmlDestDeviceSelect && !kmlDestDeviceSelect.dataset.boundDest) {
        kmlDestDeviceSelect.addEventListener('change', destChangeHandler);
        kmlDestDeviceSelect.dataset.boundDest = 'true';
    }

    if (kmlSinglePortCheckbox && !kmlSinglePortCheckbox.dataset.boundSinglePort) {
        kmlSinglePortCheckbox.addEventListener('change', singlePortChangeHandler);
        kmlSinglePortCheckbox.dataset.boundSinglePort = 'true';
    }

    if (importFormEl && !importFormEl.dataset.boundSubmit) {
        importFormEl.addEventListener('submit', importSubmitHandler);
        importFormEl.dataset.boundSubmit = 'true';
    }

    if (kmlModal && !kmlModal.dataset.boundBackdrop) {
        kmlModal.addEventListener('click', modalClickHandler);
        kmlModal.dataset.boundBackdrop = 'true';
    }
}

export async function initializeKmlModal(force = false) {
    if (initialized && !force) {
        refreshDeviceSelects();
        ensureCsrfToken();
        return true;
    }

    // Busca elementos dentro do container da página primeiro
    const pageContainer = document.querySelector('.network-design-page');
    const findElement = (id) => {
        const el = pageContainer ? pageContainer.querySelector(`#${id}`) : null;
        return el || document.getElementById(id);
    };

    kmlModal = findElement('importKmlModal');
    kmlModalContent = findElement('importKmlModalContent');
    kmlOriginDeviceSelect = findElement('kmlOriginDeviceSelect');
    kmlOriginPortSelect = findElement('kmlOriginPortSelect');
    kmlDestDeviceSelect = findElement('kmlDestDeviceSelect');
    kmlDestPortSelect = findElement('kmlDestPortSelect');
    kmlSinglePortCheckbox = findElement('kmlSinglePortOnly');
    kmlDestNotice = findElement('kmlDestNotice');
    kmlGroupSelect = findElement('kmlCableGroupSelect');
    kmlResponsibleSelect = findElement('kmlResponsibleSelect');
    importFormEl = findElement('importKmlForm');

    if (!kmlModal || !kmlModalContent || !importFormEl) {
        console.warn('[import_kml] DOM elements not ready yet.');
        return false;
    }

    refreshDeviceSelects();
    attachEventListeners();
    void syncKmlDestination();
    void loadKmlGroups();
    void loadKmlResponsibles();

    if (kmlOriginDeviceSelect && kmlOriginDeviceSelect.value) {
        await populatePorts(kmlOriginDeviceSelect.value, kmlOriginPortSelect);
    } else {
        await populatePorts('', kmlOriginPortSelect);
    }

    ensureCsrfToken();

    window.openKmlModal = openKmlModal;
    window.closeKmlModal = closeKmlModal;

    initialized = true;
    return true;
}

export function isKmlModalInitialized() {
    return initialized;
}

export function cleanupKmlModal() {
    // Remove event listeners
    if (kmlOriginDeviceSelect) {
        kmlOriginDeviceSelect.removeEventListener('change', originChangeHandler);
    }
    if (kmlDestDeviceSelect) {
        kmlDestDeviceSelect.removeEventListener('change', destChangeHandler);
    }
    if (kmlSinglePortCheckbox) {
        kmlSinglePortCheckbox.removeEventListener('change', singlePortChangeHandler);
    }
    if (kmlModal) {
        kmlModal.removeEventListener('click', modalClickHandler);
    }
    if (importFormEl) {
        importFormEl.removeEventListener('submit', importSubmitHandler);
    }
    
    // Clear references
    kmlModal = null;
    kmlModalContent = null;
    kmlOriginDeviceSelect = null;
    kmlOriginPortSelect = null;
    kmlDestDeviceSelect = null;
    kmlDestPortSelect = null;
    kmlSinglePortCheckbox = null;
    kmlDestNotice = null;
    kmlGroupSelect = null;
    kmlResponsibleSelect = null;
    importFormEl = null;
    deviceOptions = [];
    initialized = false;
    
    // Clear global functions
    delete window.openKmlModal;
    delete window.closeKmlModal;
    delete window.initializeKmlModal;
}

if (typeof window !== 'undefined') {
    window.initializeKmlModal = initializeKmlModal;
}

document.addEventListener('fiber:device-options-loaded', (event) => {
    const nextOptions = event.detail?.devices;
    if (!Array.isArray(nextOptions)) {
        return;
    }

    deviceOptions = nextOptions;
    refreshDeviceSelects();

    if (kmlOriginDeviceSelect) {
        populatePorts(kmlOriginDeviceSelect.value, kmlOriginPortSelect);
    }

    if (kmlDestDeviceSelect && !kmlSinglePortCheckbox?.checked) {
        populatePorts(kmlDestDeviceSelect.value, kmlDestPortSelect);
    }

    void syncKmlDestination();
});
