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
      <div class="flex justify-end">
        <button type="button" class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors" @click="closeModal">
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

const emit = defineEmits(['close', 'fiber-selected'])

const selectedFiber = ref(null)

const closeModal = () => {
  emit('close')
}

const handleFiberSelection = (fiber) => {
  selectedFiber.value = fiber
  emit('fiber-selected', fiber)
}

// Reset selected fiber quando modal fecha
watch(() => props.show, (newVal) => {
  if (!newVal) {
    selectedFiber.value = null
  }
})
</script>
