<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="show && cable"
        class="modal-overlay"
        @click.self="closeModal"
      >
        <div class="quick-modal-container" @click.stop>
          <!-- Header -->
          <div class="quick-modal-header">
            <div class="header-content">
              <div class="cable-icon" :class="`status-${cableStatus}`">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
              </div>
              <div class="cable-title">
                <h3>{{ cable.name }}</h3>
                <p class="cable-route">
                  {{ cable.site_a_name || 'Site A' }} 
                  <svg class="arrow-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                  {{ cable.site_b_name || 'Site B' }}
                </p>
              </div>
            </div>
            <button class="close-btn" @click="closeModal" title="Fechar (ESC)">
              <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div class="quick-modal-body">
            <!-- Status -->
            <div class="info-card status-card">
              <div class="card-icon" :class="`status-${cableStatus}`">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div class="card-content">
                <div class="card-label">Status do Cabo</div>
                <div class="card-value" :class="`text-${cableStatus}`">
                  {{ getStatusLabel(cableStatus) }}
                </div>
                <div class="status-detail">{{ cable.original_status || 'N/A' }}</div>
              </div>
            </div>

            <!-- Distância -->
            <div class="info-card distance-card">
              <div class="card-icon">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z" />
                </svg>
              </div>
              <div class="card-content">
                <div class="card-label">Distância</div>
                <div class="card-value">{{ formatDistance() }}</div>
                <div class="status-detail">{{ cable.path_coordinates?.length || 0 }} pontos</div>
              </div>
            </div>

            <!-- Fibras -->
            <div v-if="cable.fiber_count" class="info-card fiber-card">
              <div class="card-icon">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                </svg>
              </div>
              <div class="card-content">
                <div class="card-label">Fibras</div>
                <div class="card-value">{{ cable.fiber_count }}</div>
                <div class="status-detail">{{ cable.cable_type || 'Tipo não especificado' }}</div>
              </div>
            </div>

            <!-- Nível Óptico -->
            <div v-if="opticalLevel !== null" class="info-card optical-card">
              <div class="card-icon">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div class="card-content">
                <div class="card-label">Nível Óptico</div>
                <div class="card-value" :class="getOpticalClass()">
                  {{ formatOpticalLevel() }}
                </div>
                <div class="optical-quality">{{ getOpticalQuality() }}</div>
              </div>
            </div>

            <!-- Atenuação -->
            <div v-if="attenuation !== null" class="info-card attenuation-card">
              <div class="card-icon">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div class="card-content">
                <div class="card-label">Atenuação</div>
                <div class="card-value">{{ attenuation.toFixed(2) }} dB</div>
                <div class="status-detail">{{ getAttenuationQuality() }}</div>
              </div>
            </div>

            <!-- Observações -->
            <div v-if="cable.notes || cable.description" class="info-card notes-card">
              <div class="card-icon">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div class="card-content">
                <div class="card-label">Observações</div>
                <div class="notes-text">{{ cable.notes || cable.description }}</div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="quick-modal-footer">
            <button class="btn-secondary" @click="closeModal">
              Fechar
            </button>
            <button v-if="cable.id" class="btn-primary" @click="openFullDetails">
              <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Ver Detalhes Completos
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useEscapeKey } from '@/composables/useEscapeKey'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  cable: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'openFullDetails'])

// Fechar modal com ESC
useEscapeKey(() => {
  if (props.show) {
    closeModal()
  }
})

const closeModal = () => {
  emit('close')
}

const openFullDetails = () => {
  emit('openFullDetails', props.cable)
}

// Status normalizado do cabo
const cableStatus = computed(() => {
  if (!props.cable) return 'unknown'
  return String(props.cable.status || 'unknown').toLowerCase()
})

// Nível óptico (placeholder - implementar quando tiver dados reais)
const opticalLevel = computed(() => {
  // TODO: Buscar do backend quando disponível
  if (props.cable?.optical_level !== undefined) {
    return props.cable.optical_level
  }
  return null
})

// Atenuação (placeholder - implementar quando tiver dados reais)
const attenuation = computed(() => {
  // TODO: Buscar do backend quando disponível
  if (props.cable?.attenuation !== undefined) {
    return props.cable.attenuation
  }
  return null
})

const getStatusLabel = (status) => {
  const labels = {
    online: 'ONLINE',
    offline: 'OFFLINE',
    warning: 'ATENÇÃO',
    critical: 'CRÍTICO',
    unknown: 'DESCONHECIDO',
    up: 'OPERACIONAL',
    down: 'INOPERANTE'
  }
  return labels[status] || 'DESCONHECIDO'
}

