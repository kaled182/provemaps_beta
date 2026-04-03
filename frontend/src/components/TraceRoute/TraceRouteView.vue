<template>
  <div class="trace-route-container">
    <!-- Header with summary -->
    <div class="trace-header">
      <div class="trace-title">
        <h3>🔍 Trace Route - Caminho Óptico</h3>
        <span class="trace-status" :class="`status-${result.status.toLowerCase()}`">
          {{ result.status }}
        </span>
      </div>
      
      <div class="trace-summary">
        <div class="summary-item">
          <span class="label">Origem:</span>
          <span class="value">{{ sourceLabel }}</span>
        </div>
        <div class="summary-item">
          <span class="label">Destino:</span>
          <span class="value">{{ destinationLabel }}</span>
        </div>
        <div class="summary-item">
          <span class="label">Distância:</span>
          <span class="value">{{ result.total_distance_km?.toFixed(2) }} km</span>
        </div>
        <div class="summary-item">
          <span class="label">Perda Total:</span>
          <span class="value">{{ result.total_loss_db?.toFixed(2) }} dB</span>
        </div>
      </div>
    </div>

    <!-- Power Budget Card -->
    <div class="power-budget-card" :class="`budget-${result.power_budget?.status?.toLowerCase()}`">
      <h4>⚡ Orçamento de Potência (Power Budget)</h4>
      
      <div class="budget-grid">
        <div class="budget-item">
          <span class="budget-label">TX Power:</span>
          <span class="budget-value">{{ result.power_budget?.tx_power_dbm }} dBm</span>
        </div>
        <div class="budget-item">
          <span class="budget-label">RX Sensitivity:</span>
          <span class="budget-value">{{ result.power_budget?.rx_sensitivity_dbm }} dBm</span>
        </div>
        <div class="budget-item">
          <span class="budget-label">Fusões:</span>
          <span class="budget-value">{{ result.fusion_count }} × 0.1 dB</span>
        </div>
        <div class="budget-item">
          <span class="budget-label">Conectores:</span>
          <span class="budget-value">{{ result.connector_count }} × 0.5 dB</span>
        </div>
        <div class="budget-item highlight">
          <span class="budget-label">Margem Disponível:</span>
          <span class="budget-value">
            {{ result.power_budget?.available_margin_db?.toFixed(2) }} dB
          </span>
        </div>
        <div class="budget-item highlight">
          <span class="budget-label">Margem Mínima:</span>
          <span class="budget-value">{{ result.power_budget?.required_margin_db }} dB</span>
        </div>
      </div>
      
      <div class="budget-message" :class="`message-${result.power_budget?.status?.toLowerCase()}`">
        {{ result.power_budget?.message }}
      </div>
    </div>

    <!-- Optical Path Timeline (Metro-style) -->
    <div class="optical-path">
      <h4>🛤️ Caminho da Luz</h4>
      
      <div class="timeline">
        <div
          v-for="(step, index) in result.path"
          :key="index"
          class="timeline-step"
          :class="`step-type-${step.type}`"
        >
          <!-- Step Icon -->
          <div class="step-icon">
            <span v-if="step.type === 'device_port'">🟢</span>
            <span v-else-if="step.type === 'fusion'">🟠</span>
            <span v-else-if="step.type === 'fiber_strand'">━━</span>
            <span v-else>⚪</span>
          </div>

          <!-- Step Content -->
          <div class="step-content">
            <div class="step-header">
              <span class="step-number">{{ step.step_number }}</span>
              <span class="step-name">{{ step.name }}</span>
            </div>

            <!-- Device Port Details -->
            <div v-if="step.type === 'device_port'" class="step-details">
              <span class="detail-badge">{{ step.details.device_type }}</span>
              <span class="detail-text">{{ step.details.port_name }}</span>
              <span v-if="step.details.site_name" class="detail-text">
                📍 {{ step.details.site_name }}
              </span>
            </div>

            <!-- Fiber Strand Details -->
            <div v-if="step.type === 'fiber_strand'" class="step-details">
              <span class="detail-badge fiber-color" :style="{ backgroundColor: step.details.color_hex }">
                {{ step.details.fiber_color }}
              </span>
              <span class="detail-text">
                {{ step.details.distance_km?.toFixed(2) }} km
              </span>
              <span class="detail-text">
                Tubo {{ step.details.tube_number }}
              </span>
              <span v-if="step.details.attenuation_measured_db" class="detail-text">
                📊 {{ step.details.attenuation_measured_db?.toFixed(2) }} dB (OTDR)
              </span>
            </div>

            <!-- Fusion Details -->
            <div v-if="step.type === 'fusion'" class="step-details">
              <span class="detail-badge fusion">Fusão</span>
              <span v-if="step.details.fusion_location" class="detail-text">
                {{ step.details.fusion_location }}
              </span>
              <span v-if="step.details.tray" class="detail-text">
                Bandeja {{ step.details.tray }}, Slot {{ step.details.slot }}
              </span>
            </div>

            <!-- Loss Indicator -->
            <div v-if="step.loss_db" class="step-loss">
              <span class="loss-label">Perda:</span>
              <span class="loss-value">{{ step.loss_db.toFixed(2) }} dB</span>
            </div>
          </div>

          <!-- Connector Line (except last step) -->
          <div v-if="index < result.path.length - 1" class="connector-line">
            <div class="line"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="trace-actions">
      <button class="btn-action" @click="exportTrace">
        📄 Exportar Relatório
      </button>
      <button class="btn-action" @click="locateFault" :disabled="!hasOpticalData">
        🔍 Localizar Falha (OTDR)
      </button>
      <button class="btn-close" @click="$emit('close')">
        Fechar
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TraceRouteView',
  
  props: {
    result: {
      type: Object,
      required: true,
      default: () => ({
        trace_id: '',
        source: {},
        destination: {},
        path: [],
        total_distance_km: 0,
        total_loss_db: 0,
        fusion_count: 0,
        connector_count: 0,
        power_budget: {},
        status: 'UNKNOWN',
      }),
    },
  },

  emits: ['close', 'export', 'locate-fault'],

  computed: {
    sourceLabel() {
      if (!this.result.source || !this.result.source.device_name) {
        return 'N/A';
      }
      return `${this.result.source.device_name} - ${this.result.source.port_name}`;
    },

    destinationLabel() {
      if (!this.result.destination || !this.result.destination.device_name) {
        return 'N/A';
      }
      return `${this.result.destination.device_name} - ${this.result.destination.port_name}`;
    },

    hasOpticalData() {
      return this.result.path?.some(step => 
        step.type === 'fiber_strand' && step.details.attenuation_measured_db
      );
    },
  },

  methods: {
    exportTrace() {
      this.$emit('export', this.result);
    },

    locateFault() {
      if (this.hasOpticalData) {
        this.$emit('locate-fault', this.result);
      }
    },
  },
};
</script>

