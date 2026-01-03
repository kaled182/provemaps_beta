<template>
  <!-- Modal controlado por prop show do pai -->
  <div v-if="show" class="fixed inset-0 z-[2000] flex items-center justify-center bg-black/90 backdrop-blur-sm p-4">
    <div class="bg-gray-900 w-full max-w-[95vw] h-[90vh] rounded-xl flex flex-col overflow-hidden shadow-2xl border border-gray-700 ring-1 ring-gray-800">
      
      <!-- Header -->
      <div class="px-6 py-4 bg-gray-800 border-b border-gray-700 flex justify-between items-center shrink-0">
        <div class="flex items-center gap-4">
          <div class="w-10 h-10 rounded bg-orange-500/10 flex items-center justify-center text-orange-500 border border-orange-500/30">
            <i class="fas fa-network-wired text-xl"></i>
          </div>
          <div>
            <h2 class="text-xl font-bold text-white flex items-center gap-2">
              {{ boxName }}
              <span class="text-[10px] bg-gray-700 px-2 py-0.5 rounded text-gray-300 font-normal">
                {{ template.manufacturer || 'Fibracem' }} {{ template.name || 'SVT' }}
              </span>
            </h2>
            <p class="text-xs text-gray-400 mt-0.5 flex gap-3">
              <span><i class="fas fa-layer-group mr-1"></i> {{ template.max_trays }} Bandejas</span>
              <span><i class="fas fa-bolt mr-1"></i> {{ template.splices_per_tray }} Fusões/Bandeja</span>
            </p>
          </div>
        </div>
        
        <div class="flex items-center gap-4">
          <div class="text-[10px] text-gray-500 flex gap-3 border-r border-gray-700 pr-4 mr-2">
            <span class="flex items-center gap-1"><div class="w-2 h-2 rounded-full bg-green-500"></div> Ocupado</span>
            <span class="flex items-center gap-1"><div class="w-2 h-2 rounded-full border border-gray-500 border-dashed"></div> Livre</span>
          </div>
          <button @click="$emit('close')" class="text-gray-400 hover:text-white transition-colors p-2 hover:bg-gray-700 rounded-lg">
            <i class="fas fa-times text-xl"></i>
          </button>
        </div>
      </div>

      <!-- Tabs (Bandejas) -->
      <div class="flex bg-gray-800 border-b border-gray-700 overflow-x-auto shrink-0 custom-scrollbar">
        <button 
          v-for="t in (template.max_trays || 1)" 
          :key="t"
          @click="activeTray = t"
          class="px-6 py-3 text-xs font-bold uppercase tracking-wider transition-all border-r border-gray-700 relative group min-w-[120px]"
          :class="activeTray === t ? 'bg-gray-900 text-white' : 'text-gray-500 hover:bg-gray-700 hover:text-gray-300'"
        >
          <span v-if="activeTray === t" class="absolute top-0 left-0 right-0 h-0.5 bg-orange-500"></span>
          Bandeja {{ t }}
          
          <span class="ml-2 px-1.5 py-0.5 rounded-full text-[9px]"
                :class="getTrayUsage(t) >= template.splices_per_tray ? 'bg-red-900/50 text-red-400' : 'bg-gray-900 text-gray-500'">
            {{ getTrayUsage(t) }}/{{ template.splices_per_tray }}
          </span>
        </button>
      </div>

      <!-- Main Content -->
      <div class="flex-1 flex overflow-hidden relative">
        
        <!-- Loading Overlay -->
        <div v-if="loading" class="absolute inset-0 bg-gray-900/80 z-50 flex items-center justify-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
        </div>

        <!-- Left Sidebar: Direção A (Cabos Source) -->
        <div class="w-80 bg-gray-900 border-r border-gray-700 flex flex-col shrink-0">
          <div class="p-3 text-[10px] font-bold uppercase text-gray-500 bg-black/20 flex justify-between">
            <span>{{ nomeDirecaoA }}</span>
            <i class="fas fa-arrow-right"></i>
          </div>
          <div class="flex-1 overflow-y-auto p-3 custom-scrollbar">
            <CableStrippedView 
              v-for="segment in cablesDirecaoA" 
              :key="segment.virtual_id || `${segment.id}-IN`"
              :cable="segment"
              :selected="selection.a"
              @select="selectFiber('a', $event)"
            />
          </div>
        </div>

        <!-- Center: Splice Matrix -->
        <div class="flex-1 bg-gray-900 p-8 overflow-y-auto relative custom-scrollbar flex flex-col items-center">
          
          <!-- Botão de Fusão (quando duas fibras selecionadas) -->
          <div v-if="selection.a && selection.b" class="sticky top-0 z-20 mb-6 animate-in slide-in-from-top duration-300">
            <button 
              @click="fuseNextAvailable"
              class="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white px-8 py-3 rounded-full shadow-lg shadow-green-900/20 font-bold text-sm flex items-center gap-3 transform active:scale-95 transition-all"
            >
              <i class="fas fa-link"></i> 
              <span>Realizar Fusão (Próximo Slot)</span>
            </button>
          </div>

          <!-- Matriz de Slots -->
          <div class="w-full max-w-4xl bg-gray-800 rounded-2xl border border-gray-700 p-6 shadow-xl relative">
            <div class="absolute -top-3 left-1/2 -translate-x-1/2 bg-gray-700 text-gray-300 px-3 py-1 rounded-full text-xs font-bold border border-gray-600 shadow-sm">
              BANDEJA {{ activeTray }}
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-x-16 gap-y-2 mt-4">
              <div v-for="slot in template.splices_per_tray" :key="slot" 
                   class="group relative flex items-center justify-between py-1.5 border-b border-gray-700/50 last:border-0 hover:bg-white/5 rounded px-2 transition-colors cursor-pointer"
                   @click="selectSlotForFuse(slot)"
              >
                
                <!-- Fiber A (Left) -->
                <div class="flex-1 flex justify-end items-center gap-2 text-right pr-3 overflow-hidden">
                  <template v-if="getSlotData(slot)?.fiber_a">
                    <div
                      class="min-w-0"
                      :title="formatTooltip(getSlotData(slot).fiber_a)"
                    >
                      <span class="block text-gray-300 font-bold text-[10px] truncate leading-tight">
                        {{ formatDirection(getSlotData(slot).fiber_a) }}
                      </span>
                      <span class="block text-gray-500 text-[10px] truncate uppercase">
                        {{ formatColor(getSlotData(slot).fiber_a) }}
                        <template v-if="getSlotData(slot).fiber_a?.fiber_code">
                          • {{ getSlotData(slot).fiber_a.fiber_code }}
                        </template>
                      </span>
                    </div>
                    <div class="w-3 h-3 rounded-full shrink-0 border border-gray-600 shadow-sm"
                         :style="{ backgroundColor: getSlotData(slot).fiber_a.color_hex }"></div>
                  </template>
                  <span v-else class="text-gray-700 italic text-[10px] opacity-0 group-hover:opacity-100 transition-opacity">Vazio</span>
                </div>

                <!-- Slot Badge -->
                <div class="w-8 h-5 shrink-0 rounded-full flex items-center justify-center text-[9px] font-bold border transition-all duration-300"
                     :class="getSlotData(slot) 
                        ? 'bg-green-500/20 border-green-500 text-green-400 shadow-[0_0_10px_rgba(34,197,94,0.2)]' 
                        : 'bg-gray-800 border-gray-600 text-gray-600 border-dashed group-hover:border-gray-400 group-hover:text-gray-300'"
                >
                  {{ slot }}
                </div>

                <!-- Fiber B (Right) -->
                <div class="flex-1 flex items-center gap-2 text-left pl-3 overflow-hidden relative">
                  <template v-if="getSlotData(slot)?.fiber_b">
                    <div class="w-3 h-3 rounded-full shrink-0 border border-gray-600 shadow-sm"
                         :style="{ backgroundColor: getSlotData(slot).fiber_b.color_hex }"></div>
                    <div
                      class="min-w-0"
                      :title="formatTooltip(getSlotData(slot).fiber_b)"
                    >
                      <span class="block text-gray-300 font-bold text-[10px] truncate leading-tight">
                        {{ formatDirection(getSlotData(slot).fiber_b) }}
                      </span>
                      <span class="block text-gray-500 text-[10px] truncate uppercase">
                        {{ formatColor(getSlotData(slot).fiber_b) }}
                        <template v-if="getSlotData(slot).fiber_b?.fiber_code">
                          • {{ getSlotData(slot).fiber_b.fiber_code }}
                        </template>
                      </span>
                    </div>

                    <button
                      @click.stop="removeFusion(slot)"
                      class="absolute right-0 top-1/2 -translate-y-1/2 text-red-500 hover:text-red-300 bg-gray-900 p-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity shadow-md border border-gray-700"
                      title="Desfazer Fusão"
                    >
                      <i class="fas fa-times"></i>
                    </button>
                  </template>
                </div>

              </div>
            </div>
          </div>
        </div>

        <!-- Right Sidebar: Direção B (Cabos Destination) -->
        <div class="w-80 bg-gray-900 border-l border-gray-700 flex flex-col shrink-0">
          <div class="p-3 text-[10px] font-bold uppercase text-gray-500 bg-black/20 flex justify-between">
            <i class="fas fa-arrow-right"></i>
            <span>{{ nomeDirecaoB }}</span>
          </div>
          <div class="flex-1 overflow-y-auto p-3 custom-scrollbar">
            <CableStrippedView 
              v-for="segment in cablesDirecaoB" 
              :key="segment.virtual_id || `${segment.id}-OUT`" 
              :cable="segment"
              :selected="selection.b"
              @select="selectFiber('b', $event)"
            />
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useApi } from '@/composables/useApi'
import CableStrippedView from './CableStrippedView.vue'

