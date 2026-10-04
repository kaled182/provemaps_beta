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
      off: vi.fn(),
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
      setLngLat: vi.fn(function () { return this; }),
      addTo: vi.fn(function () { return this; }),
      on: vi.fn(),
      remove: vi.fn(),
      setDraggable: vi.fn(),
    });
    created.markers.push(this);
  }
  function NavigationControl() {}
  return { default: { accessToken: '', Map, Marker, NavigationControl } };
});

import { MapboxProvider } from '@/providers/maps/MapboxProvider.js';

async function makeMap() {
  const provider = new MapboxProvider();
  await provider.load({ mapboxToken: 'pk.test' });
  return provider.createMap({ id: 'c' }, { center: { lat: 0, lng: 0 }, zoom: 3 });
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
