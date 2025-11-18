// Core modules
// Revert to relative imports (server static path already resolves module directory)
import { getPath, setPath as setPathState, addPoint, updatePoint, removePoint, reorderPath, clearPath, totalDistance as calculateDistance, onPathChange } from './modules/pathState.js';
import { initMap as initializeMap, onMapClick, onMapRightClick, drawPolyline, clearPolyline, addMarker as createMarker, removeMarker, clearMarkers as clearAllMarkers, attachPolylineRightClick, createCablePolyline, getMapInstance, cleanupMap } from './modules/mapCore.js';
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
} from './modules/modalEditor.js';

// API client modules
import { fetchFibers, fetchFiber, createFiberManual, updateFiber, removeFiber } from './modules/apiClient.js';

// Business logic modules
import { initCableService, loadCableList, loadCableDetails, createCable, updateCableData, deleteCable, loadAllCablesForVisualization, validateCablePayload, removeCableVisualization, cleanupCableService } from './modules/cableService.js';

// UI helper modules
import { refreshPointsList, updateDistanceDisplay, updateSaveButtonState, extractFormData, showSuccessMessage, showErrorMessage, togglePanel, setFormSubmitting, updateCableSelect, showConfirmDialog, cleanupUIHelpers } from './modules/uiHelpers.js';

// Application state
let map;
let polyline;
let markers = [];
let activeFiberId = null;
let currentFiberMeta = null;
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
    if (!map || typeof google === 'undefined') {
        return null;
    }
    const projection = map.getProjection && map.getProjection();
    if (!projection) {
        return null;
    }
    const worldPoint = projection.fromLatLngToPoint(new google.maps.LatLng(lat, lng));
    if (!worldPoint) {
        return null;
    }
    const scale = Math.pow(2, map.getZoom());
    return new google.maps.Point(worldPoint.x * scale, worldPoint.y * scale);
}

function distanceBetweenPixels(a, b) {
    if (!a || !b) {
        return Number.POSITIVE_INFINITY;
    }
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    return Math.hypot(dx, dy);
}

