const kmlModal = document.getElementById('importKmlModal');
const kmlModalContent = document.getElementById('importKmlModalContent');
const kmlOriginDeviceSelect = document.getElementById('kmlOriginDeviceSelect');
const kmlOriginPortSelect = document.getElementById('kmlOriginPortSelect');
const kmlDestDeviceSelect = document.getElementById('kmlDestDeviceSelect');
const kmlDestPortSelect = document.getElementById('kmlDestPortSelect');
const kmlSinglePortCheckbox = document.getElementById('kmlSinglePortOnly');
const kmlDestNotice = document.getElementById('kmlDestNotice');
const kmlGroupSelect = document.getElementById('kmlCableGroupSelect');
const kmlResponsibleSelect = document.getElementById('kmlResponsibleSelect');

function showKmlToast(message, type) {
    // Reuse Vue toast host if present, else fall back to a simple banner
    const host = document.getElementById('toastHost');
    if (!host) {
        alert(message);
        return;
    }
    const toast = document.createElement('div');
    toast.style.cssText = `background:${type === 'success' ? '#065f46' : '#7f1d1d'};color:#fff;padding:.75rem 1rem;border-radius:.5rem;margin-top:.5rem;font-size:.875rem;box-shadow:0 4px 12px rgba(0,0,0,.3)`;
    toast.textContent = message;
    host.classList.remove('hidden');
    host.appendChild(toast);
    setTimeout(() => { toast.remove(); if (!host.children.length) host.classList.add('hidden'); }, 4000);
}

function openKmlModal() {
    if (!kmlModal || !kmlModalContent) return;
    kmlModal.classList.remove('pointer-events-none');
    kmlModal.classList.add('opacity-100');
    kmlModalContent.style.transform = 'scale(1)';
    kmlModalContent.style.opacity = '1';
}

function closeKmlModal() {
    if (!kmlModal || !kmlModalContent) return;
    kmlModal.classList.remove('opacity-100');
    kmlModal.classList.add('opacity-0');
    kmlModalContent.style.transform = 'scale(.95)';
    kmlModalContent.style.opacity = '0';
    setTimeout(() => { if (kmlModal) kmlModal.classList.add('pointer-events-none'); }, 300);
}

async function populatePorts(deviceId, targetSelect) {
    if (!targetSelect) return;
    targetSelect.innerHTML = '<option value="">Carregando...</option>';
    if (!deviceId) { targetSelect.innerHTML = '<option value="">Selecione...</option>'; return; }
    try {
        const res = await fetch(`/api/v1/inventory/devices/${deviceId}/ports/`, {
            headers: { 'Accept': 'application/json', 'Cache-Control': 'no-cache' },
            cache: 'no-store', credentials: 'same-origin',
        });
        if (!res.ok) { targetSelect.innerHTML = '<option value="">Falha ao carregar</option>'; return; }
        const data = await res.json();
        targetSelect.innerHTML = '<option value="">Selecione...</option>';
        (data.ports || []).forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = p.name;
            targetSelect.appendChild(opt);
        });
    } catch { targetSelect.innerHTML = '<option value="">Falha ao carregar</option>'; }
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
        const res = await fetch('/api/v1/inventory/responsibles/', { credentials: 'same-origin' });
        if (!res.ok) return;
        const data = await res.json();
        kmlResponsibleSelect.innerHTML = '<option value="">— Sem responsável —</option>';
        (data.results || []).forEach(r => {
            const opt = document.createElement('option');
            opt.value = r.id;
            opt.textContent = r.name;
            kmlResponsibleSelect.appendChild(opt);
        });
    } catch { /* ignore */ }
}

async function syncKmlDestination() {
    const singlePort = kmlSinglePortCheckbox && kmlSinglePortCheckbox.checked;
    if (kmlDestNotice) kmlDestNotice.classList.toggle('hidden', !singlePort);
    if (kmlDestDeviceSelect) {
        kmlDestDeviceSelect.disabled = singlePort;
        if (singlePort) kmlDestDeviceSelect.value = kmlOriginDeviceSelect ? kmlOriginDeviceSelect.value : '';
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
        const csrfToken = window.CSRF_TOKEN || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        const submitBtn = importFormEl.querySelector('button[type="submit"]');
        if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Importando...'; }

        try {
            const res = await fetch('/api/v1/inventory/fibers/import-kml/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                credentials: 'same-origin',
                body: formData,
            });
            const data = await res.json();
            if (res.ok) {
                showKmlToast(`Rota importada com sucesso (${data.points ?? '?'} pontos).`, 'success');
                closeKmlModal();
                importFormEl.reset();
                await populatePorts('', kmlOriginPortSelect);
                await populatePorts('', kmlDestPortSelect);
                await syncKmlDestination();
                document.dispatchEvent(new CustomEvent('fiber:cable-created', { detail: { fiberId: data.fiber_id } }));
            } else {
                showKmlToast(data.error || 'Erro ao importar rota.', 'error');
            }
        } catch (err) {
            console.error('KML import failed:', err);
            showKmlToast('Erro de rede ao importar rota.', 'error');
        } finally {
            if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Importar rota'; }
        }
    });
}

if (kmlModal) {
    kmlModal.addEventListener('click', (e) => { if (e.target === kmlModal) closeKmlModal(); });
}

// Initialize
syncKmlDestination();
loadKmlGroups();
loadKmlResponsibles();
if (kmlOriginDeviceSelect) populatePorts(kmlOriginDeviceSelect.value, kmlOriginPortSelect);

window.openKmlModal = openKmlModal;
window.closeKmlModal = closeKmlModal;
