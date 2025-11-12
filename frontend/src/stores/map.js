import { defineStore } from 'pinia';
import { ref } from 'vue';

// Store responsible for spatial viewport-based segment loading
// Phase 11 Sprint 1 MVP
export const useMapStore = defineStore('map', () => {
  const segments = ref(new Map()); // id -> feature
  const lastBbox = ref(null);
  const loading = ref(false);
  const error = ref(null);

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

  return {
    segments,
    lastBbox,
    loading,
    error,
    fetchSegmentsByBbox,
    pruneOutside,
  };
});
