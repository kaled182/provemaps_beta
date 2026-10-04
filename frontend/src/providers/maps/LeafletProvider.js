/**
 * Leaflet / OpenStreetMap Provider
 *
 * Implementa IMapProvider sobre Leaflet 1.9 com os tiles públicos do
 * OpenStreetMap. É o provider que o backend chama `osm`
 * (`setup_app.FirstTimeSetup.map_provider`). Não precisa de chave nem token.
 *
 * Marcadores são `L.divIcon` (sem os PNG padrão do Leaflet, que o bundler não
 * resolve sozinho); a edição de vértices da polyline não existe no Leaflet
 * puro, por isso `setEditable`/`setDraggable` só guardam a intenção — o mesmo
 * que o provider Mapbox faz.
 */

import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { IMapProvider, IMap, IPolyline, IMarker, IPolygon } from './IMapProvider.js';
import { getMarkerConfig } from './markerStyles.js';

export const OSM_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
export const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const OSM_MAX_ZOOM = 19;

let leafletLoaded = false;

/**
 * Converte um evento Leaflet no formato comum da interface
 * (`{lat, lng, originalEvent, clientX, clientY}`).
 */
function toMapEvent(e) {
  const original = e?.originalEvent;
  return {
    lat: e?.latlng?.lat,
    lng: e?.latlng?.lng,
    originalEvent: original,
    clientX: original?.clientX,
    clientY: original?.clientY,
    stop: () => original?.stopPropagation?.(),
  };
}

function toLatLngs(path) {
  return (path || []).map((p) => [p.lat, p.lng]);
}

function normalizeFitOptions(options) {
  if (typeof options === 'number') return { padding: options, maxZoom: 18 };
  return { padding: options?.padding ?? options?.top ?? 50, maxZoom: options?.maxZoom ?? 18 };
}

/**
 * Implementação Leaflet do IPolygon
 */
class LeafletPolygon extends IPolygon {
  constructor(map, options) {
    super();
    this.polygon = L.polygon(toLatLngs(options.path), {
      color: options.strokeColor || '#f59e0b',
      weight: options.strokeWeight || 2,
      opacity: options.strokeOpacity ?? 0.9,
      fillColor: options.fillColor || options.strokeColor || '#f59e0b',
      fillOpacity: options.fillOpacity ?? 0.12,
      interactive: options.clickable ?? false,
    }).addTo(map.leafletMap);
  }

  setPath(path) {
    this.polygon.setLatLngs(toLatLngs(path));
  }

  setStyle(style) {
    const next = {};
    if (style.strokeColor !== undefined) next.color = style.strokeColor;
    if (style.strokeWeight !== undefined) next.weight = style.strokeWeight;
    if (style.strokeOpacity !== undefined) next.opacity = style.strokeOpacity;
    if (style.fillColor !== undefined) next.fillColor = style.fillColor;
    if (style.fillOpacity !== undefined) next.fillOpacity = style.fillOpacity;
    this.polygon.setStyle(next);
  }

  remove() {
    this.polygon.remove();
  }
}

/**
 * Implementação Leaflet do IPolyline
 */
class LeafletPolyline extends IPolyline {
  constructor(map, options) {
    super();
    this.map = map;
    this.leafletMap = map.leafletMap;
    this.options = options;
    this.path = options.path || [];
    this.listeners = {};
    this.metadata = {};
    this._editable = options.editable || false;
    this._draggable = options.draggable || false;
    this._hovered = false;

    this._baseStyle = {
      color: options.strokeColor || '#2563eb',
      weight: options.strokeWeight || 4,
      opacity: options.strokeOpacity ?? 0.9,
    };

    this.polyline = L.polyline(toLatLngs(this.path), {
      ...this._baseStyle,
      interactive: options.clickable !== false,
    }).addTo(this.leafletMap);

    if (options.clickable !== false) {
      this.polyline.on('click', (e) => this._emit('click', toMapEvent(e)));
      this.polyline.on('contextmenu', (e) => {
        e.originalEvent?.preventDefault?.();
        this._emit('rightclick', toMapEvent(e));
      });
      this.polyline.on('mouseover', (e) => {
        this._setHovered(true);
        this._emit('mouseover', toMapEvent(e));
      });
      this.polyline.on('mouseout', (e) => {
        this._setHovered(false);
        this._emit('mouseout', toMapEvent(e));
      });
      this.polyline.on('mousemove', (e) => this._emit('mousemove', toMapEvent(e)));
    }
  }

  _setHovered(hovered) {
    if (this._hovered === hovered) return;
    this._hovered = hovered;
    this.polyline.setStyle(
      hovered
        ? { weight: this._baseStyle.weight + 2, opacity: 1 }
        : { weight: this._baseStyle.weight, opacity: this._baseStyle.opacity },
    );
  }

