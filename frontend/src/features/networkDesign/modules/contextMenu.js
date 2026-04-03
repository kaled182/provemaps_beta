/**
 * contextMenu.js - Context menu positioning and visibility management.
 *
 * Designed to work both in normal mode and when the Google Maps container
 * enters fullscreen. The menu is rendered as a direct child of <body> with
 * position:fixed so it always floats above the map.
 */

let menuElement = null;
let selectedOptionsEl = null;
let creatingOptionsEl = null;
let previewOptionsEl = null;
let cableInfoEl = null;
let cableNameEl = null;
let cableBadgesEl = null;
let savePathEl = null;
let generalOptionsEl = null;
let reloadButtonEl = null;
let reloadTextEl = null;

function fullscreenElement() {
    return (
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.mozFullScreenElement ||
        document.msFullscreenElement ||
        null
    );
}

function _renderCableBadges(meta) {
    if (!cableBadgesEl) return;
    const parts = [];
    const typeName = meta?.cable_type?.name;
    const groupName = meta?.cable_group?.name;
    if (typeName) parts.push(`<span class="ctx-badge ctx-badge--type">${typeName}</span>`);
    if (groupName) parts.push(`<span class="ctx-badge ctx-badge--group">${groupName}</span>`);
    cableBadgesEl.innerHTML = parts.join('');
}

export function initContextMenu() {
    // Busca dentro do container da página primeiro
    const pageContainer = document.querySelector('.network-design-page');
    const searchRoot = pageContainer || document;
    
    menuElement = searchRoot.querySelector('#contextMenu') || document.getElementById('contextMenu');
    selectedOptionsEl = searchRoot.querySelector('#contextSelectedOptions') || document.getElementById('contextSelectedOptions');
    creatingOptionsEl = searchRoot.querySelector('#contextCreatingOptions') || document.getElementById('contextCreatingOptions');
    previewOptionsEl = searchRoot.querySelector('#contextPreviewOptions') || document.getElementById('contextPreviewOptions');
    cableInfoEl = searchRoot.querySelector('#contextCableInfo') || document.getElementById('contextCableInfo');
    cableNameEl = searchRoot.querySelector('#contextCableName') || document.getElementById('contextCableName');
    cableBadgesEl = searchRoot.querySelector('#contextCableBadges') || document.getElementById('contextCableBadges');
    savePathEl = searchRoot.querySelector('#contextSavePath') || document.getElementById('contextSavePath');
    generalOptionsEl = searchRoot.querySelector('#contextGeneralOptions') || document.getElementById('contextGeneralOptions');
    reloadButtonEl = searchRoot.querySelector('#contextLoadAll') || document.getElementById('contextLoadAll');
    reloadTextEl = searchRoot.querySelector('#contextLoadAllText') || document.getElementById('contextLoadAllText');

    // Não anexa ao document.body - deixa no container da página
    if (menuElement) {
        menuElement.style.position = 'fixed';
        menuElement.style.pointerEvents = 'auto';
    }

    document.addEventListener('click', (event) => {
        if (menuElement && !menuElement.classList.contains('hidden') && !menuElement.contains(event.target)) {
            hideContextMenu();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            hideContextMenu();
        }
    });

    const handleFullscreenChange = () => {
        const fsElement = fullscreenElement();
        if (fsElement && menuElement) {
            menuElement.style.position = 'absolute';
        } else if (menuElement) {
            menuElement.style.position = 'fixed';
        }
    };

    ['fullscreenchange', 'webkitfullscreenchange', 'mozfullscreenchange', 'MSFullscreenChange'].forEach((evt) => {
        document.addEventListener(evt, handleFullscreenChange);
    });
}

