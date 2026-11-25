<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-[9999] overflow-y-auto"
    >
      <div class="flex min-h-screen items-center justify-center p-4">
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black/50 transition-opacity" @click="handleClose"></div>

        <!-- Modal -->
        <div class="relative bg-surface rounded-xl shadow-2xl w-full max-w-3xl flex flex-col overflow-hidden border border-neutral-200">

          <!-- Header -->
          <div class="flex items-center justify-between px-5 py-4 border-b border-neutral-200">
            <div class="flex items-center gap-2">
              <svg class="w-5 h-5 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              <h3 class="text-base font-semibold text-neutral-900">
                Selecionar Localização Inicial do Mapa
              </h3>
            </div>
            <button @click="handleClose" class="p-1 rounded-md text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Coordinates display -->
          <div class="flex items-center gap-3 px-5 py-2.5 bg-neutral-50 border-b border-neutral-200 flex-wrap">
            <div class="flex items-center gap-1.5">
              <span class="text-xs font-medium text-neutral-500">Latitude</span>
              <span class="text-sm font-semibold font-mono text-neutral-900">{{ currentLat.toFixed(6) }}</span>
            </div>
            <div class="text-neutral-300">·</div>
            <div class="flex items-center gap-1.5">
              <span class="text-xs font-medium text-neutral-500">Longitude</span>
              <span class="text-sm font-semibold font-mono text-neutral-900">{{ currentLng.toFixed(6) }}</span>
            </div>
            <div class="ml-auto text-xs italic text-neutral-400">
              Clique no mapa ou arraste o marcador para definir a localização
            </div>
          </div>

          <!-- Map container -->
          <div class="relative" style="min-height: 420px; flex: 1;">
            <div ref="mapContainer" style="width: 100%; height: 100%; min-height: 420px;"></div>

            <!-- Loading overlay -->
            <div v-if="mapLoading" class="absolute inset-0 flex flex-col items-center justify-center bg-surface" style="opacity: 0.92;">
              <svg class="animate-spin w-8 h-8 text-primary-500" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
              <span class="mt-2 text-sm text-neutral-500">Carregando mapa...</span>
            </div>

            <!-- Error overlay -->
            <div v-if="mapError" class="absolute inset-0 flex flex-col items-center justify-center bg-surface">
              <svg class="w-8 h-8 text-danger mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
              </svg>
              <p class="text-sm text-danger">{{ mapError }}</p>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex justify-end gap-3 px-5 py-3.5 border-t border-neutral-200">
            <button @click="handleClose" class="inline-flex items-center px-4 py-2 bg-surface text-neutral-900 text-sm font-medium rounded-lg border border-neutral-300 hover:bg-neutral-50 transition-colors">
              Cancelar
            </button>
            <button @click="handleConfirm" :disabled="mapLoading || !!mapError" class="inline-flex items-center px-4 py-2 bg-sky-500 hover:bg-sky-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors">
              <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
              Confirmar localização
            </button>
          </div>

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
