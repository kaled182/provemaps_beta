<template>
  <NdDock v-model="mode" :moving="moving ? moving.label : ''" />
  <p v-if="mode === 'measure'" class="measure" role="status" data-testid="nd-measure">
    <span class="num">{{ measureKm }}</span> · {{ measurePoints }} pontos
  </p>

  <!-- EV-0139: CEOs, CTOs, postes e reservas — cluster abaixo do zoom 16, rótulos a partir dele -->
  <PointsOverlay :map="map" :points="overlayPoints" @pick="pinClick" @menu="openMenu" />

  <NdObjectMenu v-if="menu" :x="menu.x" :y="menu.y" :title="menu.title" :items="menu.items" @pick="onMenuPick" @close="menu = null" />

  <SiteCreateModal v-if="siteCreate" :show="!!siteCreate" :point="siteCreate.point" @close="siteCreate = null" @created="afterCreate('Site criado.')" />
  <SlackCreateModal
    v-if="slackCreate"
    :show="!!slackCreate"
    :point="slackCreate.point"
    :cable="slackCreate.cable"
    @close="slackCreate = null"
    @created="afterCreate('Reserva técnica inserida.')"
  />
  <CeoCreateModal
    v-if="ceoCreate"
    :show="!!ceoCreate"
    :cable="ceoCreate.cable"
    :point="ceoCreate.point"
    @close="ceoCreate = null"
    @created="afterCreate('CEO inserida no traçado.')"
  />
  <CtoCreateModal
    v-if="ctoCreate"
    :show="!!ctoCreate"
    :point="ctoCreate.point"
    :cable="ctoCreate.cable"
    @close="ctoCreate = null"
    @created="afterCreate('CTO inserida.')"
  />
  <PoleCreateModal v-if="poleCreate" :show="!!poleCreate" :point="poleCreate.point" @close="poleCreate = null" @created="afterCreate('Poste inserido.')" />
  <CeoFusionsModal v-if="fusionsFor" :show="!!fusionsFor" :ceo="fusionsFor" @close="fusionsFor = null" />
  <CableStructureModal v-if="structureFor" :show="!!structureFor" :cable-id="structureFor" @close="structureFor = null" />
  <CeoDerivePanel v-if="deriving" :map="map" :ceo="deriving" :ceos="ceos" :sites="sites" @close="deriving = null" @created="onDerived" />
</template>

<script setup>
/**
 * Camada de engenharia do Projeto de Rede (EV-0138), por cima do construtor legado de traçados:
 * barra de modos, sites (com snap), CEOs, CTOs, postes (EV-0139) e reservas técnicas, menus de contexto por objeto e as
 * ações de CEO (inserir Sangria/Corte, emendas, derivar cabo, mover, excluir) e de reserva.
 * As escritas exigem staff no servidor (StaffWritePermission).
 */
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import PointsOverlay from './PointsOverlay.vue'
import NdDock from './NdDock.vue'
import NdObjectMenu from './NdObjectMenu.vue'
import { useDesignPoints } from './useDesignPoints'
import { useApi } from '@/composables/useApi'
import { createRouteDrawing } from '@/composables/useRouteDrawing'
import { tokenColor } from '@/utils/cssToken'
import {
  designLayers,
  designMode,
  lastCableContext,
  lastMapContext,
  onDesign,
  setSnapProvider,
} from '@/features/networkDesign/modules/designMode.js'
import {
  clickFromLayer,
  editCableRoute,
  reloadNetworkDesignCables,
  startRouteAt,
} from '@/features/networkDesign/fiberRouteBuilder.js'
import { showConfirmDialog, showErrorMessage, showSuccessMessage } from '@/features/networkDesign/modules/uiHelpers.js'

const SiteCreateModal = defineAsyncComponent(() => import('./SiteCreateModal.vue'))
const SlackCreateModal = defineAsyncComponent(() => import('./SlackCreateModal.vue'))
const CtoCreateModal = defineAsyncComponent(() => import('./CtoCreateModal.vue'))
const PoleCreateModal = defineAsyncComponent(() => import('./PoleCreateModal.vue'))
const CeoCreateModal = defineAsyncComponent(() => import('@/components/Ceo/CeoCreateModal.vue'))
const CeoFusionsModal = defineAsyncComponent(() => import('@/components/Ceo/CeoFusionsModal.vue'))
const CeoDerivePanel = defineAsyncComponent(() => import('@/components/Ceo/CeoDerivePanel.vue'))
const CableStructureModal = defineAsyncComponent(() => import('@/components/Inventory/Fibers/CableStructureModal.vue'))

