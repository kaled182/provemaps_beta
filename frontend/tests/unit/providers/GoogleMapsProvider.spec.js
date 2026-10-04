/**
 * EV-0012b — o que o MapView passou a pedir ao provider Google:
 * bounds, eventos de viewport, ícone por URL, projeção relativa ao container.
 * `google.maps` é um duplo mínimo; o SDK nunca é carregado.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { GoogleMapsProvider } from '@/providers/maps/GoogleMapsProvider.js';

function latLng(lat, lng) {
  return { lat: () => lat, lng: () => lng };
}

function evented() {
  const handlers = {};
  return {
    handlers,
    addListener: vi.fn((event, cb) => {
      (handlers[event] ||= []).push(cb);
      return { event, cb };
    }),
    fire(event, payload) { (handlers[event] || []).forEach((cb) => cb(payload)); },
  };
}

const created = { maps: [], markers: [], polylines: [] };

const fakeGoogle = {
  maps: {
    Map: vi.fn(function (container, opts) {
      Object.assign(this, evented(), {
        container,
        opts,
        getBounds: vi.fn(() => ({ getNorthEast: () => latLng(2, 3), getSouthWest: () => latLng(-2, -3) })),
        getZoom: vi.fn(() => 2),
        getProjection: vi.fn(() => ({ fromLatLngToPoint: (ll) => ({ x: ll.lng() + 10, y: 10 - ll.lat() }) })),
        setCenter: vi.fn(), getCenter: vi.fn(() => latLng(0, 0)), setZoom: vi.fn(), panTo: vi.fn(), fitBounds: vi.fn(),
      });
      created.maps.push(this);
    }),
    Marker: vi.fn(function (opts) {
      Object.assign(this, evented(), { opts, setMap: vi.fn(), setPosition: vi.fn(), setDraggable: vi.fn() });
      created.markers.push(this);
    }),
    Polyline: vi.fn(function (opts) {
      Object.assign(this, evented(), { opts, setMap: vi.fn(), setOptions: vi.fn(), setPath: vi.fn() });
      created.polylines.push(this);
    }),
    LatLng: vi.fn(function (lat, lng) { this.lat = () => lat; this.lng = () => lng; }),
    LatLngBounds: vi.fn(function () { this.extend = vi.fn(); }),
    Size: vi.fn(function (w, h) { this.width = w; this.height = h; }),
    Point: vi.fn(function (x, y) { this.x = x; this.y = y; }),
    event: { clearInstanceListeners: vi.fn(), removeListener: vi.fn() },
  },
};

async function makeMap() {
  globalThis.google = fakeGoogle;
  window.google = fakeGoogle;
  const provider = new GoogleMapsProvider();
  await provider.load({ googleMapsApiKey: 'k' });
  return provider.createMap({ id: 'c' }, { center: { lat: 0, lng: 0 }, zoom: 2 });
}

beforeEach(() => {
  created.maps.length = 0;
  created.markers.length = 0;
  created.polylines.length = 0;
  vi.clearAllMocks();
});

describe('GoogleMapClass (EV-0012b)', () => {
  it('getBounds devolve a bbox no formato da API; getContainer devolve o elemento', async () => {
    const map = await makeMap();
    expect(map.getBounds()).toEqual({ lat_min: -2, lng_min: -3, lat_max: 2, lng_max: 3 });
    expect(map.getContainer()).toEqual({ id: 'c' });
  });

  it('idle e move (bounds_changed) chegam sem rebentar por falta de payload; off remove o handle', async () => {
    const map = await makeMap();
    const onIdle = vi.fn();
    const onMove = vi.fn();
    map.on('idle', onIdle);
    map.on('move', onMove);

    const native = created.maps[0];
    expect(native.handlers.idle).toHaveLength(1);
    expect(native.handlers.bounds_changed).toHaveLength(1);
    native.fire('idle');          // o Google não passa argumento
    native.fire('bounds_changed');
    expect(onIdle).toHaveBeenCalledWith(expect.objectContaining({ lat: undefined }));
    expect(onMove).toHaveBeenCalledTimes(1);

    map.off('idle', onIdle);
    expect(fakeGoogle.maps.event.removeListener).toHaveBeenCalledWith(expect.objectContaining({ event: 'idle' }));
  });

  it('latLngToPixel é relativo ao canto noroeste visível, à escala do zoom', async () => {
    const map = await makeMap();
    // NW = (lat 2, lng -3) → ponto (7, 8); alvo (0, 0) → (10, 10); zoom 2 → escala 4
    expect(map.latLngToPixel({ lat: 0, lng: 0 })).toEqual({ x: 12, y: 8 });
  });

  it('latLngToPixel devolve null antes de haver bounds/projeção', async () => {
    const map = await makeMap();
    created.maps[0].getBounds.mockReturnValueOnce(null);
    expect(map.latLngToPixel({ lat: 0, lng: 0 })).toBeNull();
  });
});

describe('GoogleMarkerClass (EV-0012b)', () => {
  it('iconUrl vira ícone com scaledSize/anchor; sem iconUrl mantém o SVG do tipo', async () => {
    const map = await makeMap();
    map.createMarker({ position: { lat: 1, lng: 2 }, iconUrl: '/olt.png', iconSize: 30, title: 'OLT' });
    const icon = created.markers[0].opts.icon;
    expect(icon.url).toBe('/olt.png');
    expect(icon.scaledSize).toEqual(expect.objectContaining({ width: 30, height: 30 }));
    expect(icon.anchor).toEqual(expect.objectContaining({ x: 15, y: 15 }));
    expect(created.markers[0].opts.title).toBe('OLT');

    map.createMarker({ position: { lat: 1, lng: 2 }, label: 'Z' });
    expect(created.markers[1].opts.icon.url).toContain('data:image/svg+xml');
    expect(decodeURIComponent(created.markers[1].opts.icon.url)).toContain('>Z<');
  });

  it('remove limpa os listeners nativos', async () => {
    const map = await makeMap();
    const marker = map.createMarker({ position: { lat: 1, lng: 2 } });
    marker.remove();
    expect(fakeGoogle.maps.event.clearInstanceListeners).toHaveBeenCalledWith(created.markers[0]);
    expect(created.markers[0].setMap).toHaveBeenCalledWith(null);
  });
});

describe('GooglePolyline (EV-0012b)', () => {
  it('realça no mouseover e repõe no mouseout; eventos chegam com clientX/clientY', async () => {
    const map = await makeMap();
    const line = map.createPolyline({ path: [], strokeWeight: 3, strokeOpacity: 0.8 });
    const over = vi.fn();
    line.on('mouseover', over);

    const native = created.polylines[0];
    native.fire('mouseover', { latLng: latLng(1, 2), domEvent: { clientX: 4, clientY: 5 } });
    expect(native.setOptions).toHaveBeenCalledWith({ strokeWeight: 5, strokeOpacity: 1 });
    expect(over).toHaveBeenCalledWith(expect.objectContaining({ lat: 1, lng: 2, clientX: 4, clientY: 5 }));

    native.fire('mouseout', {});
    expect(native.setOptions).toHaveBeenLastCalledWith({ strokeWeight: 3, strokeOpacity: 0.8 });
  });

  it('clickable: false não liga hover; remove limpa listeners e tira do mapa', async () => {
    const map = await makeMap();
    const line = map.createPolyline({ path: [], clickable: false });
    expect(created.polylines[0].handlers.mouseover).toBeUndefined();
    line.remove();
    expect(fakeGoogle.maps.event.clearInstanceListeners).toHaveBeenCalledWith(created.polylines[0]);
    expect(created.polylines[0].setMap).toHaveBeenCalledWith(null);
  });
});
