/**
 * EV-0012b — o que o MapView passou a pedir ao provider Mapbox:
 * bounds, eventos de viewport, ícone por URL, eventos de hover na polyline.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

const created = { maps: [], markers: [] };

vi.mock('mapbox-gl/dist/mapbox-gl.css', () => ({}));
vi.mock('mapbox-gl', () => {
  function Map(opts) {
    const handlers = {};
    Object.assign(this, {
      opts,
      handlers,
      on: vi.fn((event, layerOrCb, maybeCb) => {
        const key = typeof layerOrCb === 'string' ? `${event}:${layerOrCb}` : event;
        (handlers[key] ||= []).push(typeof layerOrCb === 'string' ? maybeCb : layerOrCb);
      }),
      once: vi.fn((event, cb) => { (handlers[event] ||= []).push(cb); }),
      off: vi.fn(),
      setStyle: vi.fn(),
      moveLayer: vi.fn(),
      resize: vi.fn(),
      fitBounds: vi.fn(),
      fire(key, payload) { (handlers[key] || []).forEach((cb) => cb(payload)); },
      addControl: vi.fn(),
      addSource: vi.fn(),
      addLayer: vi.fn(),
      getLayer: vi.fn(() => true),
      getSource: vi.fn(() => ({ setData: vi.fn() })),
      removeLayer: vi.fn(),
      removeSource: vi.fn(),
      setPaintProperty: vi.fn(),
      getCanvas: vi.fn(() => ({ style: {} })),
      getContainer: vi.fn(() => ({ id: 'mapbox' })),
      getBounds: vi.fn(() => ({ getNorthEast: () => ({ lat: 2, lng: 3 }), getSouthWest: () => ({ lat: -2, lng: -3 }) })),
      project: vi.fn(() => ({ x: 1, y: 2 })),
      remove: vi.fn(),
    });
    created.maps.push(this);
  }
  function Marker(opts) {
    Object.assign(this, {
      opts,
      getElement: vi.fn(function () { return this.opts.element; }),
      setLngLat: vi.fn(function () { return this; }),
      addTo: vi.fn(function () { return this; }),
      on: vi.fn(),
      remove: vi.fn(),
      setDraggable: vi.fn(),
    });
    created.markers.push(this);
  }
  function NavigationControl() {}
  function ScaleControl() {}
  return { default: { accessToken: '', Map, Marker, NavigationControl, ScaleControl } };
});

import { MapboxProvider, resolveMapboxStyle, mapboxStyleCandidates, MAPBOX_DEFAULT_STYLE } from '@/providers/maps/MapboxProvider.js';

async function makeMap(config = {}, options = {}) {
  const provider = new MapboxProvider();
  await provider.load({ mapboxToken: 'pk.test', ...config });
  return provider.createMap({ id: 'c' }, { center: { lat: 0, lng: 0 }, zoom: 3, ...options });
}

beforeEach(() => {
  created.maps.length = 0;
  created.markers.length = 0;
  vi.spyOn(console, 'log').mockImplementation(() => {});
});

describe('MapboxMap (EV-0012b)', () => {
  it('getBounds no formato da API, getContainer e getNativeMap', async () => {
    const map = await makeMap();
    expect(map.getBounds()).toEqual({ lat_min: -2, lng_min: -3, lat_max: 2, lng_max: 3 });
    expect(map.getContainer()).toEqual({ id: 'mapbox' });
    expect(map.getNativeMap()).toBe(created.maps[0]);
  });

  it('idle/move ligam-se ao mapa nativo uma vez e avisam todos os listeners', async () => {
    const map = await makeMap();
    const a = vi.fn();
    const b = vi.fn();
    map.on('idle', a);
    map.on('idle', b);
    map.on('move', vi.fn());
    expect(created.maps[0].handlers.idle).toHaveLength(1);
    expect(created.maps[0].handlers.move).toHaveLength(1);

    created.maps[0].fire('idle');
    expect(a).toHaveBeenCalledTimes(1);
    expect(b).toHaveBeenCalledTimes(1);

    map.off('idle', a);
    created.maps[0].fire('idle');
    expect(a).toHaveBeenCalledTimes(1);
    expect(b).toHaveBeenCalledTimes(2);
  });
});

describe('MapboxMarker (EV-0012b)', () => {
  it('iconUrl cria um <img> com o tamanho pedido e o título', async () => {
    const map = await makeMap();
    map.createMarker({ position: { lat: 1, lng: 2 }, iconUrl: '/olt.png', iconSize: 28, title: 'OLT' });
    const el = created.markers[0].opts.element;
    expect(el.tagName).toBe('IMG');
    expect(el.getAttribute('src')).toBe('/olt.png');
    expect(el.style.width).toBe('28px');
    expect(el.title).toBe('OLT');
    expect(el.className).toContain('map-marker-image');
  });

  it('sem iconUrl desenha o círculo do tipo, com label explícito a vencer o do tipo', async () => {
    const map = await makeMap();
    map.createMarker({ position: { lat: 1, lng: 2 }, markerType: 'origin', label: 'X' });
    const el = created.markers[0].opts.element;
    expect(el.tagName).toBe('DIV');
    expect(el.textContent).toBe('X');
    expect(el.style.backgroundColor).toBe('rgb(34, 197, 94)');
  });
});

describe('MapboxPolyline (EV-0012b)', () => {
  it('mouseenter/mousemove/mouseleave na camada de hit viram mouseover/mousemove/mouseout', async () => {
    const map = await makeMap();
    const line = map.createPolyline({ path: [{ lat: 1, lng: 2 }, { lat: 3, lng: 4 }] });
    const over = vi.fn();
    const move = vi.fn();
    const out = vi.fn();
    line.on('mouseover', over);
    line.on('mousemove', move);
    line.on('mouseout', out);

    const native = created.maps[0];
    const ev = { lngLat: { lat: 9, lng: 8 }, originalEvent: { clientX: 1, clientY: 2 } };
    native.fire(`mouseenter:${line.hitLayerId}`, ev);
    native.fire(`mousemove:${line.hitLayerId}`, ev);
    native.fire(`mouseleave:${line.hitLayerId}`, ev);

    expect(over).toHaveBeenCalledWith(expect.objectContaining({ lat: 9, lng: 8, clientX: 1, clientY: 2 }));
    expect(move).toHaveBeenCalledTimes(1);
    expect(out).toHaveBeenCalledTimes(1);
    // realce ao entrar, reposição ao sair
    expect(native.setPaintProperty).toHaveBeenCalledWith(line.layerId, 'line-width', 6);
    expect(native.setPaintProperty).toHaveBeenLastCalledWith(line.layerId, 'line-opacity', 0.9);

    line.remove();
    expect(native.off).toHaveBeenCalledWith('mousemove', line.hitLayerId, expect.any(Function));
  });
});

describe('MapboxProvider — estilo configurado com fallback (EV-0012c)', () => {
  it('resolve aliases e URLs; inválido vira vazio', () => {
    expect(resolveMapboxStyle('dark')).toBe('mapbox://styles/mapbox/dark-v11');
    expect(resolveMapboxStyle(' mapbox://styles/x/y ')).toBe('mapbox://styles/x/y');
    expect(resolveMapboxStyle('https://example.com/style.json')).toBe('https://example.com/style.json');
    expect(resolveMapboxStyle('nao-existe')).toBe('');
    expect(resolveMapboxStyle('')).toBe('');
  });

  it('candidatos: personalizado → configurado → padrão, sem repetir', () => {
    expect(mapboxStyleCandidates({ mapboxCustomStyle: 'mapbox://styles/x/y', mapboxStyle: 'streets' }))
      .toEqual(['mapbox://styles/x/y', MAPBOX_DEFAULT_STYLE]);
    expect(mapboxStyleCandidates({})).toEqual([MAPBOX_DEFAULT_STYLE]);
  });

  it('o mapa nasce com o 1.º candidato e, se falhar antes do load, passa ao seguinte', async () => {
    const map = await makeMap({ mapboxCustomStyle: 'mapbox://styles/x/custom', mapboxStyle: 'light' });
    const native = created.maps[0];
    expect(native.opts.style).toBe('mapbox://styles/x/custom');

    vi.spyOn(console, 'warn').mockImplementation(() => {});
    native.fire('error', { error: new Error('style not found') });
    expect(native.setStyle).toHaveBeenCalledWith('mapbox://styles/mapbox/light-v11');
    expect(map.getStyleUrl()).toBe('mapbox://styles/mapbox/light-v11');

    // depois de carregar, erros de tiles não trocam o estilo
    native.fire('load');
    native.fire('error', { error: new Error('tile') });
    expect(native.setStyle).toHaveBeenCalledTimes(1);
  });

  it('um `style` explícito nas opções vence a configuração', async () => {
    await makeMap({ mapboxStyle: 'dark' }, { style: 'satellite' });
    expect(created.maps[0].opts.style).toBe('mapbox://styles/mapbox/satellite-v9');
  });
});

describe('MapboxMap — cursor, resize, fitBounds, polígono (EV-0012c)', () => {
  it('setCursor escreve no canvas; resize chama o nativo; fitBounds aceita padding e maxZoom', async () => {
    const map = await makeMap();
    const native = created.maps[0];
    const canvas = { style: {} };
    native.getCanvas.mockReturnValue(canvas);
    map.setCursor('crosshair');
    expect(canvas.style.cursor).toBe('crosshair');
    map.setCursor('');
    expect(canvas.style.cursor).toBe('');

    map.resize();
    expect(native.resize).toHaveBeenCalled();

    map.fitBounds([{ lat: 1, lng: 2 }], { padding: 80, maxZoom: 15 });
    expect(native.fitBounds).toHaveBeenCalledWith([[2, 1], [2, 1]], expect.objectContaining({ padding: 80, maxZoom: 15 }));
    map.fitBounds([{ lat: 1, lng: 2 }, { lat: 3, lng: 4 }], 20);
    expect(native.fitBounds).toHaveBeenLastCalledWith([[2, 1], [4, 3]], expect.objectContaining({ padding: 20 }));
  });

  it('createPolygon cria source + fill + line; setPath fecha o anel; remove limpa tudo', async () => {
    const map = await makeMap();
    const native = created.maps[0];
    const setData = vi.fn();
    native.getSource.mockReturnValue({ setData });

    const poly = map.createPolygon({ path: [{ lat: 0, lng: 0 }, { lat: 0, lng: 1 }, { lat: 1, lng: 1 }], strokeColor: '#f59e0b' });
    expect(native.addSource).toHaveBeenCalledWith(poly.sourceId, expect.objectContaining({ type: 'geojson' }));
    expect(native.addLayer).toHaveBeenCalledWith(expect.objectContaining({ id: poly.fillLayerId, type: 'fill' }));
    expect(native.addLayer).toHaveBeenCalledWith(expect.objectContaining({ id: poly.lineLayerId, type: 'line' }));

    poly.setPath([{ lat: 0, lng: 0 }, { lat: 0, lng: 2 }, { lat: 2, lng: 2 }]);
    const ring = setData.mock.calls[0][0].geometry.coordinates[0];
    expect(ring).toHaveLength(4);
    expect(ring[3]).toEqual(ring[0]);

    poly.setStyle({ fillOpacity: 0.3, strokeWeight: 4 });
    expect(native.setPaintProperty).toHaveBeenCalledWith(poly.fillLayerId, 'fill-opacity', 0.3);
    expect(native.setPaintProperty).toHaveBeenCalledWith(poly.lineLayerId, 'line-width', 4);

    poly.remove();
    expect(native.removeLayer).toHaveBeenCalledWith(poly.fillLayerId);
    expect(native.removeLayer).toHaveBeenCalledWith(poly.lineLayerId);
    expect(native.removeSource).toHaveBeenCalledWith(poly.sourceId);
  });

  it('polyline.setStyle muda a pintura e a base do hover; marker.setStyle muda cor/tamanho/label', async () => {
    const map = await makeMap();
    const native = created.maps[0];
    const line = map.createPolyline({ path: [{ lat: 1, lng: 2 }, { lat: 3, lng: 4 }], strokeWeight: 3 });
    line.setStyle({ strokeColor: '#111', strokeWeight: 5, strokeOpacity: 0.5 });
    expect(native.setPaintProperty).toHaveBeenCalledWith(line.layerId, 'line-color', '#111');
    expect(native.setPaintProperty).toHaveBeenCalledWith(line.layerId, 'line-width', 5);
    native.fire(`mouseenter:${line.hitLayerId}`, {});
    expect(native.setPaintProperty).toHaveBeenCalledWith(line.layerId, 'line-width', 7);

    const marker = map.createMarker({ position: { lat: 1, lng: 2 }, color: '#10b981', size: 14 });
    const el = created.markers[0].opts.element;
    expect(el.style.backgroundColor).toBe('rgb(16, 185, 129)');
    expect(el.style.width).toBe('14px');
    marker.setStyle({ color: '#ef4444', size: 20, label: '!' });
    expect(el.style.backgroundColor).toBe('rgb(239, 68, 68)');
    expect(el.style.width).toBe('20px');
    expect(el.textContent).toBe('!');
  });
});
