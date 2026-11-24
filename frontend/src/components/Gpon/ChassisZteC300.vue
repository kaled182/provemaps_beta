<template>
  <svg
    class="chassis"
    :viewBox="`0 0 ${W} ${H}`"
    width="100%"
    preserveAspectRatio="xMidYMid meet"
    role="group"
    aria-label="Vista frontal do chassi ZTE ZXA10 C300"
    data-testid="chassis-c300"
  >
    <defs>
      <linearGradient :id="`${uid}-frame`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" class="stop-frame-hi" />
        <stop offset="0.5" class="stop-frame" />
        <stop offset="1" class="stop-frame-hi" />
      </linearGradient>
      <linearGradient :id="`${uid}-plate`" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" class="stop-plate-hi" />
        <stop offset="0.45" class="stop-plate" />
        <stop offset="1" class="stop-plate-lo" />
      </linearGradient>
    </defs>

    <!-- moldura -->
    <rect x="2" y="2" :width="W - 4" :height="H - 4" rx="7" class="frame" :fill="`url(#${uid}-frame)`" />
    <rect x="8" y="8" :width="W - 16" height="26" rx="3" class="band" />
    <text x="18" y="25.5" class="brand">ZTE</text>
    <text x="50" y="25.5" class="model">ZXA10 C300</text>
    <text :x="W - 18" y="25.5" class="band-note" text-anchor="end">{{ cardCount }} placas · 21 slots</text>

    <!-- baias 0..20 -->
    <g v-for="b in bays" :key="b.n" :data-testid="`chassis-bay-${b.n}`">
      <rect :x="b.x" :y="BAY_Y" :width="BAY_W" :height="BAY_H" rx="2" class="bay" />
      <line :x1="b.x + 1" :y1="BAY_Y + 1" :x2="b.x + BAY_W - 1" :y2="BAY_Y + 1" class="bay-shadow" />
      <line :x1="b.x + 1" :y1="BAY_Y + BAY_H - 1" :x2="b.x + BAY_W - 1" :y2="BAY_Y + BAY_H - 1" class="bay-light" />

      <!-- baia vazia -->
      <g v-if="!b.card" class="empty">
        <rect :x="b.x + 3" :y="BAY_Y + 3" :width="BAY_W - 6" :height="BAY_H - 6" rx="2" class="empty-plate" />
        <text :x="b.cx" :y="BAY_Y + 16" class="slot-num-dim" text-anchor="middle">{{ slotLabel(b.n) }}</text>
      </g>

      <!-- placa -->
      <g
        v-else
        :data-testid="`chassis-card-${b.n}`"
        :data-role="b.card.role"
        :class="['card', `card-${b.card.role}`, { 'card-selected': selectedSlot === b.n }]"
      >
        <rect :x="b.x + 1.5" :y="BAY_Y + 2" :width="CARD_W" :height="BAY_H - 4" rx="2" class="plate" :fill="`url(#${uid}-plate)`" />
        <circle :cx="b.cx" :cy="BAY_Y + 6.5" r="1.6" class="screw" />
        <circle :cx="b.cx" :cy="BAY_Y + BAY_H - 6.5" r="1.6" class="screw" />

        <!-- cabeçalho: nº e tipo (clicável nas placas PON) -->
        <g
          v-if="b.card.role === 'pon'"
          class="head head-btn"
          role="button"
          tabindex="0"
          :aria-pressed="selectedSlot === b.n"
          :aria-label="`Slot ${b.n} · ${b.card.card_type} — ver as ONUs da placa`"
          :data-testid="`chassis-slot-${b.n}`"
          @click="$emit('toggle-slot', b.n)"
          @keydown.enter.prevent="$emit('toggle-slot', b.n)"
          @keydown.space.prevent="$emit('toggle-slot', b.n)"
        >
          <rect :x="b.x + 3" :y="BAY_Y + 10" :width="CARD_W - 3" height="28" rx="2" class="head-bg" />
          <text :x="b.cx" :y="BAY_Y + 22" class="slot-num" text-anchor="middle">{{ slotLabel(b.n) }}</text>
          <text :x="b.cx" :y="BAY_Y + 33" class="card-type" text-anchor="middle" :data-testid="`chassis-type-${b.n}`">{{ b.card.card_type }}</text>
        </g>
        <g v-else class="head">
          <title>{{ cardTitle(b.card) }}</title>
          <rect :x="b.x + 3" :y="BAY_Y + 10" :width="CARD_W - 3" height="28" rx="2" class="head-bg" />
          <text :x="b.cx" :y="BAY_Y + 22" class="slot-num" text-anchor="middle">{{ slotLabel(b.n) }}</text>
          <text :x="b.cx" :y="BAY_Y + 33" class="card-type" text-anchor="middle" :data-testid="`chassis-type-${b.n}`">{{ b.card.card_type }}</text>
        </g>

        <!-- LEDs da placa -->
        <g v-for="(l, i) in b.leds" :key="l.name">
          <circle :cx="b.x + 9 + i * 12" :cy="BAY_Y + 47" r="2.6" :class="['led', `led-${l.state}`]" :data-testid="`chassis-led-${b.n}-${l.name}`" />
          <text :x="b.x + 9 + i * 12" :y="BAY_Y + 56" class="led-label" text-anchor="middle">{{ l.name }}</text>
        </g>
        <g v-if="b.ms">
          <rect :x="b.cx - 7" :y="BAY_Y + 61" width="14" height="11" rx="2" :class="['ms', `ms-${b.ms}`]" />
          <text :x="b.cx" :y="BAY_Y + 69.5" class="ms-text" text-anchor="middle" :data-testid="`chassis-ms-${b.n}`">{{ b.ms }}</text>
        </g>

        <!-- portas -->
        <g
          v-for="p in b.ports"
          :key="p.port_id"
          :class="['port', `led-${p.led}`, { 'port-pon': b.card.role === 'pon', 'port-selected': p.selected, 'port-dim': p.dim }]"
          :data-testid="`chassis-port-${p.port_id}`"
          :role="b.card.role === 'pon' ? 'button' : null"
          :tabindex="b.card.role === 'pon' ? 0 : null"
          :aria-pressed="b.card.role === 'pon' ? p.selected : null"
          :aria-label="p.text"
          @click="b.card.role === 'pon' && $emit('toggle-pon', p.port_id)"
          @keydown.enter.prevent="b.card.role === 'pon' && $emit('toggle-pon', p.port_id)"
          @keydown.space.prevent="b.card.role === 'pon' && $emit('toggle-pon', p.port_id)"
          @mouseenter="hover($event, p.text)"
          @focus="hover($event, p.text)"
          @mouseleave="$emit('hover', null)"
          @blur="$emit('hover', null)"
        >
          <rect :x="b.x + 3" :y="p.y" :width="CARD_W - 3" :height="p.pitch" rx="1.5" class="hit" />
          <circle :cx="b.x + 8" :cy="p.y + p.pitch / 2" r="2.3" class="led" />
          <rect :x="b.x + 13" :y="p.y + (p.pitch - p.h) / 2" width="19" :height="p.h" rx="1.2" class="sfp" />
          <rect :x="b.x + 15.5" :y="p.y + (p.pitch - p.h) / 2 + 2.2" width="14" :height="p.h - 4.4" rx="0.6" class="sfp-hole" />
          <text :x="b.x + 37.5" :y="p.y + p.pitch / 2 + 2" class="port-num" text-anchor="middle">{{ p.port }}</text>
        </g>

        <!-- fonte: tomada e interruptor, sem portas -->
        <g v-if="b.card.role === 'power'" class="psu">
          <rect :x="b.x + 9" :y="BAY_Y + 92" width="25" height="34" rx="3" class="inlet" />
          <rect :x="b.x + 15" :y="BAY_Y + 101" width="3" height="9" rx="1" class="pin" />
          <rect :x="b.x + 25" :y="BAY_Y + 101" width="3" height="9" rx="1" class="pin" />
          <rect :x="b.x + 20" :y="BAY_Y + 114" width="3" height="6" rx="1" class="pin" />
          <circle :cx="b.cx" :cy="BAY_Y + 158" r="8" class="switch" />
          <path :d="powerGlyph(b.cx, BAY_Y + 158)" class="glyph" />
          <line v-for="v in 9" :key="v" :x1="b.x + 10" :x2="b.x + CARD_W - 8" :y1="BAY_Y + 190 + v * 11" :y2="BAY_Y + 190 + v * 11" class="vent" />
        </g>

        <rect :x="b.x + 7" :y="BAY_Y + BAY_H - 18" :width="CARD_W - 11" height="6" rx="2" class="ejector" />
        <rect
          v-if="selectedSlot === b.n"
          :x="b.x + 0.5"
          :y="BAY_Y + 1"
          :width="CARD_W + 2"
          :height="BAY_H - 2"
          rx="3"
          class="sel-ring"
        />
      </g>
    </g>

    <!-- bandeja de ventilação -->
    <rect x="8" :y="H - 24" :width="W - 16" height="16" rx="3" class="band" />
    <line v-for="v in fanLines" :key="v" :x1="v" :x2="v" :y1="H - 20" :y2="H - 12" class="vent" />
  </svg>
