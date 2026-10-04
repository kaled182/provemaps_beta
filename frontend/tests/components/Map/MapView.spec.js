/**
 * EV-0012b — MapView cria o mapa pela factory e só fala IMap:
 * nenhum `google.maps`, nenhum `vue3-google-map`.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';

const fakeFactory = { config: { mapProvider: 'osm', mapDefaultLat: '-16.5', mapDefaultLng: '-49.2', mapDefaultZoom: '7' }, maps: [] };

function makeFakeMap(options) {
  const handlers = {};
  const polylines = [];
  const markers = [];
  const map = {
    options,
    handlers,
    polylines,
    markers,
    on: vi.fn((event, cb) => { (handlers[event] ||= []).push(cb); }),
    off: vi.fn(),
    fire(event, payload) { (handlers[event] || []).forEach((cb) => cb(payload)); },
    // viewport que cobre os dados de teste (a poda por bbox tira o que fica fora)
    getBounds: vi.fn(() => ({ lat_min: -20, lng_min: -60, lat_max: 0, lng_max: -40 })),
    createPolyline: vi.fn((opts) => {
      const h = {};
      const p = { opts, h, on: vi.fn((e, cb) => { (h[e] ||= []).push(cb); }), fire(e, pl) { (h[e] || []).forEach((cb) => cb(pl)); }, remove: vi.fn() };
      polylines.push(p);
      return p;
    }),
    createMarker: vi.fn((opts) => {
      const h = {};
      const m = { opts, h, on: vi.fn((e, cb) => { (h[e] ||= []).push(cb); }), fire(e, pl) { (h[e] || []).forEach((cb) => cb(pl)); }, remove: vi.fn() };
      markers.push(m);
      return m;
    }),
    fitBounds: vi.fn(),
    panTo: vi.fn(),
    getZoom: vi.fn(() => 10),
    setZoom: vi.fn(),
    latLngToPixel: vi.fn(() => ({ x: 10, y: 10 })),
    destroy: vi.fn(),
    getNativeMap: vi.fn(() => null),
  };
  fakeFactory.maps.push(map);
  return map;
}

vi.mock('@/providers/maps/MapProviderFactory.js', () => ({
  getMapConfig: vi.fn(async () => fakeFactory.config),
  createMap: vi.fn(async (container, options) => makeFakeMap(options)),
}));

import MapView from '@/components/MapView.vue';
import { useMapStore } from '@/stores/map';
import { useInventoryStore } from '@/stores/inventory';

const SITES = [
  { id: 1, name: 'POP Centro', latitude: '-16.6', longitude: '-49.2', device_count: 2 },
  { id: 2, name: 'Sem coordenadas', latitude: null, longitude: null, device_count: 0 },
];
const FIBERS = [
  { id: 7, name: 'Cabo 7', status: 'up', path: [{ lat: -16.6, lng: -49.2 }, { lat: -16.7, lng: -49.3 }] },
];
const SEGMENTS = [
  { id: 'seg-1', path_geojson: { coordinates: [[-49.1, -16.5], [-49.0, -16.4]] }, status: 'down' },
];

function jsonResponse(body) {
  return Promise.resolve({ ok: true, json: async () => body });
}

function mountView() {
  return mount(MapView, {
    global: { stubs: { RadiusSearchTool: true } },
    attachTo: document.body,
  });
}

beforeEach(() => {
  fakeFactory.maps.length = 0;
  fakeFactory.config = { mapProvider: 'osm', mapDefaultLat: '-16.5', mapDefaultLng: '-49.2', mapDefaultZoom: '7' };
  setActivePinia(createPinia());
  vi.useFakeTimers();
  vi.spyOn(console, 'error').mockImplementation(() => {});
  vi.spyOn(console, 'debug').mockImplementation(() => {});
  global.fetch = vi.fn((url) => {
    if (String(url).startsWith('/api/v1/sites/')) return jsonResponse({ results: SITES });
    if (String(url).startsWith('/api/v1/inventory/fibers/')) return jsonResponse({ fibers: FIBERS });
    if (String(url).startsWith('/api/v1/inventory/segments/')) return jsonResponse({ segments: SEGMENTS });
    return jsonResponse({});
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('MapView (EV-0012b)', () => {
  it('cria o mapa pela factory com o centro/zoom da configuração e sem chave Google', async () => {
    const { createMap } = await import('@/providers/maps/MapProviderFactory.js');
    const wrapper = mountView();
    await flushPromises();

    expect(createMap).toHaveBeenCalledTimes(1);
    const [container, options] = createMap.mock.calls[0];
    expect(container).toBe(wrapper.find('.map-canvas').element);
    expect(options).toEqual(expect.objectContaining({ center: { lat: -16.5, lng: -49.2 }, zoom: 7 }));
    expect(wrapper.find('.missing-key').exists()).toBe(false);
    // Nenhum script do Google é injetado: o provider é quem carrega o SDK, não o componente
    expect(document.querySelectorAll('script[src*="maps.googleapis.com"]')).toHaveLength(0);
    wrapper.unmount();
  });

  it('desenha marcadores dos sites com coordenadas e polylines das fibras e dos segmentos', async () => {
    const wrapper = mountView();
    await flushPromises();
    const map = fakeFactory.maps[0];

    // Só o site com coordenadas vira marcador
    expect(map.createMarker).toHaveBeenCalledTimes(1);
    expect(map.createMarker.mock.calls[0][0]).toEqual(expect.objectContaining({
      position: { lat: -16.6, lng: -49.2 },
      title: 'POP Centro • 2 dispositivos',
    }));

    // Fibras já desenhadas; segmentos por bbox entram depois do debounce do idle
    expect(map.polylines.map((p) => p.opts.path.length)).toContain(2);
    const mapStore = useMapStore();
    vi.advanceTimersByTime(300);
    await flushPromises();
    expect(mapStore.segments.size).toBe(1);
    const colors = map.polylines.filter((p) => !p.remove.mock.calls.length).map((p) => p.opts.strokeColor);
    expect(colors).toContain('#16a34a'); // fibra 'up' → operational
    expect(colors).toContain('#dc2626'); // segmento 'down'
    wrapper.unmount();
  });

  it('idle lê getBounds do IMap, pede o bbox uma vez por viewport e enquadra só uma vez', async () => {
    const wrapper = mountView();
    await flushPromises();
    const map = fakeFactory.maps[0];
    const mapStore = useMapStore();
    // deixa o fetch do viewport inicial correr antes de espiar
    vi.advanceTimersByTime(300);
    await flushPromises();
    const fetchSpy = vi.spyOn(mapStore, 'fetchSegmentsByBbox');

    map.fire('idle');
    map.fire('idle');
    vi.advanceTimersByTime(300);
    await flushPromises();
    // o bbox é igual ao do idle inicial → nenhuma chamada nova
    expect(fetchSpy).not.toHaveBeenCalled();

    map.getBounds.mockReturnValue({ lat_min: 0, lng_min: 0, lat_max: 2, lng_max: 2 });
    map.fire('idle');
    vi.advanceTimersByTime(300);
    await flushPromises();
    expect(fetchSpy).toHaveBeenCalledWith({ lat_min: 0, lng_min: 0, lat_max: 2, lng_max: 2 });

    // fit automático só no primeiro lote de dados
    expect(map.fitBounds).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it('click na polyline abre a janela do cabo via MapPopup; hover mostra o tooltip de sinal', async () => {
    const wrapper = mountView();
    await flushPromises();
    const map = fakeFactory.maps[0];
    const fiberLine = map.polylines.find((p) => p.opts.path.length === 2);

    fiberLine.fire('mouseover', { clientX: 40, clientY: 50 });
    await flushPromises();
    expect(wrapper.find('.signal-tooltip-overlay').attributes('style')).toContain('left: 40px');

    fiberLine.fire('mouseout');
    await flushPromises();
    expect(wrapper.find('.signal-tooltip-overlay').exists()).toBe(false);

    fiberLine.fire('click');
    await flushPromises();
    expect(wrapper.find('.map-popup .fiber-info-window h4').text()).toBe('Cabo 7');
    expect(global.fetch).toHaveBeenCalledWith('/api/v1/inventory/fibers/7/', expect.anything());
    wrapper.unmount();
  });

  it('click no marcador com um só dispositivo abre a janela do dispositivo', async () => {
    const wrapper = mountView();
    await flushPromises();
    const inventory = useInventoryStore();
    vi.spyOn(inventory, 'selectSite').mockResolvedValue({
      mode: 'single',
      site: { id: 1, name: 'POP Centro', latitude: -16.6, longitude: -49.2 },
      device: { id: 42, name: 'OLT-01' },
    });
    global.fetch.mockImplementation(() => jsonResponse({ ports: [], primary_ip: '10.0.0.1' }));

    fakeFactory.maps[0].markers[0].fire('click');
    await flushPromises();
    const popup = wrapper.find('.map-popup');
    expect(popup.exists()).toBe(true);
    expect(popup.text()).toContain('OLT-01');
    expect(popup.text()).toContain('10.0.0.1');
    wrapper.unmount();
  });

  it('mostra o erro do provider em vez de rebentar e destrói o mapa ao desmontar', async () => {
    const { createMap } = await import('@/providers/maps/MapProviderFactory.js');
    createMap.mockRejectedValueOnce(new Error('Mapbox token not configured'));
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.find('.missing-key').text()).toContain('Mapbox token not configured');
    wrapper.unmount();

    const ok = mountView();
    await flushPromises();
    const map = fakeFactory.maps.at(-1);
    ok.unmount();
    expect(map.destroy).toHaveBeenCalled();
    expect(map.off).toHaveBeenCalledWith('idle', expect.any(Function));
  });
});
