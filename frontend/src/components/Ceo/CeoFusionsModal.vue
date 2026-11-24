<template>
  <BaseModal :show="show" :title="`Emendas · ${data?.ceo?.name || ceo.name}`" :subtitle="modeHint" :icon="PhGitMerge" size="detail" @close="$emit('close')">
    <p v-if="loading && !data" class="py-8 text-center text-sm text-neutral-500">A carregar as fibras da caixa…</p>
    <p v-else-if="error && !data" class="py-8 text-center text-sm text-danger" role="alert">Erro ao carregar: {{ error }}</p>
    <div v-else-if="data" class="cfm" data-testid="ceo-fusions">
      <!-- Pontas de fibra por cabo -->
      <div class="cfm-cables">
        <p v-if="!data.cables.length" class="text-sm text-neutral-500">Nenhum cabo com estrutura de fibras passa nesta caixa.</p>
        <section v-for="c in data.cables" :key="c.id" class="cfm-cable" :data-testid="`fusion-cable-${c.id}`">
          <h4 class="cfm-cable-title">{{ c.name }} <span class="cfm-role">{{ ROLE[c.role] }}</span></h4>
          <p v-if="!c.ends.length" class="text-xs text-neutral-500">Cabo sem estrutura de fibras (abra a estrutura e gere-a).</p>
          <div class="cfm-ends">
            <button
              v-for="e in c.ends"
              :key="e.key"
              type="button"
              class="end"
              :class="{ 'end-used': e.fusion_id, 'end-a': pickA?.key === e.key, 'end-b': pickB?.key === e.key }"
              :disabled="readonly || !!e.fusion_id"
              :title="`Fibra ${e.absolute_number} (${e.color}, tubo ${e.tube_number}) → ${e.toward}${e.fusion_id ? ' · já emendada' : ''}`"
              :data-testid="`end-${e.key}`"
              @click="pick(e)"
            >
              <span class="core" :style="{ background: e.color_hex }" aria-hidden="true" />
              <span class="num">{{ e.absolute_number }}</span>
              <span v-if="c.role === 'tronco'" class="end-side">→ {{ e.side.toUpperCase() }}</span>
            </button>
          </div>
          <p v-if="c.role === 'tronco'" class="text-xs text-neutral-500 mt-1">
            «→ A» é a metade que segue para {{ c.ends.find((e) => e.side === 'a')?.toward || 'a ponta A' }}; «→ B» para
            {{ c.ends.find((e) => e.side === 'b')?.toward || 'a ponta B' }}.
          </p>
        </section>
      </div>

      <!-- Criar fusão e lista -->
      <aside class="cfm-side">
        <template v-if="!readonly">
        <h4 class="cfm-h">Criar fusão</h4>
        <p class="cfm-pick" data-testid="fusion-pick-a">Fibra A: <b>{{ label(pickA) || 'clique numa fibra' }}</b></p>
        <p class="cfm-pick" data-testid="fusion-pick-b">Fibra B: <b>{{ label(pickB) || (pickA ? 'clique na outra fibra' : '—') }}</b></p>
        <div class="grid grid-cols-2 gap-2 mt-2">
          <label class="fld"><span>Bandeja</span><input v-model.number="tray" type="number" min="1" :max="data.ceo.trays" data-testid="fusion-tray" /></label>
          <label class="fld"><span>Posição</span><input v-model.number="slot" type="number" min="1" :max="data.ceo.splices_per_tray" data-testid="fusion-slot" /></label>
        </div>
        <div class="flex gap-2 mt-2">
          <button type="button" class="btn btn-primary" :disabled="!pickA || !pickB || busy" data-testid="fusion-create" @click="create">Criar fusão</button>
          <button type="button" class="btn" :disabled="!pickA" @click="clearPick">Limpar</button>
        </div>
        <p v-if="error && data" class="text-xs text-danger mt-1" role="alert" data-testid="fusion-error">{{ error }}</p>
        </template>
        <p v-else class="text-xs text-neutral-500" data-testid="fusion-readonly">
          Só leitura no monitoramento — as emendas editam-se no Projeto de Rede.
        </p>

        <h4 class="cfm-h mt-4">Fusões nesta caixa ({{ data.fusions.length }})</h4>
        <p v-if="!data.fusions.length" class="text-xs text-neutral-500">Nenhuma ainda.</p>
        <ul class="cfm-list">
          <li v-for="f in data.fusions" :key="f.id" :data-testid="`fusion-${f.id}`">
            <span class="num text-neutral-500">{{ f.tray ? `B${f.tray}·${f.slot ?? '–'}` : '—' }}</span>
            <span class="min-w-0">{{ label(f.a) }} ↔ {{ label(f.b) }}</span>
            <button v-if="!readonly" type="button" class="cfm-del" :disabled="busy" :data-testid="`fusion-del-${f.id}`" @click="remove(f)">Desfazer</button>
            <button v-else type="button" class="cfm-trace" :data-testid="`fusion-trace-${f.id}`" @click="traced = traced?.id === f.id ? null : f">
              {{ traced?.id === f.id ? 'Fechar' : 'Rastrear' }}
            </button>
            <!-- a luz que entra pela ponta do cabo para onde segue a metade A da fusão passa nesta emenda -->
            <FiberTrace v-if="traced?.id === f.id" class="cfm-trace-box" :strand-id="f.a.strand_id" :start="f.a.side" />
          </li>
        </ul>
      </aside>
    </div>
    <template #footer>
      <div class="flex justify-end gap-2">
        <EditInProjectLink v-if="readonly" type="ceo" :target="ceo" />
        <button type="button" class="btn" @click="$emit('close')">Fechar</button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
