// Core modules
import { getPath, setPath as setPathState, addPoint, updatePoint, clearPath, totalDistance as calculateDistance, onPathChange } from './modules/pathState.js';
import { initMap as initializeMap, onMapClick, onMapRightClick, drawPolyline, clearPolyline, addMarker as createMarker, removeMarker, clearMarkers as clearAllMarkers, attachPolylineRightClick } from './modules/mapCore.js';
import { initContextMenu, showContextMenu, hideContextMenu, updateContextMenuState } from './modules/contextMenu.js';
import { initModalEditor, openModalForCreate, openModalForEdit, closeModal, getEditingFiberId } from './modules/modalEditor.js';

// Business logic modules
import { loadCableList, loadCableDetails, createCable, updateCableData, deleteCable, loadAllCablesForVisualization, clearCablePolylines, validateCablePayload } from './modules/cableService.js';

// UI helper modules
import { refreshPointsList, updateDistanceDisplay, updateSaveButtonState, extractFormData, showSuccessMessage, showErrorMessage, togglePanel, setFormSubmitting, updateCableSelect } from './modules/uiHelpers.js';

// Application state
let map;
let polyline;
let markers = [];
let activeFiberId = null;
let currentFiberMeta = null;
let allCablesPolylines = [];

/**
 * Clear map and reset application state
 */
function clearMapAndResetState() {
    activeFiberId = null;
    currentFiberMeta = null;
    updateCableSelect('');
    setPath([]);
    clearCablePolylines(allCablesPolylines);
}

/**
 * Setup path change callback - handles UI updates when path changes
 */
    // Redraw polyline
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
    
    // Update distance display
    if (distanceEl) {
        distanceEl.textContent = distance.toFixed(3);
    }
    
    // Rebuild marker list
    refreshList();
    
    // Update save button state
    const saveButton = document.getElementById('savePath');
    if (saveButton) {
        const allowSave = (path.length >= 2) || (activeFiberId && path.length === 0);
        saveButton.disabled = !allowSave;
    }
});

function clearAllCablesFromMap() {
    // Remove all visualization polylines
    allCablesPolylines.forEach(polyline => polyline.setMap(null));
    allCablesPolylines = [];
}

async function loadAllCablesForVisualization() {
    try {
        // Clear previous cables
        clearAllCablesFromMap();
        
        const data = await fetchFibers();
        const cables = data.fibers || data.cables || [];
        
        if (cables.length === 0) {
            alert('No cables found.');
            return;
        }
        
        let loadedCount = 0;
        
        // Load details for each cable and draw on map
        for (const cable of cables) {
            try {
                const detail = await fetchFiber(cable.id);
                const path = detail.path || [];
                
                if (path.length < 2) continue;
                
                // Create polyline for visualization (clickable for editing)
                const viewPolyline = createCablePolyline(path, {
                    strokeColor: '#e90000ff', // Dark blue for visualization
                    strokeOpacity: 1.0,
                    strokeWeight: 2,
                });
                
                // Add right-click for editing
                makeCableEditable(viewPolyline, cable.id, cable.name);
                
                allCablesPolylines.push(viewPolyline);
                loadedCount++;
                
            } catch (error) {
                console.error(`Error loading cable ${cable.id}:`, error);
            }
        }
        
    // Removed intrusive visual alert; use discrete log
    console.info(`Visualization: ${loadedCount} cables loaded.`);
        
    } catch (error) {
        console.error('Error loading all cables:', error);
        alert('Error loading cables.');
    }
}

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
    const list = document.getElementById('pointsList');
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
    const marker = createMarker(point, { draggable: true });
    markers.push(marker);

    marker.addListener('dragend', () => {
        const index = markers.indexOf(marker);
        if (index > -1) {
            const newPos = marker.getPosition();
            updatePoint(index, newPos.lat(), newPos.lng());
            // onPathChange callback will redraw
        }
    });

    if (removable) {
        const removeMarkerHandler = () => {
            const index = markers.indexOf(marker);
            if (index > -1) {
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
        const point = { lat, lng };
        addPoint(lat, lng);
        addMarker(point);
        // onPathChange callback will handle redraw
    });
    
    // Setup right-click handler via mapCore
    onMapRightClick(({ clientX, clientY }) => {
        showContextMenu(clientX, clientY);
        updateContextMenuStateWrapper();
    });
    
    loadFibers();
    // Load visualization of all cables right after map is ready
    setTimeout(() => {
        if (map) {
            loadAllCablesForVisualization();
        } else {
            console.warn('Map not ready to load cables. Retrying...');
            setTimeout(() => map && loadAllCablesForVisualization(), 500);
        }
    }, 300);
}

