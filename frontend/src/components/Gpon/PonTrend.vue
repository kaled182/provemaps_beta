<template>
  <div class="trend" data-testid="pon-trend">
    <div class="flex items-center justify-between gap-2">
      <p class="text-xs font-semibold text-neutral-700">RX médio · 24 h</p>
      <span v-if="traffic" class="traffic num" :class="{ 'traffic-stale': traffic.stale }" :title="trafficTitle" data-testid="pon-traffic">
        <template v-if="traffic.available && (traffic.in_bps !== null || traffic.out_bps !== null)">
          ↓ {{ formatBps(traffic.in_bps) }} · ↑ {{ formatBps(traffic.out_bps) }}
        </template>
        <template v-else-if="traffic.available">tráfego sem leitura</template>
        <template v-else>tráfego da PON indisponível</template>
      </span>
    </div>
    <p v-if="loading && !body" class="mt-1 text-xs text-neutral-500">Carregando tendência…</p>
    <p v-else-if="body && !body.zabbix_ok" class="mt-1 text-xs text-warning" role="alert" data-testid="pon-trend-zabbix">
      Zabbix indisponível: tendência não carregada.
    </p>
    <p v-else-if="error" class="mt-1 text-xs text-danger" role="alert">Erro ao carregar a tendência: {{ error }}</p>
    <template v-else-if="body">
      <TimeSeriesChart
        v-if="series.length"
        :series="series"
        :thresholds="chartThresholds"
        unit="dBm"
        :decimals="1"
        :height="90"
        compact
      />
      <p v-else class="mt-1 text-xs text-neutral-500" data-testid="pon-trend-empty">
        Sem tendência de RX no Zabbix nas últimas 24 h para esta PON.
      </p>
      <p v-if="series.length" class="text-[10px] text-neutral-500">
        Médias horárias do Zabbix; o último ponto é a coleta atual.
      </p>
    </template>
  </div>
</template>

<script setup>
/**
 * Tendência 24 h do RX médio da PON e tráfego atual da porta (EV-0109).
 * Dados de `GET /api/v1/monitoring/gpon/pon-trend/` (tendências horárias do Zabbix, em
 * cache 5 min no backend). A hora em curso ainda não tem tendência: junta-se o RX médio
 * da última coleta (`currentRx`) como último ponto.
 */
import { computed, ref, watch } from 'vue'
import { useApi } from '@/composables/useApi'
import TimeSeriesChart from '@/components/charts/TimeSeriesChart.vue'
import { formatBps } from '@/utils/ptBrFormat'

const TREND_URL = '/api/v1/monitoring/gpon/pon-trend/'

const props = defineProps({
  deviceId: { type: Number, required: true },
  ponId: { type: String, required: true },
  /** RX médio da última coleta (payload do resumo), para o ponto atual */
  currentRx: { type: Number, default: null },
  thresholds: { type: Object, default: null },
})

const api = useApi()
const body = ref(null)
const loading = ref(false)
const error = ref('')
let seq = 0

async function load() {
  const mine = ++seq
  loading.value = true
  error.value = ''
  try {
    const data = await api.get(TREND_URL, { device: props.deviceId, pon: props.ponId })
    if (mine === seq) body.value = data
  } catch (e) {
    if (mine === seq) error.value = e?.message || 'erro desconhecido'
  } finally {
    if (mine === seq) loading.value = false
  }
}
watch(() => [props.deviceId, props.ponId], load, { immediate: true })

const series = computed(() => {
  const rx = body.value?.rx || []
  if (!rx.length && props.currentRx === null) return []
  const avg = rx.map((p) => ({ x: p.t, y: p.rx_avg_dbm }))
  if (props.currentRx !== null && props.currentRx !== undefined) avg.push({ x: Date.now(), y: props.currentRx })
  if (avg.length < 2) return []
  return [
    { label: 'RX médio', data: avg },
    { label: 'Pior RX (hora)', data: rx.map((p) => ({ x: p.t, y: p.rx_worst_dbm })) },
  ]
})

const chartThresholds = computed(() => {
  const t = props.thresholds
  if (!t) return []
  return [
    t.warning !== null && t.warning !== undefined ? { value: t.warning, label: 'Atenção' } : null,
    t.critical !== null && t.critical !== undefined ? { value: t.critical, label: 'Crítico' } : null,
  ].filter(Boolean)
})

const traffic = computed(() => body.value?.traffic || null)
const trafficTitle = computed(() => {
  const t = traffic.value
  if (!t) return ''
  if (!t.available) return 'O Zabbix não tem itens de tráfego desta porta PON (nas VSOL só há as interfaces de uplink).'
  if (!t.at) return 'Itens de tráfego sem leitura recente.'
  const when = new Date(t.at).toLocaleString('pt-BR')
  return `${t.stale ? 'Leitura antiga — ' : ''}↓ entrada / ↑ saída da porta na OLT · ${when}`
})
</script>

<style scoped>
.trend {
  padding-top: 10px;
  margin-top: 10px;
  border-top: 1px solid rgb(var(--n-200));
}
.num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.traffic {
  font-size: 11px;
  color: rgb(var(--n-700));
  padding: 1px 6px;
  border-radius: 4px;
  background: rgb(var(--n-100));
  white-space: nowrap;
}
.traffic-stale {
  color: rgb(var(--n-500));
  font-style: italic;
}
</style>
