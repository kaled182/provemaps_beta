// Core modules
// Revert to relative imports (server static path already resolves module directory)
import { getPath, setPath as setPathState, addPoint, updatePoint, removePoint, reorderPath, clearPath, totalDistance as calculateDistance, onPathChange } from './modules/pathState.js';
import { initMap as initializeMap, onMapClick, onMapRightClick, drawPolyline, clearPolyline, addMarker as createMarker, removeMarker, clearMarkers as clearAllMarkers, attachPolylineRightClick, createCablePolyline, getMapInstance } from './modules/mapCore.js';
import { initContextMenu, showContextMenu, hideContextMenu, updateContextMenuState } from './modules/contextMenu.js';
import { initModalEditor, openModalForCreate, openModalForEdit, closeModal, getEditingFiberId, updateEditButtonState, isModalOpen } from './modules/modalEditor.js';

// API client modules
import { fetchFibers, fetchFiber, createFiberManual, updateFiber, removeFiber } from './modules/apiClient.js';

// Business logic modules
import { initCableService, loadCableList, loadCableDetails, createCable, updateCableData, deleteCable, loadAllCablesForVisualization, validateCablePayload, removeCableVisualization } from './modules/cableService.js';

// UI helper modules
import { refreshPointsList, updateDistanceDisplay, updateSaveButtonState, extractFormData, showSuccessMessage, showErrorMessage, togglePanel, setFormSubmitting, updateCableSelect } from './modules/uiHelpers.js';

// Application state
let map;
let polyline;
let markers = [];
let activeFiberId = null;
let currentFiberMeta = null;
// ❌ REMOVIDO: let allCablesPolylines = []; // Esta lista agora é gerida DENTRO de cableService.js

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
    updateEditButtonState();
}

/**
 * Setup path change callback - handles UI updates when path changes
 * INCLUI DEBUG PARA O ERRO distance()
 */
onPathChange(({ path, distance }) => {
    // 🕵️‍♂️ DEBUGGING: Verifica o tipo e valor de 'distance' logo na entrada
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
    const distEl = distanceEl || document.getElementById('distanceKm');
    if (distEl) {
        // 🕵️‍♂️ DEBUGGING: Adiciona verificação explícita ANTES de usar .toFixed()
        if (typeof distance === 'number' && !isNaN(distance)) {
            distEl.textContent = distance.toFixed(3);
        } else {
            console.error('[DEBUG onPathChange] distance is NOT a valid number here!', distance);
            distEl.textContent = '---'; // Ou 'Error', ou 0.000
            // 🤔 PONTO DE INVESTIGAÇÃO: Se isto acontecer, o erro vem de pathState.js ou como foi chamado.
        }
    }
    
    // Rebuild marker list
    refreshList();
    
    // Update save button state
    const saveButton = document.getElementById('savePath');
    if (saveButton) {
        const allowSave = (path.length >= 2) || (activeFiberId && path.length === 0);
        saveButton.disabled = !allowSave;
    }
    
    // Update context menu state
    updateContextMenuStateWrapper();
});

// ❌ REMOVIDO: clearAllCablesFromMap() - agora em cableService.js
// ❌ REMOVIDO: loadAllCablesForVisualization_local() - agora usamos versão modular do cableService

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

    if (!map) {
        console.error("Failed to initialize the map.");
        showErrorMessage("Could not load the map.");
        return;
    }

    // ✅ INICIALIZA O cableService DEPOIS que o mapa existe e makeCableEditable está definida
    // É CRUCIAL que makeCableEditable esteja definida ANTES desta chamada.
    initCableService({
        makeEditableCallback: makeCableEditable, // Passa a função local como callback
        map: map // Passa a instância do mapa
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
 * Esta função PRECISA estar definida no escopo de fiber_route_builder.js
 * porque ela chama loadFiberDetail, showContextMenu, etc., que estão aqui.
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
 * Recarrega a visualização de todos os cabos no mapa.
 * Esta função agora delega para loadAllCablesForVisualization_local()
/**
 * Recarrega a visualização de todos os cabos no mapa.
 * Esta função agora delega para loadAllCablesForVisualization() do módulo cableService.
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
    if (typeof google !== 'undefined' && google.maps) {
        console.log('[waitForGoogleMaps] Google Maps API is ready, calling initMap()');
        try {
            initMap();
        } catch (e) {
            console.error('[waitForGoogleMaps] Error calling initMap():', e);
        }
    } else {
        console.log('[waitForGoogleMaps] Google Maps API not ready yet, retrying...');
        setTimeout(waitForGoogleMaps, 100);
    }
}

// Start checking when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('[DOMContentLoaded] DOM ready, starting waitForGoogleMaps');
        waitForGoogleMaps();
    });
} else {
    console.log('[Init] DOM already ready, starting waitForGoogleMaps');
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
        await loadAllCablesForVisualization({ fitToBounds: true });
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
        alert('Cable updated successfully.');
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
        dest_port_id: singlePort ? formData.get('origin_port_id') : formData.get('dest_port_id'),
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
        let friendlyMessage = rawMessage || 'Failed to save the route.';
        if (/duplicate entry/i.test(rawMessage)) {
            friendlyMessage = 'Já existe um cabo com este nome. Utilize um nome diferente.';
        } else if (/erro interno do servidor/i.test(rawMessage) || /internal server error/i.test(rawMessage)) {
            friendlyMessage = 'Erro ao salvar a rota. Verifique se o nome é único e os campos obrigatórios.';
        }
        alert(friendlyMessage);
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
    // ❌ REMOVIDO: contextEditPath - Edição de path já é nativa ao abrir o menu com botão direito
    
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
        
        if (confirm(`Delete cable "${currentFiberMeta?.name || activeFiberId}"? This action cannot be undone.`)) {
            console.log(`[contextDeleteCable] Deleting active cable ID ${activeFiberId}.`);
            try {
                // Chama deleteCable do service, passando callbacks para atualizar a UI localmente
                await deleteCable(activeFiberId, {
                    onSuccess: async () => {
                        showSuccessMessage(`Cable ID ${activeFiberId} deleted.`);
                        // A polyline JÁ FOI removida pelo cableService
                        // Apenas resetamos o estado local e recarregamos a lista
                        const currentSelectedValue = activeFiberId; // Guarda antes de limpar
                        clearMapAndResetState(); // Limpa path de edição, etc.
                        await loadFibers(); // Recarrega dropdown
                        // Opcional: Se o select ainda mostrar o ID apagado, limpe-o aqui
                        const select = document.getElementById('fiberSelect');
                        if (select && select.value === String(currentSelectedValue)) {
                            select.value = '';
                        }
                        await reloadCableVisualization({ fitToBounds: true });
                    },
                    onError: (error) => {
                        showErrorMessage(`Failed to delete cable: ${error.message || 'Unknown error'}`);
                    }
                });
            } catch(e) {
                console.error(`[contextDeleteCable] Unexpected error:`, e);
                showErrorMessage(`Error during delete: ${e.message}`);
            }
        } else {
            console.log(`[contextDeleteCable] Deletion cancelled.`);
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
    
    // Limpar o mapa e resetar estado
    clearMapAndResetState();
    
    // Recarregar lista de cabos
    await loadFibers();
    
    // Recarregar visualização de todos os cabos no mapa
    await loadAllCablesForVisualization({ fitToBounds: true });
    
    if (fiberId) {
        console.info(`New cable created: ${fiberId}`);
    }
});
