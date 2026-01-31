<template>
  <div class="space-y-6 relative">
    <!-- Loading Overlay -->
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner"></div>
    </div>

    <!-- Redis Configuration -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Redis Cache</h3>
        <span v-if="config.REDIS_URL" class="badge-success">Configurado</span>
        <span v-else class="badge-gray">Não configurado</span>
      </div>
      
      <div class="space-y-4">
        <div>
          <label class="label-custom">Redis URL</label>
          <input 
            v-model="config.REDIS_URL" 
            type="text" 
            class="input-custom" 
            placeholder="redis://localhost:6379"
            autocomplete="off"
          />
        </div>

        <div class="flex gap-2">
          <button 
            @click="handleTestRedis" 
            :disabled="testingRedis"
            class="btn-secondary"
          >
            <svg v-if="testingRedis" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Testar Conexão
          </button>
          
          <span v-if="testResults.redis" class="inline-flex items-center px-3 py-1 rounded-md text-sm" 
                :class="testResults.redis.success ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'">
            {{ testResults.redis.message }}
          </span>
        </div>
      </div>
    </div>

    <!-- Database Configuration -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Banco de Dados (PostGIS)</h3>
        <span v-if="config.DB_HOST && config.DB_NAME" class="badge-success">Configurado</span>
        <span v-else class="badge-gray">Não configurado</span>
      </div>
      
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="label-custom">Host</label>
          <input 
            v-model="config.DB_HOST" 
            type="text" 
            class="input-custom" 
            placeholder="localhost"
            autocomplete="off"
          />
        </div>

        <div>
          <label class="label-custom">Porta</label>
          <input 
            v-model="config.DB_PORT" 
            type="text" 
            class="input-custom" 
            placeholder="5432"
            autocomplete="off"
          />
        </div>

        <div>
          <label class="label-custom">Nome do Banco</label>
          <input 
            v-model="config.DB_NAME" 
            type="text" 
            class="input-custom" 
            placeholder="provemaps"
            autocomplete="off"
          />
        </div>

        <div>
          <label class="label-custom">Usuário</label>
          <input 
            v-model="config.DB_USER" 
            type="text" 
            class="input-custom" 
            placeholder="postgres"
            autocomplete="off"
          />
        </div>

        <div class="col-span-2">
          <label class="label-custom">Senha</label>
          <input 
            v-model="config.DB_PASSWORD" 
            type="password" 
            class="input-custom" 
            autocomplete="off"
          />
        </div>
      </div>

      <div class="flex gap-2 mt-4">
        <button 
          @click="handleTestDatabase" 
          :disabled="testingDatabase"
          class="btn-secondary"
        >
          <svg v-if="testingDatabase" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Testar Conexão
        </button>
        
        <span v-if="testResults.database" class="inline-flex items-center px-3 py-1 rounded-md text-sm" 
              :class="testResults.database.success ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'">
          {{ testResults.database.message }}
        </span>
      </div>
    </div>

    <!-- Debug & Hosts Configuration -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Debug & Hosts</h3>
      
      <div class="space-y-4">
        <div class="flex items-center">
          <input 
            v-model="config.DEBUG" 
            type="checkbox" 
            id="debug-mode"
            class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
          />
          <label for="debug-mode" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
            Modo Debug (verbose logging)
          </label>
        </div>

        <div>
          <label class="label-custom">Allowed Hosts (separados por vírgula)</label>
          <input 
            v-model="config.ALLOWED_HOSTS" 
            type="text" 
            class="input-custom" 
            placeholder="localhost,127.0.0.1,example.com"
            autocomplete="off"
          />
        </div>

        <div>
          <label class="label-custom">CSRF Trusted Origins</label>
          <input 
            v-model="config.CSRF_TRUSTED_ORIGINS" 
            type="text" 
            class="input-custom" 
            placeholder="https://example.com,https://app.example.com"
            autocomplete="off"
          />
        </div>
      </div>
    </div>

    <!-- Service Restart Commands -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div class="flex items-start justify-between mb-4">
        <div>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Reinício automático</h3>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">Informe os comandos que devem ser executados após salvar as configurações (.env).</p>
        </div>
      </div>

      <div class="space-y-3">
        <div>
          <label class="label-custom">Comandos de reinício</label>
          <textarea
            v-model="config.SERVICE_RESTART_COMMANDS"
            rows="3"
            class="input-custom resize-y"
            placeholder="docker compose -f docker/docker-compose.yml restart web; docker compose -f docker/docker-compose.yml restart celery"
          ></textarea>
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400">
          Separe múltiplos comandos usando ponto e vírgula (;). Esses comandos são executados em background sempre que as configurações forem salvas.
        </p>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="flex justify-end gap-3">
      <button @click="handleReset" class="btn-secondary">
        Resetar
      </button>
      <button @click="handleSave" :disabled="saving || !isValid" class="btn-primary">
        <svg v-if="saving" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Salvar Configurações
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useSystemConfig } from '@/composables/useSystemConfig'

