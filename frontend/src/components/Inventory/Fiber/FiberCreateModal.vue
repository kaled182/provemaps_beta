<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
    <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
      
      <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20">
        <div>
          <h3 class="text-lg font-bold text-gray-900 dark:text-white">
            {{ isEditing ? 'Editar Dados do Cabo' : 'Novo Cabo Óptico' }}
          </h3>
          <p class="text-xs text-gray-500 dark:text-gray-400">Especificações técnicas do equipamento</p>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
          <i class="fas fa-times text-xl"></i>
        </button>
      </div>

      <div class="p-6 space-y-5 overflow-y-auto">
        
        <!-- Nome / Identificador -->
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Nome / Identificador <span class="text-red-500">*</span>
          </label>
          <input 
            v-model="form.name" 
            type="text" 
            class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 focus:ring-2 focus:ring-indigo-500 outline-none" 
            placeholder="Ex: CB-BKB-01"
            :class="{ 'border-red-500': !form.name && validationAttempted }"
          />
          <p v-if="!form.name && validationAttempted" class="text-xs text-red-500 mt-1">Campo obrigatório</p>
        </div>

        <!-- Perfil de Construção -->
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Perfil de Construção <span class="text-red-500">*</span>
          </label>
          <select 
            v-model="form.profile_id" 
            class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 outline-none"
            :disabled="isEditing"
            :class="{ 'border-red-500': !form.profile_id && validationAttempted }"
          >
            <option value="" disabled>Selecione a capacidade...</option>
            <option v-for="p in profiles" :key="p.id" :value="p.id">
              {{ p.name }} ({{ p.total_fibers }}FO)
            </option>
          </select>
          <p v-if="isEditing" class="text-xs text-orange-500 mt-1">
            <i class="fas fa-lock mr-1"></i>
            O perfil físico não pode ser alterado após a criação.
          </p>
          <p v-if="!form.profile_id && validationAttempted" class="text-xs text-red-500 mt-1">Campo obrigatório</p>
        </div>

        <!-- Tipo de Uso + Status -->
        <!-- Status -->
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Status</label>
          <select v-model="form.status" class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 outline-none">
            <option value="up">Ativo (Operational)</option>
            <option value="unknown">Planejado (Unknown)</option>
            <option value="down">Rompido (Down)</option>
            <option value="degraded">Degradado</option>
          </select>
        </div>

        <!-- Info Box: Próximo passo -->
        <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-4">
          <div class="flex gap-3">
            <div class="text-blue-500 mt-0.5">
              <i class="fas fa-lightbulb text-xl"></i>
            </div>
            <div>
              <h4 class="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-1">Próximo Passo</h4>
              <p class="text-xs text-blue-700 dark:text-blue-400">
                Após criar o cabo, você poderá:
              </p>
              <ul class="text-xs text-blue-600 dark:text-blue-400 mt-2 space-y-1 list-disc list-inside">
                <li>Conectar a sites através do botão <strong>"Conectar"</strong></li>
                <li>Desenhar a rota no mapa</li>
                <li>Importar traçado via arquivo KML</li>
              </ul>
            </div>
          </div>
        </div>

      </div>

      <!-- Footer -->
      <div class="px-6 py-4 bg-gray-50 dark:bg-gray-700/30 border-t border-gray-100 dark:border-gray-700 flex justify-end gap-3">
        <button 
          @click="$emit('close')" 
          class="px-4 py-2 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
        >
          Cancelar
        </button>
        <button 
          @click="save" 
          :disabled="!isValid"
          class="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-all shadow-sm"
        >
          <i class="fas fa-save"></i> 
          {{ isEditing ? 'Salvar Alterações' : 'Criar Cabo' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({
  show: Boolean,
  cable: Object
})

const emit = defineEmits(['close', 'saved'])
const api = useApi()
const profiles = ref([])
const validationAttempted = ref(false)

const form = ref({
  name: '',
  profile_id: '',
    status: 'unknown'
})

const isEditing = computed(() => !!props.cable)

const isValid = computed(() => {
  return !!(form.value.name && form.value.profile_id)
})

onMounted(async () => {
  try {
    const response = await api.get('/api/v1/fiber-cables/profiles/')
    profiles.value = response
    console.log('Perfis carregados:', profiles.value)
  } catch(e) { 
    console.error('Erro ao carregar perfis:', e)
    alert('Erro ao carregar perfis de construção. Verifique o console.')
  }
})

watch(() => props.cable, (newVal) => {
  validationAttempted.value = false
  if (newVal) {
    form.value = {
      id: newVal.id,
      name: newVal.name || '',
      profile_id: newVal.profile || '',
        status: newVal.status || 'unknown'
    }
  } else {
    form.value = { 
      name: '', 
      profile_id: '', 
        status: 'unknown'
    }
  }
}, { immediate: true })

const save = () => {
  validationAttempted.value = true
  if (!isValid.value) return
  emit('saved', form.value)
}
</script>
