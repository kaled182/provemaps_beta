/**
 * EV-0012d — desenho de traçado sobre IMap (substitui o drawingPlugin Google-only).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createRouteDrawing, normalizePoint, haversineMeters } from '@/composables/useRouteDrawing';

function fakeMap() {
  const handlers = {};
  const map = {
    handlers,
    polylines: [],
    markers: [],
    on: vi.fn((e, cb) => { (handlers[e] ||= []).push(cb); }),
    off: vi.fn((e, cb) => { handlers[e] = (handlers[e] || []).filter((h) => h !== cb); }),
    fire(e, pl) { (handlers[e] || []).forEach((cb) => cb(pl)); },
    createPolyline: vi.fn((opts) => {
      const p = { opts, path: opts.path, setPath: vi.fn(function (path) { this.path = path; }), remove: vi.fn() };
      map.polylines.push(p);
      return p;
    }),
    createMarker: vi.fn((opts) => {
      const h = {};
      const m = { opts, position: { ...opts.position }, h, on: vi.fn((e, cb) => { (h[e] ||= []).push(cb); }), fire(e, pl) { (h[e] || []).forEach((cb) => cb(pl)); }, getPosition() { return this.position; }, setStyle: vi.fn(), remove: vi.fn() };
      map.markers.push(m);
      return m;
    }),
    fitBounds: vi.fn(),
  };
  return map;
}

let map;
beforeEach(() => { map = fakeMap(); });

describe('createRouteDrawing', () => {
  it('start liga o clique do mapa; cada clique vira um vértice numerado e a polyline cresce', () => {
    const onPathChange = vi.fn();
    const d = createRouteDrawing(map, { onPathChange });
    d.start();
    expect(map.handlers.click).toHaveLength(1);
    expect(d.isDrawing).toBe(true);

    map.fire('click', { lat: 1, lng: 2 });
    map.fire('click', { lat: 3, lng: 4 });
    map.fire('click', { lat: undefined, lng: 9 }); // ignorado

    expect(d.pointCount).toBe(2);
    expect(map.createMarker.mock.calls.map(([o]) => o.label)).toEqual(['1', '2']);
    expect(map.createMarker.mock.calls[0][0]).toEqual(expect.objectContaining({ draggable: true, markerType: 'intermediate' }));
    expect(map.polylines[0].path).toEqual([{ lat: 1, lng: 2 }, { lat: 3, lng: 4 }]);
    expect(onPathChange).toHaveBeenLastCalledWith([{ lat: 1, lng: 2 }, { lat: 3, lng: 4 }], expect.any(Number));

    d.stop();
    expect(map.handlers.click).toHaveLength(0);
    expect(d.isDrawing).toBe(false);
  });

  it('arrastar um vértice atualiza o caminho; botão direito remove e renumera', () => {
    const d = createRouteDrawing(map);
    d.setPath([{ lat: 0, lng: 0 }, { lat: 0, lng: 1 }, { lat: 1, lng: 1 }]);
    expect(d.pointCount).toBe(3);

    map.markers[1].position = { lat: 5, lng: 5 };
    map.markers[1].fire('dragend');
    expect(d.getPath()[1]).toEqual({ lat: 5, lng: 5 });
    expect(map.polylines[0].path[1]).toEqual({ lat: 5, lng: 5 });

    map.markers[0].fire('rightclick');
    expect(map.markers[0].remove).toHaveBeenCalled();
    expect(d.pointCount).toBe(2);
    expect(map.markers[1].setStyle).toHaveBeenCalledWith({ label: '1' });
    expect(map.markers[2].setStyle).toHaveBeenCalledWith({ label: '2' });
  });

  it('setPath aceita GeoJSON [lng, lat] e strings; distância por haversine; fitBounds e destroy limpam', () => {
    const d = createRouteDrawing(map);
    d.setPath([[-49.2, -16.6], { lat: '-16.7', lng: '-49.3' }, null]);
    expect(d.getPath()).toEqual([{ lat: -16.6, lng: -49.2 }, { lat: -16.7, lng: -49.3 }]);
    const km = d.getDistanceKm();
    expect(km).toBeGreaterThan(15);
    expect(km).toBeLessThan(16);

    d.fitBounds();
    expect(map.fitBounds).toHaveBeenCalledWith(d.getPath(), { padding: 50, maxZoom: 16 });

    d.clear();
    expect(d.pointCount).toBe(0);
    expect(map.polylines[0].path).toEqual([]);

    d.setPath([{ lat: 1, lng: 1 }]);
    d.start();
    d.destroy();
    expect(map.polylines[0].remove).toHaveBeenCalled();
    expect(map.markers.at(-1).remove).toHaveBeenCalled();
    expect(map.handlers.click).toHaveLength(0);
  });

  it('não editável: start é no-op e os vértices não arrastam nem removem', () => {
    const d = createRouteDrawing(map, { editable: false });
    d.start();
    expect(map.handlers.click).toBeUndefined();
    d.setPath([{ lat: 1, lng: 1 }]);
    expect(map.markers[0].opts.draggable).toBe(false);
    expect(map.markers[0].h.rightclick).toBeUndefined();
  });
});

describe('helpers', () => {
  it('normalizePoint e haversineMeters', () => {
    expect(normalizePoint([1, 2])).toEqual({ lat: 2, lng: 1 });
    expect(normalizePoint({ lat: 'x', lng: 1 })).toBeNull();
    expect(normalizePoint(null)).toBeNull();
    // ~111 km por grau de latitude no equador
    expect(haversineMeters({ lat: 0, lng: 0 }, { lat: 1, lng: 0 })).toBeCloseTo(111195, -2);
  });
});
