/**
 * Google Maps Provider Implementation
 * Implementa IMapProvider para Google Maps JavaScript API
 */

import { IMapProvider, IMap, IPolyline, IMarker } from './IMapProvider.js';

let googleMapsLoaded = false;
let loadingPromise = null;

/**
 * Implementação Google Maps do IPolyline
 */
class GooglePolyline extends IPolyline {
  constructor(map, options) {
    super();
    this.map = map;
    this.googleMap = map.googleMap;
    this.options = options;
    this.listeners = {};
    this.metadata = {};  // For custom metadata storage

    this.polyline = new google.maps.Polyline({
      path: options.path || [],
      map: this.googleMap,
      strokeColor: options.strokeColor || '#2563eb',
      strokeWeight: options.strokeWeight || 4,
      strokeOpacity: options.strokeOpacity || 0.9,
      editable: options.editable || false,
      draggable: options.draggable || false,
      clickable: options.clickable !== false,
      geodesic: true,
    });
  }

  setPath(path) {
    this.polyline.setPath(path);
  }

  getPath() {
    const path = this.polyline.getPath();
    return path.getArray().map(latLng => ({
      lat: latLng.lat(),
      lng: latLng.lng(),
    }));
  }

  setEditable(editable) {
    this.polyline.setEditable(editable);
  }

  setDraggable(draggable) {
    this.polyline.setDraggable(draggable);
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);

    // Convert event names to Google Maps format
    const googleEvent = event === 'rightclick' ? 'rightclick' : event;

    this.polyline.addListener(googleEvent, (e) => {
      const eventData = {
        lat: e.latLng?.lat(),
        lng: e.latLng?.lng(),
        domEvent: e.domEvent,
        originalEvent: e.domEvent,
        clientX: e.domEvent?.clientX,
        clientY: e.domEvent?.clientY,
        stop: () => e.domEvent?.stopPropagation?.(),
      };
      callback(eventData);
    });
  }

  // Alias for compatibility (Google Maps uses addListener natively)
  addListener(event, callback) {
    return this.on(event, callback);
  }

  // Metadata storage methods
  set(key, value) {
    this.metadata[key] = value;
    // Also store in native polyline if possible
    if (typeof this.polyline.set === 'function') {
      this.polyline.set(key, value);
    }
  }

  get(key) {
    // Try native polyline first
    if (typeof this.polyline.get === 'function') {
      return this.polyline.get(key);
    }
    return this.metadata[key];
  }

  remove() {
    this.polyline.setMap(null);
  }
}

/**
 * Implementação Google Maps do IMarker
 */
class GoogleMarkerClass extends IMarker {
  constructor(map, options) {
    super();
    this.map = map;
    this.googleMap = map.googleMap;
    this.listeners = {};

    // Get marker configuration based on type
    const markerType = options.markerType || 'default';
    const config = this._getMarkerConfig(markerType);

    // Create SVG icon with label
    const icon = this._createCustomIcon(config);

    this.marker = new google.maps.Marker({
      position: options.position,
      map: this.googleMap,
      draggable: options.draggable || false,
      title: options.title || '',
      icon: icon,
    });
  }

  setPosition(position) {
    this.marker.setPosition(position);
  }

  getPosition() {
    const pos = this.marker.getPosition();
    return { lat: pos.lat(), lng: pos.lng() };
  }

  setDraggable(draggable) {
    this.marker.setDraggable(draggable);
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);

    this.marker.addListener(event, (e) => {
      const eventData = {
        originalEvent: e.domEvent,
      };
      callback(eventData);
    });
  }

  // Alias for compatibility
  addListener(event, callback) {
    return this.on(event, callback);
  }

  remove() {
    this.marker.setMap(null);
  }

  /**
   * Get marker configuration based on type
   * @param {string} type - 'origin', 'destination', 'intermediate', 'default', 'preview'
   * @returns {{color: string, size: number, label: string}}
   */
  _getMarkerConfig(type) {
    const configs = {
      origin: {
        color: '#22c55e',
        size: 32,
        label: 'A'
      },
      destination: {
        color: '#ef4444',
        size: 32,
        label: 'B'
      },
      intermediate: {
        color: '#3b82f6',
        size: 20,
        label: ''
      },
      preview: {
        color: '#f59e0b',
        size: 20,
        label: ''
      },
      default: {
        color: '#dc2626',
        size: 24,
        label: ''
      }
    };

    return configs[type] || configs.default;
  }

  /**
   * Create custom SVG icon for Google Maps marker
   * @param {{color: string, size: number, label: string}} config
   * @returns {google.maps.Icon}
   */
  _createCustomIcon(config) {
    const svg = `
      <svg width="${config.size}" height="${config.size}" xmlns="http://www.w3.org/2000/svg">
        <circle cx="${config.size/2}" cy="${config.size/2}" r="${config.size/2 - 2}" 
                fill="${config.color}" stroke="white" stroke-width="3"/>
        ${config.label ? `
          <text x="${config.size/2}" y="${config.size/2 + config.size*0.15}" 
                text-anchor="middle" 
                fill="white" 
                font-size="${config.size * 0.6}px" 
                font-weight="bold" 
                font-family="Arial, sans-serif">${config.label}</text>
        ` : ''}
      </svg>
    `;

    return {
      url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg),
      scaledSize: new google.maps.Size(config.size, config.size),
      anchor: new google.maps.Point(config.size/2, config.size/2)
    };
  }
}

