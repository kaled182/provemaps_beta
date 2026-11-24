<template>
  <svg
    class="chassis"
    :viewBox="`0 0 ${W} ${H}`"
    width="100%"
    preserveAspectRatio="xMidYMid meet"
    role="group"
    :aria-label="`Vista frontal da OLT ${brand} ${model}`.trim()"
    data-testid="chassis-1u"
  >
    <defs>
      <linearGradient :id="`${uid}-body`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" class="stop-hi" />
        <stop offset="0.55" class="stop-mid" />
        <stop offset="1" class="stop-lo" />
      </linearGradient>
    </defs>

    <!-- orelhas de rack -->
    <g v-for="ex in [0, W - EAR]" :key="ex">
      <rect :x="ex" y="4" :width="EAR" :height="H - 8" rx="3" class="ear" />
      <rect :x="ex + EAR / 2 - 3.5" y="22" width="7" height="12" rx="3.5" class="ear-hole" />
      <rect :x="ex + EAR / 2 - 3.5" :y="H - 34" width="7" height="12" rx="3.5" class="ear-hole" />
    </g>

    <!-- corpo -->
    <rect :x="EAR" y="8" :width="W - 2 * EAR" :height="H - 16" rx="3" class="body" :fill="`url(#${uid}-body)`" />
    <line :x1="EAR + 2" y1="9.5" :x2="W - EAR - 2" y2="9.5" class="body-light" />

    <!-- marca e LED do sistema (estado da OLT no payload) -->
    <text :x="EAR + 18" y="50" class="brand">{{ brand }}</text>
    <text :x="EAR + 18" y="68" class="model">{{ model }}</text>
    <text v-if="tech" :x="EAR + 18" y="84" class="tech">{{ tech }} · {{ ports.length }} PON</text>
    <circle :cx="EAR + 24" cy="104" r="3" :class="['led', `led-${sysLed}`]" data-testid="chassis-1u-sys" />
    <text :x="EAR + 32" y="106.5" class="led-label">SYS</text>

    <!-- portas PON -->
    <rect :x="PORTS_X - 10" y="18" :width="portsW + 20" :height="H - 36" rx="3" class="port-panel" />
    <text v-if="!ports.length" :x="PORTS_X + 12" :y="H / 2 + 3" class="empty-note" data-testid="chassis-1u-empty">
      Sem portas PON conhecidas
    </text>
    <g
      v-for="p in ports"
      :key="p.port_id"
      :class="['port', `led-${p.led}`, { 'port-selected': p.selected, 'port-dim': p.dim }]"
      :data-testid="`chassis-port-${p.port_id}`"
      role="button"
      tabindex="0"
      :aria-pressed="p.selected"
      :aria-label="p.text"
      @click="$emit('toggle-pon', p.port_id)"
      @keydown.enter.prevent="$emit('toggle-pon', p.port_id)"
      @keydown.space.prevent="$emit('toggle-pon', p.port_id)"
      @mouseenter="hover($event, p.text)"
      @focus="hover($event, p.text)"
      @mouseleave="$emit('hover', null)"
      @blur="$emit('hover', null)"
    >
      <rect :x="p.x" :y="p.y" :width="p.w" :height="ROW_H" rx="2" class="hit" />
      <text :x="p.x + p.w / 2" :y="p.top ? p.y + 10 : p.y + ROW_H - 3" class="port-num" text-anchor="middle">{{ p.port }}</text>
      <circle :cx="p.x + 7" :cy="p.sfpY + SFP_H / 2" r="2.6" class="led" />
      <rect :x="p.x + 13" :y="p.sfpY" :width="p.w - 18" :height="SFP_H" rx="1.5" class="sfp" />
      <rect :x="p.x + 16" :y="p.sfpY + 3" :width="p.w - 24" :height="SFP_H - 6" rx="0.8" class="sfp-hole" />
    </g>

    <!-- grelha de ventilação (decorativa) -->
    <g>
      <rect
        v-for="v in vents"
        :key="v.k"
        :x="v.x"
        :y="v.y"
        width="14"
        height="4"
        rx="2"
        class="vent"
      />
    </g>
  </svg>
</template>

<script setup>
/**
 * Painel frontal 1U (VSOL e o resto, EV-0101): só as portas PON de `chassis.ports`
 * (até 8 numa fila, mais do que isso em duas). Nada de placas — a VSOL não as tem.
 * Mesma paleta `--chassis-*` (grafite fixo, EV-0102) da C300.
 */
import { computed, useId } from 'vue'
import { indexPons, ponLed, ponTooltip } from './chassisLed'

const props = defineProps({
  chassis: { type: Object, required: true },
  pons: { type: Array, default: () => [] },
  olt: { type: Object, default: () => ({}) },
  visiblePonIds: { type: Array, default: null },
  selectedPort: { type: String, default: null },
})
const emit = defineEmits(['toggle-pon', 'hover'])

const W = 960
const H = 132
const EAR = 24
const PORTS_X = 200
const PORTS_MAX_W = 560
const ROW_H = 46
const SFP_H = 18
const uid = `r1u-${useId()}`

