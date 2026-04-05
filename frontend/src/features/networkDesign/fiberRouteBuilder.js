// Core modules
// Revert to relative imports (server static path already resolves module directory)
import { getPath, setPath as setPathState, addPoint, updatePoint, removePoint, reorderPath, clearPath, totalDistance as calculateDistance, onPathChange } from './modules/pathState.js';
import { initMap as initializeMap, onMapClick, onMapRightClick, drawPolyline, clearPolyline, addMarker as createMarker, removeMarker, clearMarkers as clearAllMarkers, attachPolylineRightClick, createCablePolyline, getMapInstance, cleanupMap, fitMapToBounds } from './modules/mapCore-refactored.js';
import { latLngToPixel, distanceBetweenPixels, distancePointToSegmentPx } from '@/utils/mapUtils.js';
import { getCurrentProviderName } from '@/providers/maps/MapProviderFactory.js';
import { initContextMenu, showContextMenu, hideContextMenu, updateContextMenuState, cleanupContextMenu } from './modules/contextMenu.js';
import {
    initModalEditor,
    openModalForCreate,
    openModalForEdit,
    closeModal,
    getEditingFiberId,
    updateEditButtonState,
    isModalOpen,
    setDeviceOptions,
    refreshDestinationState,
    validateAllFields,
    clearValidationStates,
} from './modules/modalEditor.js';

// API client modules
import { fetchFibers, fetchFiber, createFiberManual, updateFiber, removeFiber, validateNearbyCables } from './modules/apiClient.js';

// Business logic modules
import { initCableService, loadCableList, loadCableDetails, createCable, updateCableData, deleteCable, loadAllCablesForVisualization, validateCablePayload, removeCableVisualization, cleanupCableService, highlightCable } from './modules/cableService.js';

// UI helper modules
import { refreshPointsList, updateDistanceDisplay, updateSaveButtonState, extractFormData, showSuccessMessage, showErrorMessage, togglePanel, setFormSubmitting, updateCableSelect, showConfirmDialog, cleanupUIHelpers } from './modules/uiHelpers.js';

// Application state
let map;
let polyline;
let markers = [];
let activeFiberId = null;
let currentFiberMeta = null;
// Preview state: cable selected (right-clicked) but NOT in edit mode
let previewCableId = null;
let previewCableMeta = null;
// When true, the modal was opened from preview (metadata-only); path must be preserved
let metadataOnlyEdit = false;
// REMOVED: let allCablesPolylines = []; // Managed inside cableService.js

// DOM elements
let manualForm;
let manualModal;
let distanceEl;
let manualSinglePortCheckbox;
let appInitialized = false;
let domBindingsInitialized = false;
let mapsInitStarted = false;
let deviceOptionsCache = null;
let deviceOptionsPromise = null;
let deviceOptionsDispatched = false;
let globalListenersBound = false;
let activeEndpoint = 'end'; // 'start' | 'end'

// Nearby cables validation state
let nearbyCablesWarningEl = null;

/**
 * Show or hide the Route Points panel (editing mode).
 */
function setRoutePointsPanelVisible(visible) {
    const panel = document.getElementById('routePointsPanel');
    if (!panel) return;
    panel.classList.toggle('nd-panel-hidden', !visible);
}

/**
 * Show or hide the Cable Details panel (preview/read-only mode).
 */
function setCableDetailsPanelVisible(visible) {
    const panel = document.getElementById('cableDetailsPanel');
    if (!panel) return;
    panel.classList.toggle('nd-panel-hidden', !visible);
}

/**
 * Populate the Cable Details panel with metadata.
 */
function populateCableDetailsPanel(meta) {
    const set = (id, text) => {
        const el = document.getElementById(id);
        if (el) el.textContent = text || '—';
    };
    set('cableDetailName', meta.name);
    const distance = meta.path_length_km != null ? `${parseFloat(meta.path_length_km).toFixed(3)} km` : '—';
    set('cableDetailDistance', distance);
    const originDevice = meta.origin?.device || meta.origin?.device_name || meta.origin?.device_id || null;
    const originPort = meta.origin?.port || meta.origin?.port_name || meta.origin?.port_id || null;
    set('cableDetailOrigin', originDevice ? `${originDevice}${originPort ? ` / ${originPort}` : ''}` : '—');
    const destDevice = meta.destination?.device || meta.destination?.device_name || meta.destination?.device_id || null;
    const destPort = meta.destination?.port || meta.destination?.port_name || meta.destination?.port_id || null;
    if (meta.single_port) {
        set('cableDetailDestination', destDevice ? `${destDevice} / ${destPort || '—'} (porta única)` : '— (porta única)');
    } else {
        set('cableDetailDestination', destDevice ? `${destDevice}${destPort ? ` / ${destPort}` : ''}` : '—');
    }
    set('cableDetailType', meta.cable_type?.name || '—');
    set('cableDetailGroup', meta.cable_group?.name || '—');
    const responsibleLabel = meta.responsible_user?.full_name || meta.responsible_user?.username
        || meta.responsible?.name || '—';
    set('cableDetailResponsible', responsibleLabel);
    set('cableDetailFolder', meta.folder?.name || '—');

    // Estimated optical loss
    const lossRow = document.getElementById('cableDetailLossRow');
    const lossValEl = document.getElementById('cableDetailLossValue');
    const lossWarnEl = document.getElementById('cableDetailLossWarn');
    const attenuation = meta.cable_group?.attenuation_db_per_km;
    const lengthKm = meta.path_length_km ?? meta.length_km;
    if (lossRow && attenuation != null && lengthKm != null) {
        const loss = attenuation * parseFloat(lengthKm);
        if (lossValEl) lossValEl.textContent = `${loss.toFixed(2)} dB`;
        if (lossWarnEl) lossWarnEl.style.display = loss > 30 ? '' : 'none';
        lossRow.style.display = '';
    } else if (lossRow) {
        lossRow.style.display = 'none';
    }
    // Show warning banner if cable has no stored path
    const noPathWarning = document.getElementById('cableNoPathWarning');
    if (noPathWarning) {
        noPathWarning.style.display = (!meta.path || meta.path.length < 2) ? 'block' : 'none';
    }

    // Expose preview state to Vue layer
    window.__ndPreviewCableId = meta.id;
    if (typeof window.__ndOnPreviewFolderChanged === 'function') {
        window.__ndOnPreviewFolderChanged(meta.folder ?? null);
    }
}

/**
 * Select a cable for preview (right-click) without entering edit mode.
 */
async function previewCable(id) {
    try {
        const data = await fetchFiber(id);
        previewCableId = data.id;
        previewCableMeta = data;
        // Hide edit panel, show details panel
        setRoutePointsPanelVisible(false);
        populateCableDetailsPanel(data);
        setCableDetailsPanelVisible(true);
        _setHelpMode('preview');
        updateContextMenuStateWrapper();
    } catch (err) {
        console.error('[previewCable] Error loading cable metadata', err);
        showErrorMessage('Erro ao carregar detalhes do cabo.');
    }
}

/**
 * Clear preview state and hide the details panel.
 */
function _setHelpMode(mode) {
    if (typeof window.__ndSetHelpMode === 'function') window.__ndSetHelpMode(mode);
}

function clearPreview() {
    previewCableId = null;
    previewCableMeta = null;
    window.__ndPreviewCableId = null;
    _setHelpMode('visualizacao');
    if (typeof window.__ndOnPreviewFolderChanged === 'function') {
        window.__ndOnPreviewFolderChanged(null);
    }
    const noPathWarning = document.getElementById('cableNoPathWarning');
    if (noPathWarning) noPathWarning.style.display = 'none';
    setCableDetailsPanelVisible(false);
    if (typeof window.__ndResetCableDetailPos === 'function') window.__ndResetCableDetailPos();
    updateContextMenuStateWrapper();
}

/**
 * Debounce utility
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Validate nearby cables and show warning if found
 */
async function validateNearbyCablesPath(path) {
    if (!path || path.length < 2) return;
    
    try {
        const result = await validateNearbyCables(path, activeFiberId);
        
        // Remove previous warning
        if (nearbyCablesWarningEl) {
            nearbyCablesWarningEl.remove();
            nearbyCablesWarningEl = null;
        }
        
        if (result.has_nearby && result.nearby_cables && result.nearby_cables.length > 0) {
            // Create warning element
            nearbyCablesWarningEl = document.createElement('div');
            nearbyCablesWarningEl.className = 'nearby-cables-warning';
            nearbyCablesWarningEl.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                max-width: 350px;
                background: #fef3c7;
                border: 2px solid #f59e0b;
                border-radius: 0.5rem;
                padding: 1rem;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                z-index: 9999;
                animation: slideIn 0.3s ease-out;
            `;
            
            const cableList = result.nearby_cables.map(c => 
                `<li><strong>${c.name}</strong> - ${c.distance_meters}m away</li>`
            ).join('');
            
            nearbyCablesWarningEl.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                    <strong style="color: #d97706;">⚠️ Nearby Cables Detected</strong>
                    <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #d97706;">&times;</button>
                </div>
                <p style="margin: 0.5rem 0; font-size: 0.875rem; color: #92400e;">
                    This cable path passes very close to existing cables (< ${result.threshold_meters}m):
                </p>
                <ul style="margin: 0.5rem 0; padding-left: 1.5rem; font-size: 0.875rem; color: #92400e;">
                    ${cableList}
                </ul>
                <small style="color: #78350f;">This might indicate duplicate cables or routing errors.</small>
            `;
            
            document.body.appendChild(nearbyCablesWarningEl);
            
            // Auto-dismiss after 10 seconds
            setTimeout(() => {
                if (nearbyCablesWarningEl) {
                    nearbyCablesWarningEl.style.animation = 'slideOut 0.3s ease-in';
                    setTimeout(() => {
                        if (nearbyCablesWarningEl) nearbyCablesWarningEl.remove();
                    }, 300);
                }
            }, 10000);
        }
    } catch (error) {
        console.error('Error validating nearby cables:', error);
    }
}

