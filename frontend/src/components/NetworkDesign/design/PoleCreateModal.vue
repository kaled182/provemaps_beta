<template>
  <BaseModal :show="show" title="Novo poste" :icon="PhLineVertical" size="sm" @close="$emit('close')">
    <form class="space-y-3" @submit.prevent="save">
      <p class="text-xs text-neutral-500 num">Ponto: {{ point?.lat.toFixed(6) }}, {{ point?.lng.toFixed(6) }}</p>
      <label class="fld">
        <span>Código / placa</span>
        <input v-model.trim="name" type="text" placeholder="P-01234" required data-testid="pole-name" />
      </label>
      <div class="grid grid-cols-2 gap-3">
        <label class="fld">
          <span>Concessionária</span>
          <input v-model.trim="owner" type="text" placeholder="Energisa" data-testid="pole-owner" />
        </label>
        <label class="fld">
          <span>Altura (m)</span>
          <input v-model.number="height" type="number" min="1" max="40" step="0.5" placeholder="11" data-testid="pole-height" />
        </label>
      </div>
      <p v-if="error" class="text-sm text-danger" role="alert" data-testid="pole-error">{{ error }}</p>
    </form>
    <template #footer>
      <div class="flex justify-end gap-2">
        <button type="button" class="btn" @click="$emit('close')">Cancelar</button>
        <button type="button" class="btn btn-primary" :disabled="!name || busy" data-testid="pole-save" @click="save">
          {{ busy ? 'A gravar…' : 'Inserir poste' }}
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
/** Novo poste no ponto clicado (EV-0139). */
import { ref, watch } from 'vue'
import { PhLineVertical } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({ show: { type: Boolean, default: false }, point: { type: Object, default: null } })
const emit = defineEmits(['close', 'created'])
const api = useApi()
const name = ref('')
const owner = ref('')
const height = ref(null)
const busy = ref(false)
const error = ref('')

watch(
  () => props.show,
  (open) => {
    if (open) {
      name.value = ''
      owner.value = ''
      height.value = null
      error.value = ''
    }
  },
)

async function save() {
  if (!name.value || !props.point || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const pole = await api.post('/api/v1/inventory/poles/', {
      name: name.value,
      lat: props.point.lat,
      lng: props.point.lng,
      owner: owner.value,
      height_m: Number.isFinite(height.value) ? height.value : null,
    })
    emit('created', pole)
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
