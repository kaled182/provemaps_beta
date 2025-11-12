import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import HostCard from '@/components/Dashboard/HostCard.vue';

describe('HostCard', () => {
  it('renders host name and status', () => {
    const host = {
      id: 1,
      name: 'Test Host',
      status: 'online',
    };

    const wrapper = mount(HostCard, {
      props: { host },
    });

    expect(wrapper.text()).toContain('Test Host');
    expect(wrapper.text()).toContain('Online');
  });

  it('applies correct status class', () => {
    const host = {
      id: 1,
      name: 'Test',
      status: 'offline',
    };

    const wrapper = mount(HostCard, {
      props: { host },
    });

    expect(wrapper.find('.host-card').classes()).toContain('status-offline');
  });

  it('displays metrics when available', () => {
    const host = {
      id: 1,
      name: 'Test',
      status: 'online',
      metrics: {
        cpu: 45,
        memory: 60,
      },
    };

    const wrapper = mount(HostCard, {
      props: { host },
    });

    expect(wrapper.text()).toContain('CPU');
    expect(wrapper.text()).toContain('45%');
    expect(wrapper.text()).toContain('Memória');
    expect(wrapper.text()).toContain('60%');
  });

  it('handles unknown status', () => {
    const host = {
      id: 1,
      name: 'Test',
      status: null,
    };

    const wrapper = mount(HostCard, {
      props: { host },
    });

    expect(wrapper.text()).toContain('Desconhecido');
    expect(wrapper.find('.host-card').classes()).toContain('status-unknown');
  });
});
