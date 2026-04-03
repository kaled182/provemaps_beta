<template>
  <div class="bg-gray-900 rounded-lg border border-gray-700 mb-3 overflow-hidden shadow-sm">
    <div class="bg-gray-800 px-3 py-2 flex justify-between items-center cursor-pointer hover:bg-gray-750 transition-colors" @click="expanded = !expanded">
      <div class="flex items-center gap-2 overflow-hidden">
        <i class="fas fa-chevron-right text-[10px] text-gray-500 transition-transform" :class="{'rotate-90': expanded}"></i>
        
        <div class="shrink-0" :title="segmentType === 'IN' ? 'Segmento de Entrada' : segmentType === 'OUT' ? 'Segmento de Saída' : 'Segmento Local'">
          <span v-if="isIncoming" class="w-5 h-5 rounded-full bg-green-900/50 border border-green-500 flex items-center justify-center text-green-400 text-[10px]">
            <i class="fas fa-arrow-right"></i>
          </span>
          <span v-else class="w-5 h-5 rounded-full bg-orange-900/50 border border-orange-500 flex items-center justify-center text-orange-400 text-[10px]">
            <i class="fas fa-arrow-left"></i>
          </span>
        </div>

        <div class="min-w-0">
          <div class="font-bold text-sm text-gray-200 truncate">{{ cable.direction_label || cable.label || cable.name }}</div>
          <div class="text-[10px] text-gray-500 truncate">{{ cable.profile_name || 'Sem perfil' }}</div>
        </div>
      </div>
    </div>

    <div v-if="expanded" class="p-2 space-y-2 bg-black/20 border-t border-gray-700">
      <div v-for="tube in cable.tubes" :key="tube.id" class="flex items-stretch gap-2">
        
        <div 
          class="w-6 flex flex-col items-center justify-center rounded-l-sm border-l-4 bg-gray-800 shrink-0"
          :style="{ borderLeftColor: tube.color_hex }"
          :title="`Tubo ${tube.number}: ${tube.color}`"
        >
          <span class="text-[9px] font-bold text-gray-400">T{{ tube.number }}</span>
        </div>

        <div class="flex flex-wrap gap-1.5 flex-1 py-1 px-2 bg-gray-800/50 rounded-r-sm items-center">
          <div 
            v-for="strand in tube.strands" 
            :key="`${strand.id}-${segmentVirtualId}`"
            class="w-5 h-5 rounded-full cursor-pointer border-2 transition-all duration-150 relative group"
            :class="[
              isSelected(strand) ? 'border-white scale-110 z-10 shadow-[0_0_8px_rgba(255,255,255,0.5)]' : 'border-transparent hover:border-gray-500',
              strand.is_fused_here && !isSelected(strand) ? 'opacity-60 cursor-not-allowed' : '',
              isDuplicate(strand) ? 'ring-1 ring-gray-700 opacity-70' : '',
              (!strand.is_fused_here && (strand.fused_elsewhere || strand.fused_on_other_segment) && !isDuplicate(strand)) ? 'outline-dashed' : ''
            ]"
            :style="{ backgroundColor: strand.color_hex }"
            @click="onClick(strand)"
          >
            <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block bg-black text-white text-[9px] px-1.5 py-0.5 rounded whitespace-nowrap z-20">
              <template v-if="isDuplicate(strand)">
                FO {{ strand.number }} - Espelhada na outra face
              </template>
              <template v-else-if="strand.is_fused_here">
                FO {{ strand.number }} - Fusionada aqui
              </template>
              <template v-else-if="strand.fused_elsewhere">
                FO {{ strand.number }} - {{ strand.fusion_ceo ? ('Fusionada em ' + strand.fusion_ceo) : 'Fusionada em outra caixa' }}
              </template>
              <template v-else-if="strand.fused_on_other_segment">
                FO {{ strand.number }} - Fusionada na face
                <span v-if="strand.blocked_segment_direction === 'IN'">de entrada</span>
                <span v-else-if="strand.blocked_segment_direction === 'OUT'">de saída</span>
                <span v-else>oposta</span>
              </template>
              <template v-else>
                FO {{ strand.number }} - {{ strand.status || 'Livre' }}
              </template>
            </div>

            <div v-if="strand.is_fused_here" class="absolute inset-0 flex items-center justify-center">
              <div class="w-1.5 h-1.5 bg-orange-500 rounded-full shadow-[0_0_4px_rgba(251,146,60,0.8)]"></div>
            </div>
            <div v-else-if="strand.fused_elsewhere || (strand.fused_on_other_segment && !isDuplicate(strand))" class="absolute inset-0 pointer-events-none">
              <div class="absolute inset-0 border-2 border-gray-500 border-dashed rounded-full"></div>
            </div>
          </div>
        </div>
        
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
const props = defineProps({
  cable: {
    type: Object,
    required: true
  },
  selected: {
    type: Object,
    default: null
  }
})
const emit = defineEmits(['select'])

const expanded = ref(true)

const segmentType = computed(() => {
  const cable = props.cable || {}
  const virtualId = cable.virtual_id || ''
  if (virtualId.includes('PREV_')) return 'IN'
  if (virtualId.includes('NEXT_')) return 'OUT'
  if (virtualId.includes('_ATT_')) return 'LOCAL'
  return cable.direction || 'UNKNOWN'
})

const isIncoming = computed(() => segmentType.value === 'IN')

const segmentVirtualId = computed(() => {
  const cable = props.cable || {}
  return cable.virtual_id || String(cable.id || '')
})

const isSelected = (strand) => {
  if (!props.selected) return false
  if (props.selected.fiberId !== strand.id) return false
  if (!props.selected.virtualId) return true
  return props.selected.virtualId === segmentVirtualId.value
}

const isDuplicate = (strand) => strand?.is_primary_render === false

const onClick = (strand) => {
  if (strand.is_fused_here) return
  emit('select', {
    fiberId: strand.id,
    virtualId: segmentVirtualId.value,
    strand
  })
}
</script>
