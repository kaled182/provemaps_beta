<template>
  <BaseModal :show="show" :title="title" :subtitle="modeHint" :icon="PhGitMerge" size="detail" @close="$emit('close')">
    <p v-if="loading && !data" class="py-8 text-center text-sm text-neutral-500">A carregar as fibras da caixa…</p>
    <p v-else-if="error && !data" class="py-8 text-center text-sm text-danger" role="alert">Erro ao carregar: {{ error }}</p>
    <div v-else-if="data" data-testid="splice-box">
      <p v-if="!readonly" class="sb-help" data-testid="splice-help">
        <template v-if="pickTarget">Clique na fibra para a <b>{{ pickTarget.label }}</b>.</template>
        <template v-else-if="tubePick">Escolha o tubo de destino de <b>{{ tubePick.label }}</b> («Fundir aqui») — fibra 1 com 1, 2 com 2…</template>
        <template v-else-if="picked">Fibra escolhida: <b>{{ endLabel(picked) }}</b> — clique na fibra a fundir.</template>
        <template v-else>Clique numa fibra e depois noutra para criar a fusão, ou «1:1» num tubo para o fundir inteiro.</template>
      </p>
      <p v-if="error" class="sb-error" role="alert" data-testid="splice-error">{{ error }}</p>
      <p v-if="notice" class="sb-notice" role="status" data-testid="splice-notice">{{ notice }}</p>

      <div class="sb-grid">
        <SpliceSide
          side="a"
          title="Entrada · rumo à origem"
          :groups="groupsOf('a')"
          :partners="partners"
          :picked="picked?.key || null"
          :tube-pick="tubePick"
          :readonly="readonly"
          @pick="pick"
          @tube-pick="tubePick = $event"
          @tube-target="fuseTube"
        />

        <!-- Bandeja: as fusões por posição -->
        <section class="sb-tray" data-testid="splice-tray">
          <h4 class="sb-title">Bandeja · {{ data.fusions.length }} {{ data.fusions.length === 1 ? 'fusão' : 'fusões' }}</h4>
          <p v-if="!data.fusions.length" class="sb-empty">Sem fusões nesta caixa.</p>
          <div v-for="tray in trays" :key="tray.number" class="sb-tray-group">
            <p class="sb-tray-name">Bandeja {{ tray.number ?? '—' }} <span class="num">{{ tray.fusions.length }}/{{ data.ceo.splices_per_tray }}</span></p>
            <div v-for="f in tray.fusions" :key="f.id" class="sb-row" :data-testid="`fusion-${f.id}`">
              <span class="num sb-slot">{{ f.slot ?? '–' }}</span>
              <span class="sb-end" :title="short(f.a)"><span class="sb-core" :style="{ background: f.a.color_hex }" />{{ trayLabel(f.a) }}</span>
              <span class="sb-link" aria-hidden="true">↔</span>
              <span class="sb-end" :title="short(f.b)"><span class="sb-core" :style="{ background: f.b.color_hex }" />{{ trayLabel(f.b) }}</span>
              <button v-if="!readonly" type="button" class="sb-del" :disabled="busy" :data-testid="`fusion-del-${f.id}`" @click="remove(f)">Desfazer</button>
              <button type="button" class="sb-trace" :data-testid="`fusion-trace-${f.id}`" @click="traced = traced?.id === f.id ? null : f">
                {{ traced?.id === f.id ? 'Fechar' : 'Rastrear' }}
              </button>
              <!-- a luz que entra pela ponta para onde segue a metade A da fusão passa nesta emenda -->
              <FiberTrace v-if="traced?.id === f.id" class="sb-trace-box" :strand-id="f.a.strand_id" :start="f.a.side" />
            </div>
          </div>
          <!-- EV-0142: splitters -->
          <SplitterPanel
            :splitters="data.splitters || []"
            :readonly="readonly"
            :busy="busy"
            :pick-target="pickTarget"
            @add="addSplitter"
            @remove="removeSplitter"
            @unlink-input="(sp) => patchSplitter(sp, { input: null }, 'Entrada desligada.')"
            @pick-target="setPickTarget"
            @save-port="savePort"
          />
        </section>

        <SpliceSide
          side="b"
          title="Saída · rumo ao destino"
          :groups="groupsOf('b')"
          :partners="partners"
          :picked="picked?.key || null"
          :tube-pick="tubePick"
          :readonly="readonly"
          @pick="pick"
          @tube-pick="tubePick = $event"
          @tube-target="fuseTube"
        />
      </div>
    </div>
    <template #footer>
      <div class="flex justify-end gap-2">
        <EditInProjectLink v-if="readonly" type="ceo" :target="ceo" />
        <button type="button" class="sb-btn" @click="$emit('close')">Fechar</button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
