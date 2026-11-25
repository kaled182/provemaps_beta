<template>
  <aside class="spi" :data-testid="`sw-inspector-${sw.device_id}`">
    <p v-if="!port" class="text-sm text-neutral-500">Sem portas para inspecionar neste switch.</p>
    <template v-else>
      <header class="flex items-center gap-2 flex-wrap">
        <span class="num font-semibold text-neutral-900" data-testid="spi-name">{{ port.name }}</span>
        <span class="state" :class="`state-${port.state}`" data-testid="spi-state">{{ badge }}</span>
        <span v-if="preview" class="hint" title="Porta mais crítica deste switch — clique numa porta para a escolher" data-testid="spi-preview">mais crítica</span>
      </header>
      <p class="desc" :title="port.description || ''">{{ port.description || 'Sem descrição no switch' }}</p>
      <p v-if="port.cable_name" class="cable">Cabo: {{ port.cable_name }}</p>

      <dl class="grid grid-cols-2 gap-x-3 gap-y-1.5 mt-2 text-sm">
        <dt>RX</dt>
        <dd data-testid="spi-rx" :class="rxClass">{{ port.los ? '-40 dBm (LOS)' : dbm(port.rx_dbm) }}</dd>
        <dt>TX</dt>
        <dd data-testid="spi-tx">{{ dbm(port.tx_dbm) }}</dd>
        <dt>Velocidade</dt>
        <dd>{{ port.speed_label || '—' }} <span class="text-neutral-500">· {{ KIND[port.kind] }}</span></dd>
        <dt>Tráfego ↓ / ↑</dt>
        <dd data-testid="spi-traffic" :class="{ 'text-warning': port.reasons.includes('utilization') }">
          {{ formatBps(port.in_bps) }} / {{ formatBps(port.out_bps) }}
          <span v-if="port.utilization_pct !== null" class="text-neutral-500">· {{ port.utilization_pct }}%</span>
        </dd>
        <dt>Uptime</dt>
        <dd>{{ port.uptime_s ? formatDuration(port.uptime_s) : '—' }}</dd>
        <dt>Erros ↓ / ↑</dt>
        <dd>{{ n(port.in_errors) }} / {{ n(port.out_errors) }}</dd>
      </dl>

      <!-- 24 h: tráfego e sinal (Zabbix, pela porta do inventário) -->
      <div class="trend" data-testid="spi-trend">
        <p class="text-xs font-semibold text-neutral-700">Últimas 24 h</p>
        <p v-if="!port.port_id" class="text-xs text-neutral-500" data-testid="spi-no-inventory">
          Porta sem cadastro no inventário — sem histórico.
        </p>
        <p v-else-if="loading" class="text-xs text-neutral-500">Carregando histórico…</p>
        <template v-else>
          <TimeSeriesChart v-if="trafficSeries.length" :series="trafficSeries" unit="bps" :decimals="0" :height="80" compact />
          <p v-else class="text-xs text-neutral-500" data-testid="spi-no-traffic">{{ trafficError || 'Sem histórico de tráfego.' }}</p>
          <TimeSeriesChart
            v-if="rxSeries.length"
            :series="rxSeries"
            :thresholds="chartThresholds"
            unit="dBm"
            :decimals="1"
            :height="70"
            compact
          />
        </template>
      </div>

      <div class="flex gap-2 mt-3 flex-wrap">
        <button type="button" class="act" data-testid="spi-copy" @click="copySummary">
          <component :is="copied ? PhCheck : PhClipboardText" :size="14" />
          {{ copied ? 'Copiado!' : 'Copiar resumo' }}
        </button>
        <button
          type="button"
          class="act"
          :disabled="!port.cable_id"
          :title="port.cable_id ? `Abrir o mapa com o cabo ${port.cable_name || ''} em destaque` : 'Porta sem cabo ligado no inventário'"
          data-testid="spi-map"
          @click="openMap"
        >
          <PhMapPin :size="14" /> Ver enlace no mapa
        </button>
      </div>
      <p v-if="copyError" class="mt-1 text-xs text-danger" role="alert">Não foi possível copiar: {{ copyError }}</p>
    </template>
  </aside>
