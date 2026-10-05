<template>
  <div class="map-canvas-wrapper">
    <div ref="container" class="map-canvas"></div>

    <!-- Overlays Vue (MapPopup, controlos) por cima do mapa -->
    <slot :map="map" />

    <div v-if="loading" class="map-canvas-state" role="status">
      <div class="map-canvas-spinner" aria-hidden="true"></div>
      <p>Carregando mapa...</p>
    </div>

    <div v-else-if="error" class="map-canvas-state map-canvas-error" role="alert">
      <p>{{ error }}</p>
      <button type="button" @click="init">Tentar novamente</button>
    </div>
  </div>
</template>

<script setup>
/**
 * MapCanvas — um mapa do provider configurado, pronto a receber overlays.
 *
 * Substitui a `UnifiedMapView` (EV-0012d): cria o mapa pela
 * `MapProviderFactory`, emite `ready(map)` com a instância `IMap` e
 * destrói-a ao desmontar. Quem precisa de desenhar usa `useRouteDrawing`;
 * quem precisa de janelas usa `MapPopup` dentro do slot.
 */
import { ref, shallowRef, onMounted, onBeforeUnmount } from 'vue';
import { createMap, getMapConfig } from '@/providers/maps/MapProviderFactory.js';

const props = defineProps({
  /** Centro inicial; por omissão o da configuração do backend */
  center: { type: Object, default: null },
  /** Zoom inicial; por omissão o da configuração do backend */
  zoom: { type: Number, default: null },
  mapTypeId: { type: String, default: 'roadmap' },
  /** MapControls (ver IMapProvider) */
  controls: { type: Object, default: () => ({}) },
});

const emit = defineEmits(['ready', 'error']);

const DEFAULT_CENTER = { lat: -15.7801, lng: -47.9292 };
const DEFAULT_ZOOM = 12;

const container = ref(null);
const map = shallowRef(null);
const loading = ref(false);
const error = ref(null);

async function init() {
  if (!container.value || map.value) return;
  loading.value = true;
  error.value = null;
  try {
    const config = await getMapConfig();
    const cfgLat = Number(config.mapDefaultLat);
    const cfgLng = Number(config.mapDefaultLng);
    const cfgZoom = Number(config.mapDefaultZoom);

    const center = props.center
      || (Number.isFinite(cfgLat) && Number.isFinite(cfgLng) ? { lat: cfgLat, lng: cfgLng } : DEFAULT_CENTER);
    const zoom = props.zoom ?? (Number.isFinite(cfgZoom) && cfgZoom > 0 ? cfgZoom : DEFAULT_ZOOM);

    const created = await createMap(container.value, {
      center,
      zoom,
      mapTypeId: props.mapTypeId,
      controls: props.controls,
    });
    map.value = created;
    emit('ready', created);
  } catch (err) {
    error.value = `Mapa indisponível: ${err?.message || err}`;
    console.error('[MapCanvas] Failed to create map', err);
    emit('error', err);
  } finally {
    loading.value = false;
  }
}

function destroy() {
  if (map.value) {
    try { map.value.destroy(); } catch (_) { /* best-effort */ }
    map.value = null;
  }
}

onMounted(init);
onBeforeUnmount(destroy);

defineExpose({ map, getMap: () => map.value });
</script>

<style scoped>
.map-canvas-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.map-canvas {
  width: 100%;
  height: 100%;
}

.map-canvas-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  background: var(--surface-card);
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
  padding: 20px 28px;
  border-radius: 8px;
  box-shadow: var(--shadow-lg, 0 10px 25px rgba(0, 0, 0, 0.2));
  z-index: 10;
}

.map-canvas-error {
  color: var(--accent-danger);
}

.map-canvas-error button {
  margin-top: 10px;
  padding: 6px 14px;
  border: 1px solid var(--accent-danger);
  background: transparent;
  color: var(--accent-danger);
  border-radius: 6px;
  cursor: pointer;
}

.map-canvas-spinner {
  width: 32px;
  height: 32px;
  margin: 0 auto 12px;
  border: 3px solid var(--border-primary);
  border-top-color: var(--accent-primary, currentColor);
  border-radius: 50%;
  animation: map-canvas-spin 1s linear infinite;
}

@keyframes map-canvas-spin {
  to { transform: rotate(360deg); }
}
</style>