function distancePointToSegmentPx(point, segmentStart, segmentEnd) {
    if (!point || !segmentStart || !segmentEnd) {
        return Number.POSITIVE_INFINITY;
    }
    const dx = segmentEnd.x - segmentStart.x;
    const dy = segmentEnd.y - segmentStart.y;
    if (dx === 0 && dy === 0) {
        return distanceBetweenPixels(point, segmentStart);
    }
    const t = ((point.x - segmentStart.x) * dx + (point.y - segmentStart.y) * dy) / (dx * dx + dy * dy);
    const clampedT = Math.max(0, Math.min(1, t));
    const projX = segmentStart.x + clampedT * dx;
    const projY = segmentStart.y + clampedT * dy;
    return Math.hypot(point.x - projX, point.y - projY);
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
        addMarker(point);
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
    
    // Cleanup modules
    cleanupMap();
    cleanupContextMenu();
    cleanupCableService();
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

    // Redraw polyline for the currently edited path
    if (polyline) {
        clearPolyline();
    }
    if (path.length > 0) {
        polyline = drawPolyline(path);
        // Add right-click to polyline
        if (polyline) {
            attachPolylineRightClick(polyline, ({ clientX, clientY }) => {
                showContextMenu(clientX, clientY);
                updateContextMenuStateWrapper();
            });
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
});

// REMOVED: clearAllCablesFromMap() - moved into cableService.js
// REMOVED: loadAllCablesForVisualization_local() - replaced by modular cableService version

// Expose function globally for use in import_kml.js
window.clearMapAndResetState = clearMapAndResetState;

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

function addMarker(point, removable = true) {
    console.log(`[addMarker] Creating draggable marker at:`, point);
    const marker = createMarker(point, { draggable: true });
    markers.push(marker);
    console.log(`[addMarker] Total markers now: ${markers.length}`);

    marker.addListener('dragend', () => {
        const index = markers.indexOf(marker);
        if (index > -1) {
            const newPos = marker.getPosition();
            console.log(`[addMarker] Marker #${index} dragged to:`, newPos.lat(), newPos.lng());
            updatePoint(index, newPos.lat(), newPos.lng());
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
    currentPath.forEach((point) => addMarker(point));
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
    };
    console.log(`[updateContextMenuStateWrapper] Updating menu with state:`, state);
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
            // Load cable for editing
            await loadFiberDetail(cableId); // Carrega dados E chama setPath -> onPathChange

            // Mostra menu de contexto
            setTimeout(() => {
                const clickPos = event.domEvent ? { clientX: event.domEvent.clientX, clientY: event.domEvent.clientY } : { clientX: 0, clientY: 0 };
                showContextMenu(clickPos.clientX, clickPos.clientY);
                updateContextMenuStateWrapper(); // Atualiza estado do menu
            }, 100);

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

function startGoogleMapsWatcher() {
    if (mapsInitStarted) {
        return;
    }
    mapsInitStarted = true;
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
        currentFiberMeta = {
            id: data.id,
            name: data.name || '',
            origin_device_id: data.origin?.device_id || null,
            origin_port_id: data.origin?.port_id || null,
            dest_device_id: data.destination?.device_id || null,
            dest_port_id: data.destination?.port_id || null,
            single_port: Boolean(data.single_port),
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

function fitMapToBounds(path) {
    if (!map || !path || path.length === 0) return;

    const bounds = new google.maps.LatLngBounds();
    
    // Add all points to bounds
    path.forEach(point => {
        bounds.extend(new google.maps.LatLng(point.lat, point.lng));
    });

    // Adjust map to show all points
    map.fitBounds(bounds);

    // Add small padding
    const padding = { top: 50, right: 50, bottom: 50, left: 50 };
    map.fitBounds(bounds, padding);
}

async function cancelEditing() {
    const wasEditing = Boolean(activeFiberId);
    closeManualSaveModal();
    hideContextMenu();
    clearMapAndResetState();
    await reloadCableVisualization({ fitToBounds: true });
    refreshList();
    updateContextMenuStateWrapper();
}

window.cancelFiberEditing = cancelEditing;



async function openEditFiberModal() {
    if (!activeFiberId || !currentFiberMeta) {
        showErrorMessage('Select a cable first.');
        return;
    }

    syncModalParent();
    await ensureDeviceOptionsLoaded();
    await openModalForEdit(currentFiberMeta, totalDistance());
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
function openManualSaveModal(skipReset = false) {
    syncModalParent();
    if (skipReset) {
        // Editing mode - modal already populated by openModalForEdit
        return;
    }
    void ensureDeviceOptionsLoaded();
    openModalForCreate(totalDistance());
}

function closeManualSaveModal() {
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
    try {
        await updateFiber(fiberId, payload);
        showSuccessMessage('Cable updated successfully.');
        closeManualSaveModal();
        clearMapAndResetState();
        await loadFibers();
        await reloadCableVisualization({ fitToBounds: true });
    } catch (error) {
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
        showErrorMessage('Add at least two points on the map before saving the route.');
        return;
    }

    const formData = new FormData(manualForm);
    const singlePortCheckbox = manualSinglePortCheckbox || document.getElementById('manualSinglePortOnly');
    const singlePort = singlePortCheckbox && singlePortCheckbox.checked;

    const payload = {
        name: (formData.get('name') || '').trim(),
        origin_device_id: formData.get('origin_device_id'),
        origin_port_id: formData.get('origin_port_id'),
        dest_device_id: singlePort
            ? formData.get('origin_device_id')
            : formData.get('dest_device_id'),
        dest_port_id: singlePort ? formData.get('origin_port_id') : formData.get('dest_port_id'),
        single_port: singlePort,
    };

    if (!payload.name || !payload.origin_device_id || !payload.origin_port_id) {
        showErrorMessage('Fill in all required fields.');
        return;
    }
    if (!singlePort && !payload.dest_port_id) {
        showErrorMessage('Fill in all required fields.');
        return;
    }

    // Always include path, both when creating and editing
    payload.path = path.map((point) => ({ lat: point.lat, lng: point.lng }));

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
    
    // Toggle buttons for panels
    document.getElementById('toggleRoutePoints')?.addEventListener('click', () => {
        const panel = document.getElementById('routePointsPanel');
        const helpPanel = document.getElementById('helpPanel');
        if (panel) {
            panel.classList.toggle('hidden');
            // Hide help if route points is shown
            if (!panel.classList.contains('hidden')) {
                helpPanel?.classList.add('hidden');
            }
        }
    });
    
    document.getElementById('toggleHelp')?.addEventListener('click', () => {
        const panel = document.getElementById('helpPanel');
        const routePanel = document.getElementById('routePointsPanel');
        if (panel) {
            panel.classList.toggle('hidden');
            // Hide route points if help is shown
            if (!panel.classList.contains('hidden')) {
                routePanel?.classList.add('hidden');
            }
        }
    });
    
    document.getElementById('manualCancelButton')?.addEventListener('click', async () => {
        await cancelEditing();
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
                if (activeFiberId) {
                    cancelEditing().catch((err) => console.error('[cancelEditing] Error on ESC (editing active):', err));
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
