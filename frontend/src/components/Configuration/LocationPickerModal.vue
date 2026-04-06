<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="location-picker-overlay"
      @click.self="handleClose"
    >
      <div class="location-picker-modal">
        <!-- Header -->
        <div class="location-picker-header">
          <div class="flex items-center gap-2">
            <svg class="w-5 h-5 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
            <h3 class="text-base font-semibold text-gray-900 dark:text-white">
              Selecionar Localização Inicial do Mapa
            </h3>
          </div>
          <button @click="handleClose" class="location-picker-close">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Coordinates display -->
        <div class="location-picker-coords">
          <div class="coord-item">
            <span class="coord-label">Latitude</span>
            <span class="coord-value">{{ currentLat.toFixed(6) }}</span>
          </div>
          <div class="coord-divider">·</div>
          <div class="coord-item">
            <span class="coord-label">Longitude</span>
            <span class="coord-value">{{ currentLng.toFixed(6) }}</span>
          </div>
          <div class="coord-hint">
            Clique no mapa ou arraste o marcador para definir a localização
          </div>
        </div>

        <!-- Map container -->
        <div class="location-picker-map-wrap">
          <div ref="mapContainer" class="location-picker-map"></div>

          <!-- Loading overlay -->
          <div v-if="mapLoading" class="location-picker-loading">
            <svg class="animate-spin w-8 h-8 text-primary-500" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
            </svg>
            <span class="mt-2 text-sm text-gray-500 dark:text-gray-400">Carregando mapa...</span>
          </div>

          <!-- Error overlay -->
          <div v-if="mapError" class="location-picker-error">
            <svg class="w-8 h-8 text-red-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
            <p class="text-sm text-red-500">{{ mapError }}</p>
          </div>
        </div>

        <!-- Footer -->
        <div class="location-picker-footer">
          <button @click="handleClose" class="btn-secondary-sm">
            Cancelar
          </button>
          <button @click="handleConfirm" :disabled="mapLoading || !!mapError" class="btn-primary-sm">
            <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
            Confirmar localização
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { createMap } from '@/providers/maps/MapProviderFactory.js'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  lat:    { type: Number, default: -15.7801 },
  lng:    { type: Number, default: -47.9292 },
  zoom:   { type: Number, default: 6 },
})

const emit = defineEmits(['confirm', 'close'])

const mapContainer = ref(null)
const mapInstance  = ref(null)
const mapMarker    = ref(null)
const mapLoading   = ref(false)
const mapError     = ref('')
const currentLat   = ref(props.lat)
const currentLng   = ref(props.lng)

// ── Map init ────────────────────────────────────────────────────────────────
async function initMap() {
  if (!mapContainer.value) return

  mapLoading.value = true
  mapError.value   = ''
  currentLat.value = props.lat
  currentLng.value = props.lng

  try {
    mapInstance.value = await createMap(mapContainer.value, {
      center: { lat: currentLat.value, lng: currentLng.value },
      zoom: props.zoom,
    })

    mapMarker.value = mapInstance.value.createMarker({
      position: { lat: currentLat.value, lng: currentLng.value },
      draggable: true,
      title: 'Localização inicial do mapa',
    })

    mapMarker.value.on('dragend', ({ lat, lng }) => {
      currentLat.value = lat
      currentLng.value = lng
    })

    mapInstance.value.on('click', ({ lat, lng }) => {
      currentLat.value = lat
      currentLng.value = lng
      mapMarker.value.setPosition({ lat, lng })
    })

    mapLoading.value = false
  } catch (err) {
    console.error('[LocationPickerModal] Map error:', err)
    mapError.value   = err.message || 'Erro ao carregar o mapa'
    mapLoading.value = false
  }
}

function destroyMap() {
  mapMarker.value   = null
  mapInstance.value = null
}

// ── Actions ──────────────────────────────────────────────────────────────────
function handleConfirm() {
  emit('confirm', { lat: currentLat.value, lng: currentLng.value })
}

function handleClose() {
  emit('close')
}

// ── Lifecycle ────────────────────────────────────────────────────────────────
watch(() => props.isOpen, async (open) => {
  if (open) {
    destroyMap()
    await nextTick()
    await initMap()
  } else {
    destroyMap()
  }
})

watch(() => [props.lat, props.lng], ([lat, lng]) => {
  currentLat.value = lat
  currentLng.value = lng
})
</script>

<style scoped>
.location-picker-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.location-picker-modal {
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 780px;
  max-height: 90vh;
  overflow: hidden;
}

:global(.dark) .location-picker-modal {
  background: #1f2937;
}

.location-picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #e5e7eb;
}

:global(.dark) .location-picker-header {
  border-color: #374151;
}

.location-picker-close {
  padding: 0.25rem;
  border-radius: 0.375rem;
  color: #6b7280;
  transition: background 0.15s, color 0.15s;
}
.location-picker-close:hover {
  background: #f3f4f6;
  color: #111827;
}
:global(.dark) .location-picker-close:hover {
  background: #374151;
  color: #f9fafb;
}

.location-picker-coords {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 1.25rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  flex-wrap: wrap;
}
:global(.dark) .location-picker-coords {
  background: #111827;
  border-color: #374151;
}

.coord-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}
.coord-label {
  font-size: 0.75rem;
  color: #6b7280;
  font-weight: 500;
}
.coord-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: #111827;
  font-family: monospace;
}
:global(.dark) .coord-value {
  color: #f9fafb;
}
.coord-divider {
  color: #d1d5db;
  font-size: 1rem;
}
.coord-hint {
  margin-left: auto;
  font-size: 0.7rem;
  color: #9ca3af;
  font-style: italic;
}

.location-picker-map-wrap {
  position: relative;
  flex: 1;
  min-height: 420px;
}

.location-picker-map {
  width: 100%;
  height: 100%;
  min-height: 420px;
}

.location-picker-loading,
.location-picker-error {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.85);
}
:global(.dark) .location-picker-loading,
:global(.dark) .location-picker-error {
  background: rgba(17, 24, 39, 0.85);
}

.location-picker-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 0.875rem 1.25rem;
  border-top: 1px solid #e5e7eb;
}
:global(.dark) .location-picker-footer {
  border-color: #374151;
}

.btn-primary-sm {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  background: #0ea5e9;
  color: white;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  transition: background 0.15s;
}
.btn-primary-sm:hover:not(:disabled) { background: #0284c7; }
.btn-primary-sm:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary-sm {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  background: white;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background 0.15s;
}
.btn-secondary-sm:hover { background: #f9fafb; }
:global(.dark) .btn-secondary-sm {
  background: #374151;
  color: #f9fafb;
  border-color: #4b5563;
}
:global(.dark) .btn-secondary-sm:hover { background: #4b5563; }
</style>
