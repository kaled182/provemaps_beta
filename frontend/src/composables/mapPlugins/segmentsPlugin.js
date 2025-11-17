/**
 * Plugin de Segmentos de Fibra - Para visualização e monitoramento
 * 
 * Responsável por desenhar polylines de cabos de fibra no mapa,
 * exibir informações ao clicar, e atualizar cores baseado no status.
 */

import { colorForStatus } from '@/constants/segmentStatusColors';

export default function createSegmentsPlugin(context, options = {}) {
  const { map, google } = context;
  const {
    onSegmentClick = null,
    onSegmentHover = null,
    fetchSegments = null
  } = options;

  // Estado interno do plugin
  const polylines = new Map();
  const infoWindow = new google.maps.InfoWindow();

  /**
   * Desenha ou atualiza segmentos no mapa
   * @param {Array} segments - Array de segmentos de fibra
   */
  function drawSegments(segments) {
    if (!Array.isArray(segments)) {
      console.warn('[SegmentsPlugin] Expected array, got:', typeof segments);
      return;
    }

    // Remove segmentos que não existem mais
    const currentIds = new Set(segments.map(s => s.id));
    for (const [id, polyline] of polylines) {
      if (!currentIds.has(id)) {
        polyline.setMap(null);
        polylines.delete(id);
      }
    }

    // Adiciona ou atualiza segmentos
    segments.forEach(segment => {
      const existing = polylines.get(segment.id);
      const path = parseSegmentPath(segment);
      const color = colorForStatus(segment.status || 'unknown');

      if (existing) {
        // Atualiza polyline existente
        existing.setPath(path);
        existing.setOptions({ strokeColor: color });
      } else {
        // Cria nova polyline
        const polyline = new google.maps.Polyline({
          path,
          map,
          strokeColor: color,
          strokeWeight: 3,
          strokeOpacity: 0.8,
          geodesic: true,
          clickable: true
        });

        // Event listeners
        if (onSegmentClick) {
          polyline.addListener('click', (event) => {
            onSegmentClick(segment, event);
          });
        }

        if (onSegmentHover) {
          polyline.addListener('mouseover', (event) => {
            onSegmentHover(segment, event, true);
          });
          polyline.addListener('mouseout', (event) => {
            onSegmentHover(segment, event, false);
          });
        }

        polylines.set(segment.id, polyline);
      }
    });

    console.log(`[SegmentsPlugin] Drew ${segments.length} segments`);
  }

  /**
   * Converte geometria do segmento para path do Google Maps
   * @param {Object} segment - Segmento de fibra
   * @returns {Array<{lat: number, lng: number}>}
   */
  function parseSegmentPath(segment) {
    if (segment.geometry?.coordinates) {
      // GeoJSON LineString format: [[lng, lat], ...]
      return segment.geometry.coordinates.map(([lng, lat]) => ({ lat, lng }));
    }
    if (segment.path) {
      return segment.path;
    }
    return [];
  }

  /**
   * Exibe InfoWindow para um segmento
   * @param {Object} segment - Segmento
   * @param {google.maps.LatLng} position - Posição do clique
   */
  function showSegmentInfo(segment, position) {
    const content = `
      <div style="padding: 8px;">
        <h4 style="margin: 0 0 8px 0;">${segment.properties?.name || `Cabo #${segment.id}`}</h4>
        <p style="margin: 4px 0;"><strong>Status:</strong> ${segment.status || 'unknown'}</p>
        <p style="margin: 4px 0;"><strong>Length:</strong> ${segment.properties?.length || 'N/A'}</p>
      </div>
    `;
    infoWindow.setContent(content);
    infoWindow.setPosition(position);
    infoWindow.open(map);
  }

  /**
   * Ajusta o mapa para mostrar todos os segmentos
   */
  function fitBounds() {
    if (polylines.size === 0) return;

    const bounds = new google.maps.LatLngBounds();
    for (const polyline of polylines.values()) {
      const path = polyline.getPath();
      path.forEach(latLng => bounds.extend(latLng));
    }
    map.fitBounds(bounds);
  }

  /**
   * Limpa todos os segmentos do mapa
   */
  function clearSegments() {
    for (const polyline of polylines.values()) {
      polyline.setMap(null);
    }
    polylines.clear();
    infoWindow.close();
  }

  /**
   * Cleanup do plugin
   */
  function cleanup() {
    clearSegments();
  }

  return {
    drawSegments,
    showSegmentInfo,
    fitBounds,
    clearSegments,
    cleanup,
    // Getters
    get count() {
      return polylines.size;
    }
  };
}
