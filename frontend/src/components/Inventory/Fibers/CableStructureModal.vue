<template>
  <BaseModal
    :show="show"
    title="Estrutura física do cabo"
    subtitle="Hierarquia de tubos e fibras"
    :icon="PhTreeStructure"
    size="detail"
    flush
    @close="closeModal"
  >
    <div class="h-[600px]">
      <CableStructureView 
        v-if="cableId"
        :cable-id="cableId" 
        @select-fiber="handleFiberSelection"
      />
    </div>

    <template #footer>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <button 
            :disabled="!selectedFiber"
          @click="handleFusionWorkflow"
            class="px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i class="fas fa-link"></i>
            Criar Fusão
          </button>
          <button 
            :disabled="!selectedFiber"
          @click="handlePortConnection"
            class="px-4 py-2 text-sm font-medium text-primary-600 bg-surface hover:bg-primary-50 border border-primary-300 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i class="fas fa-plug"></i>
            Conectar a Porta
          </button>
          <span v-if="!selectedFiber" class="text-xs text-neutral-500" data-testid="fiber-hint">Selecione uma fibra no diagrama</span>
        </div>

        <button 
          @click="closeModal"
          class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
        >
          Fechar
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch } from 'vue'
import { PhTreeStructure } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import CableStructureView from './CableStructureView.vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  cableId: {
    type: [Number, String],
    default: null
  }
})

const emit = defineEmits(['close', 'fiber-selected', 'fusion-requested', 'port-connection-requested'])

const selectedFiber = ref(null)

const closeModal = () => {
  emit('close')
}

const handleFiberSelection = (fiber) => {
  selectedFiber.value = fiber
  emit('fiber-selected', fiber)
}

// Sem fibra escolhida os botões ficam desativados, com a dica ao lado (sem alert).
const handleFusionWorkflow = () => {
  if (selectedFiber.value) emit('fusion-requested', selectedFiber.value)
}

const handlePortConnection = () => {
  if (selectedFiber.value) emit('port-connection-requested', selectedFiber.value)
}

// Reset selected fiber quando modal fecha
watch(() => props.show, (newVal) => {
  if (!newVal) {
    selectedFiber.value = null
  }
})
</script>
