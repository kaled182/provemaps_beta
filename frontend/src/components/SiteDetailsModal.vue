<template>
  <BaseModal
    :show="isOpen"
    :title="site?.name || 'Carregando…'"
    :subtitle="site?.location || ''"
    :icon="PhMapPin"
    :status="headerStatus"
    size="detail"
    @close="requestClose"
  >
    <!-- EV-0112: nível 2 — o equipamento inspecionado dentro do modal, sem sair do mapa -->
    <SiteDeviceInspector
      v-if="inspectedDevice"
      :device="inspectedDevice"
      :site-name="site?.name || ''"
      @back="inspectedId = null"
      @open-full="openFullScreen"
    />

    <template v-else>
    <!-- KPIs do site numa linha -->
    <div class="grid grid-cols-3 gap-2 sm:grid-cols-5" data-testid="site-kpis">
      <div v-for="k in kpis" :key="k.key" class="rounded-md border border-neutral-200 px-3 py-2">
        <div class="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-neutral-500">
          <span class="h-1.5 w-1.5 rounded-full" :class="k.dot" aria-hidden="true" />
          {{ k.label }}
        </div>
        <div class="font-mono text-xl font-semibold tabular-nums text-neutral-900" :data-testid="`site-kpi-${k.key}`">
          {{ k.value }}
        </div>
      </div>
      <button
        type="button"
        class="rounded-md border border-neutral-200 px-3 py-2 text-left hover:border-primary-500"
        title="Abrir mosaico de câmeras do site"
        data-testid="site-kpi-cameras"
        @click="openSiteMosaicModal"
      >
        <div class="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-neutral-500">
          <PhVideoCamera :size="12" aria-hidden="true" /> Câmeras
        </div>
        <div class="font-mono text-xl font-semibold tabular-nums text-neutral-900">{{ cameraCount }}</div>
      </button>
    </div>

    <div class="mt-4 mb-2 flex items-center gap-2 text-sm font-semibold text-neutral-700">
      Equipamentos
      <span class="font-mono tabular-nums text-neutral-500">{{ devices.length }}</span>
      <span v-if="deviceStats.unknown" class="text-xs font-normal text-neutral-500" data-testid="site-unknown-count">
        · {{ deviceStats.unknown }} sem estado
      </span>
      <span v-if="zabbixError" class="text-xs font-normal text-warning" data-testid="site-zabbix-error">
        · Zabbix indisponível — estado e métricas podem estar em falta
      </span>
    </div>

    <div v-if="loading" class="py-8 text-center text-sm text-neutral-500">A carregar equipamentos…</div>
    <div v-else-if="devices.length === 0" class="py-8 text-center text-sm text-neutral-500">
      Nenhum equipamento neste site
    </div>
    <div v-else class="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3" data-testid="site-devices-grid">
      <SiteDeviceCard
        v-for="device in devices"
        :key="device.id"
        :device="device"
        @open="inspectDevice"
        @edit="openEditDevice"
      />
    </div>
    </template>
  </BaseModal>

  <!-- Edição do equipamento -->
  <BaseModal
    :show="showEditModal"
    title="Editar dispositivo"
    :subtitle="editForm.name"
    :icon="PhGear"
    :dirty="editDirty"
    :z-index="3100"
    size="md"
    @close="closeEditModal"
  >
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
    <template #footer>
      <div class="edit-modal-footer">
        <button @click="closeEditModal" class="btn-secondary">
          <i class="fas fa-times"></i> Cancelar
        </button>
        <button @click="saveDevice" class="btn-primary" :disabled="saving">
          <i class="fas fa-save" :class="{ 'fa-spin': saving }"></i>
          {{ saving ? 'Salvando...' : 'Salvar Device' }}
        </button>
      </div>
    </template>
  </BaseModal>

  <!-- Device Details Modal -->
  <DeviceDetailsModal
    :is-open="showDeviceDetailsModal"
    :device="selectedDeviceForDetails"
    @close="closeDeviceDetails"
  />

  <!-- Câmeras do site -->
  <BaseModal
    :show="showCameraModal"
    :title="`Câmeras · ${site?.name || ''}`"
    :icon="PhVideoCamera"
    :z-index="3200"
    size="full"
    flush
    @close="closeCameraModal"
  >
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
  </BaseModal>

  <!-- Mosaico do site -->
  <BaseModal
    :show="showMosaicModal"
    :title="`${currentMosaic?.name || 'Mosaico'} · ${site?.name || ''}`"
    :icon="PhSquaresFour"
    :z-index="3300"
    size="full"
    flush
    @close="closeMosaicModal"
  >
      <div class="mosaic-modal-body">
        <div v-if="loadingMosaic" class="mosaic-loading">
          <i class="fas fa-spinner fa-spin"></i>
          <span>Carregando mosaico...</span>
        </div>
        <div v-else-if="mosaicCameras.length === 0" class="mosaic-empty">
          <i class="fas fa-video-slash"></i>
          <span>Nenhuma câmera no mosaico</span>
        </div>
        <div v-else class="mosaic-grid" :class="getMosaicGridClass">
          <div v-for="(camera, idx) in mosaicCameras" :key="camera.id || idx" class="mosaic-cell">
            <div class="mosaic-video-container">
              <CameraPlayer 
                :camera="camera"
                :autoplay="true"
                :muted="true"
              />
              <div class="mosaic-overlay">
                <span class="mosaic-camera-name">{{ camera.name }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch, reactive, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'
import { useWebSocket } from '@/composables/useWebSocket'
import { normalizeRealtimeMessage } from '@/composables/useRealtimeStatus'
import { useWebRTC } from '@/composables/useWebRTC'
import DeviceDetailsModal from './DeviceDetailsModal.vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import SiteDeviceCard from '@/components/SiteDetails/SiteDeviceCard.vue'
import SiteDeviceInspector from '@/components/SiteDetails/SiteDeviceInspector.vue'
import { PhMapPin, PhVideoCamera, PhGear, PhSquaresFour } from '@phosphor-icons/vue'
import { buildSiteDevice, applyRealtimeHost, countDeviceStatuses, siteHeaderStatus } from '@/utils/siteDevices'
import CameraPlayer from '@/components/Video/CameraPlayer.vue'

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

const devices = ref([])
const loading = ref(false)
const showEditModal = ref(false)
const showDeviceDetailsModal = ref(false)
const selectedDeviceForDetails = ref(null)
const saving = ref(false)
const showCameraModal = ref(false)
const cameras = ref([])
const loadingCameras = ref(false)
const cameraVideoRefs = ref({})
const cameraConnections = ref({})
const cameraCount = ref(0)
const showMosaicModal = ref(false)
const currentMosaic = ref(null)
const mosaicCameras = ref([])
const loadingMosaic = ref(false)
const mosaicVideoRefs = ref({})
const mosaicConnections = ref({})
const hasConnectedMosaic = ref(false)
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

const resolveConnectionKey = (cameraLike, fallback) => {
  const candidates = [
    cameraLike?.connectionKey,
    cameraLike?.connection_key,
    cameraLike?.restream_key,
    cameraLike?.stream_key,
    cameraLike?.id,
    cameraLike?.camera_id,
    cameraLike?.pk,
    fallback
  ]
  for (const candidate of candidates) {
    if (candidate !== undefined && candidate !== null && candidate !== '') {
      return String(candidate)
    }
  }
  return null
}

const assignConnectionKey = (cameraLike, fallback) => {
  const key = resolveConnectionKey(cameraLike, fallback)
  if (key) {
    cameraLike.connectionKey = key
  }
  return cameraLike
}

const deriveWhepUrl = (playbackUrl) => {
  if (!playbackUrl) return null
  try {
    const parsed = new URL(playbackUrl, window.location.origin)
    const sanitizedPath = parsed.pathname.replace(/\/+$/, '')
    const segments = sanitizedPath.split('/').filter(Boolean)
    if (!segments.length) return null

    const cleanup = (value) => value?.replace(/\.m3u8$/i, '')
    let possibleKey = cleanup(segments[segments.length - 1])
    if (!possibleKey || ['index', 'playlist', 'master', 'stream'].includes(possibleKey.toLowerCase())) {
      possibleKey = cleanup(segments[segments.length - 2])
    }

    if (!possibleKey) return null
    return `${parsed.origin}/whep/${possibleKey}`
  } catch (err) {
    console.warn('[SiteDetailsModal] Falha ao derivar WHEP a partir de playback_url:', playbackUrl, err)
    return null
  }
}

const reorderWhepPath = (candidate) => {
  if (!candidate) return null
  try {
    const parsed = new URL(candidate, window.location.origin)
    const segments = parsed.pathname.split('/').filter(Boolean)
    const whepIndex = segments.indexOf('whep')
    if (whepIndex === -1) return null
    if (segments.length < 2) return null

    if (whepIndex === segments.length - 1) {
      // .../key/whep => .../whep/key
      const keySegment = segments[whepIndex - 1]
      const prefix = segments.slice(0, Math.max(0, whepIndex - 1))
      if (!keySegment) return null
      parsed.pathname = `/${[...prefix, 'whep', keySegment].join('/')}`
      return parsed.toString()
    }

    const keySegment = segments[whepIndex + 1]
    if (!keySegment) return null
    const prefix = segments.slice(0, whepIndex)
    const suffix = segments.slice(whepIndex + 2)
    parsed.pathname = `/${[...prefix, keySegment, 'whep', ...suffix].join('/')}`
    return parsed.toString()
  } catch (err) {
    console.warn('[SiteDetailsModal] Falha ao reordenar caminho WHEP:', candidate, err)
    return null
  }
}

const buildWhepCandidates = (camera) => {
  const candidates = []
  const origins = new Set()

  const pushCandidate = (value) => {
    if (!value) return
    try {
      const normalized = new URL(value, window.location.origin).toString()
      if (!candidates.includes(normalized)) {
        candidates.push(normalized)
        origins.add(new URL(normalized).origin)
      }
    } catch (err) {
      console.warn('[SiteDetailsModal] Ignorando WHEP inválido:', value, err)
    }
  }

  const recordOrigin = (value) => {
    if (!value) return
    try {
      origins.add(new URL(value, window.location.origin).origin)
    } catch (err) {
      console.warn('[SiteDetailsModal] Falha ao registrar origem WHEP:', value, err)
    }
  }

  pushCandidate(camera?.whep_url)
  const derived = deriveWhepUrl(camera?.playback_url)
  if (!camera?.whep_url && derived) {
    camera.whep_url = derived
  }
  pushCandidate(derived)

  recordOrigin(camera?.playback_url)
  recordOrigin(camera?.whep_url)
  recordOrigin(camera?.webrtc_public_base_url)
  recordOrigin(camera?.webrtc_base_url)

  const snapshot = [...candidates]
  snapshot.forEach((value) => {
    const reordered = reorderWhepPath(value)
    if (reordered) pushCandidate(reordered)
  })

  const originList = origins.size ? Array.from(origins) : []
  if (!originList.length && camera?.playback_url) {
    try {
      originList.push(new URL(camera.playback_url, window.location.origin).origin)
    } catch (err) {
      console.warn('[SiteDetailsModal] Falha ao obter origem do playback_url:', camera?.playback_url, err)
    }
  }
  if (!originList.length && camera?.whep_url) {
    try {
      originList.push(new URL(camera.whep_url, window.location.origin).origin)
    } catch (err) {
      console.warn('[SiteDetailsModal] Falha ao obter origem do whep_url:', camera?.whep_url, err)
    }
  }

  const keySet = new Set()
  const potentialKeys = [
    camera?.restream_key,
    camera?.stream_key,
    camera?.connection_key,
    camera?.connectionKey,
    camera?.id,
    camera?.camera_id,
    camera?.pk,
  ]
  potentialKeys.forEach((value) => {
    if (value !== undefined && value !== null && value !== '') {
      keySet.add(String(value).replace(/^\/+|\/+$/g, ''))
    }
  })

  const numericId = Number(camera?.id)
  if (!Number.isNaN(numericId)) {
    keySet.add(String(numericId))
    keySet.add(`gateway_${numericId}`)
  }

  const connectionKey = camera?.connectionKey
  if (connectionKey) {
    keySet.add(String(connectionKey))
    if (!String(connectionKey).startsWith('gateway_')) {
      keySet.add(`gateway_${connectionKey}`)
    }
  }

  // Adicionar fallback para proxy /camera-stream (ex.: nginx 8082) quando detectamos porta 8889
  const orderedOrigins = []
  const seenOrigins = new Set()

  const pushOrigin = (value, priority = false) => {
    if (!value) return
    if (seenOrigins.has(value)) return
    seenOrigins.add(value)
    if (priority) {
      orderedOrigins.unshift(value)
    } else {
      orderedOrigins.push(value)
    }
  }

  originList.forEach((origin) => {
    pushOrigin(origin)
    try {
      const parsed = new URL(origin)
      if (parsed.port === '8889') {
        const proxyOrigin = `${parsed.protocol}//${parsed.hostname}:8082`
        pushOrigin(proxyOrigin, true)
        pushOrigin(`${proxyOrigin}/camera-stream`, true)
      }
    } catch (err) {
      console.warn('[SiteDetailsModal] Falha ao analisar origem para fallback proxy:', origin, err)
    }
  })

  if (!orderedOrigins.length) {
    pushOrigin(window.location.origin)
  }

  orderedOrigins.forEach((origin) => {
    keySet.forEach((keyCandidate) => {
      const sanitized = keyCandidate.replace(/^\/+|\/+$/g, '')
      if (!sanitized) return
      try {
        const normalizedOrigin = new URL(origin, window.location.origin).toString().replace(/\/+$/, '')
        pushCandidate(`${normalizedOrigin}/whep/${sanitized}`)
        pushCandidate(`${normalizedOrigin}/${sanitized}/whep`)
        if (!normalizedOrigin.includes('/camera-stream/')) {
          pushCandidate(`${normalizedOrigin}/camera-stream/${sanitized}/whep`)
        }
      } catch (err) {
        pushCandidate(`${origin}/whep/${sanitized}`)
        pushCandidate(`${origin}/${sanitized}/whep`)
      }
    })
  })

  return candidates
}

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const previewWarmups = new Map()
const previewRecentSuccess = new Map()
const PREVIEW_CACHE_MS = 45_000

const ensurePreviewReady = async (camera, label) => {
  const cameraId = Number(camera?.id)
  if (!cameraId || Number.isNaN(cameraId)) return

  const now = Date.now()
  const lastSuccess = previewRecentSuccess.get(cameraId)
  if (lastSuccess && now - lastSuccess < PREVIEW_CACHE_MS) {
    return
  }

  if (previewWarmups.has(cameraId)) {
    return previewWarmups.get(cameraId)
  }

  const warmup = (async () => {
    try {
      console.log(`[SiteDetailsModal] Iniciando preview backend (${label}) para câmera ${cameraId}`)
      const response = await post(`/setup_app/api/gateways/${cameraId}/video/preview/start/`)
      if (response?.success) {
        if (response.playback_url) {
          camera.playback_url = response.playback_url
        }
        if (response.preview_url) {
          camera.preview_url = response.preview_url
        }
        previewRecentSuccess.set(cameraId, Date.now())
        console.log(`[SiteDetailsModal] ✓ Preview backend iniciado para ${label}, aguardando 2s para MediaMTX publicar...`)
        await delay(2000)
      } else {
        console.warn(`[SiteDetailsModal] Preview backend respondeu sem sucesso (${label})`, response)
      }
    } catch (error) {
      console.error(`[SiteDetailsModal] Erro ao iniciar preview backend (${label})`, error)
    } finally {
      previewWarmups.delete(cameraId)
    }
  })()

  previewWarmups.set(cameraId, warmup)
  return warmup
}

const attemptWhepConnectionViaComposable = async (camera, refsMap, connectionsMap, label) => {
  const connectionKey = camera.connectionKey ?? resolveConnectionKey(camera)
  if (!connectionKey) {
    console.warn('[SiteDetailsModal] Não foi possível determinar a chave da câmera', camera)
    return false
  }

  const playbackUrl = camera.playback_url || camera.preview_url
  if (!playbackUrl) {
    console.warn(`[SiteDetailsModal] Sem playback_url para ${label}`)
    return false
  }

  const whepUrl = playbackUrl.endsWith('/') ? `${playbackUrl}whep` : `${playbackUrl}/whep`
  
  console.log(`[SiteDetailsModal] Conectando ${label} via useWebRTC composable:`, whepUrl)

  if (!connectionsMap.value) {
    connectionsMap.value = {}
  }

  const existing = connectionsMap.value?.[connectionKey]
  if (existing?.close) {
    try {
      existing.close()
    } catch (err) {
      console.warn('[SiteDetailsModal] Falha ao encerrar conexão prévia:', err)
    }
  }

  try {
    const rtc = useWebRTC({
      maxRetries: 5,
      maxBackoff: 30000
    })

    await rtc.connect(whepUrl)
    connectionsMap.value[connectionKey] = rtc

    // Aguardar próximo tick para garantir que o elemento video existe
    await nextTick()
    
    console.log(`[SiteDetailsModal] Tentando vincular stream para ${label}, connectionKey:`, connectionKey)
    console.log(`[SiteDetailsModal] refsMap.value disponível:`, Object.keys(refsMap.value))
    
    // Polling para encontrar o elemento video (pode levar alguns frames)
    const maxAttempts = 10
    for (let i = 0; i < maxAttempts; i++) {
      const videoEl = refsMap.value[connectionKey]
      console.log(`[SiteDetailsModal] Tentativa ${i + 1}/${maxAttempts} - videoEl:`, !!videoEl, 'stream:', !!rtc.stream.value)
      if (videoEl && rtc.stream.value) {
        videoEl.srcObject = rtc.stream.value
        console.log(`[SiteDetailsModal] ✓ Stream vinculado ao vídeo para ${label}`)
        break
      }
      await delay(100)
    }

    // Watch para streams que chegam depois
    const stopWatch = watch(rtc.stream, (newStream) => {
      console.log(`[SiteDetailsModal] 🔄 Watch disparado para ${label}:`, {
        hasStream: !!newStream,
        hasVideoEl: !!refsMap.value[connectionKey],
        connectionKey,
        streamTracks: newStream?.getTracks().length
      })
      
      if (newStream && refsMap.value[connectionKey]) {
        const videoEl = refsMap.value[connectionKey]
        if (videoEl.srcObject !== newStream) {
          videoEl.srcObject = newStream
          console.log(`[SiteDetailsModal] ✓ Stream atualizado para ${label}`)
        } else {
          console.log(`[SiteDetailsModal] ℹ️ Stream já vinculado para ${label}`)
        }
      } else if (newStream && !refsMap.value[connectionKey]) {
        console.error(`[SiteDetailsModal] ❌ Stream disponível mas videoEl não encontrado para ${label}, key:`, connectionKey)
        console.error(`[SiteDetailsModal] Keys disponíveis:`, Object.keys(refsMap.value))
      } else if (!newStream) {
        console.warn(`[SiteDetailsModal] ⚠️ Watch disparado mas stream vazio para ${label}`)
      }
    }, { immediate: true })

    const originalClose = rtc.close.bind(rtc)
    rtc.close = () => {
      stopWatch()
      originalClose()
    }

    console.log(`[SiteDetailsModal] ✓ Câmera conectada (${label}) via ${whepUrl}`)
    return true
  } catch (error) {
    console.error('[SiteDetailsModal] Erro ao conectar via useWebRTC:', label, whepUrl, error)
    return false
  }
}

const attemptWhepConnection = async (camera, whepUrl, refsMap, connectionsMap, label) => {
  const connectionKey = camera.connectionKey ?? resolveConnectionKey(camera)
  if (!connectionKey) {
    console.warn('[SiteDetailsModal] Não foi possível determinar a chave da câmera', camera)
    return false
  }

  if (!connectionsMap.value) {
    connectionsMap.value = {}
  }

  const existing = connectionsMap.value?.[connectionKey]
  if (existing) {
    try {
      existing.close()
    } catch (err) {
      console.warn('[SiteDetailsModal] Falha ao encerrar conexão prévia:', err)
    }
    delete connectionsMap.value[connectionKey]
  }

  const pc = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
  })

  pc.addTransceiver('video', { direction: 'recvonly' })
  pc.addTransceiver('audio', { direction: 'recvonly' })

  pc.ontrack = (event) => {
    if (!refsMap.value) {
      refsMap.value = {}
    }
    const refs = refsMap.value || {}
    const videoEl = refs[connectionKey]
    if (videoEl && event.streams[0]) {
      videoEl.srcObject = event.streams[0]
      videoEl.muted = true
      const playPromise = videoEl.play?.()
      if (playPromise && typeof playPromise.then === 'function') {
        playPromise.catch((err) => {
          console.warn('[SiteDetailsModal] Falha ao iniciar reprodução automática do vídeo:', err)
        })
      }
    }
  }

  try {
    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    const response = await fetch(whepUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/sdp' },
      body: offer.sdp
    })

    if (!response.ok) {
      console.warn(`[SiteDetailsModal] WHEP ${label} respondeu ${response.status}`, whepUrl)
      pc.close()
      return false
    }

    const answerSdp = await response.text()
    await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp })
    connectionsMap.value[connectionKey] = pc
    console.log(`[SiteDetailsModal] Câmera conectada (${label}) via ${whepUrl}`)
    return true
  } catch (error) {
    pc.close()
    console.error('[SiteDetailsModal] Erro ao negociar WHEP:', label, whepUrl, error)
    return false
  }
}

