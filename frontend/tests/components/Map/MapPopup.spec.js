/**
 * EV-0012b — MapPopup ancora conteúdo Vue numa coordenada via IMap.latLngToPixel
 * e segue o mapa no evento `move`.
 */
import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import MapPopup from '@/components/Map/MapPopup.vue';

function fakeMap(point = { x: 100, y: 200 }) {
  const handlers = {};
  return {
    handlers,
    latLngToPixel: vi.fn(() => point),
    on: vi.fn((event, cb) => { (handlers[event] ||= []).push(cb); }),
    off: vi.fn((event, cb) => { handlers[event] = (handlers[event] || []).filter((h) => h !== cb); }),
    fire(event) { (handlers[event] || []).forEach((cb) => cb({})); },
  };
}

describe('MapPopup', () => {
  it('posiciona o conteúdo no pixel da âncora, acima dela pelo offset', () => {
    const map = fakeMap();
    const wrapper = mount(MapPopup, {
      props: { map, position: { lat: 1, lng: 2 }, offsetY: 10 },
      slots: { default: '<p class="x">olá</p>' },
    });
    expect(map.latLngToPixel).toHaveBeenCalledWith({ lat: 1, lng: 2 });
    const el = wrapper.find('.map-popup');
    expect(el.attributes('style')).toContain('left: 100px');
    expect(el.attributes('style')).toContain('top: 190px');
    expect(wrapper.find('.x').text()).toBe('olá');
  });

  it('reprojeta quando o mapa se move e quando a âncora muda; esconde-se sem projeção', async () => {
    const map = fakeMap();
    const wrapper = mount(MapPopup, { props: { map, position: { lat: 1, lng: 2 } } });
    expect(map.handlers.move).toHaveLength(1);

    map.latLngToPixel.mockReturnValue({ x: 5, y: 50 });
    map.fire('move');
    await nextTick();
    expect(wrapper.find('.map-popup').attributes('style')).toContain('left: 5px');

    map.latLngToPixel.mockReturnValue(null);
    await wrapper.setProps({ position: { lat: 3, lng: 4 } });
    expect(wrapper.find('.map-popup').exists()).toBe(false);
  });

  it('solta o listener ao desmontar', () => {
    const map = fakeMap();
    const wrapper = mount(MapPopup, { props: { map, position: { lat: 1, lng: 2 } } });
    wrapper.unmount();
    expect(map.off).toHaveBeenCalledWith('move', expect.any(Function));
    expect(map.handlers.move).toHaveLength(0);
  });
});
