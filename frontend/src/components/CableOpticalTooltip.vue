<template>
  <Teleport to="body">
    <div
      v-if="visible && cableData"
      ref="tooltipRef"
      class="cable-optical-tooltip"
      :style="tooltipStyle"
    >
      <div class="tooltip-header">
        <div class="tooltip-title">{{ cableData.label }}</div>
        <div class="tooltip-subtitle">
          {{ cableData.origin }} ↔ {{ cableData.destination }}
        </div>
      </div>
      
      <div v-if="loading" class="tooltip-loading">
        <div class="spinner"></div>
        <span>Carregando níveis ópticos...</span>
      </div>
      
      <div v-else-if="error" class="tooltip-error">
        {{ error }}
      </div>
      
      <div v-else-if="hasOpticalData" class="tooltip-content">
        <!-- Interface Origem -->
        <div class="interface-section">
          <div class="interface-header">
            <span class="interface-icon">📡</span>
            <span class="interface-name">{{ opticalData.origin?.interface || 'Origem não configurada' }}</span>
          </div>
          <div v-if="opticalData.origin" class="optical-levels">
            <div class="level-item">
              <span class="level-label">TX (Transmissão):</span>
              <span class="level-value" :class="getLevelClass(opticalData.origin.tx)">
                {{ formatLevel(opticalData.origin.tx) }}
              </span>
            </div>
            <div class="level-item">
              <span class="level-label">RX (Recepção):</span>
              <span class="level-value" :class="getLevelClass(opticalData.origin.rx)">
                {{ formatLevel(opticalData.origin.rx) }}
              </span>
            </div>
          </div>
          <div v-else class="interface-placeholder">Dados ópticos indisponíveis para a origem</div>
        </div>
        
        <!-- Interface Destino -->
        <div class="interface-section">
          <div class="interface-header">
            <span class="interface-icon">📡</span>
            <span class="interface-name">{{ opticalData.destination?.interface || 'Destino não configurado' }}</span>
          </div>
          <div v-if="opticalData.destination" class="optical-levels">
            <div class="level-item">
              <span class="level-label">TX (Transmissão):</span>
              <span class="level-value" :class="getLevelClass(opticalData.destination.tx)">
                {{ formatLevel(opticalData.destination.tx) }}
              </span>
            </div>
            <div class="level-item">
              <span class="level-label">RX (Recepção):</span>
              <span class="level-value" :class="getLevelClass(opticalData.destination.rx)">
                {{ formatLevel(opticalData.destination.rx) }}
              </span>
            </div>
          </div>
          <div v-else class="interface-placeholder">Dados ópticos indisponíveis para o destino</div>
        </div>
        
        <!-- Atenuação -->
        <div v-if="opticalData.attenuation !== null" class="attenuation-section">
          <div class="attenuation-label">Atenuação estimada:</div>
          <div class="attenuation-value">{{ formatValue(opticalData.attenuation, 'dB') }}</div>
        </div>
        
        <!-- Timestamp -->
        <div v-if="opticalData.timestamp" class="tooltip-footer">
          <span class="timestamp">{{ formatTimestamp(opticalData.timestamp) }}</span>
        </div>
      </div>

      <div v-else class="tooltip-no-data">
        Nenhum dado óptico disponível para este cabo.
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  cableData: {
    type: Object,
    default: null
  },
  position: {
    type: Object,
    default: () => ({ x: 0, y: 0 })
  }
})

const { get } = useApi()

const tooltipRef = ref(null)
const loading = ref(false)
const error = ref(null)
const opticalData = ref(null)

const hasOpticalData = computed(() => {
  const data = opticalData.value
  if (!data) return false
  return Boolean(data.origin || data.destination)
})

const tooltipStyle = computed(() => {
  const offset = 15
  return {
    left: `${props.position.x + offset}px`,
    top: `${props.position.y + offset}px`
  }
})

const normalizeNumber = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? num : null
}

const buildInterfaceData = (data) => {
  if (!data) return null
  const tx = normalizeNumber(data.tx_dbm)
  const rx = normalizeNumber(data.rx_dbm)
  const deviceName = data.device_name || 'Dispositivo não identificado'
  const portName = data.port_name || 'Porta sem nome'
  const interfaceLabel = `${deviceName} - ${portName}`
  return {
    interface: interfaceLabel,
    tx,
    rx,
    timestamp: data.last_check || null
  }
}

