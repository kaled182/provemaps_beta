<template>
  <BaseModal
    :show="show"
    title="Importar rota via KML"
    subtitle="Vincula o traçado do arquivo aos dispositivos monitorados"
    :icon="PhFileArrowUp"
    :dirty="dirty"
    size="md"
    @close="close"
  >
    <form id="kml-import-form" class="space-y-3" data-testid="kml-form" @submit.prevent="submit">
      <p class="rounded-md border border-info/30 bg-info/10 px-3 py-2 text-xs text-neutral-700">
        O arquivo (<strong>.kml</strong> ou <strong>.kmz</strong>) deve ter um traçado (<em>LineString</em>) com a
        sequência de pontos origem → destino do cabo físico. Pode monitorar só a porta de origem ou definir as duas pontas.
      </p>

      <label class="block">
        <span class="kml-label">Nome da rota</span>
        <input v-model.trim="form.name" type="text" required placeholder="Ex: Backbone GYN → BSB" class="kml-input" data-testid="kml-name" />
      </label>

      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label class="block">
          <span class="kml-label">Grupo do cabo</span>
          <select v-model="form.cable_group_id" class="kml-input">
            <option value="">— Sem grupo —</option>
            <option v-for="g in groups" :key="g.id" :value="String(g.id)">{{ g.name }}</option>
          </select>
        </label>
        <label class="block">
          <span class="kml-label">Responsável</span>
          <select v-model="form.responsible_user_id" class="kml-input">
            <option value="">— Sem responsável —</option>
            <option v-for="u in users" :key="u.id" :value="String(u.id)">{{ u.full_name || u.username }}</option>
          </select>
        </label>
      </div>

      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label class="block">
          <span class="kml-label">Dispositivo origem</span>
          <select v-model="form.origin_device_id" required class="kml-input" data-testid="kml-origin-device">
            <option value="">Selecione…</option>
            <option v-for="d in devices" :key="d.id" :value="String(d.id)">{{ deviceLabel(d) }}</option>
          </select>
        </label>
        <label class="block">
          <span class="kml-label">Porta origem</span>
          <select v-model="form.origin_port_id" required class="kml-input" :disabled="!form.origin_device_id" data-testid="kml-origin-port">
            <option value="">{{ portPlaceholder(originPorts) }}</option>
            <option v-for="p in originPorts.list" :key="p.id" :value="String(p.id)">{{ p.name }}</option>
          </select>
        </label>
      </div>

      <label class="flex items-center justify-between gap-3 text-sm text-neutral-700">
        <span>Monitorar apenas a porta de origem</span>
        <input v-model="form.single_port" type="checkbox" class="h-4 w-4 accent-primary-600" data-testid="kml-single-port" />
      </label>

      <p v-if="form.single_port" class="rounded-md border border-info/30 bg-info/10 px-3 py-2 text-xs text-neutral-700" data-testid="kml-dest-notice">
        Destino desligado — só a porta de origem será monitorada.
      </p>

      <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label class="block">
          <span class="kml-label">Dispositivo destino</span>
          <select v-model="form.dest_device_id" required class="kml-input" data-testid="kml-dest-device">
            <option value="">Selecione…</option>
            <option v-for="d in devices" :key="d.id" :value="String(d.id)">{{ deviceLabel(d) }}</option>
          </select>
        </label>
        <label class="block">
          <span class="kml-label">Porta destino</span>
          <select v-model="form.dest_port_id" required class="kml-input" :disabled="!form.dest_device_id" data-testid="kml-dest-port">
            <option value="">{{ portPlaceholder(destPorts) }}</option>
            <option v-for="p in destPorts.list" :key="p.id" :value="String(p.id)">{{ p.name }}</option>
          </select>
        </label>
      </div>

      <label class="block">
        <span class="kml-label">Arquivo KML/KMZ</span>
        <input ref="fileInput" type="file" accept=".kml,.kmz" required class="kml-input" data-testid="kml-file" @change="onFile" />
      </label>

      <p v-if="error" class="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger" role="alert" data-testid="kml-error">
        {{ error }}
      </p>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <button type="button" class="h-8 rounded-md border border-neutral-200 px-3 text-sm text-neutral-700 hover:bg-neutral-100" @click="close">
          Cancelar
        </button>
        <button
          type="submit"
          form="kml-import-form"
          class="h-8 rounded-md bg-primary-600 px-3 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          :disabled="submitting"
          data-testid="kml-submit"
        >
          {{ submitting ? 'A importar…' : 'Importar rota' }}
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
/**
 * Importação de rota por KML no Projeto de rede (EV-0034). Substitui o
 * `features/networkDesign/partials/import_kml.js`, que manipulava por
 * `getElementById` o HTML que vivia no NetworkDesignView e publicava
 * `window.openKmlModal`/`closeKmlModal`/`initializeKmlModal`/`__FIBER_DEVICE_OPTIONS`.
 * Tudo por `useApi` (CSRF); o resultado sai por `imported` e pelo evento
 * `fiber:cable-created` que o fiberRouteBuilder já escuta.
 */
