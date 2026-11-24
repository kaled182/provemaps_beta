<template>
  <section class="sdi" data-testid="site-device-inspector">
    <!-- Trilha: Voltar · Site › Equipamento · estado · IP · tela completa -->
    <header class="sdi-head">
      <button type="button" class="sdi-back" data-testid="site-inspector-back" @click="emit('back')">
        <PhArrowLeft :size="14" /> Voltar
      </button>
      <nav class="sdi-crumbs" aria-label="Trilha">
        <button type="button" class="sdi-crumb-site" @click="emit('back')">{{ siteName }}</button>
        <PhCaretRight :size="12" class="sdi-crumb-sep" aria-hidden="true" />
        <span class="sdi-crumb-device" :title="device.name" data-testid="site-inspector-name">{{ device.name }}</span>
      </nav>
      <span class="sdi-status" :class="`sdi-status-${device.status}`" data-testid="site-inspector-status">{{ statusLabel }}</span>
      <span v-if="device.ip" class="sdi-ip num">{{ device.ip }}</span>
      <button type="button" class="sdi-full" data-testid="site-inspector-full" @click="emit('open-full', device)">
        Abrir tela completa <PhArrowSquareOut :size="13" />
      </button>
    </header>

    <!-- Faixa: CPU · Memória · Uptime · Temperatura -->
    <div class="sdi-strip" data-testid="site-inspector-strip">
      <div v-for="k in strip" :key="k.key" class="sdi-kpi" :title="k.title || ''">
        <span class="sdi-kpi-label">{{ k.label }}</span>
        <span class="sdi-kpi-value num" :class="k.cls" :data-testid="`site-inspector-${k.key}`">{{ k.value }}</span>
        <small v-if="k.note" class="sdi-kpi-note">{{ k.note }}</small>
      </div>
    </div>

    <!-- Portas ópticas em uso -->
    <div class="sdi-ports-head">
      <span class="text-sm font-semibold text-neutral-700">Portas ópticas em uso</span>
      <span class="num text-sm text-neutral-500" data-testid="site-inspector-ports-count">{{ opticalPorts.length }}</span>
      <span v-if="staleCount" class="text-xs text-neutral-500">· {{ staleCount }} com leitura antiga</span>
    </div>
    <p v-if="loadingPorts" class="py-6 text-center text-sm text-neutral-500">A carregar portas…</p>
    <p v-else-if="portsError" class="py-6 text-center text-sm text-danger" role="alert" data-testid="site-inspector-ports-error">
      Erro ao carregar as portas: {{ portsError }}
    </p>
    <p v-else-if="!opticalPorts.length" class="py-6 text-center text-sm text-neutral-500" data-testid="site-inspector-ports-empty">
      Nenhuma porta com leitura óptica neste equipamento.
    </p>
    <div v-else class="grid grid-cols-2 gap-2.5 lg:grid-cols-3" data-testid="site-inspector-ports">
      <article
        v-for="p in opticalPorts"
        :key="p.id"
        class="sdi-port"
        :class="`sdi-port-${portState(p, thresholds).key}`"
        data-testid="site-inspector-port"
      >
        <header class="sdi-port-head">
          <span class="sdi-port-name num" :title="p.name">{{ p.name }}</span>
          <span class="sdi-port-state">{{ portState(p, thresholds).label }}</span>
        </header>
        <p class="sdi-port-desc" :title="p.description || ''">{{ p.description || p.connected_cable?.name || '—' }}</p>
        <div class="sdi-port-levels num">
          <span :class="levelClass(p, 'rx')" :title="p.stale ? 'Leitura antiga' : ''">RX {{ dbm(p.optical_rx_power) }}</span>
          <span :class="levelClass(p, 'tx')">TX {{ dbm(p.optical_tx_power) }}</span>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
/**
 * Nível 2 do modal de Site (EV-0112): o equipamento inspecionado sem sair do mapa.
 * Faixa CPU/Memória/Uptime (já vêm do card) + Temperatura (`/devices/<id>/temperature/`)
 * e as portas com leitura óptica, coloridas pelos limiares da configuração.
 * O chassi das OLT entra no EV-0113.
 */
