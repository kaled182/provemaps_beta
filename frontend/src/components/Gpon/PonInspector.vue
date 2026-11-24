<template>
  <aside class="insp rounded-md border border-neutral-200 bg-surface text-sm" data-testid="pon-inspector" aria-live="polite">
    <!-- porta selecionada -->
    <template v-if="portId !== null">
      <header class="flex items-center gap-2 flex-wrap">
        <PhPlug :size="15" class="text-neutral-500" />
        <span class="font-semibold num" data-testid="insp-title">{{ pon?.label || `PON ${portId}` }}</span>
        <span class="state" :class="`state-${state.tone}`" data-testid="insp-state">{{ state.label }}</span>
        <span v-if="preview" class="hint" data-testid="insp-preview" title="Porta mais crítica desta OLT — clique numa porta para filtrar a tabela">mais crítica</span>
        <button v-else type="button" class="clear" data-testid="insp-clear" @click="$emit('clear')">Todas as portas ({{ portsCount }})</button>
      </header>

      <div class="mt-3">
        <div class="flex justify-between text-xs text-neutral-600 num">
          <span>Ocupação</span>
          <span data-testid="insp-occupancy">{{ occupancyText }}</span>
        </div>
        <div class="bar mt-1" aria-hidden="true">
          <span class="bar-fill" :class="highOccupancy ? 'bg-warning' : 'bg-primary-500'" :style="{ width: `${occWidth}%` }"></span>
        </div>
      </div>

      <dl class="facts mt-3 num">
        <dt>ONUs online</dt>
        <dd data-testid="insp-online">{{ pon ? `${formatInt(pon.onus_online)} / ${formatInt(pon.onus_provisioned)}` : '—' }}</dd>
        <dt>RX médio</dt>
        <dd data-testid="insp-rx-avg">{{ formatDbm(pon?.rx_avg_dbm) }}</dd>
        <dt>Pior RX</dt>
        <dd data-testid="insp-rx-worst" :class="worstClass">{{ formatDbm(pon?.rx_worst_dbm) }}</dd>
        <dt>LOS</dt>
        <dd data-testid="insp-los" :class="{ 'text-danger': pon?.los > 0 }">{{ pon ? formatInt(pon.los) : '—' }}</dd>
        <dt>Em atenção</dt>
        <dd data-testid="insp-attention" :class="{ 'text-warning': attention > 0 }">{{ pon ? formatInt(attention) : '—' }}</dd>
        <dt>Temperatura SFP</dt>
        <dd data-testid="insp-sfp-temp" title="não coletado">—</dd>
      </dl>

      <!-- EV-0109: tendência 24 h do RX médio e tráfego atual da porta -->
      <PonTrend
        v-if="pon && olt?.device_id"
        :device-id="olt.device_id"
        :pon-id="portId"
        :current-rx="pon.rx_avg_dbm ?? null"
        :thresholds="thresholds"
      />

      <!-- EV-0107: histograma de saúde óptica — clicar filtra a tabela por essa faixa -->
      <div v-if="pon" class="mt-3" data-testid="insp-bands">
        <p class="text-xs font-semibold text-neutral-700">Saúde óptica das ONUs</p>
        <button
          v-for="b in bands"
          :key="b.band"
          type="button"
          class="band"
          :class="[`band-${b.band}`, { 'band-on': signalBand === b.band }]"
          :disabled="!b.count"
          :aria-pressed="signalBand === b.band"
          :title="b.count ? `Mostrar só as ONUs ${b.label.toLowerCase()} na tabela (clique de novo para todas)` : 'Nenhuma ONU nesta faixa'"
          :data-testid="`insp-band-${b.band}`"
          @click="$emit('band', b.band)"
        >
          <span class="band-label">{{ b.label }}</span>
          <span class="band-track" aria-hidden="true"><span class="band-fill" :style="{ width: `${b.pct}%` }"></span></span>
          <span class="band-count num">{{ formatInt(b.count) }}</span>
        </button>
      </div>

      <div v-if="diagnostics.length" class="diag mt-3" data-testid="insp-diagnostics">
        <p class="flex items-center gap-1.5 text-xs font-semibold text-neutral-700">
          <PhStethoscope :size="14" /> Diagnóstico
        </p>
        <ul class="mt-1 flex flex-col gap-1.5">
          <li v-for="d in diagnostics" :key="d" class="text-xs text-neutral-700">{{ d }}</li>
        </ul>
      </div>

      <!-- EV-0107: ações rápidas da porta -->
      <div class="actions mt-3" data-testid="insp-actions">
        <button type="button" class="act" data-testid="insp-copy-os" @click="copyOs">
          <component :is="copied ? PhCheck : PhClipboardText" :size="14" />
          {{ copied ? 'Copiado!' : 'Copiar resumo OS' }}
        </button>
        <button
          type="button"
          class="act"
          :disabled="!olt?.site_id"
          :title="olt?.site_id ? `Abrir o mapa backbone com ${olt.site_name || 'o POP da OLT'} em destaque` : 'OLT sem POP no inventário'"
          data-testid="insp-map"
          @click="openMap"
        >
          <PhMapPin :size="14" /> Ver no mapa
        </button>
      </div>
      <p v-if="copyError" class="mt-1 text-xs text-danger" role="alert">Não foi possível copiar: {{ copyError }}</p>
    </template>

    <!-- placa selecionada -->
    <template v-else-if="card">
      <header class="flex items-center gap-2 flex-wrap">
        <PhCircuitry :size="15" class="text-neutral-500" />
        <span class="font-semibold num" data-testid="insp-title">Slot {{ card.slot }} · {{ card.card_type }}</span>
        <span class="state" :class="card.in_service === false ? 'state-danger' : card.in_service ? 'state-success' : 'state-neutral'">
          {{ card.in_service === false ? 'Fora de serviço' : card.in_service ? 'Em serviço' : 'Estado desconhecido' }}
        </span>
        <button type="button" class="clear" data-testid="insp-clear" @click="$emit('clear')">Todas as portas ({{ portsCount }})</button>
      </header>
      <dl class="facts mt-3 num" data-testid="insp-slot">
        <dt>PONs com ONUs</dt>
        <dd>{{ formatInt(slotSummary.pons) }}</dd>
        <dt>ONUs</dt>
        <dd data-testid="insp-slot-onus">{{ formatInt(slotSummary.online) }} / {{ formatInt(slotSummary.provisioned) }}</dd>
        <dt>LOS</dt>
        <dd data-testid="insp-slot-los" :class="{ 'text-danger': slotSummary.los > 0 }">{{ formatInt(slotSummary.los) }}</dd>
        <dt>Em atenção</dt>
        <dd data-testid="insp-slot-attention" :class="{ 'text-warning': slotSummary.attention > 0 }">{{ formatInt(slotSummary.attention) }}</dd>
        <dt>CPU</dt>
        <dd>{{ formatPercent(card.cpu_pct) }}</dd>
        <dt>Memória</dt>
        <dd>{{ formatPercent(card.mem_pct) }}</dd>
      </dl>
    </template>

    <p v-else class="h-full flex items-center justify-center gap-2 text-center text-xs text-neutral-500" data-testid="insp-empty">
      <PhCursorClick :size="16" /> Clique numa porta PON para inspecionar
    </p>
  </aside>
