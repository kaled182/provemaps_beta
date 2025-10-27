/**
 * uiHelpers.js - UI Helper Functions Module
 * 
 * Contains utility functions for UI updates:
 * - Points list rendering and drag-drop
 * - Distance display updates
 * - Button state management
 * - Form data extraction
 * 
 * @module uiHelpers
 */

import { getPath, reorderPath } from './pathState.js';

/**
 * Refresh the points list display with drag-and-drop support.
 * Shows numbered list of lat/lng coordinates.
 */
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

        // Drag start - mark as being dragged
        item.addEventListener('dragstart', (event) => {
            event.dataTransfer.setData('text/plain', index);
            item.classList.add('bg-blue-100');
        });

        // Drag end - remove visual feedback
        item.addEventListener('dragend', () => {
            item.classList.remove('bg-blue-100');
        });

        // Drag over - allow drop
        item.addEventListener('dragover', (event) => {
            event.preventDefault();
            item.classList.add('bg-blue-50');
        });

        // Drag leave - remove hover effect
        item.addEventListener('dragleave', () => {
            item.classList.remove('bg-blue-50');
        });

        // Drop - reorder path
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

/**
 * Update distance display element.
 * 
 * @param {number} distanceKm - Distance in kilometers
 */
export function updateDistanceDisplay(distanceKm) {
    const distanceEl = document.getElementById('distanceKm');
    if (distanceEl) {
        distanceEl.textContent = distanceKm.toFixed(3);
    }
}

/**
 * Update save button state based on path and active cable.
 * 
 * @param {number} pathLength - Number of points in path
 * @param {boolean} hasActiveCable - Whether a cable is currently selected
 */
export function updateSaveButtonState(pathLength, hasActiveCable) {
    const saveButton = document.getElementById('savePath');
    if (!saveButton) return;
    
    const allowSave = (pathLength >= 2) || (hasActiveCable && pathLength === 0);
    saveButton.disabled = !allowSave;
}

/**
 * Extract form data from manual save modal.
 * 
 * @returns {Object} Form data object
 */
export function extractFormData() {
    const form = document.getElementById('manualSaveForm');
    const checkbox = document.getElementById('manualSinglePortOnly');
    
    if (!form) {
        throw new Error('Form element not found');
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
        dest_port_id: singlePort ? null : formData.get('dest_port_id'),
        single_port: singlePort,
    };
}

/**
 * Show success message to user.
 * 
 * @param {string} message - Success message
 */
export function showSuccessMessage(message) {
    alert(message);
}

/**
 * Show error message to user.
 * 
 * @param {string} message - Error message
 */
export function showErrorMessage(message) {
    alert(message);
}

/**
 * Toggle panel visibility.
 * 
 * @param {string} panelId - ID of panel to toggle
 * @param {string|null} hideOtherId - ID of other panel to hide (optional)
 */
export function togglePanel(panelId, hideOtherId = null) {
    const panel = document.getElementById(panelId);
    
    if (panel) {
        panel.classList.toggle('hidden');
        
        // Hide other panel if specified and current panel is now visible
        if (hideOtherId && !panel.classList.contains('hidden')) {
            const otherPanel = document.getElementById(hideOtherId);
            if (otherPanel) {
                otherPanel.classList.add('hidden');
            }
        }
    }
}

/**
 * Disable form submit button during async operation.
 * 
 * @param {boolean} disabled - Whether to disable the button
 */
export function setFormSubmitting(disabled) {
    const form = document.getElementById('manualSaveForm');
    if (!form) return;
    
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.disabled = disabled;
        submitButton.textContent = disabled ? 'Saving...' : 'Save';
    }
}

/**
 * Update cable select dropdown value.
 * 
 * @param {string|number} cableId - Cable ID to select
 */
export function updateCableSelect(cableId) {
    const select = document.getElementById('fiberSelect');
    if (select) {
        select.value = cableId ? String(cableId) : '';
    }
}

/**
 * Get current value from cable select dropdown.
 * 
 * @returns {string|null} Selected cable ID or null
 */
export function getCableSelectValue() {
    const select = document.getElementById('fiberSelect');
    return select ? select.value : null;
}

/**
 * Get CSRF token from cookie for AJAX requests.
 * 
 * @param {string} name - Cookie name (default: 'csrftoken')
 * @returns {string|null} CSRF token or null
 */
export function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        return parts.pop().split(';').shift();
    }
    return null;
}
