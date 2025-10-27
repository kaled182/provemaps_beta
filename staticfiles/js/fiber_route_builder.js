// Core modules
import { getPath, setPath as setPathState, addPoint, updatePoint, removePoint, reorderPath, clearPath, totalDistance as calculateDistance, onPathChange } from './modules/pathState.js';
import { initMap as initializeMap, onMapClick, onMapRightClick, drawPolyline, clearPolyline, addMarker as createMarker, removeMarker, clearMarkers as clearAllMarkers, attachPolylineRightClick, createCablePolyline } from './modules/mapCore.js';
import { initContextMenu, showContextMenu, hideContextMenu, updateContextMenuState } from './modules/contextMenu.js';
import { initModalEditor, openModalForCreate, openModalForEdit, closeModal, getEditingFiberId, updateEditButtonState } from './modules/modalEditor.js';

// API client modules
import { fetchFibers, fetchFiber, createFiberManual, updateFiber, removeFiber } from './modules/apiClient.js';

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

// DOM elements
let manualForm;
let manualModal;
let distanceEl;
let manualSinglePortCheckbox;

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
onPathChange(({ path, distance }) => {
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
    
    // Update distance display (only if element exists)
    const distEl = distanceEl || document.getElementById('distanceKm');
    if (distEl) {
        distEl.textContent = distance.toFixed(3);
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

// Note: loadAllCablesForVisualization is imported from cableService.js
// Do not redeclare it here to avoid "Identifier already declared" error

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
            reloadCableVisualization();
        } else {
            console.warn('Map not ready to load cables. Retrying...');
            setTimeout(() => map && reloadCableVisualization(), 500);
        }
    }, 300);
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

// Make visualization cables clickable with right-click
function makeCableEditable(cablePolyline, cableId, cableName) {
    console.log(`[makeCableEditable] Attaching right-click to cable #${cableId}: ${cableName}`);
    
    // Right-click on cable to load + open menu
    cablePolyline.addListener('rightclick', async (event) => {
        console.log(`[makeCableEditable] Right-click detected on cable #${cableId}`);
        event.stop();
        
        // Load cable for editing
        const fiberSelect = document.getElementById('fiberSelect');
        if (fiberSelect) {
            fiberSelect.value = String(cableId);
        }
        
        console.log(`[makeCableEditable] Loading cable details...`);
        await loadFiberDetail(cableId);
        
        // Wait a moment to ensure currentFiberMeta was updated
        console.log(`[makeCableEditable] Opening context menu at:`, event.domEvent.clientX, event.domEvent.clientY);
        setTimeout(() => {
            const menuElement = document.getElementById('contextMenu');
            console.log(`[makeCableEditable] Menu element:`, menuElement, 'hasActiveFiber:', !!activeFiberId);
            showContextMenu(event.domEvent.clientX, event.domEvent.clientY);
            updateContextMenuStateWrapper();
            console.log(`[makeCableEditable] Context menu should be visible now`);
        }, 100);
    });
}

// Helper function to reload visualization with click handlers
async function reloadCableVisualization() {
    try {
        console.log('[reloadCableVisualization] Clearing old polylines...');
        // Clear previous cables
        clearCablePolylines();
        
        console.log('[reloadCableVisualization] Fetching cables...');
        const data = await fetchFibers();
        const cables = data.fibers || data.cables || [];
        
        if (cables.length === 0) {
            console.info('No cables found for visualization.');
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
                    strokeColor: '#1E3A8A', // Dark blue for visualization
                    strokeOpacity: 0.6,
                    strokeWeight: 2,
                });
                
                // Add right-click for editing
                makeCableEditable(viewPolyline, cable.id, cable.name);
                
                loadedCount++;
                
            } catch (error) {
                console.error(`Error loading cable ${cable.id}:`, error);
            }
        }
        
        console.info(`[reloadCableVisualization] ${loadedCount} cables loaded.`);
        
    } catch (error) {
        console.error('Error loading cables for visualization:', error);
    }
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
        console.log(`[loadFiberDetail] Loaded cable #${id}:`, data);
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
        console.log(`[loadFiberDetail] Setting path with ${path.length} points:`, path);
        setPath(path);
        console.log(`[loadFiberDetail] Created ${markers.length} markers`);
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
        await reloadCableVisualization();
        await loadFibers(); // Reload dropdown
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
        await reloadCableVisualization();
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
    const singlePortCheckbox = manualSinglePortCheckbox || document.getElementById('manualSinglePortOnly');
    const singlePort = singlePortCheckbox && singlePortCheckbox.checked;

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

