// frontend/tests/unit/FilterDropdown.spec.js
import { mount } from '@vue/test-utils';
import { describe, it, expect } from 'vitest';
import FilterDropdown from '@/components/filters/FilterDropdown.vue';

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
    await wrapper.find('.filter-dropdown__option').trigger('click');
    
    expect(wrapper.emitted('toggle')).toBeTruthy();
    expect(wrapper.emitted('toggle')[0]).toEqual(['opt1', true]);
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
