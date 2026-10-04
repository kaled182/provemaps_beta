/**
 * Mapbox Provider Implementation
 * Implementa IMapProvider para Mapbox GL JS
 */

import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { IMapProvider, IMap, IPolyline, IMarker, IPolygon } from './IMapProvider.js';
import { getMarkerConfig } from './markerStyles.js';

let mapboxLoaded = false;
let layerIdCounter = 0;
let markerIdCounter = 0;
let polygonIdCounter = 0;

export const MAPBOX_DEFAULT_STYLE = 'mapbox://styles/mapbox/streets-v12';

/** Aliases aceites em `MAPBOX_STYLE`/`MAPBOX_CUSTOM_STYLE` (eram do CustomMapViewer) */
export const MAPBOX_STYLE_PRESETS = {
  streets: MAPBOX_DEFAULT_STYLE,
  'streets-v12': MAPBOX_DEFAULT_STYLE,
  'street-v12': MAPBOX_DEFAULT_STYLE,
  satellite: 'mapbox://styles/mapbox/satellite-v9',
  'satellite-v9': 'mapbox://styles/mapbox/satellite-v9',
  'satellite-streets': 'mapbox://styles/mapbox/satellite-streets-v12',
  'satellite-streets-v12': 'mapbox://styles/mapbox/satellite-streets-v12',
  outdoors: 'mapbox://styles/mapbox/outdoors-v12',
  'outdoors-v12': 'mapbox://styles/mapbox/outdoors-v12',
  terrain: 'mapbox://styles/mapbox/outdoors-v12',
  light: 'mapbox://styles/mapbox/light-v11',
  'light-v11': 'mapbox://styles/mapbox/light-v11',
  dark: 'mapbox://styles/mapbox/dark-v11',
  'dark-v11': 'mapbox://styles/mapbox/dark-v11',
  navigation: 'mapbox://styles/mapbox/navigation-day-v1',
  'navigation-day': 'mapbox://styles/mapbox/navigation-day-v1',
  'navigation-day-v1': 'mapbox://styles/mapbox/navigation-day-v1',
  'navigation-night': 'mapbox://styles/mapbox/navigation-night-v1',
  'navigation-night-v1': 'mapbox://styles/mapbox/navigation-night-v1',
};

/**
 * `mapbox://…`/URL passam; alias vira URL; inválido vira ''.
 * @param {string} raw
 * @returns {string}
 */
export function resolveMapboxStyle(raw) {
  const style = (raw || '').trim();
  if (!style) return '';
  if (style.startsWith('mapbox://') || style.startsWith('http://') || style.startsWith('https://')) {
    return style;
  }
  return MAPBOX_STYLE_PRESETS[style.toLowerCase()] || '';
}

/**
 * Ordem de tentativa: estilo personalizado, estilo configurado, padrão.
 * @param {{mapboxCustomStyle?: string, mapboxStyle?: string}} config
 * @returns {string[]}
 */
export function mapboxStyleCandidates(config = {}) {
  return Array.from(new Set([
    resolveMapboxStyle(config.mapboxCustomStyle),
    resolveMapboxStyle(config.mapboxStyle),
    MAPBOX_DEFAULT_STYLE,
  ].filter(Boolean)));
}

function normalizeFitOptions(options) {
  if (typeof options === 'number') return { padding: options, maxZoom: undefined };
  return { padding: options?.padding ?? options?.top ?? 50, maxZoom: options?.maxZoom };
}

/**
 * Implementação Mapbox do IPolyline
 */
class MapboxPolyline extends IPolyline {
  constructor(map, options) {
    super();
    this.map = map;
    this.mapboxMap = map.mapboxMap;
    this.options = options;
    this.path = options.path || [];
    this.layerId = `polyline-${++layerIdCounter}`;
    this.sourceId = `polyline-source-${layerIdCounter}`;
    this.listeners = {};
    this._editable = options.editable || false;
    this._draggable = options.draggable || false;
    this.metadata = {};  // For storing custom data

    this._addToMap();
  }