const loadOpticalData = async () => {
  if (!props.cableData?.id) return
  
  loading.value = true
  error.value = null
  opticalData.value = null
  
  try {
    const response = await get(`/api/v1/inventory/fibers/${props.cableData.id}/cached-status/`)
    
    if (response.error) {
      error.value = response.error
      return
    }

    const origin = buildInterfaceData(response.origin_optical)
    const destination = buildInterfaceData(response.destination_optical)
    const attenuation = calculateAttenuation(origin?.tx, destination?.rx)
    const timestamp = origin?.timestamp || destination?.timestamp || null
    
    opticalData.value = {
      origin,
      destination,
      attenuation,
      timestamp
    }
  } catch (err) {
    console.error('[CableOpticalTooltip] Erro ao carregar dados ópticos:', err)
    error.value = 'Não foi possível carregar os níveis ópticos'
  } finally {
    loading.value = false
  }
}

const calculateAttenuation = (txOrigin, rxDest) => {
  const tx = normalizeNumber(txOrigin)
  const rx = normalizeNumber(rxDest)
  if (tx === null || rx === null) {
    return null
  }
  return Math.abs(tx - rx)
}

watch(() => props.visible, (newVal) => {
  if (newVal && props.cableData) {
    loadOpticalData()
  } else {
    opticalData.value = null
    error.value = null
  }
})

const formatValue = (value, unit = 'dBm') => {
  const num = normalizeNumber(value)
  if (num === null) return 'N/A'
  return `${num.toFixed(2)} ${unit}`
}

const formatLevel = (value) => formatValue(value, 'dBm')

const getLevelClass = (value) => {
  const num = normalizeNumber(value)
  if (num === null) return 'level-unknown'
  if (num >= -10) return 'level-excellent'
  if (num >= -20) return 'level-good'
  if (num >= -28) return 'level-warning'
  return 'level-critical'
}

const formatTimestamp = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.cable-optical-tooltip {
  position: fixed;
  z-index: 10000;
  background: var(--bg-primary, #1e293b);
  border: 1px solid var(--border-color, #334155);
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
  min-width: 320px;
  max-width: 400px;
  padding: 0;
  pointer-events: none;
  font-size: 13px;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.tooltip-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color, #334155);
  background: var(--bg-secondary, #0f172a);
  border-radius: 8px 8px 0 0;
}

.tooltip-title {
  font-weight: 600;
  color: var(--text-primary, #f1f5f9);
  font-size: 14px;
  margin-bottom: 4px;
}

.tooltip-subtitle {
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
}

.tooltip-loading,
.tooltip-error {
  padding: 24px 16px;
  text-align: center;
  color: var(--text-secondary, #94a3b8);
}

.tooltip-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-color, #334155);
  border-top-color: var(--primary-color, #3b82f6);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.tooltip-error {
  color: var(--error-color, #ef4444);
}

.tooltip-content {
  padding: 12px 16px;
}

.interface-section {
  margin-bottom: 16px;
}

.interface-section:last-of-type {
  margin-bottom: 0;
}

.interface-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-color, #334155);
}

.interface-icon {
  font-size: 16px;
}

.interface-name {
  font-weight: 600;
  color: var(--text-primary, #f1f5f9);
  font-size: 13px;
}

.optical-levels {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-left: 24px;
}

.interface-placeholder {
  padding: 8px 24px;
  font-size: 12px;
  color: var(--text-tertiary, #64748b);
}

.level-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.level-label {
  color: var(--text-secondary, #94a3b8);
  font-size: 12px;
}

.level-value {
  font-weight: 600;
  font-size: 13px;
  padding: 2px 8px;
  border-radius: 4px;
}

.level-excellent {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}

.level-good {
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
}

.level-warning {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
}

.level-critical {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.level-unknown {
  color: var(--text-secondary, #94a3b8);
  background: rgba(148, 163, 184, 0.1);
}

.attenuation-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color, #334155);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.attenuation-label {
  color: var(--text-secondary, #94a3b8);
  font-size: 12px;
}

.attenuation-value {
  font-weight: 600;
  color: var(--text-primary, #f1f5f9);
  font-size: 13px;
}

.tooltip-footer {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color, #334155);
  text-align: center;
}

.timestamp {
  font-size: 11px;
  color: var(--text-tertiary, #64748b);
}

.tooltip-no-data {
  padding: 24px 16px;
  text-align: center;
  color: var(--text-secondary, #94a3b8);
}
</style>
