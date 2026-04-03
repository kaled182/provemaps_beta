import { defineStore } from 'pinia';
import { ref } from 'vue';

// Store responsible for spatial viewport-based segment loading
// Phase 11 Sprint 1 MVP
export const useMapStore = defineStore('map', () => {
  const segments = ref(new Map()); // id -> feature
  const sites = ref([]); // Lista de sites para marcadores
  const lastBbox = ref(null);
  const loading = ref(false);
  const error = ref(null);
  
  // --- NOVO STATE ---
  const focusedItem = ref(null); // Pode ser um site ou equipamento

  function bboxToString(b) {
    return `${b.lng_min},${b.lat_min},${b.lng_max},${b.lat_max}`;
  }

  async function fetchSegmentsByBbox(bbox) {
    loading.value = true;
    error.value = null;
    try {
      const qs = bboxToString(bbox);
      const resp = await fetch(`/api/v1/inventory/segments/?bbox=${qs}`, {
        credentials: 'include'
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      
      // API returns { segments: [...] } not { features: [...] }
      // Convert to GeoJSON-like structure for compatibility
      const segmentsList = data.segments || [];
      segmentsList.forEach(seg => {
        const feature = {
          id: seg.id,
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: seg.path_geojson?.coordinates || [],
          },
          properties: {
            route_id: seg.route_id,
            order: seg.order,
            length_km: seg.length_km,
            estimated_loss_db: seg.estimated_loss_db,
            measured_loss_db: seg.measured_loss_db,
            status: seg.status || 'unknown', // Now includes real status from backend
          },
        };
        segments.value.set(feature.id, feature);
      });
      
      lastBbox.value = bbox;
    } catch (e) {
      error.value = e.message;
      console.error('[mapStore] Failed to fetch segments', e);
    } finally {
      loading.value = false;
    }
  }

  async function fetchSites() {
    try {
      const resp = await fetch('/api/v1/sites/', {
        credentials: 'include'
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      sites.value = data.results || [];
    } catch (e) {
      console.error('[mapStore] Failed to fetch sites', e);
    }
  }

  function pruneOutside(bbox) {
    const toRemove = [];
    segments.value.forEach((feature, id) => {
      const coords = feature?.geometry?.coordinates || [];
      if (!coords.length) return;
      const [lng, lat] = coords[0];
      if (
        lng < bbox.lng_min || lng > bbox.lng_max ||
        lat < bbox.lat_min || lat > bbox.lat_max
      ) {
        toRemove.push(id);
      }
    });
    toRemove.forEach(id => segments.value.delete(id));
  }

  // --- NOVA ACTION ---
  /**
   * Define um item (site/equipamento) para o mapa focar.
   * @param {object} item - O objeto do site (deve ter latitude e longitude)
   */
  function focusOnItem(item) {
    if (!item) {
      console.warn('[mapStore] Tentativa de focar em item vazio');
      return;
    }

    const lat = Number(item.latitude ?? item.lat ?? item.site?.latitude);
    const lng = Number(item.longitude ?? item.lng ?? item.site?.longitude);

    if (Number.isNaN(lat) || Number.isNaN(lng)) {
      console.warn('[mapStore] Tentativa de focar em item sem coordenadas válidas:', item);
      return;
    }

    focusedItem.value = {
      ...item,
      latitude: lat,
      longitude: lng,
    };
  }

  /**
   * Limpa o foco.
   */
  function clearFocus() {
    focusedItem.value = null;
  }

  return {
    segments,
    sites,
    lastBbox,
    loading,
    error,
    focusedItem,
    fetchSegmentsByBbox,
    fetchSites,
    pruneOutside,
    focusOnItem,
    clearFocus,
  };
});

