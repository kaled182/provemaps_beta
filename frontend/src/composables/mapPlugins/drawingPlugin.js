/**
 * Plugin de Ferramentas de Desenho - Para Network Design
 * 
 * Fornece ferramentas interativas para desenhar rotas de fibra:
 * - Adicionar pontos clicando no mapa
 * - Arrastar markers para reposicionar
 * - Polyline editável com path dinâmico
 * - Cálculo de distância em tempo real
 */

export default function createDrawingPlugin(context, options = {}) {
  const { map, google } = context;
  const {
    onPathChange = null,
    onMarkerAdded = null,
    onMarkerMoved = null,
    onMarkerRemoved = null,
    editable = true
  } = options;

  // Estado interno
  let polyline = null;
  const markers = [];
  const path = [];
  let clickListener = null;

  /**
   * Inicia modo de desenho
   */
  function startDrawing() {
    if (!editable) {
      console.warn('[DrawingPlugin] Drawing is not editable');
      return;
    }

    // Cria polyline editável se não existir
    if (!polyline) {
      polyline = new google.maps.Polyline({
        map,
        strokeColor: '#2563eb',
        strokeWeight: 3,
        strokeOpacity: 0.8,
        geodesic: true,
        editable: false // Controlamos manualmente com markers
      });
    }

    // Adiciona listener de clique no mapa
    if (!clickListener) {
      clickListener = map.addListener('click', (event) => {
        addPoint(event.latLng);
      });
    }

    console.log('[DrawingPlugin] Drawing mode started');
  }

  /**
   * Para modo de desenho
   */
  function stopDrawing() {
    if (clickListener) {
      google.maps.event.removeListener(clickListener);
      clickListener = null;
    }
    console.log('[DrawingPlugin] Drawing mode stopped');
  }

  /**
   * Adiciona um ponto ao path
   * @param {google.maps.LatLng|{lat: number, lng: number}} latLng - Coordenadas
   * @returns {google.maps.Marker}
   */
  function addPoint(latLng) {
    const position = latLng instanceof google.maps.LatLng
      ? latLng
      : new google.maps.LatLng(latLng.lat, latLng.lng);

    // Cria marker arrastável
    const marker = new google.maps.Marker({
      position,
      map,
      draggable: editable,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        fillColor: '#2563eb',
        fillOpacity: 1,
        strokeColor: '#ffffff',
        strokeWeight: 2,
        scale: 6
      },
      label: {
        text: `${markers.length + 1}`,
        color: '#ffffff',
        fontSize: '10px',
        fontWeight: 'bold'
      }
    });

    // Event listeners
    marker.addListener('dragend', () => {
      updatePath();
      if (onMarkerMoved) {
        onMarkerMoved(markers.indexOf(marker), marker.getPosition());
      }
    });

    marker.addListener('rightclick', () => {
      removePoint(marker);
    });

    markers.push(marker);
    updatePath();

    if (onMarkerAdded) {
      onMarkerAdded(markers.length - 1, position);
    }

    return marker;
  }

  /**
   * Remove um ponto do path
   * @param {google.maps.Marker|number} markerOrIndex - Marker ou índice
   */
  function removePoint(markerOrIndex) {
    const index = typeof markerOrIndex === 'number'
      ? markerOrIndex
      : markers.indexOf(markerOrIndex);

    if (index === -1 || index >= markers.length) {
      return;
    }

    const marker = markers[index];
    marker.setMap(null);
    markers.splice(index, 1);

    // Atualiza labels dos markers restantes
    updateMarkerLabels();
    updatePath();

    if (onMarkerRemoved) {
      onMarkerRemoved(index);
    }
  }

  /**
   * Atualiza o path da polyline baseado nos markers
   */
  function updatePath() {
    const newPath = markers.map(m => m.getPosition());
    path.length = 0;
    path.push(...newPath);

    if (polyline) {
      polyline.setPath(newPath);
    }

    if (onPathChange) {
      onPathChange(getPathCoordinates(), getDistance());
    }
  }

  /**
   * Atualiza labels numerados dos markers
   */
  function updateMarkerLabels() {
    markers.forEach((marker, index) => {
      marker.setLabel({
        text: `${index + 1}`,
        color: '#ffffff',
        fontSize: '10px',
        fontWeight: 'bold'
      });
    });
  }

  /**
   * Define um path completo (substitui o atual)
   * @param {Array<{lat: number, lng: number}>} coordinates - Array de coordenadas
   */
  function setPath(coordinates) {
    // Garante que polyline existe antes de adicionar pontos
    if (!polyline) {
      polyline = new google.maps.Polyline({
        map,
        strokeColor: '#2563eb',
        strokeWeight: 3,
        strokeOpacity: 0.8,
        geodesic: true,
        editable: false
      });
    }
    
    clearPath();
    coordinates.forEach(coord => addPoint(coord));
  }

  /**
   * Retorna path atual como array de coordenadas
   * @returns {Array<{lat: number, lng: number}>}
   */
  function getPathCoordinates() {
    return markers.map(m => {
      const pos = m.getPosition();
      return { lat: pos.lat(), lng: pos.lng() };
    });
  }

  /**
   * Calcula distância total do path em metros
   * @returns {number}
   */
  function getDistance() {
    if (path.length < 2) return 0;

    let distance = 0;
    for (let i = 0; i < path.length - 1; i++) {
      distance += google.maps.geometry.spherical.computeDistanceBetween(
        path[i],
        path[i + 1]
      );
    }
    return distance;
  }

  /**
   * Calcula distância em quilômetros
   * @returns {number}
   */
  function getDistanceKm() {
    return getDistance() / 1000;
  }

  /**
   * Limpa todo o path
   */
  function clearPath() {
    markers.forEach(m => m.setMap(null));
    markers.length = 0;
    path.length = 0;
    if (polyline) {
      polyline.setPath([]);
    }

    if (onPathChange) {
      onPathChange([], 0);
    }
  }

  /**
   * Ajusta o mapa para mostrar todo o path
   */
  function fitBounds() {
    if (markers.length === 0) return;

    const bounds = new google.maps.LatLngBounds();
    markers.forEach(m => bounds.extend(m.getPosition()));
    map.fitBounds(bounds);
  }

  /**
   * Cleanup do plugin
   */
  function cleanup() {
    stopDrawing();
    clearPath();
    if (polyline) {
      polyline.setMap(null);
      polyline = null;
    }
  }

  /**
   * Retorna a instância da polyline para adicionar listeners customizados
   * @returns {google.maps.Polyline|null}
   */
  function getPolyline() {
    return polyline;
  }

  return {
    startDrawing,
    stopDrawing,
    addPoint,
    removePoint,
    setPath,
    getPathCoordinates,
    getDistance,
    getDistanceKm,
    clearPath,
    fitBounds,
    cleanup,
    getPolyline,
    // Getters
    get pointCount() {
      return markers.length;
    },
    get isDrawing() {
      return clickListener !== null;
    }
  };
}
