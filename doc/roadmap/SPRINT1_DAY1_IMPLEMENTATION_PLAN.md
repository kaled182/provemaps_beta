# Sprint 1 - Day 1: Setup + Filter UI Components

**Date:** November 12, 2025  
**Sprint:** Phase 13 Sprint 1 (Filters & Search)  
**Goal:** Foundation setup + basic filter UI  
**Estimated Time:** 8 hours

---

## 🎯 Day 1 Objectives

### Primary Goals
1. ✅ Install frontend dependencies (fuse.js, @vueuse/core)
2. ✅ Create Pinia filters store structure
3. ✅ Implement FilterBar.vue component
4. ✅ Implement FilterDropdown.vue component
5. ✅ Setup component testing infrastructure

### Success Criteria
- ✅ Dependencies installed and working
- ✅ FilterBar renders in dashboard
- ✅ Dropdowns show options (status/type/location)
- ✅ At least 2 component tests passing
- ✅ No console errors or warnings

---

## 📦 Step 1: Install Dependencies (30 min)

### Frontend Dependencies

```bash
cd frontend
npm install fuse.js@7.0.0 @vueuse/core@11.0.0 --save
```

**What we're installing:**
- **fuse.js:** Fuzzy search library (12KB, lightweight, no deps)
- **@vueuse/core:** Vue composables (debounce, local storage, etc.)

### Verify Installation

```bash
# Check package.json
cat package.json | grep -E "(fuse|vueuse)"

# Expected output:
# "fuse.js": "^7.0.0",
# "@vueuse/core": "^11.0.0"
```

### Update vite.config.js (if needed)

No changes needed - both libraries are ESM-compatible.

---

## 🏗️ Step 2: Create Pinia Filters Store (1 hour)

### File Structure

```
frontend/src/
├── stores/
│   ├── dashboard.ts         # Existing
│   └── filters.ts           # NEW - Filter state management
```

### Implementation: `frontend/src/stores/filters.ts`

```typescript
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
```

### Unit Test: `frontend/src/stores/__tests__/filters.spec.ts`

```typescript
// frontend/src/stores/__tests__/filters.spec.ts
import { setActivePinia, createPinia } from 'pinia';
import { describe, it, expect, beforeEach } from 'vitest';
import { useFiltersStore } from '../filters';

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

  it('toggles status filter', () => {
    const store = useFiltersStore();
    store.toggleStatus('operational');
    expect(store.status).toContain('operational');
    
    store.toggleStatus('operational');
    expect(store.status).not.toContain('operational');
  });

  it('calculates active filter count', () => {
    const store = useFiltersStore();
    expect(store.activeFilterCount).toBe(0);
    
    store.toggleStatus('operational');
    store.toggleType('OLT');
    expect(store.activeFilterCount).toBe(2);
  });

  it('clears all filters', () => {
    const store = useFiltersStore();
    store.toggleStatus('operational');
    store.toggleType('OLT');
    store.setSearchQuery('test');
    
    store.clearAllFilters();
    
    expect(store.status).toEqual([]);
    expect(store.types).toEqual([]);
    expect(store.searchQuery).toBe('');
  });
});
```

---

## 🎨 Step 3: FilterBar Component (2 hours)

### File: `frontend/src/components/filters/FilterBar.vue`

