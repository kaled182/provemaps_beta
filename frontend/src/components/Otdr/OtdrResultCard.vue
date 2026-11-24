<template>
  <div class="orc" data-testid="otdr-card">
    <header class="orc-head">
      <span class="orc-dot" aria-hidden="true" />
      <span class="font-semibold">Rompimento OTDR</span>
      <button type="button" class="orc-x" title="Fechar o cartão (o ponto fica no mapa)" aria-label="Fechar" @click="$emit('close')">×</button>
    </header>
    <dl class="orc-facts">
      <dt>Cabo</dt>
      <dd>{{ result.cable_name }}</dd>
      <dt>Sentido</dt>
      <dd data-testid="otdr-card-direction">{{ originName }} → {{ targetName }}</dd>
      <template v-if="result.mode === 'cross' && result.cross">
        <dt>Leituras A + B</dt>
        <dd class="num" data-testid="otdr-card-cross">
          {{ formatMeters(result.cross.reading_a_m) }} + {{ formatMeters(result.cross.reading_b_m) }}
          <span class="text-neutral-500">· folga real {{ String(result.cross.slack_real_pct).replace('.', ',') }}%</span>
        </dd>
      </template>
      <template v-else>
        <dt>Leitura OTDR</dt>
        <dd class="num">{{ formatMeters(result.otdr_m) }}</dd>
      </template>
      <dt>No traçado</dt>
      <dd class="num" data-testid="otdr-card-map">
        {{ formatMeters(result.map_distance_m) }}
        <span v-if="result.mode !== 'cross'" class="text-neutral-500">(folga {{ slackText }}%)</span>
        <span v-if="offset" class="orc-offset" data-testid="otdr-card-offset">ajuste {{ offset > 0 ? '+' : '' }}{{ formatMeters(offset) }}</span>
      </dd>
      <dt>GPS</dt>
      <dd class="num" data-testid="otdr-card-coords">{{ formatCoords(result.point) }} <span class="text-neutral-500">±{{ Math.round(result.tolerance_m) }} m</span></dd>
      <dt>Até {{ originName }}</dt>
      <dd class="num">{{ formatMeters(result.origin.distance_m) }}</dd>
      <dt>Até {{ targetName }}</dt>
      <dd class="num">{{ formatMeters(result.target.distance_m) }}</dd>
    </dl>
    <p v-for="w in result.warnings || []" :key="w" class="orc-warn" role="alert" data-testid="otdr-card-warning">{{ w }}</p>

    <!-- EV-0130: ajuste fino em campo, ao longo do traçado -->
    <div class="orc-adjust" data-testid="otdr-adjust">
      <div class="orc-steps">
        <button
          v-for="step in ADJUST_STEPS"
          :key="step"
          type="button"
          class="orc-step"
          :disabled="busy"
          :data-testid="`otdr-step-${step}`"
          @click="$emit('adjust', offset + step)"
        >
          {{ step > 0 ? '+' : '−' }}{{ Math.abs(step) }} m
        </button>
      </div>
      <input
        v-model.number="slider"
        type="range"
        class="orc-slider"
        min="0"
        :max="Math.round(result.path_length_m)"
        step="10"
        :disabled="busy"
        aria-label="Posição ao longo do traçado"
        data-testid="otdr-slider"
        @change="$emit('adjust', slider - result.base_map_distance_m)"
      />
      <p class="orc-hint">{{ alert ? 'Num ponto fixado, o ajuste vale para toda a equipa.' : 'Arraste ou use os passos para acertar o ponto no terreno.' }}</p>
    </div>

    <!-- EV-0130: caixas/reservas cadastradas antes e depois do ponto -->
    <div class="orc-refs" data-testid="otdr-refs">
      <template v-if="refs.registered">
        <p v-for="side in ['before', 'after']" :key="side">
          <span class="text-neutral-500">{{ side === 'before' ? 'Anterior: ' : 'Posterior: ' }}</span>
          <template v-if="refs[side]">
            {{ refs[side].type_label }}{{ refs[side].name ? ` ${refs[side].name}` : '' }} ·
            <span class="num">{{ formatMeters(refs[side].distance_m) }}</span>
          </template>
          <template v-else>— (nenhuma neste lado)</template>
        </p>
      </template>
      <p v-else class="text-neutral-500">Nenhuma caixa ou reserva cadastrada neste cabo.</p>
    </div>

    <div class="orc-actions">
      <a class="orc-btn" :href="googleMapsUrl(result.point)" target="_blank" rel="noopener noreferrer" data-testid="otdr-gmaps">Google Maps</a>
      <a class="orc-btn" :href="wazeUrl(result.point)" target="_blank" rel="noopener noreferrer" data-testid="otdr-waze">Waze</a>
      <a class="orc-btn" :href="streetViewUrl(result.point)" target="_blank" rel="noopener noreferrer" data-testid="otdr-streetview">Street View</a>
      <button type="button" class="orc-btn" data-testid="otdr-whatsapp" @click="copyWhatsapp">
        {{ copied ? 'Copiado!' : 'Copiar para WhatsApp' }}
      </button>
      <!-- EV-0128: fixar para toda a equipa (servidor) ou limpar -->
      <button v-if="!alert" type="button" class="orc-btn orc-btn-pin" :disabled="busy" data-testid="otdr-pin-alert" @click="$emit('pin')">
        {{ busy ? 'A fixar…' : 'Fixar alerta no mapa' }}
      </button>
      <button v-if="!alert" type="button" class="orc-btn orc-btn-clear" :disabled="busy" data-testid="otdr-clear" @click="$emit('clear')">Limpar</button>
    </div>

    <!-- EV-0132: estado do atendimento de um ponto fixado (vale para toda a equipa) -->
    <div v-if="alert" class="orc-status" data-testid="otdr-status">
      <span class="orc-status-now">Atendimento: <b data-testid="otdr-status-label">{{ alert.status_label || 'Registado' }}</b></span>
      <div class="orc-status-btns">
        <button
          v-for="s in STATUS_ACTIONS"
          :key="s.value"
          type="button"
          class="orc-btn"
          :class="[{ 'orc-status-on': alert.status === s.value }, s.cls]"
          :disabled="busy || alert.status === s.value"
          :data-testid="`otdr-status-${s.value}`"
          @click="$emit('status', s.value)"
        >
          {{ s.label }}
        </button>
      </div>
    </div>
    <p v-if="alert" class="orc-pinned" data-testid="otdr-card-pinned">
      Fixado para a equipa{{ alert.created_by ? ` por ${alert.created_by}` : '' }} · {{ pinnedAt }}{{ alert.note ? ` · ${alert.note}` : '' }}
    </p>
    <p v-if="error" class="mt-1 text-xs text-danger" role="alert" data-testid="otdr-card-error">{{ error }}</p>
    <p v-if="copyError" class="mt-1 text-xs text-danger" role="alert">Não foi possível copiar: {{ copyError }}</p>
  </div>
