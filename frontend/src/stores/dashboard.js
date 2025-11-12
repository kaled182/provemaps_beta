import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { memoize } from '@/composables/usePerformance';
import { useFiltersStore } from './filters';

/**
 * Dashboard store for host status cards and real-time updates.
 * Integrates with WebSocket for live status changes.
 * Phase 11 Sprint 1 + Sprint 3 Performance Optimization
 * Phase 13 Sprint 1 Day 2: Added filtering logic
 */
export const useDashboardStore = defineStore('dashboard', () => {
  // Host status data
  const hosts = ref(new Map()); // id -> { name, status, last_update, metrics, ... }
  const lastUpdate = ref(null);
  const loading = ref(false);
  const error = ref(null);

  // Memoized filter functions for better performance with large datasets
  const filterByStatus = memoize((hostMap, status) => {
    return Array.from(hostMap.values()).filter(h => h.status === status).length;
  });

  // Computed aggregations
  const totalHosts = computed(() => hosts.value.size);
  const onlineHosts = computed(() => filterByStatus(hosts.value, 'online'));
  const offlineHosts = computed(() => filterByStatus(hosts.value, 'offline'));
  const warningHosts = computed(() => filterByStatus(hosts.value, 'warning'));
  const unknownHosts = computed(() => {
    return Array.from(hosts.value.values())
      .filter(h => !h.status || h.status === 'unknown').length;
  });

  const statusDistribution = computed(() => ({
    online: onlineHosts.value,
    offline: offlineHosts.value,
    warning: warningHosts.value,
    unknown: unknownHosts.value,
  }));

  const hostsList = computed(() => Array.from(hosts.value.values()));

  /**
   * Filtered hosts based on active filters from filters store
   * Phase 13 Sprint 1 Day 2: Client-side filtering
   */
  const filteredHosts = computed(() => {
    const filtersStore = useFiltersStore();
    const { status, types, locations, searchQuery } = filtersStore;
    
    // Start with all hosts
    let filtered = Array.from(hosts.value.values());
    
    // Apply status filter
    if (status.length > 0) {
      filtered = filtered.filter(host => status.includes(host.status));
    }
    
    // Apply type filter
    if (types.length > 0) {
      filtered = filtered.filter(host => types.includes(host.type || host.device_type));
    }
    
    // Apply location filter
    if (locations.length > 0) {
      filtered = filtered.filter(host => {
        const locationId = String(host.site_id || host.location_id || '');
        return locations.includes(locationId);
      });
    }
    
    // Apply search query (simple contains for now, fuzzy in Day 3)
    if (searchQuery.length > 0) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(host => {
        const name = (host.name || '').toLowerCase();
        const ip = (host.ip || '').toLowerCase();
        const description = (host.description || '').toLowerCase();
        return name.includes(query) || ip.includes(query) || description.includes(query);
      });
    }
    
    return filtered;
  });

  /**
   * Extract unique locations from host data with counts
   * Phase 13 Sprint 1 Day 2: Dynamic location options
   */
  const availableLocations = computed(() => {
    const locationMap = new Map();
    
    Array.from(hosts.value.values()).forEach(host => {
      const locationId = String(host.site_id || host.location_id || '');
      const locationName = host.site_name || host.location_name || `Site ${locationId}`;
      
      if (locationId && !locationMap.has(locationId)) {
        locationMap.set(locationId, {
          value: locationId,
          label: locationName,
          count: 0,
        });
      }
      
      if (locationId) {
        const loc = locationMap.get(locationId);
        loc.count += 1;
      }
    });
    
    return Array.from(locationMap.values())
      .sort((a, b) => a.label.localeCompare(b.label));
  });

  /**
   * Fetch initial dashboard data from cached endpoint
   */
  function normalizeHost(raw) {
    if (!raw) return null;
    const availability = String(raw.available ?? raw.status ?? '').trim();
    let status = 'unknown';
    if (availability === '1') {
      status = 'online';
    } else if (availability === '2') {
      status = 'offline';
    }

    return {
      id: raw.device_id || raw.hostid || raw.id,
      host_id: raw.hostid,
      name: raw.name,
      site: raw.site,
      status,
      availability,
      availability_text: raw.available_text,
      zabbix_status: raw.status,
      status_text: raw.status_text,
      error: raw.error,
      color: raw.color,
      status_class: raw.status_class,
      interface: raw.interface || null,
      ip: raw.interface?.ip || raw.ip || null,
      last_update: raw.last_update || null,
      raw,
    };
  }

  async function fetchDashboard() {
    loading.value = true;
    error.value = null;
    try {
      const resp = await fetch('/maps_view/api/dashboard/data/', {
        credentials: 'include',
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const hostEntries = Array.isArray(data.hosts_status) ? data.hosts_status : [];
      const updatedHosts = new Map();

      hostEntries.forEach(rawHost => {
        const normalized = normalizeHost(rawHost);
        if (normalized && normalized.id) {
          updatedHosts.set(normalized.id, normalized);
        }
      });

      hosts.value = updatedHosts;
      lastUpdate.value = data.cache_metadata?.timestamp || new Date().toISOString();
    } catch (e) {
      error.value = e.message;
      console.error('[dashboardStore] Failed to fetch dashboard', e);
    } finally {
      loading.value = false;
    }
  }

  /**
   * Update host status from WebSocket message
   * Expected format: { type: 'host_update', host_id: 123, status: 'online', ... }
   */
  function updateHostFromWebSocket(message) {
    if (!message || message.type !== 'host_update') return;

    const { host_id, ...updates } = message;
    if (!host_id) return;

    const existing = hosts.value.get(host_id);
    if (existing) {
      hosts.value.set(host_id, { ...existing, ...updates });
    } else {
      // New host appeared
      hosts.value.set(host_id, { id: host_id, ...updates });
    }
    lastUpdate.value = new Date().toISOString();
  }

  /**
   * Batch update multiple hosts (e.g., from full dashboard snapshot)
   * Expected format: { type: 'dashboard_snapshot', hosts: [...] }
   */
  function updateDashboardSnapshot(message) {
    if (!message || message.type !== 'dashboard_snapshot') return;
    if (!message.hosts || !Array.isArray(message.hosts)) return;

    message.hosts.forEach(host => {
      hosts.value.set(host.id, host);
    });
    lastUpdate.value = new Date().toISOString();
  }

  /**
   * Generic update handler for WebSocket messages
   */
  function handleWebSocketMessage(message) {
    if (!message) return;
    
    switch (message.type) {
      case 'host_update':
        updateHostFromWebSocket(message);
        break;
      case 'dashboard_snapshot':
        updateDashboardSnapshot(message);
        break;
      default:
        console.warn('[dashboardStore] Unknown message type:', message.type);
    }
  }

  /**
   * Clear all hosts (useful for logout/reset)
   */
  function clearHosts() {
    hosts.value.clear();
    lastUpdate.value = null;
  }

  return {
    // State
    hosts,
    lastUpdate,
    loading,
    error,
    
    // Computed
    totalHosts,
    onlineHosts,
    offlineHosts,
    warningHosts,
    unknownHosts,
    statusDistribution,
    hostsList,
    filteredHosts,
    availableLocations,
    
    // Actions
    fetchDashboard,
    updateHostFromWebSocket,
    updateDashboardSnapshot,
    handleWebSocketMessage,
    clearHosts,
  };
});