const brand = computed(() => (props.olt.vendor || '').toUpperCase())
const model = computed(() => props.olt.model || '')
const tech = computed(() => (props.olt.technology || '').toUpperCase())
const sysLed = computed(() => ({ online: 'ok', offline: 'critical' })[props.olt.status] || 'off')

const ponIdx = computed(() => indexPons(props.pons))
const visibleSet = computed(() => (props.visiblePonIds ? new Set(props.visiblePonIds.map(String)) : null))

const ports = computed(() => {
  const list = [...(props.chassis.ports || [])].sort((a, b) => a.port - b.port)
  const rows = list.length > 8 ? 2 : 1
  const cols = Math.max(1, Math.ceil(list.length / rows))
  const w = Math.min(66, PORTS_MAX_W / cols)
  const y0 = rows === 1 ? (H - ROW_H) / 2 : 20
  return list.map((p, i) => {
    const row = rows === 1 ? 0 : i % 2
    const col = rows === 1 ? i : Math.floor(i / 2)
    const pon = ponIdx.value.get(String(p.port_id))
    const y = y0 + row * ROW_H
    const top = row === 0
    return {
      ...p,
      x: PORTS_X + col * w,
      y,
      w: w - 4,
      top,
      sfpY: top ? y + 15 : y + 6,
      led: ponLed(pon),
      text: ponTooltip(p.port_id, pon, p.status),
      selected: props.selectedPort === String(p.port_id),
      dim: visibleSet.value !== null && !visibleSet.value.has(String(p.port_id)),
    }
  })
})

const portsW = computed(() => {
  return ports.value.length ? Math.max(...ports.value.map((p) => p.x + p.w)) - PORTS_X : 180
})

const vents = (() => {
  const out = []
  for (let r = 0; r < 9; r++) for (let c = 0; c < 6; c++) out.push({ k: `${r}-${c}`, x: 790 + c * 20 + (r % 2) * 10, y: 22 + r * 10 })
  return out
})()

function hover(event, text) {
  emit('hover', { text, el: event.currentTarget })
}
</script>

<style scoped>
.chassis {
  display: block;
  height: auto;
  font-family: var(--font-mono);
  user-select: none;
}
.stop-hi {
  stop-color: rgb(var(--chassis-plate-hi));
}
.stop-mid {
  stop-color: rgb(var(--chassis-plate));
}
.stop-lo {
  stop-color: rgb(var(--chassis-plate-lo));
}
.ear {
  fill: rgb(var(--chassis-body));
  stroke: rgb(var(--chassis-border));
}
.ear-hole {
  fill: rgb(var(--chassis-bay));
}
.body {
  stroke: rgb(var(--chassis-border));
  stroke-width: 1.2;
}
.body-light {
  stroke: rgb(var(--chassis-edge));
}
.brand {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 18px;
  fill: rgb(var(--chassis-text));
  letter-spacing: 1px;
}
.model {
  font-size: 11px;
  fill: rgb(var(--chassis-text-dim));
}
.tech {
  font-size: 9px;
  fill: rgb(var(--chassis-text-mute));
}
.led-label {
  font-size: 7px;
  fill: rgb(var(--chassis-text-mute));
}
.port-panel {
  fill: rgb(var(--chassis-bay) / 0.6);
  stroke: rgb(var(--chassis-edge));
}
.empty-note {
  font-size: 11px;
  fill: rgb(var(--chassis-text-mute));
}
.port {
  cursor: pointer;
}
.port:focus {
  outline: none;
}
.hit {
  fill: transparent;
}
.port:hover .hit,
.port:focus-visible .hit {
  fill: rgb(var(--primary-500) / 0.16);
  stroke: rgb(var(--primary-400));
  stroke-width: 0.8;
}
.port-selected .hit {
  fill: rgb(var(--primary-500) / 0.28);
  stroke: rgb(var(--primary-500));
  stroke-width: 1.2;
}
.port-selected .sfp {
  stroke: rgb(var(--primary-400));
}
.port-dim {
  opacity: 0.32;
}
.port-num {
  font-size: 8px;
  fill: rgb(var(--chassis-text-dim));
}
.sfp {
  fill: rgb(var(--chassis-edge));
  stroke: rgb(var(--chassis-edge));
  stroke-width: 0.8;
}
.sfp-hole {
  fill: rgb(var(--chassis-bay));
}
.vent {
  fill: rgb(var(--chassis-bay));
}
.led {
  fill: rgb(var(--chassis-edge));
  stroke: rgb(var(--chassis-bay));
  stroke-width: 0.6;
}
.led.led-ok,
.led-ok .led {
  fill: rgb(var(--success));
  filter: drop-shadow(0 0 1.5px rgb(var(--success)));
}
.led.led-warning,
.led-warning .led {
  fill: rgb(var(--warning));
  filter: drop-shadow(0 0 1.5px rgb(var(--warning)));
}
.led.led-critical,
.led-critical .led {
  fill: rgb(var(--danger));
  filter: drop-shadow(0 0 2px rgb(var(--danger)));
  animation: led-pulse 1.1s ease-in-out infinite;
}
@keyframes led-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}
@media (prefers-reduced-motion: reduce) {
  .led.led-critical,
  .led-critical .led {
    animation: none;
  }
}
</style>
