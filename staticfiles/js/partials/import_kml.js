const kmlModal = document.getElementById('importKmlModal');
const kmlModalContent = document.getElementById('importKmlModalContent');
const kmlOriginDeviceSelect = document.getElementById('kmlOriginDeviceSelect');
const kmlOriginPortSelect = document.getElementById('kmlOriginPortSelect');
const kmlDestDeviceSelect = document.getElementById('kmlDestDeviceSelect');
const kmlDestPortSelect = document.getElementById('kmlDestPortSelect');
const kmlSinglePortCheckbox = document.getElementById('kmlSinglePortOnly');
const kmlDestNotice = document.getElementById('kmlDestNotice');

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
        const response = await fetch(`/zabbix_api/api/device-ports/${deviceId}/`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            },
            cache: 'no-store',
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

if (kmlOriginDeviceSelect) {
    kmlOriginDeviceSelect.addEventListener('change', async () => {
        await populatePorts(kmlOriginDeviceSelect.value, kmlOriginPortSelect);
        await syncKmlDestination();
    });
}

if (kmlDestDeviceSelect) {
    kmlDestDeviceSelect.addEventListener('change', async () => {
        if (kmlDestDeviceSelect.disabled) return;
        await populatePorts(kmlDestDeviceSelect.value, kmlDestPortSelect);
    });
}

if (kmlSinglePortCheckbox) {
    kmlSinglePortCheckbox.addEventListener('change', syncKmlDestination);
}

const importFormEl = document.getElementById('importKmlForm');
if (importFormEl) {
    importFormEl.addEventListener('submit', async (event) => {
        event.preventDefault();
        const formData = new FormData(importFormEl);
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        try {
            const response = await fetch('/zabbix_api/api/fibers/import-kml/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                },
                body: formData,
            });

            const data = await response.json();
            if (response.ok) {
                alert(`Import completed successfully. Imported points: ${data.points ?? '?'}`);
                closeKmlModal();
                importFormEl.reset();
                await populatePorts('', kmlOriginPortSelect);
                await populatePorts('', kmlDestPortSelect);
                await syncKmlDestination();
                document.dispatchEvent(new CustomEvent('fiber:cable-created', {
                    detail: { fiberId: data.fiber_id },
                }));
            } else {
                alert(`Import failed: ${data.error || 'Upload error'}`);
            }
        } catch (error) {
            console.error('KML import failed:', error);
            alert('Network or server error during upload.');
        }
    });
}

if (kmlModal) {
    kmlModal.addEventListener('click', (event) => {
        if (event.target === kmlModal) {
            closeKmlModal();
        }
    });
}

syncKmlDestination();

if (kmlOriginDeviceSelect) {
    populatePorts(kmlOriginDeviceSelect.value, kmlOriginPortSelect);
}

window.openKmlModal = openKmlModal;
window.closeKmlModal = closeKmlModal;