const props = defineProps(['show', 'infraPoint'])
console.debug('[SpliceMatrixModal] props.show recebido:', props.show)
const emit = defineEmits(['close'])
const api = useApi()

const loading = ref(false)
const activeTray = ref(1)
const matrix = ref({})
const template = reactive({ max_trays: 1, splices_per_tray: 24, manufacturer: 'Fibracem', name: 'SVT' })
const boxName = ref('CEO')
const cables = ref([])
const selection = reactive({
  a: null,
  b: null,
})

const segmentKind = (segment) => {
  if (!segment) return 'UNKNOWN'
  const virtualId = segment.virtual_id || ''
  
  // Debug: log cada segmento
  console.log('[SpliceMatrixModal] Classificando segmento:', {
    id: segment.id,
    virtual_id: virtualId,
    direction: segment.direction,
    label: segment.label
  })
  
  // Priorizar virtual_id para identificar PREV/NEXT
  if (virtualId.includes('PREV_')) {
    console.log('  → Classificado como IN (PREV)')
    return 'IN'
  }
  if (virtualId.includes('NEXT_')) {
    console.log('  → Classificado como OUT (NEXT)')
    return 'OUT'
  }
  if (virtualId.includes('_ATT_')) {
    console.log('  → Classificado como LOCAL (ATT)')
    return 'LOCAL'
  }
  
  // Fallback para campo direction do backend
  const direction = segment.direction || ''
  if (direction === 'IN') {
    console.log('  → Classificado como IN (direction)')
    return 'IN'
  }
  if (direction === 'OUT') {
    console.log('  → Classificado como OUT (direction)')
    return 'OUT'
  }
  if (direction === 'LOCAL') {
    console.log('  → Classificado como LOCAL (direction)')
    return 'LOCAL'
  }
  
  console.log('  → Classificado como UNKNOWN')
  return 'UNKNOWN'
}

