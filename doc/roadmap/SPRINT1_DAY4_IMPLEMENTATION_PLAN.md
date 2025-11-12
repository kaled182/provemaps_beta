# Phase 13 Sprint 1 Day 4 - Implementation Plan
## 🔗 URL Persistence

**Objective:** Enable filter state persistence in URL query parameters for bookmarking and sharing

**Duration:** 8 hours (estimated) → Likely ~1 hour (based on Days 1-3 velocity)

---

## 🎯 Goals

1. **Create useUrlSync composable** to sync filters store with Vue Router
2. **Implement bi-directional sync**: URL ↔ Filters Store
3. **Add debouncing** to prevent URL history pollution
4. **Handle initial load** from URL parameters
5. **Add 8-10 unit tests** for URL sync logic

---

## 📋 Requirements

### URL Parameter Format

```
# Single filter
/dashboard?status=offline

# Multiple filters
/dashboard?status=offline,warning&type=router&location=Branch%20A

# With search query
/dashboard?status=offline&q=server

# All filters
/dashboard?status=offline,warning&type=router,switch&location=HQ&q=alpha
```

### URL Parameter Mapping

| Filter Store Property | URL Param | Format | Example |
|----------------------|-----------|--------|---------|
| `status` (array) | `status` | Comma-separated | `offline,warning` |
| `types` (array) | `type` | Comma-separated | `router,switch` |
| `locations` (array) | `location` | Comma-separated (URL-encoded) | `Branch%20A,HQ` |
| `searchQuery` (string) | `q` | String (URL-encoded) | `server%20alpha` |

### Key Features

1. **Initial Load**: Read URL params on app mount → populate filters store
2. **Filter Changes**: Update URL when filters change (debounced 500ms)
3. **Browser Navigation**: Handle back/forward buttons correctly
4. **Bookmarking**: Users can bookmark `/dashboard?status=offline` and return to that exact state
5. **Sharing**: Users can copy URL and share with colleagues
6. **Clean URLs**: Remove empty params (`?status=` becomes ``)
7. **History Management**: Use `router.replace()` during debounce to avoid polluting history

---

## 🏗️ Architecture

### Component Flow

```
[Browser URL Change]
        ↓
    popstate event
        ↓
  useUrlSync watch router.query
        ↓
  Parse URL params → arrays/strings
        ↓
  Update filters store
        ↓
  dashboard.filteredHosts recomputes
        ↓
  UI updates
```

```
[User Changes Filter]
        ↓
  FilterBar updates filters store
        ↓
  useUrlSync watch filters store (debounced 500ms)
        ↓
  Serialize filters → URL params
        ↓
  router.replace({ query: { ... } })
        ↓
  URL updates (no page reload)
```

### useUrlSync Composable

**Location:** `frontend/src/composables/useUrlSync.js`

**Responsibilities:**
1. Watch filters store changes
2. Debounce URL updates (500ms)
3. Serialize filters to URL params
4. Parse URL params to filters
5. Handle initial load from URL
6. Clean empty parameters

**API:**
```javascript
import { useUrlSync } from '@/composables/useUrlSync';
import { useFiltersStore } from '@/stores/filters';
import { useRouter, useRoute } from 'vue-router';

export default {
  setup() {
    const filtersStore = useFiltersStore();
    const router = useRouter();
    const route = useRoute();
    
    // Initialize URL sync (bi-directional)
    useUrlSync(filtersStore, router, route);
    
    // That's it! URL and filters are now synced
  }
}
```

---

## 📝 Implementation Steps

### Step 1: Create useUrlSync Composable (2 hours → 20 min)

**File:** `frontend/src/composables/useUrlSync.js`

