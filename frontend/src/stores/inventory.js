import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

/**
 * Inventory store for Sites, Devices, Ports, and site-device selection modal.
 */
export const useInventoryStore = defineStore('inventory', () => {
  const sites = ref([]);
  const devices = ref([]);
  const ports = ref([]);
  const loading = ref(false);
  const error = ref(null);

  // Site modal state
  const isSiteModalOpen = ref(false);
  const isLoadingSiteDevices = ref(false);
  const currentSiteId = ref(null);
  const currentSiteName = ref('');
  const currentSiteCity = ref('');
  const currentSiteLatitude = ref(null);
  const currentSiteLongitude = ref(null);
  const currentSiteDevices = ref([]);
  const siteDevicesError = ref(null);

  // Computed helpers
  const totalSites = computed(() => sites.value.length);
  const totalDevices = computed(() => devices.value.length);
  const totalPorts = computed(() => ports.value.length);

  const currentSiteMeta = computed(() => {
    if (!currentSiteId.value) {
      return null;
    }
    return {
      id: currentSiteId.value,
      name: currentSiteName.value,
      city: currentSiteCity.value,
      latitude: currentSiteLatitude.value,
      longitude: currentSiteLongitude.value,
      device_count: currentSiteDevices.value.length,
    };
  });

  function normalizeSitePayload(site) {
    if (!site || typeof site !== 'object') {
      return site;
    }
    const deviceCount = Number(site.device_count ?? site.devices_count ?? 0);
    return {
      ...site,
      device_count: Number.isNaN(deviceCount) ? 0 : deviceCount,
    };
  }

  function parseJsonList(payload) {
    if (Array.isArray(payload)) {
      return payload;
    }
    if (Array.isArray(payload?.results)) {
      return payload.results;
    }
    return [];
  }

  async function fetchSites() {
    loading.value = true;
    error.value = null;
    try {
      const response = await fetch('/api/v1/sites/?page_size=500', {
        credentials: 'include',
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      const siteList = parseJsonList(data).map(normalizeSitePayload);
      sites.value = siteList;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      error.value = message;
      console.error('[inventoryStore] Failed to fetch sites:', err);
    } finally {
      loading.value = false;
    }
  }

  async function fetchDevices() {
    loading.value = true;
    error.value = null;
    try {
      const response = await fetch('/api/v1/devices/', {
        credentials: 'include',
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      devices.value = parseJsonList(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      error.value = message;
      console.error('[inventoryStore] Failed to fetch devices:', err);
    } finally {
      loading.value = false;
    }
  }

  async function fetchPorts() {
    loading.value = true;
    error.value = null;
    try {
      const response = await fetch('/api/v1/ports/', {
        credentials: 'include',
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      ports.value = parseJsonList(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      error.value = message;
      console.error('[inventoryStore] Failed to fetch ports:', err);
    } finally {
      loading.value = false;
    }
  }

  async function fetchSiteDevices(siteId, { force = false } = {}) {
    const normalizedId = Number(siteId);
    if (!normalizedId) {
      console.warn('[inventoryStore] fetchSiteDevices called with invalid siteId', siteId);
      return { site: null, devices: [] };
    }

    if (
      !force &&
      currentSiteId.value === normalizedId &&
      currentSiteDevices.value.length > 0
    ) {
      return {
        site: currentSiteMeta.value,
        devices: currentSiteDevices.value,
      };
    }

    isLoadingSiteDevices.value = true;
    siteDevicesError.value = null;

    try {
      console.debug('[inventoryStore] Fetching devices for site', normalizedId, { force });
      const response = await fetch(`/api/v1/sites/${normalizedId}/devices/`, {
        credentials: 'include',
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      console.debug('[inventoryStore] /sites/{id}/devices payload', data);
      const devicesList = Array.isArray(data?.devices) ? data.devices : [];
      console.debug('[inventoryStore] devicesList length', devicesList.length);

      currentSiteId.value = normalizedId;
      currentSiteName.value = data.site_name || data.name || '';
      currentSiteCity.value = data.site_city || data.city || '';

      const latRaw = data.latitude ?? data.site_latitude ?? null;
      const lngRaw = data.longitude ?? data.site_longitude ?? null;
      currentSiteLatitude.value = latRaw !== null ? Number(latRaw) : null;
      currentSiteLongitude.value = lngRaw !== null ? Number(lngRaw) : null;

      currentSiteDevices.value = devicesList;

      const sitePayload = {
        id: normalizedId,
        name: currentSiteName.value,
        city: currentSiteCity.value,
        latitude: currentSiteLatitude.value,
        longitude: currentSiteLongitude.value,
        device_count: devicesList.length,
      };

      console.debug('[inventoryStore] Final site payload', sitePayload);
      return { site: sitePayload, devices: devicesList };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      siteDevicesError.value = message;
      currentSiteDevices.value = [];
      console.error('[inventoryStore] Failed to fetch site devices:', err);
      return { site: null, devices: [] };
    } finally {
      isLoadingSiteDevices.value = false;
    }
  }

  async function selectSite(site) {
    if (!site) {
      return { mode: 'none', site: null, device: null };
    }

    const siteId = Number(site.id ?? site.site_id);
    if (!siteId) {
      return { mode: 'none', site: null, device: null };
    }

    console.debug('[inventoryStore] selectSite start', siteId);
    const { site: siteMeta, devices: devicesList } = await fetchSiteDevices(siteId);
    console.debug('[inventoryStore] selectSite devices length', devicesList.length);
    const deviceCount = devicesList.length;

    if (deviceCount <= 0) {
      isSiteModalOpen.value = true;
      return { mode: 'empty', site: siteMeta, device: null };
    }

    if (deviceCount === 1) {
      isSiteModalOpen.value = false;
      return { mode: 'single', site: siteMeta, device: devicesList[0] };
    }

    console.debug('[inventoryStore] Opening modal for multi device site', siteId);
    isSiteModalOpen.value = true;
    return { mode: 'modal', site: siteMeta, device: null };
  }

  function closeSiteModal() {
    isSiteModalOpen.value = false;
  }

  return {
    // State
    sites,
    devices,
    ports,
    loading,
    error,
    isSiteModalOpen,
    isLoadingSiteDevices,
    currentSiteId,
    currentSiteName,
    currentSiteCity,
    currentSiteLatitude,
    currentSiteLongitude,
    currentSiteDevices,
    siteDevicesError,

    // Computed
    totalSites,
    totalDevices,
    totalPorts,
    currentSiteMeta,

    // Actions
    fetchSites,
    fetchDevices,
    fetchPorts,
    fetchSiteDevices,
    selectSite,
    closeSiteModal,
  };
});
