import { setActivePinia, createPinia } from 'pinia';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useMapStore } from '../../src/stores/map';

// Mock fetch - Updated for new API response format (segments array, not features)
global.fetch = vi.fn(async () => ({
  ok: true,
  json: async () => ({ 
    count: 1,
    bbox: "-48,-16,-47.5,-15.5",
    segments: [
      { 
        id: 1, 
        route_id: 1,
        order: 1,
        length_km: 1.5,
        status: 'operational',
        path_geojson: {
          type: 'LineString',
          coordinates: [[-47.9, -15.78], [-47.89, -15.77]]
        }
      }
    ]
  })
}));

describe('map store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    fetch.mockClear();
  });

  it('fetches segments by bbox', async () => {
    const store = useMapStore();
    await store.fetchSegmentsByBbox({ lng_min: -48, lat_min: -16, lng_max: -47.5, lat_max: -15.5 });
    expect(store.segments.size).toBe(1);
  });
});