</template>

<script setup>
/**
 * Inspetor de porta/placa do chassi (EV-0101). Só factos do payload: o que o Zabbix
 * não dá (temperatura do SFP) fica «—» com «não coletado» (§2.1).
 */
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  PhCheck,
  PhCircuitry,
  PhClipboardText,
  PhCursorClick,
  PhMapPin,
  PhPlug,
  PhStethoscope,
} from '@phosphor-icons/vue'
import { OCCUPANCY_LIMIT } from '@/composables/useGponOverview'
import { formatDbm, formatInt, formatPercent } from '@/utils/ptBrFormat'
import { ponState } from './chassisLed'
import { copyText, ponDiagnostics, ponOsSummary, ponSignalBands } from './ponDiagnosis'
import PonTrend from './PonTrend.vue'

defineEmits(['clear', 'band'])
const props = defineProps({
  /** pon_id da porta selecionada nesta OLT (ou null). */
  portId: { type: String, default: null },
  /** PON do payload que casa com a porta (null = porta sem ONUs). */
  pon: { type: Object, default: null },
  /** Estado da porta no chassi (up | down | unknown), se houver. */
  portStatus: { type: String, default: null },
  /** Placa selecionada (entrada de chassis.slots) ou null. */
  card: { type: Object, default: null },
  /** PONs da placa selecionada. */
  cardPons: { type: Array, default: () => [] },
  thresholds: { type: Object, default: null },
  /** EV-0106: a porta mostrada é a pré-visualização da mais crítica (não está selecionada). */
  preview: { type: Boolean, default: false },
  /** Nº de PONs da OLT, para o botão «Todas as portas (N)». */
  portsCount: { type: Number, default: 0 },
  /** EV-0107: ONUs desta porta (todas, sem os filtros da tabela). */
  onus: { type: Array, default: () => [] },
  /** EV-0107: OLT (nome, POP, site_id) para o resumo da OS e o «Ver no mapa». */
  olt: { type: Object, default: null },
  /** EV-0107: faixa do histograma ativa na tabela (normal|warning|critical) ou null. */
  signalBand: { type: String, default: null },
})

const attention = computed(() => (props.pon?.signal_warning ?? 0) + (props.pon?.signal_critical ?? 0))
const state = computed(() => ponState(props.pon, props.portStatus))
const diagnostics = computed(() =>
  ponDiagnostics(props.pon, props.thresholds, props.portStatus, props.onus, Date.now()),
)
const bands = computed(() => ponSignalBands(props.onus, props.thresholds))

const router = useRouter()
const copied = ref(false)
const copyError = ref('')
let copiedTimer = null