// Debounced validation (1 second delay to avoid spam)
const debouncedNearbyCablesValidation = debounce(validateNearbyCablesPath, 1000);
const modalDefaultParent = { current: null };
let googleRetryCount = 0;
const GOOGLE_MAX_RETRY = 50;

const getGoogleApiKey = () => {
    if (typeof document === 'undefined') return '';
    return document.querySelector('meta[name="google-maps-api-key"]')?.getAttribute('content')
        || (typeof import.meta !== 'undefined' && import.meta?.env?.VITE_GOOGLE_MAPS_API_KEY) || '';
};

const SEGMENT_INSERT_THRESHOLD_PX = 28;
const ENDPOINT_THRESHOLD_PX = 36;

function resetNetworkDesignState() {
    map = null;
    polyline = null;
    markers = [];
    activeFiberId = null;
    currentFiberMeta = null;
    manualForm = null;
    manualModal = null;
    distanceEl = null;
    manualSinglePortCheckbox = null;
    domBindingsInitialized = false;
    mapsInitStarted = false;
    activeEndpoint = 'end';
    modalDefaultParent.current = null;
    googleRetryCount = 0;
}

function getFullscreenElement() {
    return (
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.mozFullScreenElement ||
        document.msFullscreenElement ||
        null
    );
}

/**
 * Helper to find elements within the page container first, then globally
 */
function findElement(id) {
    const pageContainer = document.querySelector('.network-design-page');
    const element = pageContainer ? pageContainer.querySelector(`#${id}`) : null;
    return element || document.getElementById(id);
}

function syncModalParent() {
    if (!manualModal) {
        manualModal = document.getElementById('manualSaveModal');
    }
    if (manualModal && !modalDefaultParent.current) {
        modalDefaultParent.current = manualModal.parentElement || document.body;
    }
    if (!manualModal) return;
    const fsElement = getFullscreenElement();
    const targetParent = fsElement || modalDefaultParent.current || document.body;
    if (manualModal.parentElement !== targetParent) {
        targetParent.appendChild(manualModal);
    }
    manualModal.style.position = 'fixed';
    manualModal.style.zIndex = '2147483647';
}

function getPixelPoint(lat, lng) {
    const map = getMapInstance();
    if (!map) {
        return null;
    }
    return latLngToPixel(map, lat, lng);
}

async function fetchDeviceOptions() {
    if (deviceOptionsCache) {
        return deviceOptionsCache;
    }
    if (deviceOptionsPromise) {
        return deviceOptionsPromise;
    }

    deviceOptionsPromise = (async () => {
        const response = await fetch('/api/v1/inventory/devices/select-options/', {
            method: 'GET',
            headers: {
                Accept: 'application/json',
                'Cache-Control': 'no-cache',
            },
            credentials: 'same-origin',
            cache: 'no-store',
        });

        if (!response.ok) {
            throw new Error(`Failed to load device options (${response.status})`);
        }

        const data = await response.json();
        const devices = Array.isArray(data.devices) ? data.devices : [];
        deviceOptionsCache = devices;
        return devices;
    })();

    try {
        return await deviceOptionsPromise;
    } finally {
        deviceOptionsPromise = null;
    }
}

async function ensureDeviceOptionsLoaded() {
    try {
        const options = await fetchDeviceOptions();

        window.__FIBER_DEVICE_OPTIONS = options;
        setDeviceOptions(options);

        if (!deviceOptionsDispatched) {
            deviceOptionsDispatched = true;
        }

        document.dispatchEvent(
            new CustomEvent('fiber:device-options-loaded', {
                detail: { devices: options },
            }),
        );

        await refreshDestinationState();
    } catch (error) {
        console.error('[NetworkDesign] Failed to load device options:', error);
    }
}

function resetActiveEndpoint() {
    activeEndpoint = 'end';
}

function determineInsertionAction(lat, lng) {
    const path = getPath();
    if (!map || !path || path.length === 0) {
        return { mode: 'append' };
    }

    const clickPixel = getPixelPoint(lat, lng);
    if (!clickPixel) {
        return { mode: 'append' };
    }

    const startPx = getPixelPoint(path[0].lat, path[0].lng);
    const endPx = getPixelPoint(path[path.length - 1].lat, path[path.length - 1].lng);
    const distToStart = distanceBetweenPixels(clickPixel, startPx);
    const distToEnd = distanceBetweenPixels(clickPixel, endPx);

    if (distToStart <= ENDPOINT_THRESHOLD_PX) {
        activeEndpoint = 'start';
        return { mode: 'select-endpoint' };
    }

    if (distToEnd <= ENDPOINT_THRESHOLD_PX) {
        activeEndpoint = 'end';
        return { mode: 'select-endpoint' };
    }

    let bestInsertIndex = -1;
    let bestDistance = Number.POSITIVE_INFINITY;

    for (let i = 0; i < path.length - 1; i += 1) {
        const startPxSegment = getPixelPoint(path[i].lat, path[i].lng);
        const endPxSegment = getPixelPoint(path[i + 1].lat, path[i + 1].lng);
        const distancePx = distancePointToSegmentPx(clickPixel, startPxSegment, endPxSegment);
        if (distancePx < bestDistance) {
            bestDistance = distancePx;
            bestInsertIndex = i + 1;
        }
    }

    if (bestInsertIndex > 0 && bestDistance <= SEGMENT_INSERT_THRESHOLD_PX) {
        return { mode: 'insert', index: bestInsertIndex };
    }

    return { mode: 'extend', endpoint: activeEndpoint };
}

function extendPathAtEndpoint(lat, lng) {
    const path = getPath();
    if (!path || path.length === 0 || activeEndpoint === 'end') {
        const point = { lat, lng };
        addPoint(lat, lng);
        // Determine type based on current path length
        const currentPath = getPath();
        const markerType = currentPath.length === 1 ? 'origin' : 'destination';
        addMarker(point, markerType);
        return;
    }

    const updated = [{ lat, lng }, ...path];
    setPath(updated);
}

/**
 * Clear map and reset application state
 */
function clearMapAndResetState() {
    activeFiberId = null;
    currentFiberMeta = null;
    updateCableSelect('');
    setPath([]);
    resetActiveEndpoint();
    updateEditButtonState();
}

/**
 * Complete cleanup - removes all DOM elements, listeners and resets state
 * Call this when unmounting the component
 */
function destroyNetworkDesignApp() {
    console.log('[NetworkDesign] Starting complete cleanup...');
    
    // Clear application state
    clearMapAndResetState();
    
    // Cleanup modules — cable polylines MUST be removed before map is destroyed
    // (polylines hold a reference to the map; calling remove() after map.destroy() crashes)
    cleanupCableService();
    cleanupMap();
    cleanupContextMenu();
    cleanupUIHelpers();
    
    // Clear path state
    clearPath();
    
    // Reset local state
    resetNetworkDesignState();
    
    // Clear global references
    delete window.clearMapAndResetState;
    delete window.initMap;
    delete window.loadFibers;
    delete window.cancelFiberEditing;
    delete window.closeManualSaveModal;
    delete window.loadFiberDetail;
    delete window.closeKmlModal;
    
    appInitialized = false;
    globalListenersBound = false;
    
    console.log('[NetworkDesign] Cleanup complete.');
}

/**
 * Setup path change callback - handles UI updates when path changes
 * Includes debug logging for the distance() issue
 */
onPathChange(({ path, distance }) => {
    // Evita executar em rotas onde o DOM da NetworkDesign não existe (ex.: monitoring)
    const container = document.querySelector('.network-design-page');
    if (!container) {
        console.warn('[onPathChange] NetworkDesign container not found, skipping callback.');
        return;
    }

    // DEBUG: verify the type and value of "distance" on entry
    console.log('[DEBUG onPathChange] Received distance - Type:', typeof distance, 'Value:', distance);
    if (currentFiberMeta) {
        currentFiberMeta.path = path.map((point) => ({ ...point }));
    }

    // Update help mode based on current drawing state
    if (path.length > 0) {
        _setHelpMode(activeFiberId ? 'edicao' : 'desenho');
    }

    // Redraw polyline for the currently edited path
    if (polyline) {
        clearPolyline();
    }
    if (path.length > 0) {
        // Use preview color (orange) for new cables, blue for existing cables
        const isPreview = !activeFiberId;
        const polylineOptions = isPreview ? {
            strokeColor: '#f59e0b', // amber-500 (preview)
            strokeWeight: 4,
            strokeOpacity: 0.8,
        } : {
            strokeColor: '#2563eb', // blue-600 (saved)
            strokeWeight: 4,
            strokeOpacity: 0.9,
        };
        
        polyline = drawPolyline(path, polylineOptions);
        // Add right-click to polyline
        if (polyline) {
            attachPolylineRightClick(polyline, ({ clientX, clientY }) => {
                showContextMenu(clientX, clientY);
                updateContextMenuStateWrapper();
            });
        }
        
        // Validate nearby cables (debounced to avoid excessive API calls)
        if (path.length >= 2) {
            debouncedNearbyCablesValidation(path);
        }
    }
    
    // Update distance display (only if element exists)
    const distEl = distanceEl || findElement('distanceKm');
    if (distEl) {
        // Defensive guard: avoid calling toFixed on invalid values
        if (typeof distance === 'number' && !Number.isNaN(distance)) {
            distEl.textContent = distance.toFixed(3);
        } else {
            console.error('[onPathChange] distance is not a valid number', distance);
            distEl.textContent = '---';
            // If this branch triggers, investigate pathState.js and the caller chain.
        }
    }
    
    // Show/hide route points panel based on active editing state
    setRoutePointsPanelVisible(path.length > 0 || !!activeFiberId);

    // Rebuild marker list
    refreshList();

    // Update save button state
    const saveButton = findElement('savePath');
    if (saveButton) {
        const allowSave = (path.length >= 2) || (activeFiberId && path.length === 0);
        saveButton.disabled = !allowSave;
    }

    // Update context menu state
    updateContextMenuStateWrapper();

    // Update optical loss estimate
    _updateLossEstimate(typeof distance === 'number' && !Number.isNaN(distance) ? distance : 0);
});

