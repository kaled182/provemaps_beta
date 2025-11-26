<template>
  <teleport to="body">
    <transition name="modal">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 overflow-y-auto"
        @click.self="closeModal"
      >
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity"></div>

        <!-- Modal Container -->
        <div class="flex min-h-screen items-center justify-center p-4">
          <div
            class="relative w-full max-w-5xl bg-white dark:bg-gray-800 rounded-lg shadow-xl transform transition-all"
            @click.stop
          >
            <!-- Header -->
            <div class="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
                <i class="fas fa-robot mr-2 text-indigo-600 dark:text-indigo-400"></i>
                Regras de Auto-Associação
              </h2>
              <button
                @click="closeModal"
                class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              >
                <i class="fas fa-times text-xl"></i>
              </button>
            </div>

            <!-- Content -->
            <div class="p-6">
              <!-- Add Rule Button -->
              <div class="mb-4 flex justify-between items-center">
                <p class="text-sm text-gray-600 dark:text-gray-400">
                  Regras aplicadas automaticamente durante importação do Zabbix.
                  <br>
                  <span class="font-medium">Ordem:</span> prioridade crescente (0 = maior prioridade).
                </p>
                <button
                  @click="addNewRule"
                  class="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-sm"
                >
                  <i class="fas fa-plus mr-2"></i>
                  Nova Regra
                </button>
              </div>

              <!-- Rules Table -->
              <div class="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm">
                <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead class="bg-gray-50 dark:bg-gray-900">
                    <tr>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Prioridade
                      </th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Padrão Regex
                      </th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Categoria
                      </th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Grupo
                      </th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Status
                      </th>
                      <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Ações
                      </th>
                    </tr>
                  </thead>
                  <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    <tr
                      v-for="rule in sortedRules"
                      :key="rule.id"
                      :class="{ 'opacity-50': !rule.is_active }"
                    >
                      <td class="px-4 py-3 whitespace-nowrap">
                        <div class="flex items-center space-x-2">
                          <button
                            @click="moveRuleUp(rule)"
                            :disabled="isFirstRule(rule)"
                            class="text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                            title="Mover para cima"
                          >
                            <i class="fas fa-arrow-up"></i>
                          </button>
                          <span class="font-mono text-sm font-semibold text-gray-900 dark:text-gray-100">{{ rule.priority }}</span>
                          <button
                            @click="moveRuleDown(rule)"
                            :disabled="isLastRule(rule)"
                            class="text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                            title="Mover para baixo"
                          >
                            <i class="fas fa-arrow-down"></i>
                          </button>
                        </div>
                      </td>
                      <td class="px-4 py-3">
                        <code class="text-sm bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded font-mono text-gray-900 dark:text-gray-100">
                          {{ rule.pattern }}
                        </code>
                        <p v-if="rule.description" class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {{ rule.description }}
                        </p>
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap">
                        <span :class="getCategoryBadgeClass(rule.category)">
                          {{ getCategoryLabel(rule.category) }}
                        </span>
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                        {{ rule.group_name || '(nenhum)' }}
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap">
                        <span
                          :class="
                            rule.is_active
                              ? 'px-2 py-1 text-xs font-semibold rounded bg-green-100 text-green-800'
                              : 'px-2 py-1 text-xs font-semibold rounded bg-gray-100 text-gray-800'
                          "
                        >
                          {{ rule.is_active ? 'Ativa' : 'Inativa' }}
                        </span>
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap text-right text-sm font-medium space-x-2">
                        <button
                          @click="testRule(rule)"
                          class="text-blue-600 hover:text-blue-800"
                          title="Testar regex"
                        >
                          <i class="fas fa-flask"></i>
                        </button>
                        <button
                          @click="editRule(rule)"
                          class="text-indigo-600 hover:text-indigo-800"
                          title="Editar"
                        >
                          <i class="fas fa-edit"></i>
                        </button>
                        <button
                          @click="toggleRuleStatus(rule)"
                          :class="
                            rule.is_active
                              ? 'text-yellow-600 hover:text-yellow-800'
                              : 'text-green-600 hover:text-green-800'
                          "
                          :title="rule.is_active ? 'Desativar' : 'Ativar'"
                        >
                          <i :class="rule.is_active ? 'fas fa-ban' : 'fas fa-check'"></i>
                        </button>
                        <button
                          @click="deleteRule(rule)"
                          class="text-red-600 hover:text-red-800"
                          title="Excluir"
                        >
                          <i class="fas fa-trash"></i>
                        </button>
                      </td>
                    </tr>
                    <tr v-if="rules.length === 0">
                      <td colspan="6" class="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                        <i class="fas fa-info-circle mr-2"></i>
                        Nenhuma regra configurada. Clique em "Nova Regra" para começar.
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Info Box -->
              <div class="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <h4 class="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
                  <i class="fas fa-lightbulb mr-2"></i>
                  Como funciona?
                </h4>
                <ul class="text-sm text-blue-800 dark:text-blue-200 space-y-1 list-disc list-inside">
                  <li>As regras são aplicadas em ordem de prioridade durante a importação</li>
                  <li>O padrão regex é testado contra o nome do dispositivo no Zabbix</li>
                  <li>Quando há match, o dispositivo recebe automaticamente a categoria e grupo definidos</li>
                  <li>Apenas regras <strong>ativas</strong> são aplicadas</li>
                </ul>
              </div>
            </div>

            <!-- Footer -->
            <div class="flex justify-end space-x-3 p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
              <button
                @click="closeModal"
                class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- Edit/Create Modal -->
    <ImportRuleFormModal
      v-model="showFormModal"
      :rule="selectedRule"
      :device-groups="deviceGroups"
      @save="handleRuleSave"
    />

    <!-- Test Modal -->
    <ImportRuleTestModal
      v-model="showTestModal"
      :rule="testingRule"
    />
  </teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useApi } from '@/composables/useApi';
