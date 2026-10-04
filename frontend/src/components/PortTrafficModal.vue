<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="isOpen" class="modal-overlay" @click.self="close">
        <div class="modal-container traffic-modal">
          <!-- Header -->
          <div class="modal-header">
            <div class="header-content">
              <i class="fas fa-chart-line"></i>
              <div>
                <h2>Tráfego de Rede</h2>
                <p class="subtitle">{{ port?.name }} - {{ port?.description || 'Sem descrição' }}</p>
              </div>
            </div>
            <button class="btn-close" @click="close">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <!-- Body -->
          <div class="modal-body">
            <!-- Loading State -->
            <div v-if="loading" class="loading-state">
              <i class="fas fa-spinner fa-spin"></i>
              <span>Carregando dados de tráfego...</span>
            </div>

            <!-- Error State -->
            <div v-else-if="error" class="error-state">
              <i class="fas fa-exclamation-triangle"></i>
              <span>{{ error }}</span>
              <button class="btn-retry" @click="loadTrafficData">
                <i class="fas fa-redo"></i>
                Tentar Novamente
              </button>
            </div>

            <!-- Content -->
            <div v-else-if="trafficData">
              <!-- Period Selector -->
              <div class="period-selector">
                <button
                  v-for="period in periods"
                  :key="period.value"
                  class="period-btn"
                  :class="{ active: selectedPeriod === period.value }"
                  @click="changePeriod(period.value)"
                >
                  {{ period.label }}
                </button>
              </div>

              <!-- Seção: Tráfego de Rede -->
              <div class="collapsible-section">
                <button class="section-header" @click="trafficSectionOpen = !trafficSectionOpen">
                  <div class="section-title">
                    <i class="fas fa-chart-line"></i>
                    <span>Tráfego de Rede</span>
                  </div>
                  <i class="fas" :class="trafficSectionOpen ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
                </button>

                <Transition name="collapse">
                  <div v-show="trafficSectionOpen" class="section-content">
                    <!-- Statistics Cards -->
                    <div class="stats-grid">
                      <div class="stat-card percentile-95">
                        <div class="stat-header">
                          <i class="fas fa-chart-bar"></i>
                          <span>95º Percentil</span>
                        </div>
                        <div class="stat-values">
                          <div class="stat-row">
                            <span class="stat-label">Download:</span>
                            <span class="stat-value">{{ formatBandwidth(trafficData.statistics.percentile_95_in) }}</span>
                          </div>
                          <div class="stat-row">
                            <span class="stat-label">Upload:</span>
                            <span class="stat-value">{{ formatBandwidth(trafficData.statistics.percentile_95_out) }}</span>
                          </div>
                        </div>
                      </div>

                      <div class="stat-card">
                        <div class="stat-header">
                          <i class="fas fa-chart-line"></i>
                          <span>Média</span>
                        </div>
                        <div class="stat-values">
                          <div class="stat-row">
                            <span class="stat-label">Download:</span>
                            <span class="stat-value">{{ formatBandwidth(trafficData.statistics.avg_in) }}</span>
                          </div>
                          <div class="stat-row">
                            <span class="stat-label">Upload:</span>
                            <span class="stat-value">{{ formatBandwidth(trafficData.statistics.avg_out) }}</span>
                          </div>
                        </div>
                      </div>

                      <div class="stat-card">
                        <div class="stat-header">
                          <i class="fas fa-arrow-up"></i>
                          <span>Pico</span>
                        </div>
                        <div class="stat-values">
                          <div class="stat-row">
                            <span class="stat-label">Download:</span>
                            <span class="stat-value">{{ formatBandwidth(trafficData.statistics.max_in) }}</span>
                          </div>
                          <div class="stat-row">
                            <span class="stat-label">Upload:</span>
                            <span class="stat-value">{{ formatBandwidth(trafficData.statistics.max_out) }}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- Chart -->
                    <div class="chart-container">
                      <TimeSeriesChart ref="trafficChartRef" :series="trafficSeries" unit="Mbps" :begin-at-zero="true" :height="260" empty-message="Sem dados de tráfego para o período selecionado" />
                    </div>
                  </div>
                </Transition>
              </div>

              <!-- Seção: Sinal Óptico -->
              <div v-if="port?.optical_rx_power !== null || port?.optical_tx_power !== null" class="collapsible-section">
                <button class="section-header" @click="opticalSectionOpen = !opticalSectionOpen">
                  <div class="section-title">
                    <i class="fas fa-signal"></i>
                    <span>Sinal Óptico</span>
                  </div>
                  <i class="fas" :class="opticalSectionOpen ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
                </button>

                <Transition name="collapse">
                  <div v-show="opticalSectionOpen" class="section-content">
                    <!-- Current Signal -->
                    <div class="optical-current">
                      <div class="optical-stat">
                        <span class="optical-label">RX:</span>
                        <span class="optical-value" :class="getOpticalClass(port?.optical_rx_power)">
                          {{ formatOptical(port?.optical_rx_power) }} dBm
                        </span>
                      </div>
                      <div class="optical-stat">
                        <span class="optical-label">TX:</span>
                        <span class="optical-value" :class="getOpticalClass(port?.optical_tx_power)">
                          {{ formatOptical(port?.optical_tx_power) }} dBm
                        </span>
                      </div>
                    </div>

                    <!-- Optical Chart -->
                    <div class="chart-container">
                      <TimeSeriesChart ref="opticalChartRef" :series="opticalSeries" :thresholds="opticalThresholds" unit="dBm" :decimals="2" :height="260" :empty-message="opticalEmptyMessage" />
                    </div>

                    <!-- Botão Configurar Alarme -->
                    <div class="alarm-config-section">
                      <button class="btn-config-alarm" @click="openAlarmConfig">
                        <i class="fas fa-bell"></i>
                        Configurar Alarme
                      </button>
                      <div v-if="port?.alarm_enabled" class="alarm-status">
                        <i class="fas fa-check-circle"></i>
                        Alarme Personalizado Ativo
                      </div>
                    </div>
                  </div>
                </Transition>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="modal-footer">
            <button class="btn-secondary" @click="close">
              Fechar
            </button>
            <div class="export-dropdown-wrapper" @click.stop>
              <button class="btn-primary" @click="exportMenuOpen = !exportMenuOpen">
                <i class="fas fa-download"></i>
                Exportar
                <i class="fas fa-chevron-up" :class="{ 'fa-chevron-down': !exportMenuOpen, 'fa-chevron-up': exportMenuOpen }"></i>
              </button>
              <div v-if="exportMenuOpen" class="export-options">
                <button @click="exportCSV"><i class="fas fa-file-csv"></i> CSV</button>
                <button @click="exportPNG"><i class="fas fa-image"></i> PNG</button>
                <button @click="exportPDF"><i class="fas fa-file-pdf"></i> PDF</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Alarm Config Modal -->
    <AlarmConfigModal
      :is-open="showAlarmConfig"
      :port="port"
      @close="closeAlarmConfig"
      @saved="handleAlarmSaved"
    />
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useApi } from '@/composables/useApi'
import { useEscapeKey } from '@/composables/useEscapeKey'
import TimeSeriesChart from './charts/TimeSeriesChart.vue'
import {
  normalizeOpticalHistory,
  OPTICAL_HISTORY_EMPTY_MESSAGE,
  OPTICAL_HISTORY_ERROR_MESSAGE,
} from '@/utils/opticalHistory'
import { bpsToMbps } from '@/utils/opticalSeries'
import AlarmConfigModal from './AlarmConfigModal.vue'

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


