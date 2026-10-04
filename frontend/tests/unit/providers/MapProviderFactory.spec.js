/**
 * EV-0012a — a factory honra os três provedores que o backend aceita
 * (`google`, `mapbox`, `osm`). Antes `osm` lançava «not supported» e o
 * NetworkDesign caía num alert().
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('leaflet/dist/leaflet.css', () => ({}));
vi.mock('mapbox-gl/dist/mapbox-gl.css', () => ({}));
vi.mock('mapbox-gl', () => ({ default: { accessToken: '', Map: vi.fn(), Marker: vi.fn(), NavigationControl: vi.fn() } }));
vi.mock('leaflet', () => {
  const chain = () => ({ addTo: vi.fn(function () { return this; }), on: vi.fn(), off: vi.fn(), remove: vi.fn() });
  return {
    default: {
      map: vi.fn(() => ({ on: vi.fn(), off: vi.fn(), remove: vi.fn(), getZoom: vi.fn(() => 6) })),
      tileLayer: vi.fn(() => chain()),
      polyline: vi.fn(() => chain()),
      marker: vi.fn(() => chain()),
      divIcon: vi.fn((o) => o),
      latLngBounds: vi.fn((b) => b),
    },
  };
});

function mockConfig(config) {
  global.fetch = vi.fn(async () => ({ ok: true, json: async () => config }));
}

async function freshFactory() {
  vi.resetModules();
  return import('@/providers/maps/MapProviderFactory.js');
}

beforeEach(() => {
  vi.spyOn(console, 'log').mockImplementation(() => {});
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

describe('MapProviderFactory', () => {
  it('regista os três provedores que `FirstTimeSetup.map_provider` aceita', async () => {
    const factory = await freshFactory();
    expect(factory.listProviders().sort()).toEqual(['google', 'mapbox', 'osm']);
    expect(factory.LeafletProvider).toBeDefined();
  });

  it('com mapProvider "osm" devolve o LeafletProvider carregado, sem precisar de chaves', async () => {
    mockConfig({ mapProvider: 'osm', googleMapsApiKey: '', mapboxToken: '' });
    const factory = await freshFactory();

    const provider = await factory.getMapProvider();
    expect(provider.getName()).toBe('osm');
    expect(provider.isLoaded()).toBe(true);
    expect(await factory.getCurrentProviderName()).toBe('osm');

    const map = await factory.createMap({ id: 'c' }, { center: { lat: 0, lng: 0 }, zoom: 5 });
    expect(map.getNativeMap()).toBeDefined();
    // Só uma leitura de /api/config/ (cache) e o provider é reutilizado.
    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(await factory.getMapProvider()).toBe(provider);
  });

  it('um provedor desconhecido continua a falhar de forma explícita', async () => {
    mockConfig({ mapProvider: 'esri' });
    const factory = await freshFactory();
    await expect(factory.getMapProvider()).rejects.toThrow(/'esri' not supported/);
  });

  it('mapbox sem token falha no load e não fica em cache como carregado', async () => {
    mockConfig({ mapProvider: 'mapbox', mapboxToken: '' });
    const factory = await freshFactory();
    await expect(factory.getMapProvider()).rejects.toThrow(/Mapbox token/);
  });

  it('reloadProvider limpa a config em cache e volta a consultar o backend', async () => {
    mockConfig({ mapProvider: 'osm' });
    const factory = await freshFactory();
    await factory.getMapProvider();
    factory.reloadProvider();
    await factory.getMapProvider();
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });
});
