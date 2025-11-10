import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

/**
 * Inventory store for Sites, Devices, Ports
 * Replaces legacy dashboard.js state management (1,137 lines)
 */
export const useInventoryStore = defineStore('inventory', () => {
  const sites = ref([]);
  const devices = ref([]);
  const ports = ref([]);
  const loading = ref(false);
  const error = ref(null);

  // Computed
  const totalSites = computed(() => sites.value.length);
  const totalDevices = computed(() => devices.value.length);
  const totalPorts = computed(() => ports.value.length);

  // Actions
  async function fetchSites() {
    loading.value = true;
    error.value = null;
    try {
      const response = await fetch('/api/v1/sites/'); // DRF endpoint (to be created)
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      sites.value = await response.json();
    } catch (err) {
      error.value = err.message;
      console.error('Failed to fetch sites:', err);
    } finally {
      loading.value = false;
    }
  }

  async function fetchDevices() {
    loading.value = true;
    error.value = null;
    try {
      const response = await fetch('/api/v1/devices/');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      devices.value = await response.json();
    } catch (err) {
      error.value = err.message;
      console.error('Failed to fetch devices:', err);
    } finally {
      loading.value = false;
    }
  }

  async function fetchPorts() {
    loading.value = true;
    error.value = null;
    try {
      const response = await fetch('/api/v1/ports/');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      ports.value = await response.json();
    } catch (err) {
      error.value = err.message;
      console.error('Failed to fetch ports:', err);
    } finally {
      loading.value = false;
    }
  }

  return {
    // State
    sites,
    devices,
    ports,
    loading,
    error,
    // Computed
    totalSites,
    totalDevices,
    totalPorts,
    // Actions
    fetchSites,
    fetchDevices,
    fetchPorts,
  };
});
