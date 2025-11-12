// frontend/tests/unit/FilterBar.spec.js
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { describe, it, expect, beforeEach } from 'vitest';
import FilterBar from '@/components/filters/FilterBar.vue';
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
    
    // Updated text: "1 filter active" instead of "Filters (1)"
    expect(wrapper.text()).toContain('1 filter active');
  });

  it('shows clear all button when filters active', async () => {
    const wrapper = mount(FilterBar);
    const store = useFiltersStore();
    
    store.toggleStatus('operational');
    await wrapper.vm.$nextTick();
    
    const clearButton = wrapper.find('.btn-outline');
    expect(clearButton.exists()).toBe(true);
    expect(clearButton.text()).toBe('Clear All');
  });

  it('clears all filters when clear button clicked', async () => {
    const wrapper = mount(FilterBar);
    const store = useFiltersStore();
    
    store.toggleStatus('operational');
    store.toggleType('OLT');
    await wrapper.vm.$nextTick();
    
    await wrapper.find('.btn-outline').trigger('click');
    
    expect(store.status).toEqual([]);
    expect(store.types).toEqual([]);
  });
});