const _LOSS_THRESHOLD_DB = 30;

function _updateLossEstimate(distanceKm) {
    const lossEl = document.getElementById('manualLossEstimate');
    const lossValEl = document.getElementById('manualLossValue');
    const lossWarnEl = document.getElementById('manualLossWarning');
    if (!lossEl || !lossValEl) return;

    const groupSelect = document.getElementById('manualCableGroupSelect');
    const selectedOpt = groupSelect?.options[groupSelect.selectedIndex];
    const attenuation = selectedOpt ? parseFloat(selectedOpt.dataset.attenuation || '') : NaN;

    if (!isNaN(attenuation) && attenuation > 0 && distanceKm > 0) {
        const loss = attenuation * distanceKm;
        lossValEl.textContent = `${loss.toFixed(2)} dB`;
        lossEl.style.display = '';
        const isWarning = loss > _LOSS_THRESHOLD_DB;
        lossEl.classList.toggle('modal-loss-estimate--warning', isWarning);
        if (lossWarnEl) lossWarnEl.style.display = isWarning ? '' : 'none';
    } else {
        lossEl.style.display = 'none';
    }
}

// REMOVED: clearAllCablesFromMap() - moved into cableService.js
// REMOVED: loadAllCablesForVisualization_local() - replaced by modular cableService version

// Expose function globally for use in import_kml.js
window.clearMapAndResetState = clearMapAndResetState;

// Exposed for admin panel: reload all cables visualization without fitting bounds
window.__ndReloadAllCables = () => loadAllCablesForVisualization({ fitToBounds: false });

updateEditButtonState();

// Legacy functions removed - now using pathState module
// haversineKm and totalDistance are imported from pathState.js

function totalDistance() {
    // Wrapper for compatibility - delegates to imported calculateDistance
    return calculateDistance();
}

// redrawPolyline removed - handled by onPathChange callback

function refreshList() {
    const list = findElement('pointsList');
    if (!list) {
        console.warn('[refreshList] pointsList element not found, skipping.');
        return;
    }
    const currentPath = getPath(); // Get from module
    list.innerHTML = '';
    currentPath.forEach((point, index) => {
        const item = document.createElement('li');
        item.className = 'point-row flex justify-between items-center';
        item.draggable = true;
        item.dataset.idx = index;
        item.innerHTML = `<span>${index + 1}. ${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}</span>`;

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
            if (Number.isInteger(fromIndex) && Number.isInteger(toIndex) && fromIndex !== toIndex) {
                reorderPath(fromIndex, toIndex);
                // No need to call setPath - onPathChange will handle it
            }
        });

        list.appendChild(item);
    });
    // Distance already updated via onPathChange callback
}

// clearMarkers and addMarker now delegate to mapCore module
function clearMarkers() {
    clearAllMarkers();
    markers = []; // Keep local array in sync
}

function addMarker(point, markerType = 'intermediate', removable = true) {
    console.log(`[addMarker] Creating ${markerType} marker at:`, point);
    const marker = createMarker(point, { 
        draggable: true,
        markerType: markerType
    });
    markers.push(marker);
    console.log(`[addMarker] Total markers now: ${markers.length}`);

    marker.addListener('dragend', () => {
        const index = markers.indexOf(marker);
        if (index > -1) {
            const newPos = marker.getPosition();
            // getPosition() returns {lat, lng} as plain numbers (provider-agnostic)
            const lat = typeof newPos.lat === 'function' ? newPos.lat() : newPos.lat;
            const lng = typeof newPos.lng === 'function' ? newPos.lng() : newPos.lng;
            updatePoint(index, lat, lng);
            // onPathChange callback will redraw
        }
    });

    if (removable) {
        const removeMarkerHandler = () => {
            const index = markers.indexOf(marker);
            if (index > -1) {
                console.log(`[addMarker] Removing marker #${index}`);
                markers.splice(index, 1);
                removePoint(index);
                removeMarker(marker);
                // onPathChange callback will redraw
            }
        };

        marker.addListener('dblclick', removeMarkerHandler);
        marker.addListener('rightclick', removeMarkerHandler);
    }

    return marker;
}

// setPath now syncs markers with path from module
function setPath(points) {
    clearMarkers();
    setPathState(points);
    const currentPath = getPath();
    currentPath.forEach((point, index) => {
        // Determine marker type based on position
        let markerType = 'intermediate';
        if (index === 0) {
            markerType = 'origin';
        } else if (index === currentPath.length - 1) {
            markerType = 'destination';
        }
        addMarker(point, markerType);
    });
    // onPathChange callback will handle polyline drawing
}

function initMap() {
    map = initializeMap('builderMap', {
        center: { lat: -16.6869, lng: -49.2648 },
        zoom: 6,
        mapTypeId: 'terrain',
    });

    if (!map) {
        console.error("Failed to initialize the map.");
        showErrorMessage("Could not load the map.");
        return;
    }

    // Initialize cableService only after the map exists and makeCableEditable is defined
    // It is critical that makeCableEditable is configured before this invocation.
    initCableService({
        makeEditableCallback: makeCableEditable, // Pass local callback
        map: map // Provide the map instance
    });
    console.log("[initMap] cableService initialized.");

    // Setup click handler via mapCore
    onMapClick(({ lat, lng }) => {
        hideContextMenu();
        
        // Store last map click for proximity sorting in device autocomplete
        window.__lastMapClick = { lat, lng };
        
        const currentPath = getPath();
        if (activeFiberId && currentPath.length === 0) {
            activeFiberId = null;
            const fiberSelect = document.getElementById('fiberSelect');
            if (fiberSelect) {
                fiberSelect.value = '';
            }
        }
        const action = determineInsertionAction(lat, lng);
        if (action.mode === 'select-endpoint') {
            return;
        }
        if (action.mode === 'insert' && typeof action.index === 'number') {
            const updated = currentPath.slice();
            updated.splice(action.index, 0, { lat, lng });
            setPath(updated);
            return;
        }
        extendPathAtEndpoint(lat, lng);
        return;
    });
    
    // Setup right-click handler via mapCore
    onMapRightClick(({ clientX, clientY }) => {
        showContextMenu(clientX, clientY);
        updateContextMenuStateWrapper();
    });
    
    loadFibers();
    // Load visualization of all cables using the MODULAR function
    setTimeout(() => {
        if (map) {
            console.log("[initMap] Map ready, calling cableService.loadAllCablesForVisualization.");
            loadAllCablesForVisualization({ fitToBounds: true });
        } else {
            console.warn('[initMap] Map not ready for loadAllCablesForVisualization. Retrying...');
            setTimeout(() => {
                 if(getMapInstance()) { // Usa getMapInstance de mapCore para verificar
                      console.log("[initMap Retry] Map ready, calling cableService.loadAllCablesForVisualization.");
                      loadAllCablesForVisualization({ fitToBounds: true });
                 } else {
                      console.error("[initMap Retry] Map still not ready after delay.");
                 }
            }, 1000);
        }
    }, 500);
}

// Context menu wrapper - delegates to module with current app state
function updateContextMenuStateWrapper() {
    const state = {
        hasActiveFiber: !!activeFiberId,
        fiberMeta: currentFiberMeta,
        pathLength: getPath().length,
        previewCableId,
        previewCableMeta,
    };
    updateContextMenuState(state);
}

/**
 * Callback function passed to cableService.
 * Attaches the right-click listener to a cable polyline.
 * This function must stay within fiber_route_builder.js
 * because it calls loadFiberDetail, showContextMenu, and other local helpers.
 * @param {google.maps.Polyline} cablePolyline - The polyline object.
 * @param {number|string} cableId - The ID of the cable.
 * @param {string} cableName - The name of the cable.
 */
function makeCableEditable(cablePolyline, cableId, cableName) {
    if (!cablePolyline || typeof cablePolyline.addListener !== 'function') {
        console.error(`[makeCableEditable] Invalid polyline received for cable ID ${cableId}`);
        return;
    }
    
    // Store cable ID in polyline for later reference
    cablePolyline.set('cableId', cableId);
    cablePolyline.set('cableName', cableName);
    
    // Right-click on cable to load + open menu
    cablePolyline.addListener('rightclick', async (event) => {
        if (event.domEvent && typeof event.domEvent.stopPropagation === 'function') {
            event.domEvent.stopPropagation();
        } else if (typeof event.stop === 'function') {
             event.stop();
        }

        console.log(`[Polyline RightClick] Clicked on cable ID ${cableId}. Loading details...`);
        
        // Update dropdown
        const fiberSelect = document.getElementById('fiberSelect');
        if (fiberSelect) {
            fiberSelect.value = String(cableId);
        }
        
        try {
            // Load cable for preview (no edit mode)
            await previewCable(cableId);

            // Show context menu
            const clickPos = event.domEvent
                ? { clientX: event.domEvent.clientX, clientY: event.domEvent.clientY }
                : { clientX: 0, clientY: 0 };
            showContextMenu(clickPos.clientX, clickPos.clientY);
            updateContextMenuStateWrapper();

        } catch (error) {
            console.error(`[Polyline RightClick] Error loading details for cable ID ${cableId}:`, error);
            showErrorMessage(`Failed to load details for cable ${cableName}.`);
        }
    });
}