const connectCameraWithFallback = async (camera, refsMap, connectionsMap, label) => {
  await ensurePreviewReady(camera, label)
  
  const success = await attemptWhepConnectionViaComposable(camera, refsMap, connectionsMap, label)
  
  if (!success) {
    console.error('[SiteDetailsModal] Falha ao conectar WHEP para', label)
  }
}


const zabbixError = ref(false)
const deviceStats = computed(() => countDeviceStatuses(devices.value))
const headerStatus = computed(() => (devices.value.length ? siteHeaderStatus(deviceStats.value) : 'neutral'))
const kpis = computed(() => [
  { key: 'online', label: 'Online', value: deviceStats.value.online, dot: 'bg-success' },
  { key: 'warning', label: 'Atenção', value: deviceStats.value.warning, dot: 'bg-warning' },
  { key: 'critical', label: 'Crítico', value: deviceStats.value.critical, dot: 'bg-danger' },
  { key: 'offline', label: 'Offline', value: deviceStats.value.offline, dot: 'bg-neutral-400' },
])

/**
 * EV-0065: inventário do site + disponibilidade Zabbix + métricas em lote. O estado
 * deixa de ser adivinhado pelo uptime; sem disponibilidade conhecida → «sem estado».
 */
const loadDevices = async () => {
  if (!props.site) return
  const siteId = props.site.id || props.site.site_id
  if (!siteId) {
    devices.value = []
    return
  }
  loading.value = true
  zabbixError.value = false
  try {
    const response = await get(`/api/v1/devices/?site=${encodeURIComponent(siteId)}&page_size=200`)
    const raw = response?.results || []
    const ids = raw.map((d) => d.id).filter(Boolean).join(',')
    const [status, metrics, oltSummary, portsSummary] = ids
      ? await Promise.all([
          get('/api/v1/inventory/devices/zabbix-status/', { device_ids: ids }).catch(() => ({ statuses: {}, zabbix_error: true })),
          get('/api/v1/devices/metrics-batch/', { ids }).catch(() => ({ results: {}, zabbix_error: true })),
          // EV-0111: indicadores dos cards (sem eles o card fica só com CPU/memória)
          get('/api/v1/monitoring/gpon/olt-summary/', { device_ids: ids }).catch(() => ({ olts: {} })),
          get('/api/v1/inventory/devices/ports-summary/', { device_ids: ids }).catch(() => ({ devices: {} })),
        ])
      : [{ statuses: {} }, { results: {} }, { olts: {} }, { devices: {} }]
    zabbixError.value = Boolean(status?.zabbix_error || metrics?.zabbix_error)
    const statuses = status?.statuses || {}
    const results = metrics?.results || {}
    const olts = oltSummary?.olts || {}
    const ports = portsSummary?.devices || {}
    devices.value = raw.map((d) => ({
      ...buildSiteDevice(d, statuses[String(d.id)], results[String(d.id)]),
      olt: olts[String(d.id)] || null,
      ports: ports[String(d.id)] || null,
    }))
  } catch (error) {
    console.error('[SiteDetailsModal] Erro ao carregar dispositivos:', error)
    devices.value = []
  } finally {
    loading.value = false
  }
}

