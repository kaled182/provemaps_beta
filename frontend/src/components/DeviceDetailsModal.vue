<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="device-modal-overlay" @click.self="close">
        <div class="device-modal-container" :class="{ dark: isDark }">
          <!-- Header -->
          <div class="device-modal-header">
            <div class="header-content">
              <div class="device-icon-large">
                <i :class="getDeviceIcon(device?.type)"></i>
              </div>
              <div class="device-info">
                <h2 class="device-name">{{ device?.name || 'Carregando...' }}</h2>
                <p class="device-meta">{{ device?.type || 'N/A' }} • {{ device?.ip || 'N/A' }}</p>
              </div>
            </div>
            <button class="close-button" @click="close">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <!-- Device Metrics Summary -->
          <div class="metrics-summary">
            <div class="metric-card">
              <div class="metric-icon cpu">
                <i class="fas fa-microchip"></i>
              </div>
              <div class="metric-info">
                <span class="metric-label">CPU</span>
                <span class="metric-value">{{ device?.cpu || 0 }}%</span>
              </div>
            </div>
            <div class="metric-card">
              <div class="metric-icon memory">
                <i class="fas fa-memory"></i>
              </div>
              <div class="metric-info">
                <span class="metric-label">Memória</span>
                <span class="metric-value">{{ device?.memory || 0 }}%</span>
              </div>
            </div>
            <div class="metric-card">
              <div class="metric-icon uptime">
                <i class="fas fa-clock"></i>
              </div>
              <div class="metric-info">
                <span class="metric-label">Uptime</span>
                <span class="metric-value">{{ device?.uptime_human || formatUptime(device?.uptime) }}</span>
              </div>
            </div>
            <div class="metric-card">
              <div class="metric-icon status" :class="device?.status">
                <i class="fas fa-circle"></i>
              </div>
              <div class="metric-info">
                <span class="metric-label">Status</span>
                <span class="metric-value">{{ getStatusLabel(device?.status) }}</span>
              </div>
            </div>
          </div>

          <!-- Ports Section -->
          <div class="ports-section">
            <div class="section-header">
              <h3 class="section-title">
                <i class="fas fa-ethernet"></i>
                Portas em Uso ({{ portsInUse.length }})
              </h3>
              <div class="section-actions">
                <div class="search-box">
                  <i class="fas fa-search"></i>
                  <input
                    v-model="searchQuery"
                    type="text"
                    placeholder="Buscar porta ou descrição..."
                    class="search-input"
                  />
                </div>
                <button class="btn-export" @click="exportToCSV" title="Exportar para CSV">
                  <i class="fas fa-download"></i>
                  Exportar CSV
                </button>
                <button class="btn-filter" :class="{ active: filterOnlyInUse }" @click="filterOnlyInUse = !filterOnlyInUse">
                  <i class="fas fa-filter"></i>
                  {{ filterOnlyInUse ? 'Todas' : 'Apenas em Uso' }}
                </button>
              </div>
            </div>

            <div v-if="loadingPorts" class="loading-state">
              <i class="fas fa-spinner fa-spin"></i>
              <span>Carregando portas...</span>
            </div>

            <div v-else-if="displayedPorts.length === 0" class="empty-state">
              <i class="fas fa-plug"></i>
              <span>Nenhuma porta encontrada</span>
            </div>

            <div v-else class="ports-grid">
              <div
                v-for="port in displayedPorts"
                :key="port.id"
                class="port-card"
                :class="getPortStatusClass(port)"
                @click="openTrafficModal(port)"
                style="cursor: pointer;"
              >
                <!-- Port Header -->
                <div class="port-header">
                  <div class="port-name">
                    <i class="fas fa-network-wired"></i>
                    <span>{{ port.name }}</span>
                  </div>
                  <div class="port-header-actions">
                    <button 
                      v-if="port.optical_rx_power !== null" 
                      class="icon-btn" 
                      @click.stop="openAlarmConfig(port)"
                      title="Configurar Alarme"
                    >
                      <i class="fas fa-bell"></i>
                    </button>
                    <button 
                      v-if="port.connected_cable" 
                      class="icon-btn" 
                      @click.stop="openConnectivityMap(port)"
                      title="Mapa de Conectividade"
                    >
                      <i class="fas fa-project-diagram"></i>
                    </button>
                    <button 
                      class="icon-btn" 
                      @click.stop="openPortActions(port)"
                      title="Ações"
                    >
                      <i class="fas fa-ellipsis-v"></i>
                    </button>
                    <div class="port-status-badge" :class="getPortStatusClass(port)">
                      {{ getPortStatus(port) }}
                    </div>
                  </div>
                </div>

                <!-- Port Info -->
                <div class="port-info">
                  <div v-if="port.description" class="info-row">
                    <i class="fas fa-tag"></i>
                    <span class="info-label">Descrição:</span>
                    <span class="info-value">{{ port.description }}</span>
                  </div>

                  <!-- Optical Signal -->
                  <div v-if="port.optical_rx_power !== null || port.optical_tx_power !== null" class="info-row optical">
                    <i class="fas fa-lightbulb"></i>
                    <span class="info-label">Sinal Óptico:</span>
                    <div class="optical-signals">
                      <div v-if="port.optical_rx_power !== null" class="signal-item">
                        <span class="signal-label">RX:</span>
                        <span class="signal-value" :class="getSignalClass(port.optical_rx_power)">
                          {{ formatOpticalPower(port.optical_rx_power) }} dBm
                        </span>
                      </div>
                      <div v-if="port.optical_tx_power !== null" class="signal-item">
                        <span class="signal-label">TX:</span>
                        <span class="signal-value" :class="getSignalClass(port.optical_tx_power)">
                          {{ formatOpticalPower(port.optical_tx_power) }} dBm
                        </span>
                      </div>
                    </div>
                  </div>

                  <!-- VLAN -->
                  <div v-if="port.vlan" class="info-row">
                    <i class="fas fa-network-wired"></i>
                    <span class="info-label">VLAN:</span>
                    <span class="info-value">{{ port.vlan }}</span>
                  </div>

                  <!-- Speed -->
                  <div v-if="port.speed" class="info-row">
                    <i class="fas fa-tachometer-alt"></i>
                    <span class="info-label">Velocidade:</span>
                    <span class="info-value">{{ port.speed }}</span>
                  </div>

                  <!-- Connected Cable -->
                  <div v-if="port.connected_cable" class="info-row cable">
                    <i class="fas fa-link"></i>
                    <span class="info-label">Cabo Conectado:</span>
                    <span class="info-value cable-name">{{ port.connected_cable.name || `Cabo #${port.connected_cable.id}` }}</span>
                  </div>

                  <!-- Port Type -->
                  <div v-if="port.port_type" class="info-row">
                    <i class="fas fa-info-circle"></i>
                    <span class="info-label">Tipo:</span>
                    <span class="info-value">{{ port.port_type }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Sub-modals -->
        <PortActionsModal
          :is-open="showPortActions"
          :port="selectedPort"
          @close="closePortActions"
          @refresh="loadPorts"
        />

        <AlarmConfigModal
          :is-open="showAlarmConfig"
          :port="selectedPort"
          @close="closeAlarmConfig"
          @saved="handleAlarmSaved"
        />

        <ConnectivityMapModal
          :is-open="showConnectivityMap"
          :port="selectedPort"
          :device-info="device"
          @close="closeConnectivityMap"
        />
      </div>
    </Transition>
  </Teleport>

  <!-- PortTrafficModal fora do DeviceDetailsModal para evitar conflitos de z-index -->
  <PortTrafficModal
    :is-open="showTrafficModal"
    :port="selectedPort"
    @close="closeTrafficModal"
  />
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'
import { useEscapeKey } from '@/composables/useEscapeKey'
import { useUiStore } from '@/stores/ui'
import PortActionsModal from './PortActionsModal.vue'
import AlarmConfigModal from './AlarmConfigModal.vue'
import ConnectivityMapModal from './ConnectivityMapModal.vue'
import PortTrafficModal from './PortTrafficModal.vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  device: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close'])

