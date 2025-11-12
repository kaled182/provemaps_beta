// frontend/tests/unit/dashboardStoreFilters.spec.js
import { setActivePinia, createPinia } from 'pinia';
import { describe, it, expect, beforeEach } from 'vitest';
import { useDashboardStore } from '@/stores/dashboard';
import { useFiltersStore } from '@/stores/filters';

describe('Dashboard Store - Filtered Hosts', () => {
  let dashboardStore;
  let filtersStore;

  beforeEach(() => {
    setActivePinia(createPinia());
    dashboardStore = useDashboardStore();
    filtersStore = useFiltersStore();
    
    // Setup test data
    dashboardStore.hosts.set(1, {
      id: 1,
      name: 'OLT-Central-01',
      status: 'operational',
      type: 'OLT',
      site_id: '1',
      site_name: 'POP Central',
    });
    dashboardStore.hosts.set(2, {
      id: 2,
      name: 'Switch-Norte-01',
      status: 'warning',
      type: 'Switch',
      site_id: '2',
      site_name: 'POP Norte',
    });
    dashboardStore.hosts.set(3, {
      id: 3,
      name: 'OLT-Sul-01',
      status: 'operational',
      type: 'OLT',
      site_id: '3',
      site_name: 'POP Sul',
    });
  });

  it('returns all hosts when no filters active', () => {
    expect(dashboardStore.filteredHosts.length).toBe(3);
  });

  it('filters by status', () => {
    filtersStore.toggleStatus('operational');
    expect(dashboardStore.filteredHosts.length).toBe(2);
    expect(dashboardStore.filteredHosts.every(h => h.status === 'operational')).toBe(true);
  });

  it('filters by type', () => {
    filtersStore.toggleType('OLT');
    expect(dashboardStore.filteredHosts.length).toBe(2);
    expect(dashboardStore.filteredHosts.every(h => h.type === 'OLT')).toBe(true);
  });

  it('filters by location', () => {
    filtersStore.toggleLocation('1');
    expect(dashboardStore.filteredHosts.length).toBe(1);
    expect(dashboardStore.filteredHosts[0].site_id).toBe('1');
  });

  it('combines multiple filters', () => {
    filtersStore.toggleStatus('operational');
    filtersStore.toggleType('OLT');
    expect(dashboardStore.filteredHosts.length).toBe(2);
    expect(dashboardStore.filteredHosts.every(h => 
      h.status === 'operational' && h.type === 'OLT'
    )).toBe(true);
  });

  it('returns empty array when no matches', () => {
    filtersStore.toggleStatus('offline');
    expect(dashboardStore.filteredHosts.length).toBe(0);
  });

  it('filters by search query', () => {
    filtersStore.setSearchQuery('Central');
    expect(dashboardStore.filteredHosts.length).toBe(1);
    expect(dashboardStore.filteredHosts[0].name).toContain('Central');
  });

  it('search query is case insensitive', () => {
    filtersStore.setSearchQuery('central');
    expect(dashboardStore.filteredHosts.length).toBe(1);
  });

  it('extracts available locations', () => {
    const locations = dashboardStore.availableLocations;
    expect(locations.length).toBe(3);
    expect(locations[0]).toHaveProperty('value');
    expect(locations[0]).toHaveProperty('label');
    expect(locations[0]).toHaveProperty('count');
  });

  it('sorts locations alphabetically', () => {
    const locations = dashboardStore.availableLocations;
    const labels = locations.map(l => l.label);
    const sorted = [...labels].sort();
    expect(labels).toEqual(sorted);
  });

  it('counts devices per location', () => {
    // Add another device to POP Central
    dashboardStore.hosts.set(4, {
      id: 4,
      name: 'Router-Central-01',
      status: 'operational',
      type: 'Router',
      site_id: '1',
      site_name: 'POP Central',
    });
    
    const locations = dashboardStore.availableLocations;
    const centralLocation = locations.find(l => l.value === '1');
    expect(centralLocation.count).toBe(2);
  });
});
