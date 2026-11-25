<template>
  <BaseModal :show="show" title="Reserva técnica" :subtitle="cable?.name || ''" :icon="PhSpiral" size="sm" @close="$emit('close')">
    <form class="space-y-3" @submit.prevent="save">
      <p class="text-xs text-neutral-500 num">Ponto: {{ point?.lat.toFixed(6) }}, {{ point?.lng.toFixed(6) }}</p>
      <p class="text-xs text-neutral-500">A sobra fica no ponto do traçado mais próximo e soma ao comprimento do cabo.</p>
      <label class="fld">
        <span>Metros</span>
        <input v-model.number="meters" type="number" min="1" step="1" placeholder="30" required data-testid="slack-meters" />
      </label>
      <label class="fld">
        <span>Nome (opcional)</span>
        <input v-model.trim="name" type="text" placeholder="Reserva 30 m" data-testid="slack-name" />
      </label>
      <p v-if="error" class="text-sm text-danger" role="alert" data-testid="slack-error">{{ error }}</p>
    </form>
    <template #footer>
      <div class="flex justify-end gap-2">
        <button type="button" class="btn" @click="$emit('close')">Cancelar</button>
        <button type="button" class="btn btn-primary" :disabled="!(meters > 0) || busy" data-testid="slack-save" @click="save">
          {{ busy ? 'A gravar…' : 'Inserir reserva' }}
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
/** Reserva técnica no ponto do cabo clicado (EV-0138). */
import { ref, watch } from 'vue'
import { PhSpiral } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({
  show: { type: Boolean, default: false },
  point: { type: Object, default: null },
  cable: { type: Object, default: null },
})
const emit = defineEmits(['close', 'created'])
const api = useApi()
const name = ref('')
const meters = ref(null)
const busy = ref(false)
const error = ref('')

watch(
  () => props.show,
  (open) => {
    if (open) {
      name.value = ''
      meters.value = null
      error.value = ''
    }
  },
)

async function save() {
  if (!(meters.value > 0) || !props.point || !props.cable || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const slack = await api.post('/api/v1/inventory/slacks/', {
      cable_id: props.cable.id,
      lat: props.point.lat,
      lng: props.point.lng,
      meters: Number(meters.value),
      name: name.value,
    })
    emit('created', slack)
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
.fld input {
  padding: 6px 10px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  background: rgb(var(--surface));
  font-size: 13px;
  font-weight: 400;
  color: rgb(var(--n-900));
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
