import { useLocalStorage } from '@vueuse/core';

/**
 * Search history management with localStorage persistence
 * Phase 13 Sprint 1 Day 3
 * 
 * @param {String} storageKey - localStorage key for history
 * @returns {Object} - { history, addToHistory, clearHistory, removeFromHistory }
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