  _emit(event, payload) {
    (this.listeners[event] || []).forEach((cb) => cb(payload));
  }

  setPath(path) {
    this.path = path || [];
    this.polyline.setLatLngs(toLatLngs(this.path));
  }

  getPath() {
    return this.polyline.getLatLngs().map((ll) => ({ lat: ll.lat, lng: ll.lng }));
  }

  setStyle(style) {
    if (style.strokeColor !== undefined) this._baseStyle.color = style.strokeColor;
    if (style.strokeWeight !== undefined) this._baseStyle.weight = style.strokeWeight;
    if (style.strokeOpacity !== undefined) this._baseStyle.opacity = style.strokeOpacity;
    if (this._hovered) {
      this.polyline.setStyle({ color: this._baseStyle.color, weight: this._baseStyle.weight + 2, opacity: 1 });
    } else {
      this.polyline.setStyle({ ...this._baseStyle });
    }
    if (style.zIndex !== undefined && style.zIndex >= 1000) this.polyline.bringToFront?.();
  }

  setEditable(editable) {
    // Leaflet puro não edita vértices (precisaria de leaflet-editable/geoman).
    this._editable = editable;
  }

  setDraggable(draggable) {
    this._draggable = draggable;
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  // Alias de compatibilidade com a API do Google Maps
  addListener(event, callback) {
    return this.on(event, callback);
  }

  set(key, value) {
    this.metadata[key] = value;
  }

  get(key) {
    return this.metadata[key];
  }

  remove() {
    this.polyline.off();
    this.polyline.remove();
    this.listeners = {};
  }
}

/**
 * Implementação Leaflet do IMarker
 */
class LeafletMarker extends IMarker {
  constructor(map, options) {
    super();
    this.map = map;
    this.leafletMap = map.leafletMap;
    this.options = options;
    this.position = options.position;
    this.listeners = {};

    const markerType = options.markerType || 'default';
    const config = getMarkerConfig(markerType);
    this.markerType = markerType;
    this._style = {
      color: options.color ?? config.color,
      size: options.size ?? config.size,
      label: options.label ?? config.label,
      iconUrl: options.iconUrl,
      iconSize: options.iconSize || 24,
    };

    this.marker = L.marker([this.position.lat, this.position.lng], {
      draggable: options.draggable || false,
      title: options.title || '',
      icon: this._buildIcon(),
    }).addTo(this.leafletMap);

    this.marker.on('drag', () => {
      this._syncPosition();
      this._emit('drag');
    });
    this.marker.on('dragend', () => {
      this._syncPosition();
      this._emit('dragend');
    });
    this.marker.on('click', (e) => this._emit('click', { originalEvent: e.originalEvent }));
  }

  _buildIcon() {
    const s = this._style;
    return s.iconUrl
      ? this._createImageIcon(this.markerType, s.iconUrl, s.iconSize)
      : this._createIcon(this.markerType, { color: s.color, size: s.size, label: s.label }, this.options.draggable);
  }

  setStyle(style) {
    this._style = { ...this._style, ...style };
    this.marker.setIcon(this._buildIcon());
  }

  _createImageIcon(markerType, url, size) {
    return L.icon({
      className: `map-marker map-marker-${markerType} map-marker-image`,
      iconUrl: url,
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
    });
  }

  _createIcon(markerType, config, draggable) {
    const style = [
      `width:${config.size}px`,
      `height:${config.size}px`,
      'border-radius:50%',
      `background-color:${config.color}`,
      'border:3px solid white',
      'box-shadow:0 2px 4px rgba(0,0,0,0.3)',
      `cursor:${draggable ? 'move' : 'pointer'}`,
      'display:flex',
      'align-items:center',
      'justify-content:center',
      'font-weight:bold',
      'color:white',
      `font-size:${config.size * 0.6}px`,
      'user-select:none',
      'box-sizing:border-box',
    ].join(';');

    return L.divIcon({
      className: `map-marker map-marker-${markerType}`,
      html: `<div style="${style}">${config.label || ''}</div>`,
      iconSize: [config.size, config.size],
      iconAnchor: [config.size / 2, config.size / 2],
    });
  }

  _syncPosition() {
    const ll = this.marker.getLatLng();
    this.position = { lat: ll.lat, lng: ll.lng };
  }

  _emit(event, payload) {
    (this.listeners[event] || []).forEach((cb) => cb(payload));
  }

  setPosition(position) {
    this.position = position;
    this.marker.setLatLng([position.lat, position.lng]);
  }

  getPosition() {
    return this.position;
  }

