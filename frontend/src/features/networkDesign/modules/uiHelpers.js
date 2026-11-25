/**
 * uiHelpers.js - UI Helper Functions Module
 *
 * Provides shared UI utilities for the Fiber Route Builder.
 * Includes point list rendering, the new toast/confirmation helpers,
 * form handling helpers, and common utilities.
 */

import { getPath, reorderPath } from './pathState.js';

const TOAST_DEFAULT_DURATION = 4200;

function getFullscreenElement() {
    return (
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.mozFullScreenElement ||
        document.msFullscreenElement ||
        null
    );
}

function ensureHost(hostId) {
    // Primeiro tenta encontrar dentro do container da página Network Design
    const pageContainer = document.querySelector('.network-design-page');
    let host = pageContainer ? pageContainer.querySelector(`#${hostId}`) : null;
    
    // Se não encontrou, busca globalmente
    if (!host) {
        host = document.getElementById(hostId);
    }
    
    // Se ainda não existe, cria dentro do container da página (não no body)
    if (!host) {
        host = document.createElement('div');
        host.id = hostId;
        host.className = 'hidden';
        const targetContainer = pageContainer || document.body;
        targetContainer.appendChild(host);
    }
    
    // Não move o elemento se já estiver no lugar certo
    return host;
}

function createToast(message, { title, type = 'info', duration = TOAST_DEFAULT_DURATION } = {}) {
    const host = ensureHost('toastHost');
    host.classList.remove('hidden');
    host.style.pointerEvents = 'none';

    const card = document.createElement('div');
    card.className = `toast-card toast-${type}`;
    // EV-0138: texto por textContent (a mensagem pode trazer dados do servidor); estilo global
    // em NetworkDesignView (o <style scoped> não chega a nós criados por JS)
    const body = document.createElement('div');
    body.className = 'toast-body';
    if (title) {
        const strong = document.createElement('strong');
        strong.textContent = title;
        body.appendChild(strong);
    }
    const text = document.createElement('div');
    text.textContent = message;
    body.appendChild(text);
    card.appendChild(body);

    host.appendChild(card);

    const remove = () => {
        if (!card.parentElement) return;
        card.classList.add('opacity-0');
        setTimeout(() => {
            card.remove();
            if (!host.hasChildNodes()) {
                host.classList.add('hidden');
            }
        }, 160);
    };

    setTimeout(remove, duration);
    return remove;
}

export function showSuccessMessage(message, options = {}) {
    const { title = 'Concluído', duration } = options;
    createToast(message, { title, type: 'success', duration });
}

export function showErrorMessage(message, options = {}) {
    const { title = 'Erro', duration } = options;
    createToast(message, { title, type: 'error', duration: duration ?? 5200 });
}

export function showInfoMessage(message, options = {}) {
    const { title = 'Informação', duration } = options;
    createToast(message, { title, type: 'info', duration });
}

function createConfirm(options = {}) {
    const host = ensureHost('confirmHost');
    host.innerHTML = '';
    host.classList.add('active');
    host.classList.remove('hidden');

    const backdrop = document.createElement('div');
    backdrop.className = 'confirm-backdrop';

    const {
        title = 'Confirmação',
        description = '',
        confirmText = 'Confirmar',
        cancelText = 'Cancelar',
        tone = 'primary',
    } = options;

    // EV-0138: textos por textContent (nomes de cabos vêm do utilizador)
    const card = document.createElement('div');
    card.className = 'confirm-card';
    if (title) {
        const h = document.createElement('h3');
        h.textContent = title;
        card.appendChild(h);
    }
    if (description) {
        const p = document.createElement('p');
        p.textContent = description;
        card.appendChild(p);
    }
    const buttons = document.createElement('div');
    buttons.className = 'confirm-buttons';
    const cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.dataset.variant = 'secondary';
    cancel.textContent = cancelText;
    const ok = document.createElement('button');
    ok.type = 'button';
    ok.dataset.variant = tone === 'danger' ? 'danger' : 'primary';
    ok.textContent = confirmText;
    buttons.append(cancel, ok);
    card.appendChild(buttons);

    host.appendChild(backdrop);
    host.appendChild(card);
    return { host, backdrop, card };
}

