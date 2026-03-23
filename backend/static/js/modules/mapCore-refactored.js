/**
 * mapCore.js - Refatorado para usar Provider Pattern
 * 
 * API compatível com código legado, mas usa providers abstratos (Google, Mapbox, etc.)
 * Responsabilidades:
 *  - Initialize map instance (provider-agnostic)
 *  - Draw/update polylines
 *  - Manage markers (create, drag, remove)
 *  - Fit map bounds to path
 *  - Handle map click events
 */

import { createMap, getCurrentProviderName } from '@/providers/maps/MapProviderFactory.js';

let map = null;
let polyline = null;
let markers = [];
let clickCallback = null;
let rightClickCallback = null;

/**
 * Initialize map using configured provider
 * @param {string} elementId - ID do elemento DOM
 * @param {Object} options - Opções do mapa
 * @returns {Promise<IMap>}
 */
export async function initMap(elementId, options = {}) {
  const defaults = {
    center: { lat: -16.6869, lng: -49.2648 },
    zoom: 6,
    mapTypeId: 'terrain',
  };

  const element = document.getElementById(elementId);
  if (!element) {
    throw new Error(`Element with id '${elementId}' not found`);
  }

  const providerName = await getCurrentProviderName();
  console.log(`[mapCore] Initializing map with provider: ${providerName}`);

  // Create map usando factory (retorna IMap)
  map = await createMap(element, { ...defaults, ...options });

  // Setup click listeners
  map.on('click', (event) => {
    if (clickCallback) {
      clickCallback({
        lat: event.lat,
        lng: event.lng,
      });
    }
  });

  map.on('rightclick', (event) => {
    if (rightClickCallback) {
      rightClickCallback({
        lat: event.lat,
        lng: event.lng,
        clientX: event.clientX,
        clientY: event.clientY,
      });
    }
  });

  console.log('[mapCore] ✅ Map initialized successfully');
  return map;
}

/**
 * Get map instance
 * @returns {IMap|null}
 */
export function getMap() {
  return map;
}

/**
 * Set click handler
 * @param {Function} callback
 */
export function onMapClick(callback) {
  clickCallback = callback;
}

/**
 * Set right-click handler
 * @param {Function} callback
 */
export function onMapRightClick(callback) {
  rightClickCallback = callback;
}

/**
 * Draw or update polyline
 * @param {Array<{lat: number, lng: number}>} path
 * @param {Object} options
 * @returns {IPolyline}
 */
export function drawPolyline(path, options = {}) {
  if (polyline) {
    polyline.remove();
  }

  const defaults = {
    strokeColor: '#2563eb',
    strokeWeight: 4,
    strokeOpacity: 0.9,
    clickable: true,
  };

  polyline = map.createPolyline({
    path,
    ...defaults,
    ...options,
  });

  return polyline;
}

/**
 * Get current polyline
 * @returns {IPolyline|null}
 */
export function getPolyline() {
  return polyline;
}

/**
 * Add right-click listener to polyline
 * @param {Function} callback
 */
export function onPolylineRightClick(callback) {
  if (polyline) {
    polyline.on('rightclick', (event) => {
      callback({
        clientX: event.clientX,
        clientY: event.clientY,
      });
    });
  }
}

/**
 * Clear polyline
 */
export function clearPolyline() {
  if (polyline) {
    polyline.remove();
    polyline = null;
  }
}

/**
 * Add draggable marker
 * @param {{lat: number, lng: number}} position
 * @param {Object} options
 * @returns {IMarker}
 */
export function addMarker(position, options = {}) {
  const defaults = {
    draggable: true,
  };

  const marker = map.createMarker({
    position,
    ...defaults,
    ...options,
  });

  markers.push(marker);
  return marker;
}

/**
 * Remove specific marker
 * @param {IMarker} marker
 * @returns {boolean}
 */
export function removeMarker(marker) {
  const index = markers.indexOf(marker);
  if (index > -1) {
    marker.remove();
    markers.splice(index, 1);
    return true;
  }
  return false;
}

/**
 * Clear all markers
 */
export function clearMarkers() {
  markers.forEach((m) => m.remove());
  markers = [];
}

/**
 * Get all markers
 * @returns {IMarker[]}
 */
export function getMarkers() {
  return markers.slice();
}

/**
 * Fit map to show all points in path
 * @param {Array<{lat: number, lng: number}>} path
 * @param {number|Object} padding
 */
export function fitMapToBounds(path, padding = 50) {
  if (!map || !path || path.length === 0) return;
  map.fitBounds(path, padding);
}

/**
 * Create cable polyline for visualization (non-editable)
 * @param {Array<{lat: number, lng: number}>} path
 * @param {Object} options
 * @returns {IPolyline}
 */
export function createCablePolyline(path, options = {}) {
  const defaults = {
    strokeColor: '#1E3A8A',
    strokeOpacity: 0.6,
    strokeWeight: 2,
    clickable: true,
  };

  return map.createPolyline({
    path,
    geodesic: true,
    ...defaults,
    ...options,
  });
}

/**
 * Attach right-click to external polyline
 * @param {IPolyline} polylineInstance
 * @param {Function} callback
 */
export function attachPolylineRightClick(polylineInstance, callback) {
  polylineInstance.on('rightclick', (event) => {
    callback({
      clientX: event.clientX,
      clientY: event.clientY,
    });
  });
}

/**
 * Get the current map instance
 * @returns {IMap|null}
 */
export function getMapInstance() {
  return map;
}

/**
 * Cleanup map resources
 */
export function cleanupMap() {
  clearPolyline();
  clearMarkers();

  if (map) {
    map.destroy();
  }

  map = null;
  polyline = null;
  markers = [];
  clickCallback = null;
  rightClickCallback = null;

  console.log('[mapCore] ✅ Map resources cleaned up');
}

/**
 * Set path editable mode
 * @param {boolean} isEditable
 * @param {HTMLElement} mapDiv
 */
export function setPathEditable(isEditable, mapDiv = null) {
  if (!polyline) {
    console.warn('[mapCore] setPathEditable: polyline is null');
    return;
  }

  polyline.setEditable(isEditable);
  polyline.setDraggable(isEditable);

  console.log(`[mapCore] Polyline editable: ${isEditable}`);

  // Feedback visual: cursor do mapa
  if (mapDiv) {
    mapDiv.style.cursor = isEditable ? 'crosshair' : 'grab';
  }
}