const close = () => {
  emit('close')
}

// Esc/clique fora chegam pelo BaseModal; com um modal filho aberto, quem fecha é o filho.
const hasChildModalOpen = computed(() => 
  showEditModal.value || showDeviceDetailsModal.value || showMosaicModal.value || showCameraModal.value
)
const requestClose = () => {
  if (hasChildModalOpen.value) return
  // EV-0112: no nível do equipamento, Esc/X volta primeiro à lista do Site
  if (inspectedId.value !== null) {
    inspectedId.value = null
    return
  }
  close()
}

// EV-0112: navegação em 2 níveis. Guarda-se o id (não uma cópia) para o estado em
// tempo real do WebSocket, que muda o objeto em `devices`, chegar também ao nível 2.
const inspectedId = ref(null)
const inspectedDevice = computed(() => devices.value.find((d) => d.id === inspectedId.value) || null)
const inspectDevice = (device) => {
  inspectedId.value = device?.id ?? null
}
/** «Abrir tela completa ↗»: OLT → ecrã GPON filtrado pelo POP; resto → modal de Dispositivo. */
const openFullScreen = (device) => {
  if (device?.olt) {
    const pop = props.site?.name
    router.push({ path: '/monitoring/gpon', query: pop ? { pop } : {} })
    close()
    return
  }
  openDeviceDetails(device)
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
    editSnapshot.value = JSON.stringify(editForm)

    showEditModal.value = true
  } catch (error) {
    console.error('[SiteDetailsModal] Failed to load device data:', error)
    notifyError('Erro', 'Não foi possível carregar os dados do dispositivo')
  }
}

