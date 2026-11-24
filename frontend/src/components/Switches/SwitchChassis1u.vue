<template>
  <svg
    class="chassis"
    :viewBox="`0 0 ${W} ${H}`"
    width="100%"
    preserveAspectRatio="xMidYMid meet"
    role="group"
    :aria-label="`Vista frontal do switch ${brand} ${model}`.trim()"
    :data-testid="`sw-chassis-${sw.device_id}`"
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
      <rect :x="ex" y="4" :width="EAR" :height="BODY_H - 8" rx="3" class="ear" />
      <rect :x="ex + EAR / 2 - 3.5" y="22" width="7" height="12" rx="3.5" class="ear-hole" />
      <rect :x="ex + EAR / 2 - 3.5" :y="BODY_H - 34" width="7" height="12" rx="3.5" class="ear-hole" />
    </g>

    <!-- corpo -->
    <rect :x="EAR" y="8" :width="W - 2 * EAR" :height="BODY_H - 16" rx="3" class="body" :fill="`url(#${uid}-body)`" />
    <line :x1="EAR + 2" y1="9.5" :x2="W - EAR - 2" y2="9.5" class="body-light" />

    <!-- marca, modelo e LED do sistema -->
    <text :x="EAR + 14" y="42" class="brand">{{ brand }}</text>
    <text :x="EAR + 14" y="58" class="model">{{ model || 'modelo —' }}</text>
    <circle :cx="EAR + 20" cy="78" r="3" :class="['led', `led-${sysLed}`]" data-testid="sw-chassis-sys" />
    <text :x="EAR + 28" y="80.5" class="led-label">SYS</text>

    <!-- MEth (gerência) junto da marca -->
    <g
      v-for="p in mgmt"
      :key="p.name"
      :class="['port', `led-${p.led}`, { 'port-selected': p.selected }]"
      role="button"
      tabindex="0"
      :aria-label="p.text"
      :data-testid="`sw-port-${p.name}`"
      @click="$emit('select', p.raw)"
      @keydown.enter.prevent="$emit('select', p.raw)"
      @mouseenter="hover($event, p.text)"
      @mouseleave="$emit('hover', null)"
    >
      <rect :x="p.x - 2" :y="p.y - 2" :width="p.w + 4" :height="p.h + 4" rx="2" class="hit" />
      <path :d="rj45Path(p.x, p.y, p.w, p.h)" class="rj45" />
      <circle :cx="p.x + p.w + 6" :cy="p.y + p.h / 2" r="2.4" class="led" />
      <text :x="p.x" :y="p.y + p.h + 10" class="port-num">MGMT</text>
    </g>

    <!-- grupos de portas (SFP+, QSFP, RJ45) -->
    <g v-for="g in groups" :key="g.key">
      <rect :x="g.x - 6" y="16" :width="g.width + 12" :height="BODY_H - 32" rx="3" class="port-panel" />
      <text :x="g.x" y="27" class="group-label">{{ g.label }}</text>
      <g
        v-for="p in g.ports"
        :key="p.name"
        :class="['port', `led-${p.led}`, { 'port-selected': p.selected, 'port-dim': p.dim }]"
        role="button"
        tabindex="0"
        :aria-pressed="p.selected"
        :aria-label="p.text"
        :data-testid="`sw-port-${p.name}`"
        @click="$emit('select', p.raw)"
        @keydown.enter.prevent="$emit('select', p.raw)"
        @keydown.space.prevent="$emit('select', p.raw)"
        @mouseenter="hover($event, p.text)"
        @focus="hover($event, p.text)"
        @mouseleave="$emit('hover', null)"
        @blur="$emit('hover', null)"
      >
        <rect :x="p.x - 1.5" :y="p.y - (p.top ? 10 : 2)" :width="p.w + 3" :height="p.h + 12" rx="2" class="hit" />
        <text :x="p.x + p.w / 2" :y="p.top ? p.y - 3 : p.y + p.h + 9" class="port-num" text-anchor="middle">{{ p.num }}</text>
        <template v-if="g.cage === 'rj45'">
          <path :d="rj45Path(p.x, p.y, p.w, p.h)" class="rj45" />
        </template>
        <template v-else>
          <rect :x="p.x" :y="p.y" :width="p.w" :height="p.h" rx="1.5" class="sfp" />
          <rect :x="p.x + 2.5" :y="p.y + 3" :width="p.w - 5" :height="p.h - 6" rx="0.8" class="sfp-hole" />
        </template>
        <circle :cx="p.x + p.w / 2" :cy="p.top ? p.y + p.h + 4 : p.y - 4" r="2.2" class="led" />
      </g>
    </g>

    <text v-if="!groups.length" :x="PORTS_X + 10" :y="BODY_H / 2 + 3" class="empty-note" data-testid="sw-chassis-empty">
      Sem portas conhecidas no Zabbix
    </text>

    <ChassisLegend
      :x="EAR"
      :y="BODY_H - 2"
      :w="W - 2 * EAR"
      :h="18"
      :active="counts.active"
      :free="counts.free"
      :items="LEGEND"
      noun="portas"
    />
  </svg>
