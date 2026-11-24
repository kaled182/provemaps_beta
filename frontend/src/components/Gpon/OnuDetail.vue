<template>
  <div class="od" :data-testid="`onu-detail-${onu.id}`">
    <!-- Ficha técnica e diagnóstico -->
    <dl class="od-facts">
      <div><dt>Serial / MAC</dt><dd class="num">{{ [onu.serial, onu.mac].filter(Boolean).join(' · ') || '—' }}</dd></div>
      <div><dt>OLT · PON : ID</dt><dd class="num">{{ onu.olt_name }} · {{ onu.pon_id }} : {{ onu.onu_index ?? '—' }}</dd></div>
      <div><dt>Distância</dt><dd class="num">{{ onu.distance_m === null || onu.distance_m === undefined ? '—' : formatDistance(onu.distance_m) }}</dd></div>
      <div>
        <dt>{{ onu.status === 'online' ? 'Online' : onu.status === 'offline' ? 'Em queda' : 'Estado' }}</dt>
        <dd class="num" data-testid="onu-detail-since">{{ sinceText }}</dd>
      </div>
      <div>
        <dt>Diagnóstico</dt>
        <dd :class="diagnosis.cls" data-testid="onu-detail-diagnosis">{{ diagnosis.text }}</dd>
      </div>
      <div><dt>Cliente</dt><dd>{{ onu.cliente_nome || '—' }}</dd></div>
      <div><dt>Login</dt><dd class="num">{{ onu.login_radius || '—' }}</dd></div>
      <div><dt>CTO</dt><dd class="num">{{ onu.caixa_cto || '—' }}</dd></div>
    </dl>

    <!-- Gráfico do RX que o Zabbix guarda para esta ONU -->
    <div class="od-chart">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-xs font-semibold text-neutral-700">{{ history?.label || 'RX' }}</span>
        <div class="pills ml-auto" role="group" aria-label="Período">
          <button
            v-for="h in PERIODS"
            :key="h.hours"
            type="button"
            class="pill"
            :class="{ 'pill-on': hours === h.hours }"
            :aria-pressed="hours === h.hours"
            :data-testid="`onu-detail-hours-${h.hours}`"
            @click="hours = h.hours"
          >
            {{ h.label }}
          </button>
        </div>
      </div>
      <p v-if="!onu.has_history" class="od-msg" data-testid="onu-detail-no-history">Sem item de RX no Zabbix para esta ONU — sem histórico.</p>
      <p v-else-if="loading && !history" class="od-msg">Carregando histórico…</p>
      <p v-else-if="error" class="od-msg text-danger" role="alert">Erro ao carregar o histórico: {{ error }}</p>
      <p v-else-if="history && !history.zabbix_ok" class="od-msg text-warning" role="alert" data-testid="onu-detail-zabbix-down">
        Zabbix indisponível<span v-if="history.zabbix_error">: {{ history.zabbix_error }}</span>
      </p>
      <p v-else-if="history && !history.points.length" class="od-msg" data-testid="onu-detail-empty">Sem leituras no período.</p>
      <TimeSeriesChart
        v-else-if="history"
        :series="series"
        :thresholds="chartThresholds"
        :unit="history.unit || 'dBm'"
        :height="150"
        compact
      />
    </div>
  </div>
</template>

<script setup>
/**
 * Ficha de uma ONU expandida na própria linha da lista (EV-0119), em vez do modal de
 * histórico: dados da coleta, diagnóstico (LOS × Dying Gasp × sinal degradado) e o
 * gráfico do RX que o Zabbix tem (ZTE: RX na OLT; VSOL: RX na ONU) — 24 h ou 7 d.
 */
import { computed, ref, watch } from 'vue'
import { useApi } from '@/composables/useApi'
import TimeSeriesChart from '@/components/charts/TimeSeriesChart.vue'
import { formatDistance, formatSince } from '@/utils/ptBrFormat'

const PERIODS = [
  { hours: 24, label: '24 h' },
  { hours: 168, label: '7 d' },
]

const props = defineProps({
  onu: { type: Object, required: true },
  thresholds: { type: Object, default: null },
})

const api = useApi()
const hours = ref(24)
const history = ref(null)
const loading = ref(false)
const error = ref('')
let seq = 0

async function load() {
  if (!props.onu.has_history) return
  const mine = ++seq
  loading.value = true
  error.value = ''
  try {
    const res = await api.get(`/api/v1/monitoring/gpon/onus/${props.onu.id}/history/`, { hours: hours.value })
    if (mine === seq) history.value = res
  } catch (e) {
    if (mine === seq) error.value = e?.message || 'erro desconhecido'
  } finally {
    if (mine === seq) loading.value = false
  }
}
watch(() => props.onu.id, () => {
  history.value = null
  load()
}, { immediate: true })
watch(hours, load)

const series = computed(() => [{ label: history.value?.label || 'RX', data: history.value?.points || [] }])
const chartThresholds = computed(() => {
  const t = props.thresholds
  if (!t) return []
  return [
    { value: t.warning, label: 'Atenção' },
    { value: t.critical, label: 'Crítico' },
  ].filter((x) => typeof x.value === 'number')
})

const sinceText = computed(() => {
  const o = props.onu
  if (!o.status_since) return '—'
  const rel = formatSince(o.status_since, Boolean(o.status_since_is_first_seen))
  const when = new Date(o.status_since).toLocaleString('pt-BR')
  return o.status_since_is_first_seen ? `${rel} (registo desde ${when})` : `${rel} (desde ${when})`
})

const diagnosis = computed(() => {
  const o = props.onu
  if (o.status === 'offline' && o.reason === 'los') return { text: 'LOS — perda de sinal na fibra (drop, conector ou CTO)', cls: 'text-danger' }
  if (o.status === 'offline' && o.reason === 'dying_gasp') return { text: 'Dying Gasp — a ONU perdeu energia no cliente', cls: 'text-info' }
  if (o.status === 'offline') return { text: `Offline${o.reason_label ? ` — ${o.reason_label}` : ''}`, cls: 'text-neutral-700' }
  if (o.status === 'online' && o.signal === 'critical') return { text: 'Sinal degradado — abaixo do limiar crítico', cls: 'text-danger' }
  if (o.status === 'online' && o.signal === 'warning') return { text: 'Sinal atenuado — abaixo do limiar de atenção', cls: 'text-warning' }
  if (o.status === 'online') return { text: 'Online com sinal normal', cls: 'text-success' }
  return { text: 'Sem coleta recente', cls: 'text-neutral-500' }
})
</script>

<style scoped>
.od {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
  padding: 10px 12px 12px;
  background: rgb(var(--n-50));
  border-top: 1px dashed rgb(var(--n-200));
}
@media (min-width: 1024px) {
  .od {
    grid-template-columns: minmax(0, 2fr) minmax(0, 3fr);
  }
}
.od-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 12px;
  margin: 0;
}
.od-facts dt {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: rgb(var(--n-500));
}
.od-facts dd {
  margin: 0;
  font-size: 12px;
  color: rgb(var(--n-900));
  overflow-wrap: anywhere;
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.od-msg {
  font-size: 12px;
  color: rgb(var(--n-500));
}
.pills {
  display: inline-flex;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  overflow: hidden;
}
.pill {
  padding: 2px 8px;
  font-size: 11px;
  color: rgb(var(--n-600));
  background: rgb(var(--surface));
  border-left: 1px solid rgb(var(--n-200));
}
.pill:first-child {
  border-left: 0;
}
.pill-on {
  color: rgb(var(--primary-600));
  background: rgb(var(--primary-500) / 0.12);
  font-weight: 600;
}
</style>
