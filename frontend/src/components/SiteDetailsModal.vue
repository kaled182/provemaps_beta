<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="modal-overlay" @click.self="close">
        <div class="modal-container" :class="{ dark: isDark }">
          <!-- Header -->
          <div class="modal-header">
            <div class="header-content">
              <div class="site-icon">
                <i class="fas fa-map-marker-alt"></i>
              </div>
              <div class="site-info">
                <h2 class="site-name">{{ site?.name || 'Carregando...' }}</h2>
                <p class="site-location">{{ site?.location || 'N/A' }}</p>
              </div>
            </div>
            <button class="close-button" @click="close">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <!-- Site Summary -->
          <div class="site-summary">
            <div class="summary-card">
              <div class="summary-icon online">
                <i class="fas fa-check-circle"></i>
              </div>
              <div class="summary-content">
                <span class="summary-label">Online</span>
                <span class="summary-value">{{ deviceStats.online }}</span>
              </div>
            </div>
            <div class="summary-card">
              <div class="summary-icon warning">
                <i class="fas fa-exclamation-triangle"></i>
              </div>
              <div class="summary-content">
                <span class="summary-label">Atenção</span>
                <span class="summary-value">{{ deviceStats.warning }}</span>
              </div>
            </div>
            <div class="summary-card">
              <div class="summary-icon critical">
                <i class="fas fa-exclamation-circle"></i>
              </div>
              <div class="summary-content">
                <span class="summary-label">Crítico</span>
                <span class="summary-value">{{ deviceStats.critical }}</span>
              </div>
            </div>
            <div class="summary-card">
              <div class="summary-icon offline">
                <i class="fas fa-times-circle"></i>
              </div>
              <div class="summary-content">
                <span class="summary-label">Offline</span>
                <span class="summary-value">{{ deviceStats.offline }}</span>
              </div>
            </div>
            <div class="summary-card camera-card" @click="showCamerasTab = true" style="cursor: pointer;">
              <div class="summary-icon cameras">
                <i class="fas fa-video"></i>
              </div>
              <div class="summary-content">
                <span class="summary-label">Câmeras</span>
                <span class="summary-value">{{ cameraCount }}</span>
              </div>
            </div>
          </div>

          <!-- Devices List -->
          <div class="devices-section">
            <h3 class="section-title">
              <i class="fas fa-server"></i>
              Dispositivos ({{ devices.length }})
            </h3>

            <div v-if="loading" class="loading-state">
              <i class="fas fa-spinner fa-spin"></i>
              <span>Carregando dispositivos...</span>
            </div>

            <div v-else-if="devices.length === 0" class="empty-state">
              <i class="fas fa-inbox"></i>
              <span>Nenhum dispositivo encontrado neste site</span>
            </div>

            <div v-else class="devices-grid">
              <div
                v-for="device in devices"
                :key="device.id"
                class="device-card"
                :class="getStatusClass(device.status)"
                :title="getDeviceTooltip(device)"
                @click="openDeviceDetails(device)"
                style="cursor: pointer;"
              >
                <!-- Device Header -->
                <div class="device-header">
                  <div class="device-icon">
                    <i :class="getDeviceIcon(device.type)"></i>
                  </div>
                  <div class="device-title">
                    <h4>{{ device.name }}</h4>
                    <span class="device-type">{{ device.type || 'N/A' }}</span>
                  </div>
                  <div class="device-status">
                    <span class="status-badge" :class="device.status">
                      {{ getStatusLabel(device.status) }}
                    </span>
                  </div>
                  <button 
                    @click.stop="openEditDevice(device)" 
                    class="config-icon-button"
                    title="Configurar dispositivo"
                  >
                    <i class="fas fa-cog"></i>
                  </button>
                </div>

                <!-- Device Metrics -->
                <div class="device-metrics">
                  <div class="metric">
                    <div class="metric-header">
                      <i class="fas fa-microchip"></i>
                      <span>CPU</span>
                    </div>
                    <div class="metric-value">
                      <div class="progress-bar">
                        <div 
                          class="progress-fill" 
                          :class="getMetricClass(device.cpu)"
                          :style="{ width: device.cpu + '%' }"
                        ></div>
                      </div>
                      <span class="metric-text">{{ device.cpu || 0 }}%</span>
                    </div>
                  </div>

                  <div class="metric">
                    <div class="metric-header">
                      <i class="fas fa-memory"></i>
                      <span>Memória</span>
                    </div>
                    <div class="metric-value">
                      <div class="progress-bar">
                        <div 
                          class="progress-fill" 
                          :class="getMetricClass(device.memory)"
                          :style="{ width: device.memory + '%' }"
                        ></div>
                      </div>
                      <span class="metric-text">{{ device.memory || 0 }}%</span>
                    </div>
                  </div>

                  <div class="metric">
                    <div class="metric-header">
                      <i class="fas fa-clock"></i>
                      <span>Uptime</span>
                    </div>
                    <div class="metric-value uptime">
                      <span class="metric-text">{{ formatUptime(device.uptime) }}</span>
                    </div>
                  </div>

                  <div class="metric">
                    <div class="metric-header">
                      <i class="fas fa-network-wired"></i>
                      <span>IP</span>
                    </div>
                    <div class="metric-value ip">
                      <span class="metric-text">{{ device.ip || 'N/A' }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Device Edit Modal -->
        <Teleport to="body">
          <Transition name="modal">
            <div v-if="showEditModal" class="modal-overlay" @click.self="closeEditModal">
              <div class="edit-modal-container" :class="{ dark: isDark }">
                <!-- Header -->
                <div class="edit-modal-header">
                  <div class="header-content">
                    <i class="fas fa-cog"></i>
                    <h3>Editar Dispositivo</h3>
                  </div>
                  <button class="close-button" @click="closeEditModal">
                    <i class="fas fa-times"></i>
                  </button>
                </div>

                <!-- Content -->
                <div class="edit-modal-content">
                  <div class="form-section">
                    <h4 class="section-title">Informações Básicas</h4>
                    <div class="form-field">
                      <label>Nome do Host</label>
                      <input v-model="editForm.name" type="text" class="form-input" readonly />
                    </div>
                    <div class="form-field">
                      <label>IP de Gerência</label>
                      <div class="input-with-icon">
                        <i class="fas fa-globe"></i>
                        <input v-model="editForm.ip_address" type="text" class="form-input" readonly />
                      </div>
                    </div>
                    <div class="form-field">
                      <label>Zabbix HostID</label>
                      <input v-model="editForm.zabbix_hostid" type="text" class="form-input" readonly />
                    </div>
                  </div>

                  <div class="form-section">
                    <h4 class="section-title">Zabbix & Métricas</h4>
                    <div class="form-field">
                      <label>Uptime item key</label>
                      <input v-model="editForm.uptime_item_key" type="text" class="form-input" placeholder="ex: sysUpTime | system.uptime" />
                      <p class="field-help">Zabbix item key para uptime (e.g. system.uptime)</p>
                    </div>

                    <div class="form-field">
                      <label>Cpu usage item key</label>
                      <input v-model="editForm.cpu_usage_item_key" type="text" class="form-input" placeholder="ex: system.cpu.util[,user]" />
                      <p class="field-help">Zabbix item key para CPU usage (e.g. system.cpu.util[,user])</p>
                    </div>

                    <div class="form-field">
                      <label>Memory usage item key</label>
                      <input v-model="editForm.memory_usage_item_key" type="text" class="form-input" placeholder="ex: vm.memory.size[percent] | mem.util" />
                      <p class="field-help">Zabbix item key para Memory usage (e.g. vm.memory.size[percent] ou mem.util)</p>
                    </div>

                    <div class="form-row">
                      <div class="form-field">
                        <label>Cpu usage manual percent</label>
                        <input v-model.number="editForm.cpu_usage_manual_percent" type="number" step="0.1" min="0" max="100" class="form-input" placeholder="ex: 30" />
                        <p class="field-help">Valor manual quando Zabbix estiver indisponível</p>
                      </div>
                      <div class="form-field">
                        <label>Memory usage manual percent</label>
                        <input v-model.number="editForm.memory_usage_manual_percent" type="number" step="0.1" min="0" max="100" class="form-input" placeholder="ex: 55" />
                        <p class="field-help">Valor manual quando Zabbix estiver indisponível</p>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Footer -->
                <div class="edit-modal-footer">
                  <button @click="closeEditModal" class="btn-secondary">
                    <i class="fas fa-times"></i> Cancelar
                  </button>
                  <button @click="saveDevice" class="btn-primary" :disabled="saving">
                    <i class="fas fa-save" :class="{ 'fa-spin': saving }"></i>
                    {{ saving ? 'Salvando...' : 'Salvar Device' }}
                  </button>
                </div>
              </div>
            </div>
          </Transition>
        </Teleport>

        <!-- Device Details Modal -->
        <DeviceDetailsModal
          :is-open="showDeviceDetailsModal"
          :device="selectedDeviceForDetails"
          @close="closeDeviceDetails"
        />
      </div>
    </Transition>
  </Teleport>

  <!-- Camera Mosaic Modal -->
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showCameraModal" class="camera-modal-overlay" @click.self="closeCameraModal">
        <div class="camera-modal-container">
          <div class="camera-modal-header">
            <h3>
              <i class="fas fa-video"></i>
              Câmeras - {{ site?.name }}
            </h3>
            <button class="camera-close-btn" @click="closeCameraModal">
              <i class="fas fa-times"></i>
            </button>
          </div>
          <div class="camera-modal-body">
            <div v-if="loadingCameras" class="camera-loading">
              <i class="fas fa-spinner fa-spin"></i>
              <span>Carregando câmeras...</span>
            </div>
            <div v-else-if="cameras.length === 0" class="camera-empty">
              <i class="fas fa-video-slash"></i>
              <span>Nenhuma câmera encontrada para este site</span>
            </div>
            <div v-else class="camera-grid" :class="getCameraGridClass">
              <div v-for="camera in cameras" :key="camera.connectionKey ?? camera.id" class="camera-cell">
                <div class="camera-video-container">
                  <video 
                    :ref="el => { if (el) cameraVideoRefs[camera.connectionKey ?? camera.id] = el }"
                    class="camera-video"
                    autoplay
                    muted
                    playsinline
                  ></video>
                  <div class="camera-overlay">
                    <span class="camera-name">{{ camera.name }}</span>
                    <span v-if="cameraConnections[camera.connectionKey ?? camera.id]" class="camera-status connected">
                      <i class="fas fa-circle"></i> Ao vivo
                    </span>
                    <span v-else class="camera-status connecting">
                      <i class="fas fa-spinner fa-spin"></i> Conectando...
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- Cameras Tab Modal -->
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showCamerasTab && site" class="cameras-modal-overlay" @click.self="showCamerasTab = false">
        <div class="cameras-modal-container">
          <div class="cameras-modal-header">
            <h3>
              <i class="fas fa-video"></i>
              Câmeras - {{ site.name }}
            </h3>
            <button class="cameras-close-btn" @click="showCamerasTab = false">
              <i class="fas fa-times"></i>
            </button>
          </div>
          <div class="cameras-modal-body">
            <SiteCamerasTab :siteId="site.id" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, reactive, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'
import { useEscapeKey } from '@/composables/useEscapeKey'
import { useUiStore } from '@/stores/ui'
import { useWebSocket } from '@/composables/useWebSocket'
import DeviceDetailsModal from './DeviceDetailsModal.vue'
import SiteCamerasTab from '@/components/Site/SiteCamerasTab.vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  site: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close'])

