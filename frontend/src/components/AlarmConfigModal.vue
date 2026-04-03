<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="alarm-modal-overlay" @click.self="close">
        <div class="alarm-modal-container" :class="{ dark: isDark }">
          <!-- Header -->
          <div class="alarm-modal-header">
            <h3>
              <i class="fas fa-bell"></i>
              Alarme de Sinal Óptico - {{ port?.name }}
            </h3>
            <button class="close-button" @click="close">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <!-- Content -->
          <div class="alarm-modal-content">
            <!-- Current Signal -->
            <div class="current-signal">
              <h4>Sinal Atual</h4>
              <div class="signal-display">
                <div class="signal-item">
                  <span class="label">RX:</span>
                  <span class="value" :class="getSignalClass(port?.optical_rx_power)">
                    {{ formatPower(port?.optical_rx_power) }} dBm
                  </span>
                </div>
                <div class="signal-item">
                  <span class="label">TX:</span>
                  <span class="value" :class="getSignalClass(port?.optical_tx_power)">
                    {{ formatPower(port?.optical_tx_power) }} dBm
                  </span>
                </div>
              </div>
            </div>

            <!-- Signal History Chart -->
            <div class="signal-history">
              <h4>Histórico do Sinal (últimas 24h)</h4>
              <div class="chart-container">
                <canvas ref="chartCanvas"></canvas>
              </div>
            </div>

            <!-- Alarm Configuration -->
            <div class="alarm-config">
              <h4>Configuração de Alarme</h4>
              
              <!-- Info sobre configuração global -->
              <div v-if="!alarmEnabled" class="config-info">
                <i class="fas fa-info-circle"></i>
                <span>Valores padrão globais: {{ globalWarningThreshold }} dBm (Atenção) / {{ globalCriticalThreshold }} dBm (Crítico)</span>
              </div>
              
              <div class="form-field">
                <label>
                  <input type="checkbox" v-model="alarmEnabled" />
                  Habilitar Alarme Personalizado
                </label>
                <p v-if="!alarmEnabled" class="field-help">Quando desabilitado, usa configuração global do sistema</p>
              </div>

              <div v-if="alarmEnabled" class="threshold-config">
                <div class="form-field">
                  <label>Threshold de Atenção (dBm)</label>
                  <input 
                    v-model.number="warningThreshold" 
                    type="number" 
                    step="0.5" 
                    class="form-input"
                    placeholder="-24"
                  />
                  <p class="field-help">Alerta quando sinal ficar abaixo deste valor</p>
                </div>

                <div class="form-field">
                  <label>Threshold Crítico (dBm)</label>
                  <input 
                    v-model.number="criticalThreshold" 
                    type="number" 
                    step="0.5" 
                    class="form-input"
                    placeholder="-27"
                  />
                  <p class="field-help">Alarme crítico quando sinal ficar abaixo deste valor</p>
                </div>

                <div class="form-field">
                  <label>Notificações</label>
                  <div class="notification-options">
                    <label>
                      <input type="checkbox" v-model="notifications.email" />
                      <i class="fas fa-envelope"></i>
                      E-mail
                    </label>
                    <label>
                      <input type="checkbox" v-model="notifications.dashboard" />
                      <i class="fas fa-th-large"></i>
                      Dashboard
                    </label>
                    <label>
                      <input type="checkbox" v-model="notifications.whatsapp" />
                      <i class="fab fa-whatsapp"></i>
                      WhatsApp
                    </label>
                    <label>
                      <input type="checkbox" v-model="notifications.telegram" />
                      <i class="fab fa-telegram-plane"></i>
                      Telegram
                    </label>
                    <label>
                      <input type="checkbox" v-model="notifications.webhook" />
                      <i class="fas fa-link"></i>
                      Webhook
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="alarm-modal-footer">
            <button class="btn-secondary" @click="close">
              <i class="fas fa-times"></i>
              Cancelar
            </button>
            <button class="btn-primary" @click="saveAlarmConfig" :disabled="saving">
              <i class="fas fa-save"></i>
              {{ saving ? 'Salvando...' : 'Salvar Configuração' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'
import { useEscapeKey } from '@/composables/useEscapeKey'
import { useUiStore } from '@/stores/ui'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  port: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'saved'])