```vue
<script setup lang="ts">
import { computed } from 'vue';
import { useFiltersStore } from '@/stores/filters';
import FilterDropdown from './FilterDropdown.vue';

const filtersStore = useFiltersStore();

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

// Location options will be populated from dashboard data
const locationOptions = computed(() => {
  // TODO: Get from dashboard store
  return [
    { value: '1', label: 'POP Central' },
    { value: '2', label: 'POP Norte' },
    { value: '3', label: 'POP Sul' },
  ];
});

const showClearButton = computed(() => filtersStore.hasActiveFilters);

function handleClearAll() {
  filtersStore.clearAllFilters();
}
</script>

<template>
  <div class="filter-bar">
    <div class="filter-bar__dropdowns">
      <FilterDropdown
        label="Status"
        :options="statusOptions"
        :selected="filtersStore.status"
        @toggle="filtersStore.toggleStatus"
        @clear="filtersStore.clearStatusFilters"
      />
      
      <FilterDropdown
        label="Type"
        :options="typeOptions"
        :selected="filtersStore.types"
        @toggle="filtersStore.toggleType"
        @clear="filtersStore.clearTypeFilters"
      />
      
      <FilterDropdown
        label="Location"
        :options="locationOptions"
        :selected="filtersStore.locations"
        @toggle="filtersStore.toggleLocation"
        @clear="filtersStore.clearLocationFilters"
      />
    </div>

    <div class="filter-bar__actions">
      <span v-if="filtersStore.activeFilterCount > 0" class="filter-count">
        Filters ({{ filtersStore.activeFilterCount }})
      </span>
      
      <button
        v-if="showClearButton"
        class="btn btn-sm btn-outline"
        @click="handleClearAll"
      >
        Clear All
      </button>
    </div>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 1rem;
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
  color: #6b7280;
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
  border: 1px solid #d1d5db;
  background: white;
  color: #374151;
}

.btn-outline:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

@media (max-width: 768px) {
  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-bar__dropdowns {
    margin-bottom: 1rem;
  }

  .filter-bar__actions {
    justify-content: space-between;
  }
}
</style>
```

---

## 🎨 Step 4: FilterDropdown Component (2 hours)

### File: `frontend/src/components/filters/FilterDropdown.vue`

```vue
<script setup lang="ts">
import { ref, computed } from 'vue';
import { onClickOutside } from '@vueuse/core';

export interface FilterOption {
  value: string;
  label: string;
  color?: string;
}

interface Props {
  label: string;
  options: FilterOption[];
  selected: string[];
}

interface Emits {
  (e: 'toggle', value: string): void;
  (e: 'clear'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const isOpen = ref(false);
const dropdownRef = ref(null);

const selectedCount = computed(() => props.selected.length);
const buttonLabel = computed(() => {
  if (selectedCount.value === 0) return props.label;
  if (selectedCount.value === 1) {
    const option = props.options.find(opt => opt.value === props.selected[0]);
    return option?.label || props.label;
  }
  return `${props.label} (${selectedCount.value})`;
});

function toggleDropdown() {
  isOpen.value = !isOpen.value;
}

function handleToggle(value: string) {
  emit('toggle', value);
}

function handleClear(event: Event) {
  event.stopPropagation();
  emit('clear');
  isOpen.value = false;
}

function isSelected(value: string) {
  return props.selected.includes(value);
}

onClickOutside(dropdownRef, () => {
  isOpen.value = false;
});
</script>

<template>
  <div ref="dropdownRef" class="filter-dropdown">
    <button
      class="filter-dropdown__button"
      :class="{ 'filter-dropdown__button--active': selectedCount > 0 }"
      @click="toggleDropdown"
    >
      {{ buttonLabel }}
      <svg
        class="filter-dropdown__icon"
        :class="{ 'filter-dropdown__icon--open': isOpen }"
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <polyline points="6 9 12 15 18 9"></polyline>
      </svg>
    </button>

    <div v-if="isOpen" class="filter-dropdown__menu">
      <div class="filter-dropdown__header">
        <span class="filter-dropdown__title">{{ label }}</span>
        <button
          v-if="selectedCount > 0"
          class="filter-dropdown__clear"
          @click="handleClear"
        >
          Clear
        </button>
      </div>

      <div class="filter-dropdown__options">
        <label
          v-for="option in options"
          :key="option.value"
          class="filter-dropdown__option"
        >
          <input
            type="checkbox"
            :checked="isSelected(option.value)"
            @change="handleToggle(option.value)"
          />
          <span class="filter-dropdown__label">
            {{ option.label }}
          </span>
          <span
            v-if="isSelected(option.value)"
            class="filter-dropdown__checkmark"
          >
            ✓
          </span>
        </label>
      </div>
    </div>
  </div>
</template>

<style scoped>
.filter-dropdown {
  position: relative;
  display: inline-block;
}

.filter-dropdown__button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-dropdown__button:hover {
  border-color: #9ca3af;
  background: #f9fafb;
}

.filter-dropdown__button--active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.filter-dropdown__icon {
  transition: transform 0.2s;
}

.filter-dropdown__icon--open {
  transform: rotate(180deg);
}

.filter-dropdown__menu {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  min-width: 200px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  z-index: 10;
}

.filter-dropdown__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e5e7eb;
}

.filter-dropdown__title {
  font-weight: 600;
  font-size: 0.875rem;
  color: #111827;
}

.filter-dropdown__clear {
  font-size: 0.75rem;
  color: #3b82f6;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}

.filter-dropdown__clear:hover {
  text-decoration: underline;
}

.filter-dropdown__options {
  max-height: 300px;
  overflow-y: auto;
  padding: 0.5rem 0;
}

.filter-dropdown__option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1rem;
  cursor: pointer;
  transition: background 0.15s;
}

.filter-dropdown__option:hover {
  background: #f9fafb;
}

.filter-dropdown__option input[type="checkbox"] {
  cursor: pointer;
}

.filter-dropdown__label {
  flex: 1;
  font-size: 0.875rem;
  color: #374151;
}

.filter-dropdown__checkmark {
  color: #3b82f6;
  font-weight: bold;
}
</style>
```

