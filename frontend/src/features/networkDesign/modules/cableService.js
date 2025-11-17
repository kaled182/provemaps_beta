/**
 * cableService.js - Cable Business Logic Module
 *
 * Encapsulates all cable-related operations with callback injection pattern:
 * - Loading cable list and details
 * - Creating and updating cables
 * - Deleting cables
 * - Cable visualization on map with injected makeEditable callback
 * - Cable path management
 *
 * @module cableService
 */

import {
    fetchFibers,
    fetchFiber,
    createFiberManual,
    updateFiber,
    removeFiber,
} from './apiClient.js';
import {
    createCablePolyline,
} from './mapCore.js';
import { showErrorMessage } from './uiHelpers.js';

let _makeEditableCallback = null;
let _mapInstance = null;
let visualizationPolylines = [];
let allCablesPolylines = [];

export function initCableService(config) {
    if (config && typeof config.makeEditableCallback === 'function') {
        _makeEditableCallback = config.makeEditableCallback;
        console.log('[cableService] makeEditableCallback received.');
    } else {
        console.error('[cableService] Initialization failed: makeEditableCallback is missing or not a function.');
    }
    if (config && config.map) {
        _mapInstance = config.map;
        console.log('[cableService] Map instance received.');
    } else {
         console.error('[cableService] Initialization failed: Map instance is missing.');
    }
}

export async function loadCableList() {
    try {
        const data = await fetchFibers();
        const select = document.getElementById('fiberSelect');

        if (select) {
            select.innerHTML = '<option value="">-- select a cable --</option>';
            const cables = (data && (data.fibers || data.cables))
                ? (data.fibers || data.cables)
                : [];

            cables.forEach((cable) => {
                const option = document.createElement('option');
                option.value = cable.id;
                option.textContent = cable.name;
                select.appendChild(option);
            });
        }

        return data;
    } catch (error) {
        console.error('Error fetching cable list:', error);
        return null;
    }
}

export async function loadCableDetails(cableId) {
    try {
        const data = await fetchFiber(cableId);
        return {
            id: data.id,
            name: data.name || '',
            origin_device_id: data.origin?.device_id || null,
            origin_port_id: data.origin?.port_id || null,
            dest_device_id: data.destination?.device_id || null,
            dest_port_id: data.destination?.port_id || null,
            single_port: Boolean(data.single_port),
            path: (data.path && data.path.length)
                ? data.path
                : buildDefaultPathFromEndpoints(data),
        };
    } catch (error) {
        console.error('Error loading cable details:', error);
        throw error;
    }
}

export async function createCable(payload) {
    try {
        const data = await createFiberManual(payload);
        return data;
    } catch (error) {
        console.error('Error creating cable:', error);
        throw error;
    }
}

export async function updateCableData(cableId, payload) {
    try {
        const data = await updateFiber(cableId, payload);
        return data;
    } catch (error) {
        console.error('Error updating cable:', error);
        throw error;
    }
}

export function clearCablePolylines({ excludeCableId = null } = {}) {
    if (!visualizationPolylines.length) {
        return;
    }
    console.log(`[cableService] Clearing ${visualizationPolylines.length} visualization polylines (exclude=${excludeCableId ?? 'none'}).`);
    visualizationPolylines = visualizationPolylines.filter((record) => {
        if (excludeCableId != null && String(record?.id) === String(excludeCableId)) {
            return true;
        }
        if (record?.polyline && typeof record.polyline.setMap === 'function') {
            record.polyline.setMap(null);
        }
        return false;
    });
}

export function removeCableVisualization(cableId) {
    if (!visualizationPolylines.length) return;
    const idStr = String(cableId);
    const remaining = [];
    visualizationPolylines.forEach((record) => {
        if (record && String(record.id) === idStr) {
            if (record.polyline && typeof record.polyline.setMap === 'function') {
                record.polyline.setMap(null);
            }
        } else {
            remaining.push(record);
        }
    });
    visualizationPolylines = remaining;
}