const { get, patch } = useApi()
const { success, error: notifyError } = useNotification()
const uiStore = useUiStore()

// Gerenciar ESC key
useEscapeKey(() => close(), { isOpen: computed(() => props.isOpen) })

const alarmEnabled = ref(false)
const warningThreshold = ref(-24)
const criticalThreshold = ref(-27)
const notifications = ref({
  email: true,
  dashboard: true,
  webhook: false,
  whatsapp: false,
  telegram: false
})
const saving = ref(false)
const chartCanvas = ref(null)
let chartInstance = null

// Global thresholds from configuration
const globalWarningThreshold = ref(-24)
const globalCriticalThreshold = ref(-27)

const isDark = computed(() => uiStore.theme === 'dark')

// Load global thresholds from configuration
const loadGlobalThresholds = async () => {
  try {
    const response = await get('/setup_app/api/config/')
    if (response.success && response.configuration) {
      const cfg = response.configuration
      globalWarningThreshold.value = parseFloat(cfg.OPTICAL_RX_WARNING_THRESHOLD || '-24')
      globalCriticalThreshold.value = parseFloat(cfg.OPTICAL_RX_CRITICAL_THRESHOLD || '-27')
    }
  } catch (error) {
    console.log('[AlarmConfigModal] Could not load global thresholds, using defaults')
  }
}

const close = () => {
  emit('close')
}

const formatPower = (value) => {
  if (value === null || value === undefined) return 'N/A'
  return value.toFixed(2)
}

const getSignalClass = (value) => {
  if (value === null || value === undefined) return ''
  if (value < criticalThreshold.value) return 'signal-critical'
  if (value < warningThreshold.value) return 'signal-warning'
  return 'signal-good'
}

const loadHistoricalData = async () => {
  if (!props.port?.id) return
  
  try {
    // Tentar buscar dados reais do endpoint com período de 24h
    const response = await get(`/api/v1/ports/${props.port.id}/optical_history/`, { hours: 24 })
    
    if (response && Array.isArray(response) && response.length > 0) {
      // Converter formato do backend para formato do gráfico
      const chartData = response.map(snapshot => ({
        timestamp: new Date(snapshot.timestamp).getTime(),
        rx: snapshot.rx_power,
        tx: snapshot.tx_power
      }))
      
      await nextTick()
      renderChart(chartData)
      return
    }
  } catch (error) {
    console.warn('Falha ao carregar histórico real, usando dados mockados:', error)
  }
  
  // Fallback para mock data se API falhar ou não retornar dados
  const mockData = generateMockData()
  await nextTick()
  renderChart(mockData)
}

const generateMockData = () => {
  const now = Date.now()
  const points = []
  
  for (let i = 24; i >= 0; i--) {
    const timestamp = now - (i * 60 * 60 * 1000) // hourly points
    const rx = props.port?.optical_rx_power || -22
    const tx = props.port?.optical_tx_power || -3
    
    // Add some variation
    const rxVariation = (Math.random() - 0.5) * 2
    const txVariation = (Math.random() - 0.5) * 1
    
    points.push({
      timestamp,
      rx: rx + rxVariation,
      tx: tx + txVariation
    })
  }
  
  return points
}

