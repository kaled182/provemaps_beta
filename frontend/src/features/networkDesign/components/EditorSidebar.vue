<template>
  <div class="h-full flex flex-col bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 shadow-xl z-20 w-80 lg:w-96 transition-all duration-300">
    
    <!-- Header com info do cabo -->
    <div class="p-5 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
      <!-- Alerta de rompimento (se houver segmentos BROKEN) -->
      <div v-if="hasBrokenSegments" class="mb-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <div class="flex items-center gap-2 text-red-700 dark:text-red-400">
          <i class="fas fa-exclamation-triangle text-lg"></i>
          <div>
            <p class="text-sm font-bold">CABO ROMPIDO</p>
            <p class="text-xs">{{ brokenSegmentCount }} segmento(s) com rompimento</p>
          </div>
        </div>
      </div>
      
      <div class="flex justify-between items-start mb-2">
        <span class="px-2 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300">
          {{ cable.type || 'Backbone' }}
        </span>
        <span :class="['w-2 h-2 rounded-full', statusColor]"></span>
      </div>
      
      <h2 class="text-lg font-bold text-gray-900 dark:text-white leading-tight mb-1">
        {{ cable.name }}
      </h2>
      <p class="text-xs text-gray-500 font-mono">{{ cable.profile_name || '48FO Padrão' }}</p>
    </div>

    <!-- Métricas em grid -->
    <div class="grid grid-cols-2 gap-px bg-gray-200 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-700">
      <div class="bg-white dark:bg-gray-800 p-4 flex flex-col items-center justify-center hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
        <span class="text-xs text-gray-400 dark:text-gray-500 uppercase font-bold mb-1">Extensão</span>
        <span class="text-lg font-mono font-bold text-gray-900 dark:text-white">
          {{ formatLength(cable.length) }}
        </span>
      </div>
      <div class="bg-white dark:bg-gray-800 p-4 flex flex-col items-center justify-center hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
        <span class="text-xs text-gray-400 dark:text-gray-500 uppercase font-bold mb-1">Atenuação</span>
        <span class="text-lg font-mono font-bold text-gray-900 dark:text-white">
          {{ calculateLoss(cable.length) }}dB
        </span>
      </div>
    </div>

    <!-- Timeline de elementos -->
    <div class="flex-1 overflow-y-auto p-4">
      <h3 class="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-4 flex items-center gap-2">
        <i class="fas fa-stream"></i> Elementos de Rede
      </h3>

      <div class="relative pl-4 border-l-2 border-gray-200 dark:border-gray-600 space-y-6">
        <!-- Site A (Origem) -->
        <div class="relative">
          <div class="absolute -left-[21px] bg-blue-500 h-3 w-3 rounded-full ring-4 ring-white dark:ring-gray-800"></div>
          <p class="text-sm font-bold text-gray-900 dark:text-white">{{ cable.site_a_name || 'Início Indefinido' }}</p>
          <p class="text-xs text-gray-500">Origem</p>
        </div>

        <!-- Pontos de infraestrutura -->
        <div v-if="infrastructurePoints.length === 0" class="py-8 text-center">
          <p class="text-xs text-gray-400 dark:text-gray-500 italic">Nenhuma caixa ou reserva adicionada.</p>
          <button class="mt-2 text-xs text-indigo-600 dark:text-indigo-400 hover:underline">
            + Adicionar com botão direito no mapa
          </button>
        </div>
        
        <div v-for="point in infrastructurePoints" :key="point.id" class="relative group">
          <div :class="[
            'absolute -left-[21px] h-3 w-3 rounded-full ring-4 ring-white dark:ring-gray-800',
            point.type === 'slack' ? 'bg-blue-500' : 
            point.type === 'splice_box' ? 'bg-orange-500' :
            point.type === 'splitter_box' ? 'bg-purple-500' : 'bg-gray-500'
          ]"></div>
          <div class="flex items-start justify-between gap-2">
            <div class="flex-1 min-w-0">
              <p class="text-sm font-bold text-gray-900 dark:text-white truncate">
                {{ point.name || point.type_display }}
              </p>
              <p class="text-xs text-gray-500 dark:text-gray-400">
                {{ formatDistance(point.distance_from_origin) }}
              </p>
            </div>
            <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button 
                @click="$emit('edit-infrastructure', point)"
                class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400"
                title="Editar"
              >
                <i class="fas fa-edit text-xs"></i>
              </button>
              <button 
                @click="$emit('delete-infrastructure', point)"
                class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400"
                title="Excluir"
              >
                <i class="fas fa-trash text-xs"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- Site B (Destino) -->
        <div class="relative">
          <div class="absolute -left-[21px] bg-indigo-500 h-3 w-3 rounded-full ring-4 ring-white dark:ring-gray-800"></div>
          <p class="text-sm font-bold text-gray-900 dark:text-white">{{ cable.site_b_name || 'Fim Indefinido' }}</p>
          <p class="text-xs text-gray-500 dark:text-gray-400">Destino</p>
        </div>
      </div>
    </div>

    <!-- Footer com botão de salvar -->
    <div class="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
      <button 
        @click="$emit('save')" 
        :disabled="!isDirty"
        class="w-full py-3 px-4 rounded-xl text-sm font-bold shadow-sm transition-all duration-200 flex items-center justify-center gap-2"
        :class="isDirty ? 'bg-indigo-600 hover:bg-indigo-700 text-white hover:shadow-md hover:-translate-y-0.5' : 'bg-gray-300 text-gray-500 cursor-not-allowed'"
      >
        <i class="fas fa-save"></i> 
        {{ isDirty ? 'Salvar Alterações' : 'Sem Alterações' }}
      </button>
    </div>

  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  cable: { type: Object, required: true },
  isDirty: { type: Boolean, default: false }
})

defineEmits(['save', 'edit-infrastructure', 'delete-infrastructure'])

const infrastructurePoints = computed(() => {
  return props.cable.infrastructure_points || []
})

const statusColor = computed(() => {
  // Se houver segmentos BROKEN, forçar vermelho
  if (hasBrokenSegments.value) return 'bg-red-500 ring-2 ring-red-300 dark:ring-red-700';
  
  switch(props.cable.status) {
    case 'active': return 'bg-green-500';
    case 'planned': return 'bg-blue-500';
    case 'cut': return 'bg-red-500';
    default: return 'bg-gray-400';
  }
})

const hasBrokenSegments = computed(() => {
  if (!props.cable.segments) return false;
  return props.cable.segments.some(seg => 
    seg.status === 'broken' || seg.status === 'BROKEN'
  );
})

const brokenSegmentCount = computed(() => {
  if (!props.cable.segments) return 0;
  return props.cable.segments.filter(seg => 
    seg.status === 'broken' || seg.status === 'BROKEN'
  ).length;
})

const formatLength = (m) => {
  if (!m) return '0m'
  return m >= 1000 ? `${(m/1000).toFixed(2)}km` : `${Math.round(m)}m`
}

const formatDistance = (meters) => {
  if (!meters && meters !== 0) return '?'
  return meters >= 1000 ? `${(meters/1000).toFixed(2)}km` : `${Math.round(meters)}m`
}

const calculateLoss = (m) => {
  if (!m) return '0.0'
  // Fórmula: 0.35dB/km (atenuação típica fibra monomodo) + 0.2dB margem
  return ((m/1000) * 0.35 + 0.2).toFixed(2)
}
</script>