// Helper function to reload visualization with click handlers
/**
 * Reloads every cable on the map.
 * Delegates to loadAllCablesForVisualization() from the cableService module.
 */
async function reloadCableVisualization(options = {}) {
    const { fitToBounds = true } = options;
    console.log('[reloadCableVisualization] Delegating to cableService.loadAllCablesForVisualization()...', { fitToBounds });
    await loadAllCablesForVisualization({ fitToBounds });
}

// Make initMap available globally for Google Maps callback (legacy support)
try {
    window.initMap = initMap;
    console.log('[Global] window.initMap assigned successfully');
} catch (e) {
    console.error('[Global] Failed to assign window.initMap:', e);
}

// Module load self-check
console.log('[SelfCheck] Modules loaded:', {
    hasPathState: typeof getPath === 'function',
    hasMapCore: typeof initializeMap === 'function',
    hasCableService: typeof initCableService === 'function'
});

// Initialize map when Google Maps API is ready
function waitForGoogleMaps() {
    const key = getGoogleApiKey();
    if (!key) {
        console.warn('[waitForGoogleMaps] Google Maps API key not configured; skipping init.');
        return;
    }
    if (googleRetryCount > GOOGLE_MAX_RETRY) {
        console.error('[waitForGoogleMaps] Google Maps API not ready after retries, giving up.');
        return;
    }
    if (typeof google !== 'undefined' && google.maps) {
        console.log('[waitForGoogleMaps] Google Maps API is ready, calling initMap()');
        try {
            initMap();
        } catch (e) {
            console.error('[waitForGoogleMaps] Error calling initMap():', e);
        }
    } else {
        googleRetryCount += 1;
        console.log('[waitForGoogleMaps] Google Maps API not ready yet, retrying...', googleRetryCount);
        setTimeout(waitForGoogleMaps, 150);
    }
}

async function startGoogleMapsWatcher() {
    if (mapsInitStarted) {
        return;
    }
    mapsInitStarted = true;

    // Check configured map provider; only wait for Google when provider is 'google'
    let provider = 'google';
    try {
        provider = await getCurrentProviderName();
    } catch (e) {
        console.warn('[startGoogleMapsWatcher] Could not detect provider, assuming google:', e);
    }

    if (provider !== 'google') {
        console.log(`[startGoogleMapsWatcher] Provider is '${provider}', calling initMap() directly.`);
        try {
            await initMap();
        } catch (e) {
            console.error('[startGoogleMapsWatcher] Error calling initMap():', e);
        }
        return;
    }

    waitForGoogleMaps();
}

async function loadFibers() {
    try {
        const data = await fetchFibers();
        const select = document.getElementById('fiberSelect');
        if (select) {
            select.innerHTML = '<option value="">-- select a cable --</option>';
            const cables = (data && (data.fibers || data.cables)) ? (data.fibers || data.cables) : [];
            cables.forEach((cable) => {
                const option = document.createElement('option');
                option.value = cable.id;
                option.textContent = cable.name;
                select.appendChild(option);
            });
        }
        return data;
    } catch (error) {
        console.error('Error fetching fibers:', error);
        return null;
    }
}

// Expose function globally for use in import_kml.js
window.loadFibers = loadFibers;

async function loadFiberDetail(id) {
    try {
        const data = await fetchFiber(id);
        console.log(`[loadFiberDetail] Loaded cable #${id}:`, data);
        activeFiberId = data.id;
        // Entering edit mode — clear preview state
        previewCableId = null;
        previewCableMeta = null;
        setCableDetailsPanelVisible(false);
        setRoutePointsPanelVisible(true);
        _setHelpMode('edicao');
        currentFiberMeta = {
            id: data.id,
            name: data.name || '',
            origin_device_id: data.origin?.device_id || null,
            origin_port_id: data.origin?.port_id || null,
            dest_device_id: data.destination?.device_id || null,
            dest_port_id: data.destination?.port_id || null,
            single_port: Boolean(data.single_port),
            cable_group: data.cable_group || null,
            responsible: data.responsible || null,
        };
        resetActiveEndpoint();
        updateEditButtonState();
        const path = (data.path && data.path.length) ? data.path : buildDefaultFromEndpoints(data);
        currentFiberMeta.path = path.map((point) => ({ ...point }));
        removeCableVisualization(data.id);
        console.log(`[loadFiberDetail] Setting path with ${path.length} points:`, path);
        setPath(path);
        console.log(`[loadFiberDetail] Created ${markers.length} markers`);
        if (path && path.length > 0) {
            fitMapToBounds(path);
        }
        await loadAllCablesForVisualization({ excludeCableId: data.id, fitToBounds: false });
    } catch (err) {
        console.error('Error loading cable', err);
        showErrorMessage('Erro ao carregar o cabo.');
    }
}

async function cancelEditing() {
    closeManualSaveModal();
    hideContextMenu();
    clearMapAndResetState();
    setRoutePointsPanelVisible(false);
    clearPreview();
    await reloadCableVisualization({ fitToBounds: true });
    refreshList();
    updateContextMenuStateWrapper();
}

window.cancelFiberEditing = cancelEditing;
export { cancelEditing as cancelNetworkDesignEditing };
export { handleSaveClick as saveNetworkDesignRoute };



async function openEditFiberModal() {
    if (!activeFiberId || !currentFiberMeta) {
        showErrorMessage('Select a cable first.');
        return;
    }

    openManualSaveModal(true);  // loads groups/responsibles/folders (async, non-blocking)
    syncModalParent();
    resetModalTabs();
    await ensureDeviceOptionsLoaded();
    await openModalForEdit(currentFiberMeta, totalDistance());
    // Pre-select cable group, responsible and folder after modal is populated
    const groupSelect = document.getElementById('manualCableGroupSelect');
    if (groupSelect && currentFiberMeta?.cable_group?.id) {
        groupSelect.value = String(currentFiberMeta.cable_group.id);
    }
    const responsibleSelect = document.getElementById('manualResponsibleSelect');
    if (responsibleSelect && currentFiberMeta?.responsible_user?.id) {
        responsibleSelect.value = String(currentFiberMeta.responsible_user.id);
    }
    const folderSelect = document.getElementById('manualFolderSelect');
    if (folderSelect && currentFiberMeta?.folder?.id) {
        folderSelect.value = String(currentFiberMeta.folder.id);
    }
    _updateLossEstimate(currentFiberMeta?.path_length_km || totalDistance());
}

/**
 * Open the metadata modal for a cable that is in preview mode (not in route-edit mode).
 * Sets activeFiberId/currentFiberMeta temporarily from preview state so the existing
 * save mechanism works, without drawing path markers or entering route-edit mode.
 */
async function openMetadataModalForPreview() {
    if (!previewCableId || !previewCableMeta) return;

    // Temporarily promote preview state to active so openEditFiberModal can read it.
    // Normalize nested API response to the flat format expected by openModalForEdit.
    const data = previewCableMeta;
    activeFiberId = previewCableId;
    currentFiberMeta = {
        id: data.id,
        name: data.name || '',
        origin_device_id: data.origin?.device_id || null,
        origin_port_id: data.origin?.port_id || null,
        dest_device_id: data.destination?.device_id || null,
        dest_port_id: data.destination?.port_id || null,
        single_port: Boolean(data.single_port),
        cable_group: data.cable_group || null,
        responsible: data.responsible || null,
        responsible_user: data.responsible_user || null,
        folder: data.folder || null,
        cable_type: data.cable_type || '',
        path: data.path || [],
        path_length_km: data.path_length_km || 0,
    };
    metadataOnlyEdit = true;

    openManualSaveModal(true);  // loads groups/responsibles/folders (async, non-blocking)
    syncModalParent();
    resetModalTabs();
    await ensureDeviceOptionsLoaded();
    await openModalForEdit(currentFiberMeta, previewCableMeta.path_length_km ?? 0);

    const groupSelect = document.getElementById('manualCableGroupSelect');
    if (groupSelect && currentFiberMeta?.cable_group?.id) {
        groupSelect.value = String(currentFiberMeta.cable_group.id);
    }
    const responsibleSelect = document.getElementById('manualResponsibleSelect');
    if (responsibleSelect && currentFiberMeta?.responsible_user?.id) {
        responsibleSelect.value = String(currentFiberMeta.responsible_user.id);
    }
    const folderSelect = document.getElementById('manualFolderSelect');
    if (folderSelect && currentFiberMeta?.folder?.id) {
        folderSelect.value = String(currentFiberMeta.folder.id);
    }
    _updateLossEstimate(currentFiberMeta?.path_length_km || totalDistance());
}

