import { fetchFibers, fetchFiber, createFiberManual, updateFiber, removeFiber, fetchDevicePorts } from './modules/apiClient.js';
import { 
  getPath, 
  setPath as setPathState, 
  addPoint, 
  removePoint, 
  updatePoint, 
  reorderPath, 
  clearPath, 
  totalDistance as calculateDistance,
  onPathChange 
} from './modules/pathState.js';
import { 
  initMap as initializeMap, 
  getMap, 
  onMapClick, 
  onMapRightClick,
  drawPolyline, 
  clearPolyline,
  addMarker as createMarker, 
  removeMarker, 
  clearMarkers as clearAllMarkers,
  getMarkers,
  fitMapToBounds as fitBounds,
  createCablePolyline,
  attachPolylineRightClick
} from './modules/mapCore.js';

let map;
let polyline;
let markers = [];
let activeFiberId = null;
let allCablesPolylines = []; // Armazena polylines de todos os cabos para visualização

const distanceEl = document.getElementById('distanceKm');

// Manual save modal elements
const manualModal = document.getElementById('manualSaveModal');
const manualModalContent = document.getElementById('manualSaveModalContent');
const manualForm = document.getElementById('manualSaveForm');
const manualRouteDistanceEl = document.getElementById('manualRouteDistance');
const manualRouteNameInput = document.getElementById('manualRouteName');
const manualOriginDeviceSelect = document.getElementById('manualOriginDeviceSelect');
const manualOriginPortSelect = document.getElementById('manualOriginPortSelect');
const manualSinglePortCheckbox = document.getElementById('manualSinglePortOnly');
const manualDestDeviceSelect = document.getElementById('manualDestDeviceSelect');
const manualDestPortSelect = document.getElementById('manualDestPortSelect');
const manualDestNotice = document.getElementById('manualDestNotice');
let editingFiberId = null;
let currentFiberMeta = null;

function updateEditButtonState() {
    // Função mantida para compatibilidade, mas não há mais botão de edição
    // Edição agora é via menu de contexto
}

function clearMapAndResetState() {
    activeFiberId = null;
    currentFiberMeta = null;
    updateEditButtonState();
    const fiberSelect = document.getElementById('fiberSelect');
    if (fiberSelect) {
        fiberSelect.value = '';
    }
    setPath([]);
    clearAllCablesFromMap(); // Também limpar cabos de visualização
}

// Adapter function to bridge pathState module
function setPath(points) {
    setPathState(points);
    // Trigger redraw via path change callback
}

// Path change callback will handle UI updates
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
    // Remover todas as polylines de visualização
    allCablesPolylines.forEach(polyline => polyline.setMap(null));
    allCablesPolylines = [];
}

async function loadAllCablesForVisualization() {
    try {
        // Limpar cabos anteriores
        clearAllCablesFromMap();
        
        const data = await fetchFibers();
        const cables = data.fibers || data.cables || [];
        
        if (cables.length === 0) {
            alert('Nenhum cabo encontrado.');
            return;
        }
        
        let loadedCount = 0;
        
        // Carregar detalhes de cada cabo e desenhar no mapa
        for (const cable of cables) {
            try {
                const detail = await fetchFiber(cable.id);
                const path = detail.path || [];
                
                if (path.length < 2) continue;
                
                // Criar polyline para visualização (clicável para edição)
                const viewPolyline = createCablePolyline(path, {
                    strokeColor: '#1E3A8A', // Azul escuro para visualização
                    strokeOpacity: 0.6,
                    strokeWeight: 2,
                });
                
                // Adicionar right-click para editar
                makeCableEditable(viewPolyline, cable.id, cable.name);
                
                allCablesPolylines.push(viewPolyline);
                loadedCount++;
                
            } catch (error) {
                console.error(`Erro ao carregar cabo ${cable.id}:`, error);
            }
        }
        
    // Removido alerta visual intrusivo; usar log discreto
    console.info(`Visualization: ${loadedCount} cables loaded.`);
        
    } catch (error) {
        console.error('Erro ao carregar todos os cabos:', error);
        alert('Erro ao carregar cabos.');
    }
}