  _addToMap() {
    const coordinates = this.path.map(p => [p.lng, p.lat]);
    this.hitLayerId = `${this.layerId}-hit`;
    this._hovered = false;

    // Add source (shared by visible + hit layers)
    this.mapboxMap.addSource(this.sourceId, {
      type: 'geojson',
      data: {
        type: 'Feature',
        geometry: { type: 'LineString', coordinates },
      },
    });

    // Visible line layer
    this.mapboxMap.addLayer({
      id: this.layerId,
      type: 'line',
      source: this.sourceId,
      layout: { 'line-join': 'round', 'line-cap': 'round' },
      paint: {
        'line-color': this.options.strokeColor || '#2563eb',
        'line-width': this.options.strokeWeight || 4,
        'line-opacity': this.options.strokeOpacity || 0.9,
      },
    });

    // Transparent wide hit-area layer (easier to click/right-click)
    this.mapboxMap.addLayer({
      id: this.hitLayerId,
      type: 'line',
      source: this.sourceId,
      layout: { 'line-join': 'round', 'line-cap': 'round' },
      paint: { 'line-color': 'transparent', 'line-width': 16, 'line-opacity': 0 },
    });

    if (this.options.clickable !== false) {
      // Use hit layer for events so the wider area is responsive
      this.mapboxMap.on('click', this.hitLayerId, this._handleClick.bind(this));
      this.mapboxMap.on('contextmenu', this.hitLayerId, this._handleRightClick.bind(this));

      // Hover: cursor + highlight + eventos para quem ouve (tooltips)
      this._onMouseEnter = (e) => {
        this.mapboxMap.getCanvas().style.cursor = 'pointer';
        if (!this._hovered) {
          this._hovered = true;
          const baseWidth = this.options.strokeWeight || 4;
          this.mapboxMap.setPaintProperty(this.layerId, 'line-width', baseWidth + 2);
          this.mapboxMap.setPaintProperty(this.layerId, 'line-opacity', 1);
        }
        this._emit('mouseover', this._toEvent(e));
      };
      this._onMouseLeave = (e) => {
        this.mapboxMap.getCanvas().style.cursor = '';
        if (this._hovered) {
          this._hovered = false;
          this.mapboxMap.setPaintProperty(this.layerId, 'line-width', this.options.strokeWeight || 4);
          this.mapboxMap.setPaintProperty(this.layerId, 'line-opacity', this.options.strokeOpacity || 0.9);
        }
        this._emit('mouseout', this._toEvent(e));
      };
      this._onMouseMove = (e) => this._emit('mousemove', this._toEvent(e));
      this.mapboxMap.on('mouseenter', this.hitLayerId, this._onMouseEnter);
      this.mapboxMap.on('mouseleave', this.hitLayerId, this._onMouseLeave);
      this.mapboxMap.on('mousemove', this.hitLayerId, this._onMouseMove);
    }
  }

  _toEvent(e) {
    return {
      lat: e?.lngLat?.lat,
      lng: e?.lngLat?.lng,
      originalEvent: e?.originalEvent,
      clientX: e?.originalEvent?.clientX,
      clientY: e?.originalEvent?.clientY,
    };
  }

  _emit(event, payload) {
    (this.listeners[event] || []).forEach((cb) => cb(payload));
  }

  _handleClick(e) {
    if (this.listeners.click) {
      this.listeners.click.forEach(cb => {
        cb({
          lat: e.lngLat.lat,
          lng: e.lngLat.lng,
          originalEvent: e.originalEvent,
        });
      });
    }
  }

  _handleRightClick(e) {
    e.preventDefault();
    if (this.listeners.rightclick) {
      this.listeners.rightclick.forEach(cb => {
        cb({
          lat: e.lngLat.lat,
          lng: e.lngLat.lng,
          originalEvent: e.originalEvent,
          clientX: e.originalEvent.clientX,
          clientY: e.originalEvent.clientY,
        });
      });
    }
  }

