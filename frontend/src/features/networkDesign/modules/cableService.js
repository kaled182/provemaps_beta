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
    fitMapToBounds,
} from './mapCore-refactored.js';
import { showErrorMessage } from './uiHelpers.js';

let _makeEditableCallback = null;
let _mapInstance = null;
let visualizationPolylines = [];
let activeFolderFilter = null;    // null = no folder filter active
let activeFolderFilterIds = null; // Set of all folder IDs in the selected hierarchy (null = exact match)
let activeTypeFilters = null;     // null = show all types; Set of strings = show only those types
let _loadGeneration = 0; // incremented each call; allows in-flight requests to self-cancel
let _apiGroups = []; // groups fetched from /cable-groups/ API

export function setApiGroups(groups) {
    _apiGroups = Array.isArray(groups) ? groups : [];
}

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

function _setPolylineVisibility(rec, visible) {
    try {
        const mapInstance = rec.polyline.mapboxMap || rec.polyline.map?.mapboxMap;
        if (mapInstance && rec.polyline.layerId) {
            const viz = visible ? 'visible' : 'none';
            mapInstance.setLayoutProperty(rec.polyline.layerId, 'visibility', viz);
            if (rec.polyline.hitLayerId) {
                mapInstance.setLayoutProperty(rec.polyline.hitLayerId, 'visibility', viz);
            }
        }
    } catch (_) { /* polyline may have been removed */ }
}

function _getEffectiveVisibility(rec) {
    let folderOk;
    if (activeFolderFilter === null) {
        folderOk = true;
    } else if (activeFolderFilterIds !== null) {
        folderOk = activeFolderFilterIds.has(rec.folderId);
    } else {
        folderOk = rec.folderId === activeFolderFilter;
    }
    const typeOk = activeTypeFilters === null || activeTypeFilters.has(rec.cableType ?? '');
    return rec.groupVisible !== false && folderOk && typeOk;
}

function safeRemovePolyline(polyline) {
    if (!polyline || typeof polyline.remove !== 'function') return;
    try {
        polyline.remove();
    } catch (err) {
        // Map may have been destroyed already; ignore stale-reference errors
        console.warn('[cableService] safeRemovePolyline: ignored error on stale polyline', err?.message);
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
        safeRemovePolyline(record?.polyline);
        return false;
    });
}