</template>

<script setup>
/**
 * Painel frontal 1U de um switch (EV-0116) desenhado a partir das portas REAIS que o Zabbix
 * devolveu (não de um catálogo de modelos): SFP+ (XGigabitEthernet/25GE) e QSFP (40GE/100GE)
 * em duas filas — ímpares em cima, pares em baixo, como na frente dos Huawei —, RJ45 se
 * houver, e a MEth de gerência junto da marca. Grafite fixo `--chassis-*` (EV-0102).
 */
import { computed, useId } from 'vue'
import ChassisLegend from '@/components/Gpon/ChassisLegend.vue'
import { STATE_LABELS } from '@/composables/useSwitchesOverview'

const props = defineProps({
  sw: { type: Object, required: true },
  ports: { type: Array, default: () => [] },
  selectedName: { type: String, default: null },
  /** nomes visíveis pelo filtro (os outros ficam esbatidos); null = todos */
  visibleNames: { type: Array, default: null },
})
const emit = defineEmits(['select', 'hover'])

const W = 960
const BODY_H = 132
const H = BODY_H + 20
const EAR = 24
const PORTS_X = 150
const PORTS_END = W - EAR - 14
const GROUP_GAP = 22
const ROW_GAP = 22
const uid = `sw1u-${useId()}`

const LEGEND = [
  { led: 'ok', label: 'Normal' },
  { led: 'warning', label: 'Atenção / > 80%' },
  { led: 'critical', label: 'Down / LOS' },
  { led: 'off', label: 'Livre' },
]
const LED = { normal: 'ok', warning: 'warning', critical: 'critical', down: 'critical', free: 'off', unknown: 'off' }

/** prefixo → grupo (ordem no painel), gaiola e largura relativa */
const GROUPS = [
  { key: 'rj45', test: (n) => /^(GigabitEthernet|Ethernet)/.test(n), cage: 'rj45', unit: 1, label: 'RJ45' },
  { key: 'sfp', test: (n) => /^(XGigabitEthernet|25GE)/.test(n), cage: 'sfp', unit: 1, label: 'SFP+' },
  { key: 'qsfp', test: (n) => /^(40GE|100GE)/.test(n), cage: 'qsfp', unit: 1.6, label: 'QSFP' },
]

const brand = computed(() => (props.sw.vendor || '').toUpperCase())
const model = computed(() => props.sw.model || '')
const sysLed = computed(() => ({ online: 'ok', offline: 'critical' })[props.sw.status] || 'off')
const visibleSet = computed(() => (props.visibleNames ? new Set(props.visibleNames) : null))

const lastNumber = (name) => Number((name.match(/(\d+)$/) || [0, 0])[1])
const speedOf = (list) => {
  const labels = [...new Set(list.map((p) => p.speed_label).filter(Boolean))]
  return labels.length === 1 ? labels[0] : '' // velocidades mistas: não se escolhe uma
}

function decorate(p) {
  const state = STATE_LABELS[p.state] || p.state
  const desc = p.description ? ` · ${p.description}` : ''
  const rx = p.los ? ' · RX -40 (LOS)' : p.rx_dbm !== null && p.rx_dbm !== undefined ? ` · RX ${p.rx_dbm.toFixed(2)} dBm` : ''
  return {
    raw: p,
    name: p.name,
    num: lastNumber(p.name),
    led: LED[p.state] || 'off',
    text: `${p.name}${desc} · ${state}${rx}`,
    selected: props.selectedName === p.name,
    dim: visibleSet.value !== null && !visibleSet.value.has(p.name),
  }
}

const mgmt = computed(() =>
  props.ports
    .filter((p) => p.kind === 'mgmt')
    .slice(0, 1)
    .map((p) => ({ ...decorate(p), x: EAR + 70, y: 70, w: 16, h: 13 })),
)