// EV-0068a: o BaseModal avisa ao fechar com alterações por guardar.
const editSnapshot = ref('')
const editDirty = computed(() => showEditModal.value && JSON.stringify(editForm) !== editSnapshot.value)

const closeEditModal = () => {
  showEditModal.value = false
}


const openDeviceDetails = (device) => {
  console.log('[SiteDetailsModal] Abrindo detalhes do dispositivo:', device?.id, device?.name)
  selectedDeviceForDetails.value = device
  showDeviceDetailsModal.value = true
}

const closeDeviceDetails = () => {
  showDeviceDetailsModal.value = false
  selectedDeviceForDetails.value = null
}

const openCameraModal = async () => {
  showCameraModal.value = true
  await loadCameras()
}

// Abre o mosaico existente do site; se não existir, abre criação já com site
const openSiteMosaicModal = async () => {
  if (!props.site || !props.site.id) return
  try {
    // Tenta buscar mosaicos filtrando por site (se a API suportar)
    let res = await get(`/setup_app/video/api/mosaics/?site_id=${props.site.id}`)
    let mosaics = []
    if (res && res.success) {
      mosaics = res.mosaics || res.results || []
    }
    // Se a API não suportar filtro, buscar todos e filtrar client-side
    if (!mosaics || mosaics.length === 0) {
      res = await get('/setup_app/video/api/mosaics/')
      if (res && res.success) {
        const all = res.mosaics || res.results || []
        mosaics = all.filter(m => m.site_id === props.site.id)
      }
    }

    if (mosaics && mosaics.length > 0) {
      // Abrir o primeiro mosaico do site em modal inline
      const mosaic = mosaics[0]
      await openMosaicViewer(mosaic.id)
      return
    }
  } catch (e) {
    console.warn('[SiteDetailsModal] Falha ao buscar mosaicos do site:', e)
  }

  // Fallback: sem mosaico para este site
  notifyError('Sem Mosaico', 'Nenhum mosaico de câmeras configurado para este site. Configure em Configurações > Câmeras.')
}

