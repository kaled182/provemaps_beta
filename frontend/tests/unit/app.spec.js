import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import App from '../../src/App.vue';
import router from '../../src/router';
import { createPinia } from 'pinia';

describe('App.vue integration', () => {
  it('renders DashboardView via /dashboard route', async () => {
    const pinia = createPinia();
    router.push('/dashboard');
    await router.isReady();
    const wrapper = mount(App, {
      global: { plugins: [pinia, router] }
    });
    // Expect DashboardView container (MapView is lazy loaded)
    expect(wrapper.html()).toMatch(/dashboard-container|dashboard-header/);
  });
});
