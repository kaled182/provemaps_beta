// frontend/tests/unit/filtersStore.spec.js
import { setActivePinia, createPinia } from 'pinia';
import { describe, it, expect, beforeEach } from 'vitest';
import { useFiltersStore } from '@/stores/filters';

describe('Filters Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('initializes with empty filters', () => {
    const store = useFiltersStore();
    expect(store.status).toEqual([]);
    expect(store.types).toEqual([]);
    expect(store.locations).toEqual([]);
    expect(store.searchQuery).toBe('');
  });

  it('toggles status filter with alias support', () => {
    const store = useFiltersStore();
    store.toggleStatus('operational');
    expect(store.status).toContain('online');
    
    store.toggleStatus('operational');
    expect(store.status).not.toContain('online');
  });

  it('calculates active filter count', () => {
    const store = useFiltersStore();
    expect(store.activeFilterCount).toBe(0);
    
    store.toggleStatus('online');
    store.toggleType('OLT');
    expect(store.activeFilterCount).toBe(2);
  });

  it('clears all filters', () => {
    const store = useFiltersStore();
    store.toggleStatus('online');
    store.toggleType('OLT');
    store.setSearchQuery('test');
    
    store.clearAllFilters();
    
    expect(store.status).toEqual([]);
    expect(store.types).toEqual([]);
    expect(store.searchQuery).toBe('');
  });

  it('has hasActiveFilters computed property', () => {
    const store = useFiltersStore();
    expect(store.hasActiveFilters).toBe(false);
    
    store.setSearchQuery('test');
    expect(store.hasActiveFilters).toBe(true);
    
    store.clearAllFilters();
    store.toggleStatus('online');
    expect(store.hasActiveFilters).toBe(true);
  });

  it('sets status explicitly without duplicates', () => {
    const store = useFiltersStore();
    store.setStatusFilter('online', true);
    expect(store.status).toEqual(['online']);

    store.setStatusFilter('online', true);
    expect(store.status).toEqual(['online']);

    store.setStatusFilter('online', false);
    expect(store.status).toEqual([]);
  });
});
