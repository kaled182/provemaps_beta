<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="connectivity-modal-overlay" @click.self="close">
        <div class="connectivity-modal-container" :class="{ dark: isDark }">
          <!-- Header -->
          <div class="connectivity-modal-header">
            <h3>
              <i class="fas fa-project-diagram"></i>
              Mapa de Conectividade - {{ port?.name }}
            </h3>
            <button class="close-button" @click="close">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <!-- Content -->
          <div class="connectivity-modal-content">
            <div v-if="loading" class="loading-state">
              <i class="fas fa-spinner fa-spin"></i>
              <span>Carregando conectividade...</span>
            </div>

            <div v-else class="connectivity-map">
              <!-- Source Device/Port -->
              <div class="connection-node source">
                <div class="node-icon device">
                  <i class="fas fa-server"></i>
                </div>
                <div class="node-info">
                  <h4>{{ deviceInfo.name }}</h4>
                  <p class="node-detail">{{ port?.name }}</p>
                  <p class="node-detail">{{ deviceInfo.ip }}</p>
                  <div v-if="port?.optical_tx_power !== null" class="signal-badge tx">
                    <i class="fas fa-arrow-right"></i>
                    TX: {{ port.optical_tx_power.toFixed(2) }} dBm
                  </div>
                </div>
              </div>

              <!-- Arrow -->
              <div class="connection-arrow">
                <i class="fas fa-long-arrow-alt-right"></i>
              </div>

              <!-- Cable -->
              <div v-if="connectivity.cable" class="connection-node cable">
                <div class="node-icon cable">
                  <i class="fas fa-link"></i>
                </div>
                <div class="node-info">
                  <h4>{{ connectivity.cable.name || `Cabo #${connectivity.cable.id}` }}</h4>
                  <p class="node-detail">
                    <i class="fas fa-ruler"></i>
                    {{ connectivity.cable.length || 'N/A' }}m
                  </p>
                  <p v-if="connectivity.cable.fiber_count" class="node-detail">
                    <i class="fas fa-network-wired"></i>
                    {{ connectivity.cable.fiber_count }} fibras
                  </p>
                  <p v-if="connectivity.fiber" class="node-detail fiber">
                    <i class="fas fa-circle"></i>
                    Fibra {{ connectivity.fiber.number || connectivity.fiber.id }}
                    <span v-if="connectivity.fiber.color" class="fiber-color" :style="{ backgroundColor: connectivity.fiber.color }"></span>
                  </p>
                </div>
              </div>

              <!-- Arrow -->
              <div v-if="connectivity.cable" class="connection-arrow">
                <i class="fas fa-long-arrow-alt-right"></i>
              </div>

              <!-- Destination Device/Port -->
              <div v-if="connectivity.destinationPort" class="connection-node destination">
                <div class="node-icon device">
                  <i class="fas fa-server"></i>
                </div>
                <div class="node-info">
                  <h4>{{ connectivity.destinationDevice?.name || 'Dispositivo Destino' }}</h4>
                  <p class="node-detail">{{ connectivity.destinationPort.name }}</p>
                  <p class="node-detail">{{ connectivity.destinationDevice?.ip || 'N/A' }}</p>
                  <div v-if="connectivity.destinationPort.optical_rx_power !== null" class="signal-badge rx">
                    <i class="fas fa-arrow-left"></i>
                    RX: {{ connectivity.destinationPort.optical_rx_power.toFixed(2) }} dBm
                  </div>
                </div>
              </div>

              <!-- Not Connected -->
              <div v-else class="connection-node disconnected">
                <div class="node-icon">
                  <i class="fas fa-question-circle"></i>
                </div>
                <div class="node-info">
                  <h4>Não Conectado</h4>
                  <p class="node-detail">Nenhuma porta de destino identificada</p>
                </div>
              </div>
            </div>

            <!-- Connection Details -->
            <div v-if="!loading" class="connection-details">
              <h4>Detalhes da Conexão</h4>
              
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="detail-label">Status:</span>
                  <span class="detail-value" :class="getConnectionStatus()">
                    {{ getConnectionStatusLabel() }}
                  </span>
                </div>

                <div v-if="connectivity.cable" class="detail-item">
                  <span class="detail-label">Atenuação:</span>
                  <span class="detail-value">
                    {{ calculateAttenuation() }} dB
                  </span>
                </div>

                <div v-if="connectivity.cable?.route" class="detail-item">
                  <span class="detail-label">Rota:</span>
                  <span class="detail-value">{{ connectivity.cable.route.name }}</span>
                </div>

                <div v-if="connectivity.fiber" class="detail-item">
                  <span class="detail-label">Fibra:</span>
                  <span class="detail-value">
                    #{{ connectivity.fiber.number || connectivity.fiber.id }}
                    {{ connectivity.fiber.color ? `(${connectivity.fiber.color})` : '' }}
                  </span>
                </div>

                <div v-if="connectivity.cable?.installation_date" class="detail-item">
                  <span class="detail-label">Instalação:</span>
                  <span class="detail-value">
                    {{ formatDate(connectivity.cable.installation_date) }}
                  </span>
                </div>

                <div v-if="port?.vlan" class="detail-item">
                  <span class="detail-label">VLAN:</span>
                  <span class="detail-value">{{ port.vlan }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useApi } from '@/composables/useApi'
