<template>
  <Teleport to="body">
    <div v-if="isOpen" class="trace-modal-overlay" @click.self="close">
      <div class="trace-modal">
        <!-- Loading State -->
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>Rastreando caminho óptico...</p>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="error-state">
          <h3>❌ Erro ao Rastrear</h3>
          <p>{{ error }}</p>
          <button class="btn-close" @click="close">Fechar</button>
        </div>

        <!-- Trace Result -->
        <TraceRouteView
          v-else-if="traceResult"
          :result="traceResult"
          @close="close"
          @export="handleExport"
          @locate-fault="handleLocateFault"
        />
      </div>
    </div>
  </Teleport>
</template>

<script>
import { ref, watch } from 'vue';
import TraceRouteView from './TraceRouteView.vue';
import { useTraceRoute } from '@/composables/useTraceRoute';

export default {
  name: 'TraceRouteModal',

  components: {
    TraceRouteView,
  },

  props: {
    strandId: {
      type: [Number, String],
      default: null,
    },
    isOpen: {
      type: Boolean,
      default: false,
    },
  },

  emits: ['close', 'fault-located'],

  setup(props, { emit }) {
    const { loading, error, traceResult, traceFromStrand, exportTracePDF } = useTraceRoute();

    // Watch for strand ID changes and auto-trace
    watch(
      () => [props.strandId, props.isOpen],
      async ([newStrandId, newIsOpen]) => {
        if (newIsOpen && newStrandId) {
          try {
            await traceFromStrand(newStrandId);
          } catch (err) {
            console.error('Erro ao rastrear:', err);
          }
        }
      },
      { immediate: true }
    );

    function close() {
      emit('close');
    }

    function handleExport(trace) {
      exportTracePDF(trace);
    }

    function handleLocateFault(trace) {
      // Emit event to parent for OTDR fault location
      emit('fault-located', {
        trace,
        fiberStrands: trace.path
          .filter(step => step.type === 'fiber_strand')
          .map(step => ({
            id: step.details.strand_id,
            cableId: step.details.cable_id,
            attenuation: step.details.attenuation_measured_db,
          })),
      });
    }

    return {
      loading,
      error,
      traceResult,
      close,
      handleExport,
      handleLocateFault,
    };
  },
};
</script>

<style scoped>
.trace-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1rem;
}

.trace-modal {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 1200px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.loading-state,
.error-state {
  padding: 3rem;
  text-align: center;
}

.spinner {
  width: 3rem;
  height: 3rem;
  border: 4px solid #e2e8f0;
  border-top-color: #4299e1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-state p {
  color: #718096;
  font-size: 1.125rem;
}

.error-state h3 {
  color: #e53e3e;
  margin-bottom: 1rem;
}

.error-state p {
  color: #718096;
  margin-bottom: 1.5rem;
}

.btn-close {
  padding: 0.75rem 1.5rem;
  background: #e2e8f0;
  color: #2d3748;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-close:hover {
  background: #cbd5e0;
}
</style>