const props = defineProps({
  /** IMap do construtor (providers/maps) */
  map: { type: Object, required: true },
})

const api = useApi()
const router = useRouter()
const { sites, ceos, slacks, ctos, poles, load, snap } = useDesignPoints()

const mode = computed({
  get: () => designMode.value,
  set: (v) => {
    designMode.value = v
    if (v !== 'move') moving.value = null
  },
})
const menu = ref(null)
const moving = ref(null) // {type, obj, label}
const siteCreate = ref(null)
const slackCreate = ref(null)
const ceoCreate = ref(null)
const ctoCreate = ref(null)
const poleCreate = ref(null)
let lastCablePickAt = 0
const fusionsFor = ref(null)
const structureFor = ref(null)
const deriving = ref(null)

// ── sites: marcadores do provider (clique direito = menu; no traçado conta como ponto) ──
let siteMarkers = []
function drawSites() {
  siteMarkers.forEach((m) => m.remove())
  if (!designLayers.sites) {
    siteMarkers = []
    return
  }
  siteMarkers = sites.value.map((s) => {
    const m = props.map.createMarker({ position: { lat: s.lat, lng: s.lng }, title: s.name, color: tokenColor('--primary-600'), size: 12 })
    m.on?.('rightclick', (e) => openMenu('site', s, e))
    m.on?.('click', (e) => pinClick('site', s, e))
    return m
  })
}

async function reload() {
  await load()
  drawSites()
}

/** Pontos do overlay conforme as camadas ligadas no painel «Camadas». */
const overlayPoints = computed(() => [
  ...(designLayers.poles ? poles.value.map((item) => ({ kind: 'pole', item })) : []),
  ...(designLayers.slacks ? slacks.value.map((item) => ({ kind: 'slack', item })) : []),
  ...(designLayers.ctos ? ctos.value.map((item) => ({ kind: 'cto', item })) : []),
  ...(designLayers.ceos ? ceos.value.map((item) => ({ kind: 'ceo', item })) : []),
])
watch(() => designLayers.sites, drawSites)

// ── menus ───────────────────────────────────────────────────────────────────
const MENUS = {
  site: (s) => ({
    title: s.name,
    items: [
      { key: 'connect', label: 'Conectar novo cabo aqui' },
      { key: 'move', label: 'Mover posição' },
      { key: 'monitor', label: 'Ver portas no monitoramento' },
    ],
  }),
  ceo: (c) => ({
    title: `${c.name} · ${c.mode === 'corte' ? 'corte' : 'sangria'}`,
    items: [
      { key: 'fusions', label: 'Abrir diagrama de emendas' },
      { key: 'connect', label: 'Conectar novo cabo aqui' },
      { key: 'move', label: 'Mover posição' },
      { key: 'delete', label: 'Excluir CEO', danger: true },
    ],
  }),
  cto: (c) => ({
    title: `${c.name}${c.capacity ? ` · ${c.capacity} portas` : ''}${c.cable_name ? ` · ${c.cable_name}` : ''}`,
    items: [
      { key: 'connect', label: 'Conectar novo cabo aqui' },
      { key: 'move', label: 'Mover posição' },
      { key: 'delete', label: 'Excluir CTO', danger: true },
    ],
  }),
  pole: (p) => ({
    title: `Poste ${p.name}${p.owner ? ` · ${p.owner}` : ''}`,
    items: [
      { key: 'move', label: 'Mover posição' },
      { key: 'delete', label: 'Excluir poste', danger: true },
    ],
  }),
  slack: (s) => ({
    title: `${s.name} · ${s.slack_m} m`,
    items: [
      { key: 'move', label: 'Mover posição' },
      { key: 'delete', label: 'Excluir reserva', danger: true },
    ],
  }),
}

function eventXY(e) {
  const ev = e?.originalEvent || e
  return { x: ev?.clientX ?? window.innerWidth / 2, y: ev?.clientY ?? window.innerHeight / 2 }
}
function openMenu(type, obj, e) {
  const { x, y } = eventXY(e)
  menu.value = { type, obj, x, y, ...MENUS[type](obj) }
}

