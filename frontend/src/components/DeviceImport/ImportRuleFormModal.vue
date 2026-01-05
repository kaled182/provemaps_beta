<template>
  <teleport to="body">
    <transition name="modal">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-[60] overflow-y-auto"
        @click.self="closeModal"
      >
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black bg-opacity-50"></div>

        <!-- Modal Container -->
        <div class="flex min-h-screen items-center justify-center p-4">
          <div
            class="relative w-full max-w-2xl app-surface rounded-lg"
            @click.stop
          >
            <!-- Header -->
            <div class="flex items-center justify-between p-6 border-b app-divider">
              <h3 class="text-xl font-bold app-text-primary">
                {{ isEditMode ? 'Editar Regra' : 'Nova Regra' }}
              </h3>
              <button @click="closeModal" class="app-text-tertiary close-icon-btn">
                <i class="fas fa-times"></i>
              </button>
            </div>

            <!-- Form -->
            <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
              <!-- Pattern -->
              <div>
                <label class="block text-sm font-medium app-text-secondary mb-1">
                  Padrão Regex *
                </label>
                <input
                  v-model="formData.pattern"
                  type="text"
                  required
                  class="w-full px-3 py-2 font-mono text-sm app-input"
                  placeholder="^OLT.*|^SWITCH-HUAWEI.*"
                />
                <p class="text-xs app-text-tertiary mt-1">
                  <i class="fas fa-info-circle mr-1"></i>
                  Regex case-insensitive. Use ^ para início, $ para fim, .* para qualquer caractere.
                </p>
                <p v-if="patternError" class="text-xs app-text-tertiary mt-1">
                  <i class="fas fa-exclamation-circle mr-1"></i>
                  {{ patternError }}
                </p>
              </div>

              <!-- Description -->
              <div>
                <label class="block text-sm font-medium app-text-secondary mb-1">
                  Descrição
                </label>
                <input
                  v-model="formData.description"
                  type="text"
                  class="w-full px-3 py-2 app-input"
                  placeholder="Ex: OLTs Huawei da rede FTTx"
                />
              </div>

              <!-- Category -->
              <div>
                <label class="block text-sm font-medium app-text-secondary mb-1">
                  Categoria *
                </label>
                <select
                  v-model="formData.category"
                  required
                  class="w-full px-3 py-2 app-input"
                >
                  <option value="">Selecione...</option>
                  <option value="backbone">Backbone / IP</option>
                  <option value="gpon">GPON / FTTx</option>
                  <option value="dwdm">DWDM / Óptico</option>
                  <option value="access">Acesso / Clientes</option>
                </select>
              </div>

              <!-- Group -->
              <div>
                <label class="block text-sm font-medium app-text-secondary mb-1">
                  Grupo de Monitoramento
                </label>
                <select
                  v-model="formData.group"
                  class="w-full px-3 py-2 app-input"
                >
                  <option :value="null">(nenhum)</option>
                  <option
                    v-for="group in deviceGroups"
                    :key="group.id"
                    :value="group.id"
                  >
                    {{ group.name }}
                  </option>
                </select>
                <p class="text-xs app-text-tertiary mt-1">
                  Grupo do Zabbix a ser associado automaticamente
                </p>
              </div>

              <!-- Priority -->
              <div>
                <label class="block text-sm font-medium app-text-secondary mb-1">
                  Prioridade *
                </label>
                <input
                  v-model.number="formData.priority"
                  type="number"
                  min="0"
                  required
                  class="w-full px-3 py-2 app-input"
                />
                <p class="text-xs app-text-tertiary mt-1">
                  Menor número = maior prioridade (0 = primeira regra aplicada)
                </p>
              </div>

              <!-- Active -->
              <div class="flex items-center">
                <input
                  v-model="formData.is_active"
                  type="checkbox"
                  id="is_active"
                  class="h-4 w-4 rounded"
                  style="accent-color: var(--accent-info);"
                />
                <label for="is_active" class="ml-2 block text-sm app-text-secondary">
                  Regra ativa (aplicar durante importação)
                </label>
              </div>
            </form>

            <!-- Footer -->
            <div class="flex justify-end space-x-3 p-6 border-t app-divider app-surface-muted">
              <button
                @click="closeModal"
                type="button"
                class="px-4 py-2 rounded-lg app-btn"
              >
                Cancelar
              </button>
              <button
                @click="handleSubmit"
                type="submit"
                class="px-4 py-2 rounded-lg app-btn-primary"
              >
                <i class="fas fa-save mr-2"></i>
                {{ isEditMode ? 'Salvar' : 'Criar' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useApi } from '@/composables/useApi';

const props = defineProps({
  modelValue: Boolean,
  rule: Object,
  deviceGroups: Array,
});

const emit = defineEmits(['update:modelValue', 'save']);

const api = useApi();

// Estado
const formData = ref({
  pattern: '',
  description: '',
  category: '',
  group: null,
  priority: 0,
  is_active: true,
});

const patternError = ref('');

// Computed
const isEditMode = computed(() => !!props.rule?.id);

// Métodos
const resetForm = () => {
  formData.value = {
    pattern: '',
    description: '',
    category: '',
    group: null,
    priority: 0,
    is_active: true,
  };
  patternError.value = '';
};

const closeModal = () => {
  emit('update:modelValue', false);
  resetForm();
};

// Watchers
watch(
  () => props.rule,
  (newRule) => {
    if (newRule) {
      formData.value = {
        pattern: newRule.pattern || '',
        description: newRule.description || '',
        category: newRule.category || '',
        group: newRule.group || null,
        priority: newRule.priority || 0,
        is_active: newRule.is_active ?? true,
      };
    } else {
      resetForm();
    }
  },
  { immediate: true }
);

const validatePattern = async () => {
  patternError.value = '';
  
  if (!formData.value.pattern) {
    return false;
  }

  try {
    await api.post('/api/v1/import-rules/test_pattern/', {
      pattern: formData.value.pattern,
      samples: ['TEST'],
    });
    return true;
  } catch (error) {
    patternError.value = error.response?.data?.error || 'Padrão regex inválido';
    return false;
  }
};

const handleSubmit = async () => {
  // Validar regex
  const isValid = await validatePattern();
  if (!isValid) return;

  try {
    if (isEditMode.value) {
      await api.patch(`/api/v1/import-rules/${props.rule.id}/`, formData.value);
    } else {
      await api.post('/api/v1/import-rules/', formData.value);
    }

    emit('save');
    closeModal();
  } catch (error) {
    console.error('Erro ao salvar regra:', error);
    alert('Erro ao salvar regra: ' + (error.response?.data?.error || error.message));
  }
};
</script>

<style scoped>
.close-icon-btn:hover {
  color: var(--text-primary);
}
</style>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