export async function loadAllCablesForVisualization(options = {}) {
    const {
        excludeCableId = null,
        fitToBounds = true,
    } = options;

    if (!_makeEditableCallback || !_mapInstance) {
        console.error('[loadAllCablesForVisualization] cableService not initialized correctly. Cannot proceed.');
        showErrorMessage('Cable service error. Visualization unavailable.');
        return;
    }

    console.log('[loadAllCablesForVisualization - cableService] Starting to load cables...', { excludeCableId, fitToBounds });
    clearCablePolylines({});

    try {
        const data = await fetchFibers();
        const cables = (data && (data.fibers || data.cables)) ? (data.fibers || data.cables) :
                       Array.isArray(data) ? data : [];

        console.log(`[loadAllCablesForVisualization - cableService] Fetched ${cables.length} cables.`);

        if (cables.length === 0) {
            console.log('[loadAllCablesForVisualization - cableService] No cables to display.');
            return;
        }

        let bounds = null;
        if (fitToBounds && typeof google !== 'undefined' && google.maps) {
            bounds = new google.maps.LatLngBounds();
        }

        let drawnCount = 0;
        cables.forEach((cable) => {
            if (excludeCableId != null && String(cable?.id) === String(excludeCableId)) {
                return;
            }
            if (!cable || cable.id == null || !cable.path || !Array.isArray(cable.path) || cable.path.length < 2) {
                console.warn(`[cableService] Skipping cable ID ${cable?.id} due to insufficient path data.`);
                return;
            }
             const validPath = cable.path.filter(p => p && typeof p.lat === 'number' && typeof p.lng === 'number');
             if (validPath.length < 2) {
                 console.warn(`[cableService] Skipping cable ID ${cable.id} after filtering invalid points (remaining: ${validPath.length}).`);
                 return;
             }

            const viewPolyline = createCablePolyline(validPath, {
                strokeColor: '#0000FF',
                strokeOpacity: 0.6,
                strokeWeight: 4,
                clickable: true,
                map: _mapInstance,
            });

            if (viewPolyline) {
                viewPolyline.set('cableId', cable.id);
                visualizationPolylines.push({ id: cable.id, polyline: viewPolyline });
                drawnCount++;

                if (bounds) {
                    validPath.forEach((point) => {
                        bounds.extend(new google.maps.LatLng(point.lat, point.lng));
                    });
                }

                _makeEditableCallback(viewPolyline, cable.id, cable.name || `Cable ${cable.id}`);

            } else {
                console.warn(`[cableService] Failed to create polyline object for cable ID ${cable.id}`);
            }
        });
        console.log(`[loadAllCablesForVisualization - cableService] Finished drawing ${drawnCount} valid cable polylines.`);

        if (bounds) {
            try {
                _mapInstance.fitBounds(bounds);
            } catch (err) {
                console.warn('[cableService] Failed to fit bounds for visualization:', err);
            }
        }

    } catch (error) {
        console.error('[loadAllCablesForVisualization - cableService] Error loading or drawing cables:', error);
        showErrorMessage('Failed to load cable visualizations.');
    }
}

export async function deleteCable(cableId, callbacks = {}) {
    try {
        await removeFiber(cableId);
        console.log(`[cableService] Cable ${cableId} deleted via API.`);

        removeCableVisualization(cableId);

        if (callbacks.onSuccess) callbacks.onSuccess();

    } catch (error) {
        console.error(`[cableService] Error deleting cable ${cableId}:`, error);
        if (callbacks.onError) callbacks.onError(error);
        throw error;
    }
}

function buildDefaultPathFromEndpoints(cable) {
    const points = [];

    if (cable.origin?.lat != null && cable.origin?.lng != null) {
        points.push({ lat: cable.origin.lat, lng: cable.origin.lng });
    }

    if (cable.destination?.lat != null && cable.destination?.lng != null) {
        points.push({
            lat: cable.destination.lat,
            lng: cable.destination.lng,
        });
    }

    return points;
}

export function validateCablePayload(payload, isEditing = false) {
    if (!payload.name || !payload.name.trim()) {
        return { valid: false, error: 'Cable name is required.' };
    }

    if (!payload.origin_device_id || !payload.origin_port_id) {
        return {
            valid: false,
            error: 'Origin device and port are required.',
        };
    }

    if (!payload.single_port && !payload.dest_port_id) {
        return {
            valid: false,
            error: 'Destination port is required (or enable Single Port mode).',
        };
    }

    if (!isEditing && (!payload.path || payload.path.length < 2)) {
        return {
            valid: false,
            error: 'Cable path must have at least 2 points.',
        };
    }

    return { valid: true, error: null };
}

export function cleanupCableService() {
    clearCablePolylines();
    _mapInstance = null;
    allCablesPolylines = [];
}