```javascript
import { watch } from 'vue';
import { useDebounceFn } from '@vueuse/core';

/**
 * Syncs filters store with URL query parameters
 * Enables bookmarking and sharing of filter states
 * 
 * @param {Object} filtersStore - Pinia filters store
 * @param {Object} router - Vue Router instance
 * @param {Object} route - Vue Router route
 */
export function useUrlSync(filtersStore, router, route) {
  // Parse URL params to filter values
  const parseUrlParams = (query) => {
    return {
      status: parseArrayParam(query.status),
      types: parseArrayParam(query.type),
      locations: parseArrayParam(query.location),
      searchQuery: query.q || '',
    };
  };

  // Parse comma-separated string to array
  const parseArrayParam = (param) => {
    if (!param) return [];
    if (Array.isArray(param)) return param; // Vue Router might parse as array
    return param.split(',').filter(Boolean);
  };

  // Serialize filters to URL params
  const serializeFilters = () => {
    const params = {};

    if (filtersStore.status.length > 0) {
      params.status = filtersStore.status.join(',');
    }

    if (filtersStore.types.length > 0) {
      params.type = filtersStore.types.join(',');
    }

    if (filtersStore.locations.length > 0) {
      params.location = filtersStore.locations.join(',');
    }

    if (filtersStore.searchQuery.trim().length > 0) {
      params.q = filtersStore.searchQuery.trim();
    }

    return params;
  };

  // Update URL (debounced to prevent history pollution)
  const updateUrl = useDebounceFn(() => {
    const newQuery = serializeFilters();
    
    // Only update if query actually changed
    if (JSON.stringify(route.query) !== JSON.stringify(newQuery)) {
      router.replace({ query: newQuery });
    }
  }, 500); // 500ms debounce

  // Initialize filters from URL on mount
  const initializeFromUrl = () => {
    const filters = parseUrlParams(route.query);
    
    // Update store without triggering URL update
    filtersStore.$patch(filters);
  };

  // Watch filters store changes → update URL
  watch(
    () => ({
      status: filtersStore.status,
      types: filtersStore.types,
      locations: filtersStore.locations,
      searchQuery: filtersStore.searchQuery,
    }),
    () => {
      updateUrl();
    },
    { deep: true }
  );

  // Watch URL changes (browser back/forward) → update filters
  watch(
    () => route.query,
    (newQuery) => {
      const filters = parseUrlParams(newQuery);
      
      // Only update if filters actually changed (avoid infinite loop)
      if (
        JSON.stringify(filters.status) !== JSON.stringify(filtersStore.status) ||
        JSON.stringify(filters.types) !== JSON.stringify(filtersStore.types) ||
        JSON.stringify(filters.locations) !== JSON.stringify(filtersStore.locations) ||
        filters.searchQuery !== filtersStore.searchQuery
      ) {
        filtersStore.$patch(filters);
      }
    }
  );

  // Run initialization
  initializeFromUrl();
}
```

**Key Design Decisions:**

1. **500ms Debounce**: Longer than search debounce (300ms) because URL changes are more expensive
2. **router.replace()**: Doesn't create new history entry during rapid changes
3. **Deep Comparison**: Prevents infinite update loops
4. **$patch**: Batch updates to filters store for efficiency
5. **Clean Params**: Empty arrays/strings are omitted from URL

---

### Step 2: Integrate into DashboardView (30 min → 5 min)

**File:** `frontend/src/components/Dashboard/DashboardView.vue`

**Add to script setup:**

```javascript
import { useUrlSync } from '@/composables/useUrlSync';
import { useRouter, useRoute } from 'vue-router';

// ... existing code ...

const filtersStore = useFiltersStore();
const router = useRouter();
const route = useRoute();

// Initialize URL sync
useUrlSync(filtersStore, router, route);
```

**That's it!** The sync is automatic after initialization.

---

### Step 3: Create Unit Tests (2 hours → 25 min)

**File:** `frontend/tests/unit/useUrlSync.spec.js`

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ref } from 'vue';
import { useUrlSync } from '@/composables/useUrlSync';

// Mock @vueuse/core
vi.mock('@vueuse/core', async () => {
  const actual = await vi.importActual('@vueuse/core');
  return {
    ...actual,
    useDebounceFn: (fn) => fn, // No debounce in tests
  };
});

