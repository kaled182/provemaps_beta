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
                      <canvas ref="chartCanvas"></canvas>
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
                      <canvas ref="opticalChartCanvas" style="width: 100% !important; height: 100% !important;"></canvas>
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
            <button class="btn-primary" @click="exportData">
              <i class="fas fa-download"></i>
              Exportar Dados
            </button>
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
import { ref, computed, watch, onUnmounted, onMounted, nextTick } from 'vue'
import { useApi } from '@/composables/useApi'
import { useEscapeKey } from '@/composables/useEscapeKey'
import Chart from 'chart.js/auto'
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

console.log('[PortTrafficModal] Props iniciais - isOpen:', props.isOpen, 'port:', props.port)

onMounted(() => {
  console.log('[PortTrafficModal] Componente montado')
})

const emit = defineEmits(['close', 'alarm-saved'])

const api = useApi()

const loading = ref(false)
const error = ref(null)
const trafficData = ref(null)
const selectedPeriod = ref(24)
const chartCanvas = ref(null)
const opticalChartCanvas = ref(null)
const trafficSectionOpen = ref(true)
const opticalSectionOpen = ref(true)
const showAlarmConfig = ref(false)
let chartInstance = null
let opticalChartInstance = null
let opticalChartData = null // Armazenar dados para tooltips
let opticalChartConfig = null // Armazenar configuração do gráfico

const close = () => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
  if (opticalChartInstance) {
    opticalChartInstance.destroy()
    opticalChartInstance = null
  }
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
    
    console.log('[PortTrafficModal] Dados recebidos:', response)
    console.log('[PortTrafficModal] History points:', response.history?.length)
    
    // Definir os dados E parar o loading para o DOM renderizar
    trafficData.value = response
    loading.value = false  // Parar loading ANTES do nextTick
    
    // AGUARDAR Vue renderizar o conteúdo (v-else-if="trafficData")
    await nextTick()
    await nextTick()
    await nextTick() // Múltiplos ticks para garantir
    
    console.log('[PortTrafficModal] Após nextTick - chartCanvas.value:', chartCanvas.value)
    
    if (chartCanvas.value) {
      renderChart()
    } else {
      console.error('[PortTrafficModal] Canvas ainda não disponível!')
      // Tentar novamente após mais tempo
      setTimeout(() => {
        console.log('[PortTrafficModal] Retry - chartCanvas.value:', chartCanvas.value)
        if (chartCanvas.value) {
          renderChart()
        }
      }, 500)
    }
  } catch (err) {
    console.error('Erro ao carregar dados de tráfego:', err)
    error.value = err.message || 'Erro ao carregar dados de tráfego'
    loading.value = false
  }
}

const renderChart = () => {
  console.log('[PortTrafficModal] renderChart chamado')
  console.log('[PortTrafficModal] chartCanvas.value:', chartCanvas.value)
  console.log('[PortTrafficModal] trafficData.value:', trafficData.value)
  
  if (!chartCanvas.value) {
    console.error('[PortTrafficModal] Canvas não disponível!')
    return
  }
  
  if (!trafficData.value) {
    console.error('[PortTrafficModal] Dados de tráfego não disponíveis!')
    return
  }

  // Destruir gráfico anterior
  if (chartInstance) {
    chartInstance.destroy()
  }

  const ctx = chartCanvas.value.getContext('2d')
  const history = trafficData.value.history || []
  
  console.log('[PortTrafficModal] Renderizando gráfico com', history.length, 'pontos')

  const labels = history.map(d => {
    const date = new Date(d.timestamp)
    return date.toLocaleString('pt-BR', { 
      month: '2-digit', 
      day: '2-digit', 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  })

  const trafficInData = history.map(d => d.traffic_in ? d.traffic_in / 1000000 : null) // Converter para Mbps
  const trafficOutData = history.map(d => d.traffic_out ? d.traffic_out / 1000000 : null)

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Download (Mbps)',
          data: trafficInData,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 5
        },
        {
          label: 'Upload (Mbps)',
          data: trafficOutData,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 5
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      layout: {
        padding: {
          top: 5,
          right: 5,
          bottom: 5,
          left: 5
        }
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            color: '#9ca3af',
            font: { size: 12 }
          }
        },
        tooltip: {
          backgroundColor: 'rgba(17, 24, 39, 0.95)',
          titleColor: '#f3f4f6',
          bodyColor: '#d1d5db',
          borderColor: '#374151',
          borderWidth: 1,
          padding: 12,
          displayColors: true
        }
      },
      scales: {
        x: {
          grid: {
            color: 'rgba(75, 85, 99, 0.2)',
            drawBorder: false
          },
          ticks: {
            color: '#9ca3af',
            maxRotation: 45,
            minRotation: 45,
            font: { size: 10 }
          }
        },
        y: {
          grid: {
            color: 'rgba(75, 85, 99, 0.2)',
            drawBorder: false
          },
          ticks: {
            color: '#9ca3af',
            font: { size: 11 },
            callback: value => `${value.toFixed(1)} Mbps`
          },
          beginAtZero: true
        }
      }
    }
  })
}

