<template>
  <div class="min-h-full flex flex-col bg-canvas text-neutral-900">
    <!-- EV-0123: uma só barra de rolagem — a do shell (App.vue <main>); o cabeçalho fica fixo -->
    <GponHeader
      v-model:olt="oltFilter"
      v-model:vendor="vendorFilter"
      v-model:pop="popFilter"
      v-model:filter="filter"
      v-model:query="query"
      :zabbix="zabbix"
      :zabbix-error="data?.zabbix_error || null"
      :thresholds="thresholds"
      :olts="scopedOlts"
      :all-count="allOlts.length"
      :vendors="vendors"
      :pops="pops"
      :loading="loading"
      @refresh="load"
    />

    <main class="flex-1 px-4 md:px-6 py-3 flex flex-col gap-3">
      <p v-if="error" class="px-3 py-2 rounded-md border border-danger/40 bg-danger/10 text-sm text-danger" role="alert" data-testid="gpon-error">
        Erro ao carregar o monitoramento GPON: {{ error }}
      </p>
      <p v-if="data && !data.zabbix_ok" class="px-3 py-2 rounded-md border border-warning/40 bg-warning/10 text-sm text-warning" role="alert" data-testid="gpon-zabbix-down">
        Zabbix indisponível na última coleta: os estados abaixo podem estar desatualizados.
      </p>
      <p v-if="loading && !data" class="text-sm text-neutral-500">Carregando…</p>

      <template v-if="data">
        <!-- EV-0120: trilha do afunilamento — KPIs, chassi e tabela seguem o nível escolhido -->
        <nav v-if="funnel.level !== 'network'" class="funnel" aria-label="Afunilamento" data-testid="gpon-funnel">
          <button type="button" class="crumb-root" data-testid="gpon-funnel-network" @click="backToNetwork">Rede</button>
          <PhCaretRight :size="12" class="text-neutral-400" aria-hidden="true" />
          <span class="chip" data-testid="gpon-funnel-olt">
            {{ funnel.olt?.name || 'OLT' }}
            <button type="button" class="chip-x" title="Voltar à rede inteira" aria-label="Tirar a OLT" @click="backToNetwork">
              <PhX :size="11" weight="bold" />
            </button>
          </span>
          <template v-if="funnel.level === 'pon' || funnel.level === 'slot'">
            <PhCaretRight :size="12" class="text-neutral-400" aria-hidden="true" />
            <span class="chip chip-on" data-testid="gpon-funnel-pon">
              {{ funnel.label }}
              <button type="button" class="chip-x" title="Voltar à OLT inteira" aria-label="Tirar a porta" data-testid="gpon-funnel-pon-clear" @click="backToOlt">
                <PhX :size="11" weight="bold" />
              </button>
            </span>
          </template>
        </nav>
        <GponKpis :totals="totals" :olt="funnel.olt" />

        <p v-if="!visibleOlts.length" class="px-3 py-4 rounded-lg border border-neutral-200 bg-surface text-center text-sm text-neutral-500" data-testid="gpon-no-olts">
          Nenhuma OLT neste filtro.
        </p>
        <div v-if="visibleOlts.length" class="flex items-center justify-end">
          <div class="view-toggle" role="group" aria-label="Vista das OLTs" data-testid="gpon-view-toggle">
            <button
              v-for="v in VIEWS"
              :key="v.value"
              type="button"
              :class="{ 'view-on': view === v.value }"
              :aria-pressed="view === v.value"
              :data-testid="`gpon-view-${v.value}`"
              @click="setView(v.value)"
            >
              <component :is="v.icon" :size="14" /> {{ v.label }}
            </button>
          </div>
        </div>

        <template v-if="view === 'chassis'">
          <OltChassis
            v-for="o in visibleOlts"
            :key="o.device_id"
            :olt="o"
            :pons="ponsOf(o.device_id)"
            :filtered="filter !== 'all'"
            :selected-pon="selectedPon"
            :selected-slot="selectedSlot"
            :thresholds="thresholds"
            :onus="onusOf(o.device_id)"
            :signal-band="signalBand"
            @toggle-pon="togglePon"
            @toggle-slot="toggleSlot"
            @clear-selection="clearSelection"
            @signal-band="toggleSignalBand"
          />
        </template>
        <template v-else>
          <OltCard
            v-for="o in visibleOlts"
            :key="o.device_id"
            :olt="o"
            :selected-pon="selectedPon"
            @toggle-pon="togglePon"
          />
        </template>

        <OnuTable
          :onus="visibleOnus"
          :scope="tableScope"
          :events-for="eventsFor"
          :refresh-key="data?.collected_at || null"
          :show-olt="oltFilter === null && selectedPon === null && selectedSlot === null"
          :thresholds="thresholds"
        />
      </template>
    </main>

  </div>
