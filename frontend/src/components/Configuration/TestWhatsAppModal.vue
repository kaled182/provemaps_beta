<template>
  <teleport to="body">
    <div class="fixed inset-0 z-[60] overflow-y-auto">
      <div class="flex min-h-screen items-center justify-center p-4">
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black/50 transition-opacity" @click="$emit('close')"></div>

        <!-- Modal -->
        <div class="relative bg-surface rounded-lg shadow-xl max-w-md w-full p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-neutral-900">
              Testar WhatsApp
            </h3>
            <button @click="$emit('close')" class="text-neutral-400 hover:text-neutral-500">
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
              </svg>
            </button>
          </div>

          <form @submit.prevent="handleTest" class="space-y-4">
            <!-- Recipient Field -->
            <div>
              <label for="recipient" class="block text-sm font-medium text-neutral-700 mb-1">
                Número do Destinatário *
              </label>
              <input
                id="recipient"
                v-model="formData.recipient"
                type="tel"
                required
                placeholder="+5561999999999"
                class="w-full rounded-md border-neutral-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
              />
              <p class="mt-1 text-xs text-neutral-500">
                Formato: +55 DDD + número (exemplo: +5561999999999)
              </p>
            </div>

            <!-- Message Field -->
            <div>
              <label for="message" class="block text-sm font-medium text-neutral-700 mb-1">
                Mensagem *
              </label>
              <textarea
                id="message"
                v-model="formData.message"
                required
                rows="4"
                placeholder="Digite a mensagem de teste..."
                class="w-full rounded-md border-neutral-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
              ></textarea>
              <p class="mt-1 text-xs text-neutral-500">
                {{ formData.message.length }} caracteres
              </p>
            </div>

            <!-- Connection Status Warning -->
            <div v-if="!isConnected" class="bg-warning/10 border border-warning rounded-lg p-3">
              <div class="flex items-start gap-2">
                <svg class="w-5 h-5 text-warning flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
                <p class="text-sm text-warning">
                  <strong>Atenção:</strong> O WhatsApp não está conectado. Conecte antes de testar.
                </p>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="flex justify-end gap-3 pt-4 border-t border-neutral-200">
              <button
                type="button"
                @click="$emit('close')"
                class="btn-secondary"
              >
                Cancelar
              </button>
              <button
                type="submit"
                :disabled="testing || !isConnected"
                class="btn-primary"
              >
                <svg v-if="testing" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {{ testing ? 'Enviando...' : 'Enviar Teste' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  gatewayId: {
    type: [Number, String],
    required: true,
  },
  isConnected: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'test'])

const testing = ref(false)
const formData = ref({
  recipient: '',
  message: 'Esta é uma mensagem de teste do sistema ProveMaps.',
})

const handleTest = async () => {
  if (!formData.value.recipient || !formData.value.message) {
    return
  }

  testing.value = true
  try {
    await emit('test', {
      recipient: formData.value.recipient,
      message: formData.value.message,
    })
    
    // Reset form after successful test
    formData.value.recipient = ''
    formData.value.message = 'Esta é uma mensagem de teste do sistema ProveMaps.'
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.btn-primary {
  @apply inline-flex items-center justify-center rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200;
}

.btn-secondary {
  @apply inline-flex items-center justify-center rounded-md bg-surface px-4 py-2 text-sm font-semibold text-neutral-900 shadow-sm ring-1 ring-inset ring-neutral-300 hover:bg-neutral-50 transition-all duration-200;
}
</style>
