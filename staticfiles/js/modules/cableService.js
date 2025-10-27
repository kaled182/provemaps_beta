/**
 * cableService.js - Cable Business Logic Module
 * 
 * Encapsulates all cable-related operations:
 * - Loading cable list and details
 * - Creating and updating cables
 * - Deleting cables
 * - Cable visualization on map
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
 * Delete cable by ID.
 * 
 * @param {number|string} cableId - Cable ID
 * @returns {Promise<void>}
 */
export async function deleteCable(cableId) {
    if (!confirm('Confirm cable deletion? This action cannot be undone.')) {
        return;
    }
    
    try {
        await removeFiber(cableId);
        return true;
    } catch (error) {
        console.error('Error deleting cable:', error);
        throw error;
    }
}

/**
 * Load all cables and draw them on the map.
 * 
 * @param {Object} options - Configuration options
 * @param {Function} options.onCableClick - Callback when cable is clicked
 * @param {Object} options.styleOptions - Polyline style options
 * @returns {Promise<Array>} Array of polyline objects
 */
export async function loadAllCablesForVisualization(options = {}) {
    const {
        onCableClick = null,
        styleOptions = {
            strokeColor: '#1E3A8A',
            strokeOpacity: 0.6,
            strokeWeight: 2,
        }
    } = options;
    
    try {
        const data = await fetchFibers();
        const cables = data.fibers || data.cables || [];
        
        if (cables.length === 0) {
            console.info('No cables found for visualization.');
            return [];
        }
        
        const polylines = [];
        let loadedCount = 0;
        
        for (const cable of cables) {
            try {
                const detail = await fetchFiber(cable.id);
                const path = detail.path || [];
                
                if (path.length < 2) continue;
                
                // Create polyline for visualization
                const polyline = createCablePolyline(path, styleOptions);
                
                // Attach click handler if provided
                if (onCableClick && polyline) {
                    polyline.set('cableId', cable.id);
                    polyline.set('cableName', cable.name);
                    
                    polyline.addListener('rightclick', (event) => {
                        event.stop();
                        onCableClick({
                            cableId: cable.id,
                            cableName: cable.name,
                            event: event.domEvent
                        });
                    });
                }
                
                polylines.push(polyline);
                loadedCount++;
                
            } catch (error) {
                console.error(`Error loading cable ${cable.id}:`, error);
            }
        }
        
        console.info(`Visualization: ${loadedCount} cables loaded.`);
        return polylines;
        
    } catch (error) {
        console.error('Error loading cables for visualization:', error);
        throw error;
    }
}

/**
 * Clear all cable polylines from map.
 * 
 * @param {Array} polylines - Array of Google Maps Polyline objects
 */
export function clearCablePolylines(polylines) {
    polylines.forEach(polyline => polyline.setMap(null));
    polylines.length = 0; // Clear array
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