// Composable
const {
  config,
  testResults,
  loading,
  isValid,
  testingRedis,
  testingDatabase,
  loadSystemConfig,
  saveSystemConfig,
  testRedis,
  testDatabase,
  clearTestResults,
  resetForm,
} = useSystemConfig()

// Local state
const saving = ref(false)

// Methods
const handleTestRedis = async () => {
  await testRedis()
}

const handleTestDatabase = async () => {
  await testDatabase()
}

const handleSave = async () => {
  saving.value = true
  try {
    const success = await saveSystemConfig()
    if (success) {
      clearTestResults()
    }
  } finally {
    saving.value = false
  }
}

const handleReset = () => {
  if (confirm('Resetar formulário? As alterações não salvas serão perdidas.')) {
    resetForm()
    clearTestResults()
  }
}

// Lifecycle
onMounted(async () => {
  console.log('[SystemParamsTab] Mounting component, loading config...')
  await loadSystemConfig()
  console.log('[SystemParamsTab] Config loaded:', config)
})
</script>

<style scoped>
.label-custom {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.375rem;
}

.input-custom {
  width: 100%;
  border-radius: 0.375rem;
  border: 1px solid #d1d5db;
  background-color: #ffffff;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: #111827;
  transition: all 0.2s;
}

.input-custom::placeholder {
  color: #9ca3af;
}

.input-custom:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  background-color: #3b82f6;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #ffffff;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.2s;
  border: none;
  cursor: pointer;
}

.btn-primary:hover:not(:disabled) {
  background-color: #2563eb;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  background-color: #ffffff;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #111827;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  border: 1px solid #d1d5db;
  transition: all 0.2s;
  cursor: pointer;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #f9fafb;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.badge-success {
  display: inline-flex;
  padding: 0.125rem 0.625rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  background-color: #d1fae5;
  color: #065f46;
}

.badge-gray {
  display: inline-flex;
  padding: 0.125rem 0.625rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  background-color: #f3f4f6;
  color: #4b5563;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  background-color: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  border-radius: 0.5rem;
}

.loading-spinner {
  width: 2rem;
  height: 2rem;
  border: 4px solid #bfdbfe;
  border-top-color: #3b82f6;
  border-radius: 9999px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>

<style>
/* Dark mode styles - não-scoped para garantir aplicação */
html.dark .input-custom,
.dark .input-custom {
  border-color: #374151;
  background-color: #1f2937 !important;
  color: #e5e7eb;
}

html.dark .input-custom::placeholder,
.dark .input-custom::placeholder {
  color: #6b7280;
}

html.dark .input-custom:focus,
.dark .input-custom:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

html.dark .label-custom,
.dark .label-custom {
  color: #e5e7eb;
}

html.dark .btn-secondary,
.dark .btn-secondary {
  background-color: #374151;
  color: #f3f4f6;
  border-color: #4b5563;
}

html.dark .btn-secondary:hover:not(:disabled),
.dark .btn-secondary:hover:not(:disabled) {
  background-color: #4b5563;
}

html.dark .badge-success,
.dark .badge-success {
  background-color: rgba(16, 185, 129, 0.3);
  color: #6ee7b7;
}

html.dark .badge-gray,
.dark .badge-gray {
  background-color: #374151;
  color: #9ca3af;
}

html.dark .loading-overlay,
.dark .loading-overlay {
  background-color: rgba(17, 24, 39, 0.8);
}

html.dark .loading-spinner,
.dark .loading-spinner {
  border-color: #1e3a8a;
  border-top-color: #60a5fa;
}
</style>
