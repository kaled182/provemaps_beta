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
            class="relative w-full max-w-5xl app-surface rounded-lg transform transition-all"
            @click.stop
          >
            <!-- Header -->
            <div class="flex items-center justify-between p-6 border-b app-divider">
              <h2 class="text-2xl font-bold app-text-primary">
                <i class="fas fa-robot mr-2" style="color: var(--accent-info);"></i>
                Regras de Auto-Associação
              </h2>
              <button
                @click="closeModal"
                class="app-text-tertiary close-icon-btn transition-colors"
              >
                <i class="fas fa-times text-xl"></i>
              </button>
            </div>

            <!-- Content -->
            <div class="p-6">
              <!-- Add Rule Button -->
              <div class="mb-4 flex justify-between items-center">
                <p class="text-sm app-text-tertiary">
                  Regras aplicadas automaticamente durante importação do Zabbix.
                  <br>
                  <span class="font-medium">Ordem:</span> prioridade crescente (0 = maior prioridade).
                </p>
                <button
                  @click="addNewRule"
                  class="inline-flex items-center px-4 py-2 rounded-lg transition-colors shadow-sm app-btn-primary"
                >
                  <i class="fas fa-plus mr-2"></i>
                  Nova Regra
                </button>
              </div>

              <!-- Rules Table -->
              <div class="overflow-x-auto border app-divider rounded-lg shadow-sm">
                <table class="min-w-full divide-y app-divide">
                  <thead class="app-surface-muted">
                    <tr>
                      <th class="px-4 py-3 text-left text-xs font-medium app-text-tertiary uppercase tracking-wider">
                        Prioridade
                      </th>
                      <th class="px-4 py-3 text-left text-xs font-medium app-text-tertiary uppercase tracking-wider">
                        Padrão Regex
                      </th>
                      <th class="px-4 py-3 text-left text-xs font-medium app-text-tertiary uppercase tracking-wider">
                        Categoria
                      </th>
                      <th class="px-4 py-3 text-left text-xs font-medium app-text-tertiary uppercase tracking-wider">
                        Grupo
                      </th>
                      <th class="px-4 py-3 text-left text-xs font-medium app-text-tertiary uppercase tracking-wider">
                        Status
                      </th>
                      <th class="px-4 py-3 text-right text-xs font-medium app-text-tertiary uppercase tracking-wider">
                        Ações
                      </th>
                    </tr>
                  </thead>
                  <tbody class="app-surface divide-y app-divide">
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
                            class="app-text-tertiary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                            title="Mover para cima"
                          >
                            <i class="fas fa-arrow-up"></i>
                          </button>
                          <span class="font-mono text-sm font-semibold app-text-primary">{{ rule.priority }}</span>
                          <button
                            @click="moveRuleDown(rule)"
                            :disabled="isLastRule(rule)"
                            class="app-text-tertiary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                            title="Mover para baixo"
                          >
                            <i class="fas fa-arrow-down"></i>
                          </button>
                        </div>
                      </td>
                      <td class="px-4 py-3">
                        <code class="text-sm app-surface-muted px-2 py-1 rounded font-mono app-text-primary">
                          {{ rule.pattern }}
                        </code>
                        <p v-if="rule.description" class="text-xs app-text-tertiary mt-1">
                          {{ rule.description }}
                        </p>
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap">
                        <span :class="getCategoryBadgeClass(rule.category)">
                          {{ getCategoryLabel(rule.category) }}
                        </span>
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap text-sm app-text-tertiary">
                        {{ rule.group_name || '(nenhum)' }}
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap">
                        <span
                          :class="
                            rule.is_active
                              ? 'app-badge app-badge-success'
                              : 'app-badge app-badge-muted'
                          "
                        >
                          {{ rule.is_active ? 'Ativa' : 'Inativa' }}
                        </span>
                      </td>
                      <td class="px-4 py-3 whitespace-nowrap text-right text-sm font-medium space-x-2">
                        <button
                          @click="testRule(rule)"
                          class="app-text-secondary"
                          title="Testar regex"
                        >
                          <i class="fas fa-flask"></i>
                        </button>
                        <button
                          @click="editRule(rule)"
                          class="app-text-secondary"
                          title="Editar"
                        >
                          <i class="fas fa-edit"></i>
                        </button>
                        <button
                          @click="toggleRuleStatus(rule)"
                          :class="
                            rule.is_active
                              ? 'app-text-secondary'
                              : 'app-text-secondary'
                          "
                          :title="rule.is_active ? 'Desativar' : 'Ativar'"
                        >
                          <i :class="rule.is_active ? 'fas fa-ban' : 'fas fa-check'"></i>
                        </button>
                        <button
                          @click="deleteRule(rule)"
                          class="app-text-secondary"
                          title="Excluir"
                        >
                          <i class="fas fa-trash"></i>
                        </button>
                      </td>
                    </tr>
                    <tr v-if="rules.length === 0">
                      <td colspan="6" class="px-4 py-8 text-center app-text-tertiary">
                        <i class="fas fa-info-circle mr-2"></i>
                        Nenhuma regra configurada. Clique em "Nova Regra" para começar.
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Info Box -->
              <div class="mt-4 p-4 app-surface-muted border app-divider rounded-lg">
                <h4 class="text-sm font-semibold app-text-primary mb-2">
                  <i class="fas fa-lightbulb mr-2"></i>
                  Como funciona?
                </h4>
                <ul class="text-sm app-text-secondary space-y-1 list-disc list-inside">
                  <li>As regras são aplicadas em ordem de prioridade durante a importação</li>
                  <li>O padrão regex é testado contra o nome do dispositivo no Zabbix</li>
                  <li>Quando há match, o dispositivo recebe automaticamente a categoria e grupo definidos</li>
                  <li>Apenas regras <strong>ativas</strong> são aplicadas</li>
                </ul>
              </div>
            </div>

            <!-- Footer -->
            <div class="flex justify-end space-x-3 p-6 border-t app-divider app-surface-muted">
              <button
                @click="closeModal"
                class="px-4 py-2 rounded-lg transition-colors app-btn"
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
    backbone: 'app-badge app-badge-info',
    gpon: 'app-badge app-badge-success',
    dwdm: 'app-badge app-badge-warning',
    access: 'app-badge app-badge-danger',
  };
  return classes[category] || 'app-badge app-badge-muted';
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

.close-icon-btn:hover {
  color: var(--text-primary);
}
</style>
