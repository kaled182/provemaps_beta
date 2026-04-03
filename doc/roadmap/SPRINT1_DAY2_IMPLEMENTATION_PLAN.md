# Sprint 1 - Day 2: Filter Logic + State Management

**Date:** November 12, 2025  
**Sprint:** Phase 13 Sprint 1 (Filters & Search)  
**Goal:** Connect filters to device list, implement filtering logic  
**Estimated Time:** 8 hours

---

## 🎯 Day 2 Objectives

### Primary Goals
1. ✅ Implement `filteredHosts` computed property in dashboard store
2. ✅ Connect filters to actually filter the device list
3. ✅ Add dynamic location options from dashboard data
4. ✅ Show "X of Y devices" indicator
5. ✅ Performance testing with 100+ devices

### Success Criteria
- ✅ Filters actually filter the device list (not just UI)
- ✅ Location dropdown shows real locations from data
- ✅ Filter count shows "Showing X of Y devices"
- ✅ Filters apply in <50ms (client-side only)
- ✅ All existing + new tests passing

---

## 📝 Implementation Steps

### Step 1: Add filteredHosts to Dashboard Store (1.5 hours)

**File:** `frontend/src/stores/dashboard.js`

Add a computed property that applies all active filters:

```javascript
import { useFiltersStore } from './filters';

// Inside defineStore callback, after existing computed properties:

const filteredHosts = computed(() => {
  const filtersStore = useFiltersStore();
  const { status, types, locations, searchQuery } = filtersStore;
  
  // Start with all hosts
  let filtered = Array.from(hosts.value.values());
  
  // Apply status filter
  if (status.length > 0) {
    filtered = filtered.filter(host => status.includes(host.status));
  }
  
  // Apply type filter
  if (types.length > 0) {
    filtered = filtered.filter(host => types.includes(host.type || host.device_type));
  }
  
  // Apply location filter
  if (locations.length > 0) {
    filtered = filtered.filter(host => {
      const locationId = String(host.site_id || host.location_id);
      return locations.includes(locationId);
    });
  }
  
  // Apply search query (simple contains for now, fuzzy in Day 3)
  if (searchQuery.length > 0) {
    const query = searchQuery.toLowerCase();
    filtered = filtered.filter(host => {
      const name = (host.name || '').toLowerCase();
      const ip = (host.ip || '').toLowerCase();
      const description = (host.description || '').toLowerCase();
      return name.includes(query) || ip.includes(query) || description.includes(query);
    });
  }
  
  return filtered;
});

// Add to return statement
return {
  // ... existing
  filteredHosts,
};
```

### Step 2: Extract Unique Locations from Data (1 hour)

**File:** `frontend/src/stores/dashboard.js`

Add computed property for unique locations:

```javascript
const availableLocations = computed(() => {
  const locationMap = new Map();
  
  Array.from(hosts.value.values()).forEach(host => {
    const locationId = String(host.site_id || host.location_id);
    const locationName = host.site_name || host.location_name || `Site ${locationId}`;
    
    if (locationId && !locationMap.has(locationId)) {
      locationMap.set(locationId, {
        value: locationId,
        label: locationName,
        count: 0,
      });
    }
    
    if (locationId) {
      const loc = locationMap.get(locationId);
      loc.count += 1;
    }
  });
  
  return Array.from(locationMap.values())
    .sort((a, b) => a.label.localeCompare(b.label));
});

// Add to return
return {
  // ... existing
  availableLocations,
};
```

### Step 3: Update FilterBar to Use Dynamic Locations (30 min)

**File:** `frontend/src/components/filters/FilterBar.vue`

Replace hardcoded locations:

```vue
<script setup>
import { computed } from 'vue';
import { useFiltersStore } from '@/stores/filters';
import { useDashboardStore } from '@/stores/dashboard';
import FilterDropdown from './FilterDropdown.vue';

const filtersStore = useFiltersStore();
const dashboardStore = useDashboardStore();

// ... existing statusOptions, typeOptions

// Use real locations from dashboard
const locationOptions = computed(() => dashboardStore.availableLocations);
</script>
```

### Step 4: Update DashboardView to Show Filtered List (1 hour)

**File:** `frontend/src/components/Dashboard/DashboardView.vue`

