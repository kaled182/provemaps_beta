// mapCore.js - Google Maps drawing and interaction
// Responsibilities:
//  - Initialize Google Maps instance
//  - Draw/update polylines
//  - Manage markers (create, drag, remove)
//  - Fit map bounds to path
//  - Handle map click events

let map = null;
let polyline = null;
let markers = [];
let clickCallback = null;
let rightClickCallback = null;

// Initialize map
export function initMap(elementId, options = {}) {
  const defaults = {
    center: { lat: -16.6869, lng: -49.2648 },
    zoom: 6,
    mapTypeId: 'terrain',
  };
  map = new google.maps.Map(
    document.getElementById(elementId),
    { ...defaults, ...options }
  );

  // Setup click listeners
  map.addListener('click', (event) => {
    if (clickCallback) {
      clickCallback({
        lat: event.latLng.lat(),
        lng: event.latLng.lng(),
      });
    }
  });

  map.addListener('rightclick', (event) => {
    if (event.domEvent && typeof event.domEvent.stopPropagation === 'function') {
      event.domEvent.stopPropagation();
    } else if (typeof event.stop === 'function') {
      event.stop();
    }
    if (rightClickCallback) {
      rightClickCallback({
        lat: event.latLng.lat(),
        lng: event.latLng.lng(),
        clientX: event.domEvent?.clientX ?? 0,
        clientY: event.domEvent?.clientY ?? 0,
      });
    }
  });

  return map;
}

// Get map instance
export function getMap() {
  return map;
}

// Set click handler
export function onMapClick(callback) {
  clickCallback = callback;
}

// Set right-click handler
export function onMapRightClick(callback) {
  rightClickCallback = callback;
}

// Draw or update polyline
export function drawPolyline(path, options = {}) {
  if (polyline) {
    polyline.setMap(null);
  }
  const defaults = {
    strokeColor: '#2563eb',
    strokeWeight: 4,
    strokeOpacity: 0.9,
    clickable: true,
  };
  polyline = new google.maps.Polyline({
    path,
    map,
    ...defaults,
    ...options,
  });
  return polyline;
}

// Get current polyline
export function getPolyline() {
  return polyline;
}

// Add right-click listener to polyline
export function onPolylineRightClick(callback) {
  if (polyline) {
    polyline.addListener('rightclick', (event) => {
      if (event.domEvent && typeof event.domEvent.stopPropagation === 'function') {
        event.domEvent.stopPropagation();
      } else if (typeof event.stop === 'function') {
        event.stop();
      }
      callback({
        clientX: event.domEvent?.clientX ?? 0,
        clientY: event.domEvent?.clientY ?? 0,
      });
    });
  }
}

// Clear polyline
export function clearPolyline() {
  if (polyline) {
    polyline.setMap(null);
    polyline = null;
  }
}

// Add draggable marker
export function addMarker(position, options = {}) {
  const defaults = {
    draggable: true,
    map,
  };
  const marker = new google.maps.Marker({
    position,
    ...defaults,
    ...options,
  });
  markers.push(marker);
  return marker;
}

// Remove specific marker
export function removeMarker(marker) {
  const index = markers.indexOf(marker);
  if (index > -1) {
    marker.setMap(null);
    markers.splice(index, 1);
    return true;
  }
  return false;
}

// Clear all markers
export function clearMarkers() {
  markers.forEach((m) => m.setMap(null));
  markers = [];
}

// Get all markers
export function getMarkers() {
  return markers.slice();
}

// Fit map to show all points in path
export function fitMapToBounds(path, padding = 50) {
  if (!map || !path || path.length === 0) return;
  const bounds = new google.maps.LatLngBounds();
  path.forEach((point) => {
    bounds.extend(new google.maps.LatLng(point.lat, point.lng));
  });
  map.fitBounds(bounds);
  if (typeof padding === 'number') {
    const uniformPadding = { top: padding, right: padding, bottom: padding, left: padding };
    map.fitBounds(bounds, uniformPadding);
  } else {
    map.fitBounds(bounds, padding);
  }
}

// Create cable polyline for visualization (non-editable)
export function createCablePolyline(path, options = {}) {
  const defaults = {
    strokeColor: '#1E3A8A',
    strokeOpacity: 0.6,
    strokeWeight: 2,
    clickable: true,
  };
  return new google.maps.Polyline({
    path,
    geodesic: true,
    map,
    ...defaults,
    ...options,
  });
}

// Attach right-click to external polyline
export function attachPolylineRightClick(polylineInstance, callback) {
  polylineInstance.addListener('rightclick', (event) => {
    if (event.domEvent && typeof event.domEvent.stopPropagation === 'function') {
      event.domEvent.stopPropagation();
    } else if (typeof event.stop === 'function') {
      event.stop();
    }
    callback({
      clientX: event.domEvent?.clientX ?? 0,
      clientY: event.domEvent?.clientY ?? 0,
    });
  });
}

/**
 * Get the current map instance
 * @returns {google.maps.Map|null} The map instance or null if not initialized
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
  
  // Clear event listeners if map exists
  if (map) {
    google.maps.event.clearInstanceListeners(map);
  }
  
  // Reset references
  map = null;
  polyline = null;
  markers = [];
  clickCallback = null;
  rightClickCallback = null;
}

/**
 * Alterna o modo de edição de um caminho (polyline)
 * 
 * @param {boolean} isEditable - true = modo edição, false = modo visualização
 * @param {HTMLElement} mapDiv - Container do mapa (para feedback de cursor)
 * 
 * Comportamento:
 * - Google Maps: polyline.setEditable() + polyline.setDraggable()
 * - Cursor: crosshair (edit) / grab (read)
 */
export function setPathEditable(isEditable, mapDiv = null) {
  if (!polyline) {
    console.warn('[mapCore] setPathEditable: polyline is null');
    return;
  }

  // Google Maps API
  polyline.setEditable(isEditable);
  polyline.setDraggable(isEditable);
  console.log(`[mapCore] Google Maps polyline editable: ${isEditable}`);

  // Feedback visual: cursor do mapa
  if (mapDiv) {
    mapDiv.style.cursor = isEditable ? 'crosshair' : 'grab';
    console.log(`[mapCore] Map cursor: ${mapDiv.style.cursor}`);
  }
}