import { useUiStore } from '@/stores/ui'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  port: {
    type: Object,
    default: null
  },
  deviceInfo: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['close'])

const { get } = useApi()
const uiStore = useUiStore()

const loading = ref(false)
const connectivity = ref({
  cable: null,
  fiber: null,
  destinationPort: null,
  destinationDevice: null
})

const isDark = computed(() => uiStore.theme === 'dark')

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
    console.warn('[ConnectivityMapModal] Thresholds load failed, using defaults', e)
  }
}

const close = () => {
  emit('close')
}

const loadConnectivity = async () => {
  if (!props.port?.id) return
  
  loading.value = true
  try {
    console.log('[ConnectivityMapModal] Loading connectivity for port:', props.port.id)
    
    // Get cable info
    if (props.port.connected_cable) {
      const cableId = typeof props.port.connected_cable === 'object' 
        ? props.port.connected_cable.id 
        : props.port.connected_cable
      
      const cable = await get(`/api/v1/cables/${cableId}/`)
      connectivity.value.cable = cable
      
      // Try to find fiber and destination port
      // This would require a specific endpoint or logic to trace the connection
      // For now, we'll use mock data structure
      
      // TODO: Implement proper fiber tracing endpoint
      // const trace = await get(`/api/v1/ports/${props.port.id}/trace/`)
      
      // Mock fiber info (would come from backend)
      if (cable.fibers && cable.fibers.length > 0) {
        connectivity.value.fiber = cable.fibers[0]
      }
    }
    
  } catch (error) {
    console.error('[ConnectivityMapModal] Error loading connectivity:', error)
  } finally {
    loading.value = false
  }
}

const calculateAttenuation = () => {
  if (!props.port?.optical_tx_power || !connectivity.value.destinationPort?.optical_rx_power) {
    return 'N/A'
  }
  
  const attenuation = props.port.optical_tx_power - connectivity.value.destinationPort.optical_rx_power
  return Math.abs(attenuation).toFixed(2)
}

const getConnectionStatus = () => {
  if (!connectivity.value.cable) return 'disconnected'
  if (!connectivity.value.destinationPort) return 'incomplete'
  
  const rxPower = connectivity.value.destinationPort.optical_rx_power
  if (rxPower === null) return 'unknown'
  if (rxPower < opticalCriticalThreshold.value) return 'critical'
  if (rxPower < opticalWarningThreshold.value) return 'warning'
  return 'good'
}