  setPath(path) {
    this.path = path;
    const coordinates = path.map(p => [p.lng, p.lat]);
    const source = this.mapboxMap.getSource(this.sourceId);
    if (source) {
      source.setData({
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: coordinates,
        },
      });
    }
  }

  setStyle(style) {
    if (!this.mapboxMap.getLayer(this.layerId)) return;
    if (style.strokeColor !== undefined) {
      this.options.strokeColor = style.strokeColor;
      this.mapboxMap.setPaintProperty(this.layerId, 'line-color', style.strokeColor);
    }
    if (style.strokeWeight !== undefined) {
      this.options.strokeWeight = style.strokeWeight;
      if (!this._hovered) this.mapboxMap.setPaintProperty(this.layerId, 'line-width', style.strokeWeight);
    }
    if (style.strokeOpacity !== undefined) {
      this.options.strokeOpacity = style.strokeOpacity;
      if (!this._hovered) this.mapboxMap.setPaintProperty(this.layerId, 'line-opacity', style.strokeOpacity);
    }
    // zIndex: o Mapbox desenha camadas por ordem de inserção; traz-se para cima
    if (style.zIndex !== undefined && style.zIndex >= 1000) {
      this.mapboxMap.moveLayer(this.layerId);
      this.mapboxMap.moveLayer(this.hitLayerId);
    }
  }

  getPath() {
    return this.path;
  }

  setEditable(editable) {
    this._editable = editable;
    console.log(`[MapboxPolyline] setEditable(${editable}) - ⚠️ Full editing with mapbox-gl-draw not implemented yet`);
    // TODO: Integrate mapbox-gl-draw for full editing support
  }

  setDraggable(draggable) {
    this._draggable = draggable;
    console.log(`[MapboxPolyline] setDraggable(${draggable}) - ⚠️ Dragging not fully supported`);
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  // Alias for Google Maps API compatibility
  addListener(event, callback) {
    return this.on(event, callback);
  }

  // Metadata storage (Google Maps API compatibility)
  set(key, value) {
    this.metadata[key] = value;
  }

  get(key) {
    return this.metadata[key];
  }

  remove() {
    // Remove hit layer first (it's on top)
    if (this.hitLayerId && this.mapboxMap.getLayer(this.hitLayerId)) {
      this.mapboxMap.off('click', this.hitLayerId, this._handleClick);
      this.mapboxMap.off('contextmenu', this.hitLayerId, this._handleRightClick);
      if (this._onMouseEnter) this.mapboxMap.off('mouseenter', this.hitLayerId, this._onMouseEnter);
      if (this._onMouseLeave) this.mapboxMap.off('mouseleave', this.hitLayerId, this._onMouseLeave);
      if (this._onMouseMove) this.mapboxMap.off('mousemove', this.hitLayerId, this._onMouseMove);
      this.mapboxMap.removeLayer(this.hitLayerId);
    }
    if (this.mapboxMap.getLayer(this.layerId)) {
      this.mapboxMap.off('click', this.layerId, this._handleClick);
      this.mapboxMap.off('contextmenu', this.layerId, this._handleRightClick);
      this.mapboxMap.removeLayer(this.layerId);
    }
    if (this.mapboxMap.getSource(this.sourceId)) {
      this.mapboxMap.removeSource(this.sourceId);
    }
    // Reset cursor if this polyline was being hovered when removed
    try { this.mapboxMap.getCanvas().style.cursor = ''; } catch (_) { /* best-effort: ignorado de propósito */ }
  }
}

/**
 * Implementação Mapbox do IMarker
 */
class MapboxMarker extends IMarker {
  constructor(map, options) {
    super();
    this.map = map;
    this.mapboxMap = map.mapboxMap;
    this.position = options.position;
    this.options = options;
    this.listeners = {};
    this.markerId = `marker-${++markerIdCounter}`;

    this._createMarker();
  }

  _createMarker() {
    // Determine marker configuration based on type
    const markerType = this.options.markerType || 'default';
    const config = this._getMarkerConfig(markerType);
    this._style = {
      color: this.options.color ?? config.color,
      size: this.options.size ?? config.size,
      label: this.options.label ?? config.label,
      iconUrl: this.options.iconUrl,
      iconSize: this.options.iconSize || 24,
    };

    const el = this._style.iconUrl
      ? this._createImageElement(markerType, this._style.iconUrl, this._style.iconSize)
      : this._createCircleElement(markerType, this._style);
    if (this.options.title) {
      el.title = this.options.title;
    }

    this.marker = new mapboxgl.Marker({
      element: el,
      draggable: this.options.draggable || false,
    })
      .setLngLat([this.position.lng, this.position.lat])
      .addTo(this.mapboxMap);

    // Handle drag events
    if (this.options.draggable) {
      this.marker.on('drag', () => {
        const lngLat = this.marker.getLngLat();
        this.position = { lat: lngLat.lat, lng: lngLat.lng };
        if (this.listeners.drag) {
          this.listeners.drag.forEach(cb => cb());
        }
      });

      this.marker.on('dragend', () => {
        const lngLat = this.marker.getLngLat();
        this.position = { lat: lngLat.lat, lng: lngLat.lng };
        if (this.listeners.dragend) {
          this.listeners.dragend.forEach(cb => cb());
        }
      });
    }

    // Handle click
    el.addEventListener('click', (e) => {
      if (this.listeners.click) {
        this.listeners.click.forEach(cb => cb({ originalEvent: e }));
      }
    });
  }

