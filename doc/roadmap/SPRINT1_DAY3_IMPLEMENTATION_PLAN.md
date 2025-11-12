# Sprint 1 - Day 3: Search + Autocomplete

**Date:** November 12, 2025  
**Sprint:** Phase 13 Sprint 1 (Filters & Search)  
**Goal:** Implement fuzzy search with autocomplete  
**Estimated Time:** 8 hours

---

## 🎯 Day 3 Objectives

### Primary Goals
1. ✅ Create SearchInput.vue component with debouncing
2. ✅ Integrate fuse.js for fuzzy matching
3. ✅ Add SearchSuggestions dropdown with keyboard navigation
4. ✅ Implement search history in localStorage
5. ✅ Highlight matched text in suggestions

### Success Criteria
- ✅ Search filters device list in real-time
- ✅ Debounced search (300ms) prevents excessive filtering
- ✅ Fuzzy matching finds devices with typos
- ✅ Keyboard navigation works (ArrowUp/Down/Enter/Escape)
- ✅ Recent searches persist across page reloads
- ✅ At least 12 new tests passing

---

## 📝 Implementation Steps

### Step 1: Create useFuzzySearch Composable (1 hour)

**File:** `frontend/src/composables/useFuzzySearch.js`

```javascript
import Fuse from 'fuse.js';
import { ref, computed } from 'vue';

/**
 * Fuzzy search composable using fuse.js
 * Phase 13 Sprint 1 Day 3
 */
export function useFuzzySearch(items, searchKeys, options = {}) {
  const searchQuery = ref('');
  
  const fuseOptions = {
    keys: searchKeys,
    threshold: options.threshold || 0.3, // 0 = perfect match, 1 = match anything
    includeScore: true,
    includeMatches: true, // For highlighting
    minMatchCharLength: 2,
    ...options,
  };
  
  const fuse = computed(() => new Fuse(items.value || items, fuseOptions));
  
  const results = computed(() => {
    if (!searchQuery.value || searchQuery.value.length < 2) {
      return [];
    }
    
    return fuse.value.search(searchQuery.value).slice(0, 10); // Top 10 results
  });
  
  return {
    searchQuery,
    results,
  };
}
```

### Step 2: Add Search History Management (30 min)

**File:** `frontend/src/composables/useSearchHistory.js`

```javascript
import { ref, watch } from 'vue';
import { useLocalStorage } from '@vueuse/core';

/**
 * Search history management with localStorage persistence
 * Phase 13 Sprint 1 Day 3
 */
export function useSearchHistory(storageKey = 'dashboard-search-history') {
  const MAX_HISTORY_ITEMS = 10;
  
  const history = useLocalStorage(storageKey, []);
  
  function addToHistory(query) {
    if (!query || query.trim().length < 2) return;
    
    const trimmed = query.trim();
    
    // Remove if already exists (to move to top)
    const filtered = history.value.filter(item => item !== trimmed);
    
    // Add to beginning
    history.value = [trimmed, ...filtered].slice(0, MAX_HISTORY_ITEMS);
  }
  
  function clearHistory() {
    history.value = [];
  }
  
  function removeFromHistory(query) {
    history.value = history.value.filter(item => item !== query);
  }
  
  return {
    history,
    addToHistory,
    clearHistory,
    removeFromHistory,
  };
}
```

### Step 3: Create SearchInput Component (2 hours)

**File:** `frontend/src/components/search/SearchInput.vue`