const changePeriod = async (hours) => {
  selectedPeriod.value = hours
  loadTrafficData()
  // Também atualizar o gráfico óptico se disponível
  if (opticalSectionOpen.value && (props.port?.optical_rx_power !== null || props.port?.optical_tx_power !== null)) {
    await nextTick() // Garantir que o DOM está atualizado
    await renderOpticalChart() // Aguardar o carregamento dos dados
  }
}

// Versão canvas (mesma lógica usada no AlarmConfigModal) para garantir renderização
const renderOpticalCanvasChart = (data) => {
  if (!opticalChartCanvas.value) return
  const canvas = opticalChartCanvas.value
  const ctx = canvas.getContext('2d')

  // Obter dimensões reais do container pai
  const container = canvas.parentElement
  if (!container) return
  
  const containerRect = container.getBoundingClientRect()
  const width = canvas.width = containerRect.width
  const height = canvas.height = containerRect.height

  // Limpar
  ctx.clearRect(0, 0, width, height)

  // Guardas
  if (!Array.isArray(data) || data.length === 0) {
    ctx.fillStyle = '#9ca3af'
    ctx.font = '12px sans-serif'
    ctx.fillText('Sem dados de histórico para o período selecionado', 16, 24)
    return
  }

  // Padding ajustado para não cortar nada e ocupar melhor o espaço
  const padding = { top: 40, right: 20, bottom: 50, left: 70 }
  const graphWidth = width - padding.left - padding.right
  const graphHeight = height - padding.top - padding.bottom

  const rxValues = data.map(d => d.rx).filter(v => v !== null)
  const txValues = data.map(d => d.tx).filter(v => v !== null)
  const allValues = [...rxValues, ...txValues]
  const minValue = Math.min(...allValues) - 3
  const maxValue = Math.max(...allValues) + 3

  // Grade horizontal
  ctx.strokeStyle = 'rgba(75, 85, 99, 0.3)'
  ctx.lineWidth = 1
  for (let i = 0; i <= 5; i++) {
    const y = padding.top + (graphHeight / 5) * i
    ctx.beginPath()
    ctx.moveTo(padding.left, y)
    ctx.lineTo(width - padding.right, y)
    ctx.stroke()
  }

  // Desenhar linhas de threshold (se configuradas)
  const drawThreshold = (value, color, label) => {
    if (value === null || value === undefined) return
    const y = padding.top + graphHeight - ((value - minValue) / (maxValue - minValue)) * graphHeight
    
    // Linhas mais transparentes (opacas)
    ctx.strokeStyle = color + '40' // Adiciona 40 (25% opacidade) ao final da cor hex
    ctx.lineWidth = 2
    ctx.setLineDash([5, 5])
    ctx.beginPath()
    ctx.moveTo(padding.left, y)
    ctx.lineTo(width - padding.right, y)
    ctx.stroke()
    ctx.setLineDash([])
    
    // Label posicionado à esquerda do eixo Y com mais transparência
    ctx.fillStyle = color + '80' // 50% opacidade
    ctx.font = '10px sans-serif'
    ctx.fontWeight = 'bold'
    ctx.textAlign = 'right'
    ctx.fillText(label, padding.left - 15, y - 3)
  }

  const warningThreshold = props.port?.alarm_warning_threshold || -24
  const criticalThreshold = props.port?.alarm_critical_threshold || -27
  
  drawThreshold(warningThreshold, '#f59e0b', 'Atenção')
  drawThreshold(criticalThreshold, '#ef4444', 'Crítico')

  // Linhas RX
  ctx.strokeStyle = '#3b82f6'
  ctx.lineWidth = 2.5
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.beginPath()
  data.forEach((point, index) => {
    if (point.rx === null) return
    const x = padding.left + (graphWidth / Math.max(data.length - 1, 1)) * index
    const y = padding.top + graphHeight - ((point.rx - minValue) / (maxValue - minValue)) * graphHeight
    if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
  })
  ctx.stroke()
  // Linhas TX
  ctx.strokeStyle = '#8b5cf6'
  ctx.lineWidth = 2.5
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.beginPath()
  data.forEach((point, index) => {
    if (point.tx === null) return
    const x = padding.left + (graphWidth / Math.max(data.length - 1, 1)) * index
    const y = padding.top + graphHeight - ((point.tx - minValue) / (maxValue - minValue)) * graphHeight
    if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
  })
  ctx.stroke()

  // Legenda com fundo
  const legendX = padding.left
  const legendY = 20
  ctx.font = 'bold 13px sans-serif'
  
  // RX Legend
  ctx.fillStyle = '#3b82f6'
  ctx.fillText('RX', legendX, legendY)
  
  // TX Legend
  ctx.fillStyle = '#8b5cf6'
  ctx.fillText('TX', legendX + 40, legendY)
  
  // Eixo Y com valores
  ctx.fillStyle = '#9ca3af'
  ctx.font = '11px sans-serif'
  ctx.textAlign = 'right'
  for (let i = 0; i <= 5; i++) {
    const value = minValue + ((maxValue - minValue) / 5) * (5 - i)
    const y = padding.top + (graphHeight / 5) * i
    ctx.fillText(value.toFixed(1) + ' dBm', padding.left - 10, y + 4)
  }
  
  // Armazenar dados e configuração para tooltips
  opticalChartData = data
  opticalChartConfig = { padding, minValue, maxValue, graphWidth, graphHeight, width, height }
}