/** Clique esquerdo num pino/site: a traçar conta como ponto (com snap no objeto); senão abre o menu. */
function pinClick(type, obj, e) {
  const point = type === 'site' ? { lat: obj.lat, lng: obj.lng } : { lat: obj.point[1], lng: obj.point[0] }
  if (designMode.value === 'trace' && type === 'pole') {
    clickFromLayer(point.lat, point.lng) // o traçado passa pelo poste
    return
  }
  if (designMode.value === 'trace') {
    clickFromLayer(point.lat, point.lng)
    return
  }
  if (designMode.value === 'move') return
  openMenu(type, obj, e)
}

async function onMenuPick(key) {
  const { type, obj } = menu.value
  menu.value = null
  if (key === 'move') {
    moving.value = { type, obj, label: obj.name }
    designMode.value = 'move'
  } else if (key === 'connect' && type === 'site') {
    startRouteAt(obj.lat, obj.lng)
  } else if (key === 'connect' && type === 'cto') {
    startRouteAt(obj.point[1], obj.point[0])
  } else if (key === 'connect' && type === 'ceo') {
    designMode.value = 'select'
    deriving.value = obj
  } else if (key === 'fusions') {
    fusionsFor.value = obj
  } else if (key === 'monitor') {
    router.push({ path: '/monitoring/backbone/map/default', query: { site: String(obj.id) } })
  } else if (key === 'delete') {
    await remove(type, obj)
  }
}

const ENDPOINT = {
  ceo: (id) => `/api/v1/inventory/ceos/${id}/`,
  slack: (id) => `/api/v1/inventory/slacks/${id}/`,
  cto: (id) => `/api/v1/inventory/ctos/${id}/`,
  pole: (id) => `/api/v1/inventory/poles/${id}/`,
}
const DELETE_TEXT = {
  ceo: (o) => ['Excluir CEO', `Excluir a ${o.name}? Só é possível com a caixa vazia (sem emendas nem cabos ligados).`, 'CEO excluída.'],
  slack: (o) => ['Excluir reserva técnica', `Excluir a ${o.name}? Os ${o.slack_m} m saem do comprimento do cabo.`, 'Reserva técnica excluída.'],
  cto: (o) => ['Excluir CTO', `Excluir a ${o.name}? Só é possível sem fusões.`, 'CTO excluída.'],
  pole: (o) => ['Excluir poste', `Excluir o poste ${o.name}?`, 'Poste excluído.'],
}

async function remove(type, obj) {
  const [title, description, done] = DELETE_TEXT[type](obj)
  const ok = await showConfirmDialog({
    title,
    description,
    confirmText: 'Excluir',
    cancelText: 'Cancelar',
    tone: 'danger',
  })
  if (!ok) return
  try {
    await api.delete(ENDPOINT[type](obj.id))
    showSuccessMessage(done)
    await reload()
  } catch (e) {
    showErrorMessage(e?.message || 'erro desconhecido')
  }
}

async function finishMove(lat, lng) {
  const { type, obj } = moving.value
  designMode.value = 'select'
  moving.value = null
  try {
    if (type === 'site') {
      await api.patch(`/api/v1/sites/${obj.id}/`, { latitude: lat.toFixed(6), longitude: lng.toFixed(6) })
    } else {
      await api.patch(ENDPOINT[type](obj.id), { lat, lng })
    }
    showSuccessMessage(type === 'site' ? 'Site movido (os traçados dos cabos não mudam).' : 'Posição atualizada no traçado.')
    await reload()
  } catch (e) {
    showErrorMessage(e?.message || 'erro desconhecido')
  }
}

async function afterCreate(message) {
  siteCreate.value = null
  slackCreate.value = null
  ceoCreate.value = null
  ctoCreate.value = null
  poleCreate.value = null
  designMode.value = 'select'
  showSuccessMessage(message)
  await reload()
}
async function onDerived(cable) {
  deriving.value = null
  showSuccessMessage(`Cabo ${cable.name} criado a partir da CEO.`)
  await Promise.all([reload(), reloadNetworkDesignCables()])
}

