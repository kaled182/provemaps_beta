<template>
  <div class="site-devices-tab">
    <!-- Header Summary -->
    <div class="devices-summary-header">
      <div class="summary-title">
        <i class="fas fa-server"></i>
        <h3>Dispositivos ({{ deviceCount }})</h3>
      </div>

      <div v-if="hasDevices" class="summary-stats">
        <div class="stat-badge online">
          <i class="fas fa-circle"></i>
          <span>{{ onlineDevices }} Online</span>
        </div>
        <div v-if="warningDevices > 0" class="stat-badge warning">
          <i class="fas fa-exclamation-triangle"></i>
          <span>{{ warningDevices }} Atenção</span>
        </div>
        <div v-if="criticalDevices > 0" class="stat-badge critical">
          <i class="fas fa-exclamation-circle"></i>
          <span>{{ criticalDevices }} Crítico</span>
        </div>
        <div v-if="offlineDevices > 0" class="stat-badge offline">
          <i class="fas fa-circle"></i>
          <span>{{ offlineDevices }} Offline</span>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="devices-loading">
      <i class="fas fa-spinner fa-spin"></i>
      <p>Carregando dispositivos...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="devices-error">
      <i class="fas fa-exclamation-triangle"></i>
      <p>{{ error }}</p>
      <button @click="handleRefresh" class="retry-button">
        <i class="fas fa-redo"></i>
        Tentar novamente
      </button>
    </div>

    <!-- Empty State -->
    <div v-else-if="!hasDevices" class="devices-empty">
      <i class="fas fa-inbox"></i>
      <p>Nenhum dispositivo encontrado neste site</p>
    </div>

    <!-- Devices Grid -->
    <div v-else class="devices-grid">
      <div
        v-for="device in devices"
        :key="device.id"
        class="device-card"
        :class="getStatusClass(device.status)"
        :title="getDeviceTooltip(device)"
        @click="handleViewDetails(device)"
      >
        <!-- Card Header -->
        <div class="device-card-header">
          <div class="device-title-section">
            <i :class="getDeviceIcon(device.type)" class="device-icon"></i>
            <div class="device-title-text">
              <h4>{{ device.name }}</h4>
              <span class="device-type">{{ device.type }}</span>
            </div>
          </div>
          <div class="device-header-actions">
            <span class="status-badge" :class="getStatusClass(device.status)">
              {{ getStatusLabel(device.status) }}
            </span>
            <button
              class="edit-button"
              :title="`Editar ${device.name}`"
              @click.stop="handleEdit(device)"
            >
              <i class="fas fa-cog"></i>
            </button>
          </div>
        </div>

        <!-- Metrics Section -->
        <div class="device-metrics">
          <!-- CPU -->
          <div class="metric">
            <div class="metric-header">
              <span class="metric-label">
                <i class="fas fa-microchip"></i>
                CPU
              </span>
              <span class="metric-value">{{ device.cpu }}%</span>
            </div>
            <div class="metric-bar-container">
              <div
                class="metric-bar"
                :class="getMetricClass(device.cpu)"
                :style="{ width: `${device.cpu}%` }"
              ></div>
            </div>
          </div>

          <!-- Memory -->
          <div class="metric">
            <div class="metric-header">
              <span class="metric-label">
                <i class="fas fa-memory"></i>
                Memória
              </span>
              <span class="metric-value">{{ device.memory }}%</span>
            </div>
            <div class="metric-bar-container">
              <div
                class="metric-bar"
                :class="getMetricClass(device.memory)"
                :style="{ width: `${device.memory}%` }"
              ></div>
            </div>
          </div>

          <!-- Uptime -->
          <div class="metric-simple">
            <span class="metric-label">
              <i class="fas fa-clock"></i>
              Uptime
            </span>
            <span class="metric-text">{{ formatUptime(device.uptime) }}</span>
          </div>

          <!-- IP Address -->
          <div class="metric-simple">
            <span class="metric-label">
              <i class="fas fa-network-wired"></i>
              IP
            </span>
            <span class="metric-text">{{ device.ip }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { watch, onUnmounted } from 'vue'
import { useSiteDevices } from '@/composables/useSiteDevices'

// ===== Props & Emits =====
const props = defineProps({
  siteId: {
    type: Number,
    required: true,
  },
})

const emit = defineEmits([
  'view-device-details', // Abre DeviceDetailsModal
  'edit-device',         // Abre edit modal na modal principal
])

// ===== Composable =====
const {
  devices,
  loading,
  error,
  hasDevices,
  deviceCount,
  onlineDevices,
  warningDevices,
  criticalDevices,
  offlineDevices,
  fetchDevices,
  refreshDevices,
  clearDevices,
  getStatusClass,
  getStatusLabel,
  getDeviceIcon,
  getMetricClass,
  formatUptime,
  getDeviceTooltip,
} = useSiteDevices()

// ===== Lifecycle =====

// Watch siteId changes
watch(
  () => props.siteId,
  (newSiteId) => {
    if (newSiteId) {
      fetchDevices(newSiteId)
    }
  },
  { immediate: true }
)

// Cleanup on unmount
onUnmounted(() => {
  clearDevices()
})

// ===== Event Handlers =====

const handleViewDetails = (device) => {
  emit('view-device-details', device)
}

const handleEdit = (device) => {
  emit('edit-device', device)
}

const handleRefresh = () => {
  refreshDevices(props.siteId)
}
</script>

<style scoped>
.site-devices-tab {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem;
  max-height: 70vh;
  overflow-y: auto;
}

/* ===== Header Summary ===== */
.devices-summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);
}