  _createImageElement(markerType, url, size) {
    const el = document.createElement('img');
    el.className = `map-marker map-marker-${markerType} map-marker-image`;
    el.src = url;
    el.alt = '';
    el.style.width = `${size}px`;
    el.style.height = `${size}px`;
    el.style.cursor = this.options.draggable ? 'move' : 'pointer';
    el.style.userSelect = 'none';
    return el;
  }

  _createCircleElement(markerType, config) {
    // Create custom marker element
    const el = document.createElement('div');
    el.className = `map-marker map-marker-${markerType}`;
    el.style.width = `${config.size}px`;
    el.style.height = `${config.size}px`;
    el.style.borderRadius = '50%';
    el.style.backgroundColor = config.color;
    el.style.border = '3px solid white';
    el.style.boxShadow = '0 2px 4px rgba(0,0,0,0.3)';
    el.style.cursor = this.options.draggable ? 'move' : 'pointer';
    el.style.display = 'flex';
    el.style.alignItems = 'center';
    el.style.justifyContent = 'center';
    el.style.fontWeight = 'bold';
    el.style.color = 'white';
    el.style.fontSize = `${config.size * 0.6}px`;
    el.style.userSelect = 'none';

    // Add label if configured
    if (config.label) {
      el.textContent = config.label;
    }
    return el;
  }

  setPosition(position) {
    this.position = position;
    this.marker.setLngLat([position.lng, position.lat]);
  }

  setStyle(style) {
    this._style = { ...this._style, ...style };
    const el = this.marker.getElement();
    if (!el) return;
    if (el.tagName === 'IMG') {
      if (style.iconUrl) el.src = style.iconUrl;
      if (style.size) { el.style.width = `${style.size}px`; el.style.height = `${style.size}px`; }
      return;
    }
    if (style.color) el.style.backgroundColor = style.color;
    if (style.size) {
      el.style.width = `${style.size}px`;
      el.style.height = `${style.size}px`;
      el.style.fontSize = `${style.size * 0.6}px`;
    }
    if (style.label !== undefined) el.textContent = style.label || '';
  }

  getPosition() {
    return this.position;
  }

  setDraggable(draggable) {
    this.marker.setDraggable(draggable);
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  // Alias for Google Maps API compatibility
  addListener(event, callback) {
    return this.on(event, callback);
  }

  remove() {
    this.marker.remove();
  }

  /**
   * Estilo do marcador por tipo — tabela partilhada em `markerStyles.js`.
   * @param {string} type - 'origin', 'destination', 'intermediate', 'default', 'preview'
   * @returns {{color: string, size: number, label: string}}
   */
  _getMarkerConfig(type) {
    return getMarkerConfig(type);
  }
}

/**
 * Implementação Mapbox do IPolygon (source GeoJSON + camada fill + camada line)
 */
class MapboxPolygon extends IPolygon {
  constructor(map, options) {
    super();
    this.mapboxMap = map.mapboxMap;
    const id = ++polygonIdCounter;
    this.sourceId = `polygon-source-${id}`;
    this.fillLayerId = `polygon-fill-${id}`;
    this.lineLayerId = `polygon-line-${id}`;

    this.mapboxMap.addSource(this.sourceId, { type: 'geojson', data: this._geojson(options.path) });
    this.mapboxMap.addLayer({
      id: this.fillLayerId,
      type: 'fill',
      source: this.sourceId,
      paint: {
        'fill-color': options.fillColor || options.strokeColor || '#f59e0b',
        'fill-opacity': options.fillOpacity ?? 0.12,
      },
    });
    this.mapboxMap.addLayer({
      id: this.lineLayerId,
      type: 'line',
      source: this.sourceId,
      paint: {
        'line-color': options.strokeColor || '#f59e0b',
        'line-width': options.strokeWeight || 2,
        'line-opacity': options.strokeOpacity ?? 0.9,
      },
    });
  }