// Função para desenhar tooltip no gráfico óptico
const drawOpticalTooltip = (mouseX, mouseY) => {
  if (!opticalChartCanvas.value || !opticalChartData || !opticalChartConfig) return
  
  const canvas = opticalChartCanvas.value
  const ctx = canvas.getContext('2d')
  const { padding, minValue, maxValue, graphWidth, graphHeight } = opticalChartConfig
  
  // Encontrar o ponto mais próximo do mouse
  let closestIndex = -1
  let minDistance = Infinity
  
  opticalChartData.forEach((point, index) => {
    const x = padding.left + (graphWidth / Math.max(opticalChartData.length - 1, 1)) * index
    const distance = Math.abs(x - mouseX)
    if (distance < minDistance) {
      minDistance = distance
      closestIndex = index
    }
  })
  
  if (closestIndex === -1 || minDistance > 50) return // Muito longe
  
  const point = opticalChartData[closestIndex]
  const pointX = padding.left + (graphWidth / Math.max(opticalChartData.length - 1, 1)) * closestIndex
  
  // Redesenhar gráfico
  renderOpticalCanvasChart(opticalChartData)
  
  // Desenhar linha vertical
  ctx.strokeStyle = 'rgba(156, 163, 175, 0.5)'
  ctx.lineWidth = 1
  ctx.setLineDash([2, 2])
  ctx.beginPath()
  ctx.moveTo(pointX, padding.top)
  ctx.lineTo(pointX, padding.top + graphHeight)
  ctx.stroke()
  ctx.setLineDash([])
  
  // Desenhar pontos destacados
  if (point.rx !== null) {
    const rxY = padding.top + graphHeight - ((point.rx - minValue) / (maxValue - minValue)) * graphHeight
    ctx.fillStyle = '#3b82f6'
    ctx.beginPath()
    ctx.arc(pointX, rxY, 5, 0, 2 * Math.PI)
    ctx.fill()
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = 2
    ctx.stroke()
  }
  
  if (point.tx !== null) {
    const txY = padding.top + graphHeight - ((point.tx - minValue) / (maxValue - minValue)) * graphHeight
    ctx.fillStyle = '#8b5cf6'
    ctx.beginPath()
    ctx.arc(pointX, txY, 5, 0, 2 * Math.PI)
    ctx.fill()
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = 2
    ctx.stroke()
  }
  
  // Desenhar tooltip
  const timestamp = new Date(point.timestamp)
  const dateStr = timestamp.toLocaleString('pt-BR', { 
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit', 
    minute: '2-digit' 
  })
  
  const tooltipLines = [
    dateStr,
    point.rx !== null ? `RX: ${point.rx.toFixed(2)} dBm` : '',
    point.tx !== null ? `TX: ${point.tx.toFixed(2)} dBm` : ''
  ].filter(line => line !== '')
  
  // Calcular tamanho do tooltip
  ctx.font = '12px sans-serif'
  const tooltipPadding = 10
  const lineHeight = 18
  const maxWidth = Math.max(...tooltipLines.map(line => ctx.measureText(line).width))
  const tooltipWidth = maxWidth + tooltipPadding * 2
  const tooltipHeight = tooltipLines.length * lineHeight + tooltipPadding * 2
  
  // Posicionar tooltip
  let tooltipX = pointX + 15
  let tooltipY = mouseY - tooltipHeight / 2
  
  // Ajustar se sair da tela
  if (tooltipX + tooltipWidth > canvas.width - 20) {
    tooltipX = pointX - tooltipWidth - 15
  }
  if (tooltipY < padding.top) {
    tooltipY = padding.top
  }
  if (tooltipY + tooltipHeight > canvas.height - 20) {
    tooltipY = canvas.height - tooltipHeight - 20
  }
  
  // Desenhar fundo do tooltip
  ctx.fillStyle = 'rgba(17, 24, 39, 0.95)'
  ctx.strokeStyle = '#374151'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.roundRect(tooltipX, tooltipY, tooltipWidth, tooltipHeight, 6)
  ctx.fill()
  ctx.stroke()
  
  // Desenhar texto do tooltip
  ctx.fillStyle = '#f3f4f6'
  ctx.font = 'bold 12px sans-serif'
  ctx.textAlign = 'left'
  ctx.fillText(tooltipLines[0], tooltipX + tooltipPadding, tooltipY + tooltipPadding + 14)
  
  ctx.font = '11px sans-serif'
  tooltipLines.slice(1).forEach((line, index) => {
    const color = line.startsWith('RX:') ? '#3b82f6' : '#8b5cf6'
    ctx.fillStyle = color
    ctx.fillText(line, tooltipX + tooltipPadding, tooltipY + tooltipPadding + 14 + (index + 1) * lineHeight)
  })
}