function buildDefaultFromEndpoints(fiber) {
    const points = [];
    if (fiber.origin.lat != null && fiber.origin.lng != null) {
        points.push({ lat: fiber.origin.lat, lng: fiber.origin.lng });
    }
    if (fiber.destination.lat != null && fiber.destination.lng != null) {
        points.push({ lat: fiber.destination.lat, lng: fiber.destination.lng });
    }
    return points;
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

async function updateExistingPath() {
    if (!activeFiberId) return;
    try {
        const pathPayload = { path: getPath() };
        const result = await updateFiber(activeFiberId, pathPayload);
        showSuccessMessage(`Route updated successfully. Points: ${result.points}, distance: ${result.length_km} km.`);
        clearMapAndResetState();
        await loadFibers();
        await loadAllCablesForVisualization({ fitToBounds: true });
    } catch (error) {
        console.error('Request error:', error);
        showErrorMessage('Connection failure or unexpected error while saving.');
    }
}

// Modal management wrappers - delegate to modalEditor module
function resetModalTabs() {
    // Switch back to first tab whenever the modal is opened
    const tabs = ['tabBtnIdentification', 'tabBtnConnections'];
    const panels = ['tabPanelIdentification', 'tabPanelConnections'];
    tabs.forEach((id, i) => {
        const btn = document.getElementById(id);
        const panel = document.getElementById(panels[i]);
        if (btn) {
            btn.classList.toggle('active', i === 0);
            btn.setAttribute('aria-selected', String(i === 0));
        }
        if (panel) panel.classList.toggle('hidden', i !== 0);
    });
}

function openManualSaveModal(skipReset = false) {
    syncModalParent();
    resetModalTabs();
    // Reload groups and responsibles each time (keeps lists fresh after inline creation)
    const select = document.getElementById('manualCableGroupSelect');
    if (select) {
        const currentVal = select.value;
        fetch('/api/v1/inventory/cable-groups/', { credentials: 'same-origin' })
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (!data) return;
                select.innerHTML = '<option value="">— Sem grupo —</option>';
                (data.results || []).forEach(g => {
                    const opt = document.createElement('option');
                    opt.value = g.id;
                    opt.textContent = g.name + (g.manufacturer ? ` (${g.manufacturer})` : '');
                    if (g.attenuation_db_per_km != null) {
                        opt.dataset.attenuation = g.attenuation_db_per_km;
                    }
                    select.appendChild(opt);
                });
                // In edit mode (skipReset) use meta only; in create mode preserve currentVal
                const targetId = skipReset
                    ? String(currentFiberMeta?.cable_group?.id || '')
                    : String(currentVal || '');
                if (targetId) select.value = targetId;
                const dist = currentFiberMeta?.path_length_km || totalDistance();
                _updateLossEstimate(dist);
            })
            .catch(() => {});
        if (!select._lossListenerAttached) {
            select._lossListenerAttached = true;
            select.addEventListener('change', () => {
                const dist = currentFiberMeta?.path_length_km || totalDistance();
                _updateLossEstimate(dist);
            });
        }
    }
    const rSelect = document.getElementById('manualResponsibleSelect');
    if (rSelect) {
        const currentVal = rSelect.value;
        fetch('/api/users/?is_active=true', { credentials: 'same-origin' })
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (!data) return;
                rSelect.innerHTML = '<option value="">— Sem responsável —</option>';
                (data.users || []).forEach(u => {
                    const opt = document.createElement('option');
                    opt.value = u.id;
                    opt.textContent = u.full_name || u.username;
                    rSelect.appendChild(opt);
                });
                const targetResponsibleId = skipReset
                    ? String(currentFiberMeta?.responsible_user?.id || '')
                    : String(currentVal || '');
                if (targetResponsibleId) rSelect.value = targetResponsibleId;
            })
            .catch(() => {});
    }
    const fSelect = document.getElementById('manualFolderSelect');
    if (fSelect) {
        const currentVal = fSelect.value;
        fetch('/api/v1/inventory/cable-folders/', { credentials: 'same-origin' })
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (!data) return;
                fSelect.innerHTML = '<option value="">— Sem pasta —</option>';
                function appendFolderOptions(nodes, prefix) {
                    (nodes || []).forEach(node => {
                        const opt = document.createElement('option');
                        opt.value = node.id;
                        opt.textContent = prefix + node.name;
                        fSelect.appendChild(opt);
                        appendFolderOptions(node.children, prefix + '\u00a0\u00a0\u00a0');
                    });
                }
                appendFolderOptions(data.tree, '');
                const targetFolderId = skipReset
                    ? String(currentFiberMeta?.folder?.id || '')
                    : String(currentVal || '');
                if (targetFolderId) fSelect.value = targetFolderId;
            })
            .catch(() => {});
    }
    _loadTypeSelect(skipReset);
    if (skipReset) {
        // Editing mode - modal already populated by openModalForEdit
        return;
    }
    void ensureDeviceOptionsLoaded();
    openModalForCreate(totalDistance());
}

function _loadTypeSelect(skipReset = false) {
    const tSelect = document.getElementById('manualCableTypeSelect');
    if (!tSelect) return;
    const currentVal = tSelect.value;
    fetch('/api/v1/inventory/cable-types/', { credentials: 'same-origin' })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            if (!data) return;
            tSelect.innerHTML = '<option value="">— Sem tipo —</option>';
            (data.results || []).forEach(t => {
                const opt = document.createElement('option');
                opt.value = t.id;
                opt.textContent = t.name;
                tSelect.appendChild(opt);
            });
            const targetTypeId = skipReset
                ? String(currentFiberMeta?.cable_type?.id || '')
                : String(currentVal || '');
            if (targetTypeId) tSelect.value = targetTypeId;
        })
        .catch(() => {});
}

// Expose so Vue admin panel can reload after CRUD
window.__ndReloadCableTypes = () => _loadTypeSelect(true);

function closeManualSaveModal() {
    // If canceling a metadata-only edit, clean up the promoted state
    if (metadataOnlyEdit) {
        metadataOnlyEdit = false;
        activeFiberId = null;
        currentFiberMeta = null;
    }
    closeModal();
    if (!getFullscreenElement() && modalDefaultParent.current && manualModal?.parentElement !== modalDefaultParent.current) {
        modalDefaultParent.current.appendChild(manualModal);
    }
}

// Legacy functions removed - now handled by modalEditor module
// All device/port loading logic moved to modalEditor.js
// Legacy functions kept only for external compatibility if needed

async function performCreateFiber(payload) {
    try {
        const data = await createFiberManual(payload);
        showSuccessMessage('Cable created successfully.');
        closeManualSaveModal();
        document.dispatchEvent(new CustomEvent('fiber:cable-created', { detail: { fiberId: data.fiber_id } }));
        await reloadCableVisualization({ fitToBounds: true });
        await loadFibers(); // Reload dropdown
    } catch (error) {
        console.error('Error creating cable:', error);
        throw error;
    }
}

async function performUpdateFiber(fiberId, payload) {
    const wasMetadataOnly = metadataOnlyEdit;
    metadataOnlyEdit = false;
    try {
        await updateFiber(fiberId, payload);
        showSuccessMessage('Cable updated successfully.');
        closeManualSaveModal();
        if (wasMetadataOnly) {
            // Came from preview panel: reset active state but keep map clean
            activeFiberId = null;
            currentFiberMeta = null;
            clearPreview();
        } else {
            clearMapAndResetState();
        }
        await loadFibers();
        await reloadCableVisualization({ fitToBounds: false });
    } catch (error) {
        metadataOnlyEdit = wasMetadataOnly; // restore on error
        console.error('Error updating cable:', error);
        throw error;
    }
}

async function handleManualFormSubmit(event) {
    event.preventDefault();
    const editingFiberId = getEditingFiberId();
    const isEditing = Boolean(editingFiberId);
    const path = getPath();

    if (!isEditing && path.length < 2) {
        showErrorMessage('Adicione pelo menos dois pontos no mapa antes de salvar a rota.');
        return;
    }

    // Validate all fields in real-time
    const isValid = await validateAllFields();
    if (!isValid) {
        showErrorMessage('Corrija os erros de validação antes de salvar.');
        return;
    }

    const formData = new FormData(manualForm);
    const singlePortCheckbox = manualSinglePortCheckbox || document.getElementById('manualSinglePortOnly');
    const singlePort = singlePortCheckbox && singlePortCheckbox.checked;

    const cableGroupRaw = formData.get('cable_group_id');
    const responsibleRaw = formData.get('responsible_user_id');
    const folderRaw = formData.get('folder_id');
    const cableTypeRaw = formData.get('cable_type_id');
    const payload = {
        name: (formData.get('name') || '').trim(),
        cable_group_id: cableGroupRaw ? parseInt(cableGroupRaw, 10) : null,
        responsible_user_id: responsibleRaw ? parseInt(responsibleRaw, 10) : null,
        folder_id: folderRaw ? parseInt(folderRaw, 10) : null,
        cable_type_id: cableTypeRaw ? parseInt(cableTypeRaw, 10) : null,
        origin_device_id: formData.get('origin_device_id'),
        origin_port_id: formData.get('origin_port_id'),
        dest_device_id: singlePort
            ? formData.get('origin_device_id')
            : formData.get('dest_device_id'),
        dest_port_id: singlePort ? formData.get('origin_port_id') : formData.get('dest_port_id'),
        single_port: singlePort,
    };

    if (!payload.name || !payload.origin_device_id || !payload.origin_port_id) {
        showErrorMessage('Preencha todos os campos obrigatórios.');
        return;
    }
    if (!singlePort && !payload.dest_port_id) {
        showErrorMessage('Preencha todos os campos obrigatórios.');
        return;
    }

    // When editing metadata only (from preview panel), do NOT include path in the
    // payload so the backend skips update_fiber_path and preserves the stored path.
    // Only include path when actually editing the route.
    if (!metadataOnlyEdit) {
        payload.path = path.map((point) => ({ lat: point.lat, lng: point.lng }));
    }

    const submitButton = manualForm.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = true;

    try {
        if (isEditing && editingFiberId) {
            if (currentFiberMeta) {
                currentFiberMeta.single_port = singlePort;
                currentFiberMeta.origin_device_id = payload.origin_device_id;
                currentFiberMeta.origin_port_id = payload.origin_port_id;
                currentFiberMeta.dest_device_id = payload.dest_device_id;
                currentFiberMeta.dest_port_id = payload.dest_port_id;
            }
            await performUpdateFiber(editingFiberId, payload);
        } else {
            await performCreateFiber(payload);
        }
    } catch (error) {
        console.error('Error saving route:', error);
        const rawMessage = (error && error.message) ? String(error.message) : '';
        let friendlyMessage = rawMessage || 'Unable to save the route.';
        if (/duplicate entry/i.test(rawMessage)) {
            friendlyMessage = 'A cable with this name already exists. Please choose a different name.';
        } else if (/erro interno do servidor/i.test(rawMessage) || /internal server error/i.test(rawMessage)) {
            friendlyMessage = 'Error saving the route. Ensure the name is unique and required fields are filled.';
        }
        showErrorMessage(friendlyMessage);
    } finally {
        if (submitButton) submitButton.disabled = false;
    }
}
function handleSaveClick() {
    if (activeFiberId) {
        updateExistingPath();
        return;
    }
    if (getPath().length < 2) {
        showErrorMessage('Add at least two points to the map before saving the route.');
        return;
    }
    openManualSaveModal();
}