async function copyOs() {
  copyError.value = ''
  const text = ponOsSummary({
    olt: props.olt,
    pon: props.pon,
    portId: props.portId,
    stateLabel: state.value.label,
    onus: props.onus,
    diagnostics: diagnostics.value,
  })
  try {
    await copyText(text)
    copied.value = true
    clearTimeout(copiedTimer)
    copiedTimer = setTimeout(() => {
      copied.value = false
    }, 1500)
  } catch (e) {
    copyError.value = e?.message || 'área de transferência indisponível'
  }
}
onBeforeUnmount(() => clearTimeout(copiedTimer))

function openMap() {
  if (!props.olt?.site_id) return
  router.push({ path: '/monitoring/backbone/map/default', query: { site: String(props.olt.site_id) } })
}
const highOccupancy = computed(() => (props.pon?.occupancy_pct ?? 0) > OCCUPANCY_LIMIT)
const occWidth = computed(() => Math.min(Math.max(props.pon?.occupancy_pct ?? 0, 0), 100))
const occupancyText = computed(() => {
  if (!props.pon) return '—'
  const { onus_provisioned: n, capacity: cap, occupancy_pct: pct } = props.pon
  return `${formatInt(n)} / ${formatInt(cap)} ONUs · ${formatPercent(pct, 1)}`
})
const worstClass = computed(() => {
  const v = props.pon?.rx_worst_dbm
  const t = props.thresholds
  if (v === null || v === undefined || !t) return null
  if (t.critical !== null && t.critical !== undefined && v < t.critical) return 'text-danger'
  if (t.warning !== null && t.warning !== undefined && v < t.warning) return 'text-warning'
  return null
})

const slotSummary = computed(() => {
  const sum = (k) => props.cardPons.reduce((acc, p) => acc + (p[k] ?? 0), 0)
  return {
    pons: props.cardPons.filter((p) => p.onus_provisioned > 0).length,
    provisioned: sum('onus_provisioned'),
    online: sum('onus_online'),
    los: sum('los'),
    attention: sum('signal_warning') + sum('signal_critical'),
  }
})
</script>

<style scoped>
.insp {
  padding: 12px;
  min-height: 100%;
}
.num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.state {
  margin-left: auto;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid rgb(var(--n-300));
  color: rgb(var(--n-600));
}
.state-success {
  color: rgb(var(--success));
  border-color: rgb(var(--success) / 0.4);
  background: rgb(var(--success) / 0.1);
}
.state-warning {
  color: rgb(var(--warning));
  border-color: rgb(var(--warning) / 0.45);
  background: rgb(var(--warning) / 0.1);
}
.state-danger {
  color: rgb(var(--danger));
  border-color: rgb(var(--danger) / 0.45);
  background: rgb(var(--danger) / 0.1);
}
.bar {
  height: 6px;
  border-radius: 999px;
  background: rgb(var(--n-200));
  overflow: hidden;
}
.bar-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
}
.facts {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 12px;
  font-size: 12px;
  color: rgb(var(--n-800));
}
.facts dt {
  color: rgb(var(--n-500));
}
.facts dd {
  text-align: right;
}
.diag {
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid rgb(var(--warning) / 0.35);
  background: rgb(var(--warning) / 0.07);
}
.band {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) 2.5rem;
  align-items: center;
  gap: 8px;
  width: 100%;
  margin-top: 4px;
  padding: 3px 6px;
  border-radius: 6px;
  border: 1px solid transparent;
  font-size: 11px;
  text-align: left;
  color: rgb(var(--n-700));
}
.band:hover:not(:disabled) {
  background: rgb(var(--n-100));
}
.band:disabled {
  opacity: 0.55;
  cursor: default;
}
.band-on {
  border-color: rgb(var(--primary-500) / 0.6);
  background: rgb(var(--primary-500) / 0.08);
}
.band-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.band-track {
  height: 6px;
  border-radius: 999px;
  background: rgb(var(--n-200));
  overflow: hidden;
}
.band-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
}
.band-normal .band-fill { background: rgb(var(--success)); }
.band-warning .band-fill { background: rgb(var(--warning)); }
.band-critical .band-fill { background: rgb(var(--danger)); }
.band-count {
  text-align: right;
  font-weight: 600;
  color: rgb(var(--n-900));
}
.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  padding-top: 10px;
  border-top: 1px solid rgb(var(--n-200));
}
.act {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  border: 1px solid rgb(var(--n-300));
  font-size: 12px;
  font-weight: 500;
  color: rgb(var(--n-800));
}
.act:hover:not(:disabled) {
  background: rgb(var(--n-100));
}
.act:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.hint {
  margin-left: auto;
  padding: 0 6px;
  border-radius: 4px;
  font-size: 11px;
  color: rgb(var(--n-600));
  border: 1px dashed rgb(var(--n-300));
}
.clear {
  margin-left: auto;
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: rgb(var(--primary-700));
  border: 1px solid rgb(var(--primary-500) / 0.4);
  background: rgb(var(--primary-500) / 0.08);
}
.clear:hover {
  background: rgb(var(--primary-500) / 0.16);
}
</style>
