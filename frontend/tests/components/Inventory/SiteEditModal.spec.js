/**
 * SiteEditModal — a posição do site escolhe-se no LocationPickerModal (que já
 * cria o mapa pela factory, EV-0012c/EV-0035); o modal só recebe lat/lng.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { h } from 'vue';

const LocationPickerStub = {
  name: 'LocationPickerModal',
  props: ['isOpen', 'lat', 'lng', 'zoom'],
  emits: ['confirm', 'close'],
  render() { return h('div', { 'data-testid': 'picker', 'data-open': this.isOpen }); },
};

import SiteEditModal from '@/components/Inventory/SiteEditModal.vue';

const mountModal = (site) =>
  mount(SiteEditModal, {
    props: { show: true, site },
    global: { stubs: { LocationPickerModal: LocationPickerStub, Teleport: true } },
  });

beforeEach(() => {
  vi.useFakeTimers();
  global.fetch = vi.fn(async () => ({
    ok: true,
    json: async () => ({
      display_name: 'Rua X, Goiânia',
      address: { road: 'Rua X', city: 'Goiânia', state: 'GO', postcode: '74000' },
    }),
  }));
  vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('SiteEditModal — seletor de localização', () => {
  it('abre o picker centrado no site e, ao confirmar, escreve lat/lng no form e geocodifica', async () => {
    const wrapper = mountModal({ id: 1, name: 'POP', lat: -16.6, lng: -49.2 });
    await flushPromises();

    const picker = wrapper.findComponent(LocationPickerStub);
    expect(picker.props('isOpen')).toBe(false);
    expect(picker.props('lat')).toBe(-16.6);
    expect(picker.props('lng')).toBe(-49.2);

    wrapper.vm.showPicker = true;
    await flushPromises();
    expect(picker.props('isOpen')).toBe(true);

    picker.vm.$emit('confirm', { lat: -16.61, lng: -49.21 });
    await flushPromises();
    expect(wrapper.vm.form.lat).toBe(-16.61);
    expect(wrapper.vm.form.lng).toBe(-49.21);
    expect(wrapper.vm.showPicker).toBe(false);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('nominatim.openstreetmap.org/reverse'),
      expect.anything(),
    );
    wrapper.unmount();
  });

  it('sem coordenadas o picker abre no centro por omissão; digitar lat/lng válidos geocodifica com debounce', async () => {
    const wrapper = mountModal(null);
    await flushPromises();
    const picker = wrapper.findComponent(LocationPickerStub);
    expect(picker.props('lat')).toBe(-15.7801);
    expect(picker.props('lng')).toBe(-47.9292);

    wrapper.vm.form.lat = '-10';
    wrapper.vm.form.lng = '-50';
    await flushPromises();
    expect(global.fetch).not.toHaveBeenCalled(); // ainda dentro do debounce
    vi.advanceTimersByTime(800);
    await flushPromises();
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // fora do intervalo válido não geocodifica
    wrapper.vm.form.lat = '95';
    await flushPromises();
    vi.advanceTimersByTime(800);
    await flushPromises();
    expect(global.fetch).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });
});