const { get } = useApi()
const { success, error: notifyError } = useNotification()
const uiStore = useUiStore()

const ports = ref([])
const loadingPorts = ref(false)
const filterOnlyInUse = ref(true)
const searchQuery = ref('')
const selectedPort = ref(null)
const showPortActions = ref(false)
const showAlarmConfig = ref(false)
const showConnectivityMap = ref(false)
const showTrafficModal = ref(false)

const close = () => {
  emit('close')
}

// Gerenciar ESC key - ignora quando algum modal filho está aberto
const hasChildModalOpen = computed(() => 
  showPortActions.value || showAlarmConfig.value || showConnectivityMap.value || showTrafficModal.value
)
useEscapeKey(() => close(), { isOpen: computed(() => props.isOpen), shouldIgnore: hasChildModalOpen })

const isDark = computed(() => uiStore.theme === 'dark')

// Network thresholds (fetched from setup config)
const opticalWarningThreshold = ref(-24)
const opticalCriticalThreshold = ref(-27)

const loadNetworkThresholds = async () => {
  try {
    const res = await get('/setup_app/api/config/')
    const cfg = res?.configuration || {}
    const warnRaw = cfg.OPTICAL_RX_WARNING_THRESHOLD
    const critRaw = cfg.OPTICAL_RX_CRITICAL_THRESHOLD
    const warn = warnRaw === undefined || warnRaw === null || warnRaw === '' ? -24 : Number(warnRaw)
    const crit = critRaw === undefined || critRaw === null || critRaw === '' ? -27 : Number(critRaw)
    opticalWarningThreshold.value = Number.isFinite(warn) ? warn : -24
    opticalCriticalThreshold.value = Number.isFinite(crit) ? crit : -27
  } catch (e) {
    // Keep defaults on failure
    console.warn('[DeviceDetailsModal] Thresholds load failed, using defaults', e)
  }
}

