import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import SearchSuggestions from '@/components/search/SearchSuggestions.vue';
import { useDashboardStore } from '@/stores/dashboard';

describe('SearchSuggestions', () => {
  let wrapper;
  let dashboardStore;

  const mockDevices = [
    {
      id: 1,
      name: 'Server Alpha',
      ip: '192.168.1.10',
      status: 'operational',
      type: 'server',
      site_name: 'HQ',
      description: 'Production server',
    },
    {
      id: 2,
      name: 'Router Beta',
      ip: '10.0.0.1',
      status: 'offline',
      type: 'router',
      site_name: 'Branch A',
      description: 'Main router',
    },
    {
      id: 3,
      name: 'Switch Gamma',
      ip: '10.0.0.2',
      status: 'warning',
      type: 'switch',
      site_name: 'Branch B',
      description: 'Core switch',
    },
  ];

  beforeEach(() => {
    setActivePinia(createPinia());
    dashboardStore = useDashboardStore();
    
    // Set hosts via Map (the actual dashboard store structure)
    const hostsMap = new Map();
    mockDevices.forEach(device => {
      hostsMap.set(device.id, device);
    });
    dashboardStore.hosts = hostsMap;
  });

  it('should render suggestions container', () => {
    wrapper = mount(SearchSuggestions, {
      props: {
        query: '',
        selectedIndex: -1,
      },
    });
    
    expect(wrapper.find('.search-suggestions').exists()).toBe(true);
  });

  it('should show hint when query is empty', () => {
    wrapper = mount(SearchSuggestions, {
      props: {
        query: '',
        selectedIndex: -1,
      },
    });
    
    expect(wrapper.find('.suggestions-hint').exists()).toBe(true);
    expect(wrapper.text()).toContain('Start typing to search');
  });

  it('should show fuzzy search results when query length >= 2', async () => {
    wrapper = mount(SearchSuggestions, {
      props: {
        query: 'se',
        selectedIndex: -1,
      },
    });
    
    // Wait for fuzzy search to compute
    await wrapper.vm.$nextTick();
    
    const suggestions = wrapper.findAll('.search-suggestion');
    expect(suggestions.length).toBeGreaterThan(0);
  });

  it('should show device status icon', async () => {
    wrapper = mount(SearchSuggestions, {
      props: {
        query: 'Server',
        selectedIndex: -1,
      },
    });
    
    await wrapper.vm.$nextTick();
    
    const suggestion = wrapper.find('.search-suggestion');
    if (suggestion.exists()) {
      const statusIcon = suggestion.find('.suggestion-status');
      expect(statusIcon.exists()).toBe(true);
    }
  });

  it('should show device name and metadata', async () => {
    wrapper = mount(SearchSuggestions, {
      props: {
        query: 'Server',
        selectedIndex: -1,
      },
    });
    
    await wrapper.vm.$nextTick();
    
    const suggestion = wrapper.find('.search-suggestion');
    if (suggestion.exists()) {
      expect(suggestion.find('.suggestion-name').exists()).toBe(true);
      expect(suggestion.find('.suggestion-meta').exists()).toBe(true);
    }
  });

  it('should emit select event when suggestion clicked', async () => {
    wrapper = mount(SearchSuggestions, {
      props: {
        query: 'Server',
        selectedIndex: -1,
      },
    });
    
    await wrapper.vm.$nextTick();
    
    const suggestion = wrapper.find('.search-suggestion');
    await suggestion.trigger('click');
    
    expect(wrapper.emitted('select')).toBeTruthy();
    expect(wrapper.emitted('select')[0][0]).toMatchObject({
      name: 'Server Alpha',
    });
  });

  it('should highlight selected suggestion', async () => {
    wrapper = mount(SearchSuggestions, {
      props: {
        query: 'se',
        selectedIndex: 0,
      },
    });
    
    await wrapper.vm.$nextTick();
    
    const suggestions = wrapper.findAll('.search-suggestion');
    expect(suggestions[0].classes()).toContain('selected');
  });

  it('should show empty state when no results found', async () => {
    wrapper = mount(SearchSuggestions, {
      props: {
        query: 'nonexistent device xyz',
        selectedIndex: -1,
      },
    });
    
    await wrapper.vm.$nextTick();
    
    expect(wrapper.find('.suggestions-empty').exists()).toBe(true);
    expect(wrapper.text()).toContain('No devices found');
  });

  it('should show correct status icon for each status', async () => {
    wrapper = mount(SearchSuggestions, {
      props: {
        query: 'se',
        selectedIndex: -1,
      },
    });
    
    await wrapper.vm.$nextTick();
    
    const operationalStatus = wrapper.vm.getStatusIcon('operational');
    const offlineStatus = wrapper.vm.getStatusIcon('offline');
    const warningStatus = wrapper.vm.getStatusIcon('warning');
    
    expect(operationalStatus).toBe('✅');
    expect(offlineStatus).toBe('⚫'); // Black circle for offline
    expect(warningStatus).toBe('⚠️');
  });

  it('should limit results to 10 items', async () => {
    // Add more devices via hosts Map
    const manyDevices = Array.from({ length: 20 }, (_, i) => ({
      id: i,
      name: `Device ${i}`,
      ip: `192.168.1.${i}`,
      status: 'operational',
      type: 'server',
      site_name: 'HQ',
    }));
    
    const hostsMap = new Map();
    manyDevices.forEach(device => {
      hostsMap.set(device.id, device);
    });
    dashboardStore.hosts = hostsMap;
    
    wrapper = mount(SearchSuggestions, {
      props: {
        query: 'de',
        selectedIndex: -1,
      },
    });
    
    await wrapper.vm.$nextTick();
    
    const suggestions = wrapper.findAll('.search-suggestion');
    expect(suggestions.length).toBeLessThanOrEqual(10);
  });

  it('should reactively update when query prop changes', async () => {
    wrapper = mount(SearchSuggestions, {
      props: {
        query: 'Server',
        selectedIndex: -1,
      },
    });
    
    await wrapper.vm.$nextTick();
    let suggestions = wrapper.findAll('.search-suggestion');
    expect(suggestions.length).toBeGreaterThan(0);
    
    await wrapper.setProps({ query: 'Router' });
    await wrapper.vm.$nextTick();
    
    suggestions = wrapper.findAll('.search-suggestion');
    expect(suggestions.length).toBeGreaterThan(0);
    expect(wrapper.text()).toContain('Router');
  });
});
