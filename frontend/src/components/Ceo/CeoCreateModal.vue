<template>
  <BaseModal :show="show" title="Inserir CEO no traçado" :subtitle="cable ? cable.name : ''" :icon="PhPackage" size="md" @close="$emit('close')">
    <form class="space-y-3" data-testid="ceo-form" @submit.prevent="save">
      <p class="text-xs text-neutral-500">
        A caixa fica no ponto do traçado mais próximo de onde clicou no cabo
        <span v-if="point" class="num">({{ point.lat.toFixed(6) }}, {{ point.lng.toFixed(6) }})</span>; o km no cabo é calculado no servidor.
      </p>
      <label class="fld">
        <span>Nome / código</span>
        <input v-model.trim="name" type="text" placeholder="CEO-04" required data-testid="ceo-name" />
      </label>
      <fieldset>
        <legend class="fld-label">Passagem do cabo pela caixa</legend>
        <div class="seg" role="group">
          <button v-for="m in MODES" :key="m.value" type="button" class="seg-btn" :class="{ 'seg-on': mode === m.value }" :data-testid="`ceo-mode-${m.value}`" @click="mode = m.value">
            {{ m.label }}
          </button>
        </div>
        <p class="text-xs text-neutral-500 mt-1">{{ MODES.find((m) => m.value === mode).hint }}</p>
      </fieldset>
      <div class="grid grid-cols-2 gap-3">
        <label class="fld">
          <span>Reserva técnica (m)</span>
          <input v-model.number="slack" type="number" min="0" step="1" placeholder="20" data-testid="ceo-slack" />
        </label>
        <label class="fld">
          <span>Bandejas</span>
          <input v-model.number="trays" type="number" min="1" max="96" step="1" placeholder="2" data-testid="ceo-trays" />
        </label>
      </div>
      <p v-if="error" class="text-sm text-danger" role="alert" data-testid="ceo-error">{{ error }}</p>
    </form>
    <template #footer>
      <div class="flex justify-end gap-2">
        <button type="button" class="btn" @click="$emit('close')">Cancelar</button>
        <button type="button" class="btn btn-primary" :disabled="!name || busy" data-testid="ceo-save" @click="save">
          {{ busy ? 'A gravar…' : 'Inserir CEO' }}
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
/** Inserir uma CEO no traçado de um cabo (EV-0135), no ponto onde se clicou no cabo. */
import { ref, watch } from 'vue'
import { PhPackage } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({
  show: { type: Boolean, default: false },
  cable: { type: Object, default: null },
  /** {lat, lng} do clique no cabo */
  point: { type: Object, default: null },
})
const emit = defineEmits(['close', 'created'])

const MODES = [
  { value: 'sangria', label: 'Sangria (passagem direta)', hint: 'O cabo atravessa a caixa sem ser cortado; só as fibras escolhidas são sangradas para o derivado.' },
  { value: 'corte', label: 'Corte / emenda total', hint: 'O cabo é cortado na caixa: todas as fibras podem ser emendadas livremente.' },
]

const api = useApi()
const name = ref('')
const mode = ref('sangria')
const slack = ref(null)
const trays = ref(null)
const busy = ref(false)
const error = ref('')

watch(
  () => props.show,
  (open) => {
    if (open) {
      name.value = ''
      mode.value = 'sangria'
      slack.value = null
      trays.value = null
      error.value = ''
    }
  },
)

async function save() {
  if (!name.value || !props.cable || !props.point || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const ceo = await api.post('/api/v1/inventory/ceos/', {
      cable_id: props.cable.id,
      lat: props.point.lat,
      lng: props.point.lng,
      name: name.value,
      mode: mode.value,
      slack_m: slack.value === '' || slack.value === null ? null : Number(slack.value),
      trays: trays.value === '' || trays.value === null ? null : Number(trays.value),
    })
    emit('created', ceo)
  } catch (e) {
    error.value = e?.message || 'erro desconhecido'
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
}
.fld {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: rgb(var(--n-700));
}
.fld-label {
  margin-bottom: 4px;
  font-size: 12px;
  font-weight: 600;
  color: rgb(var(--n-700));
}
.fld input {
  padding: 6px 10px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  background: rgb(var(--surface));
  font-size: 13px;
  font-weight: 400;
  color: rgb(var(--n-900));
}
.seg {
  display: inline-flex;
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
.seg-on {
  color: rgb(var(--primary-700));
  background: rgb(var(--primary-500) / 0.12);
  font-weight: 600;
}
.btn {
  height: 32px;
  padding: 0 12px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  font-size: 13px;
  color: rgb(var(--n-700));
  background: rgb(var(--surface));
}
.btn-primary {
  border-color: rgb(var(--primary-600));
  background: rgb(var(--primary-600));
  @apply text-white;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
