/**
 * contextMenu.js - Context Menu Management Module
 * 
 * Handles right-click context menu display, positioning, and state management.
 * Supports three scenarios:
 * - Scenario A: Empty state (no cable selected, no points drawn)
 * - Scenario B: Creating new cable (points drawn, no cable selected)
 * - Scenario C: Cable selected (editing existing cable)
 * 
 * @module contextMenu
 */

// DOM element cache
let menuElement = null;
let selectedOptionsEl = null;
let creatingOptionsEl = null;
let cableInfoEl = null;
let cableNameEl = null;
let savePathEl = null;
let generalOptionsEl = null;
let reloadButtonEl = null;
let reloadTextEl = null;

/**
 * Initialize the context menu module.
 * Caches DOM references and sets up event listeners.
 * Should be called once on page load.
 */
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

    // Setup global click listener to hide menu when clicking outside
    document.addEventListener('click', (e) => {
        if (menuElement && !menuElement.contains(e.target)) {
            hideContextMenu();
        }
    });

    // Setup ESC key to close menu
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            hideContextMenu();
        }
    });
}

/**
 * Show context menu at specified coordinates.
 * Automatically adjusts position to stay within viewport bounds.
 * 
 * @param {number} x - X coordinate (clientX from mouse event)
 * @param {number} y - Y coordinate (clientY from mouse event)
 */
export function showContextMenu(x, y) {
    if (!menuElement) return;

    // Menu dimensions and viewport constraints
    const menuWidth = 220;
    const menuHeight = 300; // Estimated (not critical)
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    const offsetX = 5;
    const offsetY = 5;
    const margin = 20; // Safety margin from viewport edges

    // Adjust X to prevent overflow (right side)
    let adjustedX = x + offsetX;
    if (adjustedX + menuWidth > windowWidth - margin) {
        // Position to the left of cursor
        adjustedX = x - menuWidth - offsetX;
        // If still overflows left side, force minimum margin
        if (adjustedX < margin) {
            adjustedX = margin;
        }
    }

    // Adjust Y to prevent overflow (bottom)
    let adjustedY = y + offsetY;
    if (adjustedY + menuHeight > windowHeight - margin) {
        adjustedY = windowHeight - menuHeight - margin;
    }
    if (adjustedY < margin) {
        adjustedY = margin;
    }

    // Position and show menu
    menuElement.style.left = adjustedX + 'px';
    menuElement.style.top = adjustedY + 'px';
    menuElement.classList.remove('hidden');
}

/**
 * Hide the context menu.
 */
export function hideContextMenu() {
    if (menuElement) {
        menuElement.classList.add('hidden');
    }
}

/**
 * Update context menu state based on application context.
 * Shows/hides appropriate menu sections based on current scenario.
 * 
 * @param {Object} context - Application state context
 * @param {boolean} context.hasActiveFiber - Whether a cable is currently selected
 * @param {Object|null} context.fiberMeta - Metadata of selected cable (name, id, etc.)
 * @param {number} context.pathLength - Number of points in current path
 */
export function updateContextMenuState(context) {
    const { hasActiveFiber, fiberMeta, pathLength } = context;

    // Determine scenario
    const isCreatingNewCable = !hasActiveFiber && pathLength > 0; // Scenario B
    const isSelectedCable = hasActiveFiber && !!fiberMeta; // Scenario C
    const isEmpty = !hasActiveFiber && pathLength === 0; // Scenario A

    // Reset all sections (hide everything)
    selectedOptionsEl?.classList.add('hidden');
    creatingOptionsEl?.classList.add('hidden');
    cableInfoEl?.classList.add('hidden');
    generalOptionsEl?.classList.add('hidden');
    reloadButtonEl?.classList.add('hidden');

    if (isCreatingNewCable) {
        // Scenario B: Drawing new cable
        creatingOptionsEl?.classList.remove('hidden');
        // No reload, no import options
    } else if (isSelectedCable) {
        // Scenario C: Cable selected for editing
        selectedOptionsEl?.classList.remove('hidden');
        cableInfoEl?.classList.remove('hidden');

        // Update cable name display
        if (cableNameEl) {
            const isEditing = pathLength > 0;
            const status = isEditing ? ' - EDITING' : '';
            const displayName = fiberMeta.name || `Cable #${fiberMeta.id || '?'}`;
            cableNameEl.textContent = `📌 ${displayName}${status}`;
        }

        // Show "Reload This Cable" button
        if (reloadButtonEl && reloadTextEl) {
            reloadButtonEl.classList.remove('hidden');
            reloadTextEl.textContent = 'Reload This Cable';
        }

        // Enable "Save Path" only if ≥2 points
        if (savePathEl) {
            savePathEl.disabled = pathLength < 2;
            savePathEl.style.opacity = pathLength >= 2 ? '1' : '0.5';
        }
    } else if (isEmpty) {
        // Scenario A: Empty state
        generalOptionsEl?.classList.remove('hidden'); // Show "Import KML"

        // Show "Reload All Cables" button
        if (reloadButtonEl && reloadTextEl) {
            reloadButtonEl.classList.remove('hidden');
            reloadTextEl.textContent = 'Reload All Cables';
        }
    }
}

/**
 * Check if context menu is currently visible.
 * 
 * @returns {boolean} True if menu is visible, false otherwise
 */
export function isContextMenuVisible() {
    return menuElement && !menuElement.classList.contains('hidden');
}

/**
 * Get the current position of the context menu.
 * 
 * @returns {{x: number, y: number}|null} Menu position or null if menu not visible
 */
export function getContextMenuPosition() {
    if (!menuElement || menuElement.classList.contains('hidden')) {
        return null;
    }
    return {
        x: parseInt(menuElement.style.left, 10) || 0,
        y: parseInt(menuElement.style.top, 10) || 0,
    };
}
