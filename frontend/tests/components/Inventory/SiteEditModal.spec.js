/**
 * EV-0012c — o mini-mapa do SiteEditModal usa o provider configurado via
 * factory; o marcador arrastável e o clique no mapa escrevem lat/lng no form.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';

const fakeFactory = { maps: [] };
function makeFakeMap(options) {
  const handlers = {};
  const map = {
    options, handlers, markers: [],
    on: vi.fn((e, cb) => { (handlers[e] ||= []).push(cb); }),
    off: vi.fn(),
    fire(e, pl) { (handlers[e] || []).forEach((cb) => cb(pl)); },
    createMarker: vi.fn((opts) => {
      const h = {};
      const m = { opts, h, position: opts.position, on: vi.fn((e, cb) => { (h[e] ||= []).push(cb); }), fire(e, pl) { (h[e] || []).forEach((cb) => cb(pl)); }, setPosition: vi.fn(function (p) { this.position = p; }), getPosition() { return this.position; }, remove: vi.fn() };
      map.markers.push(m);
      return m;
    }),
    panTo: vi.fn(), setZoom: vi.fn(), destroy: vi.fn(),
  };
  fakeFactory.maps.push(map);
  return map;
}
vi.mock('@/providers/maps/MapProviderFactory.js', () => ({
  createMap: vi.fn(async (container, options) => makeFakeMap(options)),
}));

import SiteEditModal from '@/components/Inventory/SiteEditModal.vue';

beforeEach(() => {
  fakeFactory.maps.length = 0;
  global.fetch = vi.fn(async () => ({ ok: true, json: async () => ({ display_name: 'Rua X, Goiânia', address: { road: 'Rua X', city: 'Goiânia', state: 'GO', postcode: '74000' } }) }));
  vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => vi.restoreAllMocks());

describe('SiteEditModal — mini-mapa (EV-0012c)', () => {
  it('abre centrado no site, com marcador arrastável, e o arrasto escreve no form', async () => {
    const { createMap } = await import('@/providers/maps/MapProviderFactory.js');
    const wrapper = mount(SiteEditModal, { props: { show: true, site: { id: 1, name: 'POP', lat: -16.6, lng: -49.2 } }, attachTo: document.body });
    await flushPromises();

    expect(createMap).toHaveBeenCalledTimes(1);
    expect(createMap.mock.calls[0][1]).toEqual(expect.objectContaining({ center: { lat: -16.6, lng: -49.2 }, zoom: 15 }));
    const map = fakeFactory.maps[0];
    expect(map.createMarker).toHaveBeenCalledWith(expect.objectContaining({ position: { lat: -16.6, lng: -49.2 }, draggable: true }));
    expect(map.setZoom).toHaveBeenCalledWith(16);

    const marker = map.markers[0];
    marker.position = { lat: -16.61, lng: -49.21 };
    marker.fire('dragend');
    await flushPromises();
    expect(wrapper.vm.form.lat).toBe(-16.61);
    expect(wrapper.vm.form.lng).toBe(-49.21);
    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('nominatim.openstreetmap.org/reverse'), expect.anything());
    wrapper.unmount();
  });

  it('sem coordenadas abre afastado; clicar no mapa cria o marcador e preenche lat/lng; fechar destrói o mapa', async () => {
    const wrapper = mount(SiteEditModal, { props: { show: true, site: null }, attachTo: document.body });
    await flushPromises();
    const map = fakeFactory.maps[0];
    expect(map.options.zoom).toBe(6);
    expect(map.createMarker).not.toHaveBeenCalled();

    map.fire('click', { lat: -10, lng: -50 });
    await flushPromises();
    expect(map.createMarker).toHaveBeenCalledTimes(1);
    expect(wrapper.vm.form.lat).toBe(-10);
    expect(map.panTo).toHaveBeenCalledWith({ lat: -10, lng: -50 });

    map.fire('click', { lat: -11, lng: -51 });
    expect(map.createMarker).toHaveBeenCalledTimes(1);
    expect(map.markers[0].setPosition).toHaveBeenCalledWith({ lat: -11, lng: -51 });

    await wrapper.setProps({ show: false });
    expect(map.destroy).toHaveBeenCalled();
    expect(map.markers[0].remove).toHaveBeenCalled();
    wrapper.unmount();
  });
});
