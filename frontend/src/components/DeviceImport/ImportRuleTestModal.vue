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
            class="relative w-full max-w-3xl app-surface rounded-lg"
            @click.stop
          >
            <!-- Header -->
            <div class="flex items-center justify-between p-6 border-b app-divider">
              <h3 class="text-xl font-bold app-text-primary">
                <i class="fas fa-flask mr-2" style="color: var(--accent-info);"></i>
                Testar Regex
              </h3>
              <button @click="closeModal" class="app-text-tertiary close-icon-btn">
                <i class="fas fa-times"></i>
              </button>
            </div>

            <!-- Content -->
            <div class="p-6 space-y-4">
              <!-- Pattern Display -->
              <div>
                <label class="block text-sm font-medium app-text-secondary mb-1">
                  Padrão
                </label>
                <code class="block app-surface-muted px-3 py-2 rounded font-mono text-sm app-text-primary">
                  {{ rule?.pattern }}
                </code>
                <p v-if="rule?.description" class="text-xs app-text-tertiary mt-1">
                  {{ rule.description }}
                </p>
              </div>

              <!-- Sample Names Input -->
              <div>
                <label class="block text-sm font-medium app-text-secondary mb-1">
                  Nomes de Teste
                  <span class="text-xs app-text-tertiary">(um por linha)</span>
                </label>
                <textarea
                  v-model="sampleNamesText"
                  rows="6"
                  class="w-full px-3 py-2 rounded-lg font-mono text-sm app-input"
                  placeholder="OLT-HUAWEI-001&#10;SWITCH-CISCO-CORE&#10;RTR-MIKROTIK-EDGE-01&#10;ONU-FTTx-Cliente-456"
                />
              </div>

              <!-- Test Button -->
              <button
                @click="runTest"
                :disabled="!sampleNamesText.trim()"
                class="w-full px-4 py-2 rounded-lg app-btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <i class="fas fa-play mr-2"></i>
                Executar Teste
              </button>

              <!-- Results -->
              <div v-if="testResults" class="space-y-4">
                <!-- Matches -->
                <div v-if="testResults.matches.length > 0">
                  <h4 class="text-sm font-semibold app-text-primary mb-2">
                    <i class="fas fa-check-circle mr-1"></i>
                    Correspondências ({{ testResults.matches.length }})
                  </h4>
                  <div class="app-surface-muted border app-divider rounded-lg p-3 space-y-1">
                    <div
                      v-for="(match, index) in testResults.matches"
                      :key="`match-${index}`"
                      class="text-sm font-mono app-text-secondary"
                    >
                      <i class="fas fa-check mr-2" style="color: var(--status-online);"></i>
                      {{ match }}
                    </div>
                  </div>
                </div>

                <!-- Non-matches -->
                <div v-if="testResults.non_matches.length > 0">
                  <h4 class="text-sm font-semibold app-text-primary mb-2">
                    <i class="fas fa-times-circle mr-1"></i>
                    Não Corresponderam ({{ testResults.non_matches.length }})
                  </h4>
                  <div class="app-surface-muted border app-divider rounded-lg p-3 space-y-1">
                    <div
                      v-for="(nonMatch, index) in testResults.non_matches"
                      :key="`non-match-${index}`"
                      class="text-sm font-mono app-text-secondary"
                    >
                      <i class="fas fa-times mr-2" style="color: var(--status-offline);"></i>
                      {{ nonMatch }}
                    </div>
                  </div>
                </div>

                <!-- Empty Results -->
                <div v-if="testResults.matches.length === 0 && testResults.non_matches.length === 0">
                  <div class="app-surface-muted border app-divider rounded-lg p-4 text-center app-text-tertiary">
                    <i class="fas fa-info-circle mr-2"></i>
                    Nenhum resultado
                  </div>
                </div>
              </div>
            </div>

            <!-- Footer -->
            <div class="flex justify-end p-6 border-t app-divider app-surface-muted">
              <button
                @click="closeModal"
                class="px-4 py-2 rounded-lg app-btn"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useApi } from '@/composables/useApi';

const props = defineProps({
  modelValue: Boolean,
  rule: Object,
});

const emit = defineEmits(['update:modelValue']);

const api = useApi();

// Estado
const sampleNamesText = ref(`OLT-HUAWEI-001
SWITCH-CISCO-CORE
RTR-MIKROTIK-EDGE-01
ONU-FTTx-Cliente-456
GPON-OLT-CENTRO
DWDM-OPTICAL-LINK-01`);

const testResults = ref(null);

// Watchers
watch(
  () => props.modelValue,
  (newValue) => {
    if (!newValue) {
      testResults.value = null;
    }
  }
);

// Métodos
const closeModal = () => {
  emit('update:modelValue', false);
};

const runTest = async () => {
  if (!props.rule?.pattern) return;

  const samples = sampleNamesText.value
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  if (samples.length === 0) return;

  try {
    const response = await api.post('/api/v1/import-rules/test_pattern/', {
      pattern: props.rule.pattern,
      samples: samples,
    });

    testResults.value = response;
  } catch (error) {
    console.error('Erro ao testar regex:', error);
    alert('Erro ao testar regex: ' + (error.response?.data?.error || error.message));
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

.close-icon-btn:hover {
  color: var(--text-primary);
}
</style>
