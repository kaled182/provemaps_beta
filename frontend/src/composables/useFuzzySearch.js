import Fuse from 'fuse.js';
import { ref, computed } from 'vue';

/**
 * Fuzzy search composable using fuse.js
 * Phase 13 Sprint 1 Day 3
 * 
 * @param {Ref|Array} items - Items to search (reactive or static array)
 * @param {Array} searchKeys - Keys to search within items
 * @param {Object} options - Fuse.js configuration options
 * @returns {Object} - { searchQuery, results }
 */
export function useFuzzySearch(items, searchKeys, options = {}) {
  const searchQuery = ref('');
  
  const fuseOptions = {
    keys: searchKeys,
    threshold: options.threshold || 0.3, // 0 = perfect match, 1 = match anything
    includeScore: true,
    includeMatches: true, // For highlighting matched text
    minMatchCharLength: 2,
    ignoreLocation: true, // Don't weight matches by position
    ...options,
  };
  
  const fuse = computed(() => new Fuse(items.value || items, fuseOptions));
  
  const results = computed(() => {
    if (!searchQuery.value || searchQuery.value.length < 2) {
      return [];
    }
    
    const searchResults = fuse.value.search(searchQuery.value);
    return searchResults.slice(0, options.maxResults || 10);
  });
  
  return {
    searchQuery,
    results,
  };
}