const openMosaicViewer = async (mosaicId) => {
  console.log('[SiteDetailsModal] openMosaicViewer iniciado')
  loadingMosaic.value = true
  hasConnectedMosaic.value = false
  
  try {
    const response = await get(`/setup_app/video/api/mosaics/${mosaicId}/`)
    if (response && response.success) {
      currentMosaic.value = response.mosaic || response.data
      const camerasFromMosaic = currentMosaic.value.cameras || []
      
      console.log('[SiteDetailsModal] Mosaico:', currentMosaic.value.name, '- Câmeras:', camerasFromMosaic.length)
      
      // Buscar câmeras com WHEP URLs da API de câmeras
      try {
        const camerasResponse = await get(`/api/v1/cameras/?site=${props.site.id}`)
        const camerasWithWhep = camerasResponse.results || []
        
        mosaicCameras.value = camerasFromMosaic.map((mosaicCam, idx) => {
          // Se o item do mosaico for número, criar objeto base
          if (typeof mosaicCam === 'number' || typeof mosaicCam === 'string') {
            const camId = Number(mosaicCam)
            const fullCam = camerasWithWhep.find(c => Number(c.id) === camId)
            const obj = fullCam ? { ...fullCam } : { id: camId, name: `Camera ${camId}` }
            if (!obj.whep_url) {
              const fallbackWhep = deriveWhepUrl(obj.playback_url)
              if (fallbackWhep) obj.whep_url = fallbackWhep
            }
            assignConnectionKey(obj, `mosaic-${mosaicId}-${idx}`)
            return obj
          }
          // Caso seja objeto
          const camId = mosaicCam.id ?? mosaicCam.camera_id ?? mosaicCam.pk ?? mosaicCam.camera?.id ?? idx
          const fullCam = camerasWithWhep.find(c => Number(c.id) === Number(camId) || c.name === mosaicCam.name)
          const merged = fullCam ? { ...fullCam, ...mosaicCam, id: Number(camId) } : { ...mosaicCam, id: Number(camId) }
          if (!merged.whep_url) {
            const fallbackWhep = deriveWhepUrl(merged.playback_url)
            if (fallbackWhep) merged.whep_url = fallbackWhep
          }
          assignConnectionKey(merged, `mosaic-${mosaicId}-${idx}`)
          return merged
        })
        
        // OTIMIZAÇÃO: Abrir modal ANTES de esperar streams
        showMosaicModal.value = true
        loadingMosaic.value = false
        
        // Streams iniciam em background (não bloqueia abertura do modal)
        console.log('[SiteDetailsModal] Iniciando streams em background...')
        startMosaicStreams()
        
      } catch (cameraError) {
        console.error('[SiteDetailsModal] Erro ao buscar câmeras:', cameraError)
        // Fallback: construir objetos básicos a partir dos IDs
        mosaicCameras.value = camerasFromMosaic.map((mosaicCam, idx) => {
          const base = typeof mosaicCam === 'number' || typeof mosaicCam === 'string'
            ? { id: Number(mosaicCam), name: `Camera ${mosaicCam}` }
            : { ...mosaicCam, id: mosaicCam.id ?? idx }
          return assignConnectionKey(base, `mosaic-${mosaicId}-${idx}`)
        })
        
        showMosaicModal.value = true
        loadingMosaic.value = false
      }
    }
  } catch (error) {
    console.error('[SiteDetailsModal] Erro ao carregar mosaico:', error)
    notifyError('Erro', 'Não foi possível carregar o mosaico')
    showMosaicModal.value = false
    loadingMosaic.value = false
  }
}