</template>

<script setup>
/**
 * Inspetor da porta do switch (EV-0116): estado atual (do payload), 24 h de tráfego e RX
 * (rotas da porta do inventário: traffic_history e optical_history, Zabbix), resumo para OS
 * e o enlace no mapa (?cable=<id>).
 */
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { PhCheck, PhClipboardText, PhMapPin } from '@phosphor-icons/vue'
import { useApi } from '@/composables/useApi'
import TimeSeriesChart from '@/components/charts/TimeSeriesChart.vue'
import { copyText } from '@/components/Gpon/ponDiagnosis'
import { STATE_LABELS } from '@/composables/useSwitchesOverview'
import { formatBps, formatDuration, formatInt } from '@/utils/ptBrFormat'

const props = defineProps({
  sw: { type: Object, required: true },
  port: { type: Object, default: null },
  preview: { type: Boolean, default: false },
  thresholds: { type: Object, default: null },
})

const KIND = { optical: 'óptica', electrical: 'elétrica', mgmt: 'gerência' }
const router = useRouter()
const api = useApi()
const n = (v) => (v === null || v === undefined ? '—' : formatInt(v))
const dbm = (v) => (v === null || v === undefined ? '—' : `${v.toFixed(2)} dBm`)

const badge = computed(() => {
  const p = props.port
  if (!p) return ''
  if (p.state === 'down') return p.los ? 'DOWN · LOS' : 'DOWN'
  if (p.state === 'free') return 'Livre'
  if (p.state === 'unknown') return 'Sem dados'
  return `UP · ${STATE_LABELS[p.state]}`
})
const rxClass = computed(() => {
  const p = props.port
  const t = props.thresholds
  if (!p || !t) return ''
  if (p.los) return 'text-danger'
  if (p.rx_dbm === null || p.rx_dbm === undefined) return 'text-neutral-500'
  if (p.rx_dbm < t.critical) return 'text-danger'
  if (p.rx_dbm <= t.warning) return 'text-warning'
  return 'text-success'
})
const chartThresholds = computed(() =>
  props.thresholds
    ? [
        { value: props.thresholds.warning, label: 'Atenção' },
        { value: props.thresholds.critical, label: 'Crítico' },
      ]
    : [],
)

// ── histórico 24 h ───────────────────────────────────────────────────────────
const traffic = ref(null)
const optical = ref(null)
const trafficError = ref('')
const loading = ref(false)
let seq = 0

async function loadHistory() {
  const mine = ++seq
  traffic.value = null
  optical.value = null
  trafficError.value = ''
  const id = props.port?.port_id
  if (!id) return
  loading.value = true
  const [t, o] = await Promise.allSettled([
    api.get(`/api/v1/ports/${id}/traffic_history/`, { hours: 24 }),
    props.port.kind === 'optical' ? api.get(`/api/v1/ports/${id}/optical_history/`, { hours: 24 }) : Promise.resolve(null),
  ])
  if (mine !== seq) return
  if (t.status === 'fulfilled') traffic.value = t.value
  else trafficError.value = `Erro ao carregar o tráfego: ${t.reason?.message || 'desconhecido'}`
  optical.value = o.status === 'fulfilled' ? o.value : null
  loading.value = false
}
watch(() => [props.sw.device_id, props.port?.name, props.port?.port_id], loadHistory, { immediate: true })

/**
 * `/api/v1/ports/<id>/traffic_history/` devolve `{history: [{timestamp, traffic_in, traffic_out}],
 * statistics}` (linhas já alinhadas por bucket, bps, None nos buracos) — EV-0129: lia-se o formato
 * de outra rota e o gráfico ficava sempre «sem histórico».
 */
