<template>
  <div class="ft" data-testid="fiber-trace">
    <p v-if="loading" class="ft-msg">A rastrear a luz…</p>
    <p v-else-if="error" class="ft-msg text-danger" role="alert">Erro no rastreamento: {{ error }}</p>
    <template v-else-if="trace">
      <ol class="ft-steps">
        <li v-for="(s, i) in trace.steps" :key="i" class="ft-step" :class="`ft-${s.type}`" :data-testid="`trace-step-${s.type}`">
          <template v-if="s.type === 'port'">
            <b>{{ s.device_name }}</b> → <span class="num">{{ s.port_name }}</span>
            <span v-if="s.site_name" class="ft-sub"> · {{ s.site_name }}</span>
          </template>
          <template v-else-if="s.type === 'cable'">
            <span class="core" :style="{ background: s.color_hex }" aria-hidden="true" />
            {{ s.cable_name }} · F{{ s.absolute_number }} ({{ s.color }})
            <span class="ft-sub">rumo a {{ s.toward }} · <span class="num">{{ fmtKm(s.km) }}</span></span>
            <span v-if="s.passes?.length" class="ft-sub"> · passa direto: {{ s.passes.join(', ') }}</span>
            <span v-if="s.broken" class="text-danger"> · rompido</span>
          </template>
          <template v-else-if="s.type === 'fusion'">
            Fusão na <b>{{ s.ceo_name }}</b>
            <span v-if="s.tray" class="ft-sub num"> · bandeja {{ s.tray }}{{ s.slot ? `, posição ${s.slot}` : '' }}</span>
          </template>
        </li>
      </ol>
      <p class="ft-end" :class="trace.end.reason === 'port' ? 'text-success' : 'text-warning'" data-testid="trace-end">
        {{ trace.end.reason === 'port' ? 'Chega a' : 'Fim' }}: {{ trace.end.label }}
      </p>
      <p class="ft-sub" data-testid="trace-total">
        <span class="num">{{ fmtKm(trace.total_km) }}</span> · {{ trace.fusions }} {{ trace.fusions === 1 ? 'fusão' : 'fusões' }}
        <template v-if="trace.loss_db_estimate !== null">
          · perda estimada <span class="num">{{ trace.loss_db_estimate.toLocaleString('pt-BR') }} dB</span>
          <span title="Atenuação do tipo de cabo × km + 0,1 dB por fusão; não é medição">(cálculo)</span>
        </template>
      </p>
    </template>
  </div>
</template>

<script setup>
/** Rastreamento da luz fim-a-fim a partir de uma ponta da fibra (EV-0136). */
import { ref, watch } from 'vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({
  strandId: { type: Number, required: true },
  start: { type: String, default: 'a' },
})
const api = useApi()
const trace = ref(null)
const loading = ref(false)
const error = ref('')
const fmtKm = (v) => `${Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} km`

watch(
  () => [props.strandId, props.start],
  async () => {
    loading.value = true
    error.value = ''
    try {
      trace.value = await api.get(`/api/v1/inventory/strands/${props.strandId}/trace/`, { from: props.start })
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
.ft-steps {
  margin: 0;
  padding: 0;
  list-style: none;
  border-left: 2px solid rgb(var(--n-200));
}
.ft-step {
  position: relative;
  margin: 0 0 6px;
  padding-left: 12px;
  color: rgb(var(--n-900));
}
.ft-step::before {
  content: '';
  position: absolute;
  left: -5px;
  top: 5px;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: rgb(var(--n-400));
}
.ft-port::before {
  background: rgb(var(--success));
}
.ft-fusion::before {
  background: rgb(var(--info));
  border-radius: 2px;
  transform: rotate(45deg);
}
.ft-sub {
  color: rgb(var(--n-500));
}
.ft-end {
  margin: 4px 0 2px;
  font-weight: 600;
}
.core {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 999px;
  border: 1px solid rgb(var(--n-400));
  vertical-align: -1px;
}
</style>
