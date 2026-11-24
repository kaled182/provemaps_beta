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
      <dt>Leitura OTDR</dt>
      <dd class="num">{{ formatMeters(result.otdr_m) }}</dd>
      <dt>No traçado</dt>
      <dd class="num" data-testid="otdr-card-map">{{ formatMeters(result.map_distance_m) }} <span class="text-neutral-500">(folga {{ slackText }}%)</span></dd>
      <dt>GPS</dt>
      <dd class="num" data-testid="otdr-card-coords">{{ formatCoords(result.point) }} <span class="text-neutral-500">±{{ Math.round(result.tolerance_m) }} m</span></dd>
      <dt>Até {{ originName }}</dt>
      <dd class="num">{{ formatMeters(result.origin.distance_m) }}</dd>
      <dt>Até {{ targetName }}</dt>
      <dd class="num">{{ formatMeters(result.target.distance_m) }}</dd>
    </dl>
    <div class="orc-actions">
      <a class="orc-btn" :href="googleMapsUrl(result.point)" target="_blank" rel="noopener noreferrer" data-testid="otdr-gmaps">Google Maps</a>
      <a class="orc-btn" :href="wazeUrl(result.point)" target="_blank" rel="noopener noreferrer" data-testid="otdr-waze">Waze</a>
      <button type="button" class="orc-btn" data-testid="otdr-whatsapp" @click="copyWhatsapp">
        {{ copied ? 'Copiado!' : 'Copiar para WhatsApp' }}
      </button>
      <!-- EV-0128: fixar para toda a equipa (servidor) ou limpar -->
      <button v-if="!alert" type="button" class="orc-btn orc-btn-pin" :disabled="busy" data-testid="otdr-pin-alert" @click="$emit('pin')">
        {{ busy ? 'A fixar…' : 'Fixar alerta no mapa' }}
      </button>
      <button type="button" class="orc-btn orc-btn-clear" :disabled="busy" data-testid="otdr-clear" @click="$emit('clear')">Limpar</button>
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
import { computed, onBeforeUnmount, ref } from 'vue'
import { copyText } from '@/components/Gpon/ponDiagnosis'
import { formatCoords, formatMeters, googleMapsUrl, wazeUrl, whatsappText } from '@/utils/otdr'

const props = defineProps({
  result: { type: Object, required: true },
  /** EV-0128: alerta fixado (servidor) a que este ponto pertence; null = só neste ecrã */
  alert: { type: Object, default: null },
  busy: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
defineEmits(['close', 'clear', 'pin'])

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