const router = useRouter()
const { get, patch, post } = useApi()
const { success, error: notifyError } = useNotification()
const uiStore = useUiStore()

const devices = ref([])
const loading = ref(false)
const showEditModal = ref(false)
const showDeviceDetailsModal = ref(false)
const selectedDeviceForDetails = ref(null)
const saving = ref(false)
const showCamerasTab = ref(false)
const editForm = reactive({
  id: null,
  name: '',
  ip_address: '',
  zabbix_hostid: '',
  uptime_item_key: '',
  cpu_usage_item_key: '',
  memory_usage_item_key: '',
  cpu_usage_manual_percent: null,
  memory_usage_manual_percent: null,
})

const isDark = computed(() => uiStore.theme === 'dark')

const deviceStats = computed(() => {
  const stats = {
    online: 0,
    warning: 0,
    critical: 0,
    offline: 0
  }
  
  devices.value.forEach(device => {
    const status = device.status?.toLowerCase()
    if (status === 'online') stats.online++
    else if (status === 'warning' || status === 'atenção') stats.warning++
    else if (status === 'critical' || status === 'crítico') stats.critical++
    else stats.offline++
  })
  
  return stats
})

const loadDevices = async () => {
  if (!props.site) return
  
  loading.value = true
  try {
    console.log('[SiteDetailsModal] Carregando dispositivos para site:', props.site)
    
    // Usar o ID do site se disponível
    const siteId = props.site.id || props.site.site_id
    
    console.log('[SiteDetailsModal] ID do site:', siteId)
    console.log('[SiteDetailsModal] Nome do site:', props.site.name)
    
    if (!siteId) {
      console.warn('[SiteDetailsModal] Site sem ID, não é possível carregar dispositivos')
      devices.value = []
      return
    }
    
    // Buscar todos os devices e filtrar pelo site ID
    const response = await get('/api/v1/devices/')
    
    console.log('[SiteDetailsModal] Resposta da API devices:', {
      count: response.count,
      totalResults: response.results?.length
    })
    
    // Filtrar devices pelo site ID
    const devicesData = response.results?.filter(device => device.site === siteId) || []
    
    console.log('[SiteDetailsModal] Devices encontrados para este site:', devicesData.length)
    console.log('[SiteDetailsModal] Exemplo de device:', devicesData[0])
    
    devices.value = devicesData.map(device => ({
      id: device.id,
      name: device.name || 'Dispositivo sem nome',
      type: device.group_name || 'Dispositivo',
      status: 'offline', // será atualizado após buscar métricas
      cpu: 0,
      memory: 0,
      uptime: 0,
      ip: device.primary_ip || 'N/A',
      zabbixHostId: device.zabbix_hostid,
      cpuItemKey: device.cpu_usage_item_key,
      uptimeItemKey: device.uptime_item_key
    }))
    
    console.log('[SiteDetailsModal] Dispositivos mapeados:', devices.value)

    // Fetch metrics for each device in parallel
    try {
      const metricPromises = devices.value.map(async (dev) => {
        try {
          const m = await get(`/api/v1/devices/${dev.id}/metrics/`)
          dev.cpu = typeof m.cpu === 'number' ? Math.round(m.cpu) : (dev.cpu || 0)
          dev.memory = typeof m.memory === 'number' ? Math.round(m.memory) : (dev.memory || 0)
          dev.uptime_human = m.uptime_human || null
          // Map uptime in seconds for textual display
          if (typeof m.uptime_seconds === 'number' && m.uptime_seconds > 0) {
            dev.uptime = m.uptime_seconds
          }
          // Determinar status com base em uptime e thresholds
          const hasUptime = typeof m.uptime_seconds === 'number' && m.uptime_seconds > 0
          // Fallback: se não há uptime mas há métricas de CPU/Memória, considerar dispositivo ativo
          const hasMetrics = (
            typeof m.cpu === 'number' && m.cpu > 0
          ) || (
            typeof m.memory === 'number' && m.memory > 0
          )
          const cpuCritical = dev.cpu >= 90
          const cpuWarning = dev.cpu >= 70 && dev.cpu < 90
          const memCritical = dev.memory >= 90
          const memWarning = dev.memory >= 70 && dev.memory < 90
          
          if (!hasUptime && hasMetrics) {
            // Sem uptime, mas com métricas → status baseado em thresholds
            if (cpuCritical || memCritical) {
              dev.status = 'critical'
            } else if (cpuWarning || memWarning) {
              dev.status = 'warning'
            } else {
              dev.status = 'online'
            }
          } else if (!hasUptime) {
            dev.status = 'offline'
          } else if (cpuCritical || memCritical) {
            dev.status = 'critical'
          } else if (cpuWarning || memWarning) {
            dev.status = 'warning'
          } else {
            dev.status = 'online'
          }
          return dev
        } catch (err) {
          console.warn('[SiteDetailsModal] Metrics fetch failed for device', dev.id, err)
          dev.status = 'offline'
          return dev
        }
      })
      await Promise.allSettled(metricPromises)
    } catch (err) {
      console.warn('[SiteDetailsModal] Metrics batch failed:', err)
    }
  } catch (error) {
    console.error('[SiteDetailsModal] Erro ao carregar dispositivos:', error)
    console.error('[SiteDetailsModal] Detalhes do erro:', error.response || error)
    devices.value = []
  } finally {
    loading.value = false
  }
}