const cablesDirecaoA = computed(() => {
  const incoming = cables.value.filter((segment) => segmentKind(segment) === 'IN')
  console.log('[SpliceMatrixModal] cablesDirecaoA:', incoming.length, 'segmentos')
  return incoming
})

const cablesDirecaoB = computed(() => {
  const outgoing = cables.value.filter((segment) => segmentKind(segment) === 'OUT')
  const local = cables.value.filter((segment) => segmentKind(segment) === 'LOCAL')
  const unknown = cables.value.filter((segment) => segmentKind(segment) === 'UNKNOWN')
  
  console.log('[SpliceMatrixModal] cablesDirecaoB:', {
    outgoing: outgoing.length,
    local: local.length,
    unknown: unknown.length
  })
  
  // Combinar todos os não-IN
  return [...outgoing, ...local, ...unknown]
})

const nomeDirecaoA = computed(() => {
  if (cablesDirecaoA.value.length === 0) return 'IN'
  const first = cablesDirecaoA.value[0]
  const kind = segmentKind(first)
  if (kind === 'IN') {
    // Extrair nome da label se possível
    return first.label?.includes('[Vindo de') ? 'IN' : 'Entrada'
  }
  return 'Direção A'
})

const nomeDirecaoB = computed(() => {
  if (cablesDirecaoB.value.length === 0) return 'OUT'
  const first = cablesDirecaoB.value[0]
  const kind = segmentKind(first)
  if (kind === 'OUT') return 'OUT'
  if (kind === 'LOCAL') return 'Local'
  return 'Direção B'
})

