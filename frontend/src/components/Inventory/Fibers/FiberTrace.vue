<template>
  <div class="ft" data-testid="fiber-trace">
    <p v-if="loading" class="ft-msg">A rastrear a luz…</p>
    <p v-else-if="error" class="ft-msg text-danger" role="alert">Erro no rastreamento: {{ error }}</p>
    <template v-else-if="trace">
      <p v-if="trace.tx" class="ft-tx" data-testid="trace-tx">
        Partida <span class="num">{{ fmtDbm(trace.tx.dbm) }}</span>
        <span class="ft-sub"> — {{ trace.tx.source === 'zabbix' ? `TX coletado do Zabbix (${trace.tx.port_name})` : 'TX padrão da configuração (sem coleta nesta porta)' }}</span>
      </p>
      <p v-else-if="!trace.source?.found" class="ft-tx text-warning" data-testid="trace-nosource">
        Sem fonte de luz a montante ({{ trace.source?.label || 'nenhuma porta ligada' }}) — só distâncias, sem dBm.
      </p>
      <TraceNode :node="trace.tree" />
      <p class="ft-end" :class="leaf.end.reason === 'port' ? 'text-success' : 'text-warning'" data-testid="trace-end">
        {{ leaf.end.reason === 'port' ? 'Chega a' : 'Fim' }}: {{ leaf.end.label }}
      </p>
      <p class="ft-sub" data-testid="trace-total">
        <span class="num">{{ fmtKm(leaf.km) }}</span> · {{ fusions }} {{ fusions === 1 ? 'fusão' : 'fusões' }}
        <template v-if="splitters"> · {{ splitters }} {{ splitters === 1 ? 'splitter' : 'splitters' }}</template>
        · perda estimada <span class="num">{{ db(leaf.loss_db) }}</span>
        <template v-if="leaf.dbm !== null && leaf.dbm !== undefined">
          · chega com ≈ <span class="num" data-testid="trace-rx">{{ fmtDbm(leaf.dbm) }}</span>
        </template>
      </p>
      <p v-if="trace.truncated" class="ft-note text-warning">Árvore grande: alguns ramos não foram percorridos.</p>
      <p class="ft-note" data-testid="trace-note">
        Cálculo, não medição: {{ fmtDec(trace.budget?.fiber_db_km) }} dB/km (ou o do tipo de cabo),
        {{ fmtDec(trace.budget?.fusion_db) }} dB por fusão e a perda de cada splitter — Configuração › Orçamento óptico.
      </p>
      <button v-if="traceMapAvailable" type="button" class="ft-map" data-testid="trace-show-map" @click="showOnMap">
        Ver no mapa
      </button>
    </template>
  </div>
</template>

<script setup>
/**
 * Rastreamento da luz (EV-0136) em árvore (EV-0143): da fonte (OLT/switch, procurada a montante)
 * até aos destinos, com os ramos dos splitters; o ramo da fibra pedida vem aberto e destacado.
 * No Projeto de Rede, «Ver no mapa» desenha o caminho com km e dBm (DesignLayer → TraceOverlay).
 */
import { computed, ref, watch } from 'vue'
import TraceNode from './TraceNode.vue'
import { useApi } from '@/composables/useApi'
import { emitDesign, traceMapAvailable } from '@/features/networkDesign/modules/designMode.js'
import { fmtDbm, fmtKm, focusPath } from '@/utils/traceTree'

const props = defineProps({
  strandId: { type: Number, required: true },
  start: { type: String, default: 'a' },
})
const api = useApi()
const trace = ref(null)
const loading = ref(false)
const error = ref('')
const fmtDec = (v) => Number(v ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const db = (v) => `${fmtDec(v)} dB`

const path = computed(() => (trace.value ? focusPath(trace.value.tree) : []))
const leaf = computed(() => path.value[path.value.length - 1])
const fusions = computed(() => path.value.flatMap((n) => n.steps).filter((s) => s.type === 'fusion').length)
const splitters = computed(() => path.value.filter((n) => n.splitter).length)

function showOnMap() {
  emitDesign('trace-show', trace.value)
}

watch(
  () => [props.strandId, props.start],
  async () => {
    loading.value = true
    error.value = ''
    try {
      trace.value = await api.get(`/api/v1/inventory/strands/${props.strandId}/trace/tree/`, { from: props.start })
    } catch (e) {
      error.value = e?.message || 'erro desconhecido'
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.ft {
  margin-top: 6px;
  font-size: 12px;
}
.ft-msg {
  color: rgb(var(--n-500));
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.ft-sub {
  color: rgb(var(--n-500));
}
.ft-tx {
  margin: 0 0 6px;
  color: rgb(var(--n-900));
}
.ft-note {
  margin: 2px 0 0;
  font-size: 11px;
  color: rgb(var(--n-500));
}
.ft-map {
  margin-top: 6px;
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid rgb(var(--primary-500));
  background: rgb(var(--primary-500) / 0.1);
  color: rgb(var(--primary-700));
  font-weight: 600;
  cursor: pointer;
}
.ft-end {
  margin: 4px 0 2px;
  font-weight: 600;
}
</style>
