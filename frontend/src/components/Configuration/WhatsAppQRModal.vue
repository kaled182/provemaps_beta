<template>
  <teleport to="body">
    <div class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-screen items-center justify-center p-4">
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black/50 dark:bg-black/70 transition-opacity"></div>

        <!-- Modal -->
        <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
              Conectar WhatsApp
            </h3>
            <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500">
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
              </svg>
            </button>
          </div>

          <div class="space-y-4">
            <!-- Status Message -->
            <div class="text-center">
              <div v-if="status === 'qr_pending' || status === 'disconnected'" class="space-y-2">
                <div class="w-12 h-12 mx-auto rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                  <svg class="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"/>
                  </svg>
                </div>
                <p class="text-sm font-medium text-gray-900 dark:text-white">
                  Escaneie o QR Code
                </p>
                <p class="text-xs text-gray-500 dark:text-gray-400">
                  Abra o WhatsApp no seu telefone e escaneie este código
                </p>
              </div>

              <div v-else-if="status === 'connecting' || status === 'authenticating'" class="space-y-2">
                <div class="w-12 h-12 mx-auto rounded-full bg-yellow-100 dark:bg-yellow-900/30 flex items-center justify-center">
                  <svg class="w-6 h-6 text-yellow-600 dark:text-yellow-400 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
                <p class="text-sm font-medium text-gray-900 dark:text-white">
                  QR Code escaneado!
                </p>
                <p class="text-xs text-gray-500 dark:text-gray-400">
                  Aguarde enquanto estabelecemos a conexão com o WhatsApp...
                </p>
              </div>

              <div v-else-if="status === 'connected'" class="space-y-2">
                <div class="w-12 h-12 mx-auto rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                  <svg class="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                  </svg>
                </div>
                <p class="text-sm font-medium text-green-600 dark:text-green-400">
                  Conectado com sucesso!
                </p>
                <p class="text-xs text-gray-500 dark:text-gray-400">
                  O WhatsApp está pronto para uso
                </p>
              </div>

              <div v-else-if="status === 'error'" class="space-y-2">
                <div class="w-12 h-12 mx-auto rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                  <svg class="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                </div>
                <p class="text-sm font-medium text-red-600 dark:text-red-400">
                  Erro ao conectar
                </p>
                <p class="text-xs text-gray-500 dark:text-gray-400">
                  Tente novamente ou verifique as configurações
                </p>
              </div>
            </div>

            <!-- 401 Error Warning -->
            <div v-if="lastDisconnectReason === 401 && status === 'disconnected'" class="bg-red-50 dark:bg-red-900/20 border-2 border-red-400 dark:border-red-600 rounded-lg p-4 mb-4">
              <div class="flex items-start gap-3">
                <div class="flex-shrink-0">
                  <svg class="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                  </svg>
                </div>
                <div class="flex-1">
                  <h4 class="text-sm font-bold text-red-900 dark:text-red-300 mb-2">
                    ⛔ Sessão rejeitada pelo WhatsApp
                  </h4>
                  <p class="text-xs text-red-800 dark:text-red-400 mb-3">
                    O WhatsApp recusou a conexão imediatamente. Causas comuns:
                  </p>
                  <ul class="text-xs text-red-700 dark:text-red-400 space-y-1.5 list-disc list-inside mb-3">
                    <li><strong>Limite de dispositivos (4 máximo):</strong> Você já tem 4 dispositivos conectados. Desconecte um antigo primeiro.</li>
                    <li><strong>Sessão anterior corrompida:</strong> Pode haver dados de uma tentativa anterior ainda em cache.</li>
                    <li><strong>Múltiplas tentativas:</strong> Aguarde 1 minuto antes de tentar novamente.</li>
                  </ul>
                  <div class="bg-red-100 dark:bg-red-900/40 rounded p-2">
                    <p class="text-xs font-semibold text-red-900 dark:text-red-300 mb-1">
                      🔧 Como resolver:
                    </p>
                    <ol class="text-xs text-red-800 dark:text-red-400 space-y-1 list-decimal list-inside pl-2">
                      <li>Clique em "Resetar Sessão" abaixo</li>
                      <li>Aguarde 30 segundos</li>
                      <li>Verifique dispositivos conectados no WhatsApp (Configurações > Dispositivos conectados)</li>
                      <li>Se tiver 4 dispositivos, desconecte um</li>
                      <li>Tente gerar novo QR Code</li>
                    </ol>
                  </div>
                </div>
              </div>
            </div>

            <!-- Timeout/408 Error Warning -->
            <div v-if="lastDisconnectReason === 408" class="bg-yellow-50 dark:bg-yellow-900/20 border-2 border-yellow-400 dark:border-yellow-600 rounded-lg p-4">
              <div class="flex items-start gap-3">
                <div class="flex-shrink-0">
                  <svg class="w-6 h-6 text-yellow-600 dark:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                  </svg>
                </div>
                <div class="flex-1">
                  <h4 class="text-sm font-bold text-yellow-900 dark:text-yellow-300 mb-2">
                    ⏱️ Tempo esgotado - QR Code expirou
                  </h4>
                  <p class="text-xs text-yellow-800 dark:text-yellow-400 mb-3">
                    O QR Code tem validade de 60 segundos. Possíveis causas:
                  </p>
                  <ul class="text-xs text-yellow-700 dark:text-yellow-400 space-y-1.5 list-disc list-inside mb-3">
                    <li><strong>Limite de dispositivos:</strong> WhatsApp permite apenas 4 dispositivos conectados. Você precisa desconectar um dispositivo antigo antes.</li>
                    <li><strong>Demora ao escanear:</strong> Escaneie e confirme rapidamente (menos de 60 segundos).</li>
                    <li><strong>Conexão lenta:</strong> Verifique sua conexão de internet no celular.</li>
                  </ul>
                  <div class="bg-yellow-100 dark:bg-yellow-900/40 rounded p-2 mb-2">
                    <p class="text-xs font-semibold text-yellow-900 dark:text-yellow-300 mb-1">
                      📱 Como liberar espaço para novos dispositivos:
                    </p>
                    <ol class="text-xs text-yellow-800 dark:text-yellow-400 space-y-1 list-decimal list-inside pl-2">
                      <li>Abra WhatsApp no celular</li>
                      <li>Configurações > Dispositivos conectados</li>
                      <li>Toque em um dispositivo antigo</li>
                      <li>Selecione "Desconectar"</li>
                      <li>Volte aqui e clique em "Resetar Sessão" → "Gerar QR Code"</li>
                    </ol>
                  </div>
                  <p class="text-xs font-semibold text-yellow-900 dark:text-yellow-300">
                    💡 Após liberar espaço, clique em "Resetar Sessão" abaixo para tentar novamente.
                  </p>
                </div>
              </div>
            </div>

            <!-- QR Code Display -->
            <div v-if="qrCode && (status === 'qr_pending' || status === 'disconnected')" class="flex justify-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <img :src="qrCode" alt="QR Code" class="w-64 h-64 border-4 border-white dark:border-gray-800 shadow-lg" />
            </div>

            <!-- Instructions -->
            <div v-if="status === 'qr_pending' || status === 'disconnected'" class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
              <h4 class="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-2">
                Como conectar:
              </h4>
              <ol class="text-xs text-blue-700 dark:text-blue-400 space-y-1 list-decimal list-inside">
                <li>Abra o WhatsApp no seu telefone</li>
                <li>Toque em Mais opções > Dispositivos conectados</li>
                <li>Toque em Conectar um dispositivo</li>
                <li>Aponte seu telefone para esta tela para capturar o código</li>
                <li><strong>Aja rápido:</strong> Você tem 60 segundos após escanear!</li>
              </ol>
            </div>

            <!-- Auto-check info -->
            <div v-if="status === 'qr_pending' || status === 'connecting' || status === 'disconnected'" class="text-center">
              <p class="text-xs text-gray-500 dark:text-gray-400">
                <svg class="inline-block w-3 h-3 mr-1 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Verificando status automaticamente...
              </p>
            </div>

            <!-- Action Buttons -->
            <div class="flex justify-between gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <!-- Reset Button (left) -->
              <button 
                @click="$emit('reset')"
                class="btn-danger"
                title="Resetar sessão e limpar dados"
              >
                <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>
                Resetar Sessão
              </button>

              <!-- Right side buttons -->
              <div class="flex gap-3">
                <button 
                  v-if="status === 'qr_pending' || status === 'connecting' || status === 'disconnected'"
                  @click="$emit('check')" 
                  :disabled="checking"
                  class="btn-secondary"
                >
                  <svg v-if="checking" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Verificar Agora
                </button>

                <button @click="$emit('close')" class="btn-primary">
                  {{ status === 'connected' ? 'Concluir' : 'Fechar' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  gatewayId: {
    type: [Number, String],
    required: true,
  },
  qrCode: {
    type: String,
    default: null,
  },
  status: {
    type: String,
    default: 'qr_pending',
    validator: (value) => ['qr_pending', 'connecting', 'connected', 'error', 'disconnected', 'authenticating'].includes(value),
  },
  lastDisconnectReason: {
    type: [Number, String],
    default: null,
  },
})