// Expor função globalmente para uso em import_kml.js
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
    });
    
    loadFibers();
    // Carregar visualização de todos os cabos logo após o mapa estar pronto
    setTimeout(() => {
        if (map) {
            loadAllCablesForVisualization();
        } else {
            console.warn('Map not ready to load cables. Retrying...');
            setTimeout(() => map && loadAllCablesForVisualization(), 500);
        }
    }, 300);
}

// Funções do menu de contexto
function showContextMenu(x, y) {
    const menu = document.getElementById('contextMenu');
    if (!menu) return;
    
    // -------- POSICIONAMENTO --------
    const menuWidth = 220;
    const menuHeight = 300; // estimado (não crítico)
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    const offsetX = 5;
    const offsetY = 5;
    
    // Ajustar X para não sair da tela (com margem de 20px)
    let adjustedX = x + offsetX;
    if (adjustedX + menuWidth > windowWidth - 20) {
        // Se não couber à direita, colocar à esquerda do clique
        adjustedX = x - menuWidth - offsetX;
        // Se ainda sair da tela à esquerda, forçar margem mínima
        if (adjustedX < 20) {
            adjustedX = 20;
        }
    }
    
    // Ajustar Y para não sair da tela (com margem de 20px)
    let adjustedY = y + offsetY;
    if (adjustedY + menuHeight > windowHeight - 20) {
        adjustedY = windowHeight - menuHeight - 20;
    }
    if (adjustedY < 20) {
        adjustedY = 20;
    }
    updateContextMenuState();
    
    menu.style.left = adjustedX + 'px';
    menu.style.top = adjustedY + 'px';
    menu.classList.remove('hidden');
}

// Função separada para lógica dos 3 cenários
function updateContextMenuState() {
    const selectedOptions = document.getElementById('contextSelectedOptions');
    const creatingOptions = document.getElementById('contextCreatingOptions');
    const cableInfo = document.getElementById('contextCableInfo');
    const cableName = document.getElementById('contextCableName');
    const savePath = document.getElementById('contextSavePath');
    const generalOptions = document.getElementById('contextGeneralOptions');
    const reloadButton = document.getElementById('contextLoadAll');
    const reloadText = document.getElementById('contextLoadAllText');

    const path = getPath();
    const isCreatingNewCable = !activeFiberId && path.length > 0; // Cenário B
    const isSelectedCable = !!activeFiberId && !!currentFiberMeta; // Cenário C
    const isEmpty = !activeFiberId && path.length === 0; // Cenário A

    // Reset base
    selectedOptions?.classList.add('hidden');
    creatingOptions?.classList.add('hidden');
    cableInfo?.classList.add('hidden');
    generalOptions?.classList.add('hidden');
    reloadButton?.classList.add('hidden');

    if (isCreatingNewCable) {
        // Cenário B
        creatingOptions?.classList.remove('hidden');
        // Sem reload, sem import
    } else if (isSelectedCable) {
        // Cenário C
        selectedOptions?.classList.remove('hidden');
        cableInfo?.classList.remove('hidden');
        if (cableName) {
            const isEditing = path.length > 0;
            const status = isEditing ? ' - EDITING' : '';
            cableName.textContent = `📌 ${currentFiberMeta.name || 'Cable #' + activeFiberId}${status}`;
        }
        // Reload This Cable
        if (reloadButton && reloadText) {
            reloadButton.classList.remove('hidden');
            reloadText.textContent = 'Reload This Cable';
        }
        // Save Path habilitado somente se >=2 pontos
        if (savePath) {
            savePath.disabled = path.length < 2;
            savePath.style.opacity = path.length >= 2 ? '1' : '0.5';
        }
    } else if (isEmpty) {
        // Cenário A
        generalOptions?.classList.remove('hidden'); // Import KML
        if (reloadButton && reloadText) {
            reloadButton.classList.remove('hidden');
            reloadText.textContent = 'Reload All Cables';
        }
    }
}
function hideContextMenu() {
    const menu = document.getElementById('contextMenu');
    if (menu) {
        menu.classList.add('hidden');
    }
}