import { computed, ref, watch } from 'vue'
import { PhArrowLeft, PhArrowSquareOut, PhCaretRight } from '@phosphor-icons/vue'
import { useApi } from '@/composables/useApi'
import { fetchAllPages } from '@/utils/paginate'
import { DEVICE_STATUS_LABELS, formatUptimeSeconds, metricBar } from '@/utils/siteDevices'
import {
  DEFAULT_THRESHOLDS,
  levelOf,
  normalizePort,
  portState,
  sortPorts,
  thresholdsFromConfig,
} from '@/utils/devicePorts'

const props = defineProps({
  device: { type: Object, required: true },
  siteName: { type: String, default: '' },
})
const emit = defineEmits(['back', 'open-full'])

const api = useApi()
const ports = ref([])
const loadingPorts = ref(false)
const portsError = ref('')
const thresholds = ref({ ...DEFAULT_THRESHOLDS })
const temperature = ref(null)
let seq = 0

const TEMPERATURE_REASON = {
  no_host: 'Equipamento sem host no Zabbix',
  no_item: 'Sem item de temperatura no Zabbix',
  no_reading: 'Sensores sem leitura recente no Zabbix',
}

async function load() {
  const mine = ++seq
  const id = props.device.id
  loadingPorts.value = true
  portsError.value = ''
  temperature.value = null
  const [cfg, temp, raw] = await Promise.allSettled([
    api.get('/setup_app/api/config/'),
    api.get(`/api/v1/inventory/devices/${encodeURIComponent(id)}/temperature/`),
    fetchAllPages(api, `/api/v1/ports/?device=${encodeURIComponent(id)}`),
  ])
  if (mine !== seq) return
  if (cfg.status === 'fulfilled') thresholds.value = thresholdsFromConfig(cfg.value?.configuration || {})
  temperature.value = temp.status === 'fulfilled' ? temp.value : { error: true }
  if (raw.status === 'fulfilled') {
    const now = Date.now()
    ports.value = raw.value.map((p) => normalizePort(p, now))
  } else {
    ports.value = []
    portsError.value = raw.reason?.message || 'erro desconhecido'
  }
  loadingPorts.value = false
}
watch(() => props.device.id, load, { immediate: true })

const statusLabel = computed(() => DEVICE_STATUS_LABELS[props.device.status] || DEVICE_STATUS_LABELS.unknown)

const pct = (value, source) => {
  const bar = metricBar(value)
  return {
    value: bar ? bar.label : '—',
    cls: bar ? `lv-${bar.level}` : '',
    note: bar && source === 'manual' ? 'manual' : '',
  }
}

const temperatureKpi = computed(() => {
  const t = temperature.value
  if (!t) return { key: 'temperature', label: 'Temperatura', value: '…' }
  if (t.error) return { key: 'temperature', label: 'Temperatura', value: '—', title: 'Erro ao consultar a temperatura' }
  if (!t.zabbix_ok) return { key: 'temperature', label: 'Temperatura', value: '—', title: 'Zabbix indisponível' }
  if (t.temperature_c === null || t.temperature_c === undefined) {
    return { key: 'temperature', label: 'Temperatura', value: '—', title: TEMPERATURE_REASON[t.reason] || 'Sem leitura' }
  }
  const when = t.at ? new Date(t.at).toLocaleString('pt-BR') : ''
  return {
    key: 'temperature',
    label: 'Temperatura',
    value: `${t.temperature_c.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} °C`,
    title: `${t.sensor || 'Sensor'}${t.sensors > 1 ? ` (o mais quente de ${t.sensors})` : ''}${when ? ` · ${when}` : ''}`,
  }
})

