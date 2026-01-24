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
  </Teleport>
</template>

<script setup>
import { ref, watch, onUnmounted, onMounted, nextTick } from 'vue'
import { useApi } from '@/composables/useApi'
import Chart from 'chart.js/auto'

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

const emit = defineEmits(['close'])

const api = useApi()
const loading = ref(false)
const error = ref(null)
const trafficData = ref(null)
const selectedPeriod = ref(24)
const chartCanvas = ref(null)
let chartInstance = null

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

const changePeriod = (hours) => {
  selectedPeriod.value = hours
  loadTrafficData()
}

const formatBandwidth = (bps) => {
  if (bps === null || bps === undefined) return 'N/A'
  
  const mbps = bps / 1000000
  if (mbps >= 1000) {
    return `${(mbps / 1000).toFixed(2)} Gbps`
  }
  return `${mbps.toFixed(2)} Mbps`
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

const close = () => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
  emit('close')
}

watch(() => props.isOpen, (newValue) => {
  if (newValue) {
    loadTrafficData()
  } else {
    if (chartInstance) {
      chartInstance.destroy()
      chartInstance = null
    }
  }
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
  }
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
  min-height: 380px;
  max-height: 500px;
  height: 380px;
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
</style>