.summary-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.summary-title i {
  font-size: 1.5rem;
  color: var(--primary-color);
}

.summary-title h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.summary-stats {
  display: flex;
  gap: 0.75rem;
}

.stat-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.stat-badge.online {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.stat-badge.warning {
  background: rgba(251, 146, 60, 0.1);
  color: #fb923c;
}

.stat-badge.critical {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.stat-badge.offline {
  background: rgba(156, 163, 175, 0.1);
  color: #9ca3af;
}

/* ===== Loading/Error/Empty States ===== */
.devices-loading,
.devices-error,
.devices-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  text-align: center;
  color: var(--text-muted);
}

.devices-loading i,
.devices-error i,
.devices-empty i {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.devices-loading p,
.devices-error p,
.devices-empty p {
  margin: 0;
  font-size: 1rem;
}

.retry-button {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: var(--primary-color);
  color: white;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.retry-button:hover {
  opacity: 0.9;
}

/* ===== Devices Grid ===== */
.devices-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.device-card {
  background: var(--card-background);
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.device-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: var(--primary-color);
}

.device-card.online {
  border-left: 3px solid #10b981;
}

.device-card.warning {
  border-left: 3px solid #fb923c;
}

.device-card.critical {
  border-left: 3px solid #ef4444;
}

.device-card.offline {
  border-left: 3px solid #9ca3af;
  opacity: 0.7;
}

/* ===== Card Header ===== */
.device-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.device-title-section {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  flex: 1;
}

.device-icon {
  font-size: 1.5rem;
  color: var(--primary-color);
  margin-top: 0.125rem;
}

.device-title-text h4 {
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.device-type {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.device-header-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.status-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
}

.status-badge.online {
  background: #10b981;
  color: white;
}

.status-badge.warning {
  background: #fb923c;
  color: white;
}

.status-badge.critical {
  background: #ef4444;
  color: white;
}

.status-badge.offline {
  background: #9ca3af;
  color: white;
}

.edit-button {
  padding: 0.25rem 0.5rem;
  background: var(--secondary-background);
  border: 1px solid var(--border-color);
  border-radius: 0.25rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.edit-button:hover {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.edit-button i {
  font-size: 0.875rem;
}

/* ===== Metrics Section ===== */
.device-metrics {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-label {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-label i {
  font-size: 0.875rem;
}

.metric-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
}

.metric-bar-container {
  height: 0.5rem;
  background: var(--secondary-background);
  border-radius: 0.25rem;
  overflow: hidden;
}

.metric-bar {
  height: 100%;
  border-radius: 0.25rem;
  transition: width 0.3s ease;
}

.metric-bar.normal {
  background: #10b981;
}

.metric-bar.warning {
  background: #fb923c;
}

.metric-bar.critical {
  background: #ef4444;
}

.metric-simple {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-top: 1px solid var(--border-color);
}

.metric-text {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
}

/* ===== Responsiveness ===== */
@media (max-width: 768px) {
  .devices-grid {
    grid-template-columns: 1fr;
  }

  .devices-summary-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .summary-stats {
    flex-wrap: wrap;
  }
}
</style>