const emit = defineEmits(['close', 'alarm-saved'])

const api = useApi()

const loading = ref(false)
const error = ref(null)
const trafficData = ref(null)
const selectedPeriod = ref(24)
const trafficChartRef = ref(null)
const opticalChartRef = ref(null)
// EV-0011: só dados; o gráfico (instância Chart.js, destroy, resize) é do TimeSeriesChart.
const opticalPoints = ref([])
const opticalEmptyMessage = ref(OPTICAL_HISTORY_EMPTY_MESSAGE)
const globalWarningThreshold = ref(-24)
const globalCriticalThreshold = ref(-27)
const trafficSectionOpen = ref(true)
const opticalSectionOpen = ref(true)
const showAlarmConfig = ref(false)
const exportMenuOpen = ref(false)
const close = () => {
  emit('close')
}

// Gerenciar ESC key - ignora quando AlarmConfigModal está aberto
useEscapeKey(() => close(), { isOpen: computed(() => props.isOpen), shouldIgnore: showAlarmConfig })

const periods = [
  { label: '1h', value: 1 },
  { label: '6h', value: 6 },
  { label: '24h', value: 24 },
  { label: '7d', value: 168 }
]

const loadTrafficData = async () => {
  if (!props.port) return

  loading.value = true
  error.value = null

  try {
    const response = await api.get(`/api/v1/ports/${props.port.id}/traffic_history/?hours=${selectedPeriod.value}`)
    trafficData.value = response
    loading.value = false
  } catch (err) {
    console.error('Erro ao carregar dados de tráfego:', err)
    error.value = err.message || 'Erro ao carregar dados de tráfego'
    loading.value = false
  }
}

