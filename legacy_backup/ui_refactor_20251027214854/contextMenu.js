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
let cableInfoEl = null;
let cableNameEl = null;
let savePathEl = null;
let generalOptionsEl = null;
let reloadButtonEl = null;
let reloadTextEl = null;

const MENU_Z_INDEX = 2147483647;

function ensureMenuAttachedToBody() {
    if (!menuElement) {
        return;
    }
    if (menuElement.parentElement !== document.body) {
        document.body.appendChild(menuElement);
    }
    menuElement.style.position = 'fixed';
    menuElement.style.zIndex = String(MENU_Z_INDEX);
    menuElement.style.pointerEvents = 'auto';
}

export function initContextMenu() {
    menuElement = document.getElementById('contextMenu');
    selectedOptionsEl = document.getElementById('contextSelectedOptions');
    creatingOptionsEl = document.getElementById('contextCreatingOptions');
    cableInfoEl = document.getElementById('contextCableInfo');
    cableNameEl = document.getElementById('contextCableName');
    savePathEl = document.getElementById('contextSavePath');
    generalOptionsEl = document.getElementById('contextGeneralOptions');
    reloadButtonEl = document.getElementById('contextLoadAll');
    reloadTextEl = document.getElementById('contextLoadAllText');

    ensureMenuAttachedToBody();

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
}

export function showContextMenu(x, y) {
    if (!menuElement) {
        console.error('[contextMenu] menuElement is not initialized.');
        return;
    }

    ensureMenuAttachedToBody();

    const menuWidth = menuElement.offsetWidth || 220;
    const menuHeight = menuElement.offsetHeight || 300;
    const margin = 20;
    const offsetX = 6;
    const offsetY = 6;

    let adjustedX = x + offsetX;
    let adjustedY = y + offsetY;

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    if (adjustedX + menuWidth > viewportWidth - margin) {
        adjustedX = x - menuWidth - offsetX;
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

export function updateContextMenuState({ hasActiveFiber, fiberMeta, pathLength }) {
    if (!menuElement) return;

    const isCreatingNewCable = !hasActiveFiber && pathLength > 0;
    const isSelectedCable = hasActiveFiber && !!fiberMeta;
    const isEmpty = !hasActiveFiber && pathLength === 0;

    selectedOptionsEl?.classList.add('hidden');
    creatingOptionsEl?.classList.add('hidden');
    cableInfoEl?.classList.add('hidden');
    generalOptionsEl?.classList.add('hidden');
    reloadButtonEl?.classList.add('hidden');

    if (isCreatingNewCable) {
        creatingOptionsEl?.classList.remove('hidden');
    } else if (isSelectedCable) {
        selectedOptionsEl?.classList.remove('hidden');
        cableInfoEl?.classList.remove('hidden');
        if (cableNameEl) {
            const editingSuffix = pathLength > 0 ? ' - EDITING' : '';
            const displayName = fiberMeta.name || `Cable #${fiberMeta.id ?? '?'}`;
            cableNameEl.textContent = `📌 ${displayName}${editingSuffix}`;
        }
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
