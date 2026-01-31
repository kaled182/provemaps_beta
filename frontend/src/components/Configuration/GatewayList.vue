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
                   :class="gateway.is_active 
                     ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400' 
                     : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path v-if="typeIcon === 'sms'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
                  <path v-else-if="typeIcon === 'smtp'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                  <path v-else-if="typeIcon === 'telegram'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
                  <path v-else-if="typeIcon === 'video'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                  <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
                </svg>
              </div>
            </div>
            
            <div>
              <h4 class="text-base font-semibold text-gray-900 dark:text-white">
                {{ gateway.name }}
              </h4>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                {{ gateway.provider || typeLabel }}
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
            <p v-if="gateway.api_url"><span class="font-medium">URL:</span> {{ gateway.api_url }}</p>
            <p v-if="gateway.api_key"><span class="font-medium">API Key:</span> {{ maskApiKey(gateway.api_key) }}</p>
            <p v-if="gateway.username"><span class="font-medium">Usuário:</span> {{ gateway.username }}</p>
            <p v-if="gateway.sender_id"><span class="font-medium">Sender ID:</span> {{ gateway.sender_id }}</p>
            <p v-if="gateway.description" class="text-gray-500 dark:text-gray-500">{{ gateway.description }}</p>
          </div>
        </div>

        <div class="flex items-center gap-2 ml-4">
          <button 
            v-if="showTestButton"
            @click="$emit('test', gateway.id)" 
            :disabled="testing"
            class="btn-icon"
            title="Testar Gateway"
          >
            <svg v-if="testing" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
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
    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
    </svg>
    <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
      Nenhum gateway {{ typeLabel }} configurado
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  gateways: {
    type: Array,
    required: true,
  },
  type: {
    type: String,
    required: true,
    validator: (value) => ['sms', 'whatsapp', 'telegram', 'smtp', 'video'].includes(value),
  },
  testing: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['edit', 'delete', 'test'])

// Computed
const typeLabel = computed(() => {
  const labels = {
    sms: 'SMS',
    whatsapp: 'WhatsApp',
    telegram: 'Telegram',
    smtp: 'E-mail (SMTP)',
    video: 'Vídeo',
  }
  return labels[props.type] || props.type
})

const typeIcon = computed(() => props.type)

const showTestButton = computed(() => {
  // Show test button for SMS and SMTP gateways
  return ['sms', 'smtp'].includes(props.type)
})

// Methods
const maskApiKey = (key) => {
  if (!key) return ''
  if (key.length <= 8) return '***'
  return `${key.substring(0, 4)}${'*'.repeat(key.length - 8)}${key.substring(key.length - 4)}`
}
</script>

<style scoped>
.btn-icon {
  @apply p-2 rounded-md text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed;
}
</style>
