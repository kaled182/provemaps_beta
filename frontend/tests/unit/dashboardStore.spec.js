import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useDashboardStore } from '@/stores/dashboard';

describe('dashboardStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('initializes with empty state', () => {
    const store = useDashboardStore();
    expect(store.totalHosts).toBe(0);
    expect(store.onlineHosts).toBe(0);
    expect(store.loading).toBe(false);
  });

  it('updates host from WebSocket message', () => {
    const store = useDashboardStore();
    
    const message = {
      type: 'host_update',
      host_id: 1,
      name: 'Host1',
      status: 'online',
    };
    
    store.updateHostFromWebSocket(message);
    
    expect(store.totalHosts).toBe(1);
    expect(store.onlineHosts).toBe(1);
    expect(store.hosts.get(1)).toMatchObject({ id: 1, name: 'Host1', status: 'online' });
  });

  it('updates dashboard snapshot', () => {
    const store = useDashboardStore();
    
    const snapshot = {
      type: 'dashboard_snapshot',
      hosts: [
        { id: 1, name: 'H1', status: 'online' },
        { id: 2, name: 'H2', status: 'offline' },
        { id: 3, name: 'H3', status: 'warning' },
      ],
    };
    
    store.updateDashboardSnapshot(snapshot);
    
    expect(store.totalHosts).toBe(3);
    expect(store.onlineHosts).toBe(1);
    expect(store.offlineHosts).toBe(1);
    expect(store.warningHosts).toBe(1);
  });

  it('computes status distribution correctly', () => {
    const store = useDashboardStore();
    
    store.updateDashboardSnapshot({
      type: 'dashboard_snapshot',
      hosts: [
        { id: 1, status: 'online' },
        { id: 2, status: 'online' },
        { id: 3, status: 'offline' },
        { id: 4, status: 'warning' },
        { id: 5, status: 'unknown' },
      ],
    });
    
    expect(store.statusDistribution).toEqual({
      online: 2,
      offline: 1,
      warning: 1,
      unknown: 1,
    });
  });

  it('handles generic WebSocket messages', () => {
    const store = useDashboardStore();
    
    store.handleWebSocketMessage({
      type: 'host_update',
      host_id: 10,
      status: 'online',
    });
    
    expect(store.totalHosts).toBe(1);
  });

  it('clears hosts', () => {
    const store = useDashboardStore();
    
    store.updateHostFromWebSocket({
      type: 'host_update',
      host_id: 1,
      status: 'online',
    });
    
    expect(store.totalHosts).toBe(1);
    
    store.clearHosts();
    
    expect(store.totalHosts).toBe(0);
    expect(store.lastUpdate).toBe(null);
  });

  it('fetches dashboard from API', async () => {
    const store = useDashboardStore();
    
    // Mock fetch
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          hosts: [
            { id: 1, name: 'HostA', status: 'online' },
            { id: 2, name: 'HostB', status: 'offline' },
          ],
        }),
      })
    );
    
    await store.fetchDashboard();
    
    expect(store.totalHosts).toBe(2);
    expect(store.loading).toBe(false);
    expect(store.error).toBe(null);
  });
});
