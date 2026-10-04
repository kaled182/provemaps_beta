/**
 * EV-0012d — CableMapModal edita o traçado com useRouteDrawing sobre o MapCanvas.
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
    createMarker: vi.fn((opts) => { const m = { opts, position: { ...opts.position }, on: vi.fn(), getPosition() { return this.position; }, setStyle: vi.fn(), remove: vi.fn() }; map.markers.push(m); return m; }),
    fitBounds: vi.fn(), destroy: vi.fn(),
  };
  fake.maps.push(map);
  return map;
}
vi.mock('@/providers/maps/MapProviderFactory.js', () => ({
  getMapConfig: vi.fn(async () => ({})),
  createMap: vi.fn(async () => fakeMap()),
}));
const apiFake = { get: vi.fn(), post: vi.fn() };
vi.mock('@/composables/useApi', () => ({ useApi: () => apiFake }));

import CableMapModal from '@/components/Inventory/Fibers/CableMapModal.vue';

beforeEach(() => {
  fake.maps.length = 0;
  apiFake.get.mockReset();
  apiFake.post.mockReset();
  apiFake.get.mockResolvedValue({ id: 7, path: [[-49.2, -16.6], [-49.3, -16.7]] });
  apiFake.post.mockResolvedValue({});
  vi.spyOn(window, 'alert').mockImplementation(() => {});
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

describe('CableMapModal (EV-0012d)', () => {
  it('ao abrir carrega o traçado atual, desenha os vértices, enquadra e entra em modo desenho', async () => {
    const wrapper = mount(CableMapModal, { props: { show: true, cableId: 7, cableName: 'Cabo 7' }, attachTo: document.body });
    await flushPromises();
    const map = fake.maps[0];
    expect(apiFake.get).toHaveBeenCalledWith('/api/v1/inventory/fiber-cables/7/');
    expect(map.createMarker).toHaveBeenCalledTimes(2);
    expect(map.polylines[0].setPath).toHaveBeenLastCalledWith([{ lat: -16.6, lng: -49.2 }, { lat: -16.7, lng: -49.3 }]);
    expect(map.fitBounds).toHaveBeenCalled();
    expect(map.handlers.click).toHaveLength(1);
    expect(wrapper.text()).toContain('2 pontos');
    wrapper.unmount();
  });

  it('clique acrescenta vértice; salvar envia o caminho desenhado; fechar destrói o desenho', async () => {
    const wrapper = mount(CableMapModal, { props: { show: true, cableId: 7 }, attachTo: document.body });
    await flushPromises();
    const map = fake.maps[0];
    map.fire('click', { lat: -16.8, lng: -49.4 });
    await flushPromises();
    expect(wrapper.text()).toContain('3 pontos');

    await wrapper.findAll('button').find((b) => b.text().includes('Salvar')).trigger('click');
    await flushPromises();
    expect(apiFake.post).toHaveBeenCalledWith('/api/v1/fiber-cables/7/update-path/', {
      path: [{ lat: -16.6, lng: -49.2 }, { lat: -16.7, lng: -49.3 }, { lat: -16.8, lng: -49.4 }],
    });
    expect(wrapper.emitted('saved')[0][0]).toEqual({ cable_id: 7, points: 3 });

    await wrapper.setProps({ show: false });
    await flushPromises();
    expect(map.polylines[0].remove).toHaveBeenCalled();
    expect(map.destroy).toHaveBeenCalled();
    wrapper.unmount();
  });
});
