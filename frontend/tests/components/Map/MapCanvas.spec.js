/**
 * EV-0012d — MapCanvas cria o mapa pela factory, emite `ready` e destrói ao desmontar.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';

const fake = { config: {}, maps: [] };
vi.mock('@/providers/maps/MapProviderFactory.js', () => ({
  getMapConfig: vi.fn(async () => fake.config),
  createMap: vi.fn(async (container, options) => {
    const m = { container, options, destroy: vi.fn(), on: vi.fn(), off: vi.fn() };
    fake.maps.push(m);
    return m;
  }),
}));

import MapCanvas from '@/components/Map/MapCanvas.vue';

beforeEach(() => {
  fake.maps.length = 0;
  fake.config = { mapDefaultLat: '-16.5', mapDefaultLng: '-49.2', mapDefaultZoom: '7' };
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

describe('MapCanvas', () => {
  it('sem props usa centro/zoom da configuração; emite ready com o IMap; destrói ao desmontar', async () => {
    const wrapper = mount(MapCanvas, { attachTo: document.body });
    await flushPromises();
    const map = fake.maps[0];
    expect(map.options).toEqual(expect.objectContaining({ center: { lat: -16.5, lng: -49.2 }, zoom: 7, mapTypeId: 'roadmap' }));
    expect(map.container).toBe(wrapper.find('.map-canvas').element);
    expect(wrapper.emitted('ready')[0][0]).toBe(map);
    expect(wrapper.vm.getMap()).toBe(map);
    wrapper.unmount();
    expect(map.destroy).toHaveBeenCalled();
  });

  it('props vencem a configuração e os controlos passam ao provider; slot recebe o mapa', async () => {
    const wrapper = mount(MapCanvas, {
      props: { center: { lat: 1, lng: 2 }, zoom: 15, controls: { streetView: false } },
      slots: { default: '<p class="overlay">x</p>' },
    });
    await flushPromises();
    expect(fake.maps[0].options).toEqual(expect.objectContaining({ center: { lat: 1, lng: 2 }, zoom: 15, controls: { streetView: false } }));
    expect(wrapper.find('.overlay').exists()).toBe(true);
    wrapper.unmount();
  });

  it('erro do provider mostra a mensagem, emite error e permite tentar de novo', async () => {
    const { createMap } = await import('@/providers/maps/MapProviderFactory.js');
    createMap.mockRejectedValueOnce(new Error('Mapbox token not configured'));
    const wrapper = mount(MapCanvas);
    await flushPromises();
    expect(wrapper.find('.map-canvas-error').text()).toContain('Mapbox token not configured');
    expect(wrapper.emitted('error')).toHaveLength(1);

    await wrapper.find('.map-canvas-error button').trigger('click');
    await flushPromises();
    expect(wrapper.find('.map-canvas-error').exists()).toBe(false);
    expect(wrapper.emitted('ready')).toHaveLength(1);
    wrapper.unmount();
  });
});
