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
 * @typedef {Object} MapControls
 * @property {boolean} [mapType]     - seletor de tipo de mapa (só Google)
 * @property {boolean} [streetView]  - Street View (só Google)
 * @property {boolean} [fullscreen]  - botão de ecrã inteiro (só Google)
 * @property {boolean} [traffic]     - camada de tráfego (só Google)
 * @property {boolean} [scale]       - escala (Mapbox/Leaflet)
 */

/**
 * @typedef {Object} MapOptions
 * @property {LatLng} center
 * @property {number} zoom
 * @property {string} [mapTypeId]    - 'roadmap' | 'terrain' | 'satellite' | 'hybrid' (Google); ignorado nos outros
 * @property {'light'|'dark'} [theme] - estilização base (Google aplica `utils/mapStyles`; os outros seguem o estilo configurado)
 * @property {MapControls} [controls]
 * @property {number} [minZoom]
 * @property {number} [maxZoom]
 * @property {string} [style]        - estilo Mapbox (`mapbox://…` ou alias); por omissão vem de `/api/config/`
 */

/**
 * @typedef {Object} PolygonOptions
 * @property {LatLng[]} path
 * @property {string} [strokeColor]
 * @property {number} [strokeWeight]
 * @property {number} [strokeOpacity]
 * @property {string} [fillColor]
 * @property {number} [fillOpacity]
 * @property {boolean} [clickable]   - default false (overlay passivo)
 */

/**
 * @typedef {Object} FitBoundsOptions
 * @property {number} [padding]  - px à volta (default 50)
 * @property {number} [maxZoom]  - não aproximar mais do que isto (um único ponto não vira zoom 20)
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
 * @property {string} [title]       - tooltip nativo
 * @property {string} [label]       - texto curto dentro do marcador (quando não há `iconUrl`)
 * @property {string} [markerType]  - 'origin' | 'destination' | 'intermediate' | 'preview' | 'default' (ver markerStyles.js)
 * @property {string} [color]       - cor do círculo (ex.: cor do estado); sobrepõe-se à do `markerType`
 * @property {number} [size]        - diâmetro do círculo em px; sobrepõe-se ao do `markerType`
 * @property {string} [iconUrl]     - imagem do marcador (ícone do dispositivo); substitui o círculo
 * @property {number} [iconSize]    - lado em px do ícone (default 24)
 */

/**
 * @typedef {Object} MarkerStyle - o que `IMarker.setStyle` aceita mudar sem recriar o marcador
 * @property {string} [color]
 * @property {number} [size]
 * @property {string} [label]
 * @property {string} [iconUrl]
 */

/**
 * @typedef {Object} LineStyle - o que `IPolyline.setStyle`/`IPolygon.setStyle` aceitam
 * @property {string} [strokeColor]
 * @property {number} [strokeWeight]
 * @property {number} [strokeOpacity]
 * @property {string} [fillColor]    - só polígonos
 * @property {number} [fillOpacity]  - só polígonos
 * @property {number} [zIndex]       - só Google (Mapbox/Leaflet desenham por ordem de criação)
 */

/**
 * @typedef {Object} BBox - caixa envolvente no formato que a API `?bbox=` consome
 * @property {number} lat_min
 * @property {number} lng_min
 * @property {number} lat_max
 * @property {number} lng_max
 */

/**
 * @typedef {Object} MapEvent - payload comum dos eventos (campos ausentes quando não se aplicam)
 * @property {number} [lat]
 * @property {number} [lng]
 * @property {Event}  [originalEvent]
 * @property {number} [clientX]
 * @property {number} [clientY]
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
   * Ajusta o mapa para mostrar os pontos.
   * @param {LatLng[]} bounds
   * @param {number|FitBoundsOptions} [options] - número = padding em px
   */
  fitBounds(bounds, options) {
    throw new Error('Method fitBounds() must be implemented');
  }

  /**
   * Caixa envolvente visível, ou `null` enquanto o mapa não renderizou.
   * @returns {BBox|null}
   */
  getBounds() {
    throw new Error('Method getBounds() must be implemented');
  }

  /**
   * Elemento DOM que contém o mapa (para posicionar overlays).
   * @returns {HTMLElement}
   */
  getContainer() {
    throw new Error('Method getContainer() must be implemented');
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
   * Adiciona listener de eventos.
   * Eventos comuns aos três providers:
   *  - `click`, `rightclick` → MapEvent com lat/lng e posição do rato
   *  - `move`  → dispara continuamente enquanto o viewport muda (pan/zoom)
   *  - `idle`  → dispara uma vez quando o viewport assenta (ler `getBounds()` aqui)
   * @param {string} event
   * @param {(e: MapEvent) => void} callback
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
   * Cria um polígono (ex.: área de manutenção)
   * @param {PolygonOptions} options
   * @returns {IPolygon}
   */
  createPolygon(options) {
    throw new Error('Method createPolygon() must be implemented');
  }

  /**
   * Cursor do rato sobre o mapa ('' repõe o padrão)
   * @param {string} cursor
   */
  setCursor(cursor) {
    throw new Error('Method setCursor() must be implemented');
  }

  /**
   * Avisa o mapa de que o container mudou de tamanho (ResizeObserver, ecrã inteiro)
   */
  resize() {
    throw new Error('Method resize() must be implemented');
  }

  /**
   * Muda o tema base. Google re-estiliza; Mapbox/Leaflet mantêm o estilo configurado.
   * @param {'light'|'dark'} theme
   */
  setTheme(theme) {
    // Por omissão: nada a fazer
  }

  /**
   * Destrói o mapa e limpa recursos
   */
  destroy() {
    throw new Error('Method destroy() must be implemented');
  }

  /**
   * Conversão de coordenadas geográficas para pixels **relativos ao container
   * do mapa** (o que um overlay posicionado com `position:absolute` precisa).
   * @param {LatLng} latLng
   * @returns {{x: number, y: number}|null} - `null` enquanto o mapa não tem projeção
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
   * Muda cor/espessura sem recriar (o realce de hover passa a partir daqui)
   * @param {LineStyle} style
   */
  setStyle(style) {
    throw new Error('Method setStyle() must be implemented');
  }

  /**
   * Adiciona listener. Eventos comuns: `click`, `rightclick`, `mouseover`,
   * `mouseout`, `mousemove` — todos com MapEvent (lat/lng/clientX/clientY).
   * O realce ao passar o rato é feito pelo próprio provider.
   * @param {string} event
   * @param {(e: MapEvent) => void} callback
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
 * Interface para Polígono
 */
export class IPolygon {
  /**
   * @param {LatLng[]} path
   */
  setPath(path) {
    throw new Error('Method setPath() must be implemented');
  }

  /**
   * @param {LineStyle} style
   */
  setStyle(style) {
    throw new Error('Method setStyle() must be implemented');
  }

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
   * Muda a aparência (cor do estado, tamanho, label, ícone) sem recriar
   * @param {MarkerStyle} style
   */
  setStyle(style) {
    throw new Error('Method setStyle() must be implemented');
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
