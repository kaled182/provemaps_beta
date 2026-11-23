<template>
  <BaseModal
    :show="show"
    title="Conectar cabo"
    :subtitle="cable?.name || ''"
    :icon="PhLink"
    :dirty="dirty"
    size="md"
    flush
    @close="$emit('close')"
  >
    <div class="p-5 space-y-5">
      <p class="text-xs text-neutral-500">Defina a rota lógica entre dois sites.</p>

      <!-- Connection Visual -->
      <div class="flex items-center justify-between gap-4">
        <!-- Origem (Site A) -->
        <div class="flex-1">
          <label class="block text-sm font-semibold text-neutral-700 mb-2">
            <i class="fas fa-map-marker-alt text-info mr-1"></i>
            Origem (Site A)
          </label>
          <select 
            v-model="connection.site_a" 
            class="w-full px-4 py-3 rounded-lg border-2 border-neutral-300 bg-surface outline-none focus:border-info transition-all"
            :class="{ 'border-danger': !connection.site_a && validationAttempted }"
          >
            <option value="" disabled>Selecione o site de origem...</option>
            <option v-for="site in sites" :key="site.id" :value="site.id">
              {{ site.name }}
            </option>
          </select>
          <p v-if="connection.site_a" class="text-xs text-neutral-500 mt-2">
            <i class="fas fa-check-circle text-success mr-1"></i>
            Site selecionado
          </p>
        </div>

        <!-- Connection Icon -->
        <div class="flex-shrink-0 mt-6">
          <div class="relative">
            <div class="w-16 h-1 bg-gradient-to-r from-blue-500 to-primary-500"></div>
            <div class="absolute top-1/2 left-1/2 -translate-y-1/2 -translate-x-1/2 bg-surface p-2 rounded-full border-2 border-primary-500">
              <i class="fas fa-grip-lines-vertical text-primary-500 text-xl"></i>
            </div>
          </div>
        </div>

        <!-- Destino (Site B) -->
        <div class="flex-1">
          <label class="block text-sm font-semibold text-neutral-700 mb-2">
            <i class="fas fa-map-marker-alt text-primary-500 mr-1"></i>
            Destino (Site B)
          </label>
          <select 
            v-model="connection.site_b" 
            class="w-full px-4 py-3 rounded-lg border-2 border-neutral-300 bg-surface outline-none focus:border-primary-500 transition-all"
            :class="{ 'border-danger': !connection.site_b && validationAttempted }"
          >
            <option value="" disabled>Selecione o site de destino...</option>
            <option v-for="site in sites" :key="site.id" :value="site.id">
              {{ site.name }}
            </option>
          </select>
          <p v-if="connection.site_b" class="text-xs text-neutral-500 mt-2">
            <i class="fas fa-check-circle text-success mr-1"></i>
            Site selecionado
          </p>
        </div>
      </div>

      <!-- Validation Error -->
      <div v-if="connection.site_a && connection.site_b && connection.site_a === connection.site_b" class="bg-danger/10 border border-danger/40 rounded-lg p-3 flex items-center gap-2">
        <i class="fas fa-exclamation-triangle text-danger"></i>
        <p class="text-sm text-danger">
          Os sites de origem e destino não podem ser iguais.
        </p>
      </div>

      <!-- Optional: Estimated Length -->
      <div v-if="connection.site_a && connection.site_b && connection.site_a !== connection.site_b" class="bg-success/10 border border-success/40 rounded-lg p-4">
        <div class="flex items-start gap-3">
          <i class="fas fa-info-circle text-success text-xl mt-0.5"></i>
          <div>
            <h4 class="text-sm font-semibold text-success mb-1">Próximos Passos</h4>
            <ul class="text-xs text-success space-y-1 list-disc list-inside">
              <li>Após salvar a conexão lógica, desenhe a rota no mapa</li>
              <li>Ou importe um arquivo KML com o traçado real</li>
              <li>Conecte as pontas físicas (portas) quando estiverem disponíveis</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Status Indicator -->
      <div class="bg-neutral-50 rounded-lg p-4 border border-neutral-200">
        <h4 class="text-xs font-bold text-neutral-700 uppercase mb-2">
          <i class="fas fa-network-wired mr-1"></i>
          Status da Conexão
        </h4>
        <div class="flex items-center gap-2">
          <div v-if="!connection.site_a && !connection.site_b" class="flex items-center gap-2">
            <div class="w-3 h-3 rounded-full bg-neutral-400"></div>
            <span class="text-sm text-neutral-600">Flutuante (não conectado)</span>
          </div>
          <div v-else-if="connection.site_a && connection.site_b && connection.site_a !== connection.site_b" class="flex items-center gap-2">
            <div class="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>
            <span class="text-sm text-success font-medium">Pronto para conectar</span>
          </div>
          <div v-else class="flex items-center gap-2">
            <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
            <span class="text-sm text-warning">Configuração incompleta</span>
          </div>
        </div>
      </div>

    </div>

    <template #footer>
      <div class="flex items-center justify-between">
        <button 
          @click="$emit('close')" 
          class="px-4 py-2 text-neutral-700 hover:bg-neutral-200 rounded-lg transition-colors"
        >
          Cancelar
        </button>
        <button 
          @click="saveConnection" 
          :disabled="!isValid"
          class="px-6 py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-all shadow-md font-medium"
        >
          <i class="fas fa-link"></i> 
          Salvar Rota Lógica
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { PhLink } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'

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
// EV-0068b: aviso ao fechar com alterações por guardar (BaseModal).
const initial = ref('')
const dirty = computed(() => JSON.stringify(connection.value) !== initial.value)

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
  initial.value = JSON.stringify(connection.value)
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
