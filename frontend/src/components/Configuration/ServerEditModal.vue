<template>
  <teleport to="body">
    <div class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-screen items-center justify-center p-4">
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black/50 dark:bg-black/70 transition-opacity" @click="$emit('close')"></div>

        <!-- Modal -->
        <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
              {{ isEditing ? 'Editar Servidor' : 'Adicionar Servidor' }}
            </h3>
            <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500">
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
              </svg>
            </button>
          </div>

          <form @submit.prevent="handleSubmit" class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="label-custom">Nome *</label>
                <input 
                  v-model="form.name" 
                  type="text" 
                  class="input-custom" 
                  placeholder="Ex: Zabbix Principal"
                  required
                />
              </div>

              <div>
                <label class="label-custom">Tipo *</label>
                <select v-model="form.server_type" class="input-custom" required>
                  <option value="zabbix">Zabbix</option>
                  <option value="prometheus">Prometheus</option>
                  <option value="grafana">Grafana</option>
                  <option value="other">Outro</option>
                </select>
              </div>
            </div>

            <div>
              <label class="label-custom">URL *</label>
              <input 
                v-model="form.url" 
                type="url" 
                class="input-custom" 
                placeholder="https://zabbix.example.com"
                required
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="label-custom">Usuário</label>
                <input 
                  v-model="form.username" 
                  type="text" 
                  class="input-custom" 
                  autocomplete="off"
                />
              </div>

              <div>
                <label class="label-custom">Senha</label>
                <input 
                  v-model="form.password" 
                  type="password" 
                  class="input-custom" 
                  autocomplete="new-password"
                />
              </div>
            </div>

            <div>
              <label class="label-custom">Descrição</label>
              <textarea 
                v-model="form.description" 
                class="input-custom" 
                rows="2"
                placeholder="Descrição opcional do servidor"
              ></textarea>
            </div>

            <div>
              <label class="label-custom">Configurações Extras (JSON)</label>
              <textarea 
                v-model="form.extra_config" 
                class="input-custom font-mono text-xs" 
                rows="4"
                placeholder='{"timeout": 30, "verify_ssl": true}'
              ></textarea>
              <p v-if="jsonError" class="mt-1 text-xs text-red-600 dark:text-red-400">
                {{ jsonError }}
              </p>
            </div>

            <div class="flex items-center">
              <input 
                v-model="form.is_active" 
                type="checkbox" 
                id="is-active"
                class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <label for="is-active" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Servidor ativo
              </label>
            </div>

            <div class="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button type="button" @click="$emit('close')" class="btn-secondary">
                Cancelar
              </button>
              <button type="submit" :disabled="saving || !!jsonError" class="btn-primary">
                <svg v-if="saving" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {{ isEditing ? 'Atualizar' : 'Criar' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useServerManagement } from '@/composables/useServerManagement'

const props = defineProps({
  server: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close', 'save'])

const { validateExtraConfig } = useServerManagement()

// Local state
const form = ref({ ...props.server })
const saving = ref(false)
const jsonError = ref(null)

// Computed
const isEditing = computed(() => !!props.server?.id)

// Watch extra_config for JSON validation
watch(() => form.value.extra_config, (newVal) => {
  if (!newVal || newVal.trim() === '') {
    jsonError.value = null
    return
  }
  
  const result = validateExtraConfig(newVal)
  jsonError.value = result.error || null
})

// Methods
const handleSubmit = async () => {
  saving.value = true
  try {
    await emit('save', form.value)
  } finally {
    saving.value = false
  }
}
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