// EV-0011/EV-0026: séries para o TimeSeriesChart; zero é tráfego zero, null é buraco.
const trafficSeries = computed(() => {
  const history = trafficData.value?.history || []
  if (!history.length) return []
  return [
    { label: 'Download (Mbps)', data: history.map(d => ({ x: d.timestamp, y: bpsToMbps(d.traffic_in) })) },
    { label: 'Upload (Mbps)', data: history.map(d => ({ x: d.timestamp, y: bpsToMbps(d.traffic_out) })) },
  ]
})

const hasOpticalPort = () => props.port?.optical_rx_power !== null || props.port?.optical_tx_power !== null

const changePeriod = async (hours) => {
  selectedPeriod.value = hours
  loadTrafficData()
  if (hasOpticalPort()) {
    await loadOpticalHistory()
  }
}

// Limiares: os da porta, senão os globais da configuração (nunca constantes no componente).
const loadGlobalThresholds = async () => {
  try {
    const response = await api.get('/setup_app/api/config/')
    const cfg = response?.configuration
    if (cfg) {
      globalWarningThreshold.value = parseFloat(cfg.OPTICAL_RX_WARNING_THRESHOLD || '-24')
      globalCriticalThreshold.value = parseFloat(cfg.OPTICAL_RX_CRITICAL_THRESHOLD || '-27')
    }
  } catch (err) {
    console.info('[PortTrafficModal] Limiares globais indisponíveis; mantendo padrão', err?.message)
  }
}

const opticalThresholds = computed(() => [
  { value: props.port?.alarm_warning_threshold ?? globalWarningThreshold.value, label: 'Atenção' },
  { value: props.port?.alarm_critical_threshold ?? globalCriticalThreshold.value, label: 'Crítico', color: '#f87171' },
])

const opticalSeries = computed(() => {
  if (!opticalPoints.value.length) return []
  return [
    { label: 'RX (dBm)', data: opticalPoints.value.map(p => ({ x: p.timestamp, y: p.rx })) },
    { label: 'TX (dBm)', data: opticalPoints.value.map(p => ({ x: p.timestamp, y: p.tx })) },
  ]
})

// EV-0001: sem histórico mostra-se «sem dados» / «erro» — nunca uma série inventada.
// EV-0011: sem AbortController improvisado — a resposta mais recente ganha pelo contador.
let opticalRequestSeq = 0
const loadOpticalHistory = async () => {
  if (!props.port?.id) return
  const seq = ++opticalRequestSeq
  const url = `/api/v1/ports/${props.port.id}/optical_history/`
  const params = { hours: selectedPeriod.value }
  try {
    const response = await api.get(url, params)
    if (seq !== opticalRequestSeq) return // chegou uma resposta mais nova
    opticalEmptyMessage.value = OPTICAL_HISTORY_EMPTY_MESSAGE
    opticalPoints.value = normalizeOpticalHistory(response).points
  } catch (err) {
    if (seq !== opticalRequestSeq) return
    console.error('[PortTrafficModal] Erro ao carregar histórico óptico:', { message: err?.message, url, params })
    opticalPoints.value = []
    opticalEmptyMessage.value = OPTICAL_HISTORY_ERROR_MESSAGE
  }
}

const formatBandwidth = (bps) => {
  if (bps === null || bps === undefined) return 'N/A'
  
  const mbps = bps / 1000000
  if (mbps >= 1000) {
    return `${(mbps / 1000).toFixed(2)} Gbps`
  }
  return `${mbps.toFixed(2)} Mbps`
}

