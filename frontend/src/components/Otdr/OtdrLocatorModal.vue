<template>
  <BaseModal
    :show="show"
    title="Localizar rompimento (OTDR)"
    :subtitle="current ? `${current.name}${lengthText ? ` · ${lengthText}` : ''}` : 'Escolha o cabo'"
    :icon="PhCrosshair"
    :z-index="zIndex"
    size="md"
    @close="$emit('close')"
  >
    <form class="space-y-4" data-testid="otdr-form" @submit.prevent="locate">
      <!-- EV-0128: aberto pela barra do mapa, escolhe-se o cabo aqui -->
      <div v-if="!cable">
        <label class="otdr-label" for="otdr-cable">Cabo</label>
        <select id="otdr-cable" v-model="pickedId" class="otdr-input otdr-select" data-testid="otdr-cable">
          <option :value="null" disabled>Escolher o cabo…</option>
          <option v-for="c in pickable" :key="c.id" :value="c.id">{{ c.name }}{{ c.length_km ? ` · ${formatMeters(c.length_km * 1000)}` : '' }}</option>
        </select>
      </div>

      <!-- Sentido da medição -->
      <fieldset>
        <legend class="otdr-label">Sentido da medição (onde está o OTDR)</legend>
        <div class="seg" role="group">
          <button
            v-for="d in directions"
            :key="d.value"
            type="button"
            class="seg-btn"
            :class="{ 'seg-on': direction === d.value }"
            :aria-pressed="direction === d.value"
            :data-testid="`otdr-dir-${d.value}`"
            @click="direction = d.value"
          >
            {{ d.label }}
          </button>
        </div>
      </fieldset>

      <!-- Distância medida -->
      <div>
        <label class="otdr-label" for="otdr-distance">Distância medida no OTDR</label>
        <div class="flex items-center gap-2">
          <input
            id="otdr-distance"
            v-model="distance"
            type="number"
            min="0"
            step="any"
            inputmode="decimal"
            class="otdr-input num"
            placeholder="14,85"
            required
            data-testid="otdr-distance"
          />
          <div class="seg" role="group" aria-label="Unidade">
            <button v-for="u in ['km', 'm']" :key="u" type="button" class="seg-btn" :class="{ 'seg-on': unit === u }" :data-testid="`otdr-unit-${u}`" @click="unit = u">
              {{ u }}
            </button>
          </div>
        </div>
      </div>

      <!-- Folga / reserva técnica -->
      <fieldset>
        <legend class="otdr-label">Folga / reserva técnica</legend>
        <div class="flex flex-wrap items-center gap-2">
          <div class="seg" role="group">
            <button
              v-for="p in SLACK_PRESETS"
              :key="p.value"
              type="button"
              class="seg-btn"
              :class="{ 'seg-on': !customSlack && slack === p.value }"
              :data-testid="`otdr-slack-${p.value}`"
              @click="pickSlack(p.value)"
            >
              {{ p.label }}
            </button>
            <button type="button" class="seg-btn" :class="{ 'seg-on': customSlack }" data-testid="otdr-slack-custom" @click="customSlack = true">
              Personalizado
            </button>
          </div>
          <label v-if="customSlack" class="flex items-center gap-1">
            <input v-model.number="slack" type="number" min="0" :max="SLACK_MAX" step="0.1" class="otdr-input otdr-input-sm num" data-testid="otdr-slack-value" />
            <span class="text-sm text-neutral-500">%</span>
          </label>
        </div>
        <p class="mt-1 text-xs text-neutral-500" data-testid="otdr-preview">
          No traçado: <span class="num">{{ previewText }}</span> = OTDR ÷ (1 + folga)
        </p>
      </fieldset>

      <p v-if="localError || error" class="text-sm text-danger" role="alert" data-testid="otdr-error">{{ localError || error }}</p>
    </form>
    <template #footer>
      <div class="flex justify-end gap-2">
        <button type="button" class="otdr-btn" @click="$emit('close')">Cancelar</button>
        <button type="button" class="otdr-btn otdr-btn-primary" :disabled="loading" data-testid="otdr-submit" @click="locate">
          {{ loading ? 'A calcular…' : 'Localizar no mapa' }}
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
/**
 * Formulário do localizador OTDR (EV-0127): cabo (já escolhido), sentido A→B / B→A, leitura
 * em km ou m, folga. O cálculo é do backend; o resultado sai por `located`.
 */
import { computed, ref, watch } from 'vue'
import { PhCrosshair } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import { useApi } from '@/composables/useApi'
import { SLACK_MAX, SLACK_PRESETS, formatMeters } from '@/utils/otdr'

const props = defineProps({
  show: { type: Boolean, default: false },
  /** cabo do mapa: { id, name, length_km, site_a_name, site_b_name }; null → escolher em `cables` */
  cable: { type: Object, default: null },
  /** EV-0128: cabos do mapa para escolher (só os com traçado) */
  cables: { type: Array, default: () => [] },
  zIndex: { type: Number, default: 3000 },
})
const emit = defineEmits(['close', 'located'])

