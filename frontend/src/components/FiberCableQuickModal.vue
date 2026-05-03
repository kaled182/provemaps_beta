<template>
  <Teleport to="body">
    <Transition name="modal-float">
      <div
        v-if="show && cable"
        ref="modalEl"
        class="quick-modal-container"
        :class="{ dragging: isDragging }"
        :style="modalStyle"
        @click.stop
      >
        <!-- Header — alça de arrastar -->
        <div
          class="quick-modal-header"
          @mousedown.prevent="startDrag"
          @touchstart.passive="startDrag"
          title="Arraste para mover"
        >
          <div class="drag-grip" aria-hidden="true">
            <span></span><span></span><span></span>
          </div>

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

          <button class="close-btn" @click.stop="closeModal" title="Fechar (ESC)">
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
              <div class="status-detail">{{ cable.status || 'N/A' }}</div>
            </div>
          </div>

          <!-- Distância -->
          <div class="info-card distance-card">
            <div class="card-icon">
              <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z" />
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
              <div class="card-value" :class="getOpticalClass()">{{ formatOpticalLevel() }}</div>
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
              <div class="card-label">Atenuação Estimada</div>
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
          <button class="btn-secondary" @click="closeModal">Fechar</button>
          <button v-if="cable.id" class="btn-primary" @click="openFullDetails">
            <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Ver Detalhes Completos
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { useEscapeKey } from '@/composables/useEscapeKey'

const props = defineProps({
  show: { type: Boolean, default: false },
  cable: { type: Object, default: null },
})

const emit = defineEmits(['close', 'openFullDetails'])

useEscapeKey(() => { if (props.show) closeModal() })

const closeModal = () => emit('close')
const openFullDetails = () => emit('openFullDetails', props.cable)

// ── Drag state ──────────────────────────────────────────────────────────────
const modalEl = ref(null)
const pos = ref({ x: 0, y: 0 })
const isDragging = ref(false)
const dragOrigin = { mouseX: 0, mouseY: 0, posX: 0, posY: 0 }

const MODAL_W = 480   // approx modal width
const MODAL_H = 440   // approx modal height

const initPosition = () => {
  const vw = window.innerWidth
  const vh = window.innerHeight
  const w = Math.min(MODAL_W, vw - 32)
  const h = Math.min(MODAL_H, vh - 80)
  pos.value = {
    x: Math.max(8, Math.round((vw - w) / 2)),
    y: Math.max(8, Math.round((vh - h) / 2.2)),
  }
}

const modalStyle = computed(() => ({
  left: `${pos.value.x}px`,
  top: `${pos.value.y}px`,
}))

const clientXY = (e) => {
  if (e.touches && e.touches.length) {
    return { x: e.touches[0].clientX, y: e.touches[0].clientY }
  }
  return { x: e.clientX, y: e.clientY }
}

const startDrag = (e) => {
  const { x, y } = clientXY(e)
  dragOrigin.mouseX = x
  dragOrigin.mouseY = y
  dragOrigin.posX = pos.value.x
  dragOrigin.posY = pos.value.y
  isDragging.value = true
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchmove', onDrag, { passive: false })
  document.addEventListener('touchend', stopDrag)
}

const onDrag = (e) => {
  if (!isDragging.value) return
  if (e.cancelable) e.preventDefault()
  const { x, y } = clientXY(e)
  const dx = x - dragOrigin.mouseX
  const dy = y - dragOrigin.mouseY
  const vw = window.innerWidth
  const vh = window.innerHeight
  pos.value = {
    x: Math.max(0, Math.min(vw - 120, dragOrigin.posX + dx)),
    y: Math.max(0, Math.min(vh - 60, dragOrigin.posY + dy)),
  }
}

const stopDrag = () => {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)
}

// `immediate: true` cobre o caso em que o componente é montado já com show=true
// (parent usa lazy v-if → não há transição false→true para observar)
watch(() => props.show, (val) => { if (val) initPosition() }, { immediate: true })
onUnmounted(stopDrag)