// Note: deleteCable is imported from cableService.js
// Do not redeclare it here to avoid "Identifier already declared" error

function initializeDomBindings() {
    if (domBindingsInitialized) {
        return;
    }
    domBindingsInitialized = true;

    // Initialize DOM elements
    manualForm = findElement('manualSaveForm');
    manualModal = findElement('manualSaveModal');
    distanceEl = findElement('distanceKm');
    manualSinglePortCheckbox = findElement('manualSinglePortOnly');
    if (!modalDefaultParent.current && manualModal) {
        modalDefaultParent.current = manualModal.parentElement || document.body;
    }
    
    console.log('[NetworkDesign] DOM elements initialized:', {
        manualForm: !!manualForm,
        manualModal: !!manualModal,
        distanceEl: !!distanceEl,
        manualSinglePortCheckbox: !!manualSinglePortCheckbox
    });
    
    // Initialize modules
    initContextMenu();
    initModalEditor();
    
    // Collapse button for route points panel
    document.getElementById('toggleRoutePoints')?.addEventListener('click', () => {
        const panel = document.getElementById('routePointsPanel');
        const body = document.getElementById('routePointsPanelBody');
        if (panel) {
            panel.classList.toggle('collapsed');
            const isCollapsed = panel.classList.contains('collapsed');
            document.getElementById('toggleRoutePoints')?.setAttribute('aria-expanded', String(!isCollapsed));
            body?.setAttribute('aria-hidden', String(isCollapsed));
        }
    });

    
    document.getElementById('manualCancelButton')?.addEventListener('click', async () => {
        await cancelEditing();
    });
    
    // Context menu - Preview options (cable right-clicked, not editing)
    document.getElementById('contextViewDetails')?.addEventListener('click', () => {
        hideContextMenu();
        setCableDetailsPanelVisible(true);
    });

    document.getElementById('contextViewPhotos')?.addEventListener('click', () => {
        hideContextMenu();
        setCableDetailsPanelVisible(true);
        // Switch to Photos tab after panel is visible
        setTimeout(() => document.getElementById('tabBtnPhotos')?.click(), 50);
    });

    document.getElementById('contextEditMetaPreview')?.addEventListener('click', () => {
        hideContextMenu();
        if (previewCableId) openEditFiberModal();
    });

    document.getElementById('contextStartEdit')?.addEventListener('click', async () => {
        hideContextMenu();
        if (previewCableId) {
            await loadFiberDetail(previewCableId);
        }
    });

    document.getElementById('contextDeletePreview')?.addEventListener('click', async () => {
        hideContextMenu();
        if (!previewCableId || !previewCableMeta) return;
        const confirmed = await showConfirmDialog(
            `Excluir cabo "${previewCableMeta.name || `#${previewCableId}`}"?`,
            'Esta ação não pode ser desfeita.',
        );
        if (!confirmed) return;
        try {
            await deleteCable(previewCableId);
            clearPreview();
            showSuccessMessage('Cabo excluído.');
            await reloadCableVisualization({ fitToBounds: false });
        } catch (err) {
            showErrorMessage('Erro ao excluir o cabo.');
        }
    });

    // Cable Details panel buttons
    document.getElementById('closeCableDetails')?.addEventListener('click', () => {
        clearPreview();
    });

    document.getElementById('cableDetailMetaBtn')?.addEventListener('click', async () => {
        if (previewCableId) {
            await openMetadataModalForPreview();
        }
    });

    document.getElementById('cableDetailEditBtn')?.addEventListener('click', async () => {
        if (previewCableId) {
            await loadFiberDetail(previewCableId);
        }
    });

    document.getElementById('cableDetailDeleteBtn')?.addEventListener('click', async () => {
        if (!previewCableId || !previewCableMeta) return;
        const confirmed = await showConfirmDialog(
            `Excluir cabo "${previewCableMeta.name || `#${previewCableId}`}"?`,
            'Esta ação não pode ser desfeita.',
        );
        if (!confirmed) return;
        try {
            await deleteCable(previewCableId);
            clearPreview();
            showSuccessMessage('Cabo excluído.');
            await reloadCableVisualization({ fitToBounds: false });
        } catch (err) {
            showErrorMessage('Erro ao excluir o cabo.');
        }
    });

    // Context menu - General options
    document.getElementById('contextLoadAll')?.addEventListener('click', () => {
        hideContextMenu();
        if (activeFiberId) {
            // Reload only current cable
            loadFiberDetail(activeFiberId);
        } else {
            // Reload all cables
            loadAllCablesForVisualization({ fitToBounds: true });
        }
    });
    
    document.getElementById('contextImportKML')?.addEventListener('click', () => {
        hideContextMenu();
        openKmlModal();
    });
    
    // Context menu - Conditional options (cable selected)
    // REMOVED: contextEditPath - path editing is already available via right-click menu
    
    document.getElementById('contextEditCable')?.addEventListener('click', () => {
        hideContextMenu();
        if (activeFiberId) {
            openEditFiberModal();
        }
    });
    
    document.getElementById('contextSavePath')?.addEventListener('click', () => {
        hideContextMenu();
        if (activeFiberId && getPath().length >= 2) {
            handleSaveClick();
        }
    });
    
    document.getElementById('contextCancelEdit')?.addEventListener('click', async () => {
        hideContextMenu();
        await cancelEditing();
    });
    
    document.getElementById('contextDeleteCable')?.addEventListener('click', async () => {
        hideContextMenu();
        if (!activeFiberId) {
            showErrorMessage('No cable selected for deletion.');
            return;
        }
        
        const cableLabel = currentFiberMeta?.name || activeFiberId;
        const confirmed = await showConfirmDialog({
            title: 'Excluir cabo',
            description: `Delete cable "${cableLabel}"? This action cannot be undone.`,
            confirmText: 'Excluir',
            cancelText: 'Cancelar',
            tone: 'danger',
        });

        if (confirmed) {
            console.log(`[contextDeleteCable] Deleting active cable ID ${activeFiberId}.`);
            try {
                // Chama deleteCable do service, passando callbacks para atualizar a UI localmente
                await deleteCable(activeFiberId, {
                    onSuccess: async () => {
                        showSuccessMessage(`Cable ${cableLabel} deleted.`);
                        // The polyline has already been removed by cableService
                        // Apenas resetamos o estado local e recarregamos a lista
                        const currentSelectedValue = activeFiberId; // Guarda antes de limpar
                        clearMapAndResetState(); // Clear editing path and related state
                        await loadFibers(); // Recarrega dropdown
                        // Opcional: Se o select ainda mostrar o ID apagado, limpe-o aqui
                        const select = document.getElementById('fiberSelect');
                        if (select && select.value === String(currentSelectedValue)) {
                            select.value = '';
                        }
                        await reloadCableVisualization({ fitToBounds: true });
                    },
                    onError: (error) => {
                        showErrorMessage(`Falha ao remover o cabo: ${error.message || 'Erro desconhecido'}.`);
                    }
                });
            } catch(e) {
                console.error(`[contextDeleteCable] Unexpected error:`, e);
                showErrorMessage(`Error during deletion: ${e.message}`);
            }
        } else {
            console.log(`[contextDeleteCable] Deletion cancelled.`);
        }
    });
    
    // Context menu options when creating a new cable
    document.getElementById('contextSaveNewCable')?.addEventListener('click', () => {
        console.log('[contextSaveNewCable] Button clicked, path length:', getPath().length);
        hideContextMenu();
        if (getPath().length >= 2) {
            console.log('[contextSaveNewCable] Opening modal to assign cable...');
            openManualSaveModal(false); // false = creating a new cable
        } else {
            showErrorMessage('Draw at least two points on the map before creating a cable.');
        }
    });

    document.getElementById('contextClearNew')?.addEventListener('click', () => {
        hideContextMenu();
        // Reset drawn points
        clearPath();
        clearAllMarkers();
        clearPolyline();
        // onPathChange callback will handle UI updates
        refreshList();
    });

    if (!globalListenersBound) {
        ['fullscreenchange', 'webkitfullscreenchange', 'mozfullscreenchange', 'MSFullscreenChange'].forEach((eventName) => {
            document.addEventListener(eventName, syncModalParent);
        });

        // Hide context menu when clicking outside
        document.addEventListener('click', (e) => {
            const menu = document.getElementById('contextMenu');
            if (menu && !menu.contains(e.target)) {
                hideContextMenu();
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                if (isModalOpen()) {
                    cancelEditing().catch((err) => console.error('[cancelEditing] Error on ESC (modal open):', err));
                    event.preventDefault();
                    return;
                }
                if (activeFiberId || getPath().length > 0) {
                    cancelEditing().catch((err) => console.error('[cancelEditing] Error on ESC (editing active):', err));
                    event.preventDefault();
                    return;
                }
                if (previewCableId) {
                    clearPreview();
                    event.preventDefault();
                    return;
                }
                hideContextMenu();
            }
        });

        document.addEventListener('fiber:single-port-toggle', (event) => {
            if (currentFiberMeta) {
                currentFiberMeta.single_port = Boolean(event.detail?.enabled);
            }
        });

        document.addEventListener('fiber:cable-created', async (event) => {
            const fiberId = event.detail?.fiberId;
            
            // Clear the map and reset application state
            clearMapAndResetState();
            
            // Reload cable list
            await loadFibers();
            
            // Refresh visualization for all cables on the map
            await loadAllCablesForVisualization({ fitToBounds: true });
            
            if (fiberId) {
                console.info(`New cable created: ${fiberId}`);
            }
        });

        globalListenersBound = true;
    }

    // Legacy load button removed from layout; listener kept for safety
    document.getElementById('loadFiber')?.addEventListener('click', () => {
        const id = document.getElementById('fiberSelect')?.value;
        if (!id) {
            showErrorMessage('Select a cable first.');
            return;
        }
        loadFiberDetail(id);
    });

    // Clear button now lives inside the context menu

    // Cable autoload moved to initMap to guarantee the map exists
    
    // Event listeners antigos removidos (savePath, deleteCable, editFiber)
    // All actions now flow through the context menu
    
    // ── Tab switching ─────────────────────────────────────────
    const TAB_IDS = ['tabBtnIdentification', 'tabBtnConnections', 'tabBtnHistory', 'tabBtnPhotos'];
    const PANEL_IDS = ['tabPanelIdentification', 'tabPanelConnections', 'tabPanelHistory', 'tabPanelPhotos'];

    function activateTab(tabId) {
        TAB_IDS.forEach((id, i) => {
            const btn = document.getElementById(id);
            const panel = document.getElementById(PANEL_IDS[i]);
            const isActive = id === tabId;
            if (btn) {
                btn.classList.toggle('active', isActive);
                btn.setAttribute('aria-selected', String(isActive));
            }
            if (panel) panel.classList.toggle('hidden', !isActive);
        });
        if (tabId === 'tabBtnHistory') {
            loadAuditLog();
        }
        if (tabId === 'tabBtnPhotos') {
            loadPhotos();
        }
    }

    async function loadAuditLog() {
        const listEl = document.getElementById('auditLogList');
        if (!listEl) return;
        const editingId = getEditingFiberId();
        if (!editingId) {
            listEl.innerHTML = '<p class="audit-log-empty">Salve o cabo primeiro para ver o histórico.</p>';
            return;
        }
        listEl.innerHTML = '<p class="audit-log-loading">Carregando…</p>';
        try {
            const res = await fetch(`/api/v1/inventory/fibers/${editingId}/audit-log/`, { credentials: 'same-origin' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (!data.results?.length) {
                listEl.innerHTML = '<p class="audit-log-empty">Nenhum registro encontrado.</p>';
                return;
            }
            listEl.innerHTML = data.results.map(entry => {
                const dt = new Date(entry.timestamp).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
                const badge = `<span class="audit-log-badge audit-log-badge--${entry.action}">${entry.action_display}</span>`;
                return `<div class="audit-log-entry">
                    <div class="audit-log-entry__header">${badge}<span class="audit-log-entry__meta">${dt}</span></div>
                    <div class="audit-log-entry__meta">por ${entry.username}</div>
                </div>`;
            }).join('');
        } catch (err) {
            listEl.innerHTML = '<p class="audit-log-empty">Erro ao carregar histórico.</p>';
        }
    }

    document.getElementById('tabBtnIdentification')?.addEventListener('click', () => activateTab('tabBtnIdentification'));
    document.getElementById('tabBtnConnections')?.addEventListener('click', () => activateTab('tabBtnConnections'));
    document.getElementById('tabBtnHistory')?.addEventListener('click', () => activateTab('tabBtnHistory'));
    document.getElementById('tabBtnPhotos')?.addEventListener('click', () => activateTab('tabBtnPhotos'));

    // ── Photo gallery ─────────────────────────────────────────
    async function loadPhotos() {
        const gallery = document.getElementById('photoGallery');
        if (!gallery) return;
        const editingId = getEditingFiberId();
        if (!editingId) {
            gallery.innerHTML = '<p class="photo-empty">Salve o cabo primeiro para adicionar fotos.</p>';
            return;
        }
        gallery.innerHTML = '<p class="photo-empty">Carregando…</p>';
        try {
            const res = await fetch(`/api/v1/inventory/fibers/${editingId}/photos/`, { credentials: 'same-origin' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            _renderPhotoGallery(data.photos, editingId);
        } catch {
            gallery.innerHTML = '<p class="photo-empty">Erro ao carregar fotos.</p>';
        }
    }

    function _renderPhotoGallery(photos, cableId) {
        const gallery = document.getElementById('photoGallery');
        if (!gallery) return;
        if (!photos.length) {
            gallery.innerHTML = '<p class="photo-empty">Nenhuma foto. Envie imagens acima.</p>';
            return;
        }
        gallery.innerHTML = photos.map(p => `
            <div class="photo-thumb" data-id="${p.id}">
                <img src="${p.url}" alt="${p.caption || 'Foto'}" loading="lazy" />
                ${p.caption ? `<div class="photo-thumb__caption">${p.caption}</div>` : ''}
                <button class="photo-thumb__del" data-photo-id="${p.id}" data-cable-id="${cableId}" title="Excluir foto" type="button">&times;</button>
            </div>
        `).join('');
        gallery.querySelectorAll('.photo-thumb__del').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                if (!confirm('Excluir esta foto?')) return;
                const { photoId, cableId } = btn.dataset;
                try {
                    const res = await fetch(`/api/v1/inventory/fibers/${cableId}/photos/${photoId}/`, {
                        method: 'DELETE',
                        credentials: 'same-origin',
                        headers: { 'X-CSRFToken': _getCsrfToken() },
                    });
                    if (!res.ok) throw new Error();
                    btn.closest('.photo-thumb').remove();
                    if (!gallery.querySelector('.photo-thumb')) {
                        gallery.innerHTML = '<p class="photo-empty">Nenhuma foto. Envie imagens acima.</p>';
                    }
                } catch {
                    alert('Erro ao excluir foto.');
                }
            });
        });
        // Lightbox on thumb click
        gallery.querySelectorAll('.photo-thumb').forEach((thumb, idx) => {
            thumb.addEventListener('click', (e) => {
                if (e.target.closest('.photo-thumb__del')) return;
                _openLightbox(photos, idx);
            });
        });
    }

    // ── Vanilla JS lightbox ───────────────────────────────────────────
    let _lbPhotos = [];
    let _lbIndex = 0;
    let _lbEl = null;

    function _injectLightboxStyles() {
        if (document.getElementById('nd-lightbox-style')) return;
        const style = document.createElement('style');
        style.id = 'nd-lightbox-style';
        style.textContent = `
#nd-lightbox-root{position:fixed;inset:0;z-index:2147483647;background:rgba(0,0,0,.88);
  display:flex;align-items:center;justify-content:center;}
#nd-lightbox-root .lb-close{position:absolute;top:1rem;right:1.25rem;background:none;
  border:none;color:#fff;font-size:2.2rem;line-height:1;cursor:pointer;opacity:.75;padding:0;}
#nd-lightbox-root .lb-close:hover{opacity:1;}
#nd-lightbox-root .lb-nav{background:none;border:none;color:#fff;font-size:3.5rem;
  line-height:1;cursor:pointer;padding:0 1rem;opacity:.6;user-select:none;flex-shrink:0;}
#nd-lightbox-root .lb-nav:hover{opacity:1;}
#nd-lightbox-root .lb-nav.hidden{visibility:hidden;}
#nd-lightbox-root .lb-body{display:flex;flex-direction:column;align-items:center;
  max-width:calc(100vw - 10rem);max-height:calc(100vh - 4rem);}
#nd-lightbox-root .lb-body img{max-width:100%;max-height:calc(100vh - 8rem);
  object-fit:contain;border-radius:.5rem;box-shadow:0 8px 40px rgba(0,0,0,.6);}
#nd-lightbox-root .lb-caption{margin-top:.75rem;color:rgba(255,255,255,.8);
  font-size:.875rem;text-align:center;}
#nd-lightbox-root .lb-counter{margin-top:.375rem;color:rgba(255,255,255,.4);font-size:.75rem;}
        `;
        document.head.appendChild(style);
    }

    function _buildLightboxEl() {
        _injectLightboxStyles();
        const el = document.createElement('div');
        el.id = 'nd-lightbox-root';
        el.innerHTML = `
            <button class="lb-close" aria-label="Fechar">&times;</button>
            <button class="lb-nav lb-prev" aria-label="Anterior">&#8249;</button>
            <div class="lb-body">
                <img src="" alt="" />
                <p class="lb-caption" style="display:none"></p>
                <span class="lb-counter" style="display:none"></span>
            </div>
            <button class="lb-nav lb-next" aria-label="Próxima">&#8250;</button>
        `;
        el.querySelector('.lb-close').addEventListener('click', _closeLightbox);
        el.addEventListener('click', (e) => { if (e.target === el) _closeLightbox(); });
        el.querySelector('.lb-prev').addEventListener('click', () => _lbGo(_lbIndex - 1));
        el.querySelector('.lb-next').addEventListener('click', () => _lbGo(_lbIndex + 1));
        return el;
    }

    function _lbKeydown(e) {
        if (!_lbEl) return;
        if (e.key === 'Escape') _closeLightbox();
        if (e.key === 'ArrowLeft') _lbGo(_lbIndex - 1);
        if (e.key === 'ArrowRight') _lbGo(_lbIndex + 1);
    }

    function _lbGo(idx) {
        _lbIndex = (_lbPhotos.length + idx) % _lbPhotos.length;
        _lbRender();
    }

    function _lbRender() {
        if (!_lbEl) return;
        const p = _lbPhotos[_lbIndex];
        _lbEl.querySelector('img').src = p.url;
        _lbEl.querySelector('img').alt = p.caption || 'Foto';
        const cap = _lbEl.querySelector('.lb-caption');
        cap.textContent = p.caption || '';
        cap.style.display = p.caption ? '' : 'none';
        const multi = _lbPhotos.length > 1;
        const counter = _lbEl.querySelector('.lb-counter');
        counter.textContent = `${_lbIndex + 1} / ${_lbPhotos.length}`;
        counter.style.display = multi ? '' : 'none';
        _lbEl.querySelector('.lb-prev').classList.toggle('hidden', !multi);
        _lbEl.querySelector('.lb-next').classList.toggle('hidden', !multi);
    }

    function _openLightbox(photos, index) {
        _lbPhotos = photos;
        _lbIndex = index;
        if (!_lbEl) {
            _lbEl = _buildLightboxEl();
            document.body.appendChild(_lbEl);
        }
        _lbRender();
        _lbEl.style.display = 'flex';
        document.addEventListener('keydown', _lbKeydown);
    }

    function _closeLightbox() {
        if (_lbEl) { _lbEl.style.display = 'none'; }
        document.removeEventListener('keydown', _lbKeydown);
    }

    function _getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    async function _uploadPhotos(files, cableId) {
        const progress = document.getElementById('photoUploadProgress');
        const fill = document.getElementById('photoProgressFill');
        const label = document.getElementById('photoProgressLabel');
        const prompt = document.getElementById('photoUploadPrompt');
        if (progress) { progress.style.display = 'flex'; }
        if (prompt) { prompt.style.display = 'none'; }
        const total = files.length;
        let done = 0;
        for (const file of files) {
            if (label) label.textContent = `Enviando ${done + 1} de ${total}…`;
            if (fill) fill.style.width = `${Math.round((done / total) * 100)}%`;
            const fd = new FormData();
            fd.append('image', file);
            try {
                const res = await fetch(`/api/v1/inventory/fibers/${cableId}/photos/`, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'X-CSRFToken': _getCsrfToken() },
                    body: fd,
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    alert(err.error || `Erro ao enviar ${file.name}`);
                }
            } catch {
                alert(`Erro ao enviar ${file.name}`);
            }
            done++;
        }
        if (fill) fill.style.width = '100%';
        if (label) label.textContent = 'Concluído!';
        await new Promise(r => setTimeout(r, 600));
        if (progress) progress.style.display = 'none';
        if (prompt) prompt.style.display = 'flex';
        loadPhotos();
    }

    // Wire up file input and drag & drop
    const photoFileInput = document.getElementById('photoFileInput');
    const photoDropZone = document.getElementById('photoDropZone');
    photoFileInput?.addEventListener('change', () => {
        const cableId = getEditingFiberId();
        if (!cableId || !photoFileInput.files.length) return;
        _uploadPhotos(Array.from(photoFileInput.files), cableId);
        photoFileInput.value = '';
    });
    photoDropZone?.addEventListener('dragover', (e) => {
        e.preventDefault();
        photoDropZone.classList.add('dragover');
    });
    photoDropZone?.addEventListener('dragleave', () => photoDropZone.classList.remove('dragover'));
    photoDropZone?.addEventListener('drop', (e) => {
        e.preventDefault();
        photoDropZone.classList.remove('dragover');
        const cableId = getEditingFiberId();
        const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'));
        if (!cableId) { alert('Salve o cabo primeiro.'); return; }
        if (files.length) _uploadPhotos(files, cableId);
    });

    // ── Cable groups ──────────────────────────────────────────
    async function loadCableGroups() {
        const select = document.getElementById('manualCableGroupSelect');
        if (!select) return;
        try {
            const res = await fetch('/api/v1/inventory/cable-groups/', { credentials: 'same-origin' });
            if (!res.ok) return;
            const data = await res.json();
            const current = select.value;
            // Keep the first "no group" option and rebuild the rest
            select.innerHTML = '<option value="">— Sem grupo —</option>';
            (data.results || []).forEach(g => {
                const opt = document.createElement('option');
                opt.value = g.id;
                opt.textContent = g.name + (g.manufacturer ? ` (${g.manufacturer})` : '');
                select.appendChild(opt);
            });
            if (current) select.value = current;
        } catch (err) {
            console.warn('[loadCableGroups] Failed to load cable groups:', err);
        }
    }
    void loadCableGroups();

    document.getElementById('addCableGroupBtn')?.addEventListener('click', async () => {
        const name = window.prompt('Nome do novo grupo de cabos:');
        if (!name || !name.trim()) return;
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        try {
            const res = await fetch('/api/v1/inventory/cable-groups/create/', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ name: name.trim() }),
            });
            const data = await res.json();
            if (!res.ok) {
                showErrorMessage(data.error || 'Erro ao criar grupo.');
                return;
            }
            await loadCableGroups();
            const select = document.getElementById('manualCableGroupSelect');
            if (select) select.value = String(data.id);
            showSuccessMessage(`Grupo "${data.name}" criado.`);
        } catch (err) {
            showErrorMessage('Erro ao criar grupo.');
        }
    });

    // ── Responsáveis ──────────────────────────────────────────
    // Load system users as responsibles
    async function loadResponsibles() {
        const select = document.getElementById('manualResponsibleSelect');
        if (!select) return;
        try {
            const res = await fetch('/api/users/?is_active=true', { credentials: 'same-origin' });
            if (!res.ok) return;
            const data = await res.json();
            const current = select.value;
            select.innerHTML = '<option value="">— Sem responsável —</option>';
            (data.users || []).forEach(u => {
                const opt = document.createElement('option');
                opt.value = u.id;
                opt.textContent = u.full_name || u.username;
                select.appendChild(opt);
            });
            if (current) select.value = current;
        } catch (err) {
            console.warn('[loadResponsibles] Failed:', err);
        }
    }
    void loadResponsibles();

    if (manualForm) {
        manualForm.addEventListener('submit', handleManualFormSubmit);
    }

    // Device/port change listeners now handled by modalEditor module
    // Removed duplicate listeners to avoid conflicts

    if (manualModal) {
        manualModal.addEventListener('click', (event) => {
            if (event.target === manualModal) {
                closeManualSaveModal();
            }
        });
    }

    void ensureDeviceOptionsLoaded();
}