const portsInUse = computed(() => {
  return ports.value.filter(port => {
    const hasOptical = port.optical_rx_power !== null || port.optical_tx_power !== null
    const hasConnection = !!port.connected_cable
    return hasOptical || hasConnection
  })
})

const displayedPorts = computed(() => {
  let filtered = filterOnlyInUse.value ? portsInUse.value : ports.value
  
  // Apply search filter
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(port => 
      port.name?.toLowerCase().includes(query) ||
      port.description?.toLowerCase().includes(query)
    )
  }
  
  return filtered
})

const loadPorts = async () => {
  if (!props.device?.id) return
  
  loadingPorts.value = true
  try {
    console.log('[DeviceDetailsModal] Loading ports for device:', props.device.id)
    
    const response = await get(`/api/v1/ports/?device=${props.device.id}`)
    
    // Handle both paginated and non-paginated responses
    const rawPorts = response.results || response || []
    
    // Map backend field names (last_rx_power/last_tx_power) to frontend naming (optical_rx_power/optical_tx_power)
    // Ensure values are numeric for rendering (API may return strings)
    ports.value = rawPorts.map(port => {
      const rxRaw = port.last_rx_power
      const txRaw = port.last_tx_power
      const rxNum = rxRaw === null || rxRaw === undefined || rxRaw === '' ? null : Number(rxRaw)
      const txNum = txRaw === null || txRaw === undefined || txRaw === '' ? null : Number(txRaw)
      return {
        ...port,
        // Map description consistently (backend uses 'notes') and sanitize
        description: normalizeDescription(port.description ?? port.notes ?? ''),
        // Normalize connected cable object from cable_id/name
        connected_cable: port.cable_id ? { id: port.cable_id, name: port.cable_name || '' } : null,
        optical_rx_power: Number.isFinite(rxNum) ? rxNum : null,
        optical_tx_power: Number.isFinite(txNum) ? txNum : null,
      }
    })
    
    console.log('[DeviceDetailsModal] Loaded ports:', ports.value.length)
  } catch (error) {
    console.error('[DeviceDetailsModal] Error loading ports:', error)
    ports.value = []
  } finally {
    loadingPorts.value = false
  }
}

