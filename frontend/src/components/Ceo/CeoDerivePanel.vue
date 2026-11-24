<template>
  <aside class="cdp" data-testid="ceo-derive-panel">
    <header class="cdp-head">
      <span class="font-semibold">Derivar cabo de {{ ceo.name }}</span>
      <button type="button" class="cdp-x" aria-label="Fechar" @click="close">×</button>
    </header>
    <p class="cdp-hint">
      Clique no mapa para desenhar o traçado a partir da CEO.
      <span class="num" data-testid="derive-length">{{ points }} pontos · {{ km }} km</span>
    </p>
    <label class="fld">
      <span>Nome do cabo</span>
      <input v-model.trim="name" type="text" :placeholder="`${ceo.name} - DESTINO`" data-testid="derive-name" />
    </label>
    <label class="fld">
      <span>Tipo de cabo (grupo)</span>
      <select v-model="groupId" data-testid="derive-group">
        <option :value="null">Escolher depois (pede o nº de fibras)</option>
        <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
      </select>
    </label>
    <fieldset class="fld">
      <legend>Destino</legend>
      <div class="seg" role="group">
        <button v-for="o in TARGETS" :key="o.value" type="button" class="seg-btn" :class="{ 'seg-on': target === o.value }" :data-testid="`derive-target-${o.value}`" @click="target = o.value">
          {{ o.label }}
        </button>
      </div>
    </fieldset>
    <template v-if="target === 'site'">
      <label class="fld">
        <span>Site</span>
        <select v-model="siteId" data-testid="derive-site">
          <option :value="null">Escolher o site…</option>
          <option v-for="s in sites" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </label>
      <label v-if="siteDevices.length" class="fld">
        <span>Porta (opcional)</span>
        <select v-model="portId" data-testid="derive-port">
          <option :value="null">Sem porta por agora</option>
          <optgroup v-for="d in siteDevices" :key="d.id" :label="d.name">
            <option v-for="p in d.ports" :key="p.id" :value="p.id" :disabled="!!p.used_by">
              {{ p.name }}{{ p.used_by ? ` (fibra ${p.used_by.absolute_number} · ${p.used_by.cable_name})` : '' }}
            </option>
          </optgroup>
        </select>
      </label>
    </template>
    <label v-else-if="target === 'ceo'" class="fld">
      <span>CEO de destino</span>
      <select v-model="toCeoId" data-testid="derive-ceo">
        <option :value="null">Escolher a CEO…</option>
        <option v-for="c in otherCeos" :key="c.id" :value="c.id">{{ c.name }} ({{ c.cable_name }})</option>
      </select>
    </label>
    <p v-if="error" class="cdp-error" role="alert" data-testid="derive-error">{{ error }}</p>
    <div class="cdp-actions">
      <button type="button" class="btn" :disabled="points < 2" data-testid="derive-undo" @click="undo">Desfazer ponto</button>
      <button type="button" class="btn btn-primary" :disabled="!canSave || busy" data-testid="derive-save" @click="save">
        {{ busy ? 'A gravar…' : 'Criar cabo' }}
      </button>
    </div>
  </aside>
</template>

<script setup>
/**
 * Derivar um cabo de uma CEO (EV-0135): o traçado começa na CEO e desenha-se no mapa
 * (useRouteDrawing sobre IMap); destino = site (+ porta opcional), outra CEO, ou nenhum.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useApi } from '@/composables/useApi'
import { createRouteDrawing } from '@/composables/useRouteDrawing'

const props = defineProps({
  map: { type: Object, required: true },
  ceo: { type: Object, required: true },
  ceos: { type: Array, default: () => [] },
  /** [{id, name}] */
  sites: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'created'])

const TARGETS = [
  { value: 'site', label: 'Site' },
  { value: 'ceo', label: 'Outra CEO' },
  { value: 'none', label: 'Sem destino' },
]

const api = useApi()
const name = ref('')
const groupId = ref(null)
const groups = ref([])
const target = ref('site')
const siteId = ref(null)
const portId = ref(null)
const toCeoId = ref(null)
const siteDevices = ref([])
const path = ref([])
const meters = ref(0)
const busy = ref(false)
const error = ref('')
let drawing = null