</template>

<script setup>
/**
 * Painel frontal da ZTE C300 (EV-0101): 21 baias (slots 0..20) da esquerda para a direita;
 * placas e portas só as que vêm em `chassis.slots`. Cores do chassi: tokens `--chassis-*` (grafite fixo, EV-0102)
 * (não inverte no tema escuro — o painel é escuro nos dois temas) e LEDs pelas semânticas.
 */
import { computed, useId } from 'vue'
import { cardLeds, indexPons, linkTooltip, portLed, ponTooltip, slotLabel } from './chassisLed'

const props = defineProps({
  chassis: { type: Object, required: true },
  pons: { type: Array, default: () => [] },
  /** pon_ids que passam a pílula; null = sem filtro. */
  visiblePonIds: { type: Array, default: null },
  selectedPort: { type: String, default: null },
  selectedSlot: { type: Number, default: null },
})
const emit = defineEmits(['toggle-pon', 'toggle-slot', 'hover'])

const W = 960
const H = 410
const SLOTS = 21
const X0 = 18
const PITCH = (W - 2 * X0) / SLOTS
const BAY_W = PITCH - 2
const CARD_W = BAY_W - 3
const BAY_Y = 40
const BAY_H = H - BAY_Y - 30
const PORTS_Y = BAY_Y + 78
const PORTS_END = BAY_Y + BAY_H - 24
const uid = `c300-${useId()}`

