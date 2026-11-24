<template>
  <div class="csv" data-testid="cable-structure">
    <!-- Cabeçalho: cabo, perfil e contagens por estado -->
    <header class="csv-head">
      <div class="min-w-0">
        <h3 class="csv-title">{{ structure.name || 'A carregar a estrutura…' }}</h3>
        <p class="csv-sub">
          {{ structure.profile_name || 'Sem perfil' }} · {{ tubes.length }} {{ tubes.length === 1 ? 'tubo' : 'tubos' }} ·
          {{ allStrands.length }} fibras
        </p>
      </div>
      <ul class="csv-legend" aria-label="Legenda">
        <li v-for="s in STATES" :key="s.key" :data-testid="`legend-${s.key}`">
          <span class="dot" :class="`st-${s.key}`" aria-hidden="true" />{{ s.label }}
          <b class="num">{{ counts[s.key] || 0 }}</b>
        </li>
      </ul>
    </header>

    <p v-if="loading && !loaded" class="csv-msg">A carregar a estrutura do cabo…</p>
    <div v-else-if="error" class="csv-msg csv-error" role="alert">
      Erro ao carregar a estrutura do cabo: {{ error }}
      <button type="button" class="csv-link" @click="fetchStructure">Tentar novamente</button>
    </div>

    <!-- EV-0133: cabo sem perfil nem grupo — escolher o nº de fibras para gerar a estrutura -->
    <div v-else-if="structure.needs_profile" class="csv-msg" data-testid="structure-needs-profile">
      <p>Este cabo não tem grupo nem perfil: escolha o nº de fibras para gerar os tubos loose e as fibras (cores ABNT).</p>
      <div class="flex items-center justify-center gap-2 mt-2">
        <select v-model="pickedProfile" class="csv-select" data-testid="structure-profile-select">
          <option :value="null" disabled>Escolher o perfil…</option>
          <option v-for="p in structure.available_profiles || []" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <button type="button" class="csv-btn csv-btn-primary" :disabled="!pickedProfile || busy" data-testid="structure-generate" @click="generate">
          {{ busy ? 'A gerar…' : 'Gerar estrutura' }}
        </button>
      </div>
      <p v-if="actionError" class="csv-error mt-2" role="alert">{{ actionError }}</p>
    </div>

    <div v-else-if="loaded" class="csv-body">
      <!-- Diagrama -->
      <div class="csv-diagram">
        <p v-if="structure.otdr_alert" class="csv-otdr" role="alert" data-testid="structure-otdr">
          Rompimento OTDR ativo neste cabo{{ otdrWhere }} — as fibras aparecem como rompidas até o atendimento ser concluído.
        </p>
        <section v-for="tube in tubes" :key="tube.id" class="tube" :data-testid="`tube-${tube.number}`">
          <header class="tube-head">
            <span class="tube-swatch" :style="{ background: tube.color_hex }" aria-hidden="true" />
            Tubo {{ tube.number }} · {{ tube.color }}
          </header>
          <div class="tube-fibers">
            <button
              v-for="f in tube.strands"
              :key="f.id"
              type="button"
              class="fiber"
              :class="[`st-${f.state}`, { 'fiber-on': selected?.id === f.id }]"
              :title="`Fibra ${f.absolute_number} · ${f.color} · ${STATE_LABEL[f.state]}`"
              :aria-pressed="selected?.id === f.id"
              :data-testid="`fiber-${f.absolute_number}`"
              @click="select(f, tube)"
            >
              <span class="fiber-core" :style="{ background: f.color_hex }" aria-hidden="true" />
              <span class="fiber-num num">{{ f.number }}</span>
            </button>
          </div>
        </section>
      </div>

      <!-- Painel da fibra selecionada -->
      <aside class="csv-panel" data-testid="fiber-panel">
        <p v-if="!selected" class="csv-hint" data-testid="fiber-hint">Selecione uma fibra no diagrama.</p>
        <template v-else>
          <h4 class="panel-title">
            <span class="fiber-core sm" :style="{ background: selected.color_hex }" aria-hidden="true" />
            Fibra {{ selected.absolute_number }}
            <span class="panel-sub">· Tubo {{ selectedTube.number }} ({{ selectedTube.color }}) · {{ selected.color }}</span>
          </h4>
          <p class="panel-state" :class="`st-text-${selected.state}`" data-testid="fiber-state">{{ STATE_LABEL[selected.state] }}</p>

          <!-- Pontas A e B: «Conectar a porta» -->
          <div v-for="end in ['a', 'b']" :key="end" class="panel-end" :data-testid="`end-${end}`">
            <p class="end-title">Ponta {{ end.toUpperCase() }} · {{ ends[end]?.site_name || (ends[end]?.ceo_name ? `na ${ends[end].ceo_name} (emenda na caixa)` : 'sem site no cabo') }}</p>
            <p v-if="portOf(selected, end)" class="end-port" :data-testid="`end-${end}-port`">
              {{ portOf(selected, end).device_name }} → <span class="num">{{ portOf(selected, end).name }}</span>
            </p>
            <p v-else class="end-free">Sem porta ligada</p>
            <div v-if="ends[end]?.devices?.length" class="end-form">
              <select v-model="pick[end]" class="csv-select" :aria-label="`Porta da ponta ${end.toUpperCase()}`" :data-testid="`end-${end}-select`">
                <option :value="null">Escolher a porta…</option>
                <optgroup v-for="d in ends[end].devices" :key="d.id" :label="d.name">
                  <option v-for="p in d.ports" :key="p.id" :value="p.id" :disabled="!!p.used_by && p.used_by.strand_id !== selected.id">
                    {{ p.name }}{{ p.used_by && p.used_by.strand_id !== selected.id ? ` (fibra ${p.used_by.absolute_number} · ${p.used_by.cable_name})` : '' }}
                  </option>
                </optgroup>
              </select>
              <button type="button" class="csv-btn csv-btn-primary" :disabled="!pick[end] || busy" :data-testid="`end-${end}-connect`" @click="connect(end, pick[end])">
                Conectar
              </button>
              <button v-if="portOf(selected, end)" type="button" class="csv-btn" :disabled="busy" :data-testid="`end-${end}-disconnect`" @click="connect(end, null)">
                Desligar
              </button>
            </div>
            <p v-else-if="ends[end]?.site_name" class="end-free">Nenhum equipamento cadastrado neste site.</p>
          </div>

          <div v-if="selected.fusions?.length" class="panel-fusions">
            <p class="end-title">Fusões</p>
            <p v-for="(fu, i) in selected.fusions" :key="i" class="end-port">{{ fusionText(fu) }}</p>
          </div>
          <p v-if="actionError" class="csv-error" role="alert" data-testid="fiber-error">{{ actionError }}</p>
        </template>
      </aside>
    </div>
  </div>