import { computed, reactive, ref, watch } from 'vue'
import { PhFileArrowUp } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'

const props = defineProps({
  show: { type: Boolean, default: false },
  /** [{ id, name, site }] — vem do evento `fiber:device-options-loaded` */
  devices: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'imported'])

const api = useApi()
const { success } = useNotification()

const emptyForm = () => ({
  name: '',
  cable_group_id: '',
  responsible_user_id: '',
  origin_device_id: '',
  origin_port_id: '',
  single_port: false,
  dest_device_id: '',
  dest_port_id: '',
})
const form = reactive(emptyForm())
const file = ref(null)
const fileInput = ref(null)
const groups = ref([])
const users = ref([])
const originPorts = reactive({ list: [], state: 'idle' })
const destPorts = reactive({ list: [], state: 'idle' })
const error = ref('')
const submitting = ref(false)

const dirty = computed(() => JSON.stringify(form) !== JSON.stringify(emptyForm()) || Boolean(file.value))

const deviceLabel = (d) => (d.site ? `${d.name} (${d.site})` : d.name)
const portPlaceholder = (ports) =>
  ports.state === 'loading' ? 'A carregar…' : ports.state === 'error' ? 'Falha ao carregar as portas' : 'Selecione…'

async function loadPorts(deviceId, target) {
  target.list = []
  if (!deviceId) {
    target.state = 'idle'
    return
  }
  target.state = 'loading'
  try {
    const data = await api.get(`/api/v1/inventory/devices/${encodeURIComponent(deviceId)}/ports/`)
    target.list = Array.isArray(data?.ports) ? data.ports : []
    target.state = 'ok'
  } catch (e) {
    console.error('[KmlImportModal] Falha ao carregar portas:', e)
    target.state = 'error'
  }
}

watch(
  () => form.origin_device_id,
  (id) => {
    form.origin_port_id = ''
    loadPorts(id, originPorts)
  },
)
watch(
  () => form.dest_device_id,
  (id) => {
    form.dest_port_id = ''
    loadPorts(id, destPorts)
  },
)
watch(
  () => form.single_port,
  (single) => {
    if (single) {
      form.dest_device_id = ''
      form.dest_port_id = ''
    }
  },
)

async function loadLookups() {
  const [g, u] = await Promise.allSettled([
    api.get('/api/v1/inventory/cable-groups/'),
    api.get('/api/users/', { is_active: true }),
  ])
  groups.value = g.status === 'fulfilled' ? g.value?.results || [] : []
  users.value = u.status === 'fulfilled' ? u.value?.users || [] : []
}

function reset() {
  Object.assign(form, emptyForm())
  file.value = null
  if (fileInput.value) fileInput.value.value = ''
  originPorts.list = []
  originPorts.state = 'idle'
  destPorts.list = []
  destPorts.state = 'idle'
  error.value = ''
}

watch(
  () => props.show,
  (open) => {
    if (open) {
      error.value = ''
      loadLookups()
    }
  },
  { immediate: true },
)

const onFile = (event) => {
  file.value = event.target.files?.[0] || null
}

const close = () => emit('close')

async function submit() {
  error.value = ''
  if (!file.value) {
    error.value = 'Escolha o arquivo KML/KMZ.'
    return
  }
  const body = new FormData()
  for (const [k, v] of Object.entries(form)) {
    if (k === 'single_port') {
      if (v) body.append('single_port', 'true')
    } else if (v !== '') {
      body.append(k, v)
    }
  }
  body.append('kml_file', file.value)
  submitting.value = true
  try {
    const data = await api.postFormData('/api/v1/inventory/fibers/import-kml/', body)
    success('Rota importada', `${data?.points ?? '?'} pontos.`)
    document.dispatchEvent(new CustomEvent('fiber:cable-created', { detail: { fiberId: data?.fiber_id } }))
    emit('imported', data)
    reset()
    emit('close')
  } catch (e) {
    error.value = e?.message || 'Erro ao importar a rota.'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.kml-label {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  font-weight: 500;
  color: rgb(var(--n-700));
}
.kml-input {
  width: 100%;
  border-radius: 6px;
  border: 1px solid rgb(var(--n-200));
  background: rgb(var(--surface));
  padding: 6px 10px;
  font-size: 14px;
  color: rgb(var(--n-900));
}
.kml-input:focus {
  outline: none;
  border-color: rgb(var(--primary-500));
}
.kml-input:disabled {
  opacity: 0.6;
}
</style>
