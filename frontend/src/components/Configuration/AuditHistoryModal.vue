<template>
  <teleport to="body">
    <div class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-screen items-center justify-center p-4">
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black/50 dark:bg-black/70 transition-opacity" @click="$emit('close')"></div>

        <!-- Modal -->
        <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full">
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
              Histórico de Auditoria
            </h3>
            <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500">
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
              </svg>
            </button>
          </div>

          <div class="px-6 py-4 max-h-[600px] overflow-y-auto">
            <!-- Filters -->
            <div class="mb-4 flex gap-3">
              <select v-model="filter.action" class="input-sm">
                <option value="">Todas as ações</option>
                <option value="create">Criar</option>
                <option value="update">Atualizar</option>
                <option value="delete">Deletar</option>
              </select>

              <select v-model="filter.entity" class="input-sm">
                <option value="">Todas as entidades</option>
                <option value="system">Sistema</option>
                <option value="server">Servidor</option>
                <option value="gateway">Gateway</option>
                <option value="backup">Backup</option>
              </select>

              <input 
                v-model="filter.user" 
                type="text" 
                placeholder="Filtrar por usuário"
                class="input-sm"
              />
            </div>

            <!-- Audit Logs List -->
            <div v-if="filteredLogs.length > 0" class="space-y-3">
              <div 
                v-for="log in filteredLogs" 
                :key="log.id"
                class="flex items-start gap-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
              >
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 rounded-full flex items-center justify-center"
                       :class="getActionColor(log.action)">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path v-if="log.action === 'create'" fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd"/>
                      <path v-else-if="log.action === 'update'" fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
                      <path v-else fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/>
                    </svg>
                  </div>
                </div>

                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-gray-900 dark:text-white">
                      {{ log.user }}
                    </span>
                    <span class="text-xs px-2 py-0.5 rounded-full"
                          :class="getActionBadge(log.action)">
                      {{ log.action }}
                    </span>
                    <span class="text-xs text-gray-500 dark:text-gray-400">
                      {{ formatDate(log.timestamp) }}
                    </span>
                  </div>
                  <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">
                    {{ log.description }}
                  </p>
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {{ log.entity_type }}: {{ log.entity_name }}
                  </p>
                </div>
              </div>
            </div>

            <!-- Empty State -->
            <div v-else class="text-center py-12">
              <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">Nenhum registro de auditoria encontrado</p>
            </div>
          </div>

          <div class="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
            <button @click="$emit('close')" class="btn-primary">
              Fechar
            </button>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'

defineEmits(['close'])

const api = useApi()

// State
const logs = ref([])
const loading = ref(false)

const filter = ref({
  action: '',
  entity: '',
  user: '',
})

// Computed
const filteredLogs = computed(() => {
  return logs.value.filter(log => {
    if (filter.value.action && log.action !== filter.value.action) return false
    if (filter.value.entity && log.entity_type !== filter.value.entity) return false
    if (filter.value.user && !log.user.toLowerCase().includes(filter.value.user.toLowerCase())) return false
    return true
  })
})

// Methods
const getActionColor = (action) => {
  const colors = {
    create: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    update: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    delete: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
  }
  return colors[action] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
}

const getActionBadge = (action) => {
  const badges = {
    create: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    update: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    delete: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  }
  return badges[action] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

const loadAuditLogs = async () => {
  loading.value = true
  try {
    const response = await api.get('/api/v1/audit/logs/')
    logs.value = response.data || []
  } catch (error) {
    // Use mock data for development
    logs.value = [
      {
        id: 1,
        user: 'admin',
        action: 'update',
        entity_type: 'system',
        entity_name: 'Configurações do Sistema',
        description: 'Alterou REDIS_URL e DEBUG',
        timestamp: new Date().toISOString(),
      },
      {
        id: 2,
        user: 'admin',
        action: 'create',
        entity_type: 'server',
        entity_name: 'Zabbix Principal',
        description: 'Criou novo servidor de monitoramento',
        timestamp: new Date(Date.now() - 3600000).toISOString(),
      },
    ]
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadAuditLogs()
})
</script>

<style scoped>
.input-sm {
  @apply rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20;
}

.btn-primary {
  @apply inline-flex items-center justify-center rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 transition-all duration-200;
}
</style>
