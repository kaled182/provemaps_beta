<template>
  <div class="flex flex-col h-full bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
    
    <!-- Header com informações do cabo -->
    <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 flex flex-wrap justify-between items-center gap-4 bg-gray-50/50 dark:bg-gray-800">
      <div>
        <h3 class="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <i class="fas fa-bullseye text-indigo-500"></i>
          {{ cableName || 'Carregando estrutura...' }}
        </h3>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {{ profileName }} • {{ tubesCount }} Tubos • {{ totalFibers }} Fibras
        </p>
      </div>

      <!-- Legenda de Status -->
      <div class="flex items-center gap-4 text-xs text-gray-600 dark:text-gray-300">
        <div class="flex items-center gap-1">
          <span class="w-3 h-3 rounded-full bg-gray-400"></span> Apagada
        </div>
        <div class="flex items-center gap-1">
          <span class="w-3 h-3 rounded-full bg-green-500 ring-2 ring-green-200 dark:ring-green-900"></span> Iluminada
        </div>
        <div class="flex items-center gap-1">
          <span class="w-3 h-3 rounded-full border border-red-500 flex items-center justify-center text-[8px] text-red-500 font-bold relative">
            <span class="absolute inset-0 bg-red-500/20 rounded-full"></span>×
          </span> Rompida
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex-1 flex flex-col items-center justify-center min-h-[300px]">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600 mb-3"></div>
      <span class="text-sm text-gray-500">Carregando perfil físico...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="flex-1 flex flex-col items-center justify-center min-h-[300px] text-red-500">
      <i class="fas fa-exclamation-triangle text-3xl mb-2"></i>
      <p>Erro ao carregar estrutura do cabo.</p>
      <button @click="fetchStructure" class="mt-4 text-sm underline text-indigo-600">Tentar novamente</button>
    </div>

    <!-- Estrutura Visual (Tubos e Fibras) -->
    <div v-else class="flex-1 p-8 overflow-y-auto bg-gray-50 dark:bg-gray-900/50">
      
      <div class="flex flex-wrap justify-center gap-8 max-w-5xl mx-auto">
        
        <!-- Loop por cada tubo -->
        <div 
          v-for="tube in structure.tubes" 
          :key="tube.id"
          class="flex flex-col items-center group"
        >
          <!-- Círculo do Tubo (borda colorida ABNT) -->
          <div 
            class="relative rounded-full bg-white dark:bg-gray-800 shadow-md transition-transform duration-300 hover:scale-105 hover:shadow-lg border-[6px]"
            :class="[isSingleTube ? 'w-48 h-48 p-6' : 'w-32 h-32 p-3']"
            :style="{ borderColor: tube.color_hex }"
          >
            <!-- Badge do Tubo -->
            <div class="absolute -top-3 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-sm z-10 whitespace-nowrap border border-gray-600">
              TUBO {{ tube.number }} <span class="opacity-75 font-normal ml-1">({{ tube.color }})</span>
            </div>

            <!-- Grid de Fibras dentro do Tubo -->
            <div class="h-full w-full flex flex-wrap items-center justify-center content-center gap-2">
              <div 
                v-for="strand in tube.strands" 
                :key="strand.id"
                class="relative group/fiber"
                @click="handleStrandClick(strand)"
              >
                <!-- Bolinha da Fibra (cor ABNT de preenchimento) -->
                <div 
                  class="rounded-full shadow-sm cursor-pointer transition-all duration-200 border border-gray-300 dark:border-gray-600 relative overflow-hidden"
                  :class="[
                    isSingleTube ? 'w-6 h-6' : 'w-4 h-4',
                    getStrandClasses(strand)
                  ]"
                  :style="{ backgroundColor: strand.color_hex }"
                >
                  <!-- Indicador de Fibra Rompida -->
                  <div v-if="strand.status === 'broken'" class="absolute inset-0 flex items-center justify-center bg-black/20 text-white text-[10px]">
                    <i class="fas fa-times"></i>
                  </div>
                  
                  <!-- Número da Fibra (apenas em single tube para não poluir) -->
                  <span v-if="isSingleTube" class="absolute inset-0 flex items-center justify-center text-[8px] font-bold text-gray-800 invert mix-blend-difference opacity-50">
                    {{ strand.number }}
                  </span>
                </div>

                <!-- Tooltip com Detalhes da Fibra (hover) -->
                <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 bg-gray-900/95 backdrop-blur text-white text-xs rounded-lg py-2 px-3 opacity-0 group-hover/fiber:opacity-100 pointer-events-none transition-opacity z-50 shadow-xl border border-gray-700">
                  <div class="font-bold border-b border-gray-700 pb-1 mb-1 text-indigo-300">
                    FO {{ strand.number }} ({{ strand.color }})
                  </div>
                  <div class="space-y-1">
                    <p class="flex justify-between">
                      <span class="text-gray-400">Absoluto:</span> 
                      <span>#{{ strand.absolute_number }}</span>
                    </p>
                    <p class="flex justify-between">
                      <span class="text-gray-400">Status:</span> 
                      <span :class="getStatusColorText(strand.status)">{{ strand.status_display }}</span>
                    </p>
                    <div v-if="strand.connected_device_port" class="mt-2 pt-1 border-t border-gray-700">
                      <p class="text-[10px] text-gray-400 uppercase">Conectado a:</p>
                      <p class="truncate text-green-300">Porta ID {{ strand.connected_device_port }}</p>
                    </div>
                    <div v-if="strand.fused_to" class="mt-2 pt-1 border-t border-gray-700">
                      <p class="text-[10px] text-gray-400 uppercase">Fusionado com:</p>
                      <p class="truncate text-yellow-300">Fibra ID {{ strand.fused_to }}</p>
                    </div>
                    <div v-if="strand.attenuation_db" class="mt-2 pt-1 border-t border-gray-700">
                      <p class="flex justify-between">
                        <span class="text-gray-400">Atenuação:</span>
                        <span class="text-blue-300">{{ strand.attenuation_db }} dB</span>
                      </p>
                    </div>
                  </div>
                  <!-- Seta do Tooltip -->
                  <div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                </div>

              </div>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- Footer com Ações -->
    <div class="px-6 py-3 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 flex justify-end">
      <button 
        @click="handleExport"
        class="text-xs text-gray-500 hover:text-indigo-600 flex items-center gap-1 transition-colors"
      >
        <i class="fas fa-print"></i> Exportar Diagrama
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({
  cableId: { 
    type: [Number, String], 
    required: true 
  }
})