const segmentVirtualId = (segment) => segment?.virtual_id || String(segment?.id || '')

const findStrand = (fiberId, virtualId = null) => {
  for (const segment of cables.value) {
    if (virtualId && segmentVirtualId(segment) !== virtualId) {
      continue
    }
    for (const tube of segment.tubes || []) {
      for (const strand of tube.strands || []) {
        if (strand.id === fiberId) {
          return { strand, segment }
        }
      }
    }
  }
  return null
}

const buildSelectionEntry = (payload) => {
  if (!payload || !payload.fiberId) return null
  const virtualId = payload.virtualId || null
  return {
    fiberId: payload.fiberId,
    virtualId,
  }
}

const getRealFiberId = (selectionEntry) => {
  if (!selectionEntry || !selectionEntry.fiberId) return null
  const found = findStrand(selectionEntry.fiberId, selectionEntry.virtualId)
  if (found?.strand?.real_id) return found.strand.real_id
  return selectionEntry.fiberId
}

const formatDirection = (fiber) => {
  if (!fiber) return '—'
  return fiber.direction || fiber.direction_label || fiber.cable || '—'
}

const formatColor = (fiber) => {
  if (!fiber) return '—'
  const label = fiber.color_name || fiber.color
  return label ? String(label).toUpperCase() : '—'
}

const formatTooltip = (fiber) => {
  if (!fiber) return ''
  const parts = []
  if (fiber.cable) parts.push(fiber.cable)
  if (fiber.direction_label && fiber.direction_label !== fiber.cable) {
    parts.push(fiber.direction_label)
  }
  if (fiber.fiber_code) parts.push(fiber.fiber_code)
  return parts.join(' • ')
}

const canFuse = computed(() => {
  // Permite qualquer combinação desde que ambas as seleções existam
  return Boolean(selection.a?.fiberId && selection.b?.fiberId)
})

// Computed: Contar uso de bandeja
const getTrayUsage = (trayNum) => {
  let count = 0
  for (let i = 1; i <= (template.splices_per_tray || 24); i++) {
    if (matrix.value[`${trayNum}-${i}`]) count++
  }
  return count
}

const loadData = async () => {
  if (!props.infraPoint?.id) return
  loading.value = true
  
  try {
    // 1. Busca a Matriz de Ocupação
    const matrixData = await api.get(`/api/v1/inventory/splice-boxes/${props.infraPoint.id}/matrix/`)
    
    // useApi retorna diretamente o JSON, não precisa de .data
    if (!matrixData) {
      throw new Error('Resposta vazia da API')
    }
    
    matrix.value = matrixData.matrix || {}
    
    const tmpl = matrixData.template || {}
    template.max_trays = tmpl.max_trays || 1
    template.splices_per_tray = tmpl.splices_per_tray || 24
    template.manufacturer = tmpl.manufacturer || 'Fibracem'
    template.name = tmpl.name || 'SVT'
    
    boxName.value = matrixData.box_name || 'CEO'
    
    // 2. Busca o Contexto (Cabos)
    const cablesData = await api.get(`/api/v1/inventory/splice-boxes/${props.infraPoint.id}/context/`)
    
    console.log('[SpliceMatrixModal] Raw cables response:', cablesData)
    
    if (!cablesData || !Array.isArray(cablesData)) {
      console.error('[SpliceMatrixModal] Invalid cables data:', cablesData)
      throw new Error('Resposta inválida da API de contexto (não é array)')
    }
    
    cables.value = cablesData

    if (selection.a && !findStrand(selection.a.fiberId, selection.a.virtualId)) {
      selection.a = null
    }
    if (selection.b && !findStrand(selection.b.fiberId, selection.b.virtualId)) {
      selection.b = null
    }
    
  } catch (error) {
    console.error('[SpliceMatrixModal] Erro ao carregar dados:', error)
    console.error('[SpliceMatrixModal] infraPoint:', props.infraPoint)
    alert('Erro ao carregar dados da CEO: ' + (error.message || 'Erro desconhecido'))
  } finally {
    loading.value = false
  }
}