<style scoped>
.trace-route-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1.5rem;
  background: #ffffff;
  border-radius: 8px;
  max-height: 80vh;
  overflow-y: auto;
}

/* Header */
.trace-header {
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 1rem;
}

.trace-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.trace-title h3 {
  margin: 0;
  color: #1a202c;
  font-size: 1.5rem;
}

.trace-status {
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.875rem;
}

.status-ok {
  background: #c6f6d5;
  color: #22543d;
}

.status-warning {
  background: #fef5e7;
  color: #975a16;
}

.trace-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.summary-item .label {
  font-size: 0.875rem;
  color: #718096;
  font-weight: 500;
}

.summary-item .value {
  font-size: 1.125rem;
  color: #2d3748;
  font-weight: 600;
}

/* Power Budget Card */
.power-budget-card {
  padding: 1.5rem;
  border-radius: 8px;
  border: 2px solid #e2e8f0;
}

.budget-ok {
  background: #f0fdf4;
  border-color: #86efac;
}

.budget-warning {
  background: #fffbeb;
  border-color: #fcd34d;
}

.power-budget-card h4 {
  margin: 0 0 1rem 0;
  color: #1a202c;
}

.budget-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.budget-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem;
  background: white;
  border-radius: 4px;
}

.budget-item.highlight {
  background: #edf2f7;
  font-weight: 600;
}

.budget-label {
  color: #4a5568;
  font-size: 0.875rem;
}

.budget-value {
  color: #2d3748;
  font-weight: 500;
}

.budget-message {
  padding: 0.75rem;
  border-radius: 4px;
  font-weight: 500;
  text-align: center;
}

.message-ok {
  background: #c6f6d5;
  color: #22543d;
}

.message-warning {
  background: #fed7d7;
  color: #742a2a;
}

/* Optical Path Timeline */
.optical-path h4 {
  margin: 0 0 1rem 0;
  color: #1a202c;
}

.timeline {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.timeline-step {
  display: flex;
  align-items: flex-start;
  position: relative;
}

.step-icon {
  flex-shrink: 0;
  width: 3rem;
  height: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  background: white;
  border-radius: 50%;
  border: 3px solid #e2e8f0;
  z-index: 2;
}

.step-type-device_port .step-icon {
  background: #c6f6d5;
  border-color: #48bb78;
}

.step-type-fusion .step-icon {
  background: #fed7d7;
  border-color: #f56565;
}

.step-content {
  flex: 1;
  margin-left: 1rem;
  padding: 1rem;
  background: #f7fafc;
  border-radius: 8px;
  border-left: 4px solid #cbd5e0;
}

.step-type-device_port .step-content {
  border-left-color: #48bb78;
}

.step-type-fusion .step-content {
  border-left-color: #f56565;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.step-number {
  background: #2d3748;
  color: white;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
}

.step-name {
  font-weight: 600;
  color: #2d3748;
  font-size: 1rem;
}

.step-details {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.detail-badge {
  padding: 0.25rem 0.5rem;
  background: #edf2f7;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  color: #4a5568;
}

.detail-badge.fiber-color {
  color: white;
  font-weight: 600;
}

.detail-badge.fusion {
  background: #fed7d7;
  color: #742a2a;
}

.detail-text {
  font-size: 0.875rem;
  color: #718096;
}

.step-loss {
  display: flex;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.loss-label {
  color: #718096;
}

.loss-value {
  color: #e53e3e;
  font-weight: 600;
}

.connector-line {
  position: absolute;
  left: 1.5rem;
  top: 3rem;
  bottom: -3rem;
  width: 4px;
  z-index: 1;
}

.line {
  width: 100%;
  height: 100%;
  background: linear-gradient(180deg, #cbd5e0 0%, #cbd5e0 100%);
}

/* Actions */
.trace-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  padding-top: 1rem;
  border-top: 2px solid #e2e8f0;
}

.btn-action,
.btn-close {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-action {
  background: #4299e1;
  color: white;
}

.btn-action:hover:not(:disabled) {
  background: #3182ce;
  transform: translateY(-1px);
}

.btn-action:disabled {
  background: #cbd5e0;
  cursor: not-allowed;
}

.btn-close {
  background: #e2e8f0;
  color: #2d3748;
}

.btn-close:hover {
  background: #cbd5e0;
}
</style>
