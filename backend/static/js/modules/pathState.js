// pathState.js - Path and marker state management
// Responsibilities:
//  - Maintain currentPath array (lat/lng coordinates)
//  - Calculate total distance using Haversine formula
//  - Provide setters/getters for path manipulation
//  - Emit path change events for UI updates

const EARTH_RADIUS_KM = 6371;

let currentPath = [];
let pathChangeCallbacks = [];

function haversineKm(pointA, pointB) {
  const dLat = (pointB.lat - pointA.lat) * Math.PI / 180;
  const dLng = (pointB.lng - pointA.lng) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(pointA.lat * Math.PI / 180) *
    Math.cos(pointB.lat * Math.PI / 180) *
    Math.sin(dLng / 2) ** 2;
  return EARTH_RADIUS_KM * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function totalDistance() {
  let total = 0;
  for (let i = 0; i < currentPath.length - 1; i++) {
    total += haversineKm(currentPath[i], currentPath[i + 1]);
  }
  return total;
}

export function getPath() {
  return currentPath.slice();
}

export function setPath(points) {
  currentPath = points.slice();
  notifyPathChange();
  return currentPath;
}

export function addPoint(lat, lng) {
  currentPath.push({ lat, lng });
  notifyPathChange();
  return currentPath.length - 1;
}

export function removePoint(index) {
  if (index >= 0 && index < currentPath.length) {
    currentPath.splice(index, 1);
    notifyPathChange();
    return true;
  }
  return false;
}

export function updatePoint(index, lat, lng) {
  if (index >= 0 && index < currentPath.length) {
    currentPath[index] = { lat, lng };
    notifyPathChange();
    return true;
  }
  return false;
}

export function reorderPath(fromIndex, toIndex) {
  if (
    fromIndex >= 0 &&
    fromIndex < currentPath.length &&
    toIndex >= 0 &&
    toIndex < currentPath.length &&
    fromIndex !== toIndex
  ) {
    const [moved] = currentPath.splice(fromIndex, 1);
    currentPath.splice(toIndex, 0, moved);
    notifyPathChange();
    return true;
  }
  return false;
}

export function clearPath() {
  currentPath = [];
  notifyPathChange();
}

export function onPathChange(callback) {
  pathChangeCallbacks.push(callback);
  return () => {
    pathChangeCallbacks = pathChangeCallbacks.filter((cb) => cb !== callback);
  };
}

function notifyPathChange() {
  pathChangeCallbacks.forEach((cb) => {
    try {
      cb({ path: getPath(), distance: totalDistance() });
    } catch (err) {
      console.error('Path change callback error:', err);
    }
  });
}

export { haversineKm };
