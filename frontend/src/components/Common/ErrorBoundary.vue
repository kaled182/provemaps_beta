<template>
  <div v-if="hasError" class="error-boundary">
    <div class="error-content">
      <svg class="error-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <h3 class="error-title">{{ errorTitle }}</h3>
      <p class="error-message">{{ error || 'Algo deu errado' }}</p>
      <div class="error-actions">
        <button @click="retry" class="btn-retry">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Tentar novamente
        </button>
        <button v-if="showDetails" @click="toggleDetails" class="btn-details">
          {{ showErrorDetails ? 'Ocultar' : 'Ver' }} detalhes
        </button>
      </div>
      <details v-if="showDetails && showErrorDetails" class="error-details">
        <summary>Detalhes técnicos</summary>
        <pre>{{ errorDetails }}</pre>
      </details>
    </div>
  </div>
  <slot v-else />
</template>

<script setup>
import { ref } from 'vue';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  errorTitle: {
    type: String,
    default: 'Erro',
  },
  showDetails: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['retry']);

const { error, hasError, errorDetails, clearError } = useErrorHandler();
const showErrorDetails = ref(false);

function retry() {
  clearError();
  showErrorDetails.value = false;
  emit('retry');
}

function toggleDetails() {
  showErrorDetails.value = !showErrorDetails.value;
}
</script>

<style scoped>
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  padding: 24px;
}

.error-content {
  text-align: center;
  max-width: 400px;
}

.error-icon {
  width: 64px;
  height: 64px;
  color: #dc2626;
  margin: 0 auto 16px;
}

.error-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.error-message {
  font-size: 14px;
  color: var(--text-tertiary);
  margin: 0 0 24px 0;
  line-height: 1.5;
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-retry,
.btn-details {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  background: var(--surface-card);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-retry {
  background: var(--accent-info);
  color: #fff;
  border-color: var(--accent-info);
}

.btn-retry:hover {
  background: var(--accent-info-dark);
  border-color: var(--accent-info-dark);
}

.btn-details:hover {
  background: var(--surface-muted);
  border-color: var(--border-secondary);
}

.btn-retry svg,
.btn-details svg {
  width: 16px;
  height: 16px;
}

.error-details {
  margin-top: 24px;
  text-align: left;
  background: var(--surface-muted);
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  padding: 12px;
}

.error-details summary {
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}

.error-details pre {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  max-height: 200px;
  overflow-y: auto;
}
</style>
