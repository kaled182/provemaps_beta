/**
 * Interface abstrata para providers de mapas
 * Define o contrato que todos os providers devem implementar
 * 
 * Suportado: Google Maps, Mapbox, OpenStreetMap, Esri
 */

/**
 * @typedef {Object} LatLng
 * @property {number} lat
 * @property {number} lng
 */

/**
 * @typedef {Object} MapOptions
 * @property {LatLng} center
 * @property {number} zoom
 * @property {string} [mapTypeId]
 */

/**
 * @typedef {Object} PolylineOptions
 * @property {LatLng[]} path
 * @property {string} [strokeColor]
 * @property {number} [strokeWeight]
 * @property {number} [strokeOpacity]
 * @property {boolean} [editable]
 * @property {boolean} [draggable]
 * @property {boolean} [clickable]
 */

/**
 * @typedef {Object} MarkerOptions
 * @property {LatLng} position
 * @property {boolean} [draggable]
 * @property {string} [title]
 */

/**
 * Interface para implementação de Map Provider
 */
export class IMapProvider {
  /**
   * Carrega as dependências do provider (scripts, CSS)
   * @param {Object} config - Configuração do provider (API keys, tokens)
   * @returns {Promise<void>}
   */
  async load(config) {
    throw new Error('Method load() must be implemented');
  }

  /**
   * Cria uma instância do mapa
   * @param {HTMLElement} container - Elemento DOM container
   * @param {MapOptions} options - Opções do mapa
   * @returns {IMap}
   */
  createMap(container, options) {
    throw new Error('Method createMap() must be implemented');
  }

  /**
   * Retorna o nome do provider
   * @returns {string}
   */
  getName() {
    throw new Error('Method getName() must be implemented');
  }

  /**
   * Verifica se o provider está carregado
   * @returns {boolean}
   */
  isLoaded() {
    throw new Error('Method isLoaded() must be implemented');
  }
}

/**
 * Interface para instância de mapa
 */
export class IMap {
  /**
   * Define o centro do mapa
   * @param {LatLng} latLng
   */
  setCenter(latLng) {
    throw new Error('Method setCenter() must be implemented');
  }

  /**
   * Retorna o centro do mapa
   * @returns {LatLng}
   */
  getCenter() {
    throw new Error('Method getCenter() must be implemented');
  }

  /**
   * Define o zoom
   * @param {number} zoom
   */
  setZoom(zoom) {
    throw new Error('Method setZoom() must be implemented');
  }

  /**
   * Retorna o zoom atual
   * @returns {number}
   */
  getZoom() {
    throw new Error('Method getZoom() must be implemented');
  }

  /**
   * Ajusta o mapa para mostrar os bounds
   * @param {LatLng[]} bounds
   * @param {number|Object} padding
   */
  fitBounds(bounds, padding) {
    throw new Error('Method fitBounds() must be implemented');
  }

  /**
   * Pan suave para uma coordenada
   * @param {LatLng} latLng
   */
  panTo(latLng) {
    throw new Error('Method panTo() must be implemented');
  }

  /**
   * Voa suavemente para uma localização com zoom
   * @param {{ lat: number, lng: number }} latLng
   * @param {number} zoom
   */
  flyTo(latLng, zoom) {
    // Fallback: comportamento básico via panTo + setZoom
    this.panTo(latLng);
  }

  /**
   * Adiciona listener de eventos
   * @param {string} event - Nome do evento (click, rightclick, etc.)
   * @param {Function} callback
   */
  on(event, callback) {
    throw new Error('Method on() must be implemented');
  }

  /**
   * Remove listener de eventos
   * @param {string} event
   * @param {Function} callback
   */
  off(event, callback) {
    throw new Error('Method off() must be implemented');
  }

  /**
   * Cria uma polyline
   * @param {PolylineOptions} options
   * @returns {IPolyline}
   */
  createPolyline(options) {
    throw new Error('Method createPolyline() must be implemented');
  }

  /**
   * Cria um marker
   * @param {MarkerOptions} options
   * @returns {IMarker}
   */
  createMarker(options) {
    throw new Error('Method createMarker() must be implemented');
  }

  /**
   * Destrói o mapa e limpa recursos
   */
  destroy() {
    throw new Error('Method destroy() must be implemented');
  }

  /**
   * Conversão de coordenadas geográficas para pixels
   * @param {LatLng} latLng
   * @returns {{x: number, y: number}}
   */
  latLngToPixel(latLng) {
    throw new Error('Method latLngToPixel() must be implemented');
  }
}

/**
 * Interface para Polyline
 */
export class IPolyline {
  /**
   * Define o caminho da polyline
   * @param {LatLng[]} path
   */
  setPath(path) {
    throw new Error('Method setPath() must be implemented');
  }

  /**
   * Retorna o caminho
   * @returns {LatLng[]}
   */
  getPath() {
    throw new Error('Method getPath() must be implemented');
  }

  /**
   * Define se é editável
   * @param {boolean} editable
   */
  setEditable(editable) {
    throw new Error('Method setEditable() must be implemented');
  }

  /**
   * Define se é draggable
   * @param {boolean} draggable
   */
  setDraggable(draggable) {
    throw new Error('Method setDraggable() must be implemented');
  }

  /**
   * Adiciona listener
   * @param {string} event
   * @param {Function} callback
   */
  on(event, callback) {
    throw new Error('Method on() must be implemented');
  }

  /**
   * Remove da mapa
   */
  remove() {
    throw new Error('Method remove() must be implemented');
  }
}

/**
 * Interface para Marker
 */
export class IMarker {
  /**
   * Define a posição
   * @param {LatLng} position
   */
  setPosition(position) {
    throw new Error('Method setPosition() must be implemented');
  }

  /**
   * Retorna a posição
   * @returns {LatLng}
   */
  getPosition() {
    throw new Error('Method getPosition() must be implemented');
  }

  /**
   * Define se é draggable
   * @param {boolean} draggable
   */
  setDraggable(draggable) {
    throw new Error('Method setDraggable() must be implemented');
  }

  /**
   * Adiciona listener
   * @param {string} event
   * @param {Function} callback
   */
  on(event, callback) {
    throw new Error('Method on() must be implemented');
  }

  /**
   * Remove do mapa
   */
  remove() {
    throw new Error('Method remove() must be implemented');
  }
}
