/**
 * Google Maps API Adapter
 * 
 * Provides a Google Maps-compatible API layer that works with multiple map providers.
 * When Mapbox is configured, this creates a fake `google.maps` object that translates
 * calls to Mapbox GL JS under the hood.
 * 
 * Supports:
 * - google.maps.Map → mapboxgl.Map
 * - google.maps.Polyline → Mapbox layer + source
 * - google.maps.Marker → mapboxgl.Marker  
 * - google.maps.LatLng, LatLngBounds, Point
 * - Event system (.addListener → .on)
 */

import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

// Counter for unique IDs
let layerCounter = 0;
let markerCounter = 0;

/**
 * LatLng adapter (Google Maps format → Mapbox array)
 */
class LatLngAdapter {
  constructor(lat, lng) {
    this._lat = lat;
    this._lng = lng;
  }

  lat() {
    return this._lat;
  }

  lng() {
    return this._lng;
  }

  toMapbox() {
    return [this._lng, this._lat]; // Mapbox uses [lng, lat]
  }

  toString() {
    return `(${this._lat}, ${this._lng})`;
  }
}

/**
 * Point adapter (pixel coordinates)
 */
class PointAdapter {
  constructor(x, y) {
    this.x = x;
    this.y = y;
  }
}

/**
 * LatLngBounds adapter
 */
class LatLngBoundsAdapter {
  constructor() {
    this._sw = null; // southwest corner
    this._ne = null; // northeast corner
  }

  extend(latLng) {
    const lat = latLng.lat();
    const lng = latLng.lng();

    if (!this._sw) {
      this._sw = { lat, lng };
      this._ne = { lat, lng };
    } else {
      this._sw.lat = Math.min(this._sw.lat, lat);
      this._sw.lng = Math.min(this._sw.lng, lng);
      this._ne.lat = Math.max(this._ne.lat, lat);
      this._ne.lng = Math.max(this._ne.lng, lng);
    }
  }

  getCenter() {
    if (!this._sw || !this._ne) return null;
    return new LatLngAdapter(
      (this._sw.lat + this._ne.lat) / 2,
      (this._sw.lng + this._ne.lng) / 2
    );
  }

  toMapbox() {
    if (!this._sw || !this._ne) return null;
    return [
      [this._sw.lng, this._sw.lat], // southwest
      [this._ne.lng, this._ne.lat], // northeast
    ];
  }
}

/**
 * Polyline adapter (Google Maps Polyline → Mapbox line layer)
 */
class PolylineAdapter {
  constructor(options) {
    this.map = options.map;
    this.path = options.path || [];
    this.options = options;
    this.listeners = {};
    this.layerId = `polyline-${++layerCounter}`;
    this.sourceId = `polyline-source-${layerCounter}`;
    this._editable = false;
    this._draggable = false;

    if (this.map) {
      this._addToMap();
    }
  }

