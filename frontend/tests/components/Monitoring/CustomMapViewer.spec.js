/**
 * EV-0012c — CustomMapViewer cria o mapa pela factory e só fala IMap:
 * marcadores por estado, cabos com hover, área de manutenção, tema e resize,
 * sem um único ramo por provider.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { ref, h } from 'vue';
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
    // projeção simples para os testes: 0,001° = 1 px (EV-0126 mede a distância cabo × site)
    latLngToPixel: ({ lat, lng }) => ({ x: Number(lng) * 1000, y: -Number(lat) * 1000 }),
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

const routeFake = { params: { mapId: 'default', category: 'backbone' }, query: {} };
vi.mock('vue-router', async () => {
  const { h } = await vi.importActual('vue');
  return {
    useRoute: () => routeFake,
    // EV-0137: «Editar no Projeto ↗» — o destino fica legível no atributo
    RouterLink: { props: ['to'], setup: (p, { slots, attrs }) => () => h('a', { ...attrs, 'data-to': JSON.stringify(p.to) }, slots.default?.()) },
  };
});

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
    applyDisplayStatus: vi.fn(),
  }),
}));

// Os componentes pesados são `defineAsyncComponent` (lazy, EV-0035): um stub por nome em
// `global.stubs` não os apanha, por isso substitui-se o módulo por um stub com nome e props.
// `__esModule: true` é obrigatório: sem ele o defineAsyncComponent não desembrulha o `default`
// e o proxy do mock do vitest rebenta ao ser inspecionado pelo VTU.
const lazyStub = (name, props = []) => ({
  __esModule: true,
  default: { name, props, emits: ['close'], render: () => h('div', { 'data-stub': name }) },
});
vi.mock('@/components/SiteDetailsModal.vue', () => lazyStub('SiteDetailsModal', ['show', 'site']));
vi.mock('@/components/FiberCableQuickModal.vue', () => lazyStub('FiberCableQuickModal', ['show', 'cable']));
vi.mock('@/components/FiberCableDetailModal.vue', () => lazyStub('FiberCableDetailModal', ['show', 'cable']));
vi.mock('@/components/CableOpticalTooltip.vue', () => lazyStub('CableOpticalTooltip', ['visible', 'position', 'cableData']));
vi.mock('@/views/monitoring/components/MapInventoryPanel.vue', () => lazyStub('MapInventoryPanel'));
vi.mock('@/views/monitoring/components/MaintenanceAreaPanel.vue', () => lazyStub('MaintenanceAreaPanel', ['affectedDevices', 'affectedCables', 'visible']));
vi.mock('@/views/monitoring/components/MaintenanceNotifyModal.vue', () => lazyStub('MaintenanceNotifyModal', ['show']));

import CustomMapViewer from '@/views/monitoring/CustomMapViewer.vue';

// Pré-carrega os módulos lazy: com os timers falsos o I/O do `import()` dinâmico não
// resolve dentro de um `flushPromises`; em cache, o defineAsyncComponent resolve em microtasks.
await Promise.all([
  import('@/components/SiteDetailsModal.vue'),
  import('@/components/FiberCableQuickModal.vue'),
  import('@/components/FiberCableDetailModal.vue'),
  import('@/components/CableOpticalTooltip.vue'),
  import('@/views/monitoring/components/MapInventoryPanel.vue'),
  import('@/views/monitoring/components/MaintenanceAreaPanel.vue'),
  import('@/views/monitoring/components/MaintenanceNotifyModal.vue'),
]);
import { useUiStore } from '@/stores/ui';

const STUBS = { MapLegend: true, MapContextMenu: true };

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
    // offline é âmbar (mesmo tom de «atenção» — paleta do main, EV-0035)
    expect(map.createMarker.mock.calls.map(([o]) => o.color)).toEqual(['#10b981', '#f59e0b']);
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
    expect(map.markers[0].setStyle).toHaveBeenCalledWith({ color: '#f59e0b' });
    expect(map.markers[1].setStyle).toHaveBeenCalledWith({ color: '#10b981' });
    // o cabo herda o pior estado das pontas: um offline → vermelho
    expect(map.polylines[0].setStyle).toHaveBeenCalledWith(expect.objectContaining({ strokeColor: '#ef4444' }));
    wrapper.unmount();
  });

  it('EV-0126: hover no cabo só mostra «nome · km» (segue o rato e some no mouseout); o card abre no clique', async () => {
    dataFake.availableItems.value.cables[0].length_km = 73.13;
    const wrapper = mountViewer();
    await flushPromises();
    const line = fakeFactory.maps[0].polylines[0];
    expect(line.opts.hitWidth).toBe(8);

    // meio do cabo, longe dos dois sites
    line.fire('mouseover', { lat: -16.65, lng: -49.25, clientX: 120, clientY: 80 });
    await flushPromises();
    vi.advanceTimersByTime(1000);
    await flushPromises();
    expect(wrapper.find('[data-testid="cable-hover-label"]').text()).toBe('Cabo 1 · 73,13 km');
    expect(wrapper.findComponent({ name: 'CableOpticalTooltip' }).exists()).toBe(false); // nada de card no hover
    line.fire('mousemove', { lat: -16.66, lng: -49.26, clientX: 150, clientY: 90 });
    await flushPromises();
    expect(wrapper.find('[data-testid="cable-hover-label"]').attributes('style')).toContain('left: 162px');
    line.fire('mouseout');
    await flushPromises();
    expect(wrapper.find('[data-testid="cable-hover-label"]').exists()).toBe(false);

    line.fire('click', { lat: -16.65, lng: -49.25, clientX: 200, clientY: 100 });
    await flushPromises();
    const tooltip = wrapper.findComponent({ name: 'CableOpticalTooltip' });
    expect(tooltip.props('visible')).toBe(true);
    expect(tooltip.props('position')).toEqual({ x: 200, y: 100 });
    expect(tooltip.props('cableData')).toEqual(expect.objectContaining({ id: 'c1' }));
    tooltip.vm.$emit('close');
    await flushPromises();
    expect(wrapper.findComponent({ name: 'CableOpticalTooltip' }).exists()).toBe(false);
    wrapper.unmount();
  });

  it('EV-0126: junto a um site (< 18 px) o cabo cede — sem etiqueta nem card', async () => {
    const wrapper = mountViewer();
    await flushPromises();
    const line = fakeFactory.maps[0].polylines[0];
    // a 10 px do marcador do OLT-01 (-16.6, -49.2)
    line.fire('mouseover', { lat: -16.6, lng: -49.21, clientX: 10, clientY: 10 });
    line.fire('click', { lat: -16.6, lng: -49.21, clientX: 10, clientY: 10 });
    await flushPromises();
    expect(wrapper.find('[data-testid="cable-hover-label"]').exists()).toBe(false);
    expect(wrapper.findComponent({ name: 'CableOpticalTooltip' }).exists()).toBe(false);
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

  it('tema do utilizador re-estiliza os cabos; desmontar destrói o mapa e desliga o tempo real', async () => {
    const wrapper = mountViewer();
    await flushPromises();
    const map = fakeFactory.maps[0];
    const ui = useUiStore();

    // a store nasce em dark nos testes: muda-se para light e verifica-se a re-estilização
    ui.theme = 'light';
    await flushPromises();
    // O fundo do mapa segue o tema pela factory (EV-0045, testado em providers/); aqui só os cabos
    expect(map.setTheme).not.toHaveBeenCalled();
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

  it('EV-0048: HUD conta sites e enlaces do mapa e os cards filtram o desenho', async () => {
    useUiStore().theme = 'light';
    const wrapper = mountViewer();
    await flushPromises();
    const map = fakeFactory.maps[0];
    const hud = wrapper.get('[data-testid="map-kpi-hud"]');
    // POP A tem um equipamento online → site online; o cabo está ok
    expect(hud.get('[data-testid="kpi-sites"]').text()).toMatch(/1\s*online.*0\s*offline/);
    expect(hud.get('[data-testid="kpi-links"]').text()).toMatch(/1\s*\/1 ok/);
    expect(hud.get('[data-testid="kpi-attenuation"]').text()).toContain('sem dados');

    // Só enlaces com problema: o único cabo está ok → sai do mapa
    await hud.get('[data-testid="kpi-links"]').trigger('click');
    await flushPromises();
    expect(map.polylines[0].remove).toHaveBeenCalled();
    expect(map.markers[0].remove).not.toHaveBeenCalled();

    // Clicar de novo limpa o filtro e o cabo volta
    await hud.get('[data-testid="kpi-links"]').trigger('click');
    await flushPromises();
    expect(map.createPolyline).toHaveBeenCalledTimes(2);

    // Só sites offline: o POP A está online → marcadores saem
    await hud.get('[data-testid="kpi-sites"]').trigger('click');
    await flushPromises();
    expect(map.markers[0].remove).toHaveBeenCalled();
    expect(map.markers[1].remove).toHaveBeenCalled();
    wrapper.unmount();
  });

  it('EV-0107: ?site= enquadra e destaca os equipamentos do POP em vez de enquadrar tudo', async () => {
    routeFake.query = { site: '10' };
    try {
      const wrapper = mountViewer();
      await flushPromises();
      const map = fakeFactory.maps[0];
      expect(map.fitBounds).toHaveBeenCalledTimes(1);
      expect(map.fitBounds).toHaveBeenCalledWith(expect.any(Array), { padding: 80, maxZoom: 16 });
      expect(map.fitBounds.mock.calls[0][0]).toHaveLength(2); // os 2 equipamentos com coordenadas do POP 10
      expect(map.markers[0].setStyle).toHaveBeenCalledWith({ size: 24 });
      vi.advanceTimersByTime(6000);
      expect(map.markers[0].setStyle).toHaveBeenLastCalledWith({ size: 14 });
      wrapper.unmount();
    } finally {
      routeFake.query = {};
    }
  });

  it('EV-0107: ?site= de um POP sem equipamentos no mapa avisa e enquadra tudo', async () => {
    routeFake.query = { site: '999' };
    try {
      const wrapper = mountViewer();
      await flushPromises();
      const map = fakeFactory.maps[0];
      expect(map.fitBounds).toHaveBeenCalledWith(expect.any(Array), { padding: 50, maxZoom: 15 });
      expect(wrapper.text()).toContain('O POP pedido não tem equipamentos com coordenadas neste mapa.');
      wrapper.unmount();
    } finally {
      routeFake.query = {};
    }
  });

  it('EV-0116: ?cable= enquadra o cabo e destaca-o; volta ao estilo normal depois', async () => {
    routeFake.query = { cable: String(CABLES[0].id) };
    try {
      const wrapper = mountViewer();
      await flushPromises();
      const map = fakeFactory.maps[0];
      expect(map.fitBounds).toHaveBeenCalledTimes(1);
      expect(map.fitBounds).toHaveBeenCalledWith(expect.any(Array), { padding: 80, maxZoom: 16 });
      expect(map.polylines[0].setStyle).toHaveBeenCalledWith(expect.objectContaining({ strokeWeight: 5, zIndex: 1000 }));
      vi.advanceTimersByTime(6000);
      expect(map.polylines[0].setStyle).toHaveBeenLastCalledWith(expect.objectContaining({ zIndex: 1 }));
      wrapper.unmount();
    } finally {
      routeFake.query = {};
    }
  });

  it('EV-0116: ?cable= de um cabo sem traçado avisa e enquadra tudo', async () => {
    routeFake.query = { cable: '99999' };
    try {
      const wrapper = mountViewer();
      await flushPromises();
      expect(fakeFactory.maps[0].fitBounds).toHaveBeenCalledWith(expect.any(Array), { padding: 50, maxZoom: 15 });
      expect(wrapper.text()).toContain('O cabo pedido não tem traçado neste mapa.');
      wrapper.unmount();
    } finally {
      routeFake.query = {};
    }
  });

  it('EV-0127: «Localizar OTDR» no cartão do cabo abre o formulário; o resultado desenha trecho, pino e cartão; Limpar tira tudo', async () => {
    const wrapper = mountViewer();
    await flushPromises();
    const map = fakeFactory.maps[0];
    map.polylines[0].fire('click', { lat: -16.65, lng: -49.25, clientX: 200, clientY: 100 });
    await flushPromises();
    wrapper.findComponent({ name: 'CableOpticalTooltip' }).vm.$emit('otdr', { id: 'c1', name: 'Cabo 1' });
    await vi.dynamicImportSettled();
    await flushPromises();
    const modal = wrapper.findComponent({ name: 'OtdrLocatorModal' });
    expect(modal.props('cable')).toEqual({ id: 'c1', name: 'Cabo 1' });
    const result = {
      cable_id: 1, cable_name: 'Cabo 1', direction: 'ab', otdr_m: 1000, slack_pct: 0, map_distance_m: 1000,
      path_length_m: 15000, inventory_length_km: null, origin: { id: 1, name: 'A', distance_m: 1000 },
      target: { id: 2, name: 'B', distance_m: 14000 }, point: [-49.21, -16.61],
      segment: [[-49.209, -16.609], [-49.211, -16.611]], tolerance_m: 40,
    };
    modal.vm.$emit('located', result);
    await flushPromises();
    const seg = map.polylines.at(-1);
    expect(seg.opts).toEqual(expect.objectContaining({ strokeColor: '#f59e0b', clickable: false }));
    expect(seg.opts.path).toEqual([{ lat: -16.609, lng: -49.209 }, { lat: -16.611, lng: -49.211 }]);
    expect(map.setCenter).toHaveBeenCalledWith({ lat: -16.61, lng: -49.21 });
    expect(wrapper.find('[data-testid="otdr-pin"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="otdr-card"]').exists()).toBe(true);
    await wrapper.find('[data-testid="otdr-clear"]').trigger('click');
    expect(seg.remove).toHaveBeenCalled();
    expect(wrapper.find('[data-testid="otdr-pin"]').exists()).toBe(false);
    wrapper.unmount();
  }, 15_000); // imports dinâmicos (modal OTDR): na suite completa a 1.ª compilação passa dos 5 s

  it('EV-0137: só leitura — o cartão do cabo não insere CEO; a CEO mostra-se, as emendas abrem em leitura e «Editar no Projeto ↗» leva ao Projeto de Rede focado', async () => {
    const CEO = { id: 4, name: 'CEO-04', cable_id: 1, cable_name: 'Cabo 1', point: [-49.25, -16.65], km: 1.2, mode: 'corte', mode_label: 'Corte / emenda total', slack_m: null, trays: 2, derived: [] };
    global.fetch = vi.fn(async (url) =>
      url === '/api/v1/inventory/ceos/'
        ? { ok: true, status: 200, json: async () => [CEO] }
        : String(url).startsWith('/api/v1/inventory/ceos/4/fusions/')
          ? { ok: true, status: 200, json: async () => ({ ceo: { id: 4, name: 'CEO-04', mode: 'corte', trays: 2, splices_per_tray: 24 }, cables: [], fusions: [] }) }
          : { ok: true, status: 200, json: async () => ({ hosts_status: [] }) },
    );
    const wrapper = mountViewer();
    await flushPromises();
    const map = fakeFactory.maps[0];
    map.polylines[0].fire('click', { lat: -16.66, lng: -49.24, clientX: 200, clientY: 100 });
    await flushPromises();
    await vi.dynamicImportSettled();
    await flushPromises();
    expect(wrapper.find('[data-testid="cable-insert-ceo"]').exists()).toBe(false);
    expect(wrapper.findAll('[data-testid="ceo-pin"]')).toHaveLength(1);
    await wrapper.find('[data-testid="ceo-pin"]').trigger('click');
    const card = wrapper.find('[data-testid="ceo-card-4"]');
    expect(card.text()).toContain('Corte / emenda total');
    expect(card.find('[data-testid="ceo-derive"]').exists()).toBe(false);
    const to = JSON.parse(card.get('[data-testid="edit-in-project"]').attributes('data-to'));
    expect(to).toEqual({ path: '/Network/NetworkDesign/', query: { foco: 'ceo', id: '4', lat: '-16.65', lng: '-49.25', nome: 'CEO-04' } });
    await card.get('[data-testid="ceo-fusions"]').trigger('click');
    await vi.dynamicImportSettled();
    await flushPromises();
    expect(wrapper.findComponent({ name: 'SpliceBoxModal' }).props('readonly')).toBe(true);
    expect(document.body.querySelector('[data-testid="splice-box"]')).not.toBeNull();
    expect(document.body.querySelector('[data-testid="splice-help"]')).toBeNull(); // sem instruções de edição
    wrapper.unmount();
  }, 15_000);

  it('EV-0128: alertas da equipa aparecem ao abrir; fixar grava no servidor; limpar um fixado limpa para todos; barra abre o formulário', async () => {
    const result = (lng, lat) => ({
      cable_id: 1, cable_name: 'Cabo 1', direction: 'ab', otdr_m: 1000, slack_pct: 1.5, map_distance_m: 985.2,
      path_length_m: 15000, inventory_length_km: null, origin: { id: 1, name: 'A', distance_m: 985.2 },
      target: { id: 2, name: 'B', distance_m: 14014.8 }, point: [lng, lat],
      segment: [[lng, lat], [lng + 0.001, lat]], tolerance_m: 40,
    });
    const alerts = [{ id: 5, cable_id: 1, note: '', created_by: 'Ana', created_at: '2026-11-24T19:00:00Z', result: result(-49.3, -16.7) }];
    const calls = [];
    global.fetch = vi.fn(async (url, opts = {}) => {
      calls.push([url, opts.method || 'GET', opts.body]);
      if (url === '/api/v1/inventory/otdr-alerts/' && (opts.method || 'GET') === 'GET')
        return { ok: true, status: 200, json: async () => alerts };
      if (url === '/api/v1/inventory/otdr-alerts/' && opts.method === 'POST')
        return { ok: true, status: 201, json: async () => ({ id: 6, cable_id: 1, note: '', created_by: 'Rui', created_at: '2026-11-24T19:30:00Z', result: result(-49.21, -16.61) }) };
      if (url.endsWith('/clear/')) return { ok: true, status: 200, json: async () => ({ id: 5, cleared_at: '2026-11-24T20:00:00Z' }) };
      if (url.endsWith('/status/')) {
        const st = JSON.parse(opts.body).status;
        return { ok: true, status: 200, json: async () => ({ ...alerts[0], status: st, status_label: st === 'done' ? 'Concluído' : 'Em deslocamento' }) };
      }
      return { ok: true, status: 200, json: async () => ({ hosts_status: [] }) };
    });
    const wrapper = mountViewer();
    await flushPromises();
    const map = fakeFactory.maps[0];
    // o alerta da equipa já está no mapa
    expect(wrapper.findAll('[data-testid="otdr-pin"]')).toHaveLength(1);
    expect(map.polylines.some((p) => p.opts.strokeColor === '#f59e0b')).toBe(true);

    // barra do mapa: formulário sem cabo (escolher)
    await wrapper.find('[data-testid="map-otdr-btn"]').trigger('click');
    await vi.dynamicImportSettled();
    await flushPromises();
    const modal = wrapper.findComponent({ name: 'OtdrLocatorModal' });
    expect(modal.props('cable')).toBeNull();
    expect(modal.props('cables')).toHaveLength(1);

    // nova medição → fixar
    modal.vm.$emit('located', result(-49.21, -16.61));
    await flushPromises();
    await wrapper.find('[data-testid="otdr-pin-alert"]').trigger('click');
    await flushPromises();
    const post = calls.find(([u, m]) => u === '/api/v1/inventory/otdr-alerts/' && m === 'POST');
    expect(JSON.parse(post[2])).toEqual({ cable_id: 1, direction: 'ab', distance_m: 1000, offset_m: 0, slack_pct: 1.5 });
    expect(wrapper.findAll('[data-testid="otdr-pin"]')).toHaveLength(2);
    expect(wrapper.find('[data-testid="otdr-card-pinned"]').text()).toContain('por Rui');

    // abrir o da Ana pelo pino: estado do atendimento (EV-0132) e concluir (sai do mapa para todos)
    await wrapper.findAll('[data-testid="otdr-pin"]')[1].trigger('click');
    await flushPromises();
    expect(wrapper.find('[data-testid="otdr-card-pinned"]').text()).toContain('por Ana');
    expect(wrapper.find('[data-testid="otdr-clear"]').exists()).toBe(false); // num fixado conclui-se
    await wrapper.find('[data-testid="otdr-status-en_route"]').trigger('click');
    await flushPromises();
    expect(wrapper.find('[data-testid="otdr-status-label"]').text()).toBe('Em deslocamento');
    await wrapper.find('[data-testid="otdr-status-done"]').trigger('click');
    await flushPromises();
    const statusCalls = calls.filter(([u, m]) => u === '/api/v1/inventory/otdr-alerts/5/status/' && m === 'POST');
    expect(statusCalls.map(([, , b]) => JSON.parse(b).status)).toEqual(['en_route', 'done']);
    expect(wrapper.findAll('[data-testid="otdr-pin"]')).toHaveLength(1);
    wrapper.unmount();
  }, 15_000); // imports dinâmicos (modal OTDR): na suite completa a 1.ª compilação passa dos 5 s

  it('EV-0130: ajuste fino — na medição pede o locate com offset; num fixado faz PATCH; o trecho redesenha', async () => {
    const result = (lng, lat, offset = 0) => ({
      cable_id: 1, cable_name: 'Cabo 1', direction: 'ab', otdr_m: 1000, slack_pct: 0, map_distance_m: 1000 + offset,
      base_map_distance_m: 1000, offset_m: offset, path_length_m: 15000, inventory_length_km: null,
      origin: { id: 1, name: 'A', distance_m: 1000 + offset }, target: { id: 2, name: 'B', distance_m: 14000 - offset },
      point: [lng, lat], segment: [[lng, lat], [lng + 0.001, lat]], tolerance_m: 40,
      references: { registered: 0, before: null, after: null },
    });
    const calls = [];
    global.fetch = vi.fn(async (url, opts = {}) => {
      calls.push([url, opts.method || 'GET', opts.body]);
      if (url.startsWith('/api/v1/inventory/cables/1/otdr-locate/')) return { ok: true, status: 200, json: async () => result(-49.22, -16.62, 100) };
      if (url === '/api/v1/inventory/otdr-alerts/' && (opts.method || 'GET') === 'GET') return { ok: true, status: 200, json: async () => [] };
      if (url === '/api/v1/inventory/otdr-alerts/' && opts.method === 'POST')
        return { ok: true, status: 201, json: async () => ({ id: 9, cable_id: 1, note: '', created_by: 'Ana', created_at: '2026-11-24T19:00:00Z', result: result(-49.22, -16.62, 100), log: [] }) };
      if (url === '/api/v1/inventory/otdr-alerts/9/' && opts.method === 'PATCH')
        return { ok: true, status: 200, json: async () => ({ id: 9, cable_id: 1, note: '', created_by: 'Ana', created_at: '2026-11-24T19:00:00Z', result: result(-49.3, -16.7, 600), log: [] }) };
      return { ok: true, status: 200, json: async () => ({ hosts_status: [] }) };
    });
    const wrapper = mountViewer();
    await flushPromises();
    const map = fakeFactory.maps[0];
    await wrapper.find('[data-testid="map-otdr-btn"]').trigger('click');
    await vi.dynamicImportSettled();
    await flushPromises();
    wrapper.findComponent({ name: 'OtdrLocatorModal' }).vm.$emit('located', result(-49.21, -16.61));
    await flushPromises();
    const firstLine = map.polylines.at(-1);
    await wrapper.find('[data-testid="otdr-step-100"]').trigger('click');
    await flushPromises();
    const locate = calls.find(([u]) => u.startsWith('/api/v1/inventory/cables/1/otdr-locate/'));
    expect(locate[0]).toContain('offset_m=100');
    expect(firstLine.remove).toHaveBeenCalled(); // trecho redesenhado
    expect(map.polylines.at(-1).opts.path[0]).toEqual({ lat: -16.62, lng: -49.22 });
    // fixar e ajustar o fixado → PATCH
    await wrapper.find('[data-testid="otdr-pin-alert"]').trigger('click');
    await flushPromises();
    await wrapper.find('[data-testid="otdr-step-500"]').trigger('click');
    await flushPromises();
    const patch = calls.find(([u, m]) => u === '/api/v1/inventory/otdr-alerts/9/' && m === 'PATCH');
    expect(JSON.parse(patch[2])).toEqual({ offset_m: 600 });
    expect(wrapper.find('[data-testid="otdr-card-offset"]').text()).toContain('+600 m');
    wrapper.unmount();
  }, 15_000);
});