const ponIdx = computed(() => indexPons(props.pons))
const visibleSet = computed(() => (props.visiblePonIds ? new Set(props.visiblePonIds.map(String)) : null))
const cardsBySlot = computed(() => new Map((props.chassis.slots || []).map((s) => [Number(s.slot), s])))
const cardCount = computed(() => cardsBySlot.value.size)
const fanLines = Array.from({ length: 90 }, (_, i) => 20 + i * 10.4)

function layoutPorts(card) {
  const ports = [...(card.ports || [])].sort((a, b) => a.port - b.port)
  const pitch = Math.min(24, (PORTS_END - PORTS_Y) / Math.max(ports.length, card.role === 'pon' ? 16 : 4))
  return ports.map((p, i) => {
    const pon = ponIdx.value.get(String(p.port_id))
    const isPon = card.role === 'pon'
    return {
      ...p,
      y: PORTS_Y + i * pitch,
      pitch,
      h: Math.min(12, pitch - 3.5),
      led: portLed(p, card.role, ponIdx.value),
      text: isPon ? ponTooltip(p.port_id, pon, p.status) : linkTooltip(p.port_id, card.role, p.status),
      selected: isPon && props.selectedPort === String(p.port_id),
      dim: isPon && visibleSet.value !== null && !visibleSet.value.has(String(p.port_id)),
    }
  })
}

const bays = computed(() =>
  Array.from({ length: SLOTS }, (_, n) => {
    const x = X0 + n * PITCH + 1
    const card = cardsBySlot.value.get(n) || null
    if (!card) return { n, x, cx: x + BAY_W / 2, card: null }
    const leds = cardLeds(card, ponIdx.value)
    return {
      n,
      x,
      cx: x + 1.5 + CARD_W / 2,
      card,
      leds: [
        { name: 'PWR', state: leds.pwr },
        { name: 'RUN', state: leds.run },
        { name: 'ALM', state: leds.alm },
      ],
      ms: leds.ms,
      ports: card.role === 'power' ? [] : layoutPorts(card),
    }
  }),
)

function cardTitle(card) {
  const pct = (v) => (v === null || v === undefined ? '—' : `${Math.round(v)}%`)
  return `Slot ${card.slot} · ${card.card_type} · CPU ${pct(card.cpu_pct)} · MEM ${pct(card.mem_pct)}`
}