/**
 * Implementação Google Maps do IMap
 */
class GoogleMapClass extends IMap {
  constructor(container, options) {
    super();
    this.container = container;
    this.options = options;
    this.listeners = {};

    this.googleMap = new google.maps.Map(container, {
      center: options.center,
      zoom: options.zoom || 10,
      mapTypeId: options.mapTypeId || 'terrain',
    });
  }

  setCenter(latLng) {
    this.googleMap.setCenter(latLng);
  }

  getCenter() {
    const center = this.googleMap.getCenter();
    return { lat: center.lat(), lng: center.lng() };
  }

  setZoom(zoom) {
    this.googleMap.setZoom(zoom);
  }

  getZoom() {
    return this.googleMap.getZoom();
  }

  fitBounds(bounds, padding) {
    const googleBounds = new google.maps.LatLngBounds();
    bounds.forEach(point => {
      googleBounds.extend(new google.maps.LatLng(point.lat, point.lng));
    });

    const paddingValue = typeof padding === 'number' 
      ? { top: padding, right: padding, bottom: padding, left: padding }
      : padding;

    this.googleMap.fitBounds(googleBounds, paddingValue);
  }

  panTo(latLng) {
    this.googleMap.panTo(latLng);
  }

  flyTo(latLng, zoom = 14) {
    this.googleMap.panTo(latLng);
    this.googleMap.setZoom(zoom);
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);

    this.googleMap.addListener(event, (e) => {
      const eventData = {
        lat: e.latLng?.lat(),
        lng: e.latLng?.lng(),
        originalEvent: e.domEvent,
        clientX: e.domEvent?.clientX,
        clientY: e.domEvent?.clientY,
      };
      callback(eventData);
    });
  }

  off(event, callback) {
    if (this.listeners[event]) {
      const index = this.listeners[event].indexOf(callback);
      if (index > -1) {
        this.listeners[event].splice(index, 1);
      }
    }
    // Google Maps doesn't easily support removing specific listeners
  }

  createPolyline(options) {
    return new GooglePolyline(this, options);
  }

  createMarker(options) {
    return new GoogleMarkerClass(this, options);
  }

  destroy() {
    this.listeners = {};
    google.maps.event.clearInstanceListeners(this.googleMap);
  }

  latLngToPixel(latLng) {
    const projection = this.googleMap.getProjection();
    if (!projection) return { x: 0, y: 0 };

    const worldPoint = projection.fromLatLngToPoint(
      new google.maps.LatLng(latLng.lat, latLng.lng)
    );
    const scale = Math.pow(2, this.googleMap.getZoom());
    return { 
      x: worldPoint.x * scale, 
      y: worldPoint.y * scale 
    };
  }

  /**
   * Retorna a instância nativa do Google Maps (para compatibilidade legada)
   */
  getNativeMap() {
    return this.googleMap;
  }
}

/**
 * Google Maps Provider
 */
export class GoogleMapsProvider extends IMapProvider {
  constructor() {
    super();
    this.name = 'google';
  }

  async load(config) {
    if (googleMapsLoaded) {
      console.log('[GoogleMapsProvider] Already loaded');
      return;
    }

    if (loadingPromise) {
      console.log('[GoogleMapsProvider] Loading in progress, waiting...');
      return loadingPromise;
    }

    if (!config.googleMapsApiKey) {
      throw new Error('Google Maps API key not configured');
    }

    loadingPromise = new Promise((resolve, reject) => {
      // Check if already loaded by another script
      if (window.google?.maps) {
        console.log('[GoogleMapsProvider] Google Maps already present on window');
        googleMapsLoaded = true;
        resolve();
        return;
      }

      const script = document.createElement('script');
      script.src = `https://maps.googleapis.com/maps/api/js?key=${config.googleMapsApiKey}&libraries=places,drawing`;
      script.async = true;
      script.defer = true;

      script.onload = () => {
        googleMapsLoaded = true;
        console.log('[GoogleMapsProvider] ✅ Google Maps API loaded');
        resolve();
      };

      script.onerror = (error) => {
        console.error('[GoogleMapsProvider] ❌ Failed to load Google Maps API', error);
        reject(new Error('Failed to load Google Maps API'));
      };

      document.head.appendChild(script);
    });

    return loadingPromise;
  }

  createMap(container, options) {
    if (!googleMapsLoaded) {
      throw new Error('GoogleMapsProvider not loaded. Call load() first.');
    }
    return new GoogleMapClass(container, options);
  }

  getName() {
    return this.name;
  }

  isLoaded() {
    return googleMapsLoaded;
  }
}
