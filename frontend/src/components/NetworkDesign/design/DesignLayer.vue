<template>
  <NdDock v-model="mode" :moving="moving ? moving.label : ''" />
  <p v-if="mode === 'measure'" class="measure" role="status" data-testid="nd-measure">
    <span class="num">{{ measureKm }}</span> · {{ measurePoints }} pontos
  </p>

  <!-- CEOs e reservas técnicas (Vue, ancorados por coordenada) -->
  <MapPopup v-for="c in ceos" :key="`ceo-${c.id}`" :map="map" :position="{ lat: c.point[1], lng: c.point[0] }" bare>
    <span class="pin-wrap" @contextmenu.prevent.stop="openMenu('ceo', c, $event)">
      <CeoPin :name="c.name" :mode="c.mode" @open="pinClick('ceo', c, $event)" />
    </span>
  </MapPopup>
  <MapPopup v-for="s in slacks" :key="`slack-${s.id}`" :map="map" :position="{ lat: s.point[1], lng: s.point[0] }" bare>
    <button
      type="button"
      class="slack-pin"
      :title="`${s.name} · ${s.slack_m} m · ${s.cable_name}`"
      data-testid="slack-pin"
      @click="pinClick('slack', s, $event)"
      @contextmenu.prevent.stop="openMenu('slack', s, $event)"
    />
  </MapPopup>

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
  <CeoFusionsModal v-if="fusionsFor" :show="!!fusionsFor" :ceo="fusionsFor" @close="fusionsFor = null" />
  <CableStructureModal v-if="structureFor" :show="!!structureFor" :cable-id="structureFor" @close="structureFor = null" />
  <CeoDerivePanel v-if="deriving" :map="map" :ceo="deriving" :ceos="ceos" :sites="sites" @close="deriving = null" @created="onDerived" />
</template>

<script setup>
/**
 * Camada de engenharia do Projeto de Rede (EV-0138), por cima do construtor legado de traçados:
 * barra de modos, sites (com snap), CEOs e reservas técnicas, menus de contexto por objeto e as
 * ações de CEO (inserir Sangria/Corte, emendas, derivar cabo, mover, excluir) e de reserva.
 * As escritas exigem staff no servidor (StaffWritePermission).
 */
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import MapPopup from '@/components/Map/MapPopup.vue'
import CeoPin from '@/components/Ceo/CeoPin.vue'
import NdDock from './NdDock.vue'
import NdObjectMenu from './NdObjectMenu.vue'
import { useDesignPoints } from './useDesignPoints'
import { useApi } from '@/composables/useApi'
import { createRouteDrawing } from '@/composables/useRouteDrawing'
import { tokenColor } from '@/utils/cssToken'
import {
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
const { sites, ceos, slacks, load, snap } = useDesignPoints()

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
const fusionsFor = ref(null)
const structureFor = ref(null)
const deriving = ref(null)

// ── sites: marcadores do provider (clique direito = menu; no traçado conta como ponto) ──
let siteMarkers = []
function drawSites() {
  siteMarkers.forEach((m) => m.remove())
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

async function remove(type, obj) {
  const ok = await showConfirmDialog({
    title: type === 'ceo' ? 'Excluir CEO' : 'Excluir reserva técnica',
    description:
      type === 'ceo'
        ? `Excluir a ${obj.name}? Só é possível com a caixa vazia (sem emendas nem cabos ligados).`
        : `Excluir a ${obj.name}? Os ${obj.slack_m} m saem do comprimento do cabo.`,
    confirmText: 'Excluir',
    cancelText: 'Cancelar',
    tone: 'danger',
  })
  if (!ok) return
  try {
    await api.delete(type === 'ceo' ? `/api/v1/inventory/ceos/${obj.id}/` : `/api/v1/inventory/slacks/${obj.id}/`)
    showSuccessMessage(type === 'ceo' ? 'CEO excluída.' : 'Reserva técnica excluída.')
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
      await api.patch(type === 'ceo' ? `/api/v1/inventory/ceos/${obj.id}/` : `/api/v1/inventory/slacks/${obj.id}/`, { lat, lng })
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
  else if (m === 'move' && moving.value) finishMove(lat, lng)
}
function onCablePick({ mode: m, cableId, cableName, lat, lng }) {
  const target = { cable: { id: cableId, name: cableName }, point: { lat, lng } }
  if (m === 'ceo') ceoCreate.value = target
  else if (m === 'slack') slackCreate.value = target
}
function onMenuAction({ action }) {
  const cable = cableTarget(lastCableContext.value)
  const point = lastMapContext.value
  if (action === 'site' && point) siteCreate.value = { point: { lat: point.lat, lng: point.lng } }
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