const groups = computed(() => {
  const data = props.ports.filter((p) => p.kind !== 'mgmt')
  const raw = GROUPS.map((g) => ({
    ...g,
    list: data.filter((p) => g.test(p.name)).sort((a, b) => lastNumber(a.name) - lastNumber(b.name)),
  })).filter((g) => g.list.length)
  // o que não casa com nenhum prefixo vai para o grupo SFP (não se perde nenhuma porta)
  const known = new Set(raw.flatMap((g) => g.list.map((p) => p.name)))
  const rest = data.filter((p) => !known.has(p.name))
  if (rest.length) {
    const sfp = raw.find((g) => g.key === 'sfp')
    if (sfp) sfp.list.push(...rest)
    // EV-0117: nomes sem prefixo conhecido (Ubiquiti «0/1»): grupo neutro, sem adivinhar a gaiola
    else raw.push({ ...GROUPS[1], key: 'ports', label: 'Portas', list: rest })
  }
  const cols = raw.map((g) => (g.list.length > 1 ? Math.ceil(g.list.length / 2) : 1))
  const units = raw.reduce((n, g, i) => n + cols[i] * g.unit, 0)
  const avail = PORTS_END - PORTS_X - GROUP_GAP * Math.max(0, raw.length - 1)
  const step = Math.min(34, units ? avail / units : 34)
  let x = PORTS_X
  return raw.map((g, gi) => {
    const colW = step * g.unit
    const w = Math.max(8, colW - 4)
    const h = g.cage === 'qsfp' ? 20 : 16
    const twoRows = g.list.length > 1
    const ports = g.list.map((p, i) => {
      const row = twoRows ? i % 2 : 0
      const col = twoRows ? Math.floor(i / 2) : i
      const top = row === 0
      const y = top ? 46 : 46 + h + ROW_GAP
      return { ...decorate(p), x: x + col * colW, y, w, h, top }
    })
    const width = cols[gi] * colW - 4
    const label = `${speedOf(g.list) || ''} ${g.label}`.trim()
    const out = { key: g.key, cage: g.cage, label, x, width, ports }
    x += cols[gi] * colW + GROUP_GAP
    return out
  })
})

const counts = computed(() => {
  const data = props.ports.filter((p) => p.kind !== 'mgmt')
  return { active: data.filter((p) => p.in_use).length, free: data.filter((p) => p.state === 'free').length }
})

/** Tomada RJ45: retângulo com o entalhe da patilha em baixo. */
function rj45Path(x, y, w, h) {
  const n = Math.min(6, w * 0.4)
  const cx = x + w / 2
  return `M${x},${y} H${x + w} V${y + h} H${cx + n / 2} V${y + h - 3} H${cx - n / 2} V${y + h} H${x} Z`
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
.stop-hi { stop-color: rgb(var(--chassis-plate-hi)); }
.stop-mid { stop-color: rgb(var(--chassis-plate)); }
.stop-lo { stop-color: rgb(var(--chassis-plate-lo)); }
.ear {
  fill: rgb(var(--chassis-body));
  stroke: rgb(var(--chassis-border));
}
.ear-hole { fill: rgb(var(--chassis-bay)); }
.body {
  stroke: rgb(var(--chassis-border));
  stroke-width: 1.2;
}
.body-light { stroke: rgb(var(--chassis-edge)); }
.brand {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 16px;
  fill: rgb(var(--chassis-text));
  letter-spacing: 1px;
}
.model {
  font-size: 10px;
  fill: rgb(var(--chassis-text-dim));
}
.led-label,
.group-label {
  font-size: 7.5px;
  fill: rgb(var(--chassis-text-mute));
  letter-spacing: 0.5px;
}
.port-panel {
  fill: rgb(var(--chassis-bay) / 0.6);
  stroke: rgb(var(--chassis-edge));
}
.empty-note {
  font-size: 11px;
  fill: rgb(var(--chassis-text-mute));
}
.port { cursor: pointer; }
.port:focus { outline: none; }
.hit { fill: transparent; }
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
.port-selected .sfp,
.port-selected .rj45 { stroke: rgb(var(--primary-400)); }
.port-dim { opacity: 0.3; }
.port-num {
  font-size: 7px;
  fill: rgb(var(--chassis-text-dim));
}
.sfp,
.rj45 {
  fill: rgb(var(--chassis-edge));
  stroke: rgb(var(--chassis-edge));
  stroke-width: 0.8;
}
.rj45 { fill: rgb(var(--chassis-bay)); }
.sfp-hole { fill: rgb(var(--chassis-bay)); }
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
  100% { opacity: 1; }
  50% { opacity: 0.35; }
}
@media (prefers-reduced-motion: reduce) {
  .led.led-critical,
  .led-critical .led { animation: none; }
}
</style>