// ── Cable data ───────────────────────────────────────────────────────────────
const cableStatus = computed(() => {
  if (!props.cable) return 'unknown'
  return String(props.cable.status || 'unknown').toLowerCase()
})

const opticalLevel = computed(() => {
  if (props.cable?.optical_level !== undefined) return props.cable.optical_level
  return null
})

const attenuation = computed(() => {
  if (props.cable?.attenuation !== undefined) return props.cable.attenuation
  return null
})

const getStatusLabel = (status) => ({
  up: 'ONLINE',
  online: 'ONLINE',
  down: 'INOPERANTE',
  offline: 'OFFLINE',
  degraded: 'DEGRADADO',
  warning: 'ATENÇÃO',
  critical: 'CRÍTICO',
  unknown: 'DESCONHECIDO',
}[status] || 'DESCONHECIDO')

const formatDistance = () => {
  if (!props.cable) return 'N/A'
  if (props.cable.length_km) return `${props.cable.length_km} km`
  if (props.cable.length_meters) return `${props.cable.length_meters} m`
  return 'N/A'
}

const formatOpticalLevel = () => {
  if (opticalLevel.value === null) return 'N/A'
  return `${opticalLevel.value.toFixed(2)} dBm`
}

const getOpticalClass = () => {
  if (opticalLevel.value === null) return ''
  if (opticalLevel.value >= -15) return 'text-up'
  if (opticalLevel.value >= -25) return 'text-warning'
  return 'text-down'
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
/* ── Container flutuante (sem overlay) ─────────────────────────────────────── */
.quick-modal-container {
  position: fixed;
  z-index: 9999;
  width: min(480px, calc(100vw - 16px));
  max-height: min(520px, calc(100vh - 32px));
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-radius: 16px;
  box-shadow:
    0 24px 48px -12px rgba(0, 0, 0, 0.7),
    0 0 0 1px rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  /* Sombra de borda luminosa sutil para destacar sobre o mapa */
  outline: 1px solid rgba(99, 102, 241, 0.25);
  transition: box-shadow 0.15s;
}

.quick-modal-container.dragging {
  box-shadow:
    0 32px 64px -12px rgba(0, 0, 0, 0.85),
    0 0 0 2px rgba(99, 102, 241, 0.5);
  cursor: grabbing;
}

/* ── Header / alça de arraste ──────────────────────────────────────────────── */
.quick-modal-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.04) 0%, transparent 100%);
  cursor: grab;
  user-select: none;
  -webkit-user-select: none;
  touch-action: none;
  flex-shrink: 0;
}

.quick-modal-header:active {
  cursor: grabbing;
}

/* Grip de 3 linhas — indica que é arrastável */
.drag-grip {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex-shrink: 0;
  opacity: 0.4;
}

