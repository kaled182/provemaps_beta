import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import StatusChart from '@/components/Dashboard/StatusChart.vue';

describe('StatusChart', () => {
  it('renders chart with distribution', () => {
    const distribution = {
      online: 5,
      offline: 2,
      warning: 1,
      unknown: 0,
    };

    const wrapper = mount(StatusChart, {
      props: { distribution },
    });

    expect(wrapper.text()).toContain('Status dos Hosts');
    expect(wrapper.text()).toContain('Online');
    expect(wrapper.text()).toContain('5');
  });

  it('calculates total correctly', () => {
    const distribution = {
      online: 3,
      offline: 2,
      warning: 1,
      unknown: 1,
    };

    const wrapper = mount(StatusChart, {
      props: { distribution },
    });

    expect(wrapper.text()).toContain('Total:');
    expect(wrapper.text()).toContain('7');
  });

  it('calculates health percentage', () => {
    const distribution = {
      online: 8,
      offline: 2,
      warning: 0,
      unknown: 0,
    };

    const wrapper = mount(StatusChart, {
      props: { distribution },
    });

    expect(wrapper.text()).toContain('Saúde:');
    expect(wrapper.text()).toContain('80%');
  });

  it('applies health class based on percentage', async () => {
    const wrapper = mount(StatusChart, {
      props: {
        distribution: {
          online: 9,
          offline: 1,
          warning: 0,
          unknown: 0,
        },
      },
    });

    // 90% health should be "good"
    expect(wrapper.find('.health-good').exists()).toBe(true);

    // Update to warning level
    await wrapper.setProps({
      distribution: {
        online: 6,
        offline: 4,
        warning: 0,
        unknown: 0,
      },
    });

    // 60% health should be "warning"
    expect(wrapper.find('.health-warning').exists()).toBe(true);

    // Update to critical level
    await wrapper.setProps({
      distribution: {
        online: 3,
        offline: 7,
        warning: 0,
        unknown: 0,
      },
    });

    // 30% health should be "critical"
    expect(wrapper.find('.health-critical').exists()).toBe(true);
  });

  it('handles empty distribution', () => {
    const wrapper = mount(StatusChart, {
      props: {
        distribution: {
          online: 0,
          offline: 0,
          warning: 0,
          unknown: 0,
        },
      },
    });

    expect(wrapper.text()).toContain('Total:');
    expect(wrapper.text()).toContain('0');
  });
});
