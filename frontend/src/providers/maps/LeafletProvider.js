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
import { IMapProvider, IMap, IPolyline, IMarker } from './IMapProvider.js';
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
  const original = e.originalEvent;
  return {
    lat: e.latlng?.lat,
    lng: e.latlng?.lng,
    originalEvent: original,
    clientX: original?.clientX,
    clientY: original?.clientY,
    stop: () => original?.stopPropagation?.(),
  };
}

function toLatLngs(path) {
  return (path || []).map((p) => [p.lat, p.lng]);
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
      this.polyline.on('mouseover', () => this._setHovered(true));
      this.polyline.on('mouseout', () => this._setHovered(false));
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

    this.marker = L.marker([this.position.lat, this.position.lng], {
      draggable: options.draggable || false,
      title: options.title || '',
      icon: this._createIcon(markerType, config, options.draggable),
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

  fitBounds(bounds, padding) {
    if (!bounds || bounds.length === 0) return;
    const paddingValue = typeof padding === 'number' ? padding : (padding?.top ?? 50);
    this.leafletMap.fitBounds(L.latLngBounds(toLatLngs(bounds)), {
      padding: [paddingValue, paddingValue],
      maxZoom: 18,
    });
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
  }

  off(event, callback) {
    const list = this.listeners[event];
    if (!list) return;
    const index = list.indexOf(callback);
    if (index > -1) {
      list.splice(index, 1);
    }
  }

  createPolyline(options) {
    return new LeafletPolyline(this, options);
  }

  createMarker(options) {
    return new LeafletMarker(this, options);
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
