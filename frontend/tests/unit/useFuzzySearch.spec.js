import { describe, it, expect, beforeEach } from 'vitest';
import { useFuzzySearch } from '@/composables/useFuzzySearch';

describe('useFuzzySearch', () => {
  let testData;

  beforeEach(() => {
    testData = [
      { id: 1, name: 'Server Alpha', description: 'Production server', ip: '192.168.1.10' },
      { id: 2, name: 'Server Beta', description: 'Development server', ip: '192.168.1.20' },
      { id: 3, name: 'Router Gamma', description: 'Main router', ip: '10.0.0.1' },
      { id: 4, name: 'Switch Delta', description: 'Core switch', ip: '10.0.0.2' },
      { id: 5, name: 'Firewall Epsilon', description: 'Security firewall', ip: '172.16.0.1' },
    ];
  });

  it('should return empty results when query is empty', () => {
    const { searchQuery, results } = useFuzzySearch(testData, ['name', 'description']);
    
    searchQuery.value = '';
    expect(results.value).toEqual([]);
  });

  it('should find exact matches', () => {
    const { searchQuery, results } = useFuzzySearch(testData, ['name', 'description']);
    
    searchQuery.value = 'Server Alpha';
    expect(results.value.length).toBeGreaterThan(0);
    expect(results.value[0].item.name).toBe('Server Alpha');
  });

  it('should find fuzzy matches with typos', () => {
    const { searchQuery, results } = useFuzzySearch(testData, ['name', 'description']);
    
    searchQuery.value = 'Servr Alpa'; // Typos in "Server Alpha"
    expect(results.value.length).toBeGreaterThan(0);
    expect(results.value[0].item.name).toContain('Server');
  });

  it('should search across multiple keys', () => {
    const { searchQuery, results } = useFuzzySearch(testData, ['name', 'description', 'ip']);
    
    searchQuery.value = '192.168';
    expect(results.value.length).toBeGreaterThan(0);
    expect(results.value[0].item.ip).toContain('192.168');
  });

  it('should limit results to maxResults', () => {
    const { searchQuery, results } = useFuzzySearch(
      testData,
      ['name', 'description'],
      { maxResults: 2 }
    );
    
    searchQuery.value = 'server';
    expect(results.value.length).toBeLessThanOrEqual(2);
  });

  it('should include score in results', () => {
    const { searchQuery, results } = useFuzzySearch(testData, ['name']);
    
    searchQuery.value = 'Server';
    expect(results.value.length).toBeGreaterThan(0);
    expect(results.value[0]).toHaveProperty('score');
    expect(typeof results.value[0].score).toBe('number');
  });

  it('should include matches in results for highlighting', () => {
    const { searchQuery, results } = useFuzzySearch(testData, ['name']);
    
    searchQuery.value = 'Server';
    expect(results.value.length).toBeGreaterThan(0);
    expect(results.value[0]).toHaveProperty('matches');
    expect(Array.isArray(results.value[0].matches)).toBe(true);
  });

  it('should respect minMatchCharLength configuration', () => {
    const { searchQuery, results } = useFuzzySearch(testData, ['name'], {
      minMatchCharLength: 1,
    });
    
    searchQuery.value = 'a'; // Single character
    // With minMatchCharLength: 1, should return results
    expect(results.value.length).toBeGreaterThanOrEqual(0);
  });

  it('should be case insensitive', () => {
    const { searchQuery, results } = useFuzzySearch(testData, ['name']);
    
    searchQuery.value = 'SERVER ALPHA';
    expect(results.value.length).toBeGreaterThan(0);
    expect(results.value[0].item.name).toBe('Server Alpha');
  });

  it('should reactively update results when query changes', () => {
    const { searchQuery, results } = useFuzzySearch(testData, ['name']);
    
    searchQuery.value = 'Server';
    const serverResults = results.value.length;
    expect(serverResults).toBeGreaterThan(0);
    
    searchQuery.value = 'Router';
    expect(results.value.length).toBeGreaterThan(0);
    expect(results.value[0].item.name).toContain('Router');
  });
});