const getConnectionStatusLabel = () => {
  const status = getConnectionStatus()
  const labels = {
    good: 'Ótimo',
    warning: 'Atenção',
    critical: 'Crítico',
    incomplete: 'Incompleto',
    disconnected: 'Desconectado',
    unknown: 'Desconhecido'
  }
  return labels[status] || 'N/A'
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString('pt-BR')
}

watch(() => props.isOpen, (newVal) => {
  if (newVal && props.port) {
    loadNetworkThresholds()
    loadConnectivity()
  }
})
</script>

<style scoped>
.connectivity-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 12000;
  padding: 20px;
}

.connectivity-modal-container {
  background: #ffffff;
  border-radius: 12px;
  max-width: 900px;
  width: 100%;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.connectivity-modal-container.dark {
  background: #1e293b;
  color: #f1f5f9;
}

.connectivity-modal-header {
  padding: 20px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.connectivity-modal-container.dark .connectivity-modal-header {
  border-bottom-color: #334155;
}

.connectivity-modal-header h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #1e293b;
}

.connectivity-modal-container.dark .connectivity-modal-header h3 {
  color: #f1f5f9;
}

.connectivity-modal-header h3 i {
  color: #667eea;
}

.close-button {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #f1f5f9;
  border: none;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.connectivity-modal-container.dark .close-button {
  background: #334155;
  color: #cbd5e1;
}

.close-button:hover {
  background: #e2e8f0;
  transform: scale(1.1);
}

.connectivity-modal-content {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
}

.loading-state {
  text-align: center;
  padding: 60px 20px;
  color: #64748b;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.loading-state i {
  font-size: 48px;
}

.connectivity-map {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin-bottom: 32px;
  padding: 24px;
  background: #f8fafc;
  border-radius: 12px;
  overflow-x: auto;
}

.connectivity-modal-container.dark .connectivity-map {
  background: #0f172a;
}

.connection-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  min-width: 180px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.connectivity-modal-container.dark .connection-node {
  background: #1e293b;
}

.connection-node.source {
  border: 2px solid #3b82f6;
}

.connection-node.destination {
  border: 2px solid #10b981;
}

.connection-node.cable {
  border: 2px solid #8b5cf6;
}

.connection-node.disconnected {
  border: 2px dashed #94a3b8;
  opacity: 0.6;
}

.node-icon {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}

.node-icon.device {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.node-icon.cable {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  color: white;
}

.connection-node.disconnected .node-icon {
  background: #e2e8f0;
  color: #94a3b8;
}

.connectivity-modal-container.dark .connection-node.disconnected .node-icon {
  background: #334155;
}

.node-info {
  text-align: center;
  width: 100%;
}

.node-info h4 {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #1e293b;
}

.connectivity-modal-container.dark .node-info h4 {
  color: #f1f5f9;
}

.node-detail {
  font-size: 12px;
  color: #64748b;
  margin: 4px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.node-detail.fiber {
  font-weight: 600;
  color: #8b5cf6;
}

.fiber-color {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid #94a3b8;
}

.signal-badge {
  margin-top: 8px;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.signal-badge.tx {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.signal-badge.rx {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.connection-arrow {
  font-size: 32px;
  color: #cbd5e1;
}

.connectivity-modal-container.dark .connection-arrow {
  color: #475569;
}

.connection-details {
  padding: 24px;
  background: #f8fafc;
  border-radius: 12px;
}

.connectivity-modal-container.dark .connection-details {
  background: #0f172a;
}

.connection-details h4 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px 0;
  color: #1e293b;
}

.connectivity-modal-container.dark .connection-details h4 {
  color: #f1f5f9;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.connectivity-modal-container.dark .detail-value {
  color: #f1f5f9;
}

.detail-value.good {
  color: #10b981;
}

.detail-value.warning {
  color: #f59e0b;
}

.detail-value.critical {
  color: #ef4444;
}

.detail-value.disconnected,
.detail-value.unknown {
  color: #94a3b8;
}

@media (max-width: 768px) {
  .connectivity-map {
    flex-direction: column;
  }
  
  .connection-arrow {
    transform: rotate(90deg);
  }
}
</style>
