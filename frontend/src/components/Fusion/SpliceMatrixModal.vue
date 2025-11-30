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

        <!-- Left Sidebar: Entrada (Cabos Source) -->
        <div class="w-80 bg-gray-900 border-r border-gray-700 flex flex-col shrink-0">
          <div class="p-3 text-[10px] font-bold uppercase text-gray-500 bg-black/20 flex justify-between">
            <span>Entradas</span>
            <i class="fas fa-arrow-right"></i>
          </div>
          <div class="flex-1 overflow-y-auto p-3 custom-scrollbar">
            <CableStrippedView 
              v-for="cable in cablesEntrada" 
              :key="cable.attachment_id || cable.id" 
              :cable="cable"
              :selected-id="selection.a"
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
                <div class="flex-1 text-right text-[10px] pr-3 truncate">
                  <template v-if="getSlotData(slot)">
                    <span class="block text-gray-300 font-medium">{{ getSlotData(slot).fiber_a.cable }}</span>
                    <span class="block text-gray-500">{{ getSlotData(slot).fiber_a.name }}</span>
                  </template>
                  <span v-else class="text-gray-700 italic opacity-0 group-hover:opacity-100 transition-opacity">Vazio</span>
                </div>

                <!-- Slot Badge -->
                <div class="w-10 h-6 shrink-0 rounded-full flex items-center justify-center text-[9px] font-bold border transition-all duration-300"
                     :class="getSlotData(slot) 
                        ? 'bg-green-500/20 border-green-500 text-green-400 shadow-[0_0_10px_rgba(34,197,94,0.2)]' 
                        : 'bg-gray-800 border-gray-600 text-gray-600 border-dashed group-hover:border-gray-400 group-hover:text-gray-300'"
                >
                  {{ slot }}
                </div>

                <!-- Fiber B (Right) -->
                <div class="flex-1 text-left text-[10px] pl-3 truncate">
                  <template v-if="getSlotData(slot)">
                    <span class="block text-gray-300 font-medium">{{ getSlotData(slot).fiber_b.cable }}</span>
                    <span class="block text-gray-500">{{ getSlotData(slot).fiber_b.name }}</span>
                  </template>
                  <button 
                    v-if="getSlotData(slot)"
                    @click.stop="removeFusion(slot)"
                    class="absolute right-2 top-1/2 -translate-y-1/2 text-red-500 opacity-0 group-hover:opacity-100 hover:text-red-400 p-1"
                    title="Desfazer Fusão"
                  >
                    <i class="fas fa-times"></i>
                  </button>
                </div>

              </div>
            </div>
          </div>
        </div>

        <!-- Right Sidebar: Saída (Cabos Destination) -->
        <div class="w-80 bg-gray-900 border-l border-gray-700 flex flex-col shrink-0">
          <div class="p-3 text-[10px] font-bold uppercase text-gray-500 bg-black/20 flex justify-between">
            <i class="fas fa-arrow-right"></i>
            <span>Saídas</span>
          </div>
          <div class="flex-1 overflow-y-auto p-3 custom-scrollbar">
             <CableStrippedView 
              v-for="cable in cablesSaida" 
              :key="cable.attachment_id || (cable.id + '_saida')" 
              :cable="cable"
              :selected-id="selection.b"
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
const selection = reactive({ a: null, b: null, aCable: null, bCable: null })

// Computed: Separar cabos por port_type
const cablesEntrada = computed(() => {
  // Se não há nenhum attachment, mostrar todos os cabos
  const hasAttachments = cables.value.some(c => c.attachment_id)
  if (!hasAttachments) {
    return cables.value
  }
  // Entrada: oval (principal/passagem) ou owner (cabo proprietário)
  return cables.value.filter(c => c.port_type === 'oval' || c.port_type === 'owner')
})

const cablesSaida = computed(() => {
  // Se não há nenhum attachment, mostrar todos os cabos
  const hasAttachments = cables.value.some(c => c.attachment_id)
  if (!hasAttachments) {
    return cables.value
  }
  // Saída: round (derivação)
  const roundCables = cables.value.filter(c => c.port_type === 'round')
  // Se não houver cabos round, mostrar os mesmos da entrada (cenário de reparo)
  return roundCables.length > 0 ? roundCables : cables.value.filter(c => c.port_type === 'oval')
})

const resolveCableId = (fiberId) => {
  if (!fiberId) return null
  for (const cable of cables.value) {
    for (const tube of cable.tubes || []) {
      for (const strand of tube.strands || []) {
        if (strand.id === fiberId) return cable.id
      }
    }
  }
  return null
}

// Extrai o real_id de uma fibra (remove sufixo _attachmentId)
const getRealFiberId = (virtualId) => {
  if (!virtualId) return null
  
  // Buscar nos cabos pelo ID virtual
  for (const cable of cables.value) {
    for (const tube of cable.tubes || []) {
      for (const strand of tube.strands || []) {
        if (strand.id === virtualId) {
          return strand.real_id || virtualId  // Usar real_id se existir
        }
      }
    }
  }
  return virtualId  // Fallback
}

const canFuse = computed(() => {
  // Apenas verifica se duas fibras foram selecionadas
  // Permite: mesma cor, mesmo cabo, refusão - sem restrições
  return !!(selection.a && selection.b)
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
    
    if (!cablesData) {
      throw new Error('Resposta vazia da API de contexto')
    }
    
    cables.value = cablesData || []
    
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

const selectFiber = (side, fiberId) => {
  if (selection[side] === fiberId) {
    selection[side] = null
    if (side === 'a') selection.aCable = null
    else selection.bCable = null
    return
  }
  selection[side] = fiberId
  const cableId = resolveCableId(fiberId)
  if (side === 'a') selection.aCable = cableId
  else selection.bCable = cableId
  console.debug('[SpliceMatrixModal] seleção', side, 'fiber', fiberId, 'cable', cableId)
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
    // Extrair IDs reais (remover sufixo virtual _attachmentId)
    const realFiberA = getRealFiberId(selection.a)
    const realFiberB = getRealFiberId(selection.b)
    
    console.debug('[SpliceMatrixModal] Fusão:', {
      virtual_a: selection.a,
      virtual_b: selection.b,
      real_a: realFiberA,
      real_b: realFiberB
    })
    
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
    selection.aCable = null
    selection.bCable = null
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
    await api.delete(`/api/v1/inventory/fusions/${slotData.fiber_a.id}/`)
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