const renderOpticalChart = async () => {
  if (!props.port?.id) {
    console.warn('[PortTrafficModal] Porta sem ID, não é possível buscar histórico')
    return
  }
  
  // Verificar se o canvas existe antes de continuar
  if (!opticalChartCanvas.value) {
    console.warn('[PortTrafficModal] Canvas óptico não disponível, aguardando...')
    await nextTick()
    if (!opticalChartCanvas.value) {
      console.error('[PortTrafficModal] Canvas óptico ainda não disponível após nextTick')
      return
    }
  }
  
  const url = `/api/v1/ports/${props.port.id}/optical_history/`
  const params = { hours: selectedPeriod.value }
  
  console.log('[PortTrafficModal] Buscando histórico óptico:', { url, params, portId: props.port.id, period: selectedPeriod.value })
  
  try {
    const response = await api.get(url, params)
    console.log('[PortTrafficModal] Resposta do servidor:', response)
    
    const history = Array.isArray(response) ? response : (response.history || [])
    console.log('[PortTrafficModal] Pontos de histórico:', history.length)

    let chartData
    if (history && history.length > 0) {
      chartData = history.map(snapshot => ({
        timestamp: new Date(snapshot.timestamp).getTime(),
        rx: snapshot.rx_power,
        tx: snapshot.tx_power,
      }))
      console.log('[PortTrafficModal] Dados reais mapeados:', chartData.length, 'pontos')
    } else {
      // Fallback para dados simulados (mesma estratégia do AlarmConfigModal)
      const now = Date.now()
      const points = []
      const rxBase = props.port?.optical_rx_power ?? -22
      const txBase = props.port?.optical_tx_power ?? -3
      const steps = selectedPeriod.value <= 24 ? selectedPeriod.value : 24
      for (let i = steps; i >= 0; i--) {
        const timestamp = now - (i * 60 * 60 * 1000)
        const rxVariation = (Math.random() - 0.5) * 2
        const txVariation = (Math.random() - 0.5) * 1
        points.push({ timestamp, rx: rxBase + rxVariation, tx: txBase + txVariation })
      }
      chartData = points
      console.warn('[PortTrafficModal] Optical history vazio; usando', chartData.length, 'pontos simulados')
    }
    await nextTick()
    renderOpticalCanvasChart(chartData)
    
    // Adicionar event listeners para tooltips
    if (opticalChartCanvas.value) {
      // Remover listeners antigos se existirem
      opticalChartCanvas.value.onmousemove = null
      opticalChartCanvas.value.onmouseleave = null
      
      // Adicionar novos listeners
      opticalChartCanvas.value.onmousemove = (e) => {
        const rect = opticalChartCanvas.value.getBoundingClientRect()
        const mouseX = e.clientX - rect.left
        const mouseY = e.clientY - rect.top
        drawOpticalTooltip(mouseX, mouseY)
      }
      
      opticalChartCanvas.value.onmouseleave = () => {
        if (opticalChartData) {
          renderOpticalCanvasChart(opticalChartData)
        }
      }
      
      // Adicionar cursor pointer
      opticalChartCanvas.value.style.cursor = 'crosshair'
    }
  } catch (err) {
    console.error('[PortTrafficModal] Erro ao carregar histórico óptico:', err)
    console.error('[PortTrafficModal] Detalhes do erro:', { message: err.message, url, params })
    await nextTick()
    renderOpticalCanvasChart([])
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

const exportData = () => {
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

const openAlarmConfig = () => {
  showAlarmConfig.value = true
}

const closeAlarmConfig = () => {
  showAlarmConfig.value = false
}

const handleAlarmSaved = () => {
  // Recarregar dados após salvar configuração de alarme
  showAlarmConfig.value = false
  // Recarregar gráfico óptico para mostrar novos thresholds
  if (opticalSectionOpen.value && opticalChartCanvas.value) {
    renderOpticalChart()
  }
  // Emitir evento para que o componente pai recarregue a porta
  emit('alarm-saved')
}

watch(() => props.isOpen, async (newValue) => {
  if (newValue) {
    loadTrafficData()
    // Carregar gráfico óptico se disponível
    if (props.port?.optical_rx_power !== null || props.port?.optical_tx_power !== null) {
      // Múltiplos nextTick para garantir que a transição CSS complete
      await nextTick()
      await nextTick()
      await nextTick()
      
      if (opticalSectionOpen.value && opticalChartCanvas.value) {
        console.log('[PortTrafficModal] Canvas pronto após nextTick, renderizando...')
        renderOpticalChart()
      } else {
        // Tentativa tardia com timeout maior para aguardar transição CSS
        console.log('[PortTrafficModal] Canvas não pronto, aguardando 300ms...')
        setTimeout(() => {
          if (opticalSectionOpen.value && opticalChartCanvas.value) {
            console.log('[PortTrafficModal] Canvas pronto após timeout, renderizando...')
            renderOpticalChart()
          } else {
            console.warn('[PortTrafficModal] Canvas ainda não disponível:', {
              opticalSectionOpen: opticalSectionOpen.value,
              canvasExists: !!opticalChartCanvas.value
            })
          }
        }, 300)
      }
    }
  } else {
    if (chartInstance) {
      chartInstance.destroy()
      chartInstance = null
    }
    if (opticalChartInstance) {
      opticalChartInstance.destroy()
      opticalChartInstance = null
    }
  }
})

// Watch para renderizar gráfico óptico quando seção abrir
watch(opticalSectionOpen, async (isOpen) => {
  if (isOpen && props.isOpen) {
    // Múltiplos nextTick para aguardar transição CSS
    await nextTick()
    await nextTick()
    await nextTick()
    if (opticalChartCanvas.value) {
      console.log('[PortTrafficModal] Seção óptica aberta, renderizando gráfico...')
      renderOpticalChart()
    } else {
      console.warn('[PortTrafficModal] Seção aberta mas canvas não disponível')
    }
  }
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
  }
  if (opticalChartInstance) {
    opticalChartInstance.destroy()
  }
})

// Renderizar assim que o canvas de óptico ficar disponível
watch(opticalChartCanvas, async (canvas) => {
  if (canvas && props.isOpen && opticalSectionOpen.value) {
    console.log('[PortTrafficModal] Canvas detectado, renderizando gráfico...')
    // Pequeno delay para garantir que o canvas está totalmente pronto
    await nextTick()
    await nextTick()
    await nextTick()
    setTimeout(() => {
      renderOpticalChart()
    }, 100)
  }
})

// Watch na porta para renderizar quando dados ópticos mudarem
watch(() => props.port, async (newPort) => {
  if (newPort && props.isOpen && opticalSectionOpen.value) {
    console.log('[PortTrafficModal] Porta mudou, verificando dados ópticos...')
    if (newPort.optical_rx_power !== null || newPort.optical_tx_power !== null) {
      await nextTick()
      await nextTick()
      await nextTick()
      if (opticalChartCanvas.value) {
        console.log('[PortTrafficModal] Renderizando após mudança de porta...')
        setTimeout(() => {
          renderOpticalChart()
        }, 150)
      }
    }
  }
}, { deep: true })
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
  max-width: 1400px;
  /* Fixed max-height so modal doesn't grow beyond viewport */
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-container {
  background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
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
  padding: 16px;
  /* Fixed height to prevent canvas from growing infinitely */
  min-height: 450px;
  max-height: 550px;
  height: 450px;
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