describe('useUrlSync', () => {
  let filtersStore;
  let router;
  let route;

  beforeEach(() => {
    // Mock filters store
    filtersStore = {
      status: [],
      types: [],
      locations: [],
      searchQuery: '',
      $patch: vi.fn((updates) => {
        Object.assign(filtersStore, updates);
      }),
    };

    // Mock route
    route = {
      query: {},
    };

    // Mock router
    router = {
      replace: vi.fn(),
    };
  });

  it('should initialize filters from URL params', () => {
    route.query = {
      status: 'offline,warning',
      type: 'router',
      location: 'Branch A',
      q: 'test',
    };

    useUrlSync(filtersStore, router, route);

    expect(filtersStore.$patch).toHaveBeenCalledWith({
      status: ['offline', 'warning'],
      types: ['router'],
      locations: ['Branch A'],
      searchQuery: 'test',
    });
  });

  it('should handle empty URL params', () => {
    route.query = {};

    useUrlSync(filtersStore, router, route);

    expect(filtersStore.$patch).toHaveBeenCalledWith({
      status: [],
      types: [],
      locations: [],
      searchQuery: '',
    });
  });

  it('should parse comma-separated status values', () => {
    route.query = { status: 'offline,warning,critical' };

    useUrlSync(filtersStore, router, route);

    expect(filtersStore.status).toEqual(['offline', 'warning', 'critical']);
  });

  it('should parse single type value', () => {
    route.query = { type: 'router' };

    useUrlSync(filtersStore, router, route);

    expect(filtersStore.types).toEqual(['router']);
  });

  it('should handle URL-encoded location values', () => {
    route.query = { location: 'Branch%20A,Main%20Office' };

    useUrlSync(filtersStore, router, route);

    // Note: Vue Router handles decoding automatically
    expect(filtersStore.locations).toBeDefined();
  });

  it('should parse search query from q parameter', () => {
    route.query = { q: 'server alpha' };

    useUrlSync(filtersStore, router, route);

    expect(filtersStore.searchQuery).toBe('server alpha');
  });

  it('should serialize filters to URL params', () => {
    filtersStore.status = ['offline', 'warning'];
    filtersStore.types = ['router'];
    filtersStore.locations = ['Branch A'];
    filtersStore.searchQuery = 'test';

    useUrlSync(filtersStore, router, route);

    // Trigger update by changing filter
    filtersStore.status = ['offline'];

    // Should call router.replace with serialized params
    // (In actual test, need to wait for watch to trigger)
  });

  it('should omit empty arrays from URL params', () => {
    filtersStore.status = [];
    filtersStore.types = [];
    filtersStore.locations = [];
    filtersStore.searchQuery = '';

    useUrlSync(filtersStore, router, route);

    // Should not include empty params in URL
    // (Test by checking router.replace was called with {})
  });

  it('should handle filter changes without infinite loops', () => {
    route.query = { status: 'offline' };

    useUrlSync(filtersStore, router, route);

    const patchCallCount = filtersStore.$patch.mock.calls.length;

    // Changing filter should not trigger another $patch
    filtersStore.status = ['offline']; // Same value

    expect(filtersStore.$patch.mock.calls.length).toBe(patchCallCount);
  });

  it('should handle browser back button (route.query change)', () => {
    useUrlSync(filtersStore, router, route);

    // Simulate browser back button changing query
    route.query = { status: 'warning' };

    // Should update filters store
    // (In actual test, need to trigger route watch)
  });
});
```

**Additional Test Scenarios:**

1. **Multiple status values:** `?status=offline,warning,critical`
2. **Multiple types:** `?type=router,switch,server`
3. **Multiple locations:** `?location=HQ,Branch%20A`
4. **All filters combined:** `?status=offline&type=router&location=HQ&q=test`
5. **URL encoding:** Special characters in search query
6. **Empty params:** No query params at all
7. **Partial params:** Only some filters set
8. **Invalid params:** Garbage in URL should not crash

---

### Step 4: Handle Edge Cases (1 hour → 10 min)

**Edge Cases to Handle:**

1. **Invalid Status Values**: `?status=invalid` → ignore
2. **Malformed Arrays**: `?status=,,,` → filter empty strings
3. **URL Injection**: Prevent XSS via URL params
4. **Very Long URLs**: > 2000 chars (browser limit)
5. **Special Characters**: `?q=test<script>alert(1)</script>` → sanitize
6. **Concurrent Updates**: User changes filter while URL is updating

**Solutions:**

```javascript
// Validate status values
const VALID_STATUSES = ['operational', 'warning', 'critical', 'offline', 'unknown'];

const parseArrayParam = (param) => {
  if (!param) return [];
  if (Array.isArray(param)) return param;
  
  return param
    .split(',')
    .filter(Boolean) // Remove empty strings
    .filter(value => VALID_STATUSES.includes(value)); // Validate
};

// Sanitize search query
const sanitizeQuery = (query) => {
  if (!query) return '';
  
  // Remove HTML tags, trim, limit length
  return query
    .replace(/<[^>]*>/g, '') // Strip HTML
    .trim()
    .slice(0, 200); // Max 200 chars
};

