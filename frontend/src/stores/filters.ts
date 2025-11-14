// frontend/src/stores/filters.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

const STATUS_ALIASES: Record<string, string> = {
  operational: 'online',
  operational_up: 'online',
  online: 'online',
  critical: 'offline',
  down: 'offline',
  offline: 'offline',
  degraded: 'degraded',
  warning: 'warning',
  maintenance: 'maintenance',
  unknown: 'unknown',
};

function normalizeStatus(value: string): string {
  const key = value?.trim().toLowerCase();
  return STATUS_ALIASES[key] ?? value;
}

export interface FilterState {
  status: string[];
  types: string[];
  locations: string[];
  searchQuery: string;
}

export const useFiltersStore = defineStore('filters', () => {
  // State
  const status = ref<string[]>([]);
  const types = ref<string[]>([]);
  const locations = ref<string[]>([]);
  const searchQuery = ref<string>('');

  // Getters
  const activeFilterCount = computed(() => {
    return status.value.length + types.value.length + locations.value.length;
  });

  const hasActiveFilters = computed(() => {
    return activeFilterCount.value > 0 || searchQuery.value.length > 0;
  });

  const filterState = computed<FilterState>(() => ({
    status: status.value,
    types: types.value,
    locations: locations.value,
    searchQuery: searchQuery.value,
  }));

  // Actions
  function setStatusFilter(statusValue: string, shouldEnable?: boolean) {
    const normalized = normalizeStatus(statusValue);
    const index = status.value.indexOf(normalized);

    if (shouldEnable === true) {
      if (index === -1) {
        status.value.push(normalized);
      }
      return;
    }

    if (shouldEnable === false) {
      if (index > -1) {
        status.value.splice(index, 1);
      }
      return;
    }

    if (index > -1) {
      status.value.splice(index, 1);
    } else {
      status.value.push(normalized);
    }
  }

  function toggleStatus(statusValue: string) {
    setStatusFilter(statusValue);
  }

  function toggleType(typeValue: string) {
    const index = types.value.indexOf(typeValue);
    if (index > -1) {
      types.value.splice(index, 1);
    } else {
      types.value.push(typeValue);
    }
  }

  function toggleLocation(locationValue: string) {
    const index = locations.value.indexOf(locationValue);
    if (index > -1) {
      locations.value.splice(index, 1);
    } else {
      locations.value.push(locationValue);
    }
  }

  function setSearchQuery(query: string) {
    searchQuery.value = query;
  }

  function clearAllFilters() {
    status.value = [];
    types.value = [];
    locations.value = [];
    searchQuery.value = '';
  }

  function clearStatusFilters() {
    status.value = [];
  }

  function clearTypeFilters() {
    types.value = [];
  }

  function clearLocationFilters() {
    locations.value = [];
  }

  return {
    // State
    status,
    types,
    locations,
    searchQuery,
    // Getters
    activeFilterCount,
    hasActiveFilters,
    filterState,
    // Actions
    setStatusFilter,
    toggleStatus,
    toggleType,
    toggleLocation,
    setSearchQuery,
    clearAllFilters,
    clearStatusFilters,
    clearTypeFilters,
    clearLocationFilters,
  };
});