Change `dashboard.hostsList` to `dashboard.filteredHosts`:

```vue
<template>
  <!-- ... existing code ... -->
  
  <!-- Host cards list -->
  <div class="host-cards-container">
    <div class="section-header">
      <h2>Hosts</h2>
      <!-- Show filter count -->
      <span class="host-count">
        {{ dashboard.filteredHosts.length }}
        <span v-if="filtersStore.hasActiveFilters" class="filter-indicator">
          of {{ dashboard.totalHosts }}
        </span>
      </span>
    </div>
    
    <!-- ... existing loading/error states ... -->
    
    <!-- Virtualized list for performance -->
    <VirtualList
      v-else-if="dashboard.filteredHosts.length > 20"
      :items="dashboard.filteredHosts"
      :item-height="92"
      :container-height="containerHeight"
      :buffer="3"
      class="host-cards-list-virtual"
    >
      <template #default="{ item }">
        <HostCard :host="item" :key="item.id" />
      </template>
    </VirtualList>
    
    <!-- Standard list for small number of hosts -->
    <div v-else class="host-cards-list">
      <HostCard 
        v-for="host in dashboard.filteredHosts" 
        :key="host.id"
        :host="host"
      />
    </div>
    
    <!-- Empty state when filters applied but no results -->
    <div v-if="!dashboard.loading && dashboard.filteredHosts.length === 0 && dashboard.totalHosts > 0" class="empty-state">
      No devices match current filters
      <button @click="filtersStore.clearAllFilters()" class="btn-link">
        Clear all filters
      </button>
    </div>
    
    <div v-if="!dashboard.loading && dashboard.totalHosts === 0" class="empty-state">
      Nenhum host encontrado
    </div>
  </div>
</template>

<script setup>
// Add filtersStore import
import { useFiltersStore } from '@/stores/filters';

// ... existing imports and code

const filtersStore = useFiltersStore();
</script>

<style scoped>
/* ... existing styles ... */

.filter-indicator {
  color: #6b7280;
  font-weight: normal;
}

.btn-link {
  background: none;
  border: none;
  color: #3b82f6;
  cursor: pointer;
  text-decoration: underline;
  padding: 0.5rem;
  margin-top: 0.5rem;
}

.btn-link:hover {
  color: #2563eb;
}
</style>
```

### Step 5: Add Filter Performance Monitoring (30 min)

**File:** `frontend/src/stores/dashboard.js`

Add performance tracking:

```javascript
const filteredHosts = computed(() => {
  const start = performance.now();
  
  // ... existing filter logic ...
  
  const duration = performance.now() - start;
  if (duration > 50) {
    console.warn(`[Performance] Filter took ${duration.toFixed(2)}ms (target: <50ms)`);
  }
  
  return filtered;
});
```

### Step 6: Unit Tests for Filter Logic (2 hours)

**File:** `frontend/tests/unit/dashboardStoreFilters.spec.js`

```javascript
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
});
```

### Step 7: Component Tests for Filter Integration (1.5 hours)

**File:** `frontend/tests/unit/DashboardViewFilters.spec.js`

```javascript
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { describe, it, expect, beforeEach } from 'vitest';
import DashboardView from '@/components/Dashboard/DashboardView.vue';
import { useDashboardStore } from '@/stores/dashboard';
import { useFiltersStore } from '@/stores/filters';

describe('DashboardView - Filter Integration', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('shows filtered device count', async () => {
    const wrapper = mount(DashboardView);
    const dashboardStore = useDashboardStore();
    const filtersStore = useFiltersStore();
    
    // Add test hosts
    dashboardStore.hosts.set(1, { id: 1, name: 'Host1', status: 'operational' });
    dashboardStore.hosts.set(2, { id: 2, name: 'Host2', status: 'offline' });
    
    filtersStore.toggleStatus('operational');
    await wrapper.vm.$nextTick();
    
    expect(wrapper.text()).toContain('1 of 2');
  });

  it('shows empty state when no matches', async () => {
    const wrapper = mount(DashboardView);
    const dashboardStore = useDashboardStore();
    const filtersStore = useFiltersStore();
    
    dashboardStore.hosts.set(1, { id: 1, name: 'Host1', status: 'operational' });
    
    filtersStore.toggleStatus('offline');
    await wrapper.vm.$nextTick();
    
    expect(wrapper.text()).toContain('No devices match current filters');
  });

  it('clear filters button works from empty state', async () => {
    const wrapper = mount(DashboardView);
    const filtersStore = useFiltersStore();
    
    filtersStore.toggleStatus('offline');
    await wrapper.vm.$nextTick();
    
    const clearButton = wrapper.find('.btn-link');
    await clearButton.trigger('click');
    
    expect(filtersStore.status).toEqual([]);
  });
});
```

