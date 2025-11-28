<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
    <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-3xl overflow-hidden flex flex-col max-h-[90vh]">
      
      <!-- Header -->
      <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20">
        <div class="flex justify-between items-start">
          <div>
            <h3 class="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <i class="fas fa-link text-purple-500"></i>
              Conectar Cabo: <span class="text-purple-600 dark:text-purple-400">{{ cable?.name }}</span>
            </h3>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Defina a rota lógica entre dois sites (Momento 2: Routing)
            </p>
          </div>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
            <i class="fas fa-times text-xl"></i>
          </button>
        </div>
      </div>

      <!-- Content -->
      <div class="p-6 space-y-6 overflow-y-auto">
        
        <!-- Connection Visual -->
        <div class="flex items-center justify-between gap-4">
          <!-- Origem (Site A) -->
          <div class="flex-1">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              <i class="fas fa-map-marker-alt text-blue-500 mr-1"></i>
              Origem (Site A)
            </label>
            <select 
              v-model="connection.site_a" 
              class="w-full px-4 py-3 rounded-lg border-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 outline-none focus:border-blue-500 transition-all"
              :class="{ 'border-red-500': !connection.site_a && validationAttempted }"
            >
              <option value="" disabled>Selecione o site de origem...</option>
              <option v-for="site in sites" :key="site.id" :value="site.id">
                {{ site.name }}
              </option>
            </select>
            <p v-if="connection.site_a" class="text-xs text-gray-500 mt-2">
              <i class="fas fa-check-circle text-green-500 mr-1"></i>
              Site selecionado
            </p>
          </div>

          <!-- Connection Icon -->
          <div class="flex-shrink-0 mt-6">
            <div class="relative">
              <div class="w-16 h-1 bg-gradient-to-r from-blue-500 to-purple-500"></div>
              <div class="absolute top-1/2 left-1/2 -translate-y-1/2 -translate-x-1/2 bg-white dark:bg-gray-800 p-2 rounded-full border-2 border-purple-500">
                <i class="fas fa-grip-lines-vertical text-purple-500 text-xl"></i>
              </div>
            </div>
          </div>

          <!-- Destino (Site B) -->
          <div class="flex-1">
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              <i class="fas fa-map-marker-alt text-purple-500 mr-1"></i>
              Destino (Site B)
            </label>
            <select 
              v-model="connection.site_b" 
              class="w-full px-4 py-3 rounded-lg border-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 outline-none focus:border-purple-500 transition-all"
              :class="{ 'border-red-500': !connection.site_b && validationAttempted }"
            >
              <option value="" disabled>Selecione o site de destino...</option>
              <option v-for="site in sites" :key="site.id" :value="site.id">
                {{ site.name }}
              </option>
            </select>
            <p v-if="connection.site_b" class="text-xs text-gray-500 mt-2">
              <i class="fas fa-check-circle text-green-500 mr-1"></i>
              Site selecionado
            </p>
          </div>
        </div>

        <!-- Validation Error -->
        <div v-if="connection.site_a && connection.site_b && connection.site_a === connection.site_b" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg p-3 flex items-center gap-2">
          <i class="fas fa-exclamation-triangle text-red-500"></i>
          <p class="text-sm text-red-700 dark:text-red-400">
            Os sites de origem e destino não podem ser iguais.
          </p>
        </div>

        <!-- Optional: Estimated Length -->
        <div v-if="connection.site_a && connection.site_b && connection.site_a !== connection.site_b" class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg p-4">
          <div class="flex items-start gap-3">
            <i class="fas fa-info-circle text-green-500 text-xl mt-0.5"></i>
            <div>
              <h4 class="text-sm font-semibold text-green-900 dark:text-green-300 mb-1">Próximos Passos</h4>
              <ul class="text-xs text-green-700 dark:text-green-400 space-y-1 list-disc list-inside">
                <li>Após salvar a conexão lógica, desenhe a rota no mapa</li>
                <li>Ou importe um arquivo KML com o traçado real</li>
                <li>Conecte as pontas físicas (portas) quando estiverem disponíveis</li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Status Indicator -->
        <div class="bg-gray-50 dark:bg-gray-700/30 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
          <h4 class="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase mb-2">
            <i class="fas fa-network-wired mr-1"></i>
            Status da Conexão
          </h4>
          <div class="flex items-center gap-2">
            <div v-if="!connection.site_a && !connection.site_b" class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-gray-400"></div>
              <span class="text-sm text-gray-600 dark:text-gray-400">Flutuante (não conectado)</span>
            </div>
            <div v-else-if="connection.site_a && connection.site_b && connection.site_a !== connection.site_b" class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>
              <span class="text-sm text-green-700 dark:text-green-400 font-medium">Pronto para conectar</span>
            </div>
            <div v-else class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
              <span class="text-sm text-yellow-700 dark:text-yellow-400">Configuração incompleta</span>
            </div>
          </div>
        </div>

      </div>

      <!-- Footer -->
      <div class="px-6 py-4 bg-gray-50 dark:bg-gray-700/30 border-t border-gray-100 dark:border-gray-700 flex justify-between items-center">
        <button 
          @click="$emit('close')" 
          class="px-4 py-2 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
        >
          Cancelar
        </button>
        <button 
          @click="saveConnection" 
          :disabled="!isValid"
          class="px-6 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-all shadow-md font-medium"
        >
          <i class="fas fa-link"></i> 
          Salvar Rota Lógica
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  show: Boolean,
  cable: Object,
  sites: { type: Array, default: () => [] }
})

const emit = defineEmits(['close', 'connected'])

const connection = ref({
  site_a: '',
  site_b: ''
})

const validationAttempted = ref(false)

const isValid = computed(() => {
  return !!(
    connection.value.site_a && 
    connection.value.site_b && 
    connection.value.site_a !== connection.value.site_b
  )
})

watch(() => props.cable, (newCable) => {
  validationAttempted.value = false
  if (newCable) {
    connection.value = {
      site_a: newCable.site_a || '',
      site_b: newCable.site_b || ''
    }
  } else {
    connection.value = { site_a: '', site_b: '' }
  }
}, { immediate: true })

const saveConnection = () => {
  validationAttempted.value = true
  if (!isValid.value) return
  
  emit('connected', {
    cable_id: props.cable.id,
    site_a: connection.value.site_a,
    site_b: connection.value.site_b
  })
}
</script>