/**
 * Editor de emendas da CEO/CTO (EV-0141), em 3 colunas: Entrada (metades que seguem para a
 * origem, lado «a») → Bandeja (fusões por posição) → Saída (lado «b»). Tubos em acordeão com a
 * ocupação; fusão fibra a fibra com dois cliques (posição automática) e «1:1» para fundir um tubo
 * inteiro cor com cor. `readonly` no monitoramento: vê-se e rastreia-se, não se edita.
 */
import { computed, ref, watch } from 'vue'
import { PhGitMerge } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import EditInProjectLink from '@/components/Map/EditInProjectLink.vue'
import FiberTrace from '@/components/Inventory/Fibers/FiberTrace.vue'
import SpliceSide from './SpliceSide.vue'
import SplitterPanel from './SplitterPanel.vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({
  show: { type: Boolean, default: false },
  ceo: { type: Object, required: true },
  readonly: { type: Boolean, default: false },
})
defineEmits(['close'])

const api = useApi()
const data = ref(null)
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const picked = ref(null)
const tubePick = ref(null)
const traced = ref(null)
const pickTarget = ref(null) // EV-0142: a fibra clicada vai para a entrada/saída de um splitter
const url = computed(() => `/api/v1/inventory/ceos/${props.ceo.id}/fusions/`)

const title = computed(() => `${data.value?.ceo?.kind === 'cto' ? 'CTO' : 'Emendas'} · ${data.value?.ceo?.name || props.ceo.name}`)
const modeHint = computed(() =>
  (data.value?.ceo?.mode || props.ceo.mode) === 'corte'
    ? 'Corte / emenda total: fibra do tronco sem emenda acaba na caixa'
    : 'Sangria: fibra do tronco sem emenda passa direto pela caixa',
)

/** Cabos do lado pedido, com os tubos e a ocupação de cada tubo. */
function groupsOf(side) {
  return (data.value?.cables || [])
    .map((c) => {
      const ends = c.ends.filter((e) => e.side === side)
      if (!ends.length) return null
      const byTube = new Map()
      for (const e of ends) {
        const t = byTube.get(e.tube_number) || { number: e.tube_number, color: e.tube_color, colorHex: e.tube_color_hex, ends: [], fused: 0 }
        t.ends.push(e)
        if (e.fusion_id || e.splitter_use) t.fused += 1
        byTube.set(e.tube_number, t)
      }
      return { key: `${c.id}:${side}`, cableId: c.id, cableName: c.name, toward: ends[0].toward, tubes: [...byTube.values()] }
    })
    .filter(Boolean)
}

const short = (e) => `${e.cable_name} · F${e.absolute_number}`
/** Na bandeja a fibra vem primeiro: se o nome do cabo cortar, o número fica à vista. */
const trayLabel = (e) => `F${e.absolute_number} ${e.cable_name}`
const endLabel = (e) => `${e.cable_name} · fibra ${e.absolute_number} (${e.color}) → ${e.toward}`

/** «fusionId:chaveDaPonta» → a outra ponta, para mostrar ao lado de cada fibra emendada. */
const partners = computed(() => {
  const out = {}
  for (const f of data.value?.fusions || []) {
    out[`${f.id}:${f.a.key}`] = short(f.b)
    out[`${f.id}:${f.b.key}`] = short(f.a)
  }
  return out
})

const trays = computed(() => {
  const m = new Map()
  for (const f of data.value?.fusions || []) {
    const t = m.get(f.tray) || { number: f.tray, fusions: [] }
    t.fusions.push(f)
    m.set(f.tray, t)
  }
  return [...m.values()].sort((a, b) => (a.number ?? 999) - (b.number ?? 999))
})

async function load() {
  loading.value = true
  try {
    data.value = await api.get(url.value)
    error.value = ''
  } catch (e) {
    error.value = e?.message || 'erro desconhecido'
  } finally {
    loading.value = false
  }
}

async function run(fn, done) {
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    const r = await fn()
    notice.value = done(r)
    await load()
  } catch (e) {
    error.value = e?.message || 'erro desconhecido'
  } finally {
    busy.value = false
  }
}