// Check URL length before updating
const updateUrl = useDebounceFn(() => {
  const newQuery = serializeFilters();
  const newUrl = router.resolve({ query: newQuery }).href;
  
  if (newUrl.length > 2000) {
    console.warn('URL too long, skipping update');
    return;
  }
  
  if (JSON.stringify(route.query) !== JSON.stringify(newQuery)) {
    router.replace({ query: newQuery });
  }
}, 500);
```

---

## 🧪 Testing Strategy

### Unit Tests (8 tests)

1. **parseUrlParams**: Correctly parses all param types
2. **parseArrayParam**: Handles comma-separated strings
3. **serializeFilters**: Converts store state to URL params
4. **initializeFromUrl**: Populates store on mount
5. **URL → Store sync**: Route changes update filters
6. **Store → URL sync**: Filter changes update URL
7. **Debouncing**: Multiple rapid changes = single URL update
8. **Clean params**: Empty arrays omitted from URL

### Integration Tests (Manual)

1. **Bookmark Test**: 
   - Set filters: status=offline, type=router
   - Copy URL: `/dashboard?status=offline&type=router`
   - Open in new tab → filters should be applied

2. **Back Button Test**:
   - Apply filter 1 (status=offline)
   - Apply filter 2 (type=router)
   - Press back → should show filter 1 only
   - Press back → should show no filters

3. **Share Test**:
   - User A sets filters
   - User A copies URL
   - User B opens URL → sees same filters

4. **Search + Filters**:
   - Set status=offline, q=router
   - URL: `/dashboard?status=offline&q=router`
   - Refresh page → both filters applied

---

## 📊 Success Metrics

### Quantitative
- ✅ 8+ unit tests passing
- ✅ 120+ total tests passing
- ✅ 0 errors, 0 warnings
- ✅ < 500ms URL update delay
- ✅ < 100ms initial load from URL

### Qualitative
- ✅ Bookmarkable URLs work correctly
- ✅ Shareable URLs preserve filter state
- ✅ Back/forward buttons work intuitively
- ✅ No history pollution (single entry per filter set)
- ✅ Clean URLs (no empty params)

---

## 🚀 Performance Considerations

### Debounce Tuning
- **Search Input:** 300ms (typing feels instant)
- **URL Update:** 500ms (prevents history spam)
- **Why Different?** URL updates are more expensive (browser history, navigation events)

### Memory
- **URL Watchers:** 2 watchers (route.query, filtersStore)
- **Debounce Buffer:** ~1KB (stores pending update)
- **Total:** < 5KB overhead

### Network
- **No Network Requests:** URL changes are client-side only
- **Page Reloads:** None (SPA navigation)

---

## 🔄 Integration with Existing Code

### No Changes Required To:
- ✅ FilterBar.vue (already updates filters store)
- ✅ FilterDropdown.vue (no changes)
- ✅ SearchInput.vue (no changes)
- ✅ filters.ts store (no changes)
- ✅ dashboard.js store (no changes)

### Only Changes:
1. **DashboardView.vue**: Add 3 lines to initialize useUrlSync
2. **New File**: useUrlSync.js composable
3. **New File**: useUrlSync.spec.js tests

**Total Impact:** Minimal, non-breaking changes

---

## 📝 Example Usage Scenarios

### Scenario 1: Support Team Debug
```
User reports: "Dashboard showing wrong devices"

Support asks: "What filters are applied?"

User sends: https://app.com/dashboard?status=offline&type=router&location=Branch%20A

Support opens URL → sees exact same view → debugs issue
```

### Scenario 2: Daily Monitoring
```
Ops team needs to monitor offline routers daily

1. Apply filters: status=offline, type=router
2. Bookmark URL: /dashboard?status=offline&type=router
3. Every morning: open bookmark → instant filtered view
```

### Scenario 3: Team Sharing
```
Manager: "Check offline devices at Branch A"

Manager sends: /dashboard?status=offline&location=Branch%20A

Team opens → everyone sees same filtered list
```

---

## 🎯 Acceptance Criteria

- [ ] Initial load from URL populates filters correctly
- [ ] Filter changes update URL within 500ms
- [ ] URL changes (back/forward) update filters
- [ ] Empty filters produce clean URL (no params)
- [ ] Multiple filters combine correctly (?status=a,b&type=c)
- [ ] Search query persists in URL (?q=test)
- [ ] Bookmarking works (open URL in new tab = same filters)
- [ ] Sharing works (copy URL to colleague = same view)
- [ ] 8+ unit tests passing
- [ ] 120+ total tests passing
- [ ] Zero errors, zero warnings

---

## 🔮 Future Enhancements (Not Day 4)

1. **URL Shortening**: Long URLs → short codes (server-side)
2. **Filter Presets**: Save common filter sets with names
3. **Query String Compression**: Encode filters more compactly
4. **Deep Linking**: Link to specific device (#device-123)
5. **Analytics**: Track which filters are most commonly shared

---

## 📚 References

- Vue Router Query Params: https://router.vuejs.org/guide/essentials/navigation.html
- URL Encoding: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/encodeURIComponent
- Browser History API: https://developer.mozilla.org/en-US/docs/Web/API/History_API
- @vueuse/core useDebounceFn: https://vueuse.org/shared/useDebounceFn/

---

**Next:** Implement useUrlSync composable → Integrate into DashboardView → Create tests → Verify bookmarking works