// Note: deleteCable is imported from cableService.js
// Do not redeclare it here to avoid "Identifier already declared" error

document.addEventListener('DOMContentLoaded', () => {
    // Initialize DOM elements
    manualForm = document.getElementById('manualSaveForm');
    manualModal = document.getElementById('manualSaveModal');
    distanceEl = document.getElementById('distanceKm');
    manualSinglePortCheckbox = document.getElementById('manualSinglePortOnly');
    
    console.log('[DOMContentLoaded] DOM elements initialized:', {
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
    document.getElementById('contextEditPath')?.addEventListener('click', () => {
        hideContextMenu();
        if (activeFiberId && currentFiberMeta) {
            console.log('[contextEditPath] Entering path edit mode');
            // Cable is already loaded, just ensure markers are visible
            const currentPath = getPath();
            if (currentPath.length === 0) {
                // If path empty, reload the cable
                loadFiberDetail(activeFiberId);
            } else {
                console.log(`[contextEditPath] Path already loaded with ${currentPath.length} points`);
                // Path already loaded by right-click event, markers should be visible
                alert(`Path edit mode active!\n${currentPath.length} draggable markers loaded.\nDrag markers to edit, right-click marker to remove.`);
            }
        }
    });
    
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
    
    // Menu de contexto - Opções ao criar novo cabo
    document.getElementById('contextSaveNewCable')?.addEventListener('click', () => {
        console.log('[contextSaveNewCable] Button clicked, path length:', getPath().length);
        hideContextMenu();
        if (getPath().length >= 2) {
            console.log('[contextSaveNewCable] Opening modal to assign cable...');
            openManualSaveModal(false); // false = criando novo cabo
        } else {
            alert('Draw at least 2 points to create a cable.');
        }
    });
    
    document.getElementById('contextClearNew')?.addEventListener('click', () => {
        hideContextMenu();
        // Limpar pontos desenhados
        clearPath();
        clearAllMarkers();
        clearPolyline();
        // onPathChange callback will handle UI updates
        refreshList();
    });
    
    // Fechar menu de contexto ao clicar fora
    document.addEventListener('click', (e) => {
        const menu = document.getElementById('contextMenu');
        if (menu && !menu.contains(e.target)) {
            hideContextMenu();
        }
    });
    
    // Botão de carregar cabo removido do layout; listener protegido
    document.getElementById('loadFiber')?.addEventListener('click', () => {
        const id = document.getElementById('fiberSelect')?.value;
        if (!id) {
            alert('Select a cable first.');
            return;
        }
        loadFiberDetail(id);
    });
    
    // Botão Clear não existe mais - funcionalidade no menu de contexto
    
    // Autoload de cabos movido para initMap para garantir que o mapa exista
    
    // Event listeners antigos removidos (savePath, deleteCable, editFiber)
    // Agora tudo é via menu de contexto
    
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
    
    // Limpar o mapa e resetar estado
    clearMapAndResetState();
    
    // Recarregar lista de cabos
    await loadFibers();
    
    // Recarregar visualização de todos os cabos no mapa
    await loadAllCablesForVisualization();
    
    if (fiberId) {
        console.info(`New cable created: ${fiberId}`);
    }
});
