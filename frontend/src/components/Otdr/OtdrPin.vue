<template>
  <span class="pin" aria-label="Rompimento OTDR" data-testid="otdr-pin">
    <span class="pin-pulse" aria-hidden="true" />
    <span class="pin-core" aria-hidden="true" />
  </span>
</template>

<script setup>
/** Marcador pulsante do ponto OTDR (EV-0127), desenhado em Vue sobre o mapa (MapPopup bare). */
</script>

<style scoped>
.pin {
  position: relative;
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