function pick(e) {
  if (props.readonly || busy.value) return
  tubePick.value = null
  if (pickTarget.value) {
    const t = pickTarget.value
    pickTarget.value = null
    const end = { strand_id: e.strand_id, side: e.side }
    if (t.type === 'input') return patchSplitter({ id: t.splitterId }, { input: end }, `Entrada ligada: ${short(e)}.`)
    return run(
      () => api.patch(`${spUrl(t.splitterId)}ports/${t.number}/`, { output: end }),
      () => `Porta ${t.number} → ${short(e)}.`,
    )
  }
  if (!picked.value) {
    picked.value = e
    return
  }
  if (picked.value.key === e.key) {
    picked.value = null
    return
  }
  const a = picked.value
  picked.value = null
  run(
    () => api.post(url.value, { a: { strand_id: a.strand_id, side: a.side }, b: { strand_id: e.strand_id, side: e.side } }),
    () => `Fusão criada: ${short(a)} ↔ ${short(e)}.`,
  )
}

function fuseTube(target) {
  if (!tubePick.value) return
  const { label, ...a } = tubePick.value
  tubePick.value = null
  run(
    () => api.post(`${url.value}tube/`, { a, b: target }),
    (r) => `${label}: ${r.created} ${r.created === 1 ? 'fusão criada' : 'fusões criadas'}${r.skipped ? ` · ${r.skipped} fibra(s) já emendada(s) ou sem par ficaram de fora` : ''}.`,
  )
}

// ── splitters (EV-0142) ──────────────────────────────────────────────────────
const spUrl = (id) => `/api/v1/inventory/ceos/${props.ceo.id}/splitters/${id}/`
function setPickTarget(t) {
  picked.value = null
  tubePick.value = null
  pickTarget.value = t
}
function addSplitter(ratio) {
  run(() => api.post(`/api/v1/inventory/ceos/${props.ceo.id}/splitters/`, { ratio }), () => `Splitter ${ratio} acrescentado.`)
}
function removeSplitter(sp) {
  run(() => api.delete(spUrl(sp.id)), () => `${sp.name} removido.`)
}
function patchSplitter(sp, body, done) {
  return run(() => api.patch(spUrl(sp.id), body), () => done)
}
function savePort(sp, number, body) {
  run(() => api.patch(`${spUrl(sp.id)}ports/${number}/`, body), () => `Porta ${number} atualizada.`)
}

function remove(f) {
  run(() => api.delete(`${url.value}${f.id}/`), () => 'Fusão desfeita.')
}

watch(
  () => [props.show, props.ceo.id],
  ([open]) => {
    if (open) {
      picked.value = null
      tubePick.value = null
      pickTarget.value = null
      notice.value = ''
      load()
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.sb-help {
  margin: 0 0 10px;
  font-size: 12px;
  color: rgb(var(--n-600));
}
.sb-error {
  margin: 0 0 8px;
  font-size: 12px;
  color: rgb(var(--danger));
}
.sb-notice {
  margin: 0 0 8px;
  font-size: 12px;
  color: rgb(var(--success));
}
.sb-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
}
@media (min-width: 1100px) {
  .sb-grid {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr) minmax(0, 1fr);
  }
}
.sb-tray {
  padding: 10px;
  border-radius: 10px;
  background: rgb(var(--canvas));
  border: 1px solid rgb(var(--n-200));
  min-width: 0;
}
.sb-title {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgb(var(--n-500));
}
.sb-empty {
  font-size: 12px;
  color: rgb(var(--n-500));
}
.sb-tray-name {
  margin: 6px 0 4px;
  font-size: 12px;
  font-weight: 600;
  color: rgb(var(--n-700));
}
.sb-row {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto minmax(0, 1fr) auto auto;
  gap: 6px;
  align-items: center;
  padding: 4px 0;
  border-top: 1px solid rgb(var(--n-200));
  font-size: 11px;
  color: rgb(var(--n-900));
}
.sb-slot {
  color: rgb(var(--n-500));
}
.sb-end {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sb-core {
  flex: none;
  width: 9px;
  height: 9px;
  border-radius: 999px;
  border: 1px solid rgb(var(--n-400));
}
.sb-link {
  color: rgb(var(--info));
}
.sb-del {
  color: rgb(var(--danger));
}
.sb-trace {
  color: rgb(var(--primary-600));
}
.sb-trace-box {
  grid-column: 1 / -1;
}
.sb-btn {
  height: 30px;
  padding: 0 12px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  font-size: 12px;
  color: rgb(var(--n-700));
  background: rgb(var(--surface));
}
</style>
