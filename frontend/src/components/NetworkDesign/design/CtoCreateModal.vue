<template>
  <BaseModal :show="show" title="Nova CTO" :subtitle="cable ? `sobre ${cable.name}` : 'solta (sem cabo)'" :icon="PhSquare" size="sm" @close="$emit('close')">
    <form class="space-y-3" @submit.prevent="save">
      <p class="text-xs text-neutral-500 num">Ponto: {{ point?.lat.toFixed(6) }}, {{ point?.lng.toFixed(6) }}</p>
      <p v-if="cable" class="text-xs text-neutral-500">Fica no ponto do traçado mais próximo; o km no cabo é calculado.</p>
      <label class="fld">
        <span>Nome / código</span>
        <input v-model.trim="name" type="text" placeholder="CTO-12" required data-testid="cto-name" />
      </label>
      <label class="fld">
        <span>Portas de atendimento</span>
        <select v-model.number="capacity" data-testid="cto-capacity">
          <option :value="null">Definir depois</option>
          <option v-for="c in [2, 4, 8, 16, 24, 32]" :key="c" :value="c">{{ c }}</option>
        </select>
      </label>
      <p v-if="error" class="text-sm text-danger" role="alert" data-testid="cto-error">{{ error }}</p>
    </form>
    <template #footer>
      <div class="flex justify-end gap-2">
        <button type="button" class="btn" @click="$emit('close')">Cancelar</button>
        <button type="button" class="btn btn-primary" :disabled="!name || busy" data-testid="cto-save" @click="save">
          {{ busy ? 'A gravar…' : 'Inserir CTO' }}
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
/** Nova CTO (EV-0139): sobre o cabo clicado (projetada no traçado) ou solta no mapa. */
import { ref, watch } from 'vue'
import { PhSquare } from '@phosphor-icons/vue'
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
const capacity = ref(null)
const busy = ref(false)
const error = ref('')

watch(
  () => props.show,
  (open) => {
    if (open) {
      name.value = ''
      capacity.value = null
      error.value = ''
    }
  },
)

async function save() {
  if (!name.value || !props.point || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const cto = await api.post('/api/v1/inventory/ctos/', {
      name: name.value,
      lat: props.point.lat,
      lng: props.point.lng,
      capacity: capacity.value,
      cable_id: props.cable?.id ?? null,
    })
    emit('created', cto)
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
.fld input,
.fld select {
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
