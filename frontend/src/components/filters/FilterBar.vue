<script setup>
import { computed } from 'vue';
import { useFiltersStore } from '@/stores/filters';
import { useDashboardStore } from '@/stores/dashboard';
import FilterDropdown from './FilterDropdown.vue';
import SearchInput from '@/components/search/SearchInput.vue';

const filtersStore = useFiltersStore();
const dashboardStore = useDashboardStore();

// Status options baseados nos valores reais do sistema
const statusOptions = [
  { value: 'online', label: '✅ Operational', color: 'green' },
  { value: 'offline', label: '⚫ Offline', color: 'red' },
  { value: 'unknown', label: '🔵 Unknown', color: 'gray' },
];

// Use real types from dashboard data (dynamic based on Zabbix groups)
const typeOptions = computed(() => dashboardStore.availableTypes);

// Use real locations from dashboard data (Phase 13 Sprint 1 Day 2)
const locationOptions = computed(() => dashboardStore.availableLocations);

const showClearButton = computed(() => filtersStore.hasActiveFilters);

function handleStatusToggle(value, checked) {
  filtersStore.setStatusFilter(value, checked);
}

function handleClearAll() {
  filtersStore.clearAllFilters();
}
</script>

<template>
  <div class="filter-bar" role="region" aria-label="Filter controls">
    <!-- Search Input (Phase 13 Sprint 1 Day 3) -->
    <div class="filter-bar__search">
      <SearchInput />
    </div>
    
    <!-- Filters em uma linha compacta -->
    <div class="filter-bar__row">
      <div class="filter-bar__dropdowns" role="group" aria-label="Filter options">
        <FilterDropdown
          label="Status"
          :options="statusOptions"
          :selected="filtersStore.status"
          @toggle="handleStatusToggle"
          @clear="filtersStore.clearStatusFilters"
          aria-label="Filter by device status"
        />
        
        <FilterDropdown
          label="Type"
          :options="typeOptions"
          :selected="filtersStore.types"
          @toggle="filtersStore.toggleType"
          @clear="filtersStore.clearTypeFilters"
          aria-label="Filter by device type"
        />
        
        <FilterDropdown
          label="Location"
          :options="locationOptions"
          :selected="filtersStore.locations"
          @toggle="filtersStore.toggleLocation"
          @clear="filtersStore.clearLocationFilters"
          aria-label="Filter by location"
        />
      </div>

      <div class="filter-bar__actions">
        <span v-if="filtersStore.activeFilterCount > 0" class="filter-count" role="status" aria-live="polite">
          {{ filtersStore.activeFilterCount }}
        </span>
        
        <button
          v-if="showClearButton"
          class="btn btn-sm btn-outline"
          @click="handleClearAll"
          :disabled="!filtersStore.hasActiveFilters"
          aria-label="Clear all filters"
          title="Clear all filters"
        >
          ✕
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: transparent;
  border-radius: 8px;
  margin-bottom: 0;
}

.filter-bar__search {
  width: 100%;
}

.filter-bar__row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
}

.filter-bar__dropdowns {
  display: flex;
  gap: 0.5rem;
  flex: 1;
  align-items: center;
}

.filter-bar__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.filter-count {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  font-weight: 600;
  min-width: 1rem;
  text-align: center;
  background: var(--surface-highlight);
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
}

.btn {
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  line-height: 1;
}

.btn-outline {
  border: 1px solid var(--border-primary);
  background: var(--surface-highlight);
  color: var(--text-primary);
}

.btn-outline:hover {
  background: var(--menu-item-hover);
  border-color: var(--border-secondary);
}

@media (max-width: 768px) {
  .filter-bar__row {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
  }

  .filter-bar__dropdowns {
    flex-wrap: wrap;
  }

  .filter-bar__actions {
    justify-content: space-between;
  }
}
</style>