const formatDistance = () => {
  if (!props.cable) return 'N/A'
  if (props.cable.length_km) {
    return `${props.cable.length_km} km`
  }
  if (props.cable.length_meters) {
    return `${props.cable.length_meters} m`
  }
  return 'N/A'
}

const formatOpticalLevel = () => {
  if (opticalLevel.value === null) return 'N/A'
  return `${opticalLevel.value.toFixed(2)} dBm`
}

const getOpticalClass = () => {
  if (opticalLevel.value === null) return ''
  if (opticalLevel.value >= -15) return 'text-online'
  if (opticalLevel.value >= -25) return 'text-warning'
  return 'text-critical'
}

const getOpticalQuality = () => {
  if (opticalLevel.value === null) return ''
  if (opticalLevel.value >= -15) return 'Excelente'
  if (opticalLevel.value >= -20) return 'Bom'
  if (opticalLevel.value >= -25) return 'Regular'
  return 'Crítico'
}

const getAttenuationQuality = () => {
  if (attenuation.value === null) return ''
  if (attenuation.value <= 0.3) return 'Excelente'
  if (attenuation.value <= 0.5) return 'Bom'
  if (attenuation.value <= 1.0) return 'Regular'
  return 'Elevado'
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.quick-modal-container {
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  max-width: 480px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

/* Header */
.quick-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.05) 0%, transparent 100%);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}

.cable-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.cable-icon.status-online {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.cable-icon.status-offline {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.cable-icon.status-warning {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

.cable-icon .icon {
  width: 28px;
  height: 28px;
  color: white;
}

.cable-title h3 {
  margin: 0;
  color: white;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.3;
}

.cable-route {
  margin: 4px 0 0 0;
  color: #94a3b8;
  font-size: 13px;
  line-height: 1.3;
  display: flex;
  align-items: center;
  gap: 6px;
}

.arrow-icon {
  width: 14px;
  height: 14px;
  color: #64748b;
}

.close-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.3);
  color: #fca5a5;
}

.close-btn .icon {
  width: 20px;
  height: 20px;
}

/* Body */
.quick-modal-body {
  padding: 20px;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.info-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  gap: 12px;
  transition: all 0.2s;
}

.info-card:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}

.card-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-icon .icon {
  width: 22px;
  height: 22px;
  color: #60a5fa;
}

.card-icon.status-online {
  background: rgba(16, 185, 129, 0.15);
}

.card-icon.status-online .icon {
  color: #10b981;
}

.card-icon.status-offline {
  background: rgba(239, 68, 68, 0.15);
}

.card-icon.status-offline .icon {
  color: #ef4444;
}

.card-icon.status-warning {
  background: rgba(245, 158, 11, 0.15);
}

.card-icon.status-warning .icon {
  color: #f59e0b;
}

.card-content {
  flex: 1;
  min-width: 0;
}

.card-label {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-value {
  color: white;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.2;
}

.text-online {
  color: #10b981;
}

.text-offline {
  color: #ef4444;
}

.text-warning {
  color: #f59e0b;
}

.text-critical {
  color: #dc2626;
}

.equipment-status {
  display: flex;
  gap: 6px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.status-badge.online {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.status-badge.offline {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.optical-quality {
  color: #94a3b8;
  font-size: 12px;
  margin-top: 4px;
}

.status-detail {
  color: #94a3b8;
  font-size: 12px;
  margin-top: 4px;
}

.notes-text {
  color: #cbd5e1;
  font-size: 13px;
  line-height: 1.5;
  margin-top: 4px;
}

.notes-card {
  grid-column: 1 / -1;
}

.coordinates {
  display: flex;
  gap: 4px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  color: #60a5fa;
  margin-top: 4px;
}

.coord-separator {
  color: #475569;
}

.coordinates-card {
  grid-column: 1 / -1;
}

/* Footer */
.quick-modal-footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.2);
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn-secondary,
.btn-primary {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.2);
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
}

.btn-primary .icon {
  width: 18px;
  height: 18px;
}

/* Animação do modal */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s;
}

.modal-enter-active .quick-modal-container,
.modal-leave-active .quick-modal-container {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .quick-modal-container,
.modal-leave-to .quick-modal-container {
  transform: scale(0.9) translateY(20px);
  opacity: 0;
}

/* Scrollbar */
.quick-modal-body::-webkit-scrollbar {
  width: 8px;
}

.quick-modal-body::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.quick-modal-body::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.quick-modal-body::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* Responsivo */
@media (max-width: 640px) {
  .quick-modal-body {
    grid-template-columns: 1fr;
  }
  
  .coordinates-card {
    grid-column: 1;
  }
}
</style>
