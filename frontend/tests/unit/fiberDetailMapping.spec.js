import { describe, it, expect } from 'vitest';
import { mapFiberDetailToForm, findSiteIdByName, normalizeStatus } from '../../src/components/Inventory/Fiber/mapFiberDetail';

describe('findSiteIdByName', () => {
  const sites = [
    { id: 1, name: 'Furacão' },
    { id: 2, name: 'Vila Mandi' },
  ];
  it('retorna id pelo nome, ignorando case', () => {
    expect(findSiteIdByName(sites, 'furacão')).toBe(1);
    expect(findSiteIdByName(sites, 'VILA MANDI')).toBe(2);
  });
  it('retorna vazio quando não encontra', () => {
    expect(findSiteIdByName(sites, 'Outro')).toBe('');
  });
});

describe('normalizeStatus', () => {
  it('mapeia up para active', () => {
    expect(normalizeStatus('up')).toBe('active');
    expect(normalizeStatus('Ativo')).toBe('active');
  });
  it('mapeia cut/dark planned', () => {
    expect(normalizeStatus('cut')).toBe('cut');
    expect(normalizeStatus('dark')).toBe('dark');
    expect(normalizeStatus('planned')).toBe('planned');
  });
  it('fallback planned', () => {
    expect(normalizeStatus('whatever')).toBe('planned');
  });
});

describe('mapFiberDetailToForm', () => {
  const sites = [
    { id: 'a1', name: 'Furacão' },
    { id: 'b2', name: 'Vila Mandi' },
  ];

  const cable = {
    id: 4,
    name: 'FRC-VMD',
    origin_site_name: 'Furacão',
    destination_site_name: 'Vila Mandi',
    length_km: '51.96',
    status: 'up',
    fiber_count: 12,
  };

  const detail = {
    status: 'up',
    length_km: '51.96',
    origin: { site: 'Furacão', device_id: 10, port_id: 79 },
    destination: { site: 'Vila Mandi', device_id: 20, port_id: 113 },
  };

  it('preenche campos com detail completo', () => {
    const mapped = mapFiberDetailToForm({
      cable,
      detail,
      sites,
    });
    expect(mapped.site_a).toBe('a1');
    expect(mapped.site_b).toBe('b2');
    expect(mapped.device_a).toBe(10);
    expect(mapped.device_b).toBe(20);
    expect(mapped.port_a).toBe(79);
    expect(mapped.port_b).toBe(113);
    expect(mapped.length).toBeCloseTo(51960);
    expect(mapped.status).toBe('active');
    expect(mapped.fiber_count).toBe(12);
  });

  it('usa info da porta quando não há device_id no detail', () => {
    const detailNoDev = {
      status: 'planned',
      length_km: '51.96',
      origin: { site: 'Furacão', port_id: 79 },
      destination: { site: 'Vila Mandi', port_id: 113 },
    };
    const originPortInfo = { device_id: 10, site_name: 'Furacão' };
    const destPortInfo = { device_id: 20, site_name: 'Vila Mandi' };
    const mapped = mapFiberDetailToForm({
      cable,
      detail: detailNoDev,
      sites,
      originPortInfo,
      destPortInfo,
    });
    expect(mapped.device_a).toBe(10);
    expect(mapped.device_b).toBe(20);
    expect(mapped.status).toBe('planned');
  });
});