const formatOptical = (value) => {
  if (value === null || value === undefined) return 'N/A'
  return value.toFixed(2)
}

const getOpticalClass = (value) => {
  if (value === null || value === undefined) return ''
  if (value < -27) return 'signal-critical'
  if (value < -24) return 'signal-warning'
  return 'signal-good'
}

const exportCSV = () => {
  exportMenuOpen.value = false
  if (!trafficData.value) return
  const csvContent = [
    ['Timestamp', 'Download (bps)', 'Upload (bps)'].join(','),
    ...trafficData.value.history.map(d => [
      d.timestamp,
      d.traffic_in || '',
      d.traffic_out || ''
    ].join(','))
  ].join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `traffic_${props.port.name}_${new Date().toISOString().split('T')[0]}.csv`
  link.click()
}

/**
 * Combina os dois gráficos (tráfego + óptico) em um único canvas empilhado verticalmente.
 * Retorna um data URL PNG ou null se nenhum canvas estiver disponível.
 */
const escapeHtml = (value) => String(value ?? '')
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

const loadImage = (src) => new Promise((resolve, reject) => {
  const img = new Image()
  img.onload = () => resolve(img)
  img.onerror = reject
  img.src = src
})

/** Junta tráfego + óptico numa só imagem PNG (tema atual, não fundo fixo). */
const buildCombinedImage = async () => {
  const parts = [
    ['Tráfego de Rede', trafficChartRef.value?.toDataURL?.()],
    ['Sinal Óptico', opticalChartRef.value?.toDataURL?.()],
  ].filter(([, data]) => !!data)
  if (!parts.length) return null

  const images = await Promise.all(parts.map(([, data]) => loadImage(data)))
  const GAP = 16
  const PADDING = 20
  const LABEL_HEIGHT = 22
  const styles = getComputedStyle(document.documentElement)
  const bg = styles.getPropertyValue('--surface-card').trim() || '#ffffff'
  const fg = styles.getPropertyValue('--text-secondary').trim() || '#334155'

  const maxWidth = Math.max(...images.map(i => i.width)) + PADDING * 2
  const totalHeight = images.reduce((acc, i) => acc + i.height + LABEL_HEIGHT + GAP, 0) - GAP + PADDING * 2
  const combined = document.createElement('canvas')
  combined.width = maxWidth
  combined.height = totalHeight
  const ctx = combined.getContext('2d')
  ctx.fillStyle = bg
  ctx.fillRect(0, 0, maxWidth, totalHeight)

  let y = PADDING
  images.forEach((img, i) => {
    ctx.fillStyle = fg
    ctx.font = 'bold 13px sans-serif'
    ctx.fillText(parts[i][0], PADDING, y + 14)
    y += LABEL_HEIGHT
    ctx.drawImage(img, PADDING + Math.floor((maxWidth - PADDING * 2 - img.width) / 2), y)
    y += img.height + GAP
  })
  return combined.toDataURL('image/png')
}

const exportPNG = async () => {
  exportMenuOpen.value = false
  const imgData = await buildCombinedImage()
  if (!imgData) return
  const filename = `trafego_optico_${props.port?.name || 'porta'}_${selectedPeriod.value}h`
    .replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_-]/g, '')
  const link = document.createElement('a')
  link.download = `${filename}.png`
  link.href = imgData
  link.click()
}

const exportPDF = async () => {
  exportMenuOpen.value = false
  const imgData = await buildCombinedImage()
  if (!imgData) return
  const device = escapeHtml(props.port?.name || 'Porta')
  const desc = escapeHtml(props.port?.description || '')
  const win = window.open('', '_blank')
  if (!win) {
    console.warn('[PortTrafficModal] Popup bloqueado: não foi possível abrir a janela de impressão')
    return
  }
  win.document.write(`<!DOCTYPE html><html><head><title>${device}</title><style>*{margin:0;padding:0;box-sizing:border-box;}body{background:#fff;display:flex;flex-direction:column;align-items:center;padding:24px;font-family:sans-serif;}h2{font-size:14px;color:#334155;margin-bottom:4px;}p{font-size:12px;color:#64748b;margin-bottom:16px;}img{max-width:100%;border:1px solid #e2e8f0;border-radius:8px;}</style></head><body><h2>${device}</h2><p>${desc} — Período: ${selectedPeriod.value}h</p><img src="${imgData}"/><script>window.onload=()=>{window.print()}<\/script></body></html>`)
  win.document.close()
}