const emit = defineEmits(['close', 'check', 'reset'])

// Local state
const checking = ref(false)
let checkInterval = null

// Debug props
console.log('[WhatsAppQRModal] Props:', {
  gatewayId: props.gatewayId,
  qrCode: props.qrCode,
  status: props.status,
  lastDisconnectReason: props.lastDisconnectReason
})

// Watch for status changes
watch(() => props.status, (newStatus, oldStatus) => {
  console.log('[WhatsAppQRModal] Status changed:', oldStatus, '->', newStatus)
  
  if (newStatus === 'connected') {
    console.log('[WhatsAppQRModal] Connected! Will close soon...')
  }
})

// Auto-check status every 3 seconds
onMounted(() => {
  if (props.status === 'qr_pending' || props.status === 'connecting' || props.status === 'disconnected' || props.status === 'authenticating') {
    checkInterval = setInterval(() => {
      emit('check')
    }, 3000)
  }
})

onUnmounted(() => {
  if (checkInterval) {
    clearInterval(checkInterval)
  }
})
</script>

<style scoped>
.btn-primary {
  @apply inline-flex items-center justify-center rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 transition-all duration-200;
}

.btn-secondary {
  @apply inline-flex items-center justify-center rounded-md bg-white dark:bg-gray-800 px-4 py-2 text-sm font-semibold text-gray-900 dark:text-gray-200 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200;
}

.btn-danger {
  @apply inline-flex items-center justify-center rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 transition-all duration-200;
}
</style>