---

## 🧪 Step 5: Component Tests (1.5 hours)

### Test: `frontend/src/components/filters/__tests__/FilterBar.spec.ts`

```typescript
// frontend/src/components/filters/__tests__/FilterBar.spec.ts
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { describe, it, expect, beforeEach } from 'vitest';
import FilterBar from '../FilterBar.vue';
import { useFiltersStore } from '@/stores/filters';

describe('FilterBar', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('renders filter dropdowns', () => {
    const wrapper = mount(FilterBar);
    expect(wrapper.find('.filter-bar').exists()).toBe(true);
    expect(wrapper.text()).toContain('Status');
    expect(wrapper.text()).toContain('Type');
    expect(wrapper.text()).toContain('Location');
  });

  it('shows filter count when filters active', async () => {
    const wrapper = mount(FilterBar);
    const store = useFiltersStore();
    
    store.toggleStatus('operational');
    await wrapper.vm.$nextTick();
    
    expect(wrapper.text()).toContain('Filters (1)');
  });

  it('shows clear all button when filters active', async () => {
    const wrapper = mount(FilterBar);
    const store = useFiltersStore();
    
    store.toggleStatus('operational');
    await wrapper.vm.$nextTick();
    
    const clearButton = wrapper.find('button');
    expect(clearButton.text()).toBe('Clear All');
  });

  it('clears all filters when clear button clicked', async () => {
    const wrapper = mount(FilterBar);
    const store = useFiltersStore();
    
    store.toggleStatus('operational');
    store.toggleType('OLT');
    await wrapper.vm.$nextTick();
    
    await wrapper.find('button').trigger('click');
    
    expect(store.status).toEqual([]);
    expect(store.types).toEqual([]);
  });
});
```

### Test: `frontend/src/components/filters/__tests__/FilterDropdown.spec.ts`

```typescript
// frontend/src/components/filters/__tests__/FilterDropdown.spec.ts
import { mount } from '@vue/test-utils';
import { describe, it, expect } from 'vitest';
import FilterDropdown from '../FilterDropdown.vue';

const mockOptions = [
  { value: 'opt1', label: 'Option 1' },
  { value: 'opt2', label: 'Option 2' },
];

describe('FilterDropdown', () => {
  it('renders with label', () => {
    const wrapper = mount(FilterDropdown, {
      props: {
        label: 'Test Filter',
        options: mockOptions,
        selected: [],
      },
    });
    
    expect(wrapper.text()).toContain('Test Filter');
  });

  it('opens dropdown when button clicked', async () => {
    const wrapper = mount(FilterDropdown, {
      props: {
        label: 'Test Filter',
        options: mockOptions,
        selected: [],
      },
    });
    
    await wrapper.find('.filter-dropdown__button').trigger('click');
    
    expect(wrapper.find('.filter-dropdown__menu').exists()).toBe(true);
  });

  it('emits toggle event when option selected', async () => {
    const wrapper = mount(FilterDropdown, {
      props: {
        label: 'Test Filter',
        options: mockOptions,
        selected: [],
      },
    });
    
    await wrapper.find('.filter-dropdown__button').trigger('click');
    await wrapper.find('input[type="checkbox"]').trigger('change');
    
    expect(wrapper.emitted('toggle')).toBeTruthy();
    expect(wrapper.emitted('toggle')![0]).toEqual(['opt1']);
  });

  it('shows selected count in button label', () => {
    const wrapper = mount(FilterDropdown, {
      props: {
        label: 'Test Filter',
        options: mockOptions,
        selected: ['opt1', 'opt2'],
      },
    });
    
    expect(wrapper.find('.filter-dropdown__button').text()).toContain('(2)');
  });
});
```