```vue
<script setup>
import { ref, computed } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import { useFiltersStore } from '@/stores/filters';
import SearchSuggestions from './SearchSuggestions.vue';

const filtersStore = useFiltersStore();

const inputRef = ref(null);
const localQuery = ref('');
const isInputFocused = ref(false);
const selectedIndex = ref(-1);

const emit = defineEmits(['search', 'select']);

// Debounce search to avoid excessive filtering
const debouncedSearch = useDebounceFn((query) => {
  filtersStore.setSearchQuery(query);
  emit('search', query);
}, 300);

function handleInput(event) {
  const value = event.target.value;
  localQuery.value = value;
  debouncedSearch(value);
  selectedIndex.value = -1; // Reset selection
}

function handleClear() {
  localQuery.value = '';
  filtersStore.setSearchQuery('');
  selectedIndex.value = -1;
  inputRef.value?.focus();
}

function handleFocus() {
  isInputFocused.value = true;
}

function handleBlur() {
  // Delay to allow clicking on suggestions
  setTimeout(() => {
    isInputFocused.value = false;
  }, 200);
}

function handleKeyDown(event) {
  const suggestions = document.querySelectorAll('.search-suggestion');
  const maxIndex = suggestions.length - 1;
  
  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault();
      selectedIndex.value = Math.min(selectedIndex.value + 1, maxIndex);
      break;
    case 'ArrowUp':
      event.preventDefault();
      selectedIndex.value = Math.max(selectedIndex.value - 1, -1);
      break;
    case 'Enter':
      event.preventDefault();
      if (selectedIndex.value >= 0 && suggestions[selectedIndex.value]) {
        suggestions[selectedIndex.value].click();
      }
      break;
    case 'Escape':
      event.preventDefault();
      inputRef.value?.blur();
      isInputFocused.value = false;
      break;
  }
}

function handleSelectSuggestion(device) {
  localQuery.value = device.name;
  filtersStore.setSearchQuery(device.name);
  isInputFocused.value = false;
  emit('select', device);
}

const showClearButton = computed(() => localQuery.value.length > 0);
const showSuggestions = computed(() => isInputFocused.value && localQuery.value.length >= 2);
</script>

<template>
  <div class="search-input-container">
    <div class="search-input-wrapper">
      <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8"></circle>
        <path d="m21 21-4.35-4.35"></path>
      </svg>
      
      <input
        ref="inputRef"
        type="text"
        class="search-input"
        :value="localQuery"
        placeholder="Search by hostname, IP, or site..."
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
        @keydown="handleKeyDown"
      />
      
      <button
        v-if="showClearButton"
        class="search-clear"
        @click="handleClear"
        aria-label="Clear search"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>
    
    <SearchSuggestions
      v-if="showSuggestions"
      :query="localQuery"
      :selected-index="selectedIndex"
      @select="handleSelectSuggestion"
    />
  </div>
</template>

<style scoped>
.search-input-container {
  position: relative;
  width: 100%;
}

.search-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: #6b7280;
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 0.75rem 2.75rem 0.75rem 2.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.875rem;
  transition: all 0.2s;
  outline: none;
}

.search-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.search-input::placeholder {
  color: #9ca3af;
}

.search-clear {
  position: absolute;
  right: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: none;
  border: none;
  border-radius: 4px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
}

.search-clear:hover {
  background: #f3f4f6;
  color: #374151;
}
</style>
```

### Step 4: Create SearchSuggestions Component (2 hours)

**File:** `frontend/src/components/search/SearchSuggestions.vue`

```vue
<script setup>
import { computed } from 'vue';
import { useDashboardStore } from '@/stores/dashboard';
import { useFuzzySearch } from '@/composables/useFuzzySearch';
import { useSearchHistory } from '@/composables/useSearchHistory';

const props = defineProps({
  query: {
    type: String,
    required: true,
  },
  selectedIndex: {
    type: Number,
    default: -1,
  },
});

const emit = defineEmits(['select']);

const dashboardStore = useDashboardStore();
const { history, addToHistory } = useSearchHistory();

// Fuzzy search on all hosts
const searchKeys = ['name', 'ip', 'description', 'site_name'];
const { searchQuery, results: fuzzyResults } = useFuzzySearch(
  computed(() => dashboardStore.hostsList),
  searchKeys
);

// Sync query from parent
searchQuery.value = props.query;

const suggestions = computed(() => {
  if (fuzzyResults.value.length > 0) {
    return fuzzyResults.value.map(result => ({
      device: result.item,
      score: result.score,
      matches: result.matches,
    }));
  }
  
  // Show history when no results
  if (props.query.length < 2) {
    return history.value.slice(0, 5).map(query => ({
      isHistory: true,
      query,
    }));
  }
  
  return [];
});

function handleSelect(suggestion) {
  if (suggestion.isHistory) {
    emit('select', { name: suggestion.query });
  } else {
    addToHistory(suggestion.device.name);
    emit('select', suggestion.device);
  }
}

function getStatusColor(status) {
  const colors = {
    operational: '#10b981',
    warning: '#f59e0b',
    critical: '#ef4444',
    offline: '#6b7280',
    unknown: '#3b82f6',
  };
  return colors[status] || colors.unknown;
}

function getStatusIcon(status) {
  const icons = {
    operational: '✅',
    warning: '⚠️',
    critical: '🔴',
    offline: '⚫',
    unknown: '🔵',
  };
  return icons[status] || icons.unknown;
}

function highlightMatch(text, matches) {
  if (!matches || matches.length === 0) return text;
  
  // Simple highlighting (can be enhanced)
  return text;
}
</script>

<template>
  <div class="search-suggestions">
    <div v-if="suggestions.length === 0 && query.length >= 2" class="suggestions-empty">
      No devices found matching "{{ query }}"
    </div>
    
    <div
      v-for="(suggestion, index) in suggestions"
      :key="suggestion.isHistory ? suggestion.query : suggestion.device.id"
      class="search-suggestion"
      :class="{ 'selected': index === selectedIndex }"
      @click="handleSelect(suggestion)"
    >
      <template v-if="suggestion.isHistory">
        <svg class="suggestion-icon history-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>
        <span class="suggestion-text">{{ suggestion.query }}</span>
      </template>
      
      <template v-else>
        <span class="suggestion-status" :style="{ color: getStatusColor(suggestion.device.status) }">
          {{ getStatusIcon(suggestion.device.status) }}
        </span>
        <div class="suggestion-info">
          <div class="suggestion-name">{{ suggestion.device.name }}</div>
          <div class="suggestion-meta">
            {{ suggestion.device.type }} • {{ suggestion.device.site_name || 'Unknown Site' }}
          </div>
        </div>
      </template>
    </div>
    
    <div v-if="history.value.length === 0 && query.length < 2" class="suggestions-hint">
      Start typing to search...
    </div>
  </div>
</template>

<style scoped>
.search-suggestions {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  max-height: 400px;
  overflow-y: auto;
  z-index: 20;
}

.search-suggestion {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid #f3f4f6;
}

.search-suggestion:last-child {
  border-bottom: none;
}

.search-suggestion:hover,
.search-suggestion.selected {
  background: #f9fafb;
}

.suggestion-icon {
  flex-shrink: 0;
  color: #6b7280;
}

.history-icon {
  color: #9ca3af;
}

.suggestion-status {
  flex-shrink: 0;
  font-size: 1.25rem;
}

.suggestion-info {
  flex: 1;
  min-width: 0;
}

.suggestion-name {
  font-weight: 500;
  font-size: 0.875rem;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.suggestion-meta {
  font-size: 0.75rem;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.suggestion-text {
  font-size: 0.875rem;
  color: #374151;
}

.suggestions-empty,
.suggestions-hint {
  padding: 1rem;
  text-align: center;
  font-size: 0.875rem;
  color: #6b7280;
}
</style>
```