</template>

<script setup>
/**
 * Estrutura física do cabo (EV-0133/0134): tubos loose com a cor ABNT e as fibras, cada uma com o
 * estado (rompida > iluminada > fusionada > livre, calculado no servidor) e o painel da fibra
 * com «Conectar a porta» nas pontas Site A / Site B.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({
  cableId: { type: [Number, String], required: true },
})
const emit = defineEmits(['select-fiber'])

const STATES = [
  { key: 'lit', label: 'Iluminada' },
  { key: 'fused', label: 'Fusionada' },
  { key: 'free', label: 'Livre' },
  { key: 'broken', label: 'Rompida' },
]
const STATE_LABEL = Object.fromEntries(STATES.map((s) => [s.key, s.label]))

const api = useApi()
const structure = ref({ tubes: [] })
const loaded = ref(false)
const loading = ref(false)
const error = ref('')
const busy = ref(false)
const actionError = ref('')
const pickedProfile = ref(null)
const selectedId = ref(null)
const pick = reactive({ a: null, b: null })

const tubes = computed(() => structure.value.tubes || [])
const allStrands = computed(() => tubes.value.flatMap((t) => t.strands || []))
const counts = computed(() => allStrands.value.reduce((acc, f) => ({ ...acc, [f.state]: (acc[f.state] || 0) + 1 }), {}))
const ends = computed(() => structure.value.ends || {})
const selected = computed(() => allStrands.value.find((f) => f.id === selectedId.value) || null)
const selectedTube = computed(() => tubes.value.find((t) => (t.strands || []).some((f) => f.id === selectedId.value)) || {})
const otdrWhere = computed(() => {
  const o = structure.value.otdr_alert
  if (!o?.map_distance_m) return ''
  const km = (o.map_distance_m / 1000).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return ` (a ${km} km${o.origin_name ? ` de ${o.origin_name}` : ''})`
})

const portOf = (f, end) => (end === 'a' ? f.port_a : f.port_b)

function fusionText(fu) {
  const where = fu.infrastructure_name || 'CEO'
  const num = fu.peer_absolute_number ?? fu.peer_number
  return `${where}: ${fu.peer_cable_name || 'outro cabo'}${num !== null && num !== undefined ? ` · fibra ${num}` : ''}`
}

async function fetchStructure() {
  if (!props.cableId) return
  loading.value = true
  error.value = ''
  try {
    // EV-0133: /api/v1/… e o JSON já lido pelo useApi (não há .data)
    structure.value = await api.get(`/api/v1/fiber-cables/${encodeURIComponent(props.cableId)}/structure/`)
    loaded.value = true
  } catch (e) {
    error.value = e?.message || 'erro desconhecido'
  } finally {
    loading.value = false
  }
}

async function generate() {
  if (!pickedProfile.value || busy.value) return
  busy.value = true
  actionError.value = ''
  try {
    await api.post(`/api/v1/fiber-cables/${encodeURIComponent(props.cableId)}/structure/profile/`, {
      profile_id: pickedProfile.value,
    })
    await fetchStructure()
  } catch (e) {
    actionError.value = `Não foi possível gerar: ${e?.message || 'erro desconhecido'}`
  } finally {
    busy.value = false
  }
}

function select(fiber, tube) {
  selectedId.value = fiber.id
  actionError.value = ''
  pick.a = fiber.port_a?.id ?? null
  pick.b = fiber.port_b?.id ?? null
  emit('select-fiber', { ...fiber, tube_number: tube.number, tube_color: tube.color })
}

/** EV-0134: liga (ou desliga, com null) a ponta da fibra a uma porta do site dessa ponta. */
async function connect(end, portId) {
  if (!selected.value || busy.value) return
  busy.value = true
  actionError.value = ''
  try {
    await api.post(
      `/api/v1/fiber-cables/${encodeURIComponent(props.cableId)}/strands/${selected.value.id}/port/`,
      { end, port_id: portId },
    )
    await fetchStructure()
    const f = selected.value
    if (f) {
      pick.a = f.port_a?.id ?? null
      pick.b = f.port_b?.id ?? null
    }
  } catch (e) {
    actionError.value = e?.message || 'erro desconhecido'
  } finally {
    busy.value = false
  }
}