const close = () => {
  emit('close')
}

// Gerenciar ESC key - ignora quando algum modal filho está aberto
const hasChildModalOpen = computed(() => 
  showEditModal.value || showDeviceDetailsModal.value || showMosaicModal.value || showCameraModal.value
)
useEscapeKey(() => close(), { isOpen: computed(() => props.isOpen), shouldIgnore: hasChildModalOpen })

const getStatusClass = (status) => {
  return status?.toLowerCase() || 'offline'
}

const getStatusLabel = (status) => {
  const labels = {
    online: 'Online',
    warning: 'Atenção',
    critical: 'Crítico',
    offline: 'Offline'
  }
  return labels[status?.toLowerCase()] || 'Offline'
}

const getDeviceIcon = (type) => {
  const icons = {
    router: 'fas fa-network-wired',
    switch: 'fas fa-code-branch',
    server: 'fas fa-server',
    firewall: 'fas fa-shield-alt',
    default: 'fas fa-server'
  }
  return icons[type?.toLowerCase()] || icons.default
}

const getMetricClass = (value) => {
  if (value >= 90) return 'critical'
  if (value >= 70) return 'warning'
  return 'normal'
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

const getDeviceTooltip = (device) => {
  const parts = [
    `${device.name}`,
    `Status: ${getStatusLabel(device.status)}`,
    `IP: ${device.ip}`,
  ]
  
  if (device.uptime_human) {
    parts.push(`Uptime: ${device.uptime_human}`)
  }
  
  if (device.cpuItemKey) {
    parts.push(`CPU Key: ${device.cpuItemKey}`)
  }
  
  if (device.uptimeItemKey) {
    parts.push(`Uptime Key: ${device.uptimeItemKey}`)
  }
  
  if (device.zabbixHostId) {
    parts.push(`Zabbix Host ID: ${device.zabbixHostId}`)
  }
  
  return parts.join('\n')
}

const openEditDevice = async (device) => {
  try {
    // Fetch fresh device data
    const freshData = await get(`/api/v1/devices/${device.id}/`)
    
    editForm.id = freshData.id
    editForm.name = freshData.name
    editForm.ip_address = freshData.primary_ip || freshData.ip_address
    editForm.zabbix_hostid = freshData.zabbix_hostid || ''
    editForm.uptime_item_key = freshData.uptime_item_key || ''
    editForm.cpu_usage_item_key = freshData.cpu_usage_item_key || ''
    editForm.memory_usage_item_key = freshData.memory_usage_item_key || ''
    editForm.cpu_usage_manual_percent = freshData.cpu_usage_manual_percent ?? null
    editForm.memory_usage_manual_percent = freshData.memory_usage_manual_percent ?? null
    
    showEditModal.value = true
  } catch (error) {
    console.error('[SiteDetailsModal] Failed to load device data:', error)
    notifyError('Erro', 'Não foi possível carregar os dados do dispositivo')
  }
}

const closeEditModal = () => {
  showEditModal.value = false
}

// ESC para fechar modal de edição
useEscapeKey(() => closeEditModal(), { isOpen: showEditModal })

const openDeviceDetails = (device) => {
  console.log('[SiteDetailsModal] Abrindo detalhes do dispositivo:', device?.id, device?.name)
  selectedDeviceForDetails.value = device
  showDeviceDetailsModal.value = true
}

const closeDeviceDetails = () => {
  showDeviceDetailsModal.value = false
  selectedDeviceForDetails.value = null
}

const saveDevice = async () => {
  if (!editForm.id) return
  
  saving.value = true
  try {
    const payload = {
      uptime_item_key: editForm.uptime_item_key || null,
      cpu_usage_item_key: editForm.cpu_usage_item_key || null,
      memory_usage_item_key: editForm.memory_usage_item_key || null,
      cpu_usage_manual_percent: editForm.cpu_usage_manual_percent ?? null,
      memory_usage_manual_percent: editForm.memory_usage_manual_percent ?? null,
    }
    
    await patch(`/api/v1/devices/${editForm.id}/`, payload)
    success('Dispositivo atualizado', 'Campos de Zabbix e métricas salvos.')
    closeEditModal()
    
    // Reload devices to reflect changes
    await loadDevices()
  } catch (error) {
    console.error('[SiteDetailsModal] Failed to save device:', error)
    notifyError('Erro ao salvar', error?.message || 'Não foi possível atualizar o dispositivo')
  } finally {
    saving.value = false
  }
}

watch(() => props.isOpen, (newVal) => {
  if (newVal && props.site) {
    loadDevices()
  }
})

// WebSocket setup for real-time updates
const wsUrl = computed(() => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return `${protocol}//${host}/ws/dashboard/status/`
})