const emit = defineEmits(['select-fiber'])

const api = useApi()
const loading = ref(false)
const error = ref(false)
const structure = ref({ tubes: [] })

// Computeds para o Header
const cableName = computed(() => structure.value.name)
const profileName = computed(() => structure.value.profile_name || 'Perfil Personalizado')
const tubesCount = computed(() => structure.value.tubes?.length || 0)
const totalFibers = computed(() => {
  return structure.value.tubes?.reduce((acc, tube) => acc + (tube.strands?.length || 0), 0) || 0
})

const isSingleTube = computed(() => tubesCount.value === 1)

/**
 * Estilos dinâmicos baseados no status da fibra
 * - lit: brilho verde (fibra ativa)
 * - broken: opacidade reduzida + grayscale
 * - reserved: anel amarelo
 */
const getStrandClasses = (strand) => {
  const classes = []
  
  if (strand.status === 'lit') {
    // Efeito de brilho para iluminada
    classes.push('ring-2 ring-green-400 ring-offset-1 dark:ring-offset-gray-800 z-10')
  } else if (strand.status === 'broken') {
    classes.push('opacity-70 grayscale')
  } else if (strand.status === 'reserved') {
    classes.push('ring-2 ring-yellow-400 ring-offset-1 dark:ring-offset-gray-800')
  }
  
  return classes.join(' ')
}

const getStatusColorText = (status) => {
  switch(status) {
    case 'lit': return 'text-green-400'
    case 'broken': return 'text-red-400'
    case 'reserved': return 'text-yellow-400'
    default: return 'text-gray-400'
  }
}

/**
 * Busca estrutura física do cabo via API
 * Lazy Creation: Se o cabo tem profile mas não tem estrutura,
 * o backend gera automaticamente na primeira chamada
 */
const fetchStructure = async () => {
  if (!props.cableId) return
  
  loading.value = true
  error.value = false
  
  try {
    const response = await api.get(`/inventory/fiber-cables/${props.cableId}/structure/`)
    structure.value = response.data
  } catch (err) {
    console.error("Erro ao buscar estrutura do cabo:", err)
    error.value = true
  } finally {
    loading.value = false
  }
}

/**
 * Evento quando usuário clica em uma fibra
 * Pode ser usado para abrir modal de fusão ou conexão
 */
const handleStrandClick = (strand) => {
  console.log("Fibra selecionada:", strand)
  emit('select-fiber', strand)
}

/**
 * Exportar diagrama como imagem (feature futura)
 */
const handleExport = () => {
  console.log("Exportar diagrama - feature em desenvolvimento")
  // TODO: Implementar export via html2canvas ou similar
}

// Watchers e Lifecycle
watch(() => props.cableId, fetchStructure)

onMounted(() => {
  fetchStructure()
})
</script>

<style scoped>
/* Animações customizadas para fibras iluminadas */
@keyframes pulse-glow {
  0%, 100% {
    box-shadow: 0 0 8px rgba(34, 197, 94, 0.6);
  }
  50% {
    box-shadow: 0 0 16px rgba(34, 197, 94, 0.8);
  }
}

.ring-green-400 {
  animation: pulse-glow 2s ease-in-out infinite;
}
</style>
