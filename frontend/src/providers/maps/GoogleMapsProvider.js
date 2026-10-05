/**
 * Google Maps Provider Implementation
 * Implementa IMapProvider para Google Maps JavaScript API
 */

import { IMapProvider, IMap, IPolyline, IMarker, IPolygon } from './IMapProvider.js';
import { getMarkerConfig } from './markerStyles.js';
import { getMapStyles } from '../../utils/mapStyles.js';

let googleMapsLoaded = false;
let loadingPromise = null;

// Fundo do mapa enquanto os tiles carregam, por tema (era do CustomMapViewer)
const BACKGROUND_BY_THEME = { dark: '#242f3e', light: '#F1F3F4' };

function normalizeFitOptions(options) {
  if (typeof options === 'number') return { padding: options, maxZoom: undefined };
  return { padding: options?.padding ?? options?.top ?? 50, maxZoom: options?.maxZoom };
}

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

    this._base = {
      strokeWeight: options.strokeWeight || 4,
      strokeOpacity: options.strokeOpacity || 0.9,
    };
    if (options.clickable !== false) {
      this.polyline.addListener('mouseover', () => {
        this.polyline.setOptions({ strokeWeight: this._base.strokeWeight + 2, strokeOpacity: 1 });
      });
      this.polyline.addListener('mouseout', () => {
        this.polyline.setOptions({ ...this._base });
      });
    }
  }

  setPath(path) {
    this.polyline.setPath(path);
  }

  setStyle(style) {
    const next = {};
    if (style.strokeColor !== undefined) next.strokeColor = style.strokeColor;
    if (style.strokeWeight !== undefined) next.strokeWeight = this._base.strokeWeight = style.strokeWeight;
    if (style.strokeOpacity !== undefined) next.strokeOpacity = this._base.strokeOpacity = style.strokeOpacity;
    if (style.zIndex !== undefined) next.zIndex = style.zIndex;
    this.polyline.setOptions(next);
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
    google.maps.event.clearInstanceListeners(this.polyline);
    this.polyline.setMap(null);
    this.listeners = {};
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

    this._style = {
      color: options.color ?? config.color,
      size: options.size ?? config.size,
      label: options.label ?? config.label,
      iconUrl: options.iconUrl,
      iconSize: options.iconSize || 24,
    };

    this.marker = new google.maps.Marker({
      position: options.position,
      map: this.googleMap,
      draggable: options.draggable || false,
      title: options.title || '',
      icon: this._buildIcon(),
    });
  }

  /** Ícone por URL (ex.: ícone do dispositivo) ou o círculo SVG com a cor/tamanho atuais */
  _buildIcon() {
    const s = this._style;
    return s.iconUrl
      ? this._createUrlIcon(s.iconUrl, s.iconSize)
      : this._createCustomIcon({ color: s.color, size: s.size, label: s.label });
  }

  setStyle(style) {
    this._style = { ...this._style, ...style };
    this.marker.setIcon(this._buildIcon());
  }

  _createUrlIcon(url, size) {
    return {
      url,
      scaledSize: new google.maps.Size(size, size),
      anchor: new google.maps.Point(size / 2, size / 2),
    };
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
    google.maps.event.clearInstanceListeners(this.marker);
    this.marker.setMap(null);
    this.listeners = {};
  }

  /**
   * Estilo do marcador por tipo — tabela partilhada em `markerStyles.js`.
   * @param {string} type - 'origin', 'destination', 'intermediate', 'default', 'preview'
   * @returns {{color: string, size: number, label: string}}
   */
  _getMarkerConfig(type) {
    return getMarkerConfig(type);
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
 * Implementação Google Maps do IPolygon
 */
class GooglePolygon extends IPolygon {
  constructor(map, options) {
    super();
    this.polygon = new google.maps.Polygon({
      paths: options.path || [],
      map: map.googleMap,
      strokeColor: options.strokeColor || '#f59e0b',
      strokeOpacity: options.strokeOpacity ?? 0.9,
      strokeWeight: options.strokeWeight || 2,
      fillColor: options.fillColor || options.strokeColor || '#f59e0b',
      fillOpacity: options.fillOpacity ?? 0.12,
      clickable: options.clickable ?? false,
    });
  }

  setPath(path) {
    this.polygon.setPaths(path || []);
  }

  setStyle(style) {
    this.polygon.setOptions(style);
  }

  remove() {
    this.polygon.setMap(null);
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

    const controls = options.controls || {};
    const theme = options.theme;

    this.googleMap = new google.maps.Map(container, {
      center: options.center,
      zoom: options.zoom || 10,
      mapTypeId: options.mapTypeId || 'terrain',
      ...(theme ? { styles: getMapStyles(theme, theme), backgroundColor: BACKGROUND_BY_THEME[theme] } : {}),
      mapTypeControl: controls.mapType ?? true,
      streetViewControl: controls.streetView ?? true,
      fullscreenControl: controls.fullscreen ?? true,
      zoomControl: true,
      gestureHandling: 'greedy',
      tilt: 0,
      ...(options.minZoom ? { minZoom: options.minZoom } : {}),
      ...(options.maxZoom ? { maxZoom: options.maxZoom } : {}),
    });

    if (controls.traffic) {
      this.trafficLayer = new google.maps.TrafficLayer();
      this.trafficLayer.setMap(this.googleMap);
    }
  }

  setTheme(theme) {
    if (!theme) return;
    this.googleMap.setOptions({ styles: getMapStyles(theme, theme), backgroundColor: BACKGROUND_BY_THEME[theme] });
  }

  setCursor(cursor) {
    this.googleMap.setOptions({ draggableCursor: cursor || '' });
  }

  resize() {
    google.maps.event.trigger(this.googleMap, 'resize');
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

  fitBounds(bounds, options) {
    if (!bounds || bounds.length === 0) return;
    const { padding, maxZoom } = normalizeFitOptions(options);
    const googleBounds = new google.maps.LatLngBounds();
    bounds.forEach(point => {
      googleBounds.extend(new google.maps.LatLng(point.lat, point.lng));
    });

    this.googleMap.fitBounds(googleBounds, { top: padding, right: padding, bottom: padding, left: padding });

    if (maxZoom) {
      // O Google aproxima ao máximo num só ponto; corrige-se quando o viewport assentar
      google.maps.event.addListenerOnce(this.googleMap, 'idle', () => {
        if (this.googleMap.getZoom() > maxZoom) this.googleMap.setZoom(maxZoom);
      });
    }
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
    // `move` é contínuo (bounds_changed); `idle` e `click` existem com o mesmo nome.
    // Eventos de viewport chegam sem argumento, daí os `?.`.
    const nativeEvent = event === 'move' ? 'bounds_changed' : event;
    const handle = this.googleMap.addListener(nativeEvent, (e) => {
      callback({
        lat: e?.latLng?.lat(),
        lng: e?.latLng?.lng(),
        originalEvent: e?.domEvent,
        clientX: e?.domEvent?.clientX,
        clientY: e?.domEvent?.clientY,
      });
    });
    this.listeners[event].push({ callback, handle });
  }

  off(event, callback) {
    const list = this.listeners[event];
    if (!list) return;
    const index = list.findIndex((entry) => entry.callback === callback);
    if (index > -1) {
      google.maps.event.removeListener(list[index].handle);
      list.splice(index, 1);
    }
  }

  getBounds() {
    const b = this.googleMap.getBounds();
    if (!b) return null;
    const ne = b.getNorthEast();
    const sw = b.getSouthWest();
    return { lat_min: sw.lat(), lng_min: sw.lng(), lat_max: ne.lat(), lng_max: ne.lng() };
  }

  getContainer() {
    return this.container;
  }

  createPolyline(options) {
    return new GooglePolyline(this, options);
  }

  createMarker(options) {
    return new GoogleMarkerClass(this, options);
  }

  createPolygon(options) {
    return new GooglePolygon(this, options);
  }

  destroy() {
    this.listeners = {};
    if (this.trafficLayer) this.trafficLayer.setMap(null);
    google.maps.event.clearInstanceListeners(this.googleMap);
  }

  latLngToPixel(latLng) {
    // Pixel relativo ao container: ponto-mundo do alvo menos o do canto
    // noroeste visível, à escala do zoom (mapa sem rotação/inclinação).
    const projection = this.googleMap.getProjection();
    const bounds = this.googleMap.getBounds();
    if (!projection || !bounds) return null;

    const scale = Math.pow(2, this.googleMap.getZoom());
    const northWest = new google.maps.LatLng(bounds.getNorthEast().lat(), bounds.getSouthWest().lng());
    const nwPoint = projection.fromLatLngToPoint(northWest);
    const point = projection.fromLatLngToPoint(new google.maps.LatLng(latLng.lat, latLng.lng));
    return {
      x: (point.x - nwPoint.x) * scale,
      y: (point.y - nwPoint.y) * scale,
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