const api = useApi()
const direction = ref('ab')
const distance = ref('')
const unit = ref('km')
const slack = ref(1.5)
const customSlack = ref(false)
const loading = ref(false)
const error = ref('')

watch(
  () => [props.show, props.cable?.id],
  ([open]) => {
    if (open) {
      error.value = ''
      loading.value = false
    }
  },
)

const pickedId = ref(null)
const pickable = computed(() =>
  props.cables
    .filter((c) => (c.path_coordinates?.length || 0) >= 2)
    .slice()
    .sort((a, b) => String(a.name).localeCompare(String(b.name), 'pt-BR')),
)
/** O cabo da medição: o recebido, ou o escolhido na lista. */
const current = computed(() => props.cable || pickable.value.find((c) => c.id === pickedId.value) || null)
const siteA = computed(() => current.value?.site_a_name || 'Site A')
const siteB = computed(() => current.value?.site_b_name || 'Site B')
const directions = computed(() => [
  { value: 'ab', label: `${siteA.value} → ${siteB.value}` },
  { value: 'ba', label: `${siteB.value} → ${siteA.value}` },
])
const lengthText = computed(() => {
  const km = Number(current.value?.length_km)
  return Number.isFinite(km) && km > 0 ? formatMeters(km * 1000) : ''
})

function pickSlack(v) {
  customSlack.value = false
  slack.value = v
}

const distanceM = computed(() => {
  const v = Number(String(distance.value).replace(',', '.'))
  if (!Number.isFinite(v) || v <= 0) return null
  return unit.value === 'km' ? v * 1000 : v
})
const slackPct = computed(() => Number(slack.value))
const mapM = computed(() => (distanceM.value === null ? null : distanceM.value / (1 + slackPct.value / 100)))
const previewText = computed(() => (mapM.value === null ? '—' : formatMeters(mapM.value)))

/** Validação local antes de ir ao servidor (o servidor valida contra o traçado real). */
const localError = computed(() => {
  if (distance.value === '' || distance.value === null) return ''
  if (distanceM.value === null) return 'Indique a distância medida no OTDR.'
  if (!Number.isFinite(slackPct.value) || slackPct.value < 0 || slackPct.value > SLACK_MAX) return `A folga vai de 0 a ${SLACK_MAX}%.`
  const km = Number(current.value?.length_km)
  if (Number.isFinite(km) && km > 0 && mapM.value > km * 1000 * 1.02) {
    return `Descontada a folga (${formatMeters(mapM.value)}), passa da extensão do cabo (${formatMeters(km * 1000)}).`
  }
  return ''
})

async function locate() {
  if (loading.value) return
  if (!current.value) {
    error.value = 'Escolha o cabo.'
    return
  }
  if (distanceM.value === null) {
    error.value = 'Indique a distância medida no OTDR.'
    return
  }
  if (localError.value) return
  loading.value = true
  error.value = ''
  try {
    const result = await api.get(`/api/v1/inventory/cables/${encodeURIComponent(current.value.id)}/otdr-locate/`, {
      direction: direction.value,
      distance_m: Math.round(distanceM.value * 10) / 10,
      slack_pct: slackPct.value,
    })
    emit('located', result)
  } catch (e) {
    error.value = e?.message || 'Não foi possível calcular o ponto.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.otdr-label {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  font-weight: 600;
  color: rgb(var(--n-700));
}
.seg {
  display: inline-flex;
  flex-wrap: wrap;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  overflow: hidden;
}
.seg-btn {
  padding: 5px 10px;
  font-size: 12px;
  color: rgb(var(--n-700));
  background: rgb(var(--surface));
  border-left: 1px solid rgb(var(--n-200));
}
.seg-btn:first-child {
  border-left: 0;
}
.seg-btn:hover {
  background: rgb(var(--n-100));
}
.seg-on,
.seg-on:hover {
  color: rgb(var(--primary-700));
  background: rgb(var(--primary-500) / 0.12);
  font-weight: 600;
}
.otdr-input {
  width: 10rem;
  padding: 6px 10px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  background: rgb(var(--surface));
  font-size: 14px;
  color: rgb(var(--n-900));
}
.otdr-select {
  width: 100%;
}
.otdr-input-sm {
  width: 5rem;
}
.otdr-input:focus {
  border-color: rgb(var(--primary-500));
  outline: none;
}
.otdr-btn {
  height: 32px;
  padding: 0 12px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  font-size: 13px;
  color: rgb(var(--n-700));
  background: rgb(var(--surface));
}
.otdr-btn:hover {
  background: rgb(var(--n-100));
}
.otdr-btn-primary {
  border-color: rgb(var(--primary-600));
  background: rgb(var(--primary-600));
  @apply text-white;
}
.otdr-btn-primary:hover {
  background: rgb(var(--primary-700));
}
.otdr-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