const onDocumentClick = () => { exportMenuOpen.value = false }

onMounted(() => { document.addEventListener('click', onDocumentClick) })

const openAlarmConfig = () => {
  showAlarmConfig.value = true
}

const closeAlarmConfig = () => {
  showAlarmConfig.value = false
}

const handleAlarmSaved = () => {
  // Recarregar dados após salvar configuração de alarme
  showAlarmConfig.value = false
  // Os limiares são computados a partir da porta/configuração: o gráfico redesenha sozinho.
  // Emitir evento para que o componente pai recarregue a porta
  emit('alarm-saved')
}

watch(() => props.isOpen, (newValue) => {
  if (newValue) {
    loadGlobalThresholds()
    loadTrafficData()
    if (hasOpticalPort()) {
      loadOpticalHistory()
    }
  } else {
    opticalPoints.value = []
    trafficData.value = null
  }
})

// Abrir a seção óptica sem histórico carregado dispara o carregamento.
watch(opticalSectionOpen, (isOpen) => {
  if (isOpen && props.isOpen && hasOpticalPort() && !opticalPoints.value.length) {
    loadOpticalHistory()
  }
})

onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick)
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 13000;
  padding: 20px;
  overflow: hidden;
}

.traffic-modal {
  width: 100%;
  max-width: 1000px;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
}

.modal-container {
  background: linear-gradient(135deg, var(--surface-card) 0%, var(--bg-secondary) 100%);
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(59, 130, 246, 0.2);
  overflow: hidden;
}

.modal-header {
  padding: 24px;
  border-bottom: 1px solid rgba(75, 85, 99, 0.3);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(59, 130, 246, 0.05);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-content i {
  font-size: 28px;
  color: #3b82f6;
}

.header-content h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #f3f4f6;
}

.subtitle {
  margin: 4px 0 0 0;
  font-size: 14px;
  color: #9ca3af;
}

.btn-close {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  border: none;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-close:hover {
  background: rgba(239, 68, 68, 0.2);
  transform: scale(1.05);
}

.modal-body {
  padding: 20px 24px;
  /* Use flex layout instead of grid for better control */
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  overflow-x: hidden;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 60px 20px;
  color: #9ca3af;
}

.loading-state i {
  font-size: 48px;
  color: #3b82f6;
}

.error-state i {
  font-size: 48px;
  color: #ef4444;
}

.btn-retry {
  margin-top: 12px;
  padding: 10px 20px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid #3b82f6;
  border-radius: 8px;
  color: #3b82f6;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-retry:hover {
  background: rgba(59, 130, 246, 0.2);
  transform: translateY(-1px);
}

.period-selector {
  display: flex;
  gap: 8px;
  padding: 4px;
  background: rgba(31, 41, 55, 0.5);
  border-radius: 12px;
  width: fit-content;
  flex-shrink: 0;
}

.period-btn {
  padding: 8px 20px;
  border: none;
  background: transparent;
  color: #9ca3af;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.period-btn.active {
  background: #3b82f6;
  color: white;
}

.period-btn:hover:not(.active) {
  background: rgba(59, 130, 246, 0.1);
  color: #60a5fa;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 12px;
  /* No bottom margin; grid gap above handles spacing */
  margin: 0;
  align-items: stretch;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .chart-container {
    height: 300px;
    padding: 12px;
  }
  
  .modal-overlay {
    padding: 10px;
  }
  
  .modal-body {
    padding: 16px;
  }
}

.stat-card {
  background: linear-gradient(135deg, rgba(31, 41, 55, 0.8) 0%, rgba(17, 24, 39, 0.9) 100%);
  border: 1px solid rgba(75, 85, 99, 0.3);
  border-radius: 12px;
  padding: 16px;
}

.stat-card.percentile-95 {
  border-color: rgba(59, 130, 246, 0.5);
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(17, 24, 39, 0.9) 100%);
}

.stat-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  color: #9ca3af;
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-header i {
  color: #3b82f6;
  font-size: 18px;
}