  _geojson(path) {
    const ring = (path || []).map(p => [p.lng, p.lat]);
    if (ring.length >= 3) ring.push(ring[0]);
    return { type: 'Feature', geometry: { type: 'Polygon', coordinates: [ring] } };
  }

  setPath(path) {
    this.mapboxMap.getSource(this.sourceId)?.setData(this._geojson(path));
  }

  setStyle(style) {
    const paint = (layer, prop, value) => {
      if (value !== undefined && this.mapboxMap.getLayer(layer)) this.mapboxMap.setPaintProperty(layer, prop, value);
    };
    paint(this.lineLayerId, 'line-color', style.strokeColor);
    paint(this.lineLayerId, 'line-width', style.strokeWeight);
    paint(this.lineLayerId, 'line-opacity', style.strokeOpacity);
    paint(this.fillLayerId, 'fill-color', style.fillColor);
    paint(this.fillLayerId, 'fill-opacity', style.fillOpacity);
  }

  remove() {
    [this.lineLayerId, this.fillLayerId].forEach((id) => {
      if (this.mapboxMap.getLayer(id)) this.mapboxMap.removeLayer(id);
    });
    if (this.mapboxMap.getSource(this.sourceId)) this.mapboxMap.removeSource(this.sourceId);
  }
}

/**
 * Implementação Mapbox do IMap
 */
class MapboxMap extends IMap {
  constructor(container, options) {
    super();
    this.container = container;
    this.options = options;
    this.listeners = {};

    // Estilo: o pedido, senão a cadeia configurada (personalizado → configurado → padrão).
    // Se um estilo falhar antes do primeiro `load`, tenta-se o seguinte.
    this._styleCandidates = options.style
      ? [resolveMapboxStyle(options.style) || options.style]
      : (options.styleCandidates?.length ? options.styleCandidates : [MAPBOX_DEFAULT_STYLE]);
    this._styleIndex = 0;
    this._loaded = false;

    this.mapboxMap = new mapboxgl.Map({
      container: container,
      style: this._styleCandidates[0],
      center: [options.center.lng, options.center.lat],
      zoom: options.zoom || 10,
      pitch: 0,
      bearing: 0,
      ...(options.minZoom ? { minZoom: options.minZoom } : {}),
      ...(options.maxZoom ? { maxZoom: options.maxZoom } : {}),
    });

    this.mapboxMap.once('load', () => { this._loaded = true; });
    this.mapboxMap.on('error', (event) => this._onStyleError(event));

    // Add controls
    this.mapboxMap.addControl(new mapboxgl.NavigationControl());
    if (options.controls?.scale && mapboxgl.ScaleControl) {
      this.mapboxMap.addControl(new mapboxgl.ScaleControl({ unit: 'metric' }));
    }

    // Setup event forwarding
    this._setupEvents();
  }

  _onStyleError(event) {
    if (this._loaded) return;
    const next = this._styleIndex + 1;
    if (next >= this._styleCandidates.length) return;
    console.warn('[MapboxProvider] Estilo falhou, a tentar o seguinte:', this._styleCandidates[this._styleIndex], event?.error?.message);
    this._styleIndex = next;
    this.mapboxMap.setStyle(this._styleCandidates[next]);
  }

  /** Estilo efetivamente carregado (depois de eventuais fallbacks) */
  getStyleUrl() {
    return this._styleCandidates[this._styleIndex];
  }

  setCursor(cursor) {
    this.mapboxMap.getCanvas().style.cursor = cursor || '';
  }

  resize() {
    this.mapboxMap.resize();
  }

  _setupEvents() {
    // Click event
    this.mapboxMap.on('click', (e) => {
      if (this.listeners.click) {
        this.listeners.click.forEach(cb => {
          cb({
            lat: e.lngLat.lat,
            lng: e.lngLat.lng,
            originalEvent: e.originalEvent,
          });
        });
      }
    });

    // Right-click event
    this.mapboxMap.on('contextmenu', (e) => {
      if (this.listeners.rightclick) {
        e.preventDefault();
        this.listeners.rightclick.forEach(cb => {
          cb({
            lat: e.lngLat.lat,
            lng: e.lngLat.lng,
            originalEvent: e.originalEvent,
            clientX: e.originalEvent.clientX,
            clientY: e.originalEvent.clientY,
          });
        });
      }
    });
  }