const getDeviceIcon = (type) => {
  const icons = {
    router: 'fas fa-network-wired',
    switch: 'fas fa-code-branch',
    server: 'fas fa-server',
    firewall: 'fas fa-shield-alt',
    olt: 'fas fa-broadcast-tower',
    default: 'fas fa-server'
  }
  return icons[type?.toLowerCase()] || icons.default
}

const getStatusLabel = (status) => {
  const labels = {
    online: 'Online',
    warning: 'Atenção',
    critical: 'Crítico',
    offline: 'Offline'
  }
  return labels[status?.toLowerCase()] || 'Desconhecido'
}

const formatUptime = (seconds) => {
  if (!seconds) return 'N/A'
  
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

const getPortStatusClass = (port) => {
  // Check optical signal quality
  if (port.optical_rx_power !== null) {
    if (port.optical_rx_power < opticalCriticalThreshold.value) return 'critical'
    if (port.optical_rx_power < opticalWarningThreshold.value) return 'warning'
  }
  
  // Check if in use
  if (port.connected_cable || port.optical_rx_power !== null) {
    return 'active'
  }
  
  return 'inactive'
}

const getPortStatus = (port) => {
  if (port.optical_rx_power !== null) {
    if (port.optical_rx_power < opticalCriticalThreshold.value) return 'Sinal Fraco'
    if (port.optical_rx_power < opticalWarningThreshold.value) return 'Atenção'
    return 'Em Uso'
  }
  
  if (port.connected_cable) return 'Conectado'
  
  return 'Disponível'
}

const formatOpticalPower = (value) => {
  if (value === null || value === undefined || value === '') return 'N/A'
  const num = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(num)) return 'N/A'
  return num.toFixed(2)
}

// Remove common Zabbix prefixes from description to keep it concise
const normalizeDescription = (text) => {
  if (!text || typeof text !== 'string') return ''
  let out = text.trim()
  // Remove Portuguese prefixes like "Status Operacional da Porta" or "Status Operacional da Interface"
  out = out.replace(/^Status\s+Operacional\s+da\s+(?:Porta|Interface)\s*/i, '')
  // Remove trailing hyphen if present (e.g., "Vlanif669 -")
  out = out.replace(/\s+-\s*$/i, '')
  return out
}

const getSignalClass = (value) => {
  if (value === null || value === undefined) return ''
  if (value < opticalCriticalThreshold.value) return 'signal-critical'
  if (value < opticalWarningThreshold.value) return 'signal-warning'
  return 'signal-good'
}

const exportToCSV = () => {
  try {
    // Prepare CSV data
    const headers = ['Porta', 'Descrição', 'Status', 'RX (dBm)', 'TX (dBm)', 'VLAN', 'Velocidade', 'Tipo', 'Cabo Conectado']
    const rows = displayedPorts.value.map(port => [
      port.name || '',
      port.description || '',
      getPortStatus(port),
      port.optical_rx_power !== null ? port.optical_rx_power.toFixed(2) : 'N/A',
      port.optical_tx_power !== null ? port.optical_tx_power.toFixed(2) : 'N/A',
      port.vlan || '',
      port.speed || '',
      port.port_type || '',
      port.connected_cable?.name || port.connected_cable?.id || ''
    ])
    
    // Build CSV content
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n')
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    const fileName = `portas_${props.device?.name?.replace(/[^a-z0-9]/gi, '_')}_${new Date().toISOString().split('T')[0]}.csv`
    
    link.setAttribute('href', url)
    link.setAttribute('download', fileName)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    console.log('[DeviceDetailsModal] CSV exported successfully:', fileName)
  } catch (error) {
    console.error('[DeviceDetailsModal] Error exporting CSV:', error)
  }
}

const openPortActions = (port) => {
  selectedPort.value = port
  showPortActions.value = true
}

const closePortActions = () => {
  showPortActions.value = false
  selectedPort.value = null
}

const openAlarmConfig = (port) => {
  selectedPort.value = port
  showAlarmConfig.value = true
}