const startMosaicStreams = async () => {
  const startTime = performance.now()
  console.log(`[SiteDetailsModal] 🚀 Iniciando ${mosaicCameras.value.length} streams em paralelo...`)
  
  const validCameras = mosaicCameras.value.filter(cam => cam.id)
  
  const promises = validCameras.map(async (camera) => {
    const camStartTime = performance.now()
    try {
      const startUrl = `/setup_app/api/gateways/${camera.id}/video/preview/start/`
      
      // Timeout de 8 segundos (reduzido para falhar mais rápido)
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 8000)
      
      const response = await post(startUrl, {}, { signal: controller.signal })
      clearTimeout(timeoutId)
      
      const apiTime = performance.now() - camStartTime
      
      if (response && response.success && response.playback_url) {
        camera.playback_url = response.playback_proxy_url || response.playback_url
        console.log(`[SiteDetailsModal] ✅ ${camera.name} - API: ${apiTime.toFixed(0)}ms`)
        return { success: true, camera, apiTime }
      } else {
        console.error(`[SiteDetailsModal] ❌ Falha: ${camera.name} - API: ${apiTime.toFixed(0)}ms`, response)
        return { success: false, camera, apiTime }
      }
    } catch (error) {
      const apiTime = performance.now() - camStartTime
      if (error.name === 'AbortError') {
        console.error(`[SiteDetailsModal] ⏱️ Timeout: ${camera.name} - 8000ms`)
      } else {
        console.error(`[SiteDetailsModal] ❌ Erro: ${camera.name} - API: ${apiTime.toFixed(0)}ms`, error)
      }
      return { success: false, camera, apiTime, error }
    }
  })
  
  const results = await Promise.all(promises)
  const totalTime = performance.now() - startTime
  const successCount = results.filter(r => r.success).length
  const avgApiTime = results.reduce((sum, r) => sum + (r.apiTime || 0), 0) / results.length
  
  console.log(`[SiteDetailsModal] ⏱️ Total: ${totalTime.toFixed(0)}ms | API média: ${avgApiTime.toFixed(0)}ms | Sucesso: ${successCount}/${validCameras.length}`)
}

