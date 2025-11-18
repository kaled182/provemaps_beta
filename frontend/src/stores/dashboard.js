import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
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
  
  // Fiber cables data
  const fiberCables = ref(new Map()); // id -> { name, status, origin, destination, ... }
  const fibersLoading = ref(false);
  const fibersError = ref(null);

  const filterByStatus = (hostMap, status) => {
    if (!(hostMap instanceof Map)) return 0;
    let count = 0;
    hostMap.forEach((h) => {
      if (h?.status === status) count += 1;
    });
    return count;
  };

  // Computed aggregations
  const hostMapSafe = () => {
    if (hosts.value instanceof Map) return hosts.value;
    const fresh = new Map();
    hosts.value = fresh;
    return fresh;
  };

  const fiberMapSafe = () => {
    if (fiberCables.value instanceof Map) return fiberCables.value;
    const fresh = new Map();
    fiberCables.value = fresh;
    return fresh;
  };

  const totalHosts = computed(() => hostMapSafe().size);
  const onlineHosts = computed(() => filterByStatus(hostMapSafe(), 'online'));
  const offlineHosts = computed(() => filterByStatus(hostMapSafe(), 'offline'));
  const warningHosts = computed(() => filterByStatus(hostMapSafe(), 'warning'));
  const unknownHosts = computed(() => {
    return Array.from(hostMapSafe().values())
      .filter(h => !h.status || h.status === 'unknown').length;
  });

  const statusDistribution = computed(() => ({
    online: onlineHosts.value,
    offline: offlineHosts.value,
    warning: warningHosts.value,
    unknown: unknownHosts.value,
  }));
  
  // Fiber status distribution
  const fiberStatusDistribution = computed(() => {
    try {
      const distribution = { up: 0, down: 0, degraded: 0, unknown: 0 };
      const cablesMap = fiberMapSafe();
      const cables = Array.from(cablesMap?.values ? cablesMap.values() : []);
      console.log('[dashboardStore] Computing fiber distribution, cables count:', cables.length);
      cables.forEach(cable => {
        const status = cable?.status || 'unknown';
        console.log('[dashboardStore] Cable:', cable?.name, 'Status:', status);
        if (Object.prototype.hasOwnProperty.call(distribution, status)) {
          distribution[status]++;
        } else {
          distribution.unknown++;
        }
      });
      console.log('[dashboardStore] Fiber distribution:', distribution);
      return distribution;
    } catch (error) {
      console.error('[dashboardStore] Failed to compute fiber distribution', error);
      return { up: 0, down: 0, degraded: 0, unknown: 0 };
    }
  });

  const hostsList = computed(() => Array.from(hostMapSafe().values()));

  /**
   * Filtered hosts based on active filters from filters store
   * Phase 13 Sprint 1 Day 2: Client-side filtering
   */
  const filteredHosts = computed(() => {
    const filtersStore = useFiltersStore();
    const { status, types, locations, searchQuery } = filtersStore;
    
    // Start with all hosts
    let filtered = Array.from(hostMapSafe().values());
    
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
    
    Array.from(hostMapSafe().values()).forEach(host => {
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
   * Extract unique device types from host data with counts
   * Only shows types that exist in the current dataset
   */
  const availableTypes = computed(() => {
    const typeMap = new Map();
    
    Array.from(hostMapSafe().values()).forEach(host => {
      const deviceType = host.device_type;
      
      if (deviceType && !typeMap.has(deviceType)) {
        typeMap.set(deviceType, {
          value: deviceType,
          label: deviceType,
          count: 0,
        });
      }
      
      if (deviceType) {
        const type = typeMap.get(deviceType);
        type.count += 1;
      }
    });
    
    return Array.from(typeMap.values())
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
      site_id: raw.site_id,
      site_name: raw.site_name,
      device_type: raw.device_type || null,
      status,
      availability,
      availability_text: raw.available_text,
      zabbix_status: raw.status,
      status_text: raw.status_text,
      error: raw.error,
      color: raw.color,
      status_class: raw.status_class,
      interface: raw.interface || null,
      ip: raw.interface?.ip || raw.ip || raw.primary_ip || null,
      primary_ip: raw.primary_ip || raw.interface?.ip || raw.ip || null,
      uptime_value: raw.uptime_value || null,
      cpu_value: raw.cpu_value || null,
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
   * Fetch fiber cables data
   */
  async function fetchFiberCables() {
    fibersLoading.value = true;
    fibersError.value = null;
    try {
      console.log('[dashboardStore] Fetching fiber cables...');
      const resp = await fetch('/api/v1/inventory/fibers/', {
        credentials: 'include',
      });
      console.log('[dashboardStore] Fiber cables response status:', resp.status);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      console.log('[dashboardStore] Fiber cables data:', data);
      const cables = Array.isArray(data.cables) ? data.cables : [];
      console.log('[dashboardStore] Cables array:', cables, 'Length:', cables.length);
      const updatedCables = new Map();

      cables.forEach(cable => {
        if (cable && cable.id) {
          updatedCables.set(cable.id, cable);
        }
      });

      fiberCables.value = updatedCables;
      console.log('[dashboardStore] Fiber cables loaded:', updatedCables.size);
    } catch (e) {
      fibersError.value = e.message;
      console.error('[dashboardStore] Failed to fetch fiber cables', e);
    } finally {
      fibersLoading.value = false;
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

    const existing = hostMapSafe().get(host_id);
    if (existing) {
      hostMapSafe().set(host_id, { ...existing, ...updates });
    } else {
      // New host appeared
      hostMapSafe().set(host_id, { id: host_id, ...updates });
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
      hostMapSafe().set(host.id, host);
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
    hostMapSafe().clear();
    lastUpdate.value = null;
  }

  return {
    // State
    hosts,
    lastUpdate,
    loading,
    error,
    fiberCables,
    fibersLoading,
    fibersError,
    
    // Computed
    totalHosts,
    onlineHosts,
    offlineHosts,
    warningHosts,
    unknownHosts,
    statusDistribution,
    fiberStatusDistribution,
    hostsList,
    filteredHosts,
    availableLocations,
    availableTypes,
    
    // Actions
    fetchDashboard,
    fetchFiberCables,
    updateHostFromWebSocket,
    updateDashboardSnapshot,
    handleWebSocketMessage,
    clearHosts,
  };
});