const strip = computed(() => [
  { key: 'cpu', label: 'CPU', ...pct(props.device.cpu, props.device.cpuSource) },
  { key: 'memory', label: 'Memória', ...pct(props.device.memory, props.device.memorySource) },
  {
    key: 'uptime',
    label: 'Uptime',
    value: props.device.uptimeHuman || formatUptimeSeconds(props.device.uptime) || '—',
  },
  temperatureKpi.value,
])

/** Só as portas com leitura óptica, pior primeiro (o critério de cor é o do modal de Dispositivo). */
const opticalPorts = computed(() =>
  sortPorts(
    ports.value.filter((p) => p.optical_rx_power !== null || p.optical_tx_power !== null),
    thresholds.value,
  ),
)
const staleCount = computed(() => opticalPorts.value.filter((p) => p.stale).length)

const dbm = (v) => (v === null || v === undefined ? '—' : `${v.toFixed(2)} dBm`)
function levelClass(port, which) {
  if (which === 'tx') return port.optical_tx_power === null ? 'lv-none' : ''
  if (port.optical_rx_power === null) return 'lv-none'
  if (port.stale) return 'lv-stale'
  return `lv-${levelOf(port.optical_rx_power, thresholds.value)}`
}
</script>

<style scoped>
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.sdi-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgb(var(--n-200));
}
.sdi-back,
.sdi-full {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 10px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 6px;
  font-size: 12px;
  color: rgb(var(--n-700));
}
.sdi-back:hover,
.sdi-full:hover {
  border-color: rgb(var(--primary-500));
  color: rgb(var(--primary-600));
}
.sdi-full {
  margin-left: auto;
}
.sdi-crumbs {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  font-size: 13px;
}
.sdi-crumb-site {
  color: rgb(var(--n-500));
  white-space: nowrap;
}
.sdi-crumb-site:hover {
  color: rgb(var(--primary-600));
  text-decoration: underline;
}
.sdi-crumb-sep {
  color: rgb(var(--n-400));
  flex-shrink: 0;
}
.sdi-crumb-device {
  font-weight: 600;
  color: rgb(var(--n-900));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sdi-status {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 9999px;
  background: rgb(var(--n-100));
  color: rgb(var(--n-600));
}
.sdi-status-online { background: rgb(var(--success) / 0.14); color: rgb(var(--success)); }
.sdi-status-warning { background: rgb(var(--warning) / 0.16); color: rgb(var(--warning)); }
.sdi-status-critical,
.sdi-status-offline { background: rgb(var(--danger) / 0.14); color: rgb(var(--danger)); }
.sdi-ip {
  font-size: 12px;
  color: rgb(var(--n-600));
}
.sdi-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin: 12px 0;
}
.sdi-kpi {
  display: flex;
  flex-direction: column;
  padding: 6px 10px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 6px;
}
.sdi-kpi-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: rgb(var(--n-500));
}
.sdi-kpi-value {
  font-size: 16px;
  font-weight: 600;
  color: rgb(var(--n-900));
}
.sdi-kpi-note {
  font-size: 9px;
  color: rgb(var(--n-500));
}
.sdi-ports-head {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 8px;
}
.sdi-port {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 8px;
  background: rgb(var(--surface));
  min-width: 0;
}
.sdi-port-critical { border-color: rgb(var(--danger) / 0.45); }
.sdi-port-warning { border-color: rgb(var(--warning) / 0.45); }
.sdi-port-head {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.sdi-port-name {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  font-weight: 600;
  color: rgb(var(--n-900));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sdi-port-state {
  font-size: 10px;
  color: rgb(var(--n-500));
  white-space: nowrap;
}
.sdi-port-desc {
  margin: 0;
  font-size: 11px;
  color: rgb(var(--n-600));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sdi-port-levels {
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: rgb(var(--n-700));
}
.lv-normal { color: rgb(var(--success)); }
.lv-warning { color: rgb(var(--warning)); }
.lv-critical { color: rgb(var(--danger)); }
.lv-stale,
.lv-none { color: rgb(var(--n-500)); }
@media (max-width: 640px) {
  .sdi-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
