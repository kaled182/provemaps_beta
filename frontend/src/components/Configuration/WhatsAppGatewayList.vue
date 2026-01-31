<template>
  <div v-if="gateways.length > 0" class="grid gap-4">
    <div 
      v-for="gateway in gateways" 
      :key="gateway.id"
      class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-5 hover:shadow-md transition-shadow"
    >
      <div class="flex items-start justify-between">
        <div class="flex-1">
          <div class="flex items-center gap-3">
            <div class="flex-shrink-0">
              <div class="w-10 h-10 rounded-full flex items-center justify-center"
                   :class="getConnectionStatusColor(gateway.connection_status)">
                <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
                </svg>
              </div>
            </div>
            
            <div>
              <h4 class="text-base font-semibold text-gray-900 dark:text-white">
                {{ gateway.name }}
              </h4>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                {{ getConnectionStatusText(gateway.connection_status) }}
              </p>
            </div>

            <span 
              class="ml-2 px-2.5 py-0.5 rounded-full text-xs font-medium"
              :class="gateway.is_active 
                ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' 
                : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'"
            >
              {{ gateway.is_active ? 'Ativo' : 'Inativo' }}
            </span>
          </div>
          
          <div class="mt-3 space-y-1 text-sm text-gray-600 dark:text-gray-400">
            <p v-if="gateway.phone_number">
              <span class="font-medium">Número:</span> {{ formatPhoneNumber(gateway.phone_number) }}
            </p>
            <p v-if="gateway.api_url">
              <span class="font-medium">API:</span> {{ gateway.api_url }}
            </p>
            <p v-if="gateway.session_id">
              <span class="font-medium">Sessão:</span> {{ gateway.session_id }}
            </p>
            <p v-if="gateway.last_connection" class="text-xs text-gray-500 dark:text-gray-500">
              Última conexão: {{ formatDate(gateway.last_connection) }}
            </p>
            <p v-if="gateway.description" class="text-gray-500 dark:text-gray-500">
              {{ gateway.description }}
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2 ml-4">
          <!-- QR Code Button -->
          <button 
            v-if="gateway.connection_status === 'disconnected' || !gateway.connection_status"
            @click="$emit('generate-qr', gateway.id)" 
            class="btn-icon"
            title="Gerar QR Code"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"/>
            </svg>
          </button>

          <!-- Check Status Button -->
          <button 
            v-if="gateway.connection_status === 'connecting' || gateway.connection_status === 'qr_pending'"
            @click="$emit('check-qr', gateway.id)" 
            class="btn-icon"
            title="Verificar Status"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
          </button>

          <!-- Disconnect Button -->
          <button 
            v-if="gateway.connection_status === 'connected'"
            @click="$emit('disconnect', gateway.id)" 
            class="btn-icon text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-900/20"
            title="Desconectar"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
            </svg>
          </button>

          <button 
            @click="$emit('edit', gateway)" 
            class="btn-icon"
            title="Editar"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
            </svg>
          </button>

          <button 
            @click="$emit('delete', gateway.id)" 
            class="btn-icon text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
            title="Excluir"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Empty State -->
  <div v-else class="text-center py-12 bg-gray-50 dark:bg-gray-800/50 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-700">
    <svg class="mx-auto h-12 w-12 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
    </svg>
    <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
      Nenhum gateway WhatsApp configurado
    </p>
    <p class="mt-1 text-xs text-gray-500 dark:text-gray-500">
      Configure um gateway para enviar mensagens via WhatsApp
    </p>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

defineProps({
  gateways: {
    type: Array,
    required: true,
  },
})

defineEmits(['edit', 'delete', 'generate-qr', 'check-qr', 'disconnect'])

// Methods
const getConnectionStatusColor = (status) => {
  const colors = {
    connected: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    connecting: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400',
    qr_pending: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    disconnected: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
    error: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
  }
  return colors[status] || colors.disconnected
}

const getConnectionStatusText = (status) => {
  const texts = {
    connected: 'Conectado',
    connecting: 'Conectando...',
    qr_pending: 'Aguardando QR Code',
    disconnected: 'Desconectado',
    error: 'Erro de conexão',
  }
  return texts[status] || 'Status desconhecido'
}

const formatPhoneNumber = (phone) => {
  if (!phone) return ''
  // Format: +55 11 98765-4321
  const cleaned = phone.replace(/\D/g, '')
  if (cleaned.length === 13) {
    return `+${cleaned.slice(0, 2)} ${cleaned.slice(2, 4)} ${cleaned.slice(4, 9)}-${cleaned.slice(9)}`
  }
  return phone
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}
</script>

<style scoped>
.btn-icon {
  @apply p-2 rounded-md text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed;
}
</style>
