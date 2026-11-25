<template>
  <div class="to" data-testid="trace-overlay">
    <div
      v-for="l in placed"
      :key="l.key"
      class="to-label"
      :class="[`to-${l.kind}`, { 'to-dim': !l.focus }]"
      :style="{ left: `${l.x}px`, top: `${l.y}px` }"
      :data-testid="`trace-label-${l.kind}`"
    >
      <span class="to-dot" aria-hidden="true" />
      <span class="to-text">{{ l.text }}</span>
    </div>
  </div>

  <aside class="to-panel" role="status" aria-live="polite" data-testid="trace-panel">
    <header class="to-head">
      <b>Rastreamento</b>
      <button type="button" class="to-close" data-testid="trace-clear" @click="$emit('close')">Limpar</button>
    </header>
    <p class="to-line">
      <span class="to-sub">De</span> {{ trace.source?.label || 'sem fonte' }}
      <span v-if="trace.tx" class="num"> · {{ fmtDbm(trace.tx.dbm) }}</span>
    </p>
    <p class="to-line">
      <span class="to-sub">Até</span> {{ leaf.end.label }}
    </p>
    <p class="to-line num" data-testid="trace-panel-total">
      {{ fmtKm(leaf.km) }}<template v-if="leaf.dbm != null"> · chega com ≈ <b>{{ fmtDbm(leaf.dbm) }}</b></template>
    </p>
    <p class="to-legend">
      <span class="to-sw to-sw-focus" /> caminho da fibra
      <span class="to-sw to-sw-other" /> outros ramos
      <span class="to-sw to-sw-broken" /> rompido
    </p>
  </aside>
</template>

<script setup>
/**
 * Destaque do rastreamento no mapa do Projeto de Rede (EV-0143): troços percorridos como
 * polilinhas do IMap (o caminho da fibra pedida mais grosso; os outros ramos dos splitters mais
 * finos; rompimentos a vermelho) e rótulos com km/dBm na fonte, nos splitters e nos fins.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { tokenColor } from '@/utils/cssToken'
import { focusPath, fmtDbm, fmtKm, traceBounds, traceLabels, traceSegments } from '@/utils/traceTree'

const props = defineProps({
  map: { type: Object, required: true },
  trace: { type: Object, required: true },
})
defineEmits(['close'])

const leaf = computed(() => {
  const p = focusPath(props.trace.tree)
  return p[p.length - 1]
})
const labels = computed(() => traceLabels(props.trace))

let lines = []
function draw() {
  lines.forEach((l) => l.remove())
  const focus = tokenColor('--primary-500')
  const other = tokenColor('--info')
  const broken = tokenColor('--danger')
  const segs = traceSegments(props.trace.tree)
  // ramos de fundo primeiro, o caminho em foco por cima
  segs.sort((a, b) => Number(a.focus) - Number(b.focus))
  lines = segs.map((s) =>
    props.map.createPolyline({
      path: s.path,
      strokeColor: s.broken ? broken : s.focus ? focus : other,
      strokeWeight: s.focus ? 7 : 4,
      strokeOpacity: s.focus ? 0.95 : 0.75,
      clickable: false,
    }),
  )
  const pts = traceBounds(props.trace)
  // margem que livra a barra de modos (topo) e o painel do rastreamento (direita)
  if (pts.length) props.map.fitBounds(pts, { padding: 130, maxZoom: 17 })
}

const tick = ref(0)
let raf = 0
function schedule() {
  if (raf) return
  raf = requestAnimationFrame(() => {
    raf = 0
    tick.value += 1
  })
}
const placed = computed(() => {
  void tick.value
  return labels.value
    .map((l) => ({ ...l, ...(props.map.latLngToPixel({ lat: l.lat, lng: l.lng }) || {}) }))
    .filter((l) => Number.isFinite(l.x) && Number.isFinite(l.y))
})

onMounted(() => {
  draw()
  props.map.on('move', schedule)
  props.map.on('idle', schedule)
  schedule()
})
watch(() => props.trace, () => {
  draw()
  schedule()
})
onBeforeUnmount(() => {
  lines.forEach((l) => l.remove())
  lines = []
  props.map.off?.('move', schedule)
  props.map.off?.('idle', schedule)
  if (raf) cancelAnimationFrame(raf)
})
</script>

<style scoped>
.to {
  position: absolute;
  inset: 0;
  z-index: 7;
  pointer-events: none;
  overflow: hidden;
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.to-label {
  position: absolute;
  transform: translate(-6px, -50%);
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}
.to-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  border: 2px solid rgb(var(--surface));
  background: rgb(var(--primary-500));
  box-shadow: 0 0 0 1px rgb(var(--n-900) / 0.25);
}
.to-splitter .to-dot {
  border-radius: 2px;
  background: rgb(var(--warning));
}
.to-source .to-dot {
  background: rgb(var(--success));
}
.to-text {
  padding: 1px 6px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  background: rgb(var(--surface) / 0.92);
  color: rgb(var(--n-900));
  box-shadow: 0 1px 3px rgb(var(--n-900) / 0.2);
}
.to-dim {
  opacity: 0.7;
}
.to-dim .to-text {
  font-weight: 500;
}
.to-panel {
  position: absolute;
  top: 116px;
  right: 12px;
  z-index: 30;
  width: 280px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgb(var(--n-200));
  background: rgb(var(--surface));
  color: rgb(var(--n-900));
  box-shadow: 0 8px 24px rgb(var(--n-900) / 0.18);
  font-size: 12px;
}
.to-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.to-close {
  border: 1px solid rgb(var(--n-300));
  background: rgb(var(--surface));
  color: rgb(var(--n-700));
  border-radius: 6px;
  padding: 2px 8px;
  cursor: pointer;
}
.to-close:hover {
  background: rgb(var(--n-100));
}
.to-line {
  margin: 0 0 4px;
}
.to-sub {
  color: rgb(var(--n-500));
}
.to-legend {
  margin: 6px 0 0;
  color: rgb(var(--n-500));
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 6px;
}
.to-sw {
  display: inline-block;
  width: 18px;
  height: 4px;
  border-radius: 2px;
}
.to-sw-focus {
  height: 6px;
  background: rgb(var(--primary-500));
}
.to-sw-other {
  background: rgb(var(--info));
}
.to-sw-broken {
  background: rgb(var(--danger));
}
</style>