</template>

<script setup>
/** Cartão do ponto OTDR no mapa (EV-0127): dados para o campo e navegação externa. */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { copyText } from '@/components/Gpon/ponDiagnosis'
import { ADJUST_STEPS, formatCoords, formatMeters, googleMapsUrl, streetViewUrl, wazeUrl, whatsappText } from '@/utils/otdr'

const props = defineProps({
  result: { type: Object, required: true },
  /** EV-0128: alerta fixado (servidor) a que este ponto pertence; null = só neste ecrã */
  alert: { type: Object, default: null },
  busy: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
defineEmits(['close', 'clear', 'pin', 'adjust', 'status'])

const STATUS_ACTIONS = [
  { value: 'en_route', label: 'Em deslocamento', cls: '' },
  { value: 'splicing', label: 'Em fusão', cls: '' },
  { value: 'done', label: 'Concluído / Remover pino', cls: 'orc-btn-done' },
]

const offset = computed(() => Number(props.result.offset_m) || 0)
const refs = computed(() => props.result.references || { registered: 0, before: null, after: null })
/** slider = posição absoluta no traçado; segue o resultado (ajustes vindos do servidor) */
const slider = ref(Math.round(props.result.map_distance_m))
watch(
  () => props.result.map_distance_m,
  (v) => {
    slider.value = Math.round(v)
  },
)

const pinnedAt = computed(() =>
  props.alert?.created_at
    ? new Date(props.alert.created_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : '',
)

const originName = computed(() => props.result.origin?.name || (props.result.direction === 'ab' ? 'Site A' : 'Site B'))
const targetName = computed(() => props.result.target?.name || (props.result.direction === 'ab' ? 'Site B' : 'Site A'))
const slackText = computed(() => String(props.result.slack_pct).replace('.', ','))

const copied = ref(false)
const copyError = ref('')
let timer = null
async function copyWhatsapp() {
  copyError.value = ''
  try {
    await copyText(whatsappText(props.result))
    copied.value = true
    clearTimeout(timer)
    timer = setTimeout(() => (copied.value = false), 1500)
  } catch (e) {
    copyError.value = e?.message || 'erro desconhecido'
  }
}
onBeforeUnmount(() => clearTimeout(timer))
</script>

<style scoped>
.orc {
  width: 300px;
  padding: 10px 12px;
  font-size: 12px;
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.orc-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 13px;
  color: rgb(var(--danger));
}
.orc-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: rgb(var(--danger));
}
.orc-x {
  margin-left: auto;
  font-size: 16px;
  line-height: 1;
  color: rgb(var(--n-500));
}
.orc-facts {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 3px 10px;
  margin: 0;
}
.orc-facts dt {
  color: rgb(var(--n-500));
  white-space: nowrap;
}
.orc-facts dd {
  margin: 0;
  color: rgb(var(--n-900));
  overflow-wrap: anywhere;
}
.orc-status {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgb(var(--n-200));
}
.orc-status-now {
  font-size: 11px;
  color: rgb(var(--n-600));
}
.orc-status-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}
.orc-status-on {
  border-color: rgb(var(--primary-500));
  color: rgb(var(--primary-700));
  background: rgb(var(--primary-500) / 0.1);
}
.orc-btn-done:hover:not(:disabled) {
  border-color: rgb(var(--success));
  color: rgb(var(--success));
}
.orc-warn {
  margin: 6px 0 0;
  padding: 4px 6px;
  border-radius: 6px;
  font-size: 11px;
  color: rgb(var(--warning));
  background: rgb(var(--warning) / 0.1);
}
.orc-offset {
  margin-left: 4px;
  padding: 0 5px;
  border-radius: 4px;
  font-size: 11px;
  background: rgb(var(--warning) / 0.14);
  color: rgb(var(--warning));
}
.orc-adjust {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgb(var(--n-200));
}
.orc-steps {
  display: flex;
  gap: 4px;
}
.orc-step {
  flex: 1;
  height: 26px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 11px;
  color: rgb(var(--n-700));
  background: rgb(var(--surface));
}
.orc-step:hover:not(:disabled) {
  border-color: rgb(var(--primary-500));
  color: rgb(var(--primary-600));
}
.orc-step:disabled {
  opacity: 0.5;
}
.orc-slider {
  width: 100%;
  margin-top: 6px;
  accent-color: rgb(var(--danger));
}
.orc-hint {
  margin: 2px 0 0;
  font-size: 10px;
  color: rgb(var(--n-500));
}
.orc-refs {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px solid rgb(var(--n-200));
  font-size: 11px;
  color: rgb(var(--n-800));
}
.orc-refs p {
  margin: 1px 0;
}
.orc-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.orc-btn {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 9px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  font-size: 12px;
  color: rgb(var(--n-700));
  background: rgb(var(--surface));
  text-decoration: none;
}
.orc-btn:hover {
  border-color: rgb(var(--primary-500));
  color: rgb(var(--primary-600));
}
.orc-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.orc-btn-pin {
  border-color: rgb(var(--danger) / 0.5);
  color: rgb(var(--danger));
}
.orc-pinned {
  margin: 8px 0 0;
  font-size: 11px;
  color: rgb(var(--n-600));
}
.orc-btn-clear:hover {
  border-color: rgb(var(--danger));
  color: rgb(var(--danger));
}
</style>
