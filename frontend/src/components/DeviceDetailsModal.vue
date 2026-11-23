<template>
  <BaseModal
    :show="isOpen"
    :title="device?.name || 'Carregando…'"
    :subtitle="subtitle"
    :icon="PhHardDrives"
    :status="headerStatus"
    :z-index="3400"
    size="detail"
    @close="requestClose"
  >
    <!-- 4 KPIs do equipamento -->
    <div class="grid grid-cols-2 gap-2 sm:grid-cols-4" data-testid="device-kpis">
      <div v-for="k in kpis" :key="k.key" class="rounded-md border border-neutral-200 px-3 py-2">
        <div class="text-[11px] uppercase tracking-wide text-neutral-500">{{ k.label }}</div>
        <div class="flex items-baseline gap-1.5">
          <span v-if="k.dot" class="h-2 w-2 self-center rounded-full" :class="k.dot" aria-hidden="true" />
          <span class="font-mono text-xl font-semibold tabular-nums text-neutral-900" :data-testid="`device-kpi-${k.key}`">{{ k.value }}</span>
          <small v-if="k.note" class="text-[10px] text-neutral-500">{{ k.note }}</small>
        </div>
      </div>
    </div>

    <!-- Barra das portas numa linha -->
    <div class="mt-4 mb-2 flex flex-wrap items-center gap-2">
      <span class="text-sm font-semibold text-neutral-700">Portas</span>
      <span class="font-mono text-sm tabular-nums text-neutral-500" data-testid="device-ports-count">
        {{ filterOnlyInUse ? `${inUseCount} em uso de ${ports.length}` : ports.length }}
      </span>
      <div class="ml-auto flex items-center gap-2">
        <input
          v-model="searchQuery"
          type="search"
          placeholder="Buscar porta ou descrição…"
          class="h-8 w-56 rounded-md border border-neutral-200 bg-surface px-2.5 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-primary-500 focus:outline-none"
        />
        <button
          type="button"
          class="h-8 rounded-md border border-neutral-200 px-2.5 text-sm text-neutral-700 hover:bg-neutral-100"
          :class="{ 'border-primary-500 text-primary-600': !filterOnlyInUse }"
          data-testid="device-ports-toggle"
          @click="filterOnlyInUse = !filterOnlyInUse"
        >
          {{ filterOnlyInUse ? 'Mostrar todas' : 'Só em uso' }}
        </button>
        <button
          type="button"
          class="inline-flex h-8 items-center gap-1.5 rounded-md border border-neutral-200 px-2.5 text-sm text-neutral-700 hover:bg-neutral-100 disabled:opacity-50"
          :disabled="!displayedPorts.length"
          title="Exportar as portas visíveis para CSV"
          @click="exportToCSV"
        >
          <PhDownloadSimple :size="14" /> CSV
        </button>
      </div>
    </div>

    <div v-if="loadingPorts" class="py-8 text-center text-sm text-neutral-500">A carregar portas…</div>
    <div v-else-if="portsError" class="py-8 text-center text-sm text-danger" data-testid="device-ports-error">
      Erro ao carregar as portas: {{ portsError }}
    </div>
    <div v-else-if="displayedPorts.length === 0" class="py-8 text-center text-sm text-neutral-500" data-testid="device-ports-empty">
      {{ ports.length ? 'Nenhuma porta corresponde ao filtro' : 'Este equipamento não tem portas cadastradas' }}
    </div>
    <div v-else class="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3" data-testid="device-ports-grid">
      <DevicePortCard
        v-for="port in displayedPorts"
        :key="port.id"
        :port="port"
        :thresholds="thresholds"
        @traffic="openTrafficModal"
        @alarm="openAlarmConfig"
        @connectivity="openConnectivityMap"
        @actions="openPortActions"
      />
    </div>
  </BaseModal>

  <!-- Sub-modais (z-index 12000–14000, acima do BaseModal) -->
  <PortActionsModal :is-open="showPortActions" :port="selectedPort" @close="closePortActions" @refresh="loadPorts" />
  <AlarmConfigModal :is-open="showAlarmConfig" :port="selectedPort" @close="closeAlarmConfig" @saved="loadPorts" />
  <ConnectivityMapModal
    :is-open="showConnectivityMap"
    :port="selectedPort"
    :device-info="device"
    @close="closeConnectivityMap"
  />
  <!-- v-if + defineAsyncComponent: o chunk só baixa quando se abre o tráfego pela 1.ª vez -->
  <PortTrafficModal
    v-if="showTrafficModal"
    :is-open="showTrafficModal"
    :port="selectedPort"
    @close="closeTrafficModal"
  />
</template>

<script setup>
/**
 * Modal de Dispositivo (EV-0066) no BaseModal: 4 KPIs do equipamento (sem «0 %»
 * inventado), grelha de portas com RX/TX em pílulas pelos limiares da configuração,
 * todas as páginas de portas (a OLT maior tem 240; antes só vinham 100).
 */