  setCenter(latLng) {
    this.mapboxMap.setCenter([latLng.lng, latLng.lat]);
  }

  getCenter() {
    const center = this.mapboxMap.getCenter();
    return { lat: center.lat, lng: center.lng };
  }

  setZoom(zoom) {
    this.mapboxMap.setZoom(zoom);
  }

  getZoom() {
    return this.mapboxMap.getZoom();
  }

  fitBounds(bounds, options) {
    if (!bounds || bounds.length === 0) return;
    const { padding, maxZoom } = normalizeFitOptions(options);

    // Calculate bounds
    let minLat = Infinity, maxLat = -Infinity;
    let minLng = Infinity, maxLng = -Infinity;

    bounds.forEach(point => {
      minLat = Math.min(minLat, point.lat);
      maxLat = Math.max(maxLat, point.lat);
      minLng = Math.min(minLng, point.lng);
      maxLng = Math.max(maxLng, point.lng);
    });

    this.mapboxMap.fitBounds(
      [[minLng, minLat], [maxLng, maxLat]],
      { padding, duration: 1000, ...(maxZoom ? { maxZoom } : {}) }
    );
  }

  panTo(latLng) {
    this.mapboxMap.panTo([latLng.lng, latLng.lat]);
  }

  flyTo(latLng, zoom = 14) {
    this.mapboxMap.flyTo({ center: [latLng.lng, latLng.lat], zoom, duration: 800 });
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
    this._bindViewportEvent(event);
  }

  /**
   * `move`/`idle` só se ligam ao mapa nativo quando alguém os pede.
   */
  _bindViewportEvent(event) {
    const nativeEvent = { move: 'move', idle: 'idle' }[event];
    if (!nativeEvent) return;
    this._boundViewportEvents ||= new Set();
    if (this._boundViewportEvents.has(event)) return;
    this._boundViewportEvents.add(event);
    this.mapboxMap.on(nativeEvent, () => {
      (this.listeners[event] || []).forEach((cb) => cb({}));
    });
  }

  off(event, callback) {
    if (this.listeners[event]) {
      const index = this.listeners[event].indexOf(callback);
      if (index > -1) {
        this.listeners[event].splice(index, 1);
      }
    }
  }

  getBounds() {
    const b = this.mapboxMap.getBounds();
    if (!b) return null;
    const ne = b.getNorthEast();
    const sw = b.getSouthWest();
    return { lat_min: sw.lat, lng_min: sw.lng, lat_max: ne.lat, lng_max: ne.lng };
  }

  getContainer() {
    return this.mapboxMap.getContainer();
  }

  createPolyline(options) {
    return new MapboxPolyline(this, options);
  }

  createMarker(options) {
    return new MapboxMarker(this, options);
  }

  createPolygon(options) {
    return new MapboxPolygon(this, options);
  }

  destroy() {
    this.listeners = {};
    this.mapboxMap.remove();
  }

  latLngToPixel(latLng) {
    const point = this.mapboxMap.project([latLng.lng, latLng.lat]);
    return { x: point.x, y: point.y };
  }

  getNativeMap() {
    return this.mapboxMap;
  }
}

/**
 * Mapbox Provider
 */
export class MapboxProvider extends IMapProvider {
  constructor() {
    super();
    this.name = 'mapbox';
  }

  async load(config) {
    this.config = config || {};
    if (mapboxLoaded) {
      console.log('[MapboxProvider] Already loaded');
      return;
    }

    if (!config.mapboxToken) {
      throw new Error('Mapbox token not configured');
    }

    mapboxgl.accessToken = config.mapboxToken;
    mapboxLoaded = true;

    console.log('[MapboxProvider] ✅ Mapbox GL JS loaded and configured');
  }

  createMap(container, options) {
    if (!mapboxLoaded) {
      throw new Error('MapboxProvider not loaded. Call load() first.');
    }
    // O estilo vem da configuração do backend (MAPBOX_CUSTOM_STYLE / MAPBOX_STYLE), salvo pedido explícito
    return new MapboxMap(container, { ...options, styleCandidates: mapboxStyleCandidates(this.config) });
  }

  getName() {
    return this.name;
  }

  isLoaded() {
    return mapboxLoaded;
  }
}