function powerGlyph(cx, cy) {
  return `M ${cx - 3.2} ${cy - 2.6} A 4.2 4.2 0 1 0 ${cx + 3.2} ${cy - 2.6} M ${cx} ${cy - 5} L ${cx} ${cy - 0.5}`
}

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
.stop-frame {
  stop-color: rgb(var(--chassis-body));
}
.stop-frame-hi {
  stop-color: rgb(var(--chassis-plate-lo));
}
.stop-plate-hi {
  stop-color: rgb(var(--chassis-plate-hi));
}
.stop-plate {
  stop-color: rgb(var(--chassis-plate));
}
.stop-plate-lo {
  stop-color: rgb(var(--chassis-plate-lo));
}
.frame {
  stroke: rgb(var(--chassis-border));
  stroke-width: 1.5;
}
.band {
  fill: rgb(var(--chassis-body));
  stroke: rgb(var(--chassis-border));
}
.brand {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 14px;
  fill: rgb(var(--chassis-text));
  letter-spacing: 0.5px;
}
.model {
  font-size: 11px;
  fill: rgb(var(--chassis-text-dim));
  letter-spacing: 1px;
}
.band-note {
  font-size: 9px;
  fill: rgb(var(--chassis-text-mute));
}
.bay {
  fill: rgb(var(--chassis-bay));
}
.bay-shadow {
  stroke: rgb(var(--chassis-bay));
  stroke-width: 2;
}
.bay-light {
  stroke: rgb(var(--chassis-bay-edge));
}
.empty {
  opacity: 0.45;
}
.empty-plate {
  fill: none;
  stroke: rgb(var(--chassis-bay-edge));
  stroke-dasharray: 3 3;
}
.slot-num-dim {
  font-size: 9px;
  fill: rgb(var(--chassis-text-mute));
}
.plate {
  stroke: rgb(var(--chassis-edge));
  stroke-width: 0.8;
}
.screw {
  fill: rgb(var(--chassis-border));
  stroke: rgb(var(--chassis-bay));
  stroke-width: 0.6;
}
.head-bg {
  fill: rgb(var(--chassis-bay) / 0.55);
  stroke: transparent;
}
.head-btn {
  cursor: pointer;
}
.head-btn:hover .head-bg,
.head-btn:focus-visible .head-bg {
  stroke: rgb(var(--primary-400));
  fill: rgb(var(--primary-500) / 0.18);
}
.head-btn:focus {
  outline: none;
}
.slot-num {
  font-size: 11px;
  font-weight: 700;
  fill: rgb(var(--chassis-text));
}
.card-type {
  font-size: 7.5px;
  fill: rgb(var(--chassis-text-dim));
  letter-spacing: 0.3px;
}
.led-label {
  font-size: 5px;
  fill: rgb(var(--chassis-text-mute));
}
.ms {
  fill: rgb(var(--chassis-bay));
  stroke: rgb(var(--chassis-edge));
}
.ms-M {
  stroke: rgb(var(--success));
}
.ms-text {
  font-size: 8px;
  font-weight: 700;
  fill: rgb(var(--chassis-text));
}
.sel-ring {
  fill: none;
  stroke: rgb(var(--primary-500));
  stroke-width: 2;
}

/* LEDs: a classe `led-<estado>` vem no próprio círculo (placa) ou no grupo da porta. */
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
.led-unknown .led {
  fill: none;
  stroke: rgb(var(--chassis-text-mute));
  stroke-dasharray: 1.2 1.2;
}

.port .hit {
  fill: transparent;
}
.port-pon {
  cursor: pointer;
}
.port-pon:hover .hit,
.port-pon:focus-visible .hit {
  fill: rgb(var(--primary-500) / 0.16);
  stroke: rgb(var(--primary-400));
  stroke-width: 0.6;
}
.port:focus {
  outline: none;
}
.port-selected .hit {
  fill: rgb(var(--primary-500) / 0.28);
  stroke: rgb(var(--primary-500));
  stroke-width: 1;
}
.port-selected .sfp {
  stroke: rgb(var(--primary-400));
}
.port-dim {
  opacity: 0.32;
}
.sfp {
  fill: rgb(var(--chassis-edge));
  stroke: rgb(var(--chassis-edge));
  stroke-width: 0.7;
}
.sfp-hole {
  fill: rgb(var(--chassis-bay));
}
.port-num {
  font-size: 6px;
  fill: rgb(var(--chassis-text-dim));
}
.inlet,
.switch {
  fill: rgb(var(--chassis-bay));
  stroke: rgb(var(--chassis-edge));
}
.pin {
  fill: rgb(var(--chassis-edge));
}
.glyph {
  fill: none;
  stroke: rgb(var(--chassis-text));
  stroke-width: 1.3;
  stroke-linecap: round;
}
.vent {
  stroke: rgb(var(--chassis-bay));
  stroke-width: 2;
  stroke-linecap: round;
}
.ejector {
  fill: rgb(var(--chassis-border));
  stroke: rgb(var(--chassis-bay));
  stroke-width: 0.6;
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
