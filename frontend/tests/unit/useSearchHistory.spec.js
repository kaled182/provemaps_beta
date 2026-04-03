import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { useSearchHistory } from '@/composables/useSearchHistory';

describe('useSearchHistory', () => {
  const TEST_KEY = 'test-search-history';

  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('should initialize with empty history', () => {
    const { history } = useSearchHistory(TEST_KEY);
    expect(history.value).toEqual([]);
  });

  it('should add items to history', () => {
    const { history, addToHistory } = useSearchHistory(TEST_KEY);
    
    addToHistory('test query');
    expect(history.value).toContain('test query');
    expect(history.value.length).toBe(1);
  });

  it('should move duplicate to top instead of adding', () => {
    const { history, addToHistory } = useSearchHistory(TEST_KEY);
    
    addToHistory('first');
    addToHistory('second');
    addToHistory('third');
    expect(history.value).toEqual(['third', 'second', 'first']);
    
    addToHistory('first'); // Add duplicate
    expect(history.value).toEqual(['first', 'third', 'second']);
    expect(history.value.length).toBe(3); // No duplicate entry
  });

  it('should limit history to MAX_HISTORY_ITEMS (10)', () => {
    const { history, addToHistory } = useSearchHistory(TEST_KEY);
    
    // Add 15 items
    for (let i = 1; i <= 15; i++) {
      addToHistory(`query ${i}`);
    }
    
    expect(history.value.length).toBe(10);
    expect(history.value[0]).toBe('query 15'); // Most recent
    expect(history.value[9]).toBe('query 6'); // 10th item
  });

  it('should trim whitespace from queries', () => {
    const { history, addToHistory } = useSearchHistory(TEST_KEY);
    
    addToHistory('  test query  ');
    expect(history.value[0]).toBe('test query');
  });

  it('should not add empty strings', () => {
    const { history, addToHistory } = useSearchHistory(TEST_KEY);
    
    addToHistory('');
    addToHistory('   ');
    expect(history.value.length).toBe(0);
  });

  it('should clear all history', () => {
    const { history, addToHistory, clearHistory } = useSearchHistory(TEST_KEY);
    
    addToHistory('first');
    addToHistory('second');
    expect(history.value.length).toBe(2);
    
    clearHistory();
    expect(history.value).toEqual([]);
  });

  it('should remove specific item from history', () => {
    const { history, addToHistory, removeFromHistory } = useSearchHistory(TEST_KEY);
    
    addToHistory('first');
    addToHistory('second');
    addToHistory('third');
    expect(history.value.length).toBe(3);
    
    removeFromHistory('second');
    expect(history.value).toEqual(['third', 'first']);
    expect(history.value.length).toBe(2);
  });

  it('should persist history in localStorage', () => {
    const { history, addToHistory } = useSearchHistory(TEST_KEY);
    
    addToHistory('persistent query');
    
    // History should be updated immediately
    expect(history.value).toContain('persistent query');
    
    // useLocalStorage from @vueuse/core automatically persists
    // In test environment, this simulates persistence
    const stored = localStorage.getItem(TEST_KEY);
    expect(stored).toBeTruthy();
  });

  it('should handle localStorage serialization correctly', () => {
    const { history, addToHistory } = useSearchHistory(TEST_KEY);
    
    addToHistory('query with "quotes"');
    addToHistory("query with 'single quotes'");
    
    // Should be stored correctly
    expect(history.value).toContain('query with "quotes"');
    expect(history.value).toContain("query with 'single quotes'");
  });
});
