/**
 * Mapbox Provider Implementation
 * Implementa IMapProvider para Mapbox GL JS
 */

import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { IMapProvider, IMap, IPolyline, IMarker } from './IMapProvider.js';

let mapboxLoaded = false;
let layerIdCounter = 0;
let markerIdCounter = 0;

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

    // Add source
    this.mapboxMap.addSource(this.sourceId, {
      type: 'geojson',
      data: {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: coordinates,
        },
      },
    });

    // Add layer
    this.mapboxMap.addLayer({
      id: this.layerId,
      type: 'line',
      source: this.sourceId,
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        'line-color': this.options.strokeColor || '#2563eb',
        'line-width': this.options.strokeWeight || 4,
        'line-opacity': this.options.strokeOpacity || 0.9,
      },
    });

    // Add click handler
    if (this.options.clickable !== false) {
      this.mapboxMap.on('click', this.layerId, this._handleClick.bind(this));
      this.mapboxMap.on('contextmenu', this.layerId, this._handleRightClick.bind(this));
    }
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
    if (this.mapboxMap.getLayer(this.layerId)) {
      this.mapboxMap.off('click', this.layerId, this._handleClick);
      this.mapboxMap.off('contextmenu', this.layerId, this._handleRightClick);
      this.mapboxMap.removeLayer(this.layerId);
    }
    if (this.mapboxMap.getSource(this.sourceId)) {
      this.mapboxMap.removeSource(this.sourceId);
    }
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
    // Create custom marker element
    const el = document.createElement('div');
    el.className = 'map-marker';
    el.style.width = '24px';
    el.style.height = '24px';
    el.style.borderRadius = '50%';
    el.style.backgroundColor = '#dc2626';
    el.style.border = '3px solid white';
    el.style.boxShadow = '0 2px 4px rgba(0,0,0,0.3)';
    el.style.cursor = this.options.draggable ? 'move' : 'pointer';

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

  setPosition(position) {
    this.position = position;
    this.marker.setLngLat([position.lng, position.lat]);
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

    // Create Mapbox map
    this.mapboxMap = new mapboxgl.Map({
      container: container,
      style: 'mapbox://styles/mapbox/streets-v12',
      center: [options.center.lng, options.center.lat],
      zoom: options.zoom || 10,
    });

    // Add controls
    this.mapboxMap.addControl(new mapboxgl.NavigationControl());

    // Setup event forwarding
    this._setupEvents();
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

  fitBounds(bounds, padding) {
    if (!bounds || bounds.length < 2) return;

    // Calculate bounds
    let minLat = Infinity, maxLat = -Infinity;
    let minLng = Infinity, maxLng = -Infinity;

    bounds.forEach(point => {
      minLat = Math.min(minLat, point.lat);
      maxLat = Math.max(maxLat, point.lat);
      minLng = Math.min(minLng, point.lng);
      maxLng = Math.max(maxLng, point.lng);
    });

    const paddingValue = typeof padding === 'number' 
      ? padding 
      : (padding?.top || 50);

    this.mapboxMap.fitBounds(
      [[minLng, minLat], [maxLng, maxLat]],
      { padding: paddingValue, duration: 1000 }
    );
  }

  panTo(latLng) {
    this.mapboxMap.panTo([latLng.lng, latLng.lat]);
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  off(event, callback) {
    if (this.listeners[event]) {
      const index = this.listeners[event].indexOf(callback);
      if (index > -1) {
        this.listeners[event].splice(index, 1);
      }
    }
  }

  createPolyline(options) {
    return new MapboxPolyline(this, options);
  }

  createMarker(options) {
    return new MapboxMarker(this, options);
  }

  destroy() {
    this.listeners = {};
    this.mapboxMap.remove();
  }

  latLngToPixel(latLng) {
    const point = this.mapboxMap.project([latLng.lng, latLng.lat]);
    return { x: point.x, y: point.y };
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
    return new MapboxMap(container, options);
  }

  getName() {
    return this.name;
  }

  isLoaded() {
    return mapboxLoaded;
  }
}