const closeMosaicModal = async () => {
  console.log('[SiteDetailsModal] Fechando modal e parando streams...')
  
  // Parar streams via API
  for (const camera of mosaicCameras.value) {
    if (!camera.gateway_id) continue
    
    try {
      const stopUrl = `/setup_app/api/gateways/${camera.gateway_id}/video/preview/stop/`
      await post(stopUrl, { camera_id: camera.id })
      console.log(`[SiteDetailsModal] Stream parado: ${camera.name}`)
    } catch (error) {
      console.error(`[SiteDetailsModal] Erro ao parar stream ${camera.name}:`, error)
    }
  }
  
  showMosaicModal.value = false
  hasConnectedMosaic.value = false
  // Limpar conexões WebRTC
  Object.values(mosaicConnections.value).forEach(pc => {
    if (pc) pc.close()
  })
  mosaicConnections.value = {}
  mosaicVideoRefs.value = {}
  mosaicCameras.value = []
  currentMosaic.value = null
}

// ESC para fechar modal de mosaico

const connectMosaicCamera = async (camera, idx) => {
  // NÃO reassinar connectionKey aqui - já foi feito em openMosaicViewer
  // assignConnectionKey(camera, `mosaic-${currentMosaic.value?.id ?? 'site'}-${idx}`)
  
  // Usar a mesma key que foi usada no template
  const key = camera.connectionKey ?? camera.id ?? camera.camera_id ?? idx
  
  console.log(`[SiteDetailsModal] 🎥 Conectando câmera:`, {
    name: camera.name,
    id: camera.id,
    connectionKey: camera.connectionKey,
    key: key,
    playback_url: camera.playback_url,
    whep_url: camera.whep_url
  })
  
  const videoEl = mosaicVideoRefs.value[key]
  if (!videoEl) {
    console.error(`[SiteDetailsModal] ERRO: Elemento <video> não encontrado para ${camera.name}, key:`, key)
    console.error('[SiteDetailsModal] Keys disponíveis:', Object.keys(mosaicVideoRefs.value))
    return
  }
  
  console.log(`[SiteDetailsModal] ✓ Elemento <video> encontrado para ${camera.name}, key:`, key)
  
  await connectCameraWithFallback(
    camera,
    mosaicVideoRefs,
    mosaicConnections,
    `mosaico:${camera.name || key}`
  )
}

const getMosaicGridClass = computed(() => {
  if (!currentMosaic.value) return 'grid-cols-2'
  const layout = currentMosaic.value.layout || '2x2'
  const cols = parseInt(layout.split('x')[0]) || 2
  return `grid-cols-${cols}`
})

const closeCameraModal = () => {
  showCameraModal.value = false
  // Limpar conexões WebRTC
  Object.values(cameraConnections.value).forEach(pc => {
    if (pc) pc.close()
  })
  cameraConnections.value = {}
  cameraVideoRefs.value = {}
  cameras.value = []
}

// ESC para fechar modal de câmeras