  setDraggable(draggable) {
    const dragging = this.marker.dragging;
    if (!dragging) return;
    if (draggable) {
      dragging.enable();
    } else {
      dragging.disable();
    }
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  addListener(event, callback) {
    return this.on(event, callback);
  }

  remove() {
    this.marker.off();
    this.marker.remove();
    this.listeners = {};
  }
}

/**
 * Implementação Leaflet do IMap
 */
class LeafletMap extends IMap {
  constructor(container, options) {
    super();
    this.container = container;
    this.options = options;
    this.listeners = {};

    this.leafletMap = L.map(container, {
      center: [options.center.lat, options.center.lng],
      zoom: options.zoom || 10,
      zoomControl: true,
      attributionControl: true,
    });

    this.tileLayer = L.tileLayer(OSM_TILE_URL, {
      attribution: OSM_ATTRIBUTION,
      maxZoom: OSM_MAX_ZOOM,
    }).addTo(this.leafletMap);

    this.leafletMap.on('click', (e) => this._emit('click', toMapEvent(e)));
    this.leafletMap.on('contextmenu', (e) => {
      if (!this.listeners.rightclick?.length) return;
      e.originalEvent?.preventDefault?.();
      this._emit('rightclick', toMapEvent(e));
    });
  }

  _emit(event, payload) {
    (this.listeners[event] || []).forEach((cb) => cb(payload));
  }

  setCenter(latLng) {
    this.leafletMap.setView([latLng.lat, latLng.lng], this.leafletMap.getZoom());
  }

  getCenter() {
    const c = this.leafletMap.getCenter();
    return { lat: c.lat, lng: c.lng };
  }

  setZoom(zoom) {
    this.leafletMap.setZoom(zoom);
  }

  getZoom() {
    return this.leafletMap.getZoom();
  }

  fitBounds(bounds, options) {
    if (!bounds || bounds.length === 0) return;
    const { padding, maxZoom } = normalizeFitOptions(options);
    this.leafletMap.fitBounds(L.latLngBounds(toLatLngs(bounds)), {
      padding: [padding, padding],
      maxZoom,
    });
  }

  setCursor(cursor) {
    this.leafletMap.getContainer().style.cursor = cursor || '';
  }

  resize() {
    this.leafletMap.invalidateSize({ animate: false });
  }

  panTo(latLng) {
    this.leafletMap.panTo([latLng.lat, latLng.lng]);
  }

  flyTo(latLng, zoom = 14) {
    this.leafletMap.flyTo([latLng.lat, latLng.lng], zoom, { duration: 0.8 });
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
    this._bindViewportEvent(event);
  }

  /**
   * `move` → `move` do Leaflet; `idle` → `moveend` (também dispara após zoom).
   * Ligam-se ao mapa nativo só quando alguém os pede.
   */
  _bindViewportEvent(event) {
    const nativeEvent = { move: 'move', idle: 'moveend' }[event];
    if (!nativeEvent) return;
    this._boundViewportEvents ||= new Set();
    if (this._boundViewportEvents.has(event)) return;
    this._boundViewportEvents.add(event);
    this.leafletMap.on(nativeEvent, () => this._emit(event, {}));
  }

  off(event, callback) {
    const list = this.listeners[event];
    if (!list) return;
    const index = list.indexOf(callback);
    if (index > -1) {
      list.splice(index, 1);
    }
  }

  getBounds() {
    const b = this.leafletMap.getBounds();
    if (!b) return null;
    return { lat_min: b.getSouth(), lng_min: b.getWest(), lat_max: b.getNorth(), lng_max: b.getEast() };
  }

  getContainer() {
    return this.leafletMap.getContainer();
  }

  createPolyline(options) {
    return new LeafletPolyline(this, options);
  }

  createMarker(options) {
    return new LeafletMarker(this, options);
  }

  createPolygon(options) {
    return new LeafletPolygon(this, options);
  }

  destroy() {
    this.listeners = {};
    this.leafletMap.off();
    this.leafletMap.remove();
  }

  latLngToPixel(latLng) {
    const point = this.leafletMap.latLngToContainerPoint([latLng.lat, latLng.lng]);
    return { x: point.x, y: point.y };
  }

  /**
   * Instância nativa do Leaflet (paridade com `getNativeMap()` do Google).
   */
  getNativeMap() {
    return this.leafletMap;
  }
}

/**
 * Leaflet / OpenStreetMap Provider
 */
export class LeafletProvider extends IMapProvider {
  constructor() {
    super();
    this.name = 'osm';
  }

  // eslint-disable-next-line no-unused-vars
  async load(_config) {
    // Leaflet e o CSS vêm no bundle; os tiles do OSM são públicos (sem chave).
    leafletLoaded = true;
  }

  createMap(container, options) {
    if (!leafletLoaded) {
      throw new Error('LeafletProvider not loaded. Call load() first.');
    }
    return new LeafletMap(container, options);
  }

  getName() {
    return this.name;
  }

  isLoaded() {
    return leafletLoaded;
  }
}
