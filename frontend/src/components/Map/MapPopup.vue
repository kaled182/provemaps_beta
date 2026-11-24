<template>
  <div
    v-if="pixel"
    class="map-popup"
    :class="{ 'map-popup-bare': bare }"
    :style="{ left: `${pixel.x}px`, top: `${pixel.y}px` }"
    :role="bare ? undefined : 'dialog'"
  >
    <slot v-if="bare" />
    <template v-else>
      <div class="map-popup-content">
        <slot />
      </div>
      <div class="map-popup-arrow" aria-hidden="true"></div>
    </template>
  </div>
</template>

<script setup>
/**
 * MapPopup — janela ancorada numa coordenada, independente do provider.
 *
 * Substitui o `InfoWindow` do Google: o conteúdo é Vue normal (slot) e a
 * posição vem de `IMap.latLngToPixel`, recalculada a cada `move` do mapa.
 * Vive dentro do `.map-wrapper` (position: relative) do componente pai.
 */
import { ref, watch, onBeforeUnmount } from 'vue';

const props = defineProps({
  /** Instância IMap (providers/maps) */
  map: { type: Object, required: true },
  /** Âncora geográfica {lat, lng} */
  position: { type: Object, required: true },
  /** Distância em px entre a âncora e a base da janela */
  offsetY: { type: Number, default: 10 },
  /** EV-0127: sem caixa nem seta, centrado na coordenada (marcadores Vue, ex. o pino OTDR) */
  bare: { type: Boolean, default: false },
});

const pixel = ref(null);

function reproject() {
  const point = props.map?.latLngToPixel?.(props.position);
  pixel.value = point ? { x: point.x, y: point.y - (props.bare ? 0 : props.offsetY) } : null;
}

let boundMap = null;
function bind(map) {
  if (boundMap === map) return;
  boundMap?.off?.('move', reproject);
  boundMap = map || null;
  boundMap?.on?.('move', reproject);
}

watch(
  () => [props.map, props.position?.lat, props.position?.lng],
  () => {
    bind(props.map);
    reproject();
  },
  { immediate: true },
);

onBeforeUnmount(() => bind(null));
</script>

<style scoped>
.map-popup {
  position: absolute;
  z-index: 20;
  transform: translate(-50%, -100%);
  pointer-events: auto;
}

.map-popup-bare {
  z-index: 19;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.map-popup-content {
  background: var(--surface-card);
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  box-shadow: var(--shadow-lg, 0 10px 25px rgba(0, 0, 0, 0.2));
  max-width: 340px;
  max-height: 60vh;
  overflow: auto;
}

.map-popup-arrow {
  width: 0;
  height: 0;
  margin: 0 auto;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 8px solid var(--surface-card);
}
</style>
