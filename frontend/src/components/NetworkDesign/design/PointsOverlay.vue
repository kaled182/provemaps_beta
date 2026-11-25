<template>
  <div class="po" aria-hidden="false">
    <template v-for="it in rendered" :key="it.key">
      <button
        v-if="it.cluster"
        type="button"
        class="po-cluster"
        :class="`po-${it.kind}`"
        :style="{ left: `${it.x}px`, top: `${it.y}px` }"
        :title="`${it.count} ${KIND[it.kind].plural} — clique para aproximar`"
        :data-testid="`cluster-${it.kind}`"
        @click="zoomInto(it)"
      >
        {{ it.count }}
      </button>
      <div v-else class="po-point" :style="{ left: `${it.x}px`, top: `${it.y}px` }">
        <button
          type="button"
          class="po-pin"
          :class="[`po-${it.kind}`, { 'po-cut': it.item.mode === 'corte' }]"
          :title="`${KIND[it.kind].label} ${it.item.name}`"
          :data-testid="`pin-${it.kind}`"
          @click.stop="$emit('pick', it.kind, it.item, $event)"
          @contextmenu.prevent.stop="$emit('menu', it.kind, it.item, $event)"
        />
        <span v-if="labels" class="po-label" :data-testid="`label-${it.kind}`">{{ it.item.name }}</span>
      </div>
    </template>
  </div>
</template>

<script setup>
/**
 * Pontos do Projeto de Rede sobre o mapa (EV-0139): CEOs, CTOs, postes e reservas num só overlay
 * posicionado por `IMap.latLngToPixel` e recalculado no `move` (um rAF por frame). Abaixo do
 * zoom 16, CTOs e postes agrupam-se por célula de ecrã (cluster com a contagem, clique aproxima);
 * a partir do 16 cada ponto aparece com o rótulo.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { LABEL_ZOOM } from '@/features/networkDesign/modules/designMode.js'

const props = defineProps({
  map: { type: Object, required: true },
  /** [{kind: 'ceo'|'cto'|'pole'|'slack', item: {id, name, point:[lng,lat], …}}] */
  points: { type: Array, required: true },
})
defineEmits(['pick', 'menu'])

const KIND = {
  ceo: { label: 'CEO', plural: 'CEOs' },
  cto: { label: 'CTO', plural: 'CTOs' },
  pole: { label: 'Poste', plural: 'postes' },
  slack: { label: 'Reserva', plural: 'reservas' },
}
const CLUSTERED = new Set(['cto', 'pole'])
const CELL = 56

const tick = ref(0)
const zoom = ref(0)
let raf = 0

function schedule() {
  if (raf) return
  raf = requestAnimationFrame(() => {
    raf = 0
    zoom.value = props.map.getZoom?.() ?? 0
    tick.value += 1
  })
}

const labels = computed(() => zoom.value >= LABEL_ZOOM)

const rendered = computed(() => {
  void tick.value
  const el = props.map.getContainer?.()
  const w = el?.clientWidth || window.innerWidth
  const h = el?.clientHeight || window.innerHeight
  const out = []
  const cells = new Map()
  for (const p of props.points) {
    const px = props.map.latLngToPixel({ lat: p.item.point[1], lng: p.item.point[0] })
    if (!px || px.x < -40 || px.y < -40 || px.x > w + 40 || px.y > h + 40) continue
    if (!labels.value && CLUSTERED.has(p.kind)) {
      const key = `${p.kind}:${Math.floor(px.x / CELL)}:${Math.floor(px.y / CELL)}`
      const c = cells.get(key) || { key, kind: p.kind, cluster: true, count: 0, sx: 0, sy: 0, lat: 0, lng: 0 }
      c.count += 1
      c.sx += px.x
      c.sy += px.y
      c.lat += p.item.point[1]
      c.lng += p.item.point[0]
      cells.set(key, c)
      continue
    }
    out.push({ key: `${p.kind}-${p.item.id}`, kind: p.kind, item: p.item, x: px.x, y: px.y })
  }
  for (const c of cells.values()) {
    if (c.count === 1) {
      const p = props.points.find((q) => q.kind === c.kind && q.item.point[0] === c.lng && q.item.point[1] === c.lat)
      if (p) {
        out.push({ key: `${p.kind}-${p.item.id}`, kind: p.kind, item: p.item, x: c.sx, y: c.sy })
        continue
      }
    }
    out.push({ ...c, x: c.sx / c.count, y: c.sy / c.count, lat: c.lat / c.count, lng: c.lng / c.count })
  }
  return out
})

function zoomInto(c) {
  const z = props.map.getZoom?.() ?? 12
  props.map.flyTo?.({ lat: c.lat, lng: c.lng }, Math.min(z + 2, LABEL_ZOOM))
}

onMounted(() => {
  props.map.on('move', schedule)
  schedule()
})
watch(() => props.points, schedule)
onBeforeUnmount(() => {
  props.map.off?.('move', schedule)
  if (raf) cancelAnimationFrame(raf)
})
</script>

<style scoped>
.po {
  position: absolute;
  inset: 0;
  z-index: 6;
  pointer-events: none;
  overflow: hidden;
}
.po-point {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
}
.po-pin {
  width: 14px;
  height: 14px;
  pointer-events: auto;
  cursor: pointer;
  border: 2px solid currentColor;
  background: rgb(var(--surface));
  box-shadow: 0 1px 3px rgb(0 0 0 / 0.35);
}
.po-label {
  margin-top: 2px;
  padding: 0 4px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
  color: rgb(var(--n-900));
  background: rgb(var(--surface) / 0.85);
}
/* CEO: losango (vazado sangria, cheio corte) · CTO: quadrado · poste: círculo pequeno · reserva: anel */
.po-ceo {
  color: rgb(var(--info));
  transform: rotate(45deg);
  border-radius: 2px;
}
.po-ceo.po-cut {
  background: rgb(var(--info));
}
.po-cto {
  color: rgb(var(--success));
  border-radius: 3px;
}
.po-pole {
  width: 9px;
  height: 9px;
  color: rgb(var(--n-500));
  border-radius: 999px;
  background: rgb(var(--n-400));
}
.po-slack {
  color: rgb(var(--warning));
  border-radius: 999px;
  border-style: double;
  border-width: 3px;
}
.po-cluster {
  position: absolute;
  transform: translate(-50%, -50%);
  min-width: 26px;
  height: 26px;
  padding: 0 6px;
  border-radius: 999px;
  pointer-events: auto;
  cursor: pointer;
  font-size: 11px;
  font-weight: 700;
  color: rgb(var(--surface));
  border: 2px solid rgb(var(--surface));
  box-shadow: 0 2px 6px rgb(0 0 0 / 0.35);
}
.po-cluster.po-cto,
.po-cluster.po-pole {
  min-width: 26px;
  width: auto;
  height: 26px;
  border-radius: 999px;
  color: rgb(var(--surface));
}
.po-cluster.po-cto {
  background: rgb(var(--success));
}
.po-cluster.po-pole {
  background: rgb(var(--n-500));
}
</style>