import ImportRuleFormModal from './ImportRuleFormModal.vue';
import ImportRuleTestModal from './ImportRuleTestModal.vue';

const props = defineProps({
  modelValue: Boolean,
});

const emit = defineEmits(['update:modelValue']);

const api = useApi();

// Estado
const rules = ref([]);
const deviceGroups = ref([]);
const showFormModal = ref(false);
const showTestModal = ref(false);
const selectedRule = ref(null);
const testingRule = ref(null);

// Computed
const sortedRules = computed(() => {
  if (!Array.isArray(rules.value)) {
    return [];
  }
  return [...rules.value].sort((a, b) => {
    if (a.priority !== b.priority) {
      return a.priority - b.priority;
    }
    return a.id - b.id;
  });
});

// Métodos
const closeModal = () => {
  emit('update:modelValue', false);
};

const fetchRules = async () => {
  try {
    const response = await api.get('/api/v1/import-rules/');
    // DRF pode retornar lista simples OU objeto paginado
    rules.value = Array.isArray(response) 
      ? response 
      : (response.results || response.data || []);
  } catch (error) {
    console.error('Erro ao carregar regras:', error);
    rules.value = [];
  }
};

const fetchDeviceGroups = async () => {
  try {
    const response = await api.get('/api/v1/device-groups/');
    // DRF pode retornar lista simples OU objeto paginado
    deviceGroups.value = Array.isArray(response)
      ? response
      : (response.results || response.data || []);
  } catch (error) {
    console.error('Erro ao carregar grupos:', error);
    deviceGroups.value = [];
  }
};

const addNewRule = () => {
  selectedRule.value = null;
  showFormModal.value = true;
};

const editRule = (rule) => {
  selectedRule.value = { ...rule };
  showFormModal.value = true;
};

const testRule = (rule) => {
  testingRule.value = rule;
  showTestModal.value = true;
};

const handleRuleSave = async () => {
  await fetchRules();
};

const toggleRuleStatus = async (rule) => {
  try {
    await api.patch(`/api/v1/import-rules/${rule.id}/`, {
      is_active: !rule.is_active,
    });
    await fetchRules();
  } catch (error) {
    console.error('Erro ao alternar status:', error);
    alert('Erro ao alternar status da regra');
  }
};

const deleteRule = async (rule) => {
  if (!confirm(`Excluir regra "${rule.pattern}"?`)) return;

  try {
    await api.delete(`/api/v1/import-rules/${rule.id}/`);
    await fetchRules();
  } catch (error) {
    console.error('Erro ao excluir regra:', error);
    alert('Erro ao excluir regra');
  }
};

const isFirstRule = (rule) => {
  const sorted = sortedRules.value;
  return sorted[0]?.id === rule.id;
};

const isLastRule = (rule) => {
  const sorted = sortedRules.value;
  return sorted[sorted.length - 1]?.id === rule.id;
};

const moveRuleUp = async (rule) => {
  const sorted = sortedRules.value;
  const currentIndex = sorted.findIndex((r) => r.id === rule.id);
  if (currentIndex === 0) return;

  const prevRule = sorted[currentIndex - 1];
  const tempPriority = rule.priority;
  
  try {
    await api.post('/api/v1/import-rules/reorder/', {
      rules: [
        { id: rule.id, priority: prevRule.priority },
        { id: prevRule.id, priority: tempPriority },
      ],
    });
    await fetchRules();
  } catch (error) {
    console.error('Erro ao reordenar:', error);
  }
};

const moveRuleDown = async (rule) => {
  const sorted = sortedRules.value;
  const currentIndex = sorted.findIndex((r) => r.id === rule.id);
  if (currentIndex === sorted.length - 1) return;

  const nextRule = sorted[currentIndex + 1];
  const tempPriority = rule.priority;
  
  try {
    await api.post('/api/v1/import-rules/reorder/', {
      rules: [
        { id: rule.id, priority: nextRule.priority },
        { id: nextRule.id, priority: tempPriority },
      ],
    });
    await fetchRules();
  } catch (error) {
    console.error('Erro ao reordenar:', error);
  }
};

const getCategoryBadgeClass = (category) => {
  const classes = {
    backbone: 'px-2 py-1 text-xs font-semibold rounded bg-blue-100 text-blue-800',
    gpon: 'px-2 py-1 text-xs font-semibold rounded bg-green-100 text-green-800',
    dwdm: 'px-2 py-1 text-xs font-semibold rounded bg-purple-100 text-purple-800',
    access: 'px-2 py-1 text-xs font-semibold rounded bg-orange-100 text-orange-800',
  };
  return classes[category] || 'px-2 py-1 text-xs font-semibold rounded bg-gray-100 text-gray-800';
};

const getCategoryLabel = (category) => {
  const labels = {
    backbone: 'Backbone / IP',
    gpon: 'GPON / FTTx',
    dwdm: 'DWDM / Óptico',
    access: 'Acesso / Clientes',
  };
  return labels[category] || category;
};

// Lifecycle
onMounted(() => {
  fetchRules();
  fetchDeviceGroups();
});
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