const loadCameras = async () => {
  if (!props.site) return
  
  loadingCameras.value = true
  try {
    // Buscar câmeras do site
    const response = await get(`/api/v1/cameras/?site=${props.site.id}`)
    const fetched = response.results || []
    cameras.value = fetched.map((cam, idx) => assignConnectionKey({ ...cam }, `camera-${idx}`))
    console.log('[SiteDetailsModal] Câmeras carregadas:', cameras.value.length)
    
    // Iniciar conexões WebRTC para cada câmera
    for (const [index, camera] of cameras.value.entries()) {
      await connectCamera(camera, index)
    }
  } catch (error) {
    console.error('[SiteDetailsModal] Erro ao carregar câmeras:', error)
    notifyError('Erro', 'Não foi possível carregar as câmeras')
  } finally {
    loadingCameras.value = false
  }
}

const connectCamera = async (camera, idx = 0) => {
  assignConnectionKey(camera, `camera-${idx}`)
  await connectCameraWithFallback(
    camera,
    cameraVideoRefs,
    cameraConnections,
    camera.name || camera.connectionKey || `camera-${idx}`
  )
}

const loadCameraCount = async () => {
  if (!props.site) return
  
  try {
    const response = await get(`/api/v1/cameras/?site=${props.site.id}`)
    cameraCount.value = response.count || response.results?.length || 0
  } catch (error) {
    console.error('[SiteDetailsModal] Erro ao contar câmeras:', error)
    cameraCount.value = 0
  }
}

const getCameraGridClass = computed(() => {
  const count = cameras.value.length
  if (count === 1) return 'grid-cols-1'
  if (count === 2) return 'grid-cols-2'
  if (count <= 4) return 'grid-cols-2'
  if (count <= 6) return 'grid-cols-3'
  return 'grid-cols-4'
})

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

// `immediate: true` é crítico: com lazy v-if no parent, o componente é
// montado já com isOpen=true — sem o flag o watcher nunca dispararia
// (não existe transição false→true a observar) e o modal abriria vazio.
watch(() => props.isOpen, (newVal) => {
  if (newVal && props.site) {
    loadDevices()
    loadCameraCount()
  } else if (!newVal) {
    inspectedId.value = null
    closeCameraModal()
    closeMosaicModal()
  }
}, { immediate: true })

// WebSocket setup for real-time updates — usa singleton compartilhado por URL.
// Antes: cada abertura do modal criava uma nova conexão WS (e o watch logo abaixo
// duplicava ainda outra). Agora 1 conexão é reutilizada entre todos os consumidores.
const wsUrl = computed(() => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return `${protocol}//${host}/ws/dashboard/status/`
})

// EV-0014: UMA instância, ligada ao abrir e desligada ao fechar. Antes, cada
// abertura criava outro useWebSocket (autoConnect) sem cleanup — vazamento de sockets.
const { connected: wsConnected, lastMessage, connect: wsConnect, disconnect: wsDisconnect } = useWebSocket(wsUrl.value, {
  autoConnect: false,
  reconnectDelay: 5000,
  maxReconnectAttempts: 10
})

// WebSocket: só disponibilidade e uptime (o canal não traz CPU/memória).
watch(lastMessage, (message) => {
  if (!message || !props.isOpen) return
  try {
    const { kind, hosts } = normalizeRealtimeMessage(message)
    if (kind !== 'hosts' || !hosts.length) return
    const byDevice = new Map(hosts.map((h) => [String(h.device_id), h]))
    devices.value.forEach((device) => {
      const host = byDevice.get(String(device.id))
      if (host) applyRealtimeHost(device, host)
    })
  } catch (error) {
    console.warn('[SiteDetailsModal] Error processing WebSocket message:', error)
  }
})

// Liga ao abrir, desliga ao fechar — sem criar instâncias novas.
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    wsConnect()
  } else {
    wsDisconnect()
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

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
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

.section-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 20px 0;
  display: flex;
  align-items: center;
  gap: 10px;
  color: rgb(var(--n-900));
}

.section-title i {
  color: rgb(var(--primary-500));
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
  color: rgb(var(--n-500));
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
  color: rgb(var(--n-900));
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 8px;
  font-size: 14px;
  color: rgb(var(--n-900));
  background: rgb(var(--surface));
  transition: all 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: rgb(var(--primary-500));
  box-shadow: 0 0 0 3px rgb(var(--primary-500) / 0.1);
}

.form-input:read-only {
  background: rgb(var(--n-50));
  cursor: not-allowed;
}

.input-with-icon {
  position: relative;
}

.input-with-icon i {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: rgb(var(--n-400));
}

.input-with-icon .form-input {
  padding-left: 40px;
}

.field-help {
  font-size: 12px;
  color: rgb(var(--n-500));
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
  border-top: 1px solid rgb(var(--n-200));
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
  background: rgb(var(--n-100));
  color: rgb(var(--n-600));
}

.btn-secondary:hover {
  background: rgb(var(--n-200));
}

.btn-primary {
  background: rgb(var(--primary-600));
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgb(var(--primary-500) / 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

/* Animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

/* Área de vídeo: sempre escura (como o visualizador de mosaicos), ocupa o corpo do BaseModal full */
.camera-modal-body {
  height: 100%;
  padding: 24px;
  overflow-y: auto;
  background: #0f172a;
  color: #e2e8f0;
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

.mosaic-modal-body {
  height: 100%;
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

</style>