const points = computed(() => path.value.length)
const km = computed(() => (meters.value / 1000).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))
const otherCeos = computed(() => props.ceos.filter((c) => c.id !== props.ceo.id))
const canSave = computed(
  () => !!name.value && points.value >= 2 && (target.value !== 'site' || !!siteId.value) && (target.value !== 'ceo' || !!toCeoId.value),
)

watch(siteId, async (id) => {
  portId.value = null
  siteDevices.value = []
  if (!id) return
  try {
    siteDevices.value = (await api.get('/api/v1/inventory/ceos/site-ports/', { site: id })).devices || []
  } catch (e) {
    error.value = `Não foi possível carregar as portas do site: ${e?.message || 'erro desconhecido'}`
  }
})

function undo() {
  const p = path.value.slice(0, -1)
  drawing?.setPath(p.length ? p : [ceoPoint()])
}
/** O provider do mapa pede uma cor CSS; lê-se o token (tripleto RGB) do tema. */
function tokenColor(name) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v ? `rgb(${v.split(/[\s,]+/).join(', ')})` : 'currentColor'
}
const ceoPoint = () => ({ lat: props.ceo.point[1], lng: props.ceo.point[0] })

async function save() {
  if (!canSave.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const cable = await api.post(`/api/v1/inventory/ceos/${props.ceo.id}/derive/`, {
      name: name.value,
      path: path.value,
      cable_group_id: groupId.value,
      to_site_id: target.value === 'site' ? siteId.value : null,
      to_port_id: target.value === 'site' ? portId.value : null,
      to_ceo_id: target.value === 'ceo' ? toCeoId.value : null,
    })
    emit('created', cable)
  } catch (e) {
    error.value = e?.message || 'erro desconhecido'
  } finally {
    busy.value = false
  }
}

function close() {
  emit('close')
}

onMounted(async () => {
  drawing = createRouteDrawing(props.map, {
    strokeColor: tokenColor('--info'),
    onPathChange: (p, d) => {
      path.value = p
      meters.value = d
    },
  })
  drawing.setPath([ceoPoint()])
  drawing.start()
  try {
    const body = await api.get('/api/v1/inventory/cable-groups/')
    groups.value = Array.isArray(body) ? body : body?.results || []
  } catch {
    groups.value = []
  }
})
onBeforeUnmount(() => drawing?.destroy())
</script>

<style scoped>
.cdp {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 20;
  width: 300px;
  max-height: calc(100% - 24px);
  overflow-y: auto;
  padding: 12px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 10px;
  background: rgb(var(--surface));
  box-shadow: 0 8px 24px rgb(0 0 0 / 0.18);
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.cdp-head {
  display: flex;
  align-items: center;
  font-size: 13px;
  color: rgb(var(--n-900));
}
.cdp-x {
  margin-left: auto;
  font-size: 16px;
  color: rgb(var(--n-500));
}
.cdp-hint {
  margin: 0;
  color: rgb(var(--n-600));
}
.cdp-hint .num {
  display: block;
  margin-top: 2px;
  color: rgb(var(--n-900));
}
.fld {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-weight: 600;
  color: rgb(var(--n-700));
}
.fld input,
.fld select {
  padding: 5px 8px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  background: rgb(var(--surface));
  font-weight: 400;
  color: rgb(var(--n-900));
}
.seg {
  display: inline-flex;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  overflow: hidden;
}
.seg-btn {
  flex: 1;
  padding: 4px 8px;
  font-weight: 400;
  color: rgb(var(--n-700));
  border-left: 1px solid rgb(var(--n-200));
}
.seg-btn:first-child {
  border-left: 0;
}
.seg-on {
  color: rgb(var(--primary-700));
  background: rgb(var(--primary-500) / 0.12);
  font-weight: 600;
}
.cdp-error {
  margin: 0;
  color: rgb(var(--danger));
}
.cdp-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}
.btn {
  height: 30px;
  padding: 0 10px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  color: rgb(var(--n-700));
  background: rgb(var(--surface));
}
.btn-primary {
  border-color: rgb(var(--primary-600));
  background: rgb(var(--primary-600));
  @apply text-white;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
