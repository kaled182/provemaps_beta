<template>
  <!-- Faixa de legenda no rodapé interno da moldura (EV-0106): LEDs e portas PON ativas/livres. -->
  <g class="legend" data-testid="chassis-legend">
    <rect :x="x" :y="y" :width="w" :height="h" rx="3" class="legend-band" />
    <g v-for="(item, i) in ITEMS" :key="item.led" :class="`led-${item.led}`">
      <circle :cx="x + 12 + i * STEP" :cy="y + h / 2" r="3.2" class="legend-led" />
      <text :x="x + 19 + i * STEP" :y="y + h / 2 + 3" class="legend-text">{{ item.label }}</text>
    </g>
    <text :x="x + w - 10" :y="y + h / 2 + 3" class="legend-text legend-count" text-anchor="end" data-testid="chassis-legend-count">
      {{ active }} PON ativas · {{ free }} livres
    </text>
  </g>
</template>

<script setup>
/** Legenda compacta dos LEDs do chassi, desenhada dentro do SVG do chassi (C300/C600/C610 e 1U). */
defineProps({
  x: { type: Number, required: true },
  y: { type: Number, required: true },
  w: { type: Number, required: true },
  h: { type: Number, default: 16 },
  active: { type: Number, default: 0 },
  free: { type: Number, default: 0 },
})

const STEP = 150
const ITEMS = [
  { led: 'ok', label: 'Normal' },
  { led: 'warning', label: 'Atenção / > 85%' },
  { led: 'critical', label: 'Queda massiva / down' },
  { led: 'off', label: 'Sem ONUs' },
]
</script>

<style scoped>
.legend-band {
  fill: rgb(var(--chassis-bay));
  stroke: rgb(var(--chassis-border));
}
.legend-text {
  font-family: var(--font-mono);
  font-size: 9px;
  fill: rgb(var(--chassis-text-dim));
}
.legend-count {
  fill: rgb(var(--chassis-text));
}
.legend-led {
  fill: rgb(var(--chassis-edge));
  stroke: rgb(var(--chassis-bay));
  stroke-width: 0.6;
}
.led-ok .legend-led {
  fill: rgb(var(--success));
}
.led-warning .legend-led {
  fill: rgb(var(--warning));
}
.led-critical .legend-led {
  fill: rgb(var(--danger));
}
</style>