---

## 🔗 Step 6: Integrate into Dashboard (1 hour)

### Update: `frontend/src/views/DashboardView.vue`

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import FilterBar from '@/components/filters/FilterBar.vue';
// ... existing imports

// ... existing code
</script>

<template>
  <div class="dashboard">
    <!-- NEW: Filter Bar -->
    <FilterBar />
    
    <!-- Existing dashboard content -->
    <div class="dashboard-map">
      <!-- ... existing map code -->
    </div>
    
    <div class="dashboard-devices">
      <!-- ... existing device list -->
    </div>
  </div>
</template>
```

---

## ✅ Day 1 Checklist

### Morning (4 hours)
- [ ] Install dependencies (fuse.js, @vueuse/core)
- [ ] Create filters store (`stores/filters.ts`)
- [ ] Write filters store unit tests (5 tests)
- [ ] Run tests: `npm run test:unit`

### Afternoon (4 hours)
- [ ] Create FilterBar component
- [ ] Create FilterDropdown component
- [ ] Write component tests (8 tests total)
- [ ] Integrate FilterBar into DashboardView
- [ ] Visual testing in browser
- [ ] Fix any console errors/warnings

### End of Day Validation
- [ ] All tests passing (`npm run test:unit`)
- [ ] FilterBar renders in dashboard
- [ ] Dropdowns open/close correctly
- [ ] Selected filters show in button badges
- [ ] Clear All button works
- [ ] No TypeScript errors (`npm run type-check`)
- [ ] Git commit: "feat(filters): Add FilterBar and FilterDropdown components"

---

## 📊 Success Metrics

**Code Coverage:**
- Filters store: 100% (all actions/getters tested)
- FilterBar: >80% (main interactions covered)
- FilterDropdown: >80% (toggle, clear, keyboard nav)

**Performance:**
- FilterBar render: <50ms
- Dropdown open: <30ms
- No memory leaks (test with DevTools)

**Quality:**
- 0 ESLint errors
- 0 TypeScript errors
- 0 console warnings
- Accessible (keyboard navigation works)

---

## 🐛 Common Issues & Solutions

### Issue: Pinia store not found
**Solution:** Make sure Pinia is initialized in `main.ts`:
```typescript
import { createPinia } from 'pinia';
app.use(createPinia());
```

### Issue: Click outside not working
**Solution:** Verify `@vueuse/core` is installed and imported correctly.

### Issue: Tests fail with "Cannot find module"
**Solution:** Check `vite.config.ts` has proper path aliases:
```typescript
resolve: {
  alias: {
    '@': fileURLToPath(new URL('./src', import.meta.url))
  }
}
```

---

## 📝 Notes for Tomorrow (Day 2)

**Prepare:**
- [ ] Review how dashboard currently gets device data
- [ ] Plan filter application logic (client-side filtering)
- [ ] Consider filter performance with 1000+ devices
- [ ] Think about virtual scrolling if needed

**Questions to Answer:**
- Should filters apply instantly or on "Apply" button click?
- How to handle empty filter results (show message? keep previous?)
- Should we persist filters to localStorage for next visit?

---

**End of Day 1 Plan** ✅

Tomorrow we'll connect the filters to actually filter the device list!