  _addToMap() {
    const mapboxMap = this.map._mapboxMap;
    const coordinates = this.path.map(p => [p.lng, p.lat]);

    // Add source
    mapboxMap.addSource(this.sourceId, {
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
    mapboxMap.addLayer({
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

    // Handle click events
    if (this.options.clickable !== false) {
      mapboxMap.on('click', this.layerId, this._handleClick.bind(this));
      mapboxMap.on('contextmenu', this.layerId, this._handleRightClick.bind(this));
    }
  }

  _handleClick(e) {
    if (this.listeners.click) {
      this.listeners.click.forEach(cb => {
        cb({
          latLng: new LatLngAdapter(e.lngLat.lat, e.lngLat.lng),
          domEvent: e.originalEvent,
        });
      });
    }
  }

  _handleRightClick(e) {
    if (this.listeners.rightclick) {
      this.listeners.rightclick.forEach(cb => {
        cb({
          latLng: new LatLngAdapter(e.lngLat.lat, e.lngLat.lng),
          domEvent: e.originalEvent,
          stop: () => e.preventDefault(),
        });
      });
    }
  }

  addListener(eventName, callback) {
    if (!this.listeners[eventName]) {
      this.listeners[eventName] = [];
    }
    this.listeners[eventName].push(callback);
  }

  setMap(map) {
    // Remove from current map
    if (this.map && this.map._mapboxMap) {
      const mapboxMap = this.map._mapboxMap;
      if (mapboxMap.getLayer(this.layerId)) {
        mapboxMap.removeLayer(this.layerId);
      }
      if (mapboxMap.getSource(this.sourceId)) {
        mapboxMap.removeSource(this.sourceId);
      }
    }

    this.map = map;
    if (map) {
      this._addToMap();
    }
  }

  setPath(path) {
    this.path = path;
    if (this.map && this.map._mapboxMap) {
      const mapboxMap = this.map._mapboxMap;
      const coordinates = path.map(p => [p.lng, p.lat]);
      const source = mapboxMap.getSource(this.sourceId);
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
  }

  setEditable(editable) {
    this._editable = editable;
    console.log(`[PolylineAdapter] setEditable(${editable}) - ⚠️ Editing not fully implemented for Mapbox`);
    // TODO: Implement with mapbox-gl-draw if needed
  }

  setDraggable(draggable) {
    this._draggable = draggable;
    console.log(`[PolylineAdapter] setDraggable(${draggable}) - ⚠️ Dragging not fully implemented for Mapbox`);
  }

  getPath() {
    return this.path;
  }
}

/**
 * Marker adapter (Google Maps Marker → Mapbox Marker)
 */
class MarkerAdapter {
  constructor(options) {
    this.position = options.position;
    this.map = options.map;
    this.options = options;
    this.listeners = {};
    this.markerId = `marker-${++markerCounter}`;

    if (this.map) {
      this._addToMap();
    }
  }

  _addToMap() {
    const mapboxMap = this.map._mapboxMap;
    const lngLat = [this.position.lng, this.position.lat];

    // Create DOM element for marker
    const el = document.createElement('div');
    el.className = 'custom-marker';
    el.style.width = '20px';
    el.style.height = '20px';
    el.style.borderRadius = '50%';
    el.style.backgroundColor = '#2563eb';
    el.style.border = '2px solid white';
    el.style.cursor = this.options.draggable ? 'move' : 'pointer';

    this._mapboxMarker = new mapboxgl.Marker({
      element: el,
      draggable: this.options.draggable || false,
    })
      .setLngLat(lngLat)
      .addTo(mapboxMap);

    // Handle drag events
    if (this.options.draggable) {
      this._mapboxMarker.on('drag', () => {
        const lngLat = this._mapboxMarker.getLngLat();
        this.position = { lat: lngLat.lat, lng: lngLat.lng };
        if (this.listeners.drag) {
          this.listeners.drag.forEach(cb => cb());
        }
      });

      this._mapboxMarker.on('dragend', () => {
        const lngLat = this._mapboxMarker.getLngLat();
        this.position = { lat: lngLat.lat, lng: lngLat.lng };
        if (this.listeners.dragend) {
          this.listeners.dragend.forEach(cb => cb());
        }
      });
    }

    // Handle click events
    el.addEventListener('click', (e) => {
      if (this.listeners.click) {
        this.listeners.click.forEach(cb => cb({ domEvent: e }));
      }
    });
  }

  addListener(eventName, callback) {
    if (!this.listeners[eventName]) {
      this.listeners[eventName] = [];
    }
    this.listeners[eventName].push(callback);
  }

  setMap(map) {
    if (this._mapboxMarker) {
      this._mapboxMarker.remove();
    }

    this.map = map;
    if (map) {
      this._addToMap();
    }
  }

  setPosition(position) {
    this.position = position;
    if (this._mapboxMarker) {
      this._mapboxMarker.setLngLat([position.lng, position.lat]);
    }
  }

  getPosition() {
    return this.position;
  }
}

/**
 * Map adapter (Google Maps Map → Mapbox Map)
 */
class MapAdapter {
  constructor(element, options) {
    this.element = element;
    this.options = options;
    this.listeners = {};

    // Initialize Mapbox map
    this._mapboxMap = new mapboxgl.Map({
      container: element,
      style: 'mapbox://styles/mapbox/streets-v12',
      center: [options.center.lng, options.center.lat],
      zoom: options.zoom || 10,
    });

    this._mapboxMap.addControl(new mapboxgl.NavigationControl());

    // Setup event forwarding
    this._setupEvents();
  }

  _setupEvents() {
    // Click events
    this._mapboxMap.on('click', (e) => {
      if (this.listeners.click) {
        this.listeners.click.forEach(cb => {
          cb({
            latLng: new LatLngAdapter(e.lngLat.lat, e.lngLat.lng),
            domEvent: e.originalEvent,
          });
        });
      }
    });

    // Right-click events
    this._mapboxMap.on('contextmenu', (e) => {
      if (this.listeners.rightclick) {
        this.listeners.rightclick.forEach(cb => {
          cb({
            latLng: new LatLngAdapter(e.lngLat.lat, e.lngLat.lng),
            domEvent: e.originalEvent,
            stop: () => e.preventDefault(),
          });
        });
      }
    });
  }

  addListener(eventName, callback) {
    if (!this.listeners[eventName]) {
      this.listeners[eventName] = [];
    }
    this.listeners[eventName].push(callback);
  }

  fitBounds(bounds, padding) {
    const mapboxBounds = bounds.toMapbox();
    if (!mapboxBounds) return;

    const paddingValue = typeof padding === 'number' 
      ? padding 
      : (padding?.top || 50);

    this._mapboxMap.fitBounds(mapboxBounds, {
      padding: paddingValue,
      duration: 1000,
    });
  }

  getProjection() {
    // Simplified projection for coordinate conversion
    return {
      fromLatLngToPoint: (latLng) => {
        const zoom = this._mapboxMap.getZoom();
        const scale = Math.pow(2, zoom);
        const point = this._mapboxMap.project([latLng.lng(), latLng.lat()]);
        return new PointAdapter(point.x / scale, point.y / scale);
      },
    };
  }

  getZoom() {
    return this._mapboxMap.getZoom();
  }

  setZoom(zoom) {
    this._mapboxMap.setZoom(zoom);
  }

  getCenter() {
    const center = this._mapboxMap.getCenter();
    return new LatLngAdapter(center.lat, center.lng);
  }

  setCenter(latLng) {
    this._mapboxMap.setCenter([latLng.lng, latLng.lat]);
  }

  panTo(latLng) {
    this._mapboxMap.panTo([latLng.lng, latLng.lat]);
  }
}

/**
 * Event utility
 */
const eventAdapter = {
  clearInstanceListeners: (instance) => {
    if (instance.listeners) {
      instance.listeners = {};
    }
    console.log('[EventAdapter] Cleared listeners from instance');
  },
};

/**
 * Create fake google.maps namespace for Mapbox
 */
export function createGoogleMapsAdapter() {
  if (window.google && window.google.maps) {
    console.log('[MapAdapter] Google Maps already loaded, using native API');
    return window.google;
  }

  console.log('[MapAdapter] Creating Google Maps adapter for Mapbox');

  const googleMapsAdapter = {
    maps: {
      Map: MapAdapter,
      Marker: MarkerAdapter,
      Polyline: PolylineAdapter,
      LatLng: LatLngAdapter,
      LatLngBounds: LatLngBoundsAdapter,
      Point: PointAdapter,
      event: eventAdapter,
    },
  };

  return googleMapsAdapter;
}

/**
 * Initialize map provider adapter based on configuration
 */
export async function initializeMapAdapter(config) {
  const provider = config.mapProvider || 'google';

  if (provider === 'mapbox') {
    console.log('[MapAdapter] Initializing Mapbox adapter...');
    
    // Set Mapbox access token
    if (config.mapboxToken) {
      mapboxgl.accessToken = config.mapboxToken;
    } else {
      console.error('[MapAdapter] Mapbox token not found in configuration!');
      throw new Error('Mapbox token required but not configured');
    }

    // Install fake google.maps namespace
    window.google = createGoogleMapsAdapter();
    
    console.log('[MapAdapter] ✅ Mapbox adapter installed as window.google.maps');
    return true;
  } else if (provider === 'google') {
    console.log('[MapAdapter] Using native Google Maps API');
    // Google Maps will be loaded by googleMapsLoader
    return false;
  } else {
    console.warn(`[MapAdapter] Unsupported provider: ${provider}`);
    return false;
  }
}