export function removeCableVisualization(cableId) {
    if (!visualizationPolylines.length) return;
    const idStr = String(cableId);
    const remaining = [];
    visualizationPolylines.forEach((record) => {
        if (record && String(record.id) === idStr) {
            safeRemovePolyline(record.polyline);
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

    // Bump generation: any prior in-flight call will see a stale generation and abort.
    const myGeneration = ++_loadGeneration;

    console.log('[loadAllCablesForVisualization - cableService] Starting to load cables...', { excludeCableId, fitToBounds });
    clearCablePolylines({});

    try {
        const data = await fetchFibers();

        // A newer call started while we were fetching — discard this result.
        if (myGeneration !== _loadGeneration) {
            console.log('[loadAllCablesForVisualization - cableService] Stale load discarded (newer call in progress).');
            return;
        }
        const cables = (data && (data.fibers || data.cables)) ? (data.fibers || data.cables) :
                       Array.isArray(data) ? data : [];

        console.log(`[loadAllCablesForVisualization - cableService] Fetched ${cables.length} cables.`);

        if (cables.length === 0) {
            console.log('[loadAllCablesForVisualization - cableService] No cables to display.');
            return;
        }

        // Collect all points for bounds calculation
        const allPoints = [];

        // Track how many fallback cables share each site point, to spread them out.
        const siteOffsetCount = new Map();
        // 8 compass directions (lat offset, lng offset) — ~11 km each
        const FALLBACK_OFFSETS = [
            [0.1, 0], [0.1, 0.1], [0, 0.1], [-0.1, 0.1],
            [-0.1, 0], [-0.1, -0.1], [0, -0.1], [0.1, -0.1],
        ];

        let drawnCount = 0;
        cables.forEach((cable) => {
            if (excludeCableId != null && String(cable?.id) === String(excludeCableId)) {
                return;
            }
            if (!cable || cable.id == null) {
                console.warn(`[cableService] Skipping cable ID ${cable?.id}: missing cable data.`);
                return;
            }

            // Build path: use stored path if valid, else fall back to straight line
            // between device coordinates (recovers cables whose paths were wiped).
            let validPath = [];
            let isFallbackPath = false;
            if (Array.isArray(cable.path)) {
                validPath = cable.path.filter(p => p && typeof p.lat === 'number' && typeof p.lng === 'number');
            }
            if (validPath.length < 2) {
                // Fallback: straight line from origin to destination site coordinates.
                // If both endpoints share the same coordinates (intra-site cable whose
                // path was wiped), add a visible offset so the polyline is findable.
                const oLat = cable.origin?.lat;
                const oLng = cable.origin?.lng;
                const dLat = cable.destination?.lat;
                const dLng = cable.destination?.lng;
                if (oLat != null && oLng != null && dLat != null && dLng != null) {
                    const isSamePoint = oLat === dLat && oLng === dLng;
                    const p1 = { lat: oLat, lng: oLng };
                    let p2;
                    if (isSamePoint) {
                        const siteKey = `${oLat},${oLng}`;
                        const idx = siteOffsetCount.get(siteKey) ?? 0;
                        siteOffsetCount.set(siteKey, idx + 1);
                        const [dLa, dLo] = FALLBACK_OFFSETS[idx % FALLBACK_OFFSETS.length];
                        p2 = { lat: oLat + dLa, lng: oLng + dLo };
                    } else {
                        p2 = { lat: dLat, lng: dLng };
                    }
                    validPath = [p1, p2];
                    isFallbackPath = true;
                    console.warn(`[cableService] Cable ID ${cable.id} has no stored path — using ${isSamePoint ? 'offset-point' : 'straight-line'} fallback (orange).`);
                } else {
                    console.warn(`[cableService] Skipping cable ID ${cable.id}: no path and no device coordinates.`);
                    return;
                }
            }

            const viewPolyline = createCablePolyline(validPath, {
                strokeColor: isFallbackPath ? '#f97316' : '#0000FF',
                strokeOpacity: isFallbackPath ? 0.9 : 0.6,
                strokeWeight: isFallbackPath ? 5 : 4,
                clickable: true,
            });

            if (viewPolyline) {
                const groupId = cable.cable_group?.id ?? null;
                const groupName = cable.cable_group?.name ?? null;
                const folderId = cable.folder?.id ?? null;
                const cableType = cable.cable_type ? String(cable.cable_type.id) : '';
                visualizationPolylines.push({ id: cable.id, name: cable.name, polyline: viewPolyline, groupId, groupName, folderId, cableType, groupVisible: true, isFallback: isFallbackPath });
                drawnCount++;

                // Add points to bounds calculation
                if (fitToBounds) {
                    allPoints.push(...validPath);
                }

                _makeEditableCallback(viewPolyline, cable.id, cable.name || `Cable ${cable.id}`);

            } else {
                console.warn(`[cableService] Failed to create polyline object for cable ID ${cable.id}`);
            }
        });
        console.log(`[loadAllCablesForVisualization - cableService] Finished drawing ${drawnCount} valid cable polylines.`);

        if (fitToBounds && allPoints.length > 0) {
            fitMapToBounds(allPoints, 50);
        }

        // Reapply active folder filter to newly created polylines
        if (activeFolderFilter !== null) {
            for (const rec of visualizationPolylines) {
                if (rec.polyline) {
                    _setPolylineVisibility(rec, _getEffectiveVisibility(rec));
                }
            }
        }

        // Notify Vue to refresh layer groups, type items and folder counts
        if (typeof window.__ndRefreshLayerGroups === 'function') {
            window.__ndRefreshLayerGroups();
        }
        if (typeof window.__ndRefreshTypeItems === 'function') {
            window.__ndRefreshTypeItems();
        }
        if (typeof window.__ndRefreshFolderCounts === 'function') {
            window.__ndRefreshFolderCounts();
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
    activeFolderFilter = null;
}

/**
 * Returns distinct groups present in loaded cables.
 * Each entry: { id: number|null, name: string }
 * null id = cables without a group ("Sem grupo").
 */
export function getLoadedGroups() {
    const seen = new Map();
    // Seed with groups known from the API (ensures new groups without cables appear)
    for (const g of _apiGroups) {
        seen.set(g.id, { id: g.id, name: g.name });
    }
    // Augment with groups present in loaded polylines (covers cables with deleted group refs)
    for (const rec of visualizationPolylines) {
        const key = rec.groupId ?? '__none__';
        if (!seen.has(key)) {
            seen.set(key, { id: rec.groupId, name: rec.groupName ?? 'Sem grupo' });
        }
    }
    // Sort: named groups first, then "Sem grupo"
    return [...seen.values()].sort((a, b) => {
        if (a.id === null) return 1;
        if (b.id === null) return -1;
        return a.name.localeCompare(b.name);
    });
}

/**
 * Return a Map of groupKey -> cable count from loaded polylines.
 * groupKey is the group id (number) or null for cables without a group.
 * @returns {Map<number|null, number>}
 */
export function getGroupCounts() {
    const counts = new Map();
    for (const rec of visualizationPolylines) {
        const key = rec.groupId ?? null;
        counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return counts;
}

/**
 * Returns a Map<cableType|'', count> for all loaded cables.
 */
export function getTypeCounts() {
    const counts = new Map();
    for (const rec of visualizationPolylines) {
        const key = rec.cableType || '';
        counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return counts;
}

/**
 * Filter map display to show only cables matching the given set of types.
 * Pass null to clear the type filter.
 * @param {Set<string>|null} typeSet - Set of cable_type values ('backbone', 'drop', etc.) or null for all
 */
export function setTypeFilter(typeSet) {
    activeTypeFilters = typeSet;
    for (const rec of visualizationPolylines) {
        if (rec.polyline) {
            _setPolylineVisibility(rec, _getEffectiveVisibility(rec));
        }
    }
}

/**
 * Temporarily highlight a cable polyline by ID (yellow flash, reverts after 3.5 s).
 */
export function highlightCable(cableId) {
    const rec = visualizationPolylines.find(r => String(r.id) === String(cableId));
    if (!rec || !rec.polyline) return;
    const map = rec.polyline.mapboxMap;
    const layerId = rec.polyline.layerId;
    if (!map || !map.getLayer(layerId)) return;

    const origColor = map.getPaintProperty(layerId, 'line-color');
    const origWidth = map.getPaintProperty(layerId, 'line-width');

    map.setPaintProperty(layerId, 'line-color', '#facc15');
    map.setPaintProperty(layerId, 'line-width', 8);

    setTimeout(() => {
        if (map.getLayer(layerId)) {
            map.setPaintProperty(layerId, 'line-color', origColor);
            map.setPaintProperty(layerId, 'line-width', origWidth);
        }
    }, 3500);
}

/**
 * Return cables that were drawn using a fallback path (no stored route).
 * @returns {{ id: number, name: string }[]}
 */
export function getFallbackCables() {
    return visualizationPolylines
        .filter(rec => rec.isFallback)
        .map(rec => ({ id: rec.id, name: rec.name }));
}

/**
 * Show or hide cables belonging to a specific group.
 * Respects active folder filter when determining effective visibility.
 * @param {number|null} groupId  null = cables without a group
 * @param {boolean} visible
 */
export function setGroupLayerVisible(groupId, visible) {
    for (const rec of visualizationPolylines) {
        const matches = groupId === null
            ? rec.groupId === null
            : rec.groupId === groupId;
        if (matches && rec.polyline) {
            rec.groupVisible = visible;
            _setPolylineVisibility(rec, _getEffectiveVisibility(rec));
        }
    }
}

/**
 * Filter map display to show only cables in a specific folder.
 * Pass null to clear the filter and show all cables (respecting group layer state).
 * @param {number|null} folderId
 */
export function setFolderFilter(folderId, folderIds = null) {
    activeFolderFilter = folderId;
    activeFolderFilterIds = folderIds; // Set of IDs covering the full sub-hierarchy
    for (const rec of visualizationPolylines) {
        if (rec.polyline) {
            _setPolylineVisibility(rec, _getEffectiveVisibility(rec));
        }
    }
}