export function showConfirmDialog(options = {}) {
    return new Promise((resolve) => {
        const { host, backdrop, card } = createConfirm(options);

        const cleanup = () => {
            document.removeEventListener('keydown', handleKey);
            host.classList.remove('active');
            host.classList.add('hidden');
            host.innerHTML = '';
        };

        const buttons = card.querySelectorAll('button');
        const cancelBtn = buttons[0];
        const confirmBtn = buttons[1];

        const onCancel = () => {
            cleanup();
            resolve(false);
        };

        const onConfirm = () => {
            cleanup();
            resolve(true);
        };

        cancelBtn.addEventListener('click', onCancel, { once: true });
        confirmBtn.addEventListener('click', onConfirm, { once: true });
        backdrop.addEventListener('click', onCancel, { once: true });

        const handleKey = (event) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                onCancel();
            } else if (event.key === 'Enter') {
                event.preventDefault();
                onConfirm();
            }
        };

        document.addEventListener('keydown', handleKey);
    });
}

export function refreshPointsList() {
    const list = document.getElementById('pointsList');
    if (!list) return;

    const currentPath = getPath();
    list.innerHTML = '';

    currentPath.forEach((point, index) => {
        const item = document.createElement('li');
        item.className = 'point-row flex justify-between items-center';
        item.draggable = true;
        item.dataset.idx = index;
        item.innerHTML = `
            <span>${index + 1}. ${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}</span>
        `;

        item.addEventListener('dragstart', (event) => {
            event.dataTransfer.setData('text/plain', index);
            item.classList.add('bg-blue-100');
        });

        item.addEventListener('dragend', () => {
            item.classList.remove('bg-blue-100');
        });

        item.addEventListener('dragover', (event) => {
            event.preventDefault();
            item.classList.add('bg-blue-50');
        });

        item.addEventListener('dragleave', () => {
            item.classList.remove('bg-blue-50');
        });

        item.addEventListener('drop', (event) => {
            event.preventDefault();
            item.classList.remove('bg-blue-50');

            const fromIndex = parseInt(event.dataTransfer.getData('text/plain'), 10);
            const toIndex = parseInt(item.dataset.idx, 10);

            if (Number.isInteger(fromIndex) &&
                Number.isInteger(toIndex) &&
                fromIndex !== toIndex) {
                reorderPath(fromIndex, toIndex);
            }
        });

        list.appendChild(item);
    });
}

export function updateDistanceDisplay(distanceKm) {
    const distanceEl = document.getElementById('distanceKm');
    if (distanceEl) {
        distanceEl.textContent = distanceKm.toFixed(3);
    }
}

export function updateSaveButtonState(pathLength, hasActiveCable) {
    const saveButton = document.getElementById('savePath');
    if (!saveButton) return;

    const allowSave = (pathLength >= 2) || (hasActiveCable && pathLength === 0);
    saveButton.disabled = !allowSave;
}

export function extractFormData() {
    const form = document.getElementById('manualSaveForm');
    const checkbox = document.getElementById('manualSinglePortOnly');

    if (!form) {
        throw new Error('Expected form element not found');
    }

    const formData = new FormData(form);
    const singlePort = checkbox ? checkbox.checked : false;

    return {
        name: (formData.get('name') || '').trim(),
        origin_device_id: formData.get('origin_device_id'),
        origin_port_id: formData.get('origin_port_id'),
        dest_device_id: singlePort
            ? formData.get('origin_device_id')
            : formData.get('dest_device_id'),
        dest_port_id: singlePort ? formData.get('origin_port_id') : formData.get('dest_port_id'),
        single_port: singlePort,
    };
}

export function togglePanel(panelId, hideOtherId = null) {
    const panel = document.getElementById(panelId);

    if (panel) {
        panel.classList.toggle('hidden');

        if (hideOtherId && !panel.classList.contains('hidden')) {
            const otherPanel = document.getElementById(hideOtherId);
            if (otherPanel) {
                otherPanel.classList.add('hidden');
            }
        }
    }
}

export function setFormSubmitting(disabled) {
    const form = document.getElementById('manualSaveForm');
    if (!form) return;

    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.disabled = disabled;
        submitButton.textContent = disabled ? 'Saving...' : 'Save';
    }
}

export function updateCableSelect(cableId) {
    const select = document.getElementById('fiberSelect');
    if (select) {
        select.value = cableId ? String(cableId) : '';
    }
}

export function getCableSelectValue() {
    const select = document.getElementById('fiberSelect');
    return select ? select.value : null;
}

export function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        return parts.pop().split(';').shift();
    }
    return null;
}

export function cleanupUIHelpers() {
    // Remove toastHost if it was created dynamically
    const toastHost = document.getElementById('toastHost');
    if (toastHost && toastHost.parentElement === document.body) {
        toastHost.remove();
    }
    
    // Remove confirmHost if it was created dynamically
    const confirmHost = document.getElementById('confirmHost');
    if (confirmHost && confirmHost.parentElement === document.body) {
        confirmHost.remove();
    }
}