const { connected: wsConnected, lastMessage } = useWebSocket(wsUrl.value, {
  autoConnect: false,
  reconnectDelay: 5000,
  maxReconnectAttempts: 10
})

// Watch for WebSocket messages and update device metrics
watch(lastMessage, (message) => {
  if (!message || !props.isOpen) return
  
  try {
    // Handle dashboard.status messages
    if (message.type === 'dashboard.status' && message.data?.devices) {
      const wsDevices = message.data.devices
      
      devices.value.forEach(device => {
        const wsDevice = wsDevices.find(d => d.id === device.id)
        if (wsDevice) {
          // Update metrics from WebSocket
          if (typeof wsDevice.cpu === 'number') {
            device.cpu = Math.round(wsDevice.cpu)
          }
          if (typeof wsDevice.memory === 'number') {
            device.memory = Math.round(wsDevice.memory)
          }
          if (wsDevice.uptime_seconds) {
            device.uptime = wsDevice.uptime_seconds
            device.uptime_human = wsDevice.uptime_human
          }
          
          // Recalculate status based on new metrics
          const hasUptime = device.uptime > 0
          const cpuCritical = device.cpu >= 90
          const cpuWarning = device.cpu >= 70 && device.cpu < 90
          const memCritical = device.memory >= 90
          const memWarning = device.memory >= 70 && device.memory < 90
          
          if (!hasUptime) {
            device.status = 'offline'
          } else if (cpuCritical || memCritical) {
            device.status = 'critical'
          } else if (cpuWarning || memWarning) {
            device.status = 'warning'
          } else {
            device.status = 'online'
          }
        }
      })
    }
  } catch (error) {
    console.warn('[SiteDetailsModal] Error processing WebSocket message:', error)
  }
})