function runWhenDomReady(callback) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', callback, { once: true });
    } else {
        setTimeout(callback, 0);
    }
}

export function initializeNetworkDesignApp(options = {}) {
    const { bindDom = true, initMap = true, force = false } = options;

    if (force) {
        resetNetworkDesignState();
        appInitialized = false;
    }

    if (appInitialized && !force) {
        return;
    }

    if (bindDom) {
        initializeDomBindings();
    }
    if (initMap) {
        startGoogleMapsWatcher();
    }

    appInitialized = true;
}

// Auto-bootstrap for legacy usage
runWhenDomReady(() => {
    if (document.getElementById('builderMap')) {
        console.log('[NetworkDesign] DOM ready; auto bootstrapping fiber route builder.');
        initializeNetworkDesignApp();
    }
});

window.closeManualSaveModal = closeManualSaveModal;
window.loadFibers = loadFibers;
window.loadFiberDetail = loadFiberDetail;
window.destroyNetworkDesignApp = destroyNetworkDesignApp;

/**
 * Fly the map to a given location. Used by the global search bar.
 * @param {number} lng
 * @param {number} lat
 * @param {number} zoom
 */
export function flyToLocation(lng, lat, zoom = 14) {
    const mapInstance = getMapInstance();
    if (!mapInstance) return;
    mapInstance.flyTo({ lat, lng }, zoom);
}