// Context menu wrapper - delegates to module with current app state
function updateContextMenuStateWrapper() {
    updateContextMenuState({
        hasActiveFiber: !!activeFiberId,
        fiberMeta: currentFiberMeta,
        pathLength: getPath().length,
    });
}

// Make visualization cables clickable with right-click
function makeCableEditable(cablePolyline, cableId, cableName) {
    // Right-click on cable to load + open menu
    cablePolyline.addListener('rightclick', async (event) => {
        event.stop();
        
        // Load cable for editing
        const fiberSelect = document.getElementById('fiberSelect');
        if (fiberSelect) {
            fiberSelect.value = String(cableId);
        }
        await loadFiberDetail(cableId);
        
        // Wait a moment to ensure currentFiberMeta was updated
        setTimeout(() => {
            showContextMenu(event.domEvent.clientX, event.domEvent.clientY);
            updateContextMenuStateWrapper();
        }, 100);
    });
}

// Make initMap available globally for Google Maps callback (legacy support)
window.initMap = initMap;

// Initialize map when Google Maps API is ready
function waitForGoogleMaps() {
    if (typeof google !== 'undefined' && google.maps) {
        initMap();
    } else {
        setTimeout(waitForGoogleMaps, 100);
    }
}

// Start checking when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', waitForGoogleMaps);
} else {
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
        activeFiberId = data.id;
        currentFiberMeta = {
            name: data.name || '',
            origin_device_id: data.origin?.device_id || null,
            origin_port_id: data.origin?.port_id || null,
            dest_device_id: data.destination?.device_id || null,
            dest_port_id: data.destination?.port_id || null,
            single_port: Boolean(data.single_port),
        };
        updateEditButtonState();
        const path = (data.path && data.path.length) ? data.path : buildDefaultFromEndpoints(data);
        setPath(path);
        if (path && path.length > 0) {
            fitMapToBounds(path);
        }
    } catch (err) {
        console.error('Error loading cable', err);
        alert('Error loading cable');
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



async function openEditFiberModal() {
    if (!activeFiberId || !currentFiberMeta) {
        alert('Select a cable first.');
        return;
    }

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
        alert(`Saved successfully.\nPoints: ${result.points}\nDistance: ${result.length_km} km`);
        clearMapAndResetState();
        await loadFibers();
        await loadAllCablesForVisualization();
    } catch (error) {
        console.error('Request error:', error);
        alert('Connection failure or unexpected error while saving.');
    }
}

// Modal management wrappers - delegate to modalEditor module
function openManualSaveModal(skipReset = false) {
    if (skipReset) {
        // Editing mode - modal already populated by openModalForEdit
        return;
    }
    openModalForCreate(totalDistance());
}

function closeManualSaveModal() {
    closeModal();
}

// Legacy functions removed - now handled by modalEditor module
// All device/port loading logic moved to modalEditor.js
// Legacy functions kept only for external compatibility if needed

async function performCreateFiber(payload) {
    try {
        const data = await createFiberManual(payload);
        alert('Cable created successfully.');
        closeManualSaveModal();
        document.dispatchEvent(new CustomEvent('fiber:cable-created', { detail: { fiberId: data.fiber_id } }));
        await loadAllCablesForVisualization();
    } catch (error) {
        console.error('Error creating cable:', error);
        throw error;
    }
}

