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
    removeFiber 
} from './apiClient.js';
import { 
    createCablePolyline 
} from './mapCore.js';
import { showErrorMessage } from './uiHelpers.js';

// Stores the callback responsible for making the polyline editable
let _makeEditableCallback = null;
let _mapInstance = null; // Keep a reference to the current map instance

// Local list to manage visualization polylines created by this module
let visualizationPolylines = [];

/**
 * Initializes cableService with external dependencies.
 * @param {object} config - Configuration object.
 * @param {function} config.makeEditableCallback - Callback that makes polylines editable (from fiber_route_builder).
 * @param {google.maps.Map} config.map - Map instance.
 */
export function initCableService(config) {
    if (config && typeof config.makeEditableCallback === 'function') {
        _makeEditableCallback = config.makeEditableCallback;
        console.log("[cableService] makeEditableCallback received.");
    } else {
        console.error("[cableService] Initialization failed: makeEditableCallback is missing or not a function.");
    }
    if (config && config.map) {
        _mapInstance = config.map;
        console.log("[cableService] Map instance received.");
    } else {
         console.error("[cableService] Initialization failed: Map instance is missing.");
    }
}

/**
 * Load all cables and populate dropdown select.
 * 
 * @returns {Promise<Object|null>} Cable data or null on error
 */
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

/**
 * Load cable details by ID.
 * 
 * @param {number|string} cableId - Cable ID
 * @returns {Promise<Object|null>} Cable details or null on error
 */
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

/**
 * Create a new cable.
 * 
 * @param {Object} payload - Cable data
 * @param {string} payload.name - Cable name
 * @param {number} payload.origin_device_id - Origin device ID
 * @param {number} payload.origin_port_id - Origin port ID
 * @param {number} payload.dest_device_id - Destination device ID
 * @param {number} payload.dest_port_id - Destination port ID
 * @param {boolean} payload.single_port - Single port mode
 * @param {Array} payload.path - Array of {lat, lng} points
 * @returns {Promise<Object>} Created cable data
 */
export async function createCable(payload) {
    try {
        const data = await createFiberManual(payload);
        return data;
    } catch (error) {
        console.error('Error creating cable:', error);
        throw error;
    }
}

/**
 * Update existing cable.
 * 
 * @param {number|string} cableId - Cable ID
 * @param {Object} payload - Updated cable data
 * @returns {Promise<Object>} Updated cable data
 */
export async function updateCableData(cableId, payload) {
    try {
        const data = await updateFiber(cableId, payload);
        return data;
    } catch (error) {
        console.error('Error updating cable:', error);
        throw error;
    }
}

/**
 * Clears every visualization polyline created by this module.
 */
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

/**
 * Removes visualization for a specific cable.
 * @param {number|string} cableId
 */
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

/**
 * Loads all cables from the API and draws them on the map for visualization.
 * Usa o callback injetado (_makeEditableCallback) para anexar o evento de right-click.
 * 
 * @returns {Promise<void>}
 */
export async function loadAllCablesForVisualization(options = {}) {
    const {
        excludeCableId = null,
        fitToBounds = true,
    } = options;

    // Ensure initialization completed successfully
    if (!_makeEditableCallback || !_mapInstance) {
        console.error('[loadAllCablesForVisualization] cableService not initialized correctly. Cannot proceed.');
        showErrorMessage("Cable service error. Visualization unavailable.");
        return;
    }

    console.log('[loadAllCablesForVisualization - cableService] Starting to load cables...', { excludeCableId, fitToBounds });
    clearCablePolylines({}); // Clear prior visualization polylines tracked by this module

    try {
        const data = await fetchFibers(); // Usa apiClient
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

            // Use mapCore.createCablePolyline (does not interfere with the editing polyline)
            const viewPolyline = createCablePolyline(validPath, {
                strokeColor: '#0000FF', // Blue stroke for visualization
                strokeOpacity: 0.6,
                strokeWeight: 4,
                clickable: true,
                map: _mapInstance // Ensure we reuse the current map instance
            });

            if (viewPolyline) {
                viewPolyline.set('cableId', cable.id);
                visualizationPolylines.push({ id: cable.id, polyline: viewPolyline }); // Track in local list
                drawnCount++;

                if (bounds) {
                    validPath.forEach((point) => {
                        bounds.extend(new google.maps.LatLng(point.lat, point.lng));
                    });
                }

                // Call the provided callback with the newly created polyline
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

/**
 * Delete cable by ID with callback support.
 * 
 * @param {number|string} cableId - Cable ID
 * @param {Object} callbacks - Success/error callbacks
 * @param {Function} callbacks.onSuccess - Called on successful deletion
 * @param {Function} callbacks.onError - Called on error
 * @returns {Promise<void>}
 */
export async function deleteCable(cableId, callbacks = {}) {
    try {
        await removeFiber(cableId);
        console.log(`[cableService] Cable ${cableId} deleted via API.`);

    // Remove the corresponding polyline from the map and local cache
        removeCableVisualization(cableId);

        if (callbacks.onSuccess) callbacks.onSuccess();

    } catch (error) {
        console.error(`[cableService] Error deleting cable ${cableId}:`, error);
        if (callbacks.onError) callbacks.onError(error);
        throw error;
    }
}

/**
 * Build default path from cable endpoints (origin and destination).
 * Used when cable has no explicit path.
 * 
 * @param {Object} cable - Cable data
 * @param {Object} cable.origin - Origin endpoint {lat, lng}
 * @param {Object} cable.destination - Destination endpoint {lat, lng}
 * @returns {Array} Array of {lat, lng} points
 * @private
 */
function buildDefaultPathFromEndpoints(cable) {
    const points = [];
    
    if (cable.origin?.lat != null && cable.origin?.lng != null) {
        points.push({ lat: cable.origin.lat, lng: cable.origin.lng });
    }
    
    if (cable.destination?.lat != null && cable.destination?.lng != null) {
        points.push({ 
            lat: cable.destination.lat, 
            lng: cable.destination.lng 
        });
    }
    
    return points;
}

/**
 * Validate cable payload before submission.
 * 
 * @param {Object} payload - Cable data to validate
 * @param {boolean} isEditing - Whether this is an edit operation
 * @returns {Object} Validation result {valid: boolean, error: string|null}
 */
export function validateCablePayload(payload, isEditing = false) {
    if (!payload.name || !payload.name.trim()) {
        return { valid: false, error: 'Cable name is required.' };
    }
    
    if (!payload.origin_device_id || !payload.origin_port_id) {
        return { 
            valid: false, 
            error: 'Origin device and port are required.' 
        };
    }
    
    if (!payload.single_port && !payload.dest_port_id) {
        return { 
            valid: false, 
            error: 'Destination port is required (or enable Single Port mode).' 
        };
    }
    
    if (!isEditing && (!payload.path || payload.path.length < 2)) {
        return { 
            valid: false, 
            error: 'Cable path must have at least 2 points.' 
        };
    }
    
    return { valid: true, error: null };
}
