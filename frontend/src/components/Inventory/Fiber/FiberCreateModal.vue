<template>
  <BaseModal
    :show="show"
    :title="isEditing ? 'Editar dados do cabo' : 'Novo cabo óptico'"
    subtitle="Especificações técnicas"
    :icon="PhPlugsConnected"
    :dirty="dirty"
    size="sm"
    flush
    @close="$emit('close')"
  >
    <div class="p-5 space-y-5">
      <p v-if="profilesError" class="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger" data-testid="profiles-error">
        Não foi possível carregar os perfis de construção: {{ profilesError }}
      </p>

      <!-- Nome / Identificador -->
      <div>
        <label class="block text-sm font-medium text-neutral-700 mb-1">
          Nome / Identificador <span class="text-danger">*</span>
        </label>
        <input 
          v-model="form.name" 
          type="text" 
          class="w-full px-3 py-2 rounded-lg border border-neutral-300 bg-surface focus:ring-2 focus:ring-primary-500 outline-none" 
          placeholder="Ex: CB-BKB-01"
          :class="{ 'border-danger': !form.name && validationAttempted }"
        />
        <p v-if="!form.name && validationAttempted" class="text-xs text-danger mt-1">Campo obrigatório</p>
      </div>

      <!-- Perfil de Construção -->
      <div>
        <label class="block text-sm font-medium text-neutral-700 mb-1">
          Perfil de Construção <span class="text-danger">*</span>
        </label>
        <select 
          v-model="form.profile_id" 
          class="w-full px-3 py-2 rounded-lg border border-neutral-300 bg-surface outline-none"
          :disabled="isEditing"
          :class="{ 'border-danger': !form.profile_id && validationAttempted }"
        >
          <option value="" disabled>Selecione a capacidade...</option>
          <option v-for="p in profiles" :key="p.id" :value="p.id">
            {{ p.name }} ({{ p.total_fibers }}FO)
          </option>
        </select>
        <p v-if="isEditing" class="text-xs text-warning mt-1">
          <i class="fas fa-lock mr-1"></i>
          O perfil físico não pode ser alterado após a criação.
        </p>
        <p v-if="!form.profile_id && validationAttempted" class="text-xs text-danger mt-1">Campo obrigatório</p>
      </div>

      <!-- Tipo de Uso + Status -->
      <!-- Status -->
      <div>
        <label class="block text-sm font-medium text-neutral-700 mb-1">Status</label>
        <select v-model="form.status" class="w-full px-3 py-2 rounded-lg border border-neutral-300 bg-surface outline-none">
          <option value="up">Ativo (Operational)</option>
          <option value="unknown">Planejado (Unknown)</option>
          <option value="down">Rompido (Down)</option>
          <option value="degraded">Degradado</option>
        </select>
      </div>

      <!-- Info Box: Próximo passo -->
      <div class="bg-info/10 border border-info/40 rounded-lg p-4">
        <div class="flex gap-3">
          <div class="text-info mt-0.5">
            <i class="fas fa-lightbulb text-xl"></i>
          </div>
          <div>
            <h4 class="text-sm font-semibold text-info mb-1">Próximo Passo</h4>
            <p class="text-xs text-info">
              Após criar o cabo, você poderá:
            </p>
            <ul class="text-xs text-info mt-2 space-y-1 list-disc list-inside">
              <li>Conectar a sites através do botão <strong>"Conectar"</strong></li>
              <li>Desenhar a rota no mapa</li>
              <li>Importar traçado via arquivo KML</li>
            </ul>
          </div>
        </div>
      </div>

    </div>

    <template #footer>
      <div class="flex justify-end gap-3">
        <button 
          @click="$emit('close')" 
          class="px-4 py-2 text-neutral-700 hover:bg-neutral-200 rounded-lg transition-colors"
        >
          Cancelar
        </button>
        <button 
          @click="save" 
          :disabled="!isValid"
          class="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-all shadow-sm"
        >
          <i class="fas fa-save"></i> 
          {{ isEditing ? 'Salvar Alterações' : 'Criar Cabo' }}
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { PhPlugsConnected } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({
  show: Boolean,
  cable: Object
})

const emit = defineEmits(['close', 'saved'])
const api = useApi()
const profiles = ref([])
const validationAttempted = ref(false)
const profilesError = ref('')
// EV-0068b: aviso ao fechar com alterações por guardar (BaseModal).
const initial = ref('')

const form = ref({
  name: '',
  profile_id: '',
    status: 'unknown'
})

const isEditing = computed(() => !!props.cable)
const dirty = computed(() => JSON.stringify(form.value) !== initial.value)

const isValid = computed(() => {
  return !!(form.value.name && form.value.profile_id)
})

onMounted(async () => {
  try {
    const response = await api.get('/api/v1/fiber-cables/profiles/')
    profiles.value = response
  } catch (e) {
    console.error('Erro ao carregar perfis:', e)
    profilesError.value = e?.message || 'erro desconhecido'
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
  initial.value = JSON.stringify(form.value)
}, { immediate: true })

const save = () => {
  validationAttempted.value = true
  if (!isValid.value) return
  emit('saved', form.value)
}
</script>