---

## 🧪 Testing Checklist

### Unit Tests
- [ ] `filteredHosts` returns all hosts when no filters
- [ ] Status filter works
- [ ] Type filter works
- [ ] Location filter works
- [ ] Multiple filters combine with AND logic
- [ ] Search query filters by name/IP
- [ ] `availableLocations` extracts unique locations
- [ ] Locations sorted alphabetically
- [ ] Location count is accurate

### Component Tests
- [ ] FilterBar uses dynamic locations
- [ ] DashboardView shows filtered count "X of Y"
- [ ] Empty state appears when no matches
- [ ] Clear filters button works
- [ ] VirtualList receives filtered items

### Manual Tests
- [ ] Filter 100+ devices completes in <50ms
- [ ] UI updates immediately when filter toggled
- [ ] Location dropdown shows real locations
- [ ] Clear All clears all filters
- [ ] No console errors

---

## 📊 Performance Targets

| Metric | Target | Measured |
|--------|--------|----------|
| Filter application time | <50ms | TBD |
| UI update latency | <100ms | TBD |
| Memory usage (1000 hosts) | <50MB | TBD |
| Virtual scroll FPS | 60fps | TBD |

---

## 🚧 Known Limitations (To Fix in Day 3-5)

1. **Simple Search**: Current search uses `includes()`, not fuzzy matching
   - **Fix in Day 3**: Implement fuse.js fuzzy search

2. **No Search History**: Search queries not saved
   - **Fix in Day 3**: Add localStorage for recent searches

3. **No URL Sync**: Filters not persisted in URL
   - **Fix in Day 4**: Implement `useUrlSync` composable

4. **Status Mapping**: Assumes `host.status` matches filter values
   - **TODO**: Verify actual API status values match filter options

5. **Type Field**: Uses `host.type || host.device_type` (inconsistent API)
   - **TODO**: Standardize backend API field names

---

## 🎯 Day 2 Deliverables

### Code Files
- [x] `frontend/src/stores/dashboard.js` - Added `filteredHosts` and `availableLocations`
- [x] `frontend/src/components/filters/FilterBar.vue` - Dynamic locations
- [x] `frontend/src/components/Dashboard/DashboardView.vue` - Shows filtered list
- [x] `frontend/tests/unit/dashboardStoreFilters.spec.js` - 9 new tests
- [x] `frontend/tests/unit/DashboardViewFilters.spec.js` - 3 new tests

### Tests
- **New Tests**: 12+ (9 store + 3 component)
- **Total Tests**: 69+ (57 existing + 12 new)

### Documentation
- [x] `doc/roadmap/SPRINT1_DAY2_IMPLEMENTATION_PLAN.md` (this file)
- [x] `doc/roadmap/SPRINT1_DAY2_COMPLETION_REPORT.md` (after implementation)

---

## 📝 Next Steps (Day 3)

**Focus:** Search & Autocomplete

1. **SearchInput Component** (2 hours)
   - Text input with debounce (300ms)
   - Clear button (X icon)
   - Search icon
   - Loading spinner

2. **Fuzzy Matching** (2 hours)
   - Integrate fuse.js
   - Configure match threshold (0.3)
   - Highlight matched text
   - Sort by relevance score

3. **Autocomplete Dropdown** (2 hours)
   - Show top 10 suggestions
   - Keyboard navigation (arrows/enter/escape)
   - Click to select
   - Show device type icons

4. **Search History** (1 hour)
   - Save to localStorage
   - Show recent searches
   - Clear history button
   - Max 10 entries

5. **Testing** (1 hour)
   - Fuzzy match algorithm tests
   - Component tests for SearchInput
   - Integration tests with filters

---

**Report Template Ready**  
**Author:** AI Assistant  
**Date:** November 12, 2025  
**Status:** Ready for Implementation