export function showContextMenu(x, y) {
    if (!menuElement) {
        console.error('[contextMenu] menuElement is not initialized.');
        return;
    }

    const fsElement = fullscreenElement();
    const parent = fsElement || menuElement.parentElement || document.body;
    const parentRect = parent.getBoundingClientRect();
    menuElement.style.position = fsElement ? 'absolute' : 'fixed';

    const menuWidth = menuElement.offsetWidth || 220;
    const menuHeight = menuElement.offsetHeight || 300;
    const margin = 20;
    const offsetX = 6;
    const offsetY = 6;

    const baseX = x - parentRect.left;
    const baseY = y - parentRect.top;

    let adjustedX = baseX + offsetX;
    let adjustedY = baseY + offsetY;

    const viewportWidth = parentRect.width;
    const viewportHeight = parentRect.height;

    if (adjustedX + menuWidth > viewportWidth - margin) {
        adjustedX = baseX - menuWidth - offsetX;
        if (adjustedX < margin) adjustedX = margin;
    } else if (adjustedX < margin) {
        adjustedX = margin;
    }

    if (adjustedY + menuHeight > viewportHeight - margin) {
        adjustedY = viewportHeight - menuHeight - margin;
    } else if (adjustedY < margin) {
        adjustedY = margin;
    }

    menuElement.style.left = `${adjustedX}px`;
    menuElement.style.top = `${adjustedY}px`;
    menuElement.classList.remove('hidden');
}

export function hideContextMenu() {
    if (menuElement) {
        menuElement.classList.add('hidden');
    }
}

export function updateContextMenuState({ hasActiveFiber, fiberMeta, pathLength, previewCableId, previewCableMeta }) {
    if (!menuElement) return;

    const isCreatingNewCable = !hasActiveFiber && !previewCableId && pathLength > 0;
    const isPreviewCable = !hasActiveFiber && !!previewCableId && !!previewCableMeta;
    const isEditingCable = hasActiveFiber && !!fiberMeta;
    const isEmpty = !hasActiveFiber && !previewCableId && pathLength === 0;

    selectedOptionsEl?.classList.add('hidden');
    creatingOptionsEl?.classList.add('hidden');
    previewOptionsEl?.classList.add('hidden');
    cableInfoEl?.classList.add('hidden');
    generalOptionsEl?.classList.add('hidden');
    reloadButtonEl?.classList.add('hidden');

    if (isCreatingNewCable) {
        creatingOptionsEl?.classList.remove('hidden');
    } else if (isPreviewCable) {
        previewOptionsEl?.classList.remove('hidden');
        cableInfoEl?.classList.remove('hidden');
        if (cableNameEl) {
            cableNameEl.textContent = previewCableMeta.name || `Cabo #${previewCableId}`;
        }
        _renderCableBadges(previewCableMeta);
    } else if (isEditingCable) {
        selectedOptionsEl?.classList.remove('hidden');
        cableInfoEl?.classList.remove('hidden');
        if (cableNameEl) {
            const editingSuffix = pathLength > 0 ? ' — editando' : '';
            const displayName = fiberMeta.name || `Cabo #${fiberMeta.id ?? '?'}`;
            cableNameEl.textContent = `${displayName}${editingSuffix}`;
        }
        _renderCableBadges(fiberMeta);
        if (reloadButtonEl && reloadTextEl) {
            reloadButtonEl.classList.remove('hidden');
            reloadTextEl.textContent = 'Reload This Cable';
        }
        if (savePathEl) {
            const enabled = pathLength >= 2;
            savePathEl.disabled = !enabled;
            savePathEl.style.opacity = enabled ? '1' : '0.5';
        }
    } else if (isEmpty) {
        generalOptionsEl?.classList.remove('hidden');
        if (reloadButtonEl && reloadTextEl) {
            reloadButtonEl.classList.remove('hidden');
            reloadTextEl.textContent = 'Reload All Cables';
        }
    }
}

export function isContextMenuVisible() {
    return Boolean(menuElement && !menuElement.classList.contains('hidden'));
}

export function getContextMenuPosition() {
    if (!menuElement || menuElement.classList.contains('hidden')) {
        return null;
    }
    return {
        x: parseInt(menuElement.style.left, 10) || 0,
        y: parseInt(menuElement.style.top, 10) || 0,
    };
}

export function cleanupContextMenu() {
    hideContextMenu();
    // Reset all references
    menuElement = null;
    selectedOptionsEl = null;
    creatingOptionsEl = null;
    previewOptionsEl = null;
    cableInfoEl = null;
    cableNameEl = null;
    cableBadgesEl = null;
    savePathEl = null;
    generalOptionsEl = null;
    reloadButtonEl = null;
    reloadTextEl = null;
}