const closeAlarmConfig = () => {
  showAlarmConfig.value = false
  selectedPort.value = null
}

const handleAlarmSaved = async () => {
  // Reload ports to get updated alarm configuration
  await loadPorts()
}

const openConnectivityMap = (port) => {
  selectedPort.value = port
  showConnectivityMap.value = true
}

const closeConnectivityMap = () => {
  showConnectivityMap.value = false
  selectedPort.value = null
}

const openTrafficModal = (port) => {
  selectedPort.value = port
  showTrafficModal.value = true
}

const closeTrafficModal = () => {
  showTrafficModal.value = false
  selectedPort.value = null
}

watch(() => props.isOpen, (newVal) => {
  if (newVal && props.device) {
    loadNetworkThresholds()
    loadPorts()
  }
})

// Also react to device changes while modal is open
watch(() => props.device, (newDevice) => {
  if (props.isOpen && newDevice) {
    console.log('[DeviceDetailsModal] Device changed, reloading ports:', newDevice.id)
    loadPorts()
  }
})
</script>

<style scoped>
/* Device Details Modal Styles */
.device-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 11000;
  padding: 20px;
  backdrop-filter: blur(4px);
}

.device-modal-container {
  background: #ffffff;
  border-radius: 16px;
  max-width: 1400px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.device-modal-container.dark {
  background: #1e293b;
  color: #f1f5f9;
}

/* Header */
.device-modal-header {
  padding: 24px 32px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.device-modal-container.dark .device-modal-header {
  border-bottom-color: #334155;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.device-icon-large {
  width: 64px;
  height: 64px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  backdrop-filter: blur(10px);
}

.device-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.device-name {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  color: white;
}

.device-meta {
  font-size: 14px;
  margin: 0;
  opacity: 0.9;
  color: white;
}

.close-button {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  transition: all 0.2s;
  backdrop-filter: blur(10px);
}

.close-button:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}

/* Metrics Summary */
.metrics-summary {
  padding: 20px 32px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.device-modal-container.dark .metrics-summary {
  background: #0f172a;
  border-bottom-color: #334155;
}

.metric-card {
  background: white;
  padding: 16px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.device-modal-container.dark .metric-card {
  background: #1e293b;
}

.metric-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.metric-icon.cpu {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.metric-icon.memory {
  background: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
}

.metric-icon.uptime {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.metric-icon.status {
  background: rgba(107, 114, 128, 0.1);
  color: #6b7280;
}

.metric-icon.status.online {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.metric-icon.status.warning {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.metric-icon.status.critical {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.metric-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
}

.device-modal-container.dark .metric-value {
  color: #f1f5f9;
}

/* Ports Section */
.ports-section {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #1e293b;
}

.device-modal-container.dark .section-title {
  color: #f1f5f9;
}

.section-title i {
  color: #667eea;
}

.section-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-box i {
  position: absolute;
  left: 12px;
  color: #94a3b8;
  font-size: 14px;
}

.search-input {
  padding: 8px 16px 8px 36px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: white;
  color: #1e293b;
  font-size: 13px;
  width: 250px;
  transition: all 0.2s;
}

.device-modal-container.dark .search-input {
  background: #1e293b;
  border-color: #334155;
  color: #cbd5e1;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.search-input::placeholder {
  color: #94a3b8;
}

.btn-export {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid #e2e8f0;
  background: white;
  color: #10b981;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.device-modal-container.dark .btn-export {
  background: #1e293b;
  border-color: #334155;
}

.btn-export:hover {
  background: rgba(16, 185, 129, 0.1);
  border-color: #10b981;
}

.btn-filter {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid #e2e8f0;
  background: white;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.device-modal-container.dark .btn-filter {
  background: #1e293b;
  border-color: #334155;
  color: #cbd5e1;
}

.btn-filter:hover {
  background: #f8fafc;
  border-color: #667eea;
  color: #667eea;
}

.btn-filter.active {
  background: #667eea;
  border-color: #667eea;
  color: white;
}

/* Loading & Empty States */
.loading-state,
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #64748b;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.loading-state i,
.empty-state i {
  font-size: 48px;
  opacity: 0.5;
}

/* Ports Grid */
.ports-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 16px;
}

.port-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
  position: relative; /* para posicionar a faixa de status */
  overflow: hidden; /* garante raio aplicado na faixa */
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.3s;
}

.device-modal-container.dark .port-card {
  background: #0f172a;
}

.port-card:hover {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

/* Faixa única de status na lateral esquerda */
.port-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 6px;
  height: 100%;
  background: var(--status-color, transparent);
  /* seguir o raio do cartão para não parecer duplicado */
  border-top-left-radius: 12px;
  border-bottom-left-radius: 12px;
}

.port-card.active { --status-color: #10b981; }
.port-card.warning { --status-color: #f59e0b; }
.port-card.critical { --status-color: #ef4444; }
.port-card.inactive { --status-color: #94a3b8; opacity: 0.7; }

/* Port Header */
.port-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e2e8f0;
}

.device-modal-container.dark .port-header {
  border-bottom-color: #334155;
}

.port-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: transparent;
  border: 1px solid #e2e8f0;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  transition: all 0.2s;
}

.device-modal-container.dark .icon-btn {
  border-color: #334155;
  color: #94a3b8;
}

.icon-btn:hover {
  background: #667eea;
  border-color: #667eea;
  color: white;
  transform: scale(1.1);
}

.port-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.device-modal-container.dark .port-name {
  color: #f1f5f9;
}

.port-name i {
  color: #667eea;
}

.port-status-badge {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.port-status-badge.active {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.port-status-badge.warning {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.port-status-badge.critical {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.port-status-badge.inactive {
  background: rgba(148, 163, 184, 0.1);
  color: #94a3b8;
}

/* Port Info */
.port-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-row {
  display: grid;
  grid-template-columns: 20px auto 1fr;
  gap: 8px;
  align-items: start;
  font-size: 13px;
}

.info-row i {
  color: #94a3b8;
  margin-top: 2px;
}

.info-label {
  font-weight: 500;
  color: #64748b;
}

.info-value {
  color: #1e293b;
  font-weight: 600;
}

.device-modal-container.dark .info-value {
  color: #f1f5f9;
}

.info-row.cable .cable-name {
  color: #667eea;
  text-decoration: underline;
  cursor: pointer;
}

/* Optical Signals */
.info-row.optical {
  grid-template-columns: 20px auto;
}

.optical-signals {
  grid-column: 2 / -1;
  display: flex;
  gap: 12px;
  margin-top: 4px;
}

.signal-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #f1f5f9;
  border-radius: 6px;
}

.device-modal-container.dark .signal-item {
  background: #1e293b;
}

.signal-label {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
}

.signal-value {
  font-size: 13px;
  font-weight: 700;
  font-family: 'Monaco', 'Courier New', monospace;
}

.signal-value.signal-good {
  color: #10b981;
}

.signal-value.signal-warning {
  color: #f59e0b;
}

.signal-value.signal-critical {
  color: #ef4444;
}

/* Animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s;
}

.modal-enter-active .device-modal-container,
.modal-leave-active .device-modal-container {
  transition: transform 0.3s, opacity 0.3s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .device-modal-container,
.modal-leave-to .device-modal-container {
  transform: scale(0.9);
  opacity: 0;
}

/* Scrollbar */
.ports-section::-webkit-scrollbar {
  width: 8px;
}

.ports-section::-webkit-scrollbar-track {
  background: #f1f5f9;
}

.device-modal-container.dark .ports-section::-webkit-scrollbar-track {
  background: #0f172a;
}

.ports-section::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

.device-modal-container.dark .ports-section::-webkit-scrollbar-thumb {
  background: #475569;
}

.ports-section::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* Responsive */
@media (max-width: 768px) {
  .device-modal-container {
    max-width: 100%;
    max-height: 100vh;
    border-radius: 0;
  }
  
  .ports-grid {
    grid-template-columns: 1fr;
  }
  
  .metrics-summary {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