const _HIGHLIGHT_SRC = '__nd_search_highlight_src';
const _HIGHLIGHT_LAYER = '__nd_search_highlight_layer';
let _highlightTimer = null;

function _removeHighlightPoint(map) {
    if (map.getLayer(_HIGHLIGHT_LAYER)) map.removeLayer(_HIGHLIGHT_LAYER);
    if (map.getSource(_HIGHLIGHT_SRC)) map.removeSource(_HIGHLIGHT_SRC);
}

function _addHighlightPoint(map, lng, lat) {
    _removeHighlightPoint(map);
    map.addSource(_HIGHLIGHT_SRC, {
        type: 'geojson',
        data: { type: 'Feature', geometry: { type: 'Point', coordinates: [lng, lat] } },
    });
    map.addLayer({
        id: _HIGHLIGHT_LAYER,
        type: 'circle',
        source: _HIGHLIGHT_SRC,
        paint: {
            'circle-radius': 20,
            'circle-color': '#facc15',
            'circle-opacity': 0.55,
            'circle-stroke-color': '#f59e0b',
            'circle-stroke-width': 3,
            'circle-stroke-opacity': 0.9,
        },
    });
    clearTimeout(_highlightTimer);
    _highlightTimer = setTimeout(() => _removeHighlightPoint(map), 4000);
}

export function highlightSearchResult(item) {
    const mapInstance = getMapInstance();
    if (!mapInstance || !mapInstance.mapboxMap) return;
    const map = mapInstance.mapboxMap;

    if (item.type === 'cable') {
        highlightCable(item.id);
    }
    if (item.lat != null && item.lng != null) {
        _addHighlightPoint(map, item.lng, item.lat);
    }
}