const renderChart = (data) => {
  if (!chartCanvas.value) return
  
  const ctx = chartCanvas.value.getContext('2d')
  const width = chartCanvas.value.width = chartCanvas.value.offsetWidth
  const height = chartCanvas.value.height = 200
  
  // Clear canvas
  ctx.clearRect(0, 0, width, height)
  
  // Setup
  const padding = 40
  const graphWidth = width - padding * 2
  const graphHeight = height - padding * 2
  
  // Find min/max for scaling
  const rxValues = data.map(d => d.rx)
  const txValues = data.map(d => d.tx)
  const allValues = [...rxValues, ...txValues]
  const minValue = Math.min(...allValues) - 2
  const maxValue = Math.max(...allValues) + 2
  
  // Draw grid
  ctx.strokeStyle = isDark.value ? '#334155' : '#e2e8f0'
  ctx.lineWidth = 1
  
  for (let i = 0; i <= 5; i++) {
    const y = padding + (graphHeight / 5) * i
    ctx.beginPath()
    ctx.moveTo(padding, y)
    ctx.lineTo(width - padding, y)
    ctx.stroke()
  }
  
  // Draw threshold lines
  const drawThreshold = (value, color, label) => {
    const y = padding + graphHeight - ((value - minValue) / (maxValue - minValue)) * graphHeight
    ctx.strokeStyle = color
    ctx.lineWidth = 1
    ctx.setLineDash([5, 5])
    ctx.beginPath()
    ctx.moveTo(padding, y)
    ctx.lineTo(width - padding, y)
    ctx.stroke()
    ctx.setLineDash([])
    
    // Label
    ctx.fillStyle = color
    ctx.font = '10px sans-serif'
    ctx.fillText(label, width - padding + 5, y + 4)
  }
  
  drawThreshold(warningThreshold.value, '#f59e0b', 'Atenção')
  drawThreshold(criticalThreshold.value, '#ef4444', 'Crítico')
  
  // Draw RX line
  ctx.strokeStyle = '#3b82f6'
  ctx.lineWidth = 2
  ctx.beginPath()
  
  data.forEach((point, index) => {
    const x = padding + (graphWidth / (data.length - 1)) * index
    const y = padding + graphHeight - ((point.rx - minValue) / (maxValue - minValue)) * graphHeight
    
    if (index === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  
  ctx.stroke()
  
  // Draw TX line
  ctx.strokeStyle = '#8b5cf6'
  ctx.lineWidth = 2
  ctx.beginPath()
  
  data.forEach((point, index) => {
    const x = padding + (graphWidth / (data.length - 1)) * index
    const y = padding + graphHeight - ((point.tx - minValue) / (maxValue - minValue)) * graphHeight
    
    if (index === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  
  ctx.stroke()
  
  // Draw legend
  ctx.font = '12px sans-serif'
  ctx.fillStyle = '#3b82f6'
  ctx.fillText('RX', 10, 20)
  ctx.fillStyle = '#8b5cf6'
  ctx.fillText('TX', 40, 20)
  
  // Draw Y-axis labels
  ctx.fillStyle = isDark.value ? '#94a3b8' : '#64748b'
  ctx.font = '10px sans-serif'
  ctx.textAlign = 'right'
  
  for (let i = 0; i <= 5; i++) {
    const value = minValue + ((maxValue - minValue) / 5) * (5 - i)
    const y = padding + (graphHeight / 5) * i
    ctx.fillText(value.toFixed(1), padding - 5, y + 4)
  }
}

const saveAlarmConfig = async () => {
  if (!props.port?.id) return
  
  saving.value = true
  try {
    await patch(`/api/v1/ports/${props.port.id}/`, {
      alarm_enabled: alarmEnabled.value,
      alarm_warning_threshold: warningThreshold.value,
      alarm_critical_threshold: criticalThreshold.value,
      alarm_notifications: notifications.value
    })
    success('Alarme configurado', 'As configurações de alarme foram salvas.')
    emit('saved') // Notify parent to reload ports
    close()
  } catch (error) {
    console.error('[AlarmConfigModal] Error saving alarm config:', error)
    notifyError('Erro', 'Não foi possível salvar as configurações.')
  } finally {
    saving.value = false
  }
}

watch(() => props.isOpen, async (newVal) => {
  if (newVal && props.port) {
    // Load global thresholds first
    await loadGlobalThresholds()
    
    // Load port-specific config or use global defaults
    alarmEnabled.value = props.port.alarm_enabled || false
    warningThreshold.value = props.port.alarm_warning_threshold || globalWarningThreshold.value
    criticalThreshold.value = props.port.alarm_critical_threshold || globalCriticalThreshold.value
    notifications.value = props.port.alarm_notifications || {
      email: true,
      dashboard: true,
      webhook: false,
      whatsapp: false,
      telegram: false
    }
    
    await loadHistoricalData()
  }
})

// Redraw chart when thresholds change
watch([warningThreshold, criticalThreshold], () => {
  if (props.isOpen && chartCanvas.value) {
    loadHistoricalData()
  }
})
</script>

<style scoped>
.alarm-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 14000;
  padding: 20px;
}

.alarm-modal-container {
  background: #ffffff;
  border-radius: 12px;
  max-width: 700px;
  width: 100%;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.alarm-modal-container.dark {
  background: #1e293b;
  color: #f1f5f9;
}

.alarm-modal-header {
  padding: 20px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.alarm-modal-container.dark .alarm-modal-header {
  border-bottom-color: #334155;
}

.alarm-modal-header h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #1e293b;
}

.alarm-modal-container.dark .alarm-modal-header h3 {
  color: #f1f5f9;
}

.alarm-modal-header h3 i {
  color: #f59e0b;
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

.alarm-modal-container.dark .close-button {
  background: #334155;
  color: #cbd5e1;
}

.close-button:hover {
  background: #e2e8f0;
  transform: scale(1.1);
}

.alarm-modal-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.current-signal,
.alarm-config,
.signal-history {
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid #e2e8f0;
}

.alarm-modal-container.dark .current-signal,
.alarm-modal-container.dark .alarm-config,
.alarm-modal-container.dark .signal-history {
  border-bottom-color: #334155;
}

.current-signal:last-child,
.alarm-config:last-child,
.signal-history:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

h4 {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: #1e293b;
}

.alarm-modal-container.dark h4 {
  color: #f1f5f9;
}

.signal-display {
  display: flex;
  gap: 16px;
}

.signal-item {
  flex: 1;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alarm-modal-container.dark .signal-item {
  background: #0f172a;
}

.signal-item .label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
}

.signal-item .value {
  font-size: 18px;
  font-weight: 700;
  font-family: 'Monaco', 'Courier New', monospace;
}

.signal-good {
  color: #10b981;
}

.signal-warning {
  color: #f59e0b;
}

.signal-critical {
  color: #ef4444;
}

.form-field {
  margin-bottom: 16px;
}

.config-info {
  padding: 12px;
  background: #dbeafe;
  border-left: 4px solid #3b82f6;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #1e40af;
  display: flex;
  align-items: center;
  gap: 8px;
}

.alarm-modal-container.dark .config-info {
  background: #1e3a8a;
  color: #93c5fd;
  border-left-color: #60a5fa;
}

.config-info i {
  font-size: 16px;
}

.form-field label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
  margin-bottom: 6px;
}

.alarm-modal-container.dark .form-field label {
  color: #f1f5f9;
}

.form-field label input[type="checkbox"] {
  margin-right: 8px;
}

.form-input {
  width: 100%;
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  color: #1e293b;
  background: white;
}

.alarm-modal-container.dark .form-input {
  background: #0f172a;
  border-color: #334155;
  color: #f1f5f9;
}

.form-input:focus {
  outline: none;
  border-color: #667eea;
}

.field-help {
  font-size: 12px;
  color: #64748b;
  margin: 4px 0 0 0;
}

.threshold-config {
  margin-top: 16px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
}

.alarm-modal-container.dark .threshold-config {
  background: #0f172a;
}

.notification-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notification-options label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: normal;
}

.notification-options label i {
  width: 16px;
  text-align: center;
  color: #667eea;
}

.notification-options label i.fa-whatsapp {
  color: #25d366;
}

.notification-options label i.fa-telegram-plane {
  color: #0088cc;
}

.notification-options label i.fa-envelope {
  color: #ea4335;
}

.notification-options label i.fa-th-large {
  color: #667eea;
}

.notification-options label i.fa-link {
  color: #64748b;
}

.chart-container {
  background: #f8fafc;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
}

.alarm-modal-container.dark .chart-container {
  background: #0f172a;
}

.chart-container canvas {
  width: 100%;
  display: block;
}

.alarm-modal-footer {
  padding: 16px 20px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.alarm-modal-container.dark .alarm-modal-footer {
  border-top-color: #334155;
}

.btn-primary,
.btn-secondary {
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5568d3;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f1f5f9;
  color: #475569;
}

.alarm-modal-container.dark .btn-secondary {
  background: #334155;
  color: #cbd5e1;
}

.btn-secondary:hover {
  background: #e2e8f0;
}
</style>
