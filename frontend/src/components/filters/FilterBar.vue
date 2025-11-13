<script setup>
import { computed } from 'vue';
import { useFiltersStore } from '@/stores/filters';
import { useDashboardStore } from '@/stores/dashboard';
import FilterDropdown from './FilterDropdown.vue';
import SearchInput from '@/components/search/SearchInput.vue';

const filtersStore = useFiltersStore();
const dashboardStore = useDashboardStore();

const statusOptions = [
  { value: 'operational', label: '✅ Operational', color: 'green' },
  { value: 'warning', label: '⚠️ Atenção', color: 'yellow' },
  { value: 'critical', label: '🔴 Crítico', color: 'red' },
  { value: 'offline', label: '⚫ Offline', color: 'gray' },
  { value: 'unknown', label: '🔵 Unknown', color: 'blue' },
];

const typeOptions = [
  { value: 'OLT', label: 'OLT (GPON)' },
  { value: 'Switch', label: 'Switch' },
  { value: 'Router', label: 'Router' },
  { value: 'Server', label: 'Server' },
  { value: 'Firewall', label: 'Firewall' },
  { value: 'AP', label: 'Access Point' },
];

// Use real locations from dashboard data (Phase 13 Sprint 1 Day 2)
const locationOptions = computed(() => dashboardStore.availableLocations);

const showClearButton = computed(() => filtersStore.hasActiveFilters);

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
    
    <div class="filter-bar__dropdowns" role="group" aria-label="Filter options">
      <FilterDropdown
        label="Status"
        :options="statusOptions"
        :selected="filtersStore.status"
        @toggle="filtersStore.toggleStatus"
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
        {{ filtersStore.activeFilterCount }} filter{{ filtersStore.activeFilterCount > 1 ? 's' : '' }} active
      </span>
      
      <button
        v-if="showClearButton"
        class="btn btn-sm btn-outline"
        @click="handleClearAll"
        :disabled="!filtersStore.hasActiveFilters"
        aria-label="Clear all filters"
      >
        Clear All
      </button>
    </div>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  background: var(--surface-card);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
  margin-bottom: 1rem;
}

.filter-bar__search {
  width: 100%;
  max-width: 400px;
}

.filter-bar__dropdowns {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.filter-bar__actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.filter-count {
  font-size: 0.875rem;
  color: var(--text-tertiary);
  font-weight: 500;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-outline {
  border: 1px solid var(--border-primary);
  background: var(--surface-muted);
  color: var(--text-primary);
}

.btn-outline:hover {
  background: var(--surface-highlight);
  border-color: var(--border-secondary);
}

@media (max-width: 768px) {
  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-bar__search {
    max-width: 100%;
  }

  .filter-bar__dropdowns {
    margin-bottom: 1rem;
  }

  .filter-bar__actions {
    justify-content: space-between;
  }
}
</style>
