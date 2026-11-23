/**
 * EV-0048 — contas do HUD do mapa e filtros dos cards.
 */
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import {
  computeMapKpis,
  siteStatuses,
  cableHealth,
  deviceMatchesKpiFilter,
  cableMatchesKpiFilter,
  formatAgo,
  KPI_FILTERS,
} from '@/utils/mapKpis';
import MapKpiHud from '@/views/monitoring/components/MapKpiHud.vue';

const DEVICES = [
  { id: 1, site: 'A', status: 'online' },
  { id: 2, site: 'A', status: 'offline' }, // A: online (um responde)
  { id: 3, site: 'B', status: 'offline' },
  { id: 4, site: 'B', status: 'critical' }, // B: offline
  { id: 5, site: 'C', status: 'unknown' }, // C: sem estado
  { id: 6, site: 'D', status: 'offline' }, // D: fora do mapa
];
const CABLES = [
  { id: 'a', status: 'up' },
  { id: 'b', status: 'down' },
  { id: 'c', status: 'degraded' },
  { id: 'd', status: 'weird' },
  { id: 'e', status: 'down' }, // fora do mapa
];

describe('mapKpis', () => {
  it('site em baixo só quando todos os equipamentos com estado estão em baixo', () => {
    const s = siteStatuses(DEVICES);
    expect(Object.fromEntries(s)).toEqual({ A: 'online', B: 'offline', C: 'unknown', D: 'offline' });
  });

  it('conta só o que está no mapa', () => {
    const k = computeMapKpis({
      devices: DEVICES,
      cables: CABLES,
      selectedDeviceIds: [1, 2, 3, 4, 5],
      selectedCableIds: ['a', 'b', 'c', 'd'],
    });
    expect(k.sites).toEqual({ online: 1, offline: 1, unknown: 1, total: 3 });
    expect(k.links).toEqual({ healthy: 1, attention: 1, critical: 1, unknown: 1, total: 4 });
  });

  it('estado de cabo desconhecido não conta como saudável', () => {
    expect(cableHealth(undefined)).toBe('unknown');
    expect(cableHealth('offline')).toBe('critical');
    expect(cableHealth('warning')).toBe('attention');
  });

  it('filtros dos cards', () => {
    const bySite = siteStatuses(DEVICES);
    expect(deviceMatchesKpiFilter(DEVICES[0], null, bySite)).toBe(true);
    expect(deviceMatchesKpiFilter(DEVICES[1], KPI_FILTERS.SITES_OFFLINE, bySite)).toBe(false); // site A online
    expect(deviceMatchesKpiFilter(DEVICES[2], KPI_FILTERS.SITES_OFFLINE, bySite)).toBe(true);
    expect(cableMatchesKpiFilter(CABLES[0], KPI_FILTERS.LINKS_PROBLEM)).toBe(false);
    expect(cableMatchesKpiFilter(CABLES[1], KPI_FILTERS.LINKS_PROBLEM)).toBe(true);
    expect(cableMatchesKpiFilter(CABLES[2], KPI_FILTERS.LINKS_PROBLEM)).toBe(true);
    expect(cableMatchesKpiFilter(CABLES[3], KPI_FILTERS.LINKS_PROBLEM)).toBe(false);
  });

  it('formatAgo', () => {
    const t = new Date(1_000_000);
    expect(formatAgo(null)).toBeNull();
    expect(formatAgo(t, 1_000_000 + 4_000)).toBe('há 4 s');
    expect(formatAgo(t, 1_000_000 + 125_000)).toBe('há 2 min');
    expect(formatAgo(t, 1_000_000 + 7_300_000)).toBe('há 2 h');
  });
});

describe('MapKpiHud', () => {
  const kpis = computeMapKpis({ devices: DEVICES, cables: CABLES });

  it('clicar alterna o filtro do card', async () => {
    const w = mount(MapKpiHud, { props: { kpis, filter: null } });
    await w.get('[data-testid="kpi-links"]').trigger('click');
    expect(w.emitted('update:filter')[0]).toEqual([KPI_FILTERS.LINKS_PROBLEM]);
    await w.setProps({ filter: KPI_FILTERS.LINKS_PROBLEM });
    expect(w.get('[data-testid="kpi-links"]').attributes('aria-pressed')).toBe('true');
    await w.get('[data-testid="kpi-links"]').trigger('click');
    expect(w.emitted('update:filter')[1]).toEqual([null]);
    w.unmount();
  });

  it('pior atenuação diz «sem dados» em vez de inventar um valor', () => {
    const w = mount(MapKpiHud, { props: { kpis } });
    expect(w.get('[data-testid="kpi-attenuation"]').text()).toContain('sem dados');
    expect(w.get('[data-testid="kpi-attenuation"]').text()).not.toMatch(/dB/);
    w.unmount();
  });

  it('telemetria mostra o modo de coleta e a idade do último estado', () => {
    const w = mount(MapKpiHud, {
      props: { kpis, telemetry: 'degraded', lastUpdate: new Date(Date.now() - 10_000) },
    });
    const text = w.get('[data-testid="kpi-telemetry"]').text();
    expect(text).toContain('Polling 60 s');
    expect(text).toMatch(/há 1\d s/);
    w.unmount();
  });

  it('cards sem itens ficam desativados', () => {
    const empty = computeMapKpis({ devices: [], cables: [] });
    const w = mount(MapKpiHud, { props: { kpis: empty } });
    expect(w.get('[data-testid="kpi-sites"]').attributes('disabled')).toBeDefined();
    expect(w.get('[data-testid="kpi-links"]').attributes('disabled')).toBeDefined();
    w.unmount();
  });
});
