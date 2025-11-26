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
            class="relative w-full max-w-2xl bg-white dark:bg-gray-800 rounded-lg shadow-xl"
            @click.stop
          >
            <!-- Header -->
            <div class="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <h3 class="text-xl font-bold text-gray-900 dark:text-white">
                {{ isEditMode ? 'Editar Regra' : 'Nova Regra' }}
              </h3>
              <button @click="closeModal" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                <i class="fas fa-times"></i>
              </button>
            </div>

            <!-- Form -->
            <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
              <!-- Pattern -->
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Padrão Regex *
                </label>
                <input
                  v-model="formData.pattern"
                  type="text"
                  required
                  class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="^OLT.*|^SWITCH-HUAWEI.*"
                />
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  <i class="fas fa-info-circle mr-1"></i>
                  Regex case-insensitive. Use ^ para início, $ para fim, .* para qualquer caractere.
                </p>
                <p v-if="patternError" class="text-xs text-red-600 dark:text-red-400 mt-1">
                  <i class="fas fa-exclamation-circle mr-1"></i>
                  {{ patternError }}
                </p>
              </div>

              <!-- Description -->
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Descrição
                </label>
                <input
                  v-model="formData.description"
                  type="text"
                  class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="Ex: OLTs Huawei da rede FTTx"
                />
              </div>

              <!-- Category -->
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Categoria *
                </label>
                <select
                  v-model="formData.category"
                  required
                  class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
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
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Grupo de Monitoramento
                </label>
                <select
                  v-model="formData.group"
                  class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
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
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Grupo do Zabbix a ser associado automaticamente
                </p>
              </div>

              <!-- Priority -->
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Prioridade *
                </label>
                <input
                  v-model.number="formData.priority"
                  type="number"
                  min="0"
                  required
                  class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Menor número = maior prioridade (0 = primeira regra aplicada)
                </p>
              </div>

              <!-- Active -->
              <div class="flex items-center">
                <input
                  v-model="formData.is_active"
                  type="checkbox"
                  id="is_active"
                  class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                />
                <label for="is_active" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                  Regra ativa (aplicar durante importação)
                </label>
              </div>
            </form>

            <!-- Footer -->
            <div class="flex justify-end space-x-3 p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
              <button
                @click="closeModal"
                type="button"
                class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                Cancelar
              </button>
              <button
                @click="handleSubmit"
                type="submit"
                class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
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
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