// Tornar cabos de visualização clicáveis com right-click
function makeCableEditable(cablePolyline, cableId, cableName) {
    // Right-click no cabo para carregar + abrir menu
    cablePolyline.addListener('rightclick', async (event) => {
        event.stop();
        
        // Carregar cabo para edição
        const fiberSelect = document.getElementById('fiberSelect');
        if (fiberSelect) {
            fiberSelect.value = String(cableId);
        }
        await loadFiberDetail(cableId);
        
        // Aguardar um momento para garantir que currentFiberMeta foi atualizado
        setTimeout(() => {
            showContextMenu(event.domEvent.clientX, event.domEvent.clientY);
        }, 100);
    });
}

window.initMap = initMap;

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

// Expor função globalmente para uso em import_kml.js
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
    
    // Adicionar todos os pontos aos bounds
    path.forEach(point => {
        bounds.extend(new google.maps.LatLng(point.lat, point.lng));
    });

    // Ajustar o mapa para mostrar todos os pontos
    map.fitBounds(bounds);

    // Adicionar um pequeno padding
    const padding = { top: 50, right: 50, bottom: 50, left: 50 };
    map.fitBounds(bounds, padding);
}



async function openEditFiberModal() {

    if (!activeFiberId || !currentFiberMeta) {

        alert('Select a cable first.');

        return;

    }

    editingFiberId = activeFiberId;

    if (!manualModal || !manualForm) {

        console.warn('Manual save modal not found.');

        return;

    }



    if (manualRouteNameInput) {

        manualRouteNameInput.value = currentFiberMeta.name || '';

    }

    if (manualSinglePortCheckbox) {

        manualSinglePortCheckbox.checked = Boolean(currentFiberMeta.single_port);

    }



    if (manualOriginDeviceSelect) {

        manualOriginDeviceSelect.value = currentFiberMeta.origin_device_id ? String(currentFiberMeta.origin_device_id) : '';

        await loadPortsForSelect(manualOriginDeviceSelect.value, manualOriginPortSelect);

        if (manualOriginPortSelect) {

            manualOriginPortSelect.value = currentFiberMeta.origin_port_id ? String(currentFiberMeta.origin_port_id) : '';

        }

    }



    if (manualSinglePortCheckbox && manualSinglePortCheckbox.checked) {

        if (manualDestDeviceSelect) {

            manualDestDeviceSelect.value = manualOriginDeviceSelect ? manualOriginDeviceSelect.value : '';

        }

        if (manualDestPortSelect) {

            manualDestPortSelect.innerHTML = '<option value="">-- destino desabilitado --</option>';

            manualDestPortSelect.disabled = true;

        }

    } else {

        if (manualDestDeviceSelect) {

            manualDestDeviceSelect.disabled = false;

            manualDestDeviceSelect.value = currentFiberMeta.dest_device_id ? String(currentFiberMeta.dest_device_id) : '';

            // Aguardar portas carregarem
            await loadPortsForSelect(manualDestDeviceSelect.value, manualDestPortSelect);

            // Set port value AFTER ports are loaded
            // Retry logic para garantir que portas estejam disponíveis
            if (manualDestPortSelect && currentFiberMeta.dest_port_id) {

                const setPortValue = () => {
                    const optionsCount = manualDestPortSelect.options.length;

                    if (optionsCount <= 1) {
                        // Portas ainda não carregaram, tentar novamente
                        setTimeout(setPortValue, 100);
                        return;
                    }

                    manualDestPortSelect.disabled = false;
                    manualDestPortSelect.value = String(currentFiberMeta.dest_port_id);
                };

                setTimeout(setPortValue, 100);

            }

        }

    }

    // Não chamar syncDestinationDevice() aqui porque já configuramos tudo manualmente
    // await syncDestinationDevice();

    if (manualRouteDistanceEl) {

        manualRouteDistanceEl.textContent = `${totalDistance().toFixed(3)} km`;

    }

    const submitButton = manualForm.querySelector('button[type="submit"]');

    if (submitButton) submitButton.textContent = 'Atualizar cabo';



    openManualSaveModal(true);

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

function resetManualSaveForm() {

    if (!manualForm) return;

    manualForm.reset();

    if (manualOriginPortSelect) {

        manualOriginPortSelect.innerHTML = '<option value="">Selecione...</option>';

    }

    if (manualDestPortSelect) {

        manualDestPortSelect.innerHTML = '<option value="">Selecione...</option>';

        manualDestPortSelect.disabled = false;

    }

    if (manualDestDeviceSelect) {

        manualDestDeviceSelect.disabled = false;

    }

    if (manualSinglePortCheckbox) {

        manualSinglePortCheckbox.checked = false;

    }

    if (manualDestNotice) {

        manualDestNotice.classList.add('hidden');

    }

    const submitButton = manualForm.querySelector('button[type="submit"]');

    if (submitButton) submitButton.textContent = 'Salvar rota';

}



function openManualSaveModal(skipReset = false) {

    if (!manualModal || !manualModalContent) {

        console.warn('Manual save modal not found in the DOM.');

        return;

    }

    if (!skipReset) {

        editingFiberId = null;

        resetManualSaveForm();

    }

    if (manualRouteDistanceEl) {

        const distance = totalDistance();

        manualRouteDistanceEl.textContent = `${distance.toFixed(3)} km`;

    }

    manualModal.classList.remove('pointer-events-none');

    manualModal.classList.add('opacity-100');

    manualModalContent.classList.add('opacity-100', 'scale-100');

    manualModalContent.classList.remove('opacity-0', 'scale-95');

    if (manualRouteNameInput) {

        requestAnimationFrame(() => manualRouteNameInput.focus());

    }

    syncDestinationDevice();

    updateEditButtonState();

}



function closeManualSaveModal() {
    if (!manualModal || !manualModalContent) return;
    manualModal.classList.remove('opacity-100');
    manualModal.classList.add('opacity-0');
    manualModalContent.classList.remove('opacity-100', 'scale-100');
    manualModalContent.classList.add('opacity-0', 'scale-95');
    setTimeout(() => {
        manualModal.classList.add('pointer-events-none');
    }, 300);
    editingFiberId = null;
    if (manualForm) {
        const submitButton = manualForm.querySelector('button[type="submit"]');
        if (submitButton) submitButton.textContent = 'Salvar rota';
    }
}
async function loadPortsForSelect(deviceId, targetSelect) {
    if (!targetSelect) return;
    targetSelect.innerHTML = '<option value="">Carregando...</option>';
    if (!deviceId) {
        targetSelect.innerHTML = '<option value="">Selecione...</option>';
        return;
    }
    try {
        const data = await fetchDevicePorts(deviceId);
        targetSelect.innerHTML = '<option value="">Selecione...</option>';
        if (Array.isArray(data.ports)) {
            data.ports.forEach((port) => {
                const option = document.createElement('option');
                option.value = port.id;
                option.textContent = port.name;
                targetSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load ports:', error);
        targetSelect.innerHTML = '<option value="">Falha ao carregar</option>';
    }
}

async function syncDestinationDevice() {
    const singlePort = manualSinglePortCheckbox && manualSinglePortCheckbox.checked;

    if (manualDestNotice) {
        manualDestNotice.classList.toggle('hidden', !singlePort);
    }

    if (manualDestDeviceSelect) {
        manualDestDeviceSelect.disabled = singlePort;
        if (singlePort) {
            manualDestDeviceSelect.value = manualOriginDeviceSelect ? manualOriginDeviceSelect.value : '';
        }
    }

    if (manualDestPortSelect) {
        if (singlePort) {
            manualDestPortSelect.innerHTML = '<option value="">-- destino desabilitado --</option>';
            manualDestPortSelect.disabled = true;
        } else {
            manualDestPortSelect.disabled = false;
            if (manualDestDeviceSelect && manualDestDeviceSelect.value) {
                await loadPortsForSelect(manualDestDeviceSelect.value, manualDestPortSelect);
            } else {
                manualDestPortSelect.innerHTML = '<option value="">Selecione...</option>';
            }
        }
    }
}

async function performCreateFiber(payload) {
    try {
        const data = await createFiberManual(payload);
        alert('Rota criada com sucesso.');
        closeManualSaveModal();
        document.dispatchEvent(new CustomEvent('fiber:cable-created', { detail: { fiberId: data.fiber_id } }));
        await loadAllCablesForVisualization();
    } catch (error) {
        console.error('Erro ao criar rota:', error);
        throw error;
    }
}

async function performUpdateFiber(fiberId, payload) {
    try {
        await updateFiber(fiberId, payload);
        alert('Cabo atualizado com sucesso.');
        closeManualSaveModal();
        clearMapAndResetState();
        await loadFibers();
        await loadAllCablesForVisualization();
    } catch (error) {
        console.error('Erro ao atualizar cabo:', error);
        throw error;
    }
}

async function handleManualFormSubmit(event) {
    event.preventDefault();
    const isEditing = Boolean(editingFiberId);
    const path = getPath();

    if (!isEditing && path.length < 2) {
        alert('Adicione pelo menos dois pontos ao mapa antes de salvar a rota.');
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
        alert('Preencha todos os campos obrigatórios.');
        return;
    }
    if (!singlePort && !payload.dest_port_id) {
        alert('Preencha todos os campos obrigatórios.');
        return;
    }

        // Sempre incluir o path, tanto ao criar quanto ao editar
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
        console.error('Erro ao salvar rota:', error);
        alert(error.message || 'Falha ao salvar a rota.');
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
        alert('Adicione pelo menos dois pontos ao mapa antes de salvar a rota.');
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
    // Botões de toggle para painéis
    document.getElementById('toggleRoutePoints')?.addEventListener('click', () => {
        const panel = document.getElementById('routePointsPanel');
        const helpPanel = document.getElementById('helpPanel');
        if (panel) {
            panel.classList.toggle('hidden');
            // Esconder help se route points for mostrado
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
            // Esconder route points se help for mostrado
            if (!panel.classList.contains('hidden')) {
                routePanel?.classList.add('hidden');
            }
        }
    });
    
    // Menu de contexto - Opções gerais
    document.getElementById('contextLoadAll')?.addEventListener('click', () => {
        hideContextMenu();
        if (activeFiberId) {
            // Recarregar apenas o cabo atual
            loadFiberDetail(activeFiberId);
        } else {
            // Recarregar todos os cabos
            loadAllCablesForVisualization();
        }
    });
    
    document.getElementById('contextImportKML')?.addEventListener('click', () => {
        hideContextMenu();
        openKmlModal();
    });
    
    // Menu de contexto - Opções condicionais (cabo selecionado)
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
        hideContextMenu();
        if (getPath().length >= 2) {
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

if (manualOriginDeviceSelect) {
        manualOriginDeviceSelect.addEventListener('change', async () => {
            await loadPortsForSelect(manualOriginDeviceSelect.value, manualOriginPortSelect);
            await syncDestinationDevice();
        });
    }
    if (manualDestDeviceSelect) {
        manualDestDeviceSelect.addEventListener('change', async () => {
            if (manualDestDeviceSelect.disabled) return;
            await loadPortsForSelect(manualDestDeviceSelect.value, manualDestPortSelect);
        });
    }
    if (manualSinglePortCheckbox) {
        manualSinglePortCheckbox.addEventListener('change', () => {
            syncDestinationDevice();
        });
    }
    if (manualModal) {
        manualModal.addEventListener('click', (event) => {
            if (event.target === manualModal) {
                closeManualSaveModal();
            }
        });
    }

    syncDestinationDevice();
});

window.closeManualSaveModal = closeManualSaveModal;
window.loadFibers = loadFibers;
window.loadFiberDetail = loadFiberDetail;
window.loadPortsForSelect = loadPortsForSelect;

document.addEventListener('fiber:cable-created', async (event) => {
    const fiberId = event.detail?.fiberId;
    
    // Limpar o mapa e resetar estado
    clearMapAndResetState();
    
    // Recarregar lista de cabos
    await loadFibers();
    
    if (fiberId) {
        console.info(`Novo cabo criado: ${fiberId}`);
    }
});
