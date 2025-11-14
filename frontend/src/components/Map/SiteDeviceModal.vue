<template>
  <div
    v-if="inventoryStore.isSiteModalOpen"
    class="site-modal-overlay"
    @click.self="close"
  >
    <div class="site-modal" role="dialog" :aria-label="`Equipamentos em ${siteTitle}`">
      <header class="site-modal__header">
        <h3>Equipamentos em {{ siteTitle }}</h3>
        <button class="site-modal__close" @click="close" aria-label="Fechar">
          &times;
        </button>
      </header>

      <section class="site-modal__body">
        <p v-if="inventoryStore.currentSiteCity" class="site-modal__subtitle">
          {{ inventoryStore.currentSiteCity }}
        </p>

        <div v-if="inventoryStore.siteDevicesError" class="site-modal__error">
          Falha ao carregar dispositivos: {{ inventoryStore.siteDevicesError }}
        </div>

        <div v-else-if="inventoryStore.isLoadingSiteDevices" class="site-modal__loading">
          Carregando dispositivos...
        </div>

        <div v-else-if="!hasDevices" class="site-modal__empty">
          Nenhum equipamento encontrado neste site.
        </div>

        <ul v-else class="device-list" role="list">
            <li
              v-for="device in deviceList"
              :key="device.id"
              class="device-list__item"
              @click="selectDevice(device)"
              @keyup.enter="selectDevice(device)"
              tabindex="0"
            >
              <div class="device-info">
                <div class="device-list__name">{{ device.name }}</div>
                <span 
                  class="status-badge" 
                  :class="`status-badge--${device.status?.toLowerCase() || 'unknown'}`"
                >
                  {{ device.status || 'UNKNOWN' }}
                </span>
              </div>
              <div class="device-stats">
                <div class="stat-item">
                  <span class="stat-icon">📍</span>
                  <span class="stat-value">{{ device.primary_ip || device.ip_address }}</span>
                </div>
                <div v-if="device.uptime" class="stat-item">
                  <span class="stat-icon">⏱️</span>
                  <span class="stat-value">{{ device.uptime }}</span>
                </div>
                <div v-if="device.cpu_usage !== undefined" class="stat-item">
                  <span class="stat-icon">💻</span>
                  <span class="stat-value">{{ device.cpu_usage }}%</span>
                </div>
              </div>
            </li>
          </ul>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, watch, onMounted } from 'vue';
import { useInventoryStore } from '@/stores/inventory';
import { useMapStore } from '@/stores/map';
import { useDashboardStore } from '@/stores/dashboard';

const inventoryStore = useInventoryStore();
const mapStore = useMapStore();
const dashboardStore = useDashboardStore();

const siteTitle = computed(() => inventoryStore.currentSiteName || 'Site');

const deviceList = computed(() => {
  const raw = inventoryStore.currentSiteDevices;
  if (!Array.isArray(raw)) return [];
  
  // Enrich device data with monitoring info from dashboard store
  return raw.map(device => {
    const enriched = { ...device };
    
    // Try to find matching host in dashboard by zabbix_hostid or id
    const dashboardHost = dashboardStore.hostsList.find(host => 
      (host.host_id && device.zabbix_hostid && host.host_id === device.zabbix_hostid) ||
      (host.id === device.id)
    );
    
    if (dashboardHost) {
      enriched.status = dashboardHost.status || 'unknown';
      enriched.uptime = dashboardHost.uptime_value || null;
      enriched.cpu_usage = dashboardHost.cpu_value ? parseFloat(dashboardHost.cpu_value) : null;
    } else {
      enriched.status = 'unknown';
    }
    
    return enriched;
  });
});

const hasDevices = computed(() => {
  const result = deviceList.value.length > 0;
  console.debug('[SiteDeviceModal] hasDevices computed', { count: deviceList.value.length, result });
  return result;
});

// Auto-fetch fallback if modal opens empty
async function ensureDevicesLoaded() {
  if (!inventoryStore.isSiteModalOpen) return;
  const siteId = inventoryStore.currentSiteId;
  if (!siteId) return;
  if (inventoryStore.isLoadingSiteDevices) return;
  if (Array.isArray(inventoryStore.currentSiteDevices) && inventoryStore.currentSiteDevices.length > 0) return;
  console.debug('[SiteDeviceModal] ensureDevicesLoaded triggering fetch for site', siteId);
  await inventoryStore.fetchSiteDevices(siteId, { force: true });
}

watch(() => inventoryStore.isSiteModalOpen, (open) => {
  if (open) {
    ensureDevicesLoaded();
  }
});

watch(() => inventoryStore.currentSiteId, (id) => {
  if (inventoryStore.isSiteModalOpen && id) {
    ensureDevicesLoaded();
  }
});

onMounted(() => {
  ensureDevicesLoaded();
});

function close() {
  inventoryStore.closeSiteModal();
}

function selectDevice(device) {
  if (!device) {
    return;
  }

  const site = inventoryStore.currentSiteMeta;
  inventoryStore.closeSiteModal();

  if (!site || site.latitude === null || site.longitude === null) {
    console.warn('[SiteDeviceModal] Site sem coordenadas para focar no mapa:', site);
    return;
  }

  mapStore.focusOnItem({
    device,
    site,
    site_id: site.id,
    latitude: Number(site.latitude),
    longitude: Number(site.longitude),
    openModal: true,
  });
}
</script>

<style scoped>
.site-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 16px;
}

.site-modal {
  width: min(480px, 100%);
  max-height: 80vh;
  background: linear-gradient(195deg, var(--menu-bg-start) 0%, var(--menu-bg-end) 100%);
  color: var(--text-primary);
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
  border: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.site-modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-primary);
  background: rgba(0, 0, 0, 0.2);
}

.site-modal__header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--text-primary);
  font-weight: 600;
}

.site-modal__close {
  border: none;
  background: transparent;
  font-size: 2rem;
  line-height: 1;
  cursor: pointer;
  color: var(--text-secondary);
  transition: color 0.2s ease;
}

.site-modal__close:hover {
  color: var(--text-primary);
}

.site-modal__body {
  padding: 16px 20px;
  overflow-y: auto;
  flex: 1;
  min-height: 120px;
}

.site-modal__subtitle {
  margin: 0 0 12px 0;
  color: var(--text-secondary);
  font-size: 0.95rem;
  font-weight: 500;
}

.site-modal__loading,
.site-modal__empty,
.site-modal__error {
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.95rem;
  padding: 20px 0;
}

.site-modal__error {
  color: var(--status-offline);
}

.device-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 60px;
}

.device-list__item {
  border: 1px solid var(--border-primary);
  border-left: 4px solid var(--status-online);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  background: var(--surface-highlight);
  transition: all 0.2s ease;
  color: var(--text-primary) !important;
}

.device-list__item:hover,
.device-list__item:focus {
  background: var(--menu-item-hover);
  outline: none;
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.device-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.device-list__name {
  font-size: 14px;
  color: var(--text-primary) !important;
  font-weight: 600;
}

.status-badge {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 4px 8px;
  border-radius: 4px;
}

.status-badge--online {
  background: var(--status-online);
  color: white;
}

.status-badge--offline {
  background: var(--status-offline);
  color: white;
}

.status-badge--warning {
  background: var(--status-warning);
  color: white;
}

.status-badge--unknown {
  background: var(--status-unknown);
  color: white;
}

.device-stats {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.stat-icon {
  font-size: 13px;
  flex-shrink: 0;
}

.stat-value {
  color: var(--text-primary);
  font-weight: 500;
  white-space: nowrap;
}
</style>