// ── eventos do construtor e do menu legado ───────────────────────────────────
const offs = []
function cableTarget(ctx) {
  return ctx ? { cable: { id: ctx.cableId, name: ctx.cableName }, point: { lat: ctx.lat, lng: ctx.lng } } : null
}
function onMapClick({ lat, lng, mode: m }) {
  if (m === 'site') siteCreate.value = { point: { lat, lng } }
  else if (m === 'pole') poleCreate.value = { point: { lat, lng } }
  else if (m === 'cto') {
    // num cabo o clique chega também ao mapa: se o cabo foi escolhido, a CTO fica nele
    setTimeout(() => {
      if (Date.now() - lastCablePickAt > 400 && !ctoCreate.value) ctoCreate.value = { point: { lat, lng }, cable: null }
    }, 120)
  }
  else if (m === 'move' && moving.value) finishMove(lat, lng)
}
function onCablePick({ mode: m, cableId, cableName, lat, lng }) {
  const target = { cable: { id: cableId, name: cableName }, point: { lat, lng } }
  lastCablePickAt = Date.now()
  if (m === 'ceo') ceoCreate.value = target
  else if (m === 'cto') ctoCreate.value = target
  else if (m === 'slack') slackCreate.value = target
}
function onMenuAction({ action }) {
  const cable = cableTarget(lastCableContext.value)
  const point = lastMapContext.value
  if (action === 'site' && point) siteCreate.value = { point: { lat: point.lat, lng: point.lng } }
  else if (action === 'cto' && point) ctoCreate.value = { point: { lat: point.lat, lng: point.lng }, cable: null }
  else if (action === 'pole' && point) poleCreate.value = { point: { lat: point.lat, lng: point.lng } }
  else if (action === 'cto-cable' && cable) ctoCreate.value = cable
  else if (action === 'trace' || action === 'measure') designMode.value = action
  else if (action === 'ceo' && cable) ceoCreate.value = cable
  else if (action === 'slack' && cable) slackCreate.value = cable
  else if (action === 'vertex' && cable) editCableRoute(cable.cable.id)
  else if (action === 'structure' && cable) structureFor.value = cable.cable.id
}

// ── medir distância ──────────────────────────────────────────────────────────
let measure = null
const measureMeters = ref(0)
const measurePoints = ref(0)
const measureKm = computed(
  () => `${(measureMeters.value / 1000).toLocaleString('pt-BR', { minimumFractionDigits: 3, maximumFractionDigits: 3 })} km`,
)
watch(designMode, (m, old) => {
  if (old === 'measure' && measure) {
    measure.destroy()
    measure = null
    measureMeters.value = 0
    measurePoints.value = 0
  }
  if (m === 'measure') {
    measure = createRouteDrawing(props.map, {
      strokeColor: tokenColor('--warning'),
      onPathChange: (path, d) => {
        measureMeters.value = d
        measurePoints.value = path.length
      },
    })
    measure.start()
  }
  if (m !== 'move') moving.value = null
})

function onKey(e) {
  if (e.key !== 'Escape' || menu.value) return
  if (designMode.value !== 'select') designMode.value = 'select'
}

onMounted(async () => {
  setSnapProvider((lat, lng) => snap(props.map, lat, lng))
  offs.push(onDesign('map-click', onMapClick), onDesign('cable-pick', onCablePick), onDesign('menu-action', onMenuAction))
  document.addEventListener('keydown', onKey)
  await reload()
})
onBeforeUnmount(() => {
  offs.forEach((off) => off())
  document.removeEventListener('keydown', onKey)
  setSnapProvider(null)
  siteMarkers.forEach((m) => m.remove())
  measure?.destroy()
  designMode.value = 'select'
})

defineExpose({ reload })
</script>

<style scoped>
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.pin-wrap {
  display: block;
}
.slack-pin {
  display: block;
  width: 14px;
  height: 14px;
  border-radius: 999px;
  border: 3px double rgb(var(--warning));
  background: rgb(var(--surface));
  cursor: pointer;
  pointer-events: auto;
  box-shadow: 0 1px 3px rgb(0 0 0 / 0.35);
}
.measure {
  position: absolute;
  left: 50%;
  bottom: 64px;
  z-index: 25;
  transform: translateX(-50%);
  margin: 0;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid rgb(var(--warning) / 0.5);
  background: rgb(var(--surface));
  color: rgb(var(--n-900));
  font-size: 13px;
  font-weight: 600;
}
</style>