watch(
  () => props.cableId,
  () => {
    selectedId.value = null
    loaded.value = false
    fetchStructure()
  },
)
onMounted(fetchStructure)
</script>

<style scoped>
.csv {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: rgb(var(--surface));
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.csv-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid rgb(var(--n-200));
}
.csv-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: rgb(var(--n-900));
}
.csv-sub {
  margin: 2px 0 0;
  font-size: 12px;
  color: rgb(var(--n-500));
}
.csv-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 12px;
  color: rgb(var(--n-700));
}
.csv-legend li {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  border: 2px solid currentColor;
}
.csv-msg {
  padding: 40px 16px;
  text-align: center;
  font-size: 13px;
  color: rgb(var(--n-600));
}
.csv-error {
  color: rgb(var(--danger));
  font-size: 13px;
}
.csv-link {
  margin-left: 6px;
  text-decoration: underline;
}
.csv-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
}
@media (min-width: 1024px) {
  .csv-body {
    grid-template-columns: minmax(0, 1fr) 320px;
  }
}
.csv-diagram {
  padding: 16px;
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 12px;
  overflow-y: auto;
  background: rgb(var(--canvas));
}
.csv-otdr {
  flex-basis: 100%;
  margin: 0;
  padding: 8px 12px;
  border: 1px solid rgb(var(--danger) / 0.4);
  border-radius: 8px;
  background: rgb(var(--danger) / 0.08);
  color: rgb(var(--danger));
  font-size: 12px;
}
.tube {
  padding: 10px 12px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 10px;
  background: rgb(var(--surface));
}
.tube-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: rgb(var(--n-800));
}
.tube-swatch {
  width: 22px;
  height: 10px;
  border-radius: 999px;
  border: 1px solid rgb(var(--n-400));
}
.tube-fibers {
  display: grid;
  grid-template-columns: repeat(6, 34px);
  gap: 6px;
}
.fiber {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 3px 0;
  border-radius: 8px;
  border: 2px solid currentColor;
  background: rgb(var(--surface));
}
.fiber-on {
  box-shadow: 0 0 0 2px rgb(var(--primary-500));
}
.fiber-core {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  border: 1px solid rgb(var(--n-400));
}
.fiber-core.sm {
  display: inline-block;
  width: 12px;
  height: 12px;
  vertical-align: -1px;
}
.fiber-num {
  font-size: 10px;
  color: rgb(var(--n-700));
}
/* estado: a cor do anel (iluminada verde, fusionada ciano/info, livre cinza, rompida coral) */
.st-lit {
  color: rgb(var(--success));
}
.st-fused {
  color: rgb(var(--info));
}
.st-free {
  color: rgb(var(--n-300));
}
.st-broken {
  color: rgb(var(--danger));
}
.st-text-lit {
  color: rgb(var(--success));
}
.st-text-fused {
  color: rgb(var(--info));
}
.st-text-free {
  color: rgb(var(--n-500));
}
.st-text-broken {
  color: rgb(var(--danger));
}
.csv-panel {
  padding: 14px 16px;
  border-left: 1px solid rgb(var(--n-200));
  overflow-y: auto;
  font-size: 13px;
}
.csv-hint {
  color: rgb(var(--n-500));
}
.panel-title {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: rgb(var(--n-900));
}
.panel-sub {
  font-size: 12px;
  font-weight: 400;
  color: rgb(var(--n-500));
}
.panel-state {
  margin: 2px 0 10px;
  font-size: 12px;
  font-weight: 600;
}
.panel-end,
.panel-fusions {
  padding: 10px 0;
  border-top: 1px solid rgb(var(--n-200));
}
.end-title {
  margin: 0 0 4px;
  font-size: 12px;
  font-weight: 600;
  color: rgb(var(--n-700));
}
.end-port {
  margin: 0 0 6px;
  font-size: 12px;
  color: rgb(var(--n-900));
}
.end-free {
  margin: 0 0 6px;
  font-size: 12px;
  color: rgb(var(--n-500));
}
.end-form {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.csv-select {
  min-width: 0;
  flex: 1;
  padding: 5px 8px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  background: rgb(var(--surface));
  font-size: 12px;
  color: rgb(var(--n-900));
}
.csv-btn {
  height: 30px;
  padding: 0 10px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  background: rgb(var(--surface));
  font-size: 12px;
  color: rgb(var(--n-700));
}
.csv-btn-primary {
  border-color: rgb(var(--primary-600));
  background: rgb(var(--primary-600));
  @apply text-white;
}
.csv-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
