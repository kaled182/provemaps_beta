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
  // Valid status values (prevent URL injection)
  const STATUS_ALIASES = {
    operational: 'online',
    online: 'online',
    operational_up: 'online',
    critical: 'offline',
    down: 'offline',
    offline: 'offline',
    degraded: 'degraded',
    warning: 'warning',
    maintenance: 'maintenance',
    unknown: 'unknown',
  };

  const VALID_STATUSES = Object.values(STATUS_ALIASES).filter((value, index, self) => self.indexOf(value) === index);

  // Parse comma-separated string to array with validation
  const parseArrayParam = (param, validValues = null) => {
    if (!param) return [];
    const normalize = value => STATUS_ALIASES[value] ?? value;
    if (Array.isArray(param)) {
      const normalized = param.map(normalize);
      return validValues ? normalized.filter(v => validValues.includes(v)) : normalized;
    }
    
    const values = param
      .split(',')
      .map(value => value.trim())
      .filter(Boolean)
      .map(value => STATUS_ALIASES[value] ?? value);
    
    // Validate if validation array provided
    if (validValues) {
      return values.filter(v => validValues.includes(v));
    }
    
    return values;
  };

  // Sanitize search query (prevent XSS)
  const sanitizeQuery = (query) => {
    if (!query) return '';
    
    return query
      .replace(/<[^>]*>?/gm, '') // Strip HTML tags (global, multiline)
      .trim()
      .slice(0, 200); // Max 200 chars
  };

  // Parse URL params to filter values
  const parseUrlParams = (query) => {
    return {
      status: parseArrayParam(query.status, VALID_STATUSES),
      types: parseArrayParam(query.type), // No validation for types (dynamic)
      locations: parseArrayParam(query.location), // No validation for locations (dynamic)
      searchQuery: sanitizeQuery(query.q || ''),
    };
  };

  // Serialize filters to URL params (omit empty values)
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

  // Check if two query objects are equal
  const queriesEqual = (q1, q2) => {
    return JSON.stringify(q1) === JSON.stringify(q2);
  };

  // Check if filters have changed
  const filtersChanged = (newFilters) => {
    return (
      JSON.stringify(newFilters.status) !== JSON.stringify(filtersStore.status) ||
      JSON.stringify(newFilters.types) !== JSON.stringify(filtersStore.types) ||
      JSON.stringify(newFilters.locations) !== JSON.stringify(filtersStore.locations) ||
      newFilters.searchQuery !== filtersStore.searchQuery
    );
  };

  // Update URL (debounced to prevent history pollution)
  const updateUrl = useDebounceFn(() => {
    const newQuery = serializeFilters();
    
    // Check URL length (browser limit ~2000 chars)
    const newUrl = router.resolve({ query: newQuery }).href;
    if (newUrl.length > 2000) {
      console.warn('[useUrlSync] URL too long, skipping update:', newUrl.length, 'chars');
      return;
    }
    
    // Only update if query actually changed
    if (!queriesEqual(route.query, newQuery)) {
      router.replace({ query: newQuery });
    }
  }, 500); // 500ms debounce (longer than search to prevent history spam)

  // Initialize filters from URL on mount
  const initializeFromUrl = () => {
    const filters = parseUrlParams(route.query);
    
    // Update store without triggering watchers
    filtersStore.$patch(filters);
  };

  // Watch filters store changes → update URL
  watch(
    () => ({
      status: [...filtersStore.status],
      types: [...filtersStore.types],
      locations: [...filtersStore.locations],
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
      if (filtersChanged(filters)) {
        filtersStore.$patch(filters);
      }
    }
  );

  // Run initialization
  initializeFromUrl();
}