.drag-grip span {
  display: block;
  width: 18px;
  height: 2px;
  background: #94a3b8;
  border-radius: 1px;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.cable-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.cable-icon.status-up,
.cable-icon.status-online {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.cable-icon.status-down,
.cable-icon.status-offline {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.cable-icon.status-degraded,
.cable-icon.status-warning {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

.cable-icon.status-critical {
  background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
}

.cable-icon .icon {
  width: 22px;
  height: 22px;
  color: white;
}

.cable-title {
  min-width: 0;
}

.cable-title h3 {
  margin: 0;
  color: white;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cable-route {
  margin: 2px 0 0;
  color: #94a3b8;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.arrow-icon {
  width: 12px;
  height: 12px;
  color: #64748b;
  flex-shrink: 0;
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  flex-shrink: 0;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.3);
  color: #fca5a5;
}

.close-btn .icon {
  width: 16px;
  height: 16px;
}

/* ── Body ──────────────────────────────────────────────────────────────────── */
.quick-modal-body {
  padding: 14px;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  flex: 1;
  min-height: 0;
}

.info-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 12px;
  display: flex;
  gap: 10px;
  transition: background 0.15s;
}

.info-card:hover {
  background: rgba(255, 255, 255, 0.08);
}

.card-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(59, 130, 246, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-icon .icon {
  width: 18px;
  height: 18px;
  color: #60a5fa;
}

.card-icon.status-up .icon,
.card-icon.status-online .icon  { color: #10b981; }
.card-icon.status-up,
.card-icon.status-online         { background: rgba(16, 185, 129, 0.15); }

.card-icon.status-down .icon,
.card-icon.status-offline .icon { color: #ef4444; }
.card-icon.status-down,
.card-icon.status-offline        { background: rgba(239, 68, 68, 0.15); }

.card-icon.status-degraded .icon,
.card-icon.status-warning .icon { color: #f59e0b; }
.card-icon.status-degraded,
.card-icon.status-warning        { background: rgba(245, 158, 11, 0.15); }

.card-icon.status-critical .icon { color: #dc2626; }
.card-icon.status-critical        { background: rgba(220, 38, 38, 0.15); }

.card-content {
  flex: 1;
  min-width: 0;
}

.card-label {
  color: #64748b;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  margin-bottom: 3px;
}

.card-value {
  color: white;
  font-size: 17px;
  font-weight: 700;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-detail,
.optical-quality {
  color: #64748b;
  font-size: 11px;
  margin-top: 2px;
}

.text-up,
.text-online  { color: #10b981; }
.text-down,
.text-offline { color: #ef4444; }
.text-degraded,
.text-warning  { color: #f59e0b; }
.text-critical { color: #dc2626; }
.text-unknown  { color: #6b7280; }

.notes-card,
.coordinates-card {
  grid-column: 1 / -1;
}

.notes-text {
  color: #cbd5e1;
  font-size: 12px;
  line-height: 1.5;
  margin-top: 3px;
}

/* ── Footer ────────────────────────────────────────────────────────────────── */
.quick-modal-footer {
  padding: 12px 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.25);
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  flex-shrink: 0;
}

.btn-secondary,
.btn-primary {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  border: none;
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.08);
  color: #94a3b8;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.13);
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  box-shadow: 0 4px 10px rgba(59, 130, 246, 0.3);
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(59, 130, 246, 0.4);
}

.btn-primary .icon {
  width: 15px;
  height: 15px;
}

/* ── Scrollbar ─────────────────────────────────────────────────────────────── */
.quick-modal-body::-webkit-scrollbar { width: 5px; }
.quick-modal-body::-webkit-scrollbar-track { background: transparent; }
.quick-modal-body::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 4px;
}

/* ── Animação de entrada ───────────────────────────────────────────────────── */
.modal-float-enter-active {
  transition: opacity 0.18s ease, transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.modal-float-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.modal-float-enter-from {
  opacity: 0;
  transform: scale(0.92) translateY(10px);
}
.modal-float-leave-to {
  opacity: 0;
  transform: scale(0.96) translateY(6px);
}

/* ── Responsivo mobile ─────────────────────────────────────────────────────── */
@media (max-width: 520px) {
  .quick-modal-container {
    /* Em telas muito pequenas, ancora na parte inferior centralizado */
    width: calc(100vw - 16px) !important;
    left: 8px !important;
    /* top é controlado pelo JS, mas garante que não saia da tela */
    max-height: 72vh;
    border-radius: 14px 14px 10px 10px;
  }

  .quick-modal-body {
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    padding: 10px;
  }

  .card-value {
    font-size: 15px;
  }

  .cable-title h3 {
    font-size: 13px;
  }

  .btn-secondary,
  .btn-primary {
    font-size: 12px;
    padding: 8px 12px;
  }
}

@media (max-width: 360px) {
  .quick-modal-body {
    grid-template-columns: 1fr;
  }

  .notes-card,
  .coordinates-card {
    grid-column: 1;
  }
}
</style>
