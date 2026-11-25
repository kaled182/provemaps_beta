<template>
  <BaseModal
    :show="isOpen"
    :title="`Ações · ${port?.name || ''}`"
    :icon="PhGear"
    :dirty="dirty"
    :z-index="3500"
    size="sm"
    @close="close"
  >
    <label class="mb-1 block text-xs font-medium uppercase tracking-wide text-neutral-500" for="port-notes">Descrição</label>
    <textarea
      id="port-notes"
      v-model="editedDescription"
      class="w-full rounded-md border border-neutral-200 bg-surface px-2.5 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-primary-500 focus:outline-none"
      placeholder="Descrição da porta…"
      maxlength="255"
      rows="3"
      data-testid="port-notes"
    ></textarea>
    <p class="mt-1 text-xs text-neutral-500">Fica no campo «notas» da porta (até 255 caracteres).</p>

    <template #footer>
      <div class="flex justify-end gap-2">
        <button type="button" class="h-8 rounded-md border border-neutral-200 px-3 text-sm text-neutral-700 hover:bg-neutral-100" @click="close">
          Fechar
        </button>
        <button
          type="button"
          class="h-8 rounded-md bg-primary-600 px-3 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          :disabled="saving || !dirty"
          data-testid="port-notes-save"
          @click="saveDescription"
        >
          {{ saving ? 'A guardar…' : 'Guardar descrição' }}
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
/**
 * Ações da porta (EV-0068a). Só o que o backend faz de facto: editar a descrição,
 * que vive em `Port.notes`. Antes o modal enviava `description` (campo que não
 * existe — o DRF ignorava e respondia 200, «Descrição salva» sem gravar nada), e
 * tinha «Resetar porta» e «Logs» sem endpoint (os logs mostravam uma entrada
 * inventada quando a chamada falhava).
 */
import { ref, computed, watch } from 'vue'
import { PhGear } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  port: { type: Object, default: null },
})
const emit = defineEmits(['close', 'refresh'])

const { patch } = useApi()
const { success, error: notifyError } = useNotification()

const original = ref('')
const editedDescription = ref('')
const saving = ref(false)
const dirty = computed(() => editedDescription.value !== original.value)

const close = () => emit('close')

const saveDescription = async () => {
  if (!props.port?.id) return
  saving.value = true
  try {
    await patch(`/api/v1/ports/${props.port.id}/`, { notes: editedDescription.value })
    original.value = editedDescription.value
    success('Descrição guardada', 'A descrição da porta foi atualizada.')
    emit('refresh')
    close()
  } catch (error) {
    console.error('[PortActionsModal] Erro ao guardar a descrição:', error)
    notifyError('Erro', 'Não foi possível guardar a descrição.')
  } finally {
    saving.value = false
  }
}

watch(
  () => [props.isOpen, props.port?.id],
  ([open]) => {
    if (!open) return
    original.value = props.port?.notes ?? props.port?.description ?? ''
    editedDescription.value = original.value
  },
  { immediate: true },
)
</script>
