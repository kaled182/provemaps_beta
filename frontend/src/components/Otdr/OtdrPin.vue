<template>
  <span class="pin" role="button" tabindex="0" aria-label="Rompimento OTDR — abrir o cartão" data-testid="otdr-pin" @click="$emit('open')" @keydown.enter.prevent="$emit('open')">
    <span class="pin-pulse" aria-hidden="true" />
    <span class="pin-core" aria-hidden="true" />
  </span>
</template>

<script setup>
/** Marcador pulsante do ponto OTDR (EV-0127), desenhado em Vue sobre o mapa (MapPopup bare);
 * clicável (EV-0128) para reabrir o cartão. */
defineEmits(['open'])
</script>

<style scoped>
.pin {
  position: relative;
  cursor: pointer;
  pointer-events: auto;
  display: block;
  width: 18px;
  height: 18px;
}
.pin-core,
.pin-pulse {
  position: absolute;
  inset: 0;
  border-radius: 999px;
  background: rgb(var(--danger));
}
.pin-core {
  border: 3px solid rgb(var(--surface));
  box-shadow: 0 0 0 1px rgb(var(--danger)), 0 2px 6px rgb(var(--n-950) / 0.4);
}
.pin-pulse {
  animation: otdr-pulse 1.4s ease-out infinite;
}
@keyframes otdr-pulse {
  0% {
    transform: scale(1);
    opacity: 0.7;
  }
  100% {
    transform: scale(3.2);
    opacity: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .pin-pulse {
    animation: none;
    opacity: 0.3;
    transform: scale(1.8);
  }
}
</style>
