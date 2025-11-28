<template>
  <Transition name="modal">
    <div 
      v-if="show" 
      class="fixed inset-0 z-50 overflow-y-auto"
      @click.self="closeModal"
    >
      <div class="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:p-0">
        
        <!-- Backdrop -->
        <div class="fixed inset-0 transition-opacity bg-gray-900/75 backdrop-blur-sm" @click="closeModal"></div>

        <!-- Modal Panel -->
        <div class="relative inline-block w-full max-w-5xl overflow-hidden text-left align-middle transition-all transform bg-white dark:bg-gray-800 rounded-2xl shadow-2xl">
          
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-gray-800 dark:to-gray-900">
            <div class="flex items-center gap-3">
              <div class="flex items-center justify-center w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900">
                <i class="fas fa-network-wired text-indigo-600 dark:text-indigo-400"></i>
              </div>
              <div>
                <h3 class="text-lg font-bold text-gray-900 dark:text-white">
                  Estrutura Física do Cabo
                </h3>
                <p class="text-xs text-gray-500 dark:text-gray-400">
                  Visualização em tempo real da hierarquia de tubos e fibras
                </p>
              </div>
            </div>
            
            <button 
              @click="closeModal"
              class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
            >
              <i class="fas fa-times text-xl"></i>
            </button>
          </div>

          <!-- Content -->
          <div class="h-[600px]">
            <CableStructureView 
              v-if="cableId"
              :cable-id="cableId" 
              @select-fiber="handleFiberSelection"
            />
          </div>

          <!-- Footer com Ações Adicionais -->
          <div class="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
            <div class="flex gap-2">
              <button 
                @click="handleFusionWorkflow"
                class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors flex items-center gap-2"
              >
                <i class="fas fa-link"></i>
                Criar Fusão
              </button>
              <button 
                @click="handlePortConnection"
                class="px-4 py-2 text-sm font-medium text-indigo-600 bg-white hover:bg-indigo-50 border border-indigo-300 rounded-lg transition-colors flex items-center gap-2"
              >
                <i class="fas fa-plug"></i>
                Conectar a Porta
              </button>
            </div>
            
            <button 
              @click="closeModal"
              class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              Fechar
            </button>
          </div>

        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, watch } from 'vue'
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
  console.log('Fibra selecionada para operação:', fiber)
}

const handleFusionWorkflow = () => {
  if (!selectedFiber.value) {
    alert('Selecione uma fibra primeiro clicando nela no diagrama')
    return
  }
  emit('fusion-requested', selectedFiber.value)
  console.log('Iniciar workflow de fusão para fibra:', selectedFiber.value)
}

const handlePortConnection = () => {
  if (!selectedFiber.value) {
    alert('Selecione uma fibra primeiro clicando nela no diagrama')
    return
  }
  emit('port-connection-requested', selectedFiber.value)
  console.log('Iniciar conexão de fibra a porta:', selectedFiber.value)
}

// Reset selected fiber quando modal fecha
watch(() => props.show, (newVal) => {
  if (!newVal) {
    selectedFiber.value = null
  }
})
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .inline-block,
.modal-leave-active .inline-block {
  transition: all 0.3s ease;
}

.modal-enter-from .inline-block,
.modal-leave-to .inline-block {
  transform: scale(0.95) translateY(-20px);
  opacity: 0;
}
</style>