/**
 * Emendas de uma CEO (EV-0136): as pontas de fibra de cada cabo que passa na caixa (no tronco,
 * cada fibra tem as duas metades «→ A» e «→ B»), «Criar fusão» fibra A ↔ fibra B com bandeja e
 * posição, e a lista das fusões com «Desfazer».
 */
import { computed, ref, watch } from 'vue'
import { PhGitMerge } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import { useApi } from '@/composables/useApi'
import EditInProjectLink from '@/components/Map/EditInProjectLink.vue'
import FiberTrace from '@/components/Inventory/Fibers/FiberTrace.vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  ceo: { type: Object, required: true },
  /** EV-0137: no mapa de monitoramento só se vê (e rastreia) */
  readonly: { type: Boolean, default: false },
})
defineEmits(['close'])

const ROLE = { tronco: 'tronco (passa na caixa)', derivado: 'derivado (nasce aqui)', chegada: 'termina aqui' }
const api = useApi()
const data = ref(null)
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const pickA = ref(null)
const pickB = ref(null)
const tray = ref(null)
const slot = ref(null)
const traced = ref(null)
const url = computed(() => `/api/v1/inventory/ceos/${props.ceo.id}/fusions/`)
const modeHint = computed(() =>
  (data.value?.ceo?.mode || props.ceo.mode) === 'corte'
    ? 'Corte / emenda total: fibra do tronco sem emenda acaba na caixa'
    : 'Sangria: fibra do tronco sem emenda passa direto pela caixa',
)

const label = (e) => (e ? `${e.cable_name} · F${e.absolute_number} (${e.color}) → ${e.toward}` : '')

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

function pick(e) {
  if (props.readonly) return
  error.value = ''
  if (pickA.value?.key === e.key) pickA.value = null
  else if (!pickA.value) pickA.value = e
  else pickB.value = pickB.value?.key === e.key ? null : e
}
function clearPick() {
  pickA.value = null
  pickB.value = null
}

async function create() {
  if (!pickA.value || !pickB.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await api.post(url.value, {
      a: { strand_id: pickA.value.strand_id, side: pickA.value.side },
      b: { strand_id: pickB.value.strand_id, side: pickB.value.side },
      tray: Number.isFinite(tray.value) ? tray.value : null,
      slot: Number.isFinite(slot.value) ? slot.value : null,
    })
    clearPick()
    if (Number.isFinite(slot.value)) slot.value += 1
    await load()
  } catch (e) {
    error.value = e?.message || 'erro desconhecido'
  } finally {
    busy.value = false
  }
}

async function remove(f) {
  busy.value = true
  error.value = ''
  try {
    await api.delete(`${url.value}${f.id}/`)
    await load()
  } catch (e) {
    error.value = e?.message || 'erro desconhecido'
  } finally {
    busy.value = false
  }
}

watch(
  () => [props.show, props.ceo.id],
  ([open]) => {
    if (open) {
      clearPick()
      load()
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.cfm {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
}
@media (min-width: 1024px) {
  .cfm {
    grid-template-columns: minmax(0, 1fr) 320px;
  }
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.cfm-cable {
  padding: 10px 12px;
  margin-bottom: 10px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 8px;
}
.cfm-cable-title {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: rgb(var(--n-900));
}
.cfm-role {
  font-weight: 400;
  font-size: 11px;
  color: rgb(var(--n-500));
}
.cfm-ends {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.end {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 6px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  font-size: 11px;
  color: rgb(var(--n-800));
  background: rgb(var(--surface));
}
.end:hover:not(:disabled) {
  border-color: rgb(var(--primary-500));
}
.end-used {
  opacity: 0.45;
  cursor: not-allowed;
  border-color: rgb(var(--info) / 0.6);
}
.end-a,
.end-b {
  border-color: rgb(var(--primary-600));
  box-shadow: 0 0 0 2px rgb(var(--primary-500) / 0.35);
}
.end-side {
  color: rgb(var(--n-500));
}
.core {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  border: 1px solid rgb(var(--n-400));
}
.cfm-side {
  font-size: 12px;
}
.cfm-h {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: rgb(var(--n-600));
}
.cfm-pick {
  margin: 0 0 3px;
  color: rgb(var(--n-700));
}
.cfm-pick b {
  font-weight: 600;
  color: rgb(var(--n-900));
}
.fld {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-weight: 600;
  color: rgb(var(--n-700));
}
.fld input {
  padding: 4px 8px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  background: rgb(var(--surface));
  font-weight: 400;
  color: rgb(var(--n-900));
}
.cfm-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.cfm-list li {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  padding: 5px 0;
  border-top: 1px solid rgb(var(--n-200));
  color: rgb(var(--n-900));
}
.cfm-trace {
  font-size: 11px;
  color: rgb(var(--primary-600));
}
.cfm-trace-box {
  grid-column: 1 / -1;
}
.cfm-del {
  font-size: 11px;
  color: rgb(var(--danger));
}
.btn {
  height: 30px;
  padding: 0 10px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  font-size: 12px;
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
