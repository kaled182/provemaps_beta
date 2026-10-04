/**
 * EV-0012c — CustomMapViewer cria o mapa pela factory e só fala IMap:
 * marcadores por estado, cabos com hover, área de manutenção, tema e resize,
 * sem um único ramo por provider.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { ref } from 'vue';
import { createPinia, setActivePinia } from 'pinia';

const fakeFactory = { config: {}, maps: [] };

function makeFakeMap(options) {
  const handlers = {};
  const map = {
    options,
    handlers,
    polylines: [],
    markers: [],
    polygons: [],
    on: vi.fn((event, cb) => { (handlers[event] ||= []).push(cb); }),
    off: vi.fn((event, cb) => { handlers[event] = (handlers[event] || []).filter((h) => h !== cb); }),
    fire(event, payload) { (handlers[event] || []).forEach((cb) => cb(payload)); },
    createPolyline: vi.fn((opts) => {
      const h = {};
      const p = { opts, h, on: vi.fn((e, cb) => { (h[e] ||= []).push(cb); }), fire(e, pl) { (h[e] || []).forEach((cb) => cb(pl)); }, setStyle: vi.fn(), setPath: vi.fn(), remove: vi.fn() };
      map.polylines.push(p);
      return p;
    }),
    createMarker: vi.fn((opts) => {
      const h = {};
      const m = { opts, h, on: vi.fn((e, cb) => { (h[e] ||= []).push(cb); }), fire(e, pl) { (h[e] || []).forEach((cb) => cb(pl)); }, setStyle: vi.fn(), getPosition: () => opts.position, remove: vi.fn() };
      map.markers.push(m);
      return m;
    }),
    createPolygon: vi.fn((opts) => {
      const g = { opts, setPath: vi.fn(), setStyle: vi.fn(), remove: vi.fn() };
      map.polygons.push(g);
      return g;
    }),
    fitBounds: vi.fn(),
    setCenter: vi.fn(),
    setZoom: vi.fn(),
    setCursor: vi.fn(),
    setTheme: vi.fn(),
    resize: vi.fn(),
    destroy: vi.fn(),
  };
  fakeFactory.maps.push(map);
  return map;
}

vi.mock('@/providers/maps/MapProviderFactory.js', () => ({
  getMapConfig: vi.fn(async () => fakeFactory.config),
  createMap: vi.fn(async (container, options) => makeFakeMap(options)),
}));

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { mapId: 'default', category: 'backbone' } }),
}));

const realtimeFake = { hostsCb: null, cablesCb: null, connect: vi.fn(), disconnect: vi.fn(), error: ref(null), connected: ref(false) };
vi.mock('@/composables/useRealtimeStatus', () => ({
  availabilityToStatus: (avail, fallback) => (avail === 1 || avail === '1' ? 'online' : avail === 2 || avail === '2' ? 'offline' : fallback),
  useRealtimeStatus: () => ({
    onHosts: (cb) => { realtimeFake.hostsCb = cb; },
    onCables: (cb) => { realtimeFake.cablesCb = cb; },
    connect: realtimeFake.connect,
    disconnect: realtimeFake.disconnect,
    error: realtimeFake.error,
    connected: realtimeFake.connected,
  }),
}));

const DEVICES = [
  { id: 1, name: 'OLT-01', site: 10, site_id: 10, site_name: 'POP A', lat: '-16.6', lng: '-49.2', status: 'online' },
  { id: 2, name: 'SW-02', site: 10, site_id: 10, site_name: 'POP A', lat: '-16.7', lng: '-49.3', status: 'offline' },
  { id: 3, name: 'Sem coords', site: 10, site_id: 10, site_name: 'POP A', lat: null, lng: null, status: 'online' },
];
const CABLES = [
  { id: 'c1', name: 'Cabo 1', label: 'Cabo 1', status: 'online', origin_device_id: 1, destination_device_id: 2,
    path_coordinates: [{ lat: '-16.6', lng: '-49.2' }, { lat: '-16.7', lng: '-49.3' }] },
];
const dataFake = { availableItems: null, sitesMap: null };
vi.mock('@/composables/map/useMapData', () => ({
  useMapData: () => ({
    availableItems: dataFake.availableItems,
    sitesMap: dataFake.sitesMap,
    foldersTree: ref([]),
    loadInventoryItems: vi.fn(async () => {}),
  }),
}));

import CustomMapViewer from '@/views/monitoring/CustomMapViewer.vue';
import { useUiStore } from '@/stores/ui';

const STUBS = {
  SiteDetailsModal: true, FiberCableQuickModal: true, FiberCableDetailModal: true, CableOpticalTooltip: true,
  MapLegend: true, MapInventoryPanel: true, MaintenanceAreaPanel: true, MapContextMenu: true, MaintenanceNotifyModal: true,
};

function mountViewer() {
  return mount(CustomMapViewer, { global: { stubs: STUBS }, attachTo: document.body });
}

beforeEach(() => {
  fakeFactory.maps.length = 0;
  fakeFactory.config = {
    mapProvider: 'mapbox', mapDefaultLat: '-16.6', mapDefaultLng: '-49.2', mapDefaultZoom: '9',
    mapType: 'roadmap', enableStreetView: false, enableTraffic: true, enableFullscreen: true,
  };
  dataFake.availableItems = ref({ devices: DEVICES.map((d) => ({ ...d })), cables: CABLES.map((c) => ({ ...c })), cameras: [], racks: [] });
  dataFake.sitesMap = ref(new Map([['10', { id: 10, name: 'POP A' }]]));
  realtimeFake.hostsCb = null;
  realtimeFake.cablesCb = null;
  setActivePinia(createPinia());
  vi.useFakeTimers();
  vi.spyOn(console, 'log').mockImplementation(() => {});
  vi.spyOn(console, 'warn').mockImplementation(() => {});
  vi.spyOn(console, 'error').mockImplementation(() => {});
  global.fetch = vi.fn(async () => ({ ok: true, json: async () => ({ hosts_status: [] }) }));
  global.ResizeObserver = class { observe() {} disconnect() {} };
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('CustomMapViewer (EV-0012c)', () => {
  it('cria o mapa pela factory com centro, tema e controlos da configuração', async () => {
    const { createMap } = await import('@/providers/maps/MapProviderFactory.js');
    const ui = useUiStore();
    ui.theme = 'dark';
    const wrapper = mountViewer();
    await flushPromises();

    expect(createMap).toHaveBeenCalledTimes(1);
    const [container, options] = createMap.mock.calls[0];
    expect(container).toBe(wrapper.find('.map-container').element);
    expect(options).toEqual(expect.objectContaining({
      center: { lat: -16.6, lng: -49.2 },
      zoom: 9,
      mapTypeId: 'roadmap',
      theme: 'dark',
      controls: expect.objectContaining({ streetView: false, traffic: true, fullscreen: true, scale: true }),
    }));
    expect(realtimeFake.connect).toHaveBeenCalled();
    wrapper.unmount();
  });

  it('mapa default seleciona tudo: um marcador por device com coordenadas (cor do estado) e uma polyline por cabo; enquadra uma vez', async () => {
    useUiStore().theme = 'light'; // a store nasce em dark nos testes; os pesos dos cabos dependem do tema
    const wrapper = mountViewer();
    await flushPromises();
    const map = fakeFactory.maps[0];

    expect(map.createMarker).toHaveBeenCalledTimes(2);
    expect(map.createMarker.mock.calls.map(([o]) => o.color)).toEqual(['#10b981', '#6b7280']);
    expect(map.createMarker.mock.calls[0][0]).toEqual(expect.objectContaining({ title: 'OLT-01', size: 14 }));

    expect(map.createPolyline).toHaveBeenCalledTimes(1);
    expect(map.createPolyline.mock.calls[0][0]).toEqual(expect.objectContaining({
      strokeColor: '#10b981', strokeWeight: 3, strokeOpacity: 0.8, clickable: true,
    }));
    expect(map.fitBounds).toHaveBeenCalledTimes(1);
    expect(map.fitBounds).toHaveBeenCalledWith(expect.any(Array), { padding: 50, maxZoom: 15 });
    wrapper.unmount();
  });

  it('estado em tempo real muda a cor do marcador e do cabo via setStyle, sem recriar', async () => {
    const wrapper = mountViewer();
    await flushPromises();
    const map = fakeFactory.maps[0];
    expect(realtimeFake.hostsCb).toBeTypeOf('function');

    realtimeFake.hostsCb([], new Map([['1', 'offline'], ['2', 'online']]));
    await flushPromises();

    expect(map.createMarker).toHaveBeenCalledTimes(2);
    expect(map.markers[0].setStyle).toHaveBeenCalledWith({ color: '#6b7280' });
    expect(map.markers[1].setStyle).toHaveBeenCalledWith({ color: '#10b981' });
    // o cabo herda o pior estado das pontas: um offline → vermelho
    expect(map.polylines[0].setStyle).toHaveBeenCalledWith(expect.objectContaining({ strokeColor: '#ef4444' }));
    wrapper.unmount();
  });

  it('hover no cabo mostra o tooltip na posição do rato após 300 ms; mouseout esconde', async () => {
    const wrapper = mountViewer();
    await flushPromises();
    const line = fakeFactory.maps[0].polylines[0];

    line.fire('mouseover', { clientX: 120, clientY: 80 });
    vi.advanceTimersByTime(300);
    await flushPromises();
    const tooltip = wrapper.findComponent({ name: 'CableOpticalTooltip' });
    expect(tooltip.props('visible')).toBe(true);
    expect(tooltip.props('position')).toEqual({ x: 120, y: 80 });
    expect(tooltip.props('cableData')).toEqual(expect.objectContaining({ id: 'c1' }));

    line.fire('mouseout');
    await flushPromises();
    expect(tooltip.props('visible')).toBe(false);
    wrapper.unmount();
  });

  it('área de manutenção: cursor, linha com 2 vértices, polígono com 3 e afetados calculados; sair limpa', async () => {
    const wrapper = mountViewer();
    await flushPromises();
    const map = fakeFactory.maps[0];
    const ctx = wrapper.findComponent({ name: 'MapContextMenu' });

    ctx.vm.$emit('action', 'maintenance');
    await flushPromises();
    expect(map.setCursor).toHaveBeenCalledWith('crosshair');
    expect(map.handlers.click).toHaveLength(1);

    map.fire('click', { lat: -16.5, lng: -49.4 });
    map.fire('click', { lat: -16.5, lng: -49.1 });
    expect(map.createPolyline).toHaveBeenCalledTimes(2); // 1 cabo + a linha provisória
    expect(map.createPolyline.mock.calls[1][0]).toEqual(expect.objectContaining({ clickable: false, strokeColor: '#f59e0b' }));

    map.fire('click', { lat: -16.8, lng: -49.1 });
    expect(map.polylines[1].remove).toHaveBeenCalled();
    expect(map.createPolygon).toHaveBeenCalledTimes(1);
    map.fire('click', { lat: -16.8, lng: -49.4 });
    expect(map.polygons[0].setPath).toHaveBeenCalled();

    await flushPromises();
    const panel = wrapper.findComponent({ name: 'MaintenanceAreaPanel' });
    expect(panel.props('affectedDevices').map((d) => d.id)).toEqual([1, 2]);
    expect(panel.props('affectedCables').map((c) => c.id)).toEqual(['c1']);

    panel.vm.$emit('close');
    await flushPromises();
    expect(map.polygons[0].remove).toHaveBeenCalled();
    expect(map.setCursor).toHaveBeenLastCalledWith('');
    expect(map.handlers.click).toHaveLength(0);
    wrapper.unmount();
  });

  it('tema do utilizador re-estiliza o mapa e os cabos; desmontar destrói o mapa e desliga o tempo real', async () => {
    const wrapper = mountViewer();
    await flushPromises();
    const map = fakeFactory.maps[0];
    const ui = useUiStore();

    // a store nasce em dark nos testes: muda-se para light e verifica-se a re-estilização
    ui.theme = 'light';
    await flushPromises();
    expect(map.setTheme).toHaveBeenCalledWith('light');
    expect(map.polylines[0].setStyle).toHaveBeenCalledWith(expect.objectContaining({ strokeWeight: 3, strokeOpacity: 0.8 }));

    wrapper.unmount();
    expect(map.destroy).toHaveBeenCalled();
    expect(map.markers.every((m) => m.remove.mock.calls.length === 1)).toBe(true);
    expect(realtimeFake.disconnect).toHaveBeenCalled();
  });

  it('erro do provider vira toast em vez de rebentar', async () => {
    const { createMap } = await import('@/providers/maps/MapProviderFactory.js');
    createMap.mockRejectedValueOnce(new Error('Mapbox token not configured'));
    const wrapper = mountViewer();
    await flushPromises();
    expect(wrapper.find('.map-toast').text()).toContain('Mapbox token not configured');
    wrapper.unmount();
  });
});
