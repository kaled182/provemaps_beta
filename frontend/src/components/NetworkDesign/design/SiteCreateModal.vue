<template>
  <BaseModal :show="show" title="Novo site / POP" :icon="PhMapPin" size="sm" @close="$emit('close')">
    <form class="space-y-3" @submit.prevent="save">
      <p class="text-xs text-neutral-500 num">Ponto: {{ point?.lat.toFixed(6) }}, {{ point?.lng.toFixed(6) }}</p>
      <label class="fld">
        <span>Nome</span>
        <input v-model.trim="name" type="text" placeholder="SITE - VILA NOVA" required data-testid="site-name" />
      </label>
      <p v-if="error" class="text-sm text-danger" role="alert" data-testid="site-error">{{ error }}</p>
    </form>
    <template #footer>
      <div class="flex justify-end gap-2">
        <button type="button" class="btn" @click="$emit('close')">Cancelar</button>
        <button type="button" class="btn btn-primary" :disabled="!name || busy" data-testid="site-save" @click="save">
          {{ busy ? 'A gravar…' : 'Criar site' }}
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
/** Novo site / POP no ponto clicado (EV-0138). */
import { ref, watch } from 'vue'
import { PhMapPin } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({ show: { type: Boolean, default: false }, point: { type: Object, default: null } })
const emit = defineEmits(['close', 'created'])
const api = useApi()
const name = ref('')
const busy = ref(false)
const error = ref('')

watch(
  () => props.show,
  (open) => {
    if (open) {
      name.value = ''
      error.value = ''
    }
  },
)

async function save() {
  if (!name.value || !props.point || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const site = await api.post('/api/v1/sites/', {
      name: name.value,
      latitude: props.point.lat.toFixed(6),
      longitude: props.point.lng.toFixed(6),
    })
    emit('created', site)
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
