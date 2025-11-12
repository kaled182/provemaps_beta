// frontend/src/stores/filters.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

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
  function toggleStatus(statusValue: string) {
    const index = status.value.indexOf(statusValue);
    if (index > -1) {
      status.value.splice(index, 1);
    } else {
      status.value.push(statusValue);
    }
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