const trafficSeries = computed(() => {
  const rows = Array.isArray(traffic.value?.history) ? traffic.value.history : []
  const inn = rows.map((r) => ({ x: r.timestamp, y: r.traffic_in ?? null }))
  const out = rows.map((r) => ({ x: r.timestamp, y: r.traffic_out ?? null }))
  const real = (pts) => pts.filter((p) => p.y !== null).length
  if (real(inn) < 2 && real(out) < 2) return []
  return [
    { label: '↓ Entrada', data: inn },
    { label: '↑ Saída', data: out },
  ]
})
const rxSeries = computed(() => {
  const rows = Array.isArray(optical.value) ? optical.value : []
  const pts = rows.map((r) => ({ x: r.timestamp, y: r.rx_power ?? null }))
  return pts.filter((p) => p.y !== null).length >= 2 ? [{ label: 'RX', data: pts }] : []
})

// ── ações ────────────────────────────────────────────────────────────────────
const copied = ref(false)
const copyError = ref('')
let copiedTimer = null

function summary() {
  const p = props.port
  const s = props.sw
  const lines = [
    `Switch: ${s.name}${s.site_name ? ` (${s.site_name})` : ''}${s.ip ? ` · ${s.ip}` : ''}`,
    `Porta: ${p.name}${p.description ? ` — ${p.description}` : ''}`,
    `Estado: ${badge.value}`,
    `RX: ${p.los ? '-40 dBm (LOS)' : dbm(p.rx_dbm)} · TX: ${dbm(p.tx_dbm)}`,
    `Velocidade: ${p.speed_label || '—'} · Tráfego ↓ ${formatBps(p.in_bps)} / ↑ ${formatBps(p.out_bps)}`,
  ]
  if (p.cable_name) lines.push(`Cabo: ${p.cable_name}`)
  lines.push(`Coletado: ${new Date().toLocaleString('pt-BR')}`)
  return lines.join('\n')
}
async function copySummary() {
  copyError.value = ''
  try {
    await copyText(summary())
    copied.value = true
    clearTimeout(copiedTimer)
    copiedTimer = setTimeout(() => (copied.value = false), 1500)
  } catch (e) {
    copyError.value = e?.message || 'erro desconhecido'
  }
}
function openMap() {
  if (!props.port?.cable_id) return
  router.push({ path: '/monitoring/backbone/map/default', query: { cable: String(props.port.cable_id) } })
}
</script>

<style scoped>
.spi {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 8px;
  background: rgb(var(--surface));
  min-width: 0;
}
.num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
dt {
  font-size: 11px;
  color: rgb(var(--n-500));
}
dd {
  margin: 0;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  color: rgb(var(--n-900));
}
.desc {
  margin: 2px 0 0;
  font-size: 12px;
  color: rgb(var(--n-700));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cable {
  margin: 0;
  font-size: 11px;
  color: rgb(var(--n-500));
}
.state {
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid rgb(var(--n-300));
  color: rgb(var(--n-600));
}
.state-normal { color: rgb(var(--success)); border-color: rgb(var(--success) / 0.4); background: rgb(var(--success) / 0.1); }
.state-warning { color: rgb(var(--warning)); border-color: rgb(var(--warning) / 0.45); background: rgb(var(--warning) / 0.1); }
.state-critical,
.state-down { color: rgb(var(--danger)); border-color: rgb(var(--danger) / 0.45); background: rgb(var(--danger) / 0.1); }
.hint {
  font-size: 11px;
  color: rgb(var(--n-500));
  font-style: italic;
}
.trend {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgb(var(--n-200));
}
.act {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 10px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 6px;
  font-size: 12px;
  color: rgb(var(--n-700));
}
.act:hover:not(:disabled) {
  border-color: rgb(var(--primary-500));
  color: rgb(var(--primary-600));
}
.act:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
