/**
 * useRouteDrawing — desenho/edição de um traçado (polyline com vértices
 * arrastáveis) sobre qualquer provider, via `IMap`.
 *
 * Substitui o `drawingPlugin` Google-only da pilha `useMapService`/`UnifiedMapView`
 * (EV-0012d). Clique no mapa acrescenta um vértice; arrastar move; botão direito
 * no vértice remove. O caminho é sempre `[{lat, lng}]`.
 *
 * @param {import('@/providers/maps/IMapProvider').IMap} map
 * @param {Object} [options]
 * @param {boolean} [options.editable=true]
 * @param {string}  [options.strokeColor='#2563eb']
 * @param {number}  [options.strokeWeight=3]
 * @param {number}  [options.strokeOpacity=0.8]
 * @param {number}  [options.vertexSize=18]
 * @param {(path: Array<{lat:number,lng:number}>, distanceMeters: number) => void} [options.onPathChange]
 */
export function createRouteDrawing(map, options = {}) {
  const {
    editable = true,
    strokeColor = '#2563eb',
    strokeWeight = 3,
    strokeOpacity = 0.8,
    vertexSize = 18,
    onPathChange = null,
  } = options;

  let polyline = null;
  let markers = [];
  let drawing = false;

  function ensurePolyline() {
    if (!polyline) {
      polyline = map.createPolyline({ path: [], strokeColor, strokeWeight, strokeOpacity, clickable: false });
    }
    return polyline;
  }

  function onMapClick(event) {
    if (!Number.isFinite(event?.lat) || !Number.isFinite(event?.lng)) return;
    addPoint({ lat: event.lat, lng: event.lng });
  }

  function getPath() {
    return markers.map((m) => {
      const { lat, lng } = m.getPosition();
      return { lat, lng };
    });
  }

  function relabel() {
    markers.forEach((m, i) => m.setStyle({ label: String(i + 1) }));
  }

  function update() {
    const path = getPath();
    ensurePolyline().setPath(path);
    onPathChange?.(path, getDistanceMeters());
  }

  function addPoint(position) {
    const marker = map.createMarker({
      position: { lat: position.lat, lng: position.lng },
      draggable: editable,
      markerType: 'intermediate',
      label: String(markers.length + 1),
      size: vertexSize,
      title: `Vértice ${markers.length + 1}`,
    });
    marker.on('dragend', update);
    if (editable) {
      marker.on('rightclick', () => removePoint(marker));
    }
    markers.push(marker);
    update();
    return marker;
  }

  function removePoint(markerOrIndex) {
    const index = typeof markerOrIndex === 'number' ? markerOrIndex : markers.indexOf(markerOrIndex);
    if (index < 0 || index >= markers.length) return;
    markers[index].remove();
    markers.splice(index, 1);
    relabel();
    update();
  }

  function clear() {
    markers.forEach((m) => m.remove());
    markers = [];
    if (polyline) polyline.setPath([]);
    onPathChange?.([], 0);
  }

  function setPath(coordinates) {
    markers.forEach((m) => m.remove());
    markers = [];
    (coordinates || []).forEach((c) => {
      const point = normalizePoint(c);
      if (point) addPoint(point);
    });
    if (!coordinates?.length) update();
  }

  function start() {
    if (!editable || drawing) return;
    ensurePolyline();
    map.on('click', onMapClick);
    drawing = true;
  }

  function stop() {
    if (!drawing) return;
    map.off('click', onMapClick);
    drawing = false;
  }

  function getDistanceMeters() {
    const path = getPath();
    let total = 0;
    for (let i = 1; i < path.length; i += 1) {
      total += haversineMeters(path[i - 1], path[i]);
    }
    return total;
  }

  function fitBounds(fitOptions = { padding: 50, maxZoom: 16 }) {
    const path = getPath();
    if (path.length) map.fitBounds(path, fitOptions);
  }

  function destroy() {
    stop();
    markers.forEach((m) => m.remove());
    markers = [];
    if (polyline) {
      polyline.remove();
      polyline = null;
    }
  }

  return {
    start,
    stop,
    addPoint,
    removePoint,
    setPath,
    getPath,
    getDistanceMeters,
    getDistanceKm: () => getDistanceMeters() / 1000,
    clear,
    fitBounds,
    destroy,
    get isDrawing() { return drawing; },
    get pointCount() { return markers.length; },
  };
}

/**
 * Aceita `{lat, lng}`, `[lng, lat]` (GeoJSON) ou strings numéricas.
 * @returns {{lat:number,lng:number}|null}
 */
export function normalizePoint(point) {
  if (!point) return null;
  let lat;
  let lng;
  if (Array.isArray(point)) {
    [lng, lat] = point;
  } else {
    ({ lat, lng } = point);
  }
  lat = Number(lat);
  lng = Number(lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  return { lat, lng };
}

const EARTH_RADIUS_M = 6371008.8;

/** Distância geodésica aproximada entre dois pontos, em metros. */
export function haversineMeters(a, b) {
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2
    + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)));
}