async function performUpdateFiber(fiberId, payload) {
    try {
        await updateFiber(fiberId, payload);
        alert('Cable updated successfully.');
        closeManualSaveModal();
        clearMapAndResetState();
        await loadFibers();
        await loadAllCablesForVisualization();
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
        alert('Add at least two points to the map before saving the route.');
        return;
    }

    const formData = new FormData(manualForm);
    const singlePort = manualSinglePortCheckbox && manualSinglePortCheckbox.checked;

    const payload = {
        name: (formData.get('name') || '').trim(),
        origin_device_id: formData.get('origin_device_id'),
        origin_port_id: formData.get('origin_port_id'),
        dest_device_id: singlePort
            ? formData.get('origin_device_id')
            : formData.get('dest_device_id'),
        dest_port_id: singlePort ? null : formData.get('dest_port_id'),
        single_port: singlePort,
    };

    if (!payload.name || !payload.origin_device_id || !payload.origin_port_id) {
        alert('Please fill all required fields.');
        return;
    }
    if (!singlePort && !payload.dest_port_id) {
        alert('Please fill all required fields.');
        return;
    }

    // Always include path, both when creating and editing
    payload.path = path.map((point) => ({ lat: point.lat, lng: point.lng }));

    const submitButton = manualForm.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = true;

    try {
        if (isEditing && editingFiberId) {
            await performUpdateFiber(editingFiberId, payload);
        } else {
            await performCreateFiber(payload);
        }
    } catch (error) {
        console.error('Error saving route:', error);
        alert(error.message || 'Failed to save the route.');
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
        alert('Add at least two points to the map before saving the route.');
        return;
    }
    openManualSaveModal();
}

async function deleteCable() {
    if (!activeFiberId) {
        alert('No cable selected to delete.');
        return;
    }
    if (!confirm('Confirm cable deletion? This action cannot be undone.')) {
        return;
    }
    try {
        await removeFiber(activeFiberId);
        alert('Cable removed successfully.');
        activeFiberId = null;
        setPath([]);
        await loadFibers();
        await loadAllCablesForVisualization();
    } catch (error) {
        console.error('Request error:', error);
        alert('Connection failure or unexpected error while deleting.');
    }
}

document.addEventListener('DOMContentLoaded', () => {
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
    
    // Context menu - General options
    document.getElementById('contextLoadAll')?.addEventListener('click', () => {
        hideContextMenu();
        if (activeFiberId) {
            // Reload only current cable
            loadFiberDetail(activeFiberId);
        } else {
            // Reload all cables
            loadAllCablesForVisualization();
        }
    });
    
    document.getElementById('contextImportKML')?.addEventListener('click', () => {
        hideContextMenu();
        openKmlModal();
    });
    
    // Context menu - Conditional options (cable selected)
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
    
    document.getElementById('contextDeleteCable')?.addEventListener('click', () => {
        hideContextMenu();
        if (activeFiberId) {
            deleteCable();
        }
    });
    
    // Context menu - options when creating a new cable
    document.getElementById('contextSaveNewCable')?.addEventListener('click', () => {
        hideContextMenu();
        if (getPath().length >= 2) {
            openManualSaveModal(false); // false = criando novo cabo
        } else {
            alert('Draw at least 2 points to create a cable.');
        }
    });
    
    document.getElementById('contextClearNew')?.addEventListener('click', () => {
        hideContextMenu();
    // Clear drawn points
        clearPath();
        clearAllMarkers();
        clearPolyline();
        // onPathChange callback will handle UI updates
        refreshList();
    });
    
    // Close context menu when clicking outside
    document.addEventListener('click', (e) => {
        const menu = document.getElementById('contextMenu');
        if (menu && !menu.contains(e.target)) {
            hideContextMenu();
        }
    });
    
    // Load cable button removed from layout; listener kept for safety
    document.getElementById('loadFiber')?.addEventListener('click', () => {
        const id = document.getElementById('fiberSelect')?.value;
        if (!id) {
            alert('Select a cable first.');
            return;
        }
        loadFiberDetail(id);
    });
    
    // Clear button no longer exists - functionality lives in the context menu
    
    // Auto-loading cables moved to initMap to ensure the map exists
    
    // Legacy listeners removed (savePath, deleteCable, editFiber)
    // Everything now routes through the context menu
    
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
});

window.closeManualSaveModal = closeManualSaveModal;
window.loadFibers = loadFibers;
window.loadFiberDetail = loadFiberDetail;

document.addEventListener('fiber:cable-created', async (event) => {
    const fiberId = event.detail?.fiberId;
    
    // Clear the map and reset application state
    clearMapAndResetState();
    
    // Reload cable list
    await loadFibers();
    
    if (fiberId) {
        console.info(`New cable created: ${fiberId}`);
    }
});