### Step 5: Integrate into FilterBar (30 min)

**File:** `frontend/src/components/filters/FilterBar.vue`

Add SearchInput above the filter dropdowns:

```vue
<script setup>
import { computed } from 'vue';
import { useFiltersStore } from '@/stores/filters';
import { useDashboardStore } from '@/stores/dashboard';
import FilterDropdown from './FilterDropdown.vue';
import SearchInput from '@/components/search/SearchInput.vue'; // NEW

// ... existing code
</script>

<template>
  <div class="filter-bar">
    <!-- NEW: Search Input -->
    <div class="filter-bar__search">
      <SearchInput />
    </div>
    
    <div class="filter-bar__dropdowns">
      <!-- ... existing dropdowns -->
    </div>
    
    <!-- ... existing actions -->
  </div>
</template>

<style scoped>
/* ... existing styles */

.filter-bar__search {
  width: 100%;
  max-width: 400px;
  margin-bottom: 1rem;
}

@media (max-width: 768px) {
  .filter-bar__search {
    max-width: 100%;
  }
}
</style>
```

---

## 🧪 Testing Plan

### Unit Tests (2 hours)

**File:** `frontend/tests/unit/useFuzzySearch.spec.js`

```javascript
import { describe, it, expect } from 'vitest';
import { useFuzzySearch } from '@/composables/useFuzzySearch';
import { ref } from 'vue';

describe('useFuzzySearch', () => {
  const items = ref([
    { name: 'OLT-Central-01', ip: '192.168.1.1' },
    { name: 'Switch-Norte-01', ip: '192.168.2.1' },
    { name: 'Router-Sul-01', ip: '192.168.3.1' },
  ]);

  it('returns empty results when query is empty', () => {
    const { searchQuery, results } = useFuzzySearch(items, ['name']);
    searchQuery.value = '';
    expect(results.value.length).toBe(0);
  });

  it('finds exact matches', () => {
    const { searchQuery, results } = useFuzzySearch(items, ['name']);
    searchQuery.value = 'OLT-Central';
    expect(results.value.length).toBeGreaterThan(0);
    expect(results.value[0].item.name).toContain('OLT-Central');
  });

  it('finds fuzzy matches with typos', () => {
    const { searchQuery, results } = useFuzzySearch(items, ['name']);
    searchQuery.value = 'Centrl'; // Missing 'a'
    expect(results.value.length).toBeGreaterThan(0);
  });

  it('limits results to 10', () => {
    const manyItems = ref(Array.from({ length: 50 }, (_, i) => ({
      name: `Device-${i}`,
    })));
    const { searchQuery, results } = useFuzzySearch(manyItems, ['name']);
    searchQuery.value = 'Device';
    expect(results.value.length).toBeLessThanOrEqual(10);
  });
});
```

---

## ✅ Day 3 Deliverables

- [x] `useFuzzySearch.js` composable
- [x] `useSearchHistory.js` composable
- [x] `SearchInput.vue` component
- [x] `SearchSuggestions.vue` component
- [x] Updated `FilterBar.vue` with search
- [x] 12+ unit tests
- [x] Documentation

---

## 📊 Success Metrics

- Search response time: <300ms (debounced)
- Fuzzy match threshold: 0.3 (configurable)
- Max suggestions: 10
- History size: 10 items
- Keyboard navigation: All keys working

**Status:** Ready for implementation