</template>

<script setup>
/**
 * Monitoramento GPON (EV-0095): OLTs, PONs e ONUs a partir do estado que a tarefa
 * de coleta gravou (o pedido não vai ao Zabbix). «Zabbix fora» ≠ «sem dados».
 */
import { computed, ref } from 'vue'
import { PhCaretRight, PhCube, PhSquaresFour, PhX } from '@phosphor-icons/vue'
import GponHeader from '@/components/Gpon/GponHeader.vue'
import GponKpis from '@/components/Gpon/GponKpis.vue'
import OltCard from '@/components/Gpon/OltCard.vue'
import OltChassis from '@/components/Gpon/OltChassis.vue'
import OnuTable from '@/components/Gpon/OnuTable.vue'
import { VIEW_KEY, useGponOverview } from '@/composables/useGponOverview'

const {
  data,
  loading,
  error,
  oltFilter,
  filter,
  query,
  selectedPon,
  selectedSlot,
  allOlts,
  vendorFilter,
  popFilter,
  vendors,
  pops,
  scopedOlts,
  thresholds,
  totals,
  funnel,
  zabbix,
  visibleOlts,
  visibleOnus,
  tableScope,
  load,
  togglePon,
  toggleSlot,
  clearSelection,
  signalBand,
  toggleSignalBand,
  focusOlt,
} = useGponOverview()

/** EV-0120: × da porta volta à OLT inteira (sem reescolher a PON mais crítica). */
function backToOlt() {
  focusOlt(funnel.value.olt?.device_id ?? null, { autoPon: false })
}
/** × da OLT (ou «Rede») volta à rede inteira. */
function backToNetwork() {
  focusOlt(null)
}

/** Vista das OLTs (EV-0101): painel frontal (padrão) ou a grade compacta de cartões. */
const VIEWS = [
  { value: 'chassis', label: 'Vista do chassi', icon: PhCube },
  { value: 'grid', label: 'Grade compacta', icon: PhSquaresFour },
]
function readView() {
  try {
    return localStorage.getItem(VIEW_KEY) === 'grid' ? 'grid' : 'chassis'
  } catch {
    return 'chassis'
  }
}
const view = ref(readView())
function setView(v) {
  view.value = v
  if (v === 'grid') selectedSlot.value = null
  try {
    localStorage.setItem(VIEW_KEY, v)
  } catch {
    /* sem localStorage (janela privada): a escolha vale só nesta visita */
  }
}

/** EV-0108: PON selecionada para a aba de eventos ({ deviceId, ponId }) ou null. */
const eventsFor = computed(() => {
  const key = selectedPon.value
  if (key === null) return null
  const i = key.indexOf(':')
  return { deviceId: Number(key.slice(0, i)), ponId: key.slice(i + 1) }
})

/** EV-0107: ONUs de uma OLT (todas, sem filtros), indexadas uma vez por atualização. */
const onusByOlt = computed(() => {
  const map = new Map()
  for (const o of data.value?.onus || []) {
    if (!map.has(o.device_id)) map.set(o.device_id, [])
    map.get(o.device_id).push(o)
  }
  return map
})
function onusOf(deviceId) {
  return onusByOlt.value.get(deviceId) || []
}

/** Todas as PONs de uma OLT (sem a pílula), para os LEDs do chassi. */
function ponsOf(deviceId) {
  return allOlts.value.find((o) => o.device_id === deviceId)?.pons || []
}

</script>

<style scoped>
.funnel {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 12px;
}
.crumb-root {
  color: rgb(var(--n-500));
}
.crumb-root:hover {
  color: rgb(var(--primary-600));
  text-decoration: underline;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 1px 4px 1px 8px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 999px;
  background: rgb(var(--surface));
  color: rgb(var(--n-800));
  font-weight: 600;
}
.chip-on {
  border-color: rgb(var(--primary-500));
  background: rgb(var(--primary-500) / 0.1);
  color: rgb(var(--primary-700));
}
.chip-x {
  display: inline-flex;
  padding: 2px;
  border-radius: 999px;
  color: rgb(var(--n-500));
}
.chip-x:hover {
  background: rgb(var(--n-200));
  color: rgb(var(--n-900));
}
.view-toggle {
  display: inline-flex;
  padding: 2px;
  border-radius: 8px;
  border: 1px solid rgb(var(--n-200));
  background: rgb(var(--surface));
}
.view-toggle button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  color: rgb(var(--n-600));
}
.view-toggle button:hover {
  color: rgb(var(--n-800));
}
.view-toggle .view-on {
  color: rgb(var(--primary-600));
  background: rgb(var(--primary-500) / 0.12);
  font-weight: 600;
}
.view-toggle button:focus-visible {
  outline: 2px solid rgb(var(--primary-500));
  outline-offset: 1px;
}
</style>