import { ref, computed, watch, defineAsyncComponent } from 'vue'
import { PhHardDrives, PhDownloadSimple } from '@phosphor-icons/vue'
import { useApi } from '@/composables/useApi'
import BaseModal from '@/components/Common/BaseModal.vue'
import DevicePortCard from '@/components/DeviceDetails/DevicePortCard.vue'
import PortActionsModal from './PortActionsModal.vue'
import AlarmConfigModal from './AlarmConfigModal.vue'
import ConnectivityMapModal from './ConnectivityMapModal.vue'
import { fetchAllPages } from '@/utils/paginate'
import { DEVICE_STATUS_LABELS, formatUptimeSeconds } from '@/utils/siteDevices'
import {
  DEFAULT_THRESHOLDS,
  thresholdsFromConfig,
  normalizePort,
  filterPorts,
  sortPorts,
  portsToCsv,
} from '@/utils/devicePorts'

// Lazy: PortTrafficModal carrega Chart.js; só quem abre o tráfego paga o peso.
const PortTrafficModal = defineAsyncComponent(() => import('./PortTrafficModal.vue'))

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  device: { type: Object, default: null },
})
const emit = defineEmits(['close'])

const api = useApi()

const ports = ref([])
const loadingPorts = ref(false)
const portsError = ref('')
const filterOnlyInUse = ref(true)
const searchQuery = ref('')
const thresholds = ref({ ...DEFAULT_THRESHOLDS })
const selectedPort = ref(null)
const showPortActions = ref(false)
const showAlarmConfig = ref(false)
const showConnectivityMap = ref(false)
const showTrafficModal = ref(false)

const hasChildModalOpen = computed(
  () => showPortActions.value || showAlarmConfig.value || showConnectivityMap.value || showTrafficModal.value,
)
// Esc/clique fora chegam pelo BaseModal; com um sub-modal aberto, quem fecha é ele.
const requestClose = () => {
  if (!hasChildModalOpen.value) emit('close')
}

const subtitle = computed(() => [props.device?.type, props.device?.ip].filter(Boolean).join(' · '))

const HEADER_STATUS = { online: 'online', warning: 'attention', critical: 'critical', offline: 'critical' }
const headerStatus = computed(() => HEADER_STATUS[props.device?.status] || 'neutral')

const STATUS_DOT = { online: 'bg-success', warning: 'bg-warning', critical: 'bg-danger', offline: 'bg-danger' }
const pct = (v) => (typeof v === 'number' && !Number.isNaN(v) ? `${Math.round(v)}%` : '—')
const kpis = computed(() => {
  const d = props.device || {}
  const status = d.status || 'unknown'
  return [
    { key: 'cpu', label: 'CPU', value: pct(d.cpu), note: d.cpu != null && d.cpuSource === 'manual' ? 'manual' : '' },
    { key: 'memory', label: 'Memória', value: pct(d.memory), note: d.memory != null && d.memorySource === 'manual' ? 'manual' : '' },
    { key: 'uptime', label: 'Uptime', value: d.uptimeHuman || formatUptimeSeconds(d.uptime) || '—' },
    { key: 'status', label: 'Estado', value: DEVICE_STATUS_LABELS[status] || DEVICE_STATUS_LABELS.unknown, dot: STATUS_DOT[status] || 'bg-neutral-400' },
  ]
})

const inUseCount = computed(() => filterPorts(ports.value, { onlyInUse: true }).length)
const displayedPorts = computed(() =>
  sortPorts(filterPorts(ports.value, { onlyInUse: filterOnlyInUse.value, query: searchQuery.value }), thresholds.value),
)

const loadThresholds = async () => {
  try {
    const res = await api.get('/setup_app/api/config/')
    thresholds.value = thresholdsFromConfig(res?.configuration || {})
  } catch (e) {
    console.warn('[DeviceDetailsModal] Limiares indisponíveis, a usar os de omissão', e)
  }
}

const loadPorts = async () => {
  if (!props.device?.id) return
  loadingPorts.value = true
  portsError.value = ''
  try {
    const raw = await fetchAllPages(api, `/api/v1/ports/?device=${encodeURIComponent(props.device.id)}`)
    const now = Date.now()
    ports.value = raw.map((p) => normalizePort(p, now))
  } catch (error) {
    console.error('[DeviceDetailsModal] Erro ao carregar portas:', error)
    ports.value = []
    portsError.value = error?.message || 'erro desconhecido'
  } finally {
    loadingPorts.value = false
  }
}

const exportToCSV = () => {
  const blob = new Blob([portsToCsv(displayedPorts.value, thresholds.value)], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `portas_${(props.device?.name || 'equipamento').replace(/[^a-z0-9]/gi, '_')}_${new Date().toISOString().split('T')[0]}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const openWith = (flag) => (port) => {
  selectedPort.value = port
  flag.value = true
}
const closeWith = (flag) => () => {
  flag.value = false
  selectedPort.value = null
}
const openPortActions = openWith(showPortActions)
const closePortActions = closeWith(showPortActions)
const openAlarmConfig = openWith(showAlarmConfig)
const closeAlarmConfig = closeWith(showAlarmConfig)
const openConnectivityMap = openWith(showConnectivityMap)
const closeConnectivityMap = closeWith(showConnectivityMap)
const openTrafficModal = openWith(showTrafficModal)
const closeTrafficModal = closeWith(showTrafficModal)

watch(
  () => [props.isOpen, props.device?.id],
  ([open, id]) => {
    if (!open || !id) return
    searchQuery.value = ''
    Promise.allSettled([loadThresholds(), loadPorts()])
  },
  { immediate: true },
)
</script>
