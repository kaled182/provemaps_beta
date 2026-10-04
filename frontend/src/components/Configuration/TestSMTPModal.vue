<template>
  <teleport to="body">
    <div class="fixed inset-0 z-[60] overflow-y-auto">
      <div class="flex min-h-screen items-center justify-center p-4">
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black/50 dark:bg-black/70 transition-opacity" @click="$emit('close')"></div>

        <!-- Modal -->
        <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
              Testar Envio de E-mail (SMTP)
            </h3>
            <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500">
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
              </svg>
            </button>
          </div>

          <form @submit.prevent="handleTest" class="space-y-4">
            <div>
              <label class="label-custom">E-mail do Destinatário *</label>
              <input
                v-model="testForm.recipient"
                type="email"
                class="input-custom"
                placeholder="destinatario@exemplo.com"
                required
                autofocus
              />
            </div>

            <div>
              <label class="label-custom">Mensagem de Teste</label>
              <textarea
                v-model="testForm.message"
                class="input-custom resize-none"
                rows="3"
                placeholder="Conteúdo da mensagem de teste..."
                maxlength="500"
              ></textarea>
              <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {{ testForm.message.length }}/500 caracteres
              </p>
            </div>

            <!-- Result Display -->
            <div v-if="testResult"
                 class="p-3 rounded-md text-sm"
                 :class="testResult.success
                   ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-800'
                   : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800'">
              <div class="flex items-start gap-2">
                <svg v-if="testResult.success" class="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <svg v-else class="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                </svg>
                <p>{{ testResult.message }}</p>
              </div>
            </div>

            <div class="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button type="button" @click="$emit('close')" class="btn-secondary">
                Fechar
              </button>
              <button type="submit" :disabled="testing" class="btn-primary">
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
import { ref } from 'vue'

const props = defineProps({
  gatewayConfig: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['close', 'test'])

const testForm = ref({
  recipient: props.gatewayConfig.test_recipient || '',
  message: 'Este é um e-mail de teste do sistema ProveMaps.',
})

const testing = ref(false)
const testResult = ref(null)

const handleTest = async () => {
  testing.value = true
  testResult.value = null

  try {
    emit('test', {
      ...props.gatewayConfig,
      test_recipient: testForm.value.recipient,
      test_message: testForm.value.message,
    })

    setTimeout(() => {
      testing.value = false
    }, 1000)
  } catch (error) {
    testResult.value = {
      success: false,
      message: error.message || 'Erro ao enviar e-mail de teste',
    }
    testing.value = false
  }
}

defineExpose({
  setResult: (result) => {
    testResult.value = result
    testing.value = false
  },
})
</script>

<style scoped>
.label-custom {
  @apply block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5;
}

.input-custom {
  @apply w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition-colors;
}

.btn-primary {
  @apply inline-flex items-center justify-center rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200;
}

.btn-secondary {
  @apply inline-flex items-center justify-center rounded-md bg-white dark:bg-gray-800 px-4 py-2 text-sm font-semibold text-gray-900 dark:text-gray-200 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all duration-200;
}
</style>
