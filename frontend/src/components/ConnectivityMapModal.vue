<template>
  <BaseModal
    :show="isOpen"
    :title="`Mapa de conectividade · ${port?.name || ''}`"
    :icon="PhGraph"
    :z-index="3500"
    size="md"
    @close="close"
  >
    <!-- Content -->
    <div class="connectivity-modal-content">
      <div v-if="loading" class="loading-state">
        <i class="fas fa-spinner fa-spin"></i>
        <span>Carregando conectividade...</span>
      </div>
      <p v-else-if="loadError" class="load-error" role="alert" data-testid="connectivity-error">
        Erro ao carregar a conectividade: {{ loadError }}
      </p>

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
              {{ connectivity.cable.lengthMeters === null ? 'extensão não cadastrada' : `${connectivity.cable.lengthMeters} m` }}
            </p>
            <p v-if="connectivity.cable.fiber_count" class="node-detail">
              <i class="fas fa-network-wired"></i>
              {{ connectivity.cable.fiber_count }} fibras
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
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useApi } from '@/composables/useApi'
import { PhGraph } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import { otherEnd, cableLengthMeters, linkLossDb } from '@/utils/portConnectivity'

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

const loading = ref(false)
const connectivity = ref({
  cable: null,
  fiber: null,
  destinationPort: null,
  destinationDevice: null
})


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

// EV-0071: o cabo vem de /api/v1/fiber-cables/ (a rota antiga /api/v1/cables/ não existe) e
// o destino é a outra ponta real do cabo. Sem «fibra» inventada (antes punha a 1.ª fibra
// do cabo como se fosse a da porta).
const loadError = ref('')
const loadConnectivity = async () => {
  if (!props.port?.id) return
  loading.value = true
  loadError.value = ''
  connectivity.value = { cable: null, fiber: null, destinationPort: null, destinationDevice: null }
  try {
    const cableId = props.port.connected_cable?.id ?? props.port.cable_id
    if (!cableId) return
    const cable = await get(`/api/v1/fiber-cables/${encodeURIComponent(cableId)}/`)
    connectivity.value.cable = { ...cable, lengthMeters: cableLengthMeters(cable) }
    const end = otherEnd(cable, props.port.id)
    if (!end) return
    const other = await get(`/api/v1/ports/${encodeURIComponent(end.portId)}/`).catch(() => null)
    const toNum = (v) => (v === null || v === undefined || v === '' || !Number.isFinite(Number(v)) ? null : Number(v))
    connectivity.value.destinationPort = {
      id: end.portId,
      name: other?.name || end.portName || `Porta #${end.portId}`,
      optical_rx_power: toNum(other?.last_rx_power),
    }
    connectivity.value.destinationDevice = { name: other?.device_name || end.deviceName || null }
  } catch (error) {
    console.error('[ConnectivityMapModal] Erro ao carregar a conectividade:', error)
    loadError.value = error?.message || 'erro desconhecido'
  } finally {
    loading.value = false
  }
}

const calculateAttenuation = () => {
  // 0 dBm é leitura válida: só «N/A» quando falta a leitura (antes `!valor` tratava 0 como falta)
  const loss = linkLossDb(props.port?.optical_tx_power, connectivity.value.destinationPort?.optical_rx_power)
  return loss === null ? 'N/A' : loss.toFixed(2)
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

.connectivity-modal-content {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
}

.load-error {
  margin: 0;
  padding: 8px 12px;
  border: 1px solid rgb(var(--danger) / 0.4);
  border-radius: 6px;
  background: rgb(var(--danger) / 0.1);
  color: rgb(var(--danger));
  font-size: 13px;
}

.loading-state {
  text-align: center;
  padding: 60px 20px;
  color: rgb(var(--n-500));
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
  background: rgb(var(--n-50));
  border-radius: 12px;
  overflow-x: auto;
}

.connection-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  min-width: 180px;
  padding: 20px;
  background: rgb(var(--surface));
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.connection-node.source {
  border: 2px solid rgb(var(--info));
}

.connection-node.destination {
  border: 2px solid rgb(var(--success));
}

.connection-node.cable {
  border: 2px solid rgb(var(--primary-500));
}

.connection-node.disconnected {
  border: 2px dashed rgb(var(--n-400));
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
  background: rgb(var(--primary-600));
  color: white;
}

.node-icon.cable {
  background: rgb(var(--primary-600));
  color: white;
}

.connection-node.disconnected .node-icon {
  background: rgb(var(--n-200));
  color: rgb(var(--n-400));
}

.node-info {
  text-align: center;
  width: 100%;
}

.node-info h4 {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: rgb(var(--n-900));
}

.node-detail {
  font-size: 12px;
  color: rgb(var(--n-500));
  margin: 4px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
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
  background: rgb(var(--info) / 0.1);
  color: rgb(var(--info));
}

.signal-badge.rx {
  background: rgb(var(--success) / 0.1);
  color: rgb(var(--success));
}

.connection-arrow {
  font-size: 32px;
  color: rgb(var(--n-300));
}

.connection-details {
  padding: 24px;
  background: rgb(var(--n-50));
  border-radius: 12px;
}

.connection-details h4 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px 0;
  color: rgb(var(--n-900));
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
  color: rgb(var(--n-500));
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  font-size: 14px;
  font-weight: 600;
  color: rgb(var(--n-900));
}

.detail-value.good {
  color: rgb(var(--success));
}

.detail-value.warning {
  color: rgb(var(--warning));
}

.detail-value.critical {
  color: rgb(var(--danger));
}

.detail-value.disconnected,
.detail-value.unknown {
  color: rgb(var(--n-400));
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
