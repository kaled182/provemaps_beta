/**
 * EV-0012d — FiberRouteEditor desenha o cabo via IMap, abre MapPopup nos extremos
 * e, em edição, salva o traçado desenhado.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';

const fake = { maps: [] };
function fakeMap() {
  const handlers = {};
  const map = {
    handlers, polylines: [], markers: [],
    on: vi.fn((e, cb) => { (handlers[e] ||= []).push(cb); }),
    off: vi.fn((e, cb) => { handlers[e] = (handlers[e] || []).filter((h) => h !== cb); }),
    fire(e, pl) { (handlers[e] || []).forEach((cb) => cb(pl)); },
    createPolyline: vi.fn((opts) => { const p = { opts, setPath: vi.fn(), remove: vi.fn() }; map.polylines.push(p); return p; }),
    createMarker: vi.fn((opts) => {
      const h = {};
      const m = { opts, position: { ...opts.position }, h, on: vi.fn((e, cb) => { (h[e] ||= []).push(cb); }), fire(e, pl) { (h[e] || []).forEach((cb) => cb(pl)); }, getPosition() { return this.position; }, setStyle: vi.fn(), remove: vi.fn() };
      map.markers.push(m);
      return m;
    }),
    fitBounds: vi.fn(), latLngToPixel: vi.fn(() => ({ x: 10, y: 10 })), destroy: vi.fn(),
  };
  fake.maps.push(map);
  return map;
}
vi.mock('@/providers/maps/MapProviderFactory.js', () => ({
  getMapConfig: vi.fn(async () => ({})),
  createMap: vi.fn(async () => fakeMap()),
}));
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { id: '7' } }) }));
const apiFake = { get: vi.fn(), post: vi.fn(), patch: vi.fn() };
vi.mock('@/composables/useApi', () => ({ useApi: () => apiFake }));

import FiberRouteEditor from '@/features/networkDesign/FiberRouteEditor.vue';

const CABLE = { id: 7, name: 'Cabo 7', calculated_length_km: 15.4, path: [[-49.2, -16.6], [-49.3, -16.7]] };

beforeEach(() => {
  fake.maps.length = 0;
  apiFake.get.mockReset().mockResolvedValue({ ...CABLE });
  apiFake.patch.mockReset().mockResolvedValue({ ...CABLE });
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

function mountEditor() {
  return mount(FiberRouteEditor, { global: { stubs: { EditorSidebar: true } }, attachTo: document.body });
}

describe('FiberRouteEditor (EV-0012d)', () => {
  it('desenha a polyline do cabo com marcadores de origem/destino, enquadra e abre popup no clique', async () => {
    const wrapper = mountEditor();
    await flushPromises();
    const map = fake.maps[0];
    expect(map.createPolyline).toHaveBeenCalledWith(expect.objectContaining({ path: [{ lat: -16.6, lng: -49.2 }, { lat: -16.7, lng: -49.3 }], clickable: false }));
    expect(map.createMarker.mock.calls.map(([o]) => o.markerType)).toEqual(['origin', 'destination']);
    expect(map.fitBounds).toHaveBeenCalledWith(expect.any(Array), { padding: 50, maxZoom: 16 });

    map.markers[1].fire('click');
    await flushPromises();
    const popup = wrapper.find('.map-popup');
    expect(popup.exists()).toBe(true);
    expect(popup.text()).toContain('Fim do Traçado');
    expect(popup.text()).toContain('15.40 km');
    wrapper.unmount();
  });

  it('«Editar Traçado» troca a polyline por vértices arrastáveis; salvar envia o caminho em GeoJSON e volta a ler', async () => {
    const wrapper = mountEditor();
    await flushPromises();
    const map = fake.maps[0];

    await wrapper.findAll('button').find((b) => b.text().includes('Editar Traçado')).trigger('click');
    await flushPromises();
    expect(map.polylines[0].remove).toHaveBeenCalled();           // polyline de leitura sai
    expect(map.markers.slice(2).map((m) => m.opts.draggable)).toEqual([true, true]);
    expect(map.handlers.click).toHaveLength(1);
    expect(wrapper.text()).toContain('2 vértices');

    map.fire('click', { lat: -16.8, lng: -49.4 });
    await flushPromises();
    expect(wrapper.text()).toContain('3 vértices');

    await wrapper.vm.saveCable({ name: 'Cabo 7' });
    await flushPromises();
    expect(apiFake.patch).toHaveBeenCalledWith('/api/v1/inventory/fiber-cables/7/', {
      name: 'Cabo 7',
      path: [[-49.2, -16.6], [-49.3, -16.7], [-49.4, -16.8]],
    });
    // de volta à leitura: vértices removidos, polyline redesenhada
    expect(map.handlers.click).toHaveLength(0);
    expect(map.createPolyline).toHaveBeenCalledTimes(3); // leitura, desenho, leitura
    wrapper.unmount();
  });
});
