import { defineStore } from 'pinia';
import { reactive, computed, toRefs } from 'vue';

const STATUS_ALIASES = {
  operational: 'online',
  operational_up: 'online',
  online: 'online',
  critical: 'critical',
  down: 'offline',
  offline: 'offline',
  degraded: 'degraded',
  warning: 'warning',
  maintenance: 'maintenance',
  unknown: 'unknown',
};

function normalizeStatus(value) {
  if (typeof value !== 'string') {
    return value;
  }
  const normalizedKey = value.trim().toLowerCase();
  return STATUS_ALIASES[normalizedKey] ?? value;
}

/**
 * Filters store for managing dashboard and map filters
 * Phase 13 Sprint 1 Day 2: Client-side filtering
 */
export const useFiltersStore = defineStore('filters', () => {
  // Estado reativo unificado
  const state = reactive({
    status: [],
    types: [],
    locations: [],
    searchQuery: ''
  });

  // Computed properties
  const hasActiveFilters = computed(() => {
    return state.status.length > 0 || 
           state.types.length > 0 || 
           state.locations.length > 0 || 
           state.searchQuery.length > 0;
  });

  const activeFilterCount = computed(() => {
    return state.status.length + state.types.length + state.locations.length;
  });

  // Actions
  function setStatusFilter(statusValue, shouldEnable) {
    const normalized = normalizeStatus(statusValue);
    if (!normalized) {
      return;
    }

    const index = state.status.indexOf(normalized);

    if (shouldEnable === true) {
      if (index === -1) {
        state.status.push(normalized);
      }
      return;
    }

    if (shouldEnable === false) {
      if (index > -1) {
        state.status.splice(index, 1);
      }
      return;
    }

    if (index > -1) {
      state.status.splice(index, 1);
    } else {
      state.status.push(normalized);
    }
  }

  function toggleStatus(statusValue) {
    setStatusFilter(statusValue);
  }

  function toggleType(typeValue) {
    const index = state.types.indexOf(typeValue);
    if (index > -1) {
      state.types.splice(index, 1);
    } else {
      state.types.push(typeValue);
    }
  }

  function toggleLocation(locationValue) {
    const index = state.locations.indexOf(locationValue);
    if (index > -1) {
      state.locations.splice(index, 1);
    } else {
      state.locations.push(locationValue);
    }
  }

  function clearStatusFilters() {
    state.status = [];
  }

  function clearTypeFilters() {
    state.types = [];
  }

  function clearLocationFilters() {
    state.locations = [];
  }

  function clearAllFilters() {
    state.status = [];
    state.types = [];
    state.locations = [];
    state.searchQuery = '';
  }

  function setSearchQuery(query) {
    state.searchQuery = query;
  }

  return {
    // State usando toRefs para manter reatividade
    ...toRefs(state),
    
    // Computed
    hasActiveFilters,
    activeFilterCount,
    
    // Actions
    setStatusFilter,
    toggleStatus,
    toggleType,
    toggleLocation,
    clearStatusFilters,
    clearTypeFilters,
    clearLocationFilters,
    clearAllFilters,
    setSearchQuery,
  };
});