const getSlotData = (slot) => {
  return matrix.value[`${activeTray.value}-${slot}`]
}

const selectFiber = (side, payload) => {
  const normalized = buildSelectionEntry(payload)
  const current = selection[side]
  if (
    current &&
    normalized &&
    current.fiberId === normalized.fiberId &&
    (current.virtualId || null) === (normalized.virtualId || null)
  ) {
    selection[side] = null
    return
  }
  selection[side] = normalized
}

const fuseNextAvailable = async () => {
  // Acha o primeiro slot vazio nesta bandeja
  if (!canFuse.value) {
    alert('Selecione duas fibras diferentes para fusionar.')
    return
  }
  let slot = 1
  while (matrix.value[`${activeTray.value}-${slot}`] && slot <= (template.splices_per_tray || 24)) slot++
  
  if (slot > (template.splices_per_tray || 24)) {
    alert('Esta bandeja está cheia! Selecione outra aba.')
    return
  }
  
  performFusion(slot)
}

const selectSlotForFuse = (slot) => {
  if (getSlotData(slot)) return // Já ocupado
  if (canFuse.value) performFusion(slot)
}

const performFusion = async (slot) => {
  loading.value = true
  if (!canFuse.value) {
    alert('Fusão inválida: selecione duas fibras diferentes.')
    return
  }
  try {
    const realFiberA = getRealFiberId(selection.a)
    const realFiberB = getRealFiberId(selection.b)

    await api.post('/api/v1/inventory/fusions/', {
      infrastructure_id: props.infraPoint.id,
      tray: activeTray.value,
      slot: slot,
      fiber_a: realFiberA,
      fiber_b: realFiberB
    })
    
    // Reset e Reload
    selection.a = null
    selection.b = null
    await loadData()
    
  } catch (e) {
    alert('Erro: ' + (e.response?.data?.detail || 'Falha na fusão'))
  } finally {
    loading.value = false
  }
}

const removeFusion = async (slot) => {
  const slotData = getSlotData(slot)
  if (!slotData) return
  
  if (!confirm('Desfazer esta fusão?')) return
  
  loading.value = true
  try {
    // Usar DELETE /fusions/<fiber_id>/
    const params = new URLSearchParams({
      fusion_id: String(slotData.fusion_id),
      infrastructure_id: String(props.infraPoint.id)
    })
    await api.delete(`/api/v1/inventory/fusions/${slotData.fiber_a.id}/?${params.toString()}`)
    await loadData()
  } catch (e) {
    alert('Erro ao remover fusão: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

// Carrega inicial ao montar
onMounted(() => {
  console.debug('[SpliceMatrixModal] onMounted - infraPoint:', props.infraPoint?.id)
  loadData()
})

// Recarrega quando muda a infraPoint (abrindo modal para outra CEO)
watch(() => props.infraPoint?.id, (newVal, oldVal) => {
  if (!newVal || newVal === oldVal) return
  console.debug('[SpliceMatrixModal] infraPoint.id changed', oldVal, '→', newVal)
  // Reset seleção antes de recarregar
  selection.a = null
  selection.b = null
  nextTick(() => loadData())
})

// (Opcional) futuro: reagir se bandejas instaladas forem alteradas externamente
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 6px; height: 6px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #4b5563; border-radius: 3px; }
.custom-scrollbar::-webkit-scrollbar-track { background: #1f2937; }

@keyframes slide-in-from-top {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-in {
  animation-fill-mode: both;
}

.slide-in-from-top {
  animation-name: slide-in-from-top;
}

.duration-300 {
  animation-duration: 300ms;
}
</style>
