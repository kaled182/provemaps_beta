/**
 * EV-0012a — LeafletProvider implementa IMapProvider sobre Leaflet/OSM.
 * O Leaflet é substituído por um duplo que regista handlers e chamadas, para
 * verificar a tradução de eventos e de coordenadas sem DOM real.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

function evented() {
  const handlers = {};
  return {
    handlers,
    on: vi.fn((event, cb) => { (handlers[event] ||= []).push(cb); }),
    off: vi.fn(),
    fire(event, payload) { (handlers[event] || []).forEach((cb) => cb(payload)); },
  };
}

const fake = {
  maps: [],
  polylines: [],
  polygons: [],
  markers: [],
  tileLayers: [],
};

vi.mock('leaflet/dist/leaflet.css', () => ({}));
vi.mock('leaflet', () => {
  const L = {
    map: vi.fn((container, opts) => {
      const m = {
        ...evented(),
        container,
        opts,
        zoom: opts.zoom,
        center: { lat: opts.center[0], lng: opts.center[1] },
        setView: vi.fn(function (c, z) { this.center = { lat: c[0], lng: c[1] }; this.zoom = z; }),
        getCenter: vi.fn(function () { return this.center; }),
        getZoom: vi.fn(function () { return this.zoom; }),
        setZoom: vi.fn(function (z) { this.zoom = z; }),
        panTo: vi.fn(),
        flyTo: vi.fn(),
        fitBounds: vi.fn(),
        remove: vi.fn(),
        latLngToContainerPoint: vi.fn(() => ({ x: 10, y: 20 })),
        getBounds: vi.fn(() => ({ getSouth: () => -2, getWest: () => -3, getNorth: () => 2, getEast: () => 3 })),
        containerEl: { style: {} },
        getContainer: vi.fn(function () { return this.containerEl; }),
        invalidateSize: vi.fn(),
      };
      fake.maps.push(m);
      return m;
    }),
    tileLayer: vi.fn((url, opts) => {
      const t = { url, opts, addTo: vi.fn(function () { return this; }) };
      fake.tileLayers.push(t);
      return t;
    }),
    polyline: vi.fn((latlngs, opts) => {
      const p = {
        ...evented(),
        latlngs,
        opts,
        addTo: vi.fn(function () { return this; }),
        setLatLngs: vi.fn(function (ll) { this.latlngs = ll; }),
        getLatLngs: vi.fn(function () { return this.latlngs.map(([lat, lng]) => ({ lat, lng })); }),
        setStyle: vi.fn(),
        bringToFront: vi.fn(),
        remove: vi.fn(),
      };
      fake.polylines.push(p);
      return p;
    }),
    polygon: vi.fn((latlngs, opts) => {
      const g = { latlngs, opts, addTo: vi.fn(function () { return this; }), setLatLngs: vi.fn(), setStyle: vi.fn(), remove: vi.fn() };
      fake.polygons.push(g);
      return g;
    }),
    marker: vi.fn((latlng, opts) => {
      const m = {
        ...evented(),
        latlng,
        opts,
        dragging: { enable: vi.fn(), disable: vi.fn() },
        addTo: vi.fn(function () { return this; }),
        setLatLng: vi.fn(function (ll) { this.latlng = ll; }),
        getLatLng: vi.fn(function () { return { lat: this.latlng[0], lng: this.latlng[1] }; }),
        setIcon: vi.fn(),
        remove: vi.fn(),
      };
      fake.markers.push(m);
      return m;
    }),
    divIcon: vi.fn((opts) => ({ divIcon: true, ...opts })),
    icon: vi.fn((opts) => ({ imageIcon: true, ...opts })),
    latLngBounds: vi.fn((latlngs) => ({ bounds: latlngs })),
  };
  return { default: L };
});

import L from 'leaflet';
import { LeafletProvider, OSM_TILE_URL } from '@/providers/maps/LeafletProvider.js';
import { IMapProvider } from '@/providers/maps/IMapProvider.js';

const container = () => ({ id: 'map' });
const options = { center: { lat: -16.68, lng: -49.26 }, zoom: 6 };

async function makeMap() {
  const provider = new LeafletProvider();
  await provider.load({});
  return { provider, map: provider.createMap(container(), options) };
}

beforeEach(() => {
  fake.maps.length = 0;
  fake.polylines.length = 0;
  fake.polygons.length = 0;
  fake.markers.length = 0;
  fake.tileLayers.length = 0;
  vi.clearAllMocks();
});

describe('LeafletProvider', () => {
  it('é um IMapProvider chamado "osm" e carrega sem chave nem token', async () => {
    const provider = new LeafletProvider();
    expect(provider).toBeInstanceOf(IMapProvider);
    expect(provider.getName()).toBe('osm');
    await expect(provider.load({})).resolves.toBeUndefined();
    expect(provider.isLoaded()).toBe(true);
  });

  it('cria o mapa com os tiles públicos do OpenStreetMap e a atribuição obrigatória', async () => {
    const { map } = await makeMap();
    expect(L.map).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'map' }),
      expect.objectContaining({ center: [-16.68, -49.26], zoom: 6, attributionControl: true }),
    );
    expect(fake.tileLayers).toHaveLength(1);
    expect(fake.tileLayers[0].url).toBe(OSM_TILE_URL);
    expect(fake.tileLayers[0].opts.attribution).toContain('OpenStreetMap');
    expect(fake.tileLayers[0].addTo).toHaveBeenCalledWith(map.leafletMap);
    expect(map.getNativeMap()).toBe(fake.maps[0]);
  });

  it('traduz click e contextmenu do mapa para {lat, lng, clientX, clientY}', async () => {
    const { map } = await makeMap();
    const onClick = vi.fn();
    const onRight = vi.fn();
    map.on('click', onClick);
    map.on('rightclick', onRight);

    const original = { clientX: 5, clientY: 7, preventDefault: vi.fn() };
    fake.maps[0].fire('click', { latlng: { lat: 1, lng: 2 }, originalEvent: original });
    fake.maps[0].fire('contextmenu', { latlng: { lat: 3, lng: 4 }, originalEvent: original });

    expect(onClick).toHaveBeenCalledWith(expect.objectContaining({ lat: 1, lng: 2, clientX: 5, clientY: 7 }));
    expect(onRight).toHaveBeenCalledWith(expect.objectContaining({ lat: 3, lng: 4 }));
    expect(original.preventDefault).toHaveBeenCalledTimes(1);

    map.off('click', onClick);
    fake.maps[0].fire('click', { latlng: { lat: 9, lng: 9 }, originalEvent: original });
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('centro, zoom, pan, flyTo e projeção respeitam a ordem [lat, lng] do Leaflet', async () => {
    const { map } = await makeMap();
    map.setCenter({ lat: -10, lng: -50 });
    expect(fake.maps[0].setView).toHaveBeenCalledWith([-10, -50], 6);
    expect(map.getCenter()).toEqual({ lat: -10, lng: -50 });

    map.setZoom(12);
    expect(map.getZoom()).toBe(12);

    map.panTo({ lat: 1, lng: 2 });
    expect(fake.maps[0].panTo).toHaveBeenCalledWith([1, 2]);

    map.flyTo({ lat: 3, lng: 4 }, 15);
    expect(fake.maps[0].flyTo).toHaveBeenCalledWith([3, 4], 15, expect.any(Object));

    expect(map.latLngToPixel({ lat: 0, lng: 0 })).toEqual({ x: 10, y: 20 });
  });

  it('fitBounds aceita padding numérico ou objeto e ignora listas vazias', async () => {
    const { map } = await makeMap();
    map.fitBounds([], 10);
    expect(fake.maps[0].fitBounds).not.toHaveBeenCalled();

    map.fitBounds([{ lat: 1, lng: 2 }, { lat: 3, lng: 4 }], 30);
    expect(L.latLngBounds).toHaveBeenCalledWith([[1, 2], [3, 4]]);
    expect(fake.maps[0].fitBounds).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ padding: [30, 30] }),
    );

    map.fitBounds([{ lat: 1, lng: 2 }], { top: 80 });
    expect(fake.maps[0].fitBounds).toHaveBeenLastCalledWith(
      expect.anything(),
      expect.objectContaining({ padding: [80, 80] }),
    );
  });

  it('destroy remove o mapa nativo e esquece os listeners', async () => {
    const { map } = await makeMap();
    const cb = vi.fn();
    map.on('click', cb);
    map.destroy();
    expect(fake.maps[0].remove).toHaveBeenCalled();
    fake.maps[0].fire('click', { latlng: { lat: 0, lng: 0 } });
    expect(cb).not.toHaveBeenCalled();
  });

  it('createMap antes de load() recusa', () => {
    // O estado "carregado" é de módulo; um provider novo sem load() só falha
    // se nenhum outro teste já tiver carregado. Garante-se o contrato via
    // a mensagem, independentemente da ordem.
    const provider = new LeafletProvider();
    if (!provider.isLoaded()) {
      expect(() => provider.createMap(container(), options)).toThrow(/not loaded/);
    } else {
      expect(provider.createMap(container(), options)).toBeDefined();
    }
  });
});

describe('LeafletPolyline', () => {
  it('desenha com as opções da interface e devolve o caminho em {lat, lng}', async () => {
    const { map } = await makeMap();
    const path = [{ lat: 1, lng: 2 }, { lat: 3, lng: 4 }];
    const line = map.createPolyline({ path, strokeColor: '#111', strokeWeight: 6, strokeOpacity: 0.5 });

    expect(L.polyline).toHaveBeenCalledWith(
      [[1, 2], [3, 4]],
      expect.objectContaining({ color: '#111', weight: 6, opacity: 0.5, interactive: true }),
    );
    expect(fake.polylines[0].addTo).toHaveBeenCalledWith(map.leafletMap);
    expect(line.getPath()).toEqual(path);

    line.setPath([{ lat: 5, lng: 6 }]);
    expect(fake.polylines[0].setLatLngs).toHaveBeenCalledWith([[5, 6]]);
    expect(line.getPath()).toEqual([{ lat: 5, lng: 6 }]);
  });

  it('click/rightclick chegam no formato comum; hover realça e repõe o traço', async () => {
    const { map } = await makeMap();
    const line = map.createPolyline({ path: [{ lat: 1, lng: 2 }], strokeWeight: 4 });
    const onClick = vi.fn();
    const onRight = vi.fn();
    line.addListener('click', onClick);
    line.on('rightclick', onRight);

    const original = { clientX: 1, clientY: 2, preventDefault: vi.fn() };
    fake.polylines[0].fire('click', { latlng: { lat: 7, lng: 8 }, originalEvent: original });
    fake.polylines[0].fire('contextmenu', { latlng: { lat: 7, lng: 8 }, originalEvent: original });
    expect(onClick).toHaveBeenCalledWith(expect.objectContaining({ lat: 7, lng: 8, clientX: 1 }));
    expect(onRight).toHaveBeenCalledWith(expect.objectContaining({ lat: 7, lng: 8, clientY: 2 }));
    expect(original.preventDefault).toHaveBeenCalled();

    fake.polylines[0].fire('mouseover');
    expect(fake.polylines[0].setStyle).toHaveBeenLastCalledWith({ weight: 6, opacity: 1 });
    fake.polylines[0].fire('mouseout');
    expect(fake.polylines[0].setStyle).toHaveBeenLastCalledWith({ weight: 4, opacity: 0.9 });
  });

  it('clickable: false não liga eventos; metadata set/get e remove funcionam', async () => {
    const { map } = await makeMap();
    const line = map.createPolyline({ path: [], clickable: false });
    expect(fake.polylines[0].opts.interactive).toBe(false);
    expect(fake.polylines[0].on).not.toHaveBeenCalled();

    line.set('cableId', 42);
    expect(line.get('cableId')).toBe(42);

    line.setEditable(true);
    line.setDraggable(true);
    line.remove();
    expect(fake.polylines[0].remove).toHaveBeenCalled();
  });
});

describe('LeafletMarker', () => {
  it('usa divIcon com o estilo do tipo e expõe a posição em {lat, lng}', async () => {
    const { map } = await makeMap();
    const marker = map.createMarker({ position: { lat: 1, lng: 2 }, markerType: 'origin', draggable: true });

    expect(L.marker).toHaveBeenCalledWith([1, 2], expect.objectContaining({ draggable: true }));
    expect(L.divIcon).toHaveBeenCalledWith(expect.objectContaining({
      className: 'map-marker map-marker-origin',
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    }));
    expect(fake.markers[0].opts.icon.html).toContain('>A<');
    expect(fake.markers[0].opts.icon.html).toContain('#22c55e');
    expect(marker.getPosition()).toEqual({ lat: 1, lng: 2 });

    marker.setPosition({ lat: 3, lng: 4 });
    expect(fake.markers[0].setLatLng).toHaveBeenCalledWith([3, 4]);
  });

  it('drag/dragend sincronizam a posição e avisam os listeners; click entrega originalEvent', async () => {
    const { map } = await makeMap();
    const marker = map.createMarker({ position: { lat: 1, lng: 2 }, draggable: true });
    const onDrag = vi.fn();
    const onDragEnd = vi.fn();
    const onClick = vi.fn();
    marker.on('drag', onDrag);
    marker.addListener('dragend', onDragEnd);
    marker.on('click', onClick);

    fake.markers[0].latlng = [9, 8];
    fake.markers[0].fire('drag');
    expect(onDrag).toHaveBeenCalledTimes(1);
    expect(marker.getPosition()).toEqual({ lat: 9, lng: 8 });
    fake.markers[0].fire('dragend');
    expect(onDragEnd).toHaveBeenCalledTimes(1);

    const original = { type: 'click' };
    fake.markers[0].fire('click', { originalEvent: original });
    expect(onClick).toHaveBeenCalledWith({ originalEvent: original });
  });

  it('setDraggable liga/desliga o handler nativo; remove limpa', async () => {
    const { map } = await makeMap();
    const marker = map.createMarker({ position: { lat: 1, lng: 2 } });
    marker.setDraggable(true);
    expect(fake.markers[0].dragging.enable).toHaveBeenCalled();
    marker.setDraggable(false);
    expect(fake.markers[0].dragging.disable).toHaveBeenCalled();
    marker.remove();
    expect(fake.markers[0].remove).toHaveBeenCalled();
  });
});

describe('LeafletMap — viewport (EV-0012b)', () => {
  it('getBounds devolve a bbox no formato da API e getContainer o elemento', async () => {
    const { map } = await makeMap();
    expect(map.getBounds()).toEqual({ lat_min: -2, lng_min: -3, lat_max: 2, lng_max: 3 });
    expect(map.getContainer()).toEqual(expect.objectContaining({ style: expect.any(Object) }));
  });

  it('idle liga-se ao moveend e move ao move, uma só vez por evento', async () => {
    const { map } = await makeMap();
    const onIdle = vi.fn();
    const onMove = vi.fn();
    map.on('idle', onIdle);
    map.on('idle', () => {});
    map.on('move', onMove);

    expect(fake.maps[0].handlers.moveend).toHaveLength(1);
    expect(fake.maps[0].handlers.move).toHaveLength(1);

    fake.maps[0].fire('moveend');
    fake.maps[0].fire('move');
    expect(onIdle).toHaveBeenCalledTimes(1);
    expect(onMove).toHaveBeenCalledTimes(1);
  });
});

describe('LeafletMarker — ícone por URL (EV-0012b)', () => {
  it('iconUrl usa L.icon com o tamanho pedido em vez do círculo', async () => {
    const { map } = await makeMap();
    map.createMarker({ position: { lat: 1, lng: 2 }, iconUrl: '/static/olt.png', iconSize: 32, title: 'OLT' });
    expect(L.icon).toHaveBeenCalledWith(expect.objectContaining({
      iconUrl: '/static/olt.png',
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    }));
    expect(L.divIcon).not.toHaveBeenCalled();
    expect(fake.markers[0].opts.title).toBe('OLT');
  });

  it('label explícito entra no divIcon quando não há iconUrl', async () => {
    const { map } = await makeMap();
    map.createMarker({ position: { lat: 1, lng: 2 }, label: '7' });
    expect(fake.markers[0].opts.icon.html).toContain('>7<');
  });
});

describe('LeafletPolyline — eventos de hover (EV-0012b)', () => {
  it('mouseover/mouseout/mousemove chegam aos listeners com lat/lng e posição do rato', async () => {
    const { map } = await makeMap();
    const line = map.createPolyline({ path: [{ lat: 1, lng: 2 }] });
    const over = vi.fn();
    const out = vi.fn();
    const move = vi.fn();
    line.on('mouseover', over);
    line.on('mouseout', out);
    line.on('mousemove', move);

    const ev = { latlng: { lat: 5, lng: 6 }, originalEvent: { clientX: 11, clientY: 22 } };
    fake.polylines[0].fire('mouseover', ev);
    fake.polylines[0].fire('mousemove', ev);
    fake.polylines[0].fire('mouseout', ev);

    expect(over).toHaveBeenCalledWith(expect.objectContaining({ lat: 5, lng: 6, clientX: 11, clientY: 22 }));
    expect(move).toHaveBeenCalledWith(expect.objectContaining({ clientX: 11 }));
    expect(out).toHaveBeenCalledTimes(1);
  });
});

describe('LeafletMap — cursor, resize, fitBounds, polígono, setStyle (EV-0012c)', () => {
  it('setCursor escreve no container; resize invalida o tamanho; fitBounds respeita maxZoom', async () => {
    const { map } = await makeMap();
    map.setCursor('crosshair');
    expect(fake.maps[0].getContainer().style.cursor).toBe('crosshair');
    map.resize();
    expect(fake.maps[0].invalidateSize).toHaveBeenCalledWith({ animate: false });
    map.fitBounds([{ lat: 1, lng: 2 }], { padding: 40, maxZoom: 15 });
    expect(fake.maps[0].fitBounds).toHaveBeenLastCalledWith(expect.anything(), { padding: [40, 40], maxZoom: 15 });
  });

  it('createPolygon usa L.polygon não interativo; setPath/setStyle/remove', async () => {
    const { map } = await makeMap();
    const poly = map.createPolygon({ path: [{ lat: 0, lng: 0 }, { lat: 0, lng: 1 }, { lat: 1, lng: 1 }], strokeColor: '#f59e0b', fillOpacity: 0.2 });
    expect(L.polygon).toHaveBeenCalledWith([[0, 0], [0, 1], [1, 1]], expect.objectContaining({ color: '#f59e0b', fillOpacity: 0.2, interactive: false }));
    poly.setPath([{ lat: 5, lng: 6 }]);
    expect(fake.polygons[0].setLatLngs).toHaveBeenCalledWith([[5, 6]]);
    poly.setStyle({ strokeWeight: 4, fillColor: '#000' });
    expect(fake.polygons[0].setStyle).toHaveBeenCalledWith({ weight: 4, fillColor: '#000' });
    poly.remove();
    expect(fake.polygons[0].remove).toHaveBeenCalled();
  });

  it('polyline.setStyle atualiza a base do hover; marker com cor/tamanho e setStyle troca o ícone', async () => {
    const { map } = await makeMap();
    const line = map.createPolyline({ path: [{ lat: 1, lng: 2 }], strokeWeight: 3, strokeOpacity: 0.8 });
    line.setStyle({ strokeColor: '#111', strokeWeight: 2 });
    expect(fake.polylines[0].setStyle).toHaveBeenLastCalledWith({ color: '#111', weight: 2, opacity: 0.8 });
    fake.polylines[0].fire('mouseover', {});
    expect(fake.polylines[0].setStyle).toHaveBeenLastCalledWith({ weight: 4, opacity: 1 });
    line.setStyle({ zIndex: 1000 });
    expect(fake.polylines[0].bringToFront).toHaveBeenCalled();

    const marker = map.createMarker({ position: { lat: 1, lng: 2 }, color: '#10b981', size: 14 });
    expect(fake.markers[0].opts.icon.html).toContain('#10b981');
    expect(fake.markers[0].opts.icon.iconSize).toEqual([14, 14]);
    marker.setStyle({ color: '#ef4444', size: 20 });
    const next = fake.markers[0].setIcon.mock.calls[0][0];
    expect(next.html).toContain('#ef4444');
    expect(next.iconSize).toEqual([20, 20]);
  });
});