.stat-values {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label {
  color: #9ca3af;
  font-size: 13px;
}

.stat-value {
  color: #f3f4f6;
  font-size: 18px;
  font-weight: 700;
}

.chart-container {
  background: rgba(31, 41, 55, 0.5);
  border: 1px solid rgba(75, 85, 99, 0.3);
  border-radius: 12px;
  padding: 12px;
  height: 280px;
  position: relative;
  overflow: hidden;
}

.chart-container canvas {
  /* Let Chart.js handle sizing with maintainAspectRatio: false */
  max-width: 100%;
  max-height: 100%;
}

.modal-footer {
  padding: 20px 24px;
  border-top: 1px solid rgba(75, 85, 99, 0.3);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background: rgba(17, 24, 39, 0.5);
}

.btn-secondary,
.btn-primary {
  padding: 10px 24px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-secondary {
  background: rgba(107, 114, 128, 0.1);
  color: #9ca3af;
  border: 1px solid rgba(107, 114, 128, 0.3);
}

.btn-secondary:hover {
  background: rgba(107, 114, 128, 0.2);
  transform: translateY(-1px);
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.3);
}

.export-dropdown-wrapper {
  position: relative;
}

.export-options {
  position: absolute;
  bottom: calc(100% + 6px);
  right: 0;
  background: var(--surface-card);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  overflow: hidden;
  min-width: 130px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  z-index: 10;
}

.export-options button {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 9px 14px;
  background: transparent;
  border: none;
  color: #e2e8f0;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
  text-align: left;
}

.export-options button:hover {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.export-options button i {
  width: 14px;
  color: #94a3b8;
}

/* Transitions */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-container,
.modal-fade-leave-active .modal-container {
  transition: transform 0.3s ease;
}

.modal-fade-enter-from .modal-container,
.modal-fade-leave-to .modal-container {
  transform: scale(0.9);
}

/* Collapsible Sections */
.collapsible-section {
  margin-bottom: 20px;
  border: 1px solid rgba(75, 85, 99, 0.3);
  border-radius: 12px;
  overflow: hidden;
  background: rgba(31, 41, 55, 0.5);
}

.section-header {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.section-header:hover {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
  font-weight: 600;
  color: #f3f4f6;
}

.section-title i {
  color: #3b82f6;
  font-size: 18px;
}

.section-header i.fa-chevron-up,
.section-header i.fa-chevron-down {
  color: #9ca3af;
  transition: transform 0.2s;
}

.section-content {
  padding: 20px;
}

/* Collapse Transition */
.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.collapse-enter-from,
.collapse-leave-to {
  opacity: 0;
  max-height: 0;
  padding: 0 20px;
}

.collapse-enter-to,
.collapse-leave-from {
  opacity: 1;
  max-height: 2000px;
}

/* Optical Signal Styles */
.optical-current {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.optical-stat {
  background: linear-gradient(135deg, rgba(31, 41, 55, 0.8) 0%, rgba(17, 24, 39, 0.9) 100%);
  border: 1px solid rgba(75, 85, 99, 0.3);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.optical-label {
  font-size: 14px;
  font-weight: 600;
  color: #9ca3af;
  text-transform: uppercase;
}

.optical-value {
  font-size: 24px;
  font-weight: 700;
}

.optical-value.signal-good {
  color: #10b981;
}

.optical-value.signal-warning {
  color: #f59e0b;
}

.optical-value.signal-critical {
  color: #ef4444;
}

/* Alarm Configuration Section */
.alarm-config-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(75, 85, 99, 0.3);
  display: flex;
  align-items: center;
  gap: 16px;
}

.btn-config-alarm {
  padding: 12px 24px;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.2) 0%, rgba(251, 191, 36, 0.1) 100%);
  border: 1px solid rgba(245, 158, 11, 0.4);
  border-radius: 8px;
  color: #fbbf24;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-config-alarm:hover {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.3) 0%, rgba(251, 191, 36, 0.2) 100%);
  border-color: rgba(245, 158, 11, 0.6);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

.btn-config-alarm i {
  font-size: 16px;
}

.alarm-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 8px;
  color: #10b981;
  font-size: 13px;
  font-weight: 500;
}

.alarm-status i {
  font-size: 14px;
}
</style>
