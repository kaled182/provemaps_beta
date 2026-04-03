/**
 * Map Utils - Helper functions for coordinate conversion (provider-agnostic)
 * 
 * Substitui funções que usavam google.maps diretamente
 */

/**
 * Converte coordenadas geográficas para pixels (usando o provider atual)
 * @param {IMap} map - Instância do mapa
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @returns {{x: number, y: number}|null}
 */
export function latLngToPixel(map, lat, lng) {
  if (!map) {
    console.warn('[mapUtils] latLngToPixel: map is null');
    return null;
  }

  try {
    return map.latLngToPixel({ lat, lng });
  } catch (error) {
    console.error('[mapUtils] latLngToPixel error:', error);
    return null;
  }
}

/**
 * Calcula distância entre dois pontos em pixels
 * @param {{x: number, y: number}} a
 * @param {{x: number, y: number}} b
 * @returns {number}
 */
export function distanceBetweenPixels(a, b) {
  if (!a || !b) {
    return Number.POSITIVE_INFINITY;
  }
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.hypot(dx, dy);
}

/**
 * Calcula distância de um ponto para um segmento de linha (em pixels)
 * @param {{x: number, y: number}} point
 * @param {{x: number, y: number}} segmentStart
 * @param {{x: number, y: number}} segmentEnd
 * @returns {number}
 */
export function distancePointToSegmentPx(point, segmentStart, segmentEnd) {
  if (!point || !segmentStart || !segmentEnd) {
    return Number.POSITIVE_INFINITY;
  }

  const dx = segmentEnd.x - segmentStart.x;
  const dy = segmentEnd.y - segmentStart.y;

  if (dx === 0 && dy === 0) {
    return distanceBetweenPixels(point, segmentStart);
  }

  const t = ((point.x - segmentStart.x) * dx + (point.y - segmentStart.y) * dy) / (dx * dx + dy * dy);
  const clampedT = Math.max(0, Math.min(1, t));
  const projX = segmentStart.x + clampedT * dx;
  const projY = segmentStart.y + clampedT * dy;

  return Math.hypot(point.x - projX, point.y - projY);
}

/**
 * Calcula distância entre dois pontos geográficos (Haversine formula)
 * @param {{lat: number, lng: number}} point1
 * @param {{lat: number, lng: number}} point2
 * @returns {number} Distância em metros
 */
export function calculateDistance(point1, point2) {
  const R = 6371000; // Raio da Terra em metros
  const dLat = toRadians(point2.lat - point1.lat);
  const dLng = toRadians(point2.lng - point1.lng);

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRadians(point1.lat)) *
      Math.cos(toRadians(point2.lat)) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Converte graus para radianos
 * @param {number} degrees
 * @returns {number}
 */
function toRadians(degrees) {
  return degrees * (Math.PI / 180);
}

/**
 * Calcula distância total de um caminho
 * @param {Array<{lat: number, lng: number}>} path
 * @returns {number} Distância total em metros
 */
export function calculatePathDistance(path) {
  if (!path || path.length < 2) {
    return 0;
  }

  let totalDistance = 0;
  for (let i = 0; i < path.length - 1; i++) {
    totalDistance += calculateDistance(path[i], path[i + 1]);
  }

  return totalDistance;
}

/**
 * Calcula o centro (centroid) de um conjunto de pontos
 * @param {Array<{lat: number, lng: number}>} points
 * @returns {{lat: number, lng: number}|null}
 */
export function calculateCenter(points) {
  if (!points || points.length === 0) {
    return null;
  }

  let sumLat = 0;
  let sumLng = 0;

  points.forEach(point => {
    sumLat += point.lat;
    sumLng += point.lng;
  });

  return {
    lat: sumLat / points.length,
    lng: sumLng / points.length,
  };
}

/**
 * Calcula bounds (min/max) de um conjunto de pontos
 * @param {Array<{lat: number, lng: number}>} points
 * @returns {{minLat: number, maxLat: number, minLng: number, maxLng: number}|null}
 */
export function calculateBounds(points) {
  if (!points || points.length === 0) {
    return null;
  }

  let minLat = Infinity;
  let maxLat = -Infinity;
  let minLng = Infinity;
  let maxLng = -Infinity;

  points.forEach(point => {
    minLat = Math.min(minLat, point.lat);
    maxLat = Math.max(maxLat, point.lat);
    minLng = Math.min(minLng, point.lng);
    maxLng = Math.max(maxLng, point.lng);
  });

  return { minLat, maxLat, minLng, maxLng };
}