// Connect/disconnect WebSocket based on modal visibility
watch(() => props.isOpen, (isOpen) => {
  if (isOpen && wsUrl.value) {
    // Connect when modal opens
    const ws = useWebSocket(wsUrl.value, {
      reconnectDelay: 5000,
      maxReconnectAttempts: 10
    })
    // Store reference for cleanup if needed
  }
})

// CRÍTICO: Aguardar template renderizar antes de conectar câmeras do mosaico
// WATCHER REMOVIDO: CameraPlayer se gerencia sozinho, não precisa de conexão manual
// watch(() => [showMosaicModal.value, mosaicCameras.value.length], async ([isOpen, count]) => {
//   ...código antigo de WebRTC removido...
// })

// Cleanup on unmount
onUnmounted(() => {
  closeCameraModal()
  closeMosaicModal()
})
</script>

<style>
/* Site Details Modal Styles */
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
  z-index: 1040;
  backdrop-filter: blur(4px);
}

.modal-container {
  background: #ffffff;
  border-radius: 16px;
  max-width: 1200px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.modal-container.dark {
  background: #1e293b;
  color: #f1f5f9;
}

/* Header */
.modal-header {
  padding: 24px 32px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.modal-container.dark .modal-header {
  border-bottom-color: #334155;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.site-icon {
  width: 56px;
  height: 56px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  backdrop-filter: blur(10px);
}

.site-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.site-name {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  color: white;
}

.site-location {
  font-size: 14px;
  margin: 0;
  opacity: 0.9;
  color: white;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.action-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  backdrop-filter: blur(10px);
}

.action-button:hover {
  background: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.action-button i {
  font-size: 16px;
}

.camera-button {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.9) 0%, rgba(37, 99, 235, 0.9) 100%);
  border-color: rgba(59, 130, 246, 0.5);
}

.camera-button:hover {
  background: linear-gradient(135deg, rgba(59, 130, 246, 1) 0%, rgba(37, 99, 235, 1) 100%);
  border-color: rgba(59, 130, 246, 0.7);
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

/* Site Summary */
.site-summary {
  padding: 24px 32px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  background: #f8fafc;
}

.modal-container.dark .site-summary {
  background: #0f172a;
}

.summary-card {
  background: white;
  padding: 16px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.modal-container.dark .summary-card {
  background: #1e293b;
}

.summary-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.summary-icon.online {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.summary-icon.warning {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.summary-icon.critical {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.summary-icon.offline {
  background: rgba(107, 114, 128, 0.1);
  color: #6b7280;
}

.summary-icon.cameras {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.camera-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.camera-card:hover .summary-icon.cameras {
  background: rgba(59, 130, 246, 0.2);
  transform: scale(1.1);
}

.summary-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-label {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.summary-value {
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
}

.modal-container.dark .summary-value {
  color: #f1f5f9;
}

/* Devices Section */
.devices-section {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 20px 0;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #1e293b;
}

.modal-container.dark .section-title {
  color: #f1f5f9;
}

.section-title i {
  color: #667eea;
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

/* Devices Grid */
.devices-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 16px;
}

.device-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  border-left: 4px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.3s;
}

.modal-container.dark .device-card {
  background: #0f172a;
  border-left-color: #334155;
}

.device-card:hover {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.device-card.online {
  border-left: 4px solid #10b981; /* verde para ONLINE */
}

.device-card.warning {
  border-left: 4px solid #f59e0b; /* amarelo para WARNING */
}

/* Garantir cor correta também no tema escuro */
.modal-container.dark .device-card.warning {
  border-left: 4px solid #f59e0b;
}

.device-card.critical {
  border-left: 4px solid #ef4444; /* vermelho para CRITICAL */
}

/* Garantir cor correta também no tema escuro */
.modal-container.dark .device-card.critical {
  border-left: 4px solid #ef4444;
}

.device-card.offline {
  border-left-color: #ef4444; /* vermelho para OFF */
}

/* Garantir cor correta também no tema escuro */
.modal-container.dark .device-card.online {
  border-left: 4px solid #10b981;
}

/* Device Header */
.device-header {

/* Garantir cor correta também no tema escuro */
.modal-container.dark .device-card.offline {
  border-left: 4px solid #ef4444;
}
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.device-icon {
  width: 40px;
  height: 40px;
  background: #f1f5f9;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #667eea;
  font-size: 18px;
}

.modal-container.dark .device-icon {
  background: #1e293b;
}

.device-title {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.device-title h4 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: #1e293b;
}

.modal-container.dark .device-title h4 {
  color: #f1f5f9;
}

.device-type {
  font-size: 12px;
  color: #64748b;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-badge.online {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.status-badge.warning {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.status-badge.critical {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.status-badge.offline {
  background: rgba(239, 68, 68, 0.1); /* vermelho claro */
  color: #ef4444; /* vermelho */
}

/* Config Icon Button */
.config-icon-button {
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #94a3b8;
  transition: all 0.2s;
  margin-left: 8px;
}

.config-icon-button:hover {
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
  transform: rotate(45deg);
}

.config-icon-button i {
  font-size: 16px;
}

/* Edit Modal */
.edit-modal-container {
  background: white;
  border-radius: 16px;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.edit-modal-container.dark {
  background: #1e293b;
}

.edit-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid #e2e8f0;
}

.edit-modal-container.dark .edit-modal-header {
  border-bottom-color: #334155;
}

.edit-modal-header .header-content {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #1e293b;
}

.edit-modal-container.dark .edit-modal-header .header-content {
  color: #f1f5f9;
}

.edit-modal-header .header-content i {
  font-size: 20px;
  color: #667eea;
}

.edit-modal-header h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.edit-modal-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.form-section {
  margin-bottom: 24px;
}

.form-section:last-child {
  margin-bottom: 0;
}

.form-section .section-title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #64748b;
  margin-bottom: 16px;
}

.form-field {
  margin-bottom: 16px;
}

.form-field:last-child {
  margin-bottom: 0;
}

.form-field label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
  margin-bottom: 8px;
}

.edit-modal-container.dark .form-field label {
  color: #f1f5f9;
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  color: #1e293b;
  background: white;
  transition: all 0.2s;
}

.edit-modal-container.dark .form-input {
  background: #0f172a;
  border-color: #334155;
  color: #f1f5f9;
}

.form-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-input:read-only {
  background: #f8fafc;
  cursor: not-allowed;
}

.edit-modal-container.dark .form-input:read-only {
  background: #0f172a;
  opacity: 0.6;
}

.input-with-icon {
  position: relative;
}

.input-with-icon i {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
}

.input-with-icon .form-input {
  padding-left: 40px;
}

.field-help {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
  margin-bottom: 0;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.edit-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid #e2e8f0;
}

.edit-modal-container.dark .edit-modal-footer {
  border-top-color: #334155;
}

.btn-secondary,
.btn-primary {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-secondary {
  background: #f1f5f9;
  color: #475569;
}

.edit-modal-container.dark .btn-secondary {
  background: #334155;
  color: #cbd5e1;
}

.btn-secondary:hover {
  background: #e2e8f0;
}

.edit-modal-container.dark .btn-secondary:hover {
  background: #475569;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}
/* Device Metrics */
.device-metrics {
  display: grid;
  gap: 12px;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.metric-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-header i {
  width: 16px;
  text-align: center;
}

.metric-value {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.modal-container.dark .progress-bar {
  background: #334155;
}

.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.progress-fill.normal {
  background: linear-gradient(90deg, #10b981, #059669);
}

.progress-fill.warning {
  background: linear-gradient(90deg, #f59e0b, #d97706);
}

.progress-fill.critical {
  background: linear-gradient(90deg, #ef4444, #dc2626);
}

.metric-text {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  min-width: 45px;
  text-align: right;
}

.modal-container.dark .metric-text {
  color: #f1f5f9;
}

.metric-value.uptime .metric-text,
.metric-value.ip .metric-text {
  min-width: auto;
  flex: 1;
  font-family: 'Monaco', 'Courier New', monospace;
}

/* Animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.3s, opacity 0.3s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.9);
  opacity: 0;
}

/* Scrollbar */
.devices-section::-webkit-scrollbar {
  width: 8px;
}

.devices-section::-webkit-scrollbar-track {
  background: #f1f5f9;
}

.modal-container.dark .devices-section::-webkit-scrollbar-track {
  background: #0f172a;
}

.devices-section::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

.modal-container.dark .devices-section::-webkit-scrollbar-thumb {
  background: #475569;
}

.devices-section::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* Responsive */
@media (max-width: 768px) {
  .modal-container {
    max-width: 100%;
    max-height: 100vh;
    border-radius: 0;
  }
  
  .devices-grid {
    grid-template-columns: 1fr;
  }
  
  .site-summary {
    grid-template-columns: repeat(2, 1fr);
  }
}
/* Camera Modal Styles */
.camera-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1060;
  padding: 20px;
}

.camera-modal-container {
  background: #1e293b;
  border-radius: 16px;
  width: 100%;
  max-width: 1600px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8);
}

.camera-modal-header {
  padding: 20px 24px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.camera-modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: white;
  display: flex;
  align-items: center;
  gap: 12px;
}

.camera-close-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.camera-close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}

.camera-modal-body {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.camera-loading,
.camera-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 60px 20px;
  color: #94a3b8;
}

.camera-loading i,
.camera-empty i {
  font-size: 48px;
  color: #3b82f6;
}

.camera-grid {
  display: grid;
  gap: 16px;
  height: 100%;
}

.camera-grid.grid-cols-1 {
  grid-template-columns: 1fr;
}

.camera-grid.grid-cols-2 {
  grid-template-columns: repeat(2, 1fr);
}

.camera-grid.grid-cols-3 {
  grid-template-columns: repeat(3, 1fr);
}

.camera-grid.grid-cols-4 {
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: repeat(2, 1fr);
}

@media (min-width: 1400px) {
  .camera-grid.grid-cols-4 {
    grid-template-columns: repeat(4, 1fr);
    grid-template-rows: 1fr;
  }
}

.camera-cell {
  background: #0f172a;
  border-radius: 12px;
  overflow: hidden;
  border: 2px solid #334155;
  transition: all 0.3s;
  min-height: 280px;
}

.camera-cell:hover {
  border-color: #3b82f6;
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.3);
}

.camera-video-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 280px;
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  background: #000;
}

.camera-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.8) 0%, transparent 100%);
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.camera-name {
  font-size: 14px;
  font-weight: 600;
  color: white;
}

.camera-status {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.camera-status.connected {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.camera-status.connecting {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.3);
}

.camera-status i {
  font-size: 8px;
}

/* Mosaic Modal Styles */
.mosaic-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
  padding: 20px;
}

.mosaic-modal-container {
  background: #1e293b;
  border-radius: 16px;
  width: 95vw;
  height: 95vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.9);
}

.mosaic-modal-header {
  padding: 20px 24px;
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.mosaic-modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: white;
  display: flex;
  align-items: center;
  gap: 12px;
}

.mosaic-close-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.mosaic-close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}

.mosaic-modal-body {
  flex: 1;
  padding: 24px;
  overflow: hidden;
  background: #0f172a;
  display: flex;
  flex-direction: column;
}

.mosaic-loading,
.mosaic-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 80px 20px;
  color: #94a3b8;
}

.mosaic-loading i,
.mosaic-empty i {
  font-size: 56px;
  color: #8b5cf6;
}

.mosaic-grid {
  display: grid;
  gap: 16px;
  height: 100%;
  width: 100%;
  flex: 1;
}

.mosaic-grid.grid-cols-1 {
  grid-template-columns: 1fr;
}

.mosaic-grid.grid-cols-2 {
  grid-template-columns: repeat(2, 1fr);
}

.mosaic-grid.grid-cols-3 {
  grid-template-columns: repeat(3, 1fr);
}

.mosaic-grid.grid-cols-4 {
  grid-template-columns: repeat(4, 1fr);
}

.mosaic-cell {
  background: #000;
  border-radius: 12px;
  overflow: hidden;
  border: 3px solid #334155;
  transition: all 0.3s;
  position: relative;
  display: flex;
  flex-direction: column;
}

.mosaic-cell:hover {
  border-color: #8b5cf6;
  box-shadow: 0 12px 32px rgba(139, 92, 246, 0.4);
  transform: translateY(-2px);
}

.mosaic-video-container {
  position: relative;
  width: 100%;
  height: 100%;
  flex: 1;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mosaic-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  background: #000;
}

.mosaic-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.9) 0%, transparent 100%);
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mosaic-camera-name {
  font-size: 16px;
  font-weight: 700;
  color: white;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
}

.mosaic-status {
  font-size: 13px;
  padding: 6px 12px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.mosaic-status.connected {
  background: rgba(16, 185, 129, 0.3);
  color: #10b981;
  border: 2px solid rgba(16, 185, 129, 0.5);
}

.mosaic-status.connecting {
  background: rgba(251, 191, 36, 0.3);
  color: #fbbf24;
  border: 2px solid rgba(251, 191, 36, 0.5);
}

.mosaic-status i {
  font-size: 10px;
}

/* Cameras Tab Modal Styles */
.cameras-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10100;
  padding: 20px;
}

.cameras-modal-container {
  background: #1e293b;
  border-radius: 16px;
  width: 95vw;
  height: 95vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.9);
}

.cameras-modal-header {
  padding: 20px 24px;
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.cameras-modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: white;
  display: flex;
  align-items: center;
  gap: 12px;
}

.cameras-close-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.cameras-close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}

.cameras-modal-body {
  flex: 1;
  overflow: hidden;
  padding: 0;
}

</style>
